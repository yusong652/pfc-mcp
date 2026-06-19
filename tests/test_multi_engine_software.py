"""Multi-engine (software param) tests: FLAC coverage, _common sharing, isolation.

PR1 introduced the required ``software`` selector and a per-engine corpus laid out
as ``resources/{_common,pfc,flac}/``. These tests lock in:
- FLAC browse/query works through the tools and loaders
- the shared ``_common`` kernel resolves for every engine
- engine corpora stay isolated (PFC-only vs FLAC-only families)
- ``software`` is genuinely required (no default engine)
"""

import json

import pytest

from itasca_mcp.knowledge.commands.loader import CommandLoader
from itasca_mcp.knowledge.config import SUPPORTED_SOFTWARE, normalize_software
from itasca_mcp.knowledge.python_api.loader import DocumentationLoader
from itasca_mcp.knowledge.query import APISearch, CommandSearch
from itasca_mcp.knowledge.references.loader import ReferenceLoader
from itasca_mcp.server import mcp


def _parse_tool_payload(result) -> dict:
    assert result is not None
    assert len(result.content) > 0
    text = result.content[0].text
    assert text.startswith("{")
    return json.loads(text)


# --- config / required-ness -------------------------------------------------


def test_supported_software_set() -> None:
    assert set(SUPPORTED_SOFTWARE) == {"pfc", "flac", "3dec"}


def test_normalize_software_validates() -> None:
    assert normalize_software("PFC") == "pfc"
    assert normalize_software("flac") == "flac"
    for bad in ("", "abaqus", "udec"):
        with pytest.raises(ValueError):
            normalize_software(bad)


@pytest.mark.asyncio
async def test_software_is_required_on_tools() -> None:
    """Omitting ``software`` is a validation error (there is no default engine)."""
    with pytest.raises(Exception, match="(?i)software"):
        await mcp.call_tool("pfc_browse_commands", {})


# --- FLAC coverage through the tools ----------------------------------------


@pytest.mark.asyncio
async def test_flac_browse_commands_root() -> None:
    result = await mcp.call_tool("pfc_browse_commands", {"software": "flac"})
    data = _parse_tool_payload(result)["data"]
    names = {e["name"] for e in data["entries"]}
    assert "zone" in names  # FLAC-only family
    assert "model" in names  # shared kernel family
    assert "ball" not in names  # PFC-only family must not leak
    assert data["summary"]["software"] == "flac"


@pytest.mark.asyncio
async def test_flac_browse_zone_command() -> None:
    result = await mcp.call_tool(
        "pfc_browse_commands", {"software": "flac", "command": "zone create", "version": "9.0"}
    )
    data = _parse_tool_payload(result)["data"]
    assert data["entries"][0]["doc"]["command"] == "zone create"


@pytest.mark.asyncio
async def test_flac_query_command_finds_zone() -> None:
    result = await mcp.call_tool("pfc_query_command", {"software": "flac", "query": "zone create"})
    data = _parse_tool_payload(result)["data"]
    assert data["summary"]["software"] == "flac"
    assert any("zone" in e["name"] for e in data["entries"])


@pytest.mark.asyncio
async def test_flac_browse_python_api_has_zone_not_ball() -> None:
    result = await mcp.call_tool("pfc_browse_python_api", {"software": "flac"})
    data = _parse_tool_payload(result)["data"]
    module_paths = {e.get("path") for e in data["entries"] if e.get("entry_type") == "module"}
    assert "itasca.zone" in module_paths
    assert "itasca.ball" not in module_paths


@pytest.mark.asyncio
async def test_flac_browse_reference_root() -> None:
    result = await mcp.call_tool("pfc_browse_reference", {"software": "flac"})
    data = _parse_tool_payload(result)["data"]
    names = {e["name"] for e in data["entries"]}
    assert "constitutive-models" in names


# --- _common sharing --------------------------------------------------------


def test_shared_model_solve_resolves_for_all_engines() -> None:
    # model solve points into _common/, which carries a 7.0 key for every engine.
    for sw in SUPPORTED_SOFTWARE:
        doc = CommandLoader.load_command_doc("model", "solve", "7.0", software=sw)
        assert doc is not None
        assert doc["command"] == "model solve"


def test_shared_itasca_module_resolves_for_all_engines() -> None:
    for sw in SUPPORTED_SOFTWARE:
        index = DocumentationLoader.load_index(software=sw)
        assert "itasca" in index["modules"]
        doc = DocumentationLoader.load_module("itasca", software=sw)
        assert doc is not None
        assert any(f["name"] == "command" for f in doc["functions"])


# --- isolation --------------------------------------------------------------


def test_command_families_are_engine_isolated() -> None:
    pfc = CommandLoader.load_index(software="pfc")["categories"]
    flac = CommandLoader.load_index(software="flac")["categories"]
    assert "ball" in pfc and "ball" not in flac
    assert "zone" in flac and "zone" not in pfc
    # shared kernel present in both
    assert "model" in pfc and "model" in flac


