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
    assert set(SUPPORTED_SOFTWARE) == {"pfc", "flac"}


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


def test_shared_model_solve_resolves_for_both_engines() -> None:
    for sw in ("pfc", "flac"):
        doc = CommandLoader.load_command_doc("model", "solve", "7.0", software=sw)
        assert doc is not None
        assert doc["command"] == "model solve"


def test_shared_itasca_module_resolves_for_both_engines() -> None:
    for sw in ("pfc", "flac"):
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
