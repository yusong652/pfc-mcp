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
    assert set(SUPPORTED_SOFTWARE) == {"pfc", "flac", "3dec", "mpoint"}


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


def test_3dec_command_families_are_isolated() -> None:
    threedec = CommandLoader.load_index(software="3dec")["categories"]
    pfc = CommandLoader.load_index(software="pfc")["categories"]
    flac = CommandLoader.load_index(software="flac")["categories"]
    assert "block" in threedec and "block" not in pfc and "block" not in flac
    assert "model" in threedec  # shared kernel present
    assert "ball" not in threedec and "zone" not in threedec


def test_3dec_ships_no_references_yet() -> None:
    # references are optional; 3DEC ships none this round -> empty index, no error.
    assert ReferenceLoader.load_index(software="3dec").get("categories", {}) == {}


# --- MPoint / MPM coverage (9.0-only engine) --------------------------------
# MPoint is the Material Point Method product; like 3DEC/FLAC it ships only the
# 9.x unified kernel, so commands are 9.0-only (queries pass version="9.0").


@pytest.mark.asyncio
async def test_mpoint_browse_commands_root() -> None:
    result = await mcp.call_tool("pfc_browse_commands", {"software": "mpoint", "version": "9.0"})
    data = _parse_tool_payload(result)["data"]
    names = {e["name"] for e in data["entries"]}
    assert "mpoint" in names  # MPoint-only family
    assert "model" in names  # shared kernel family
    assert "ball" not in names  # PFC-only family must not leak
    assert "block" not in names  # 3DEC-only family must not leak
    assert "zone" not in names  # FLAC-only top-level family
    assert data["summary"]["software"] == "mpoint"


@pytest.mark.asyncio
async def test_mpoint_browse_mpoint_create() -> None:
    result = await mcp.call_tool(
        "pfc_browse_commands", {"software": "mpoint", "command": "mpoint create", "version": "9.0"}
    )
    data = _parse_tool_payload(result)["data"]
    assert data["entries"][0]["doc"]["command"] == "mpoint create"


@pytest.mark.asyncio
async def test_mpoint_browse_node_subcommand() -> None:
    # 'mpoint node fix' is keyed as node-fix.json but addressed with spaces.
    result = await mcp.call_tool(
        "pfc_browse_commands", {"software": "mpoint", "command": "mpoint node fix", "version": "9.0"}
    )
    data = _parse_tool_payload(result)["data"]
    assert data["entries"][0]["doc"]["command"] == "mpoint node fix"


@pytest.mark.asyncio
async def test_mpoint_query_command_finds_mpoint_create() -> None:
    result = await mcp.call_tool(
        "pfc_query_command", {"software": "mpoint", "query": "create material point", "version": "9.0"}
    )
    data = _parse_tool_payload(result)["data"]
    assert data["summary"]["software"] == "mpoint"
    assert any(e["name"] == "mpoint create" for e in data["entries"])


@pytest.mark.asyncio
async def test_mpoint_python_api_exposes_itasca_core() -> None:
    result = await mcp.call_tool("pfc_query_python_api", {"software": "mpoint", "query": "run command"})
    data = _parse_tool_payload(result)["data"]
    assert any(e.get("api_path") == "itasca.command" for e in data["entries"])


def test_mpoint_command_families_are_isolated() -> None:
    mpoint = CommandLoader.load_index(software="mpoint")["categories"]
    assert "mpoint" in mpoint  # proprietary family
    assert "model" in mpoint and "fish" in mpoint  # shared kernel borrowed
    # other engines' proprietary families must not leak in
    assert "ball" not in mpoint and "block" not in mpoint and "zone" not in mpoint


def test_mpoint_borrows_common_kernel_verbatim() -> None:
    mpoint = CommandLoader.load_index(software="mpoint")["categories"]
    # every borrowed kernel command points back into _common/ (single source)
    for fam in ("data", "fish", "geometry", "history", "model", "plot", "table"):
        cmds = mpoint[fam]["commands"]
        assert cmds and all(str(c["file"]).startswith("_common/") for c in cmds)


def test_mpoint_plot_items_are_engine_specific() -> None:
    cat = ReferenceLoader.load_category_index("plot-items", software="mpoint")
    assert cat is not None
    names = {i["name"] for i in cat["items"]}
    # MPoint's distinctive plottable entities (material points + background grid).
    assert {"mpoint", "mpoint-vector", "mpoint-tensor", "meshpoint"} <= names
    # 'mpoint' is a directory item with a color-by sub-item (contour vs label).
    assert ReferenceLoader.is_directory_item("plot-items", "mpoint", software="mpoint")
    cb = ReferenceLoader.load_sub_item_doc("plot-items", "mpoint", "color-by", software="mpoint")
    assert {m["mode"] for m in cb["modes"]} == {"contour", "label"}
    # mpoint-vector documents the live-probed vector value set.
    vec = ReferenceLoader.load_item_doc("plot-items", "mpoint-vector", software="mpoint")
    assert "meshnode-vector" in vec["item_types"]  # shares the keyword set