def test_search_is_engine_scoped() -> None:
    flac_hit = CommandSearch.search("zone create", top_k=3, software="flac")
    assert flac_hit and flac_hit[0].document.name == "zone create"
    api_hit = APISearch.search("zone gridpoint", top_k=3, software="flac")
    assert api_hit and "zone" in api_hit[0].document.name.lower() or "gridpoint" in api_hit[0].document.name.lower()


def test_reference_categories_are_engine_specific() -> None:
    pfc = set(ReferenceLoader.load_index(software="pfc").get("categories", {}))
    flac = set(ReferenceLoader.load_index(software="flac").get("categories", {}))
    assert "contact-models" in pfc
    assert "constitutive-models" in flac
    assert "contact-models" not in flac


# --- 3DEC coverage (9.0-only engine) ----------------------------------------
# 3DEC ships only the 9.x unified kernel, so commands are 9.0-only; queries must
# pass version="9.0" (the tool default 7.0 is a PFC-era leftover, same caveat as
# FLAC's 9.0-only families).


@pytest.mark.asyncio
async def test_3dec_browse_commands_root() -> None:
    result = await mcp.call_tool("pfc_browse_commands", {"software": "3dec", "version": "9.0"})
    data = _parse_tool_payload(result)["data"]
    names = {e["name"] for e in data["entries"]}
    assert "block" in names  # 3DEC-only family
    assert "model" in names  # shared kernel family
    assert "ball" not in names  # PFC-only family must not leak
    assert "zone" not in names  # FLAC-only top-level family (3DEC uses 'block zone ...')
    assert data["summary"]["software"] == "3dec"


@pytest.mark.asyncio
async def test_3dec_browse_block_zone_generate() -> None:
    result = await mcp.call_tool(
        "pfc_browse_commands", {"software": "3dec", "command": "block zone generate", "version": "9.0"}
    )
    data = _parse_tool_payload(result)["data"]
    assert data["entries"][0]["doc"]["command"] == "block zone generate"


@pytest.mark.asyncio
async def test_3dec_query_command_finds_block_create() -> None:
    result = await mcp.call_tool("pfc_query_command", {"software": "3dec", "query": "create block", "version": "9.0"})
    data = _parse_tool_payload(result)["data"]
    assert data["summary"]["software"] == "3dec"
    assert any(e["name"] == "block create" for e in data["entries"])


@pytest.mark.asyncio
async def test_3dec_python_api_exposes_itasca_core() -> None:
    result = await mcp.call_tool("pfc_query_python_api", {"software": "3dec", "query": "run command"})
    data = _parse_tool_payload(result)["data"]
    assert any(e.get("api_path") == "itasca.command" for e in data["entries"])


# --- 3DEC engine-specific Python API ----------------------------------------
# The full 3DEC proprietary namespace (block / flowknot / flowplane / structure /
# dfn / contact / history / fish) is parsed from the local 9.0 Sphinx python docs
# by scripts/corpus/parse_3dec_python.py. These modules are 3DEC-only (no PFC/FLAC
# equivalent) and must not leak across engines.


def test_3dec_block_module_and_class_resolve() -> None:
    # Module function.
    find = DocumentationLoader.load_api_doc("itasca.block.find", software="3dec")
    assert find is not None
    assert find["signature"].startswith("itasca.block.find(")
    # Class method via its full official path.
    vol = DocumentationLoader.load_api_doc("itasca.block.Block.vol", software="3dec")
    assert vol is not None
    assert vol["signature"] == "block.vol() -> float"


def test_3dec_block_submodule_class_resolves() -> None:
    # Sub-namespace class (itasca.block.subcontact.Subcontact) resolves end to end.
    fs = DocumentationLoader.load_api_doc("itasca.block.subcontact.Subcontact.force_shear", software="3dec")
    assert fs is not None
    assert "force_shear" in fs["signature"]


def test_3dec_block_objects_registered_in_index() -> None:
    index = DocumentationLoader.load_index(software="3dec")
    assert "block" in index["modules"]
    assert "Block" in index["objects"]
    # The Block module exposes exactly the six confirmed namespace functions.
    assert set(index["modules"]["block"]["functions"]) == {
        "containing",
        "count",
        "find",
        "list",
        "maxid",
        "near",
    }


def test_3dec_python_block_family_is_engine_isolated() -> None:
    # block family is 3DEC-only: it must not appear in PFC/FLAC python indices.
    for sw in ("pfc", "flac"):
        assert "block" not in DocumentationLoader.load_index(software=sw)["modules"]


def test_3dec_python_search_finds_block_method() -> None:
    # API-path style query (a documented use case) ranks the exact method first.
    hits = APISearch.search("Block.vol", top_k=5, software="3dec")
    assert hits and hits[0].document.name == "itasca.block.Block.vol"


