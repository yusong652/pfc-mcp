"""Regression tests for concrete Contact type expansion."""

import json

import pytest

from pfc_mcp.knowledge.python_api.loader import DocumentationLoader
from pfc_mcp.knowledge.python_api.types.contact import THERMAL_CONTACT_METHODS, ContactTypeResolver
from pfc_mcp.server import mcp


def setup_function() -> None:
    DocumentationLoader.clear_cache()


def test_thermal_contact_methods_are_expanded_without_mechanical_force_methods() -> None:
    index = DocumentationLoader.load_index()
    quick_ref = index["quick_ref"]

    assert "itasca.BallBallThermalContact.gap" in quick_ref
    assert "itasca.BallBallThermalContact.normal" in quick_ref
    assert "itasca.BallBallThermalContact.pos" in quick_ref
    assert "itasca.BallBallThermalContact.shear" in quick_ref
    assert "itasca.BallBallThermalContact.force_normal" not in quick_ref
    assert "itasca.BallBallThermalContact.force_shear" not in quick_ref


def test_thermal_contact_loader_rejects_force_methods() -> None:
    assert DocumentationLoader.load_api_doc("itasca.BallBallThermalContact.gap") is not None
    assert DocumentationLoader.load_api_doc("itasca.BallBallThermalContact.force_normal") is None
    assert DocumentationLoader.load_method("BallBallThermalContact", "force_normal") is None


def test_thermal_contact_object_is_filtered_to_verified_methods() -> None:
    doc = DocumentationLoader.load_object("BallBallThermalContact")

    assert doc is not None
    method_names = {method["name"] for method in doc["methods"]}
    assert method_names == THERMAL_CONTACT_METHODS
    assert "force_normal" not in method_names
    assert "force_shear" not in method_names
    assert doc["availability"]["versions"] == ["6.0", "7.0", "9.0"]


def test_vertex_facet_contact_is_version_gated_to_pfc_9() -> None:
    index = DocumentationLoader.load_index()

    assert "itasca.VertexFacetContact.force_normal" in index["quick_ref"]

    doc = DocumentationLoader.load_api_doc("itasca.VertexFacetContact.force_normal")
    assert doc is not None
    assert doc["availability"]["versions"] == ["9.0"]


def test_contact_resolver_does_not_match_unrelated_object_methods() -> None:
    index = DocumentationLoader.load_index()

    assert ContactTypeResolver.resolve("BallBallContact.gap", index["quick_ref"]) is not None
    assert ContactTypeResolver.resolve("BallBallContact.radius", index["quick_ref"]) is None


@pytest.mark.asyncio
async def test_browse_python_api_reports_missing_thermal_force_method() -> None:
    result = await mcp.call_tool(
        "pfc_browse_python_api",
        {"api": "itasca.BallBallThermalContact.force_normal"},
    )

    assert result is not None
    payload = json.loads(result.content[0].text)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "method_not_found"
    assert "force_normal" not in payload["error"]["details"]["available_methods"]
