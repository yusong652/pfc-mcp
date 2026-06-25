"""Tests for the figure_reference corpus-flagging pipeline.

The ``scripts/corpus/flag_figure_defined.py`` pass marks command docs whose
geometry/parameters are defined only in figures the text corpus dropped (e.g.
``zone create2d`` primitives, whose reference-point ordering lives in
thumbnails). These tests guard both the detection logic and the end-to-end
surfacing of the flag through the loader (the path ``itasca_browse_commands``
uses).
"""

import importlib.util
from pathlib import Path

import pytest

from itasca_mcp.knowledge.commands.loader import CommandLoader

# Load the pipeline script as a module (it lives under scripts/, not the package).
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "corpus" / "flag_figure_defined.py"
_spec = importlib.util.spec_from_file_location("flag_figure_defined", _SCRIPT)
assert _spec and _spec.loader
flag_figure_defined = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flag_figure_defined)


class TestDeferralDetection:
    """Unit tests for the figure-deferral text detection."""

    def test_detects_reference_image_idiom(self):
        text = "The locations of these points are illustrated in the reference images."
        assert flag_figure_defined._find_deferrals(text)

    def test_detects_figures_above_idiom(self):
        text = "Refer to the figures above for entries and dimensions."
        assert flag_figure_defined._find_deferrals(text)

    def test_detects_thumbnail_idiom(self):
        text = "Click on any thumbnail above to access the enlargement."
        assert flag_figure_defined._find_deferrals(text)

    def test_ignores_plain_prose(self):
        text = "Create a ball at the given position with the given radius."
        assert flag_figure_defined._find_deferrals(text) == []

    def test_build_flag_collects_distinct_sentences(self):
        texts = [
            "Refer to the figures above for entries.",
            "Refer to the figures above for entries.",  # duplicate -> collapsed
            "Shown in the reference images.",
        ]
        flag = flag_figure_defined._build_flag(texts)
        assert flag is not None
        assert flag["text_incomplete"] is True
        assert len(flag["deferrals"]) == 2

    def test_build_flag_none_when_clean(self):
        assert flag_figure_defined._build_flag(["just plain text"]) is None


class TestApplyIdempotent:
    """The pass must be a stable fixed point."""

    def test_apply_twice_is_stable(self):
        doc = {
            "description": "shape command",
            "versions": {
                "9.0": {
                    "command": "zone create2d",
                    "keywords": [{"name": "size", "description": "shown in the reference images above."}],
                }
            },
        }
        first = flag_figure_defined._apply_to_doc(doc)
        second = flag_figure_defined._apply_to_doc(doc)
        assert first is True
        assert second is False  # nothing left to change
        assert "figure_reference" in doc["versions"]["9.0"]

    def test_stale_flag_removed_when_text_clean(self):
        doc = {
            "versions": {
                "9.0": {
                    "command": "x",
                    "keywords": [{"name": "k", "description": "plain prose only."}],
                    "figure_reference": {"text_incomplete": True, "note": "old", "deferrals": []},
                }
            }
        }
        changed = flag_figure_defined._apply_to_doc(doc)
        assert changed is True
        assert "figure_reference" not in doc["versions"]["9.0"]

    def test_unavailable_version_never_flagged(self):
        doc = {
            "description": "shown in the reference images",  # deferral in shared text
            "versions": {"6.0": {"available": False}},
        }
        flag_figure_defined._apply_to_doc(doc)
        assert "figure_reference" not in doc["versions"]["6.0"]


class TestCorpusUpToDate:
    """The committed corpus must already carry the flags (CI guard == --check)."""

    def test_committed_corpus_is_not_stale(self):
        import json

        stale = []
        for path in flag_figure_defined.iter_command_docs():
            doc = json.loads(path.read_text(encoding="utf-8"))
            if flag_figure_defined._apply_to_doc(doc):
                stale.append(path.name)
        assert not stale, f"Run flag_figure_defined.py; stale: {stale}"


class TestFlagSurfacesThroughLoader:
    """End-to-end: the flag must reach the doc the browse tool returns."""

    def setup_method(self):
        CommandLoader.clear_cache()

    def test_create2d_carries_figure_reference(self):
        doc = CommandLoader.load_command_doc("zone", "create2d", "9.0", software="flac")
        assert doc is not None
        fr = doc.get("figure_reference")
        assert fr is not None
        assert fr["text_incomplete"] is True
        assert any("reference image" in d.lower() or "figures above" in d.lower() for d in fr["deferrals"])

    def test_plain_command_has_no_figure_reference(self):
        doc = CommandLoader.load_command_doc("ball", "create", "7.0", software="pfc")
        assert doc is not None
        assert "figure_reference" not in doc


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