def test_3dec_structure_exposes_all_element_classes() -> None:
    # itasca.structure carries six element classes directly (no PFC/FLAC analogue).
    index = DocumentationLoader.load_index(software="3dec")
    for cls in ("Beam", "Cable", "Geogrid", "Liner", "Pile", "Shell"):
        assert cls in index["objects"], cls
    pile = DocumentationLoader.load_api_doc("itasca.structure.Pile.force", software="3dec")
    assert pile is not None and pile["signature"].startswith("pile.force(")


def test_3dec_dfn_and_flow_modules_resolve() -> None:
    frac = DocumentationLoader.load_api_doc("itasca.dfn.DFN.create_fracture", software="3dec")
    assert frac is not None
    fk = DocumentationLoader.load_api_doc("itasca.flowknot.find", software="3dec")
    assert fk is not None and fk["signature"].startswith("itasca.flowknot.find(")


def test_3dec_colliding_class_names_disambiguate_by_full_path() -> None:
    # Zone exists in both block.zone and flowplane.zone; Vertex in flowplane.vertex
    # and dfn.vertex; Contact in contact and block.contact. The shallower/earlier
    # one keeps the bare object key, the other is registered under its full path.
    index = DocumentationLoader.load_index(software="3dec")
    objects = index["objects"]
    assert "Zone" in objects and "itasca.flowplane.zone.Zone" in objects
    assert "Vertex" in objects and "itasca.flowplane.vertex.Vertex" in objects
    # Bare Zone resolves to the block.zone variant; the flowplane variant is reachable
    # under its full path. Both keep correct, distinct method docs.
    bare = DocumentationLoader.load_object("Zone", software="3dec")
    flow = DocumentationLoader.load_object("itasca.flowplane.zone.Zone", software="3dec")
    assert bare is not None and "block.zone" in bare["note"]
    assert flow is not None and "flowplane.zone" in flow["note"]


def test_3dec_python_proprietary_modules_isolated_from_pfc_flac() -> None:
    threedec = set(DocumentationLoader.load_index(software="3dec")["modules"])
    for sw in ("pfc", "flac"):
        other = set(DocumentationLoader.load_index(software=sw)["modules"])
        # None of the 3DEC-only families leak into the other engines.
        assert not ({"block", "flowknot", "flowplane", "structure", "dfn"} & other)
    assert {"block", "flowknot", "flowplane", "structure", "dfn", "contact"} <= threedec


def test_3dec_command_families_are_isolated() -> None:
    threedec = CommandLoader.load_index(software="3dec")["categories"]
    pfc = CommandLoader.load_index(software="pfc")["categories"]
    flac = CommandLoader.load_index(software="flac")["categories"]
    assert "block" in threedec and "block" not in pfc and "block" not in flac
    assert "model" in threedec  # shared kernel present
    assert "ball" not in threedec and "zone" not in threedec


# --- 3DEC references (joint constitutive models) ----------------------------
# Joint (sub-contact) constitutive models are 3DEC's defining reference and have
# no FLAC/PFC equivalent. Generated by scripts/corpus/generate_3dec_joint_models.py.


def test_3dec_joint_models_reference_category() -> None:
    cats = ReferenceLoader.load_index(software="3dec").get("categories", {})
    assert "joint-models" in cats
    # PFC contact-models / FLAC constitutive-models stay out of 3DEC.
    assert "contact-models" not in cats and "constitutive-models" not in cats


def test_3dec_joint_models_lists_all_eight() -> None:
    cat = ReferenceLoader.load_category_index("joint-models", software="3dec")
    assert cat is not None
    names = {m["name"] for m in cat["models"]}
    assert names == {
        "elastic",
        "mohr",
        "bilinear-mohr",
        "softening-mohr",
        "cyjm",
        "nonlinear",
        "power",
        "ratestate",
    }


def test_3dec_joint_model_item_has_property_vocabulary() -> None:
    mohr = ReferenceLoader.load_item_doc("joint-models", "mohr", software="3dec")
    assert mohr is not None
    keywords = {p["keyword"] for grp in mohr["property_groups"] for p in grp["properties"]}
    # Core Coulomb-slip joint property keywords parsed from the theory page.
    assert {"stiffness-normal", "stiffness-shear", "friction", "cohesion", "tension"} <= keywords


@pytest.mark.asyncio
async def test_3dec_browse_reference_joint_models() -> None:
    result = await mcp.call_tool("pfc_browse_reference", {"software": "3dec", "topic": "joint-models"})
    data = _parse_tool_payload(result)["data"]
    assert {e.get("name") for e in data["entries"]} >= {"mohr", "cyjm", "nonlinear"}


def test_3dec_references_isolated_from_flac() -> None:
    # joint-models is 3DEC-only; it must not appear in the FLAC reference index.
    flac = set(ReferenceLoader.load_index(software="flac").get("categories", {}))
    assert "joint-models" not in flac
