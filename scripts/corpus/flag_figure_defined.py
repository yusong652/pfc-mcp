"""Flag figure-defined command docs across the whole command corpus.

Many Itasca primitive/geometry commands define their geometry -- reference-point
ordering, ``size`` -> direction mapping, and ``dimension`` meaning -- ONLY in
figures. The corpus is extracted from HTML ``<dt>``/``<dd>`` text (see
``parse_pfc*.py``) and drops ``<img>`` thumbnails, so the text repeatedly defers
to "the figures above" / "the reference images" without ever stating the
convention. An agent reading the text alone cannot use these commands correctly
(observed on ``zone create2d`` annular-sector / sector-quad: point order and the
``s1 s2 s3`` directions are figure-only).

This post-processing pass scans every command doc for figure-deferral phrases
and, when found, annotates the affected version entry with a structured
``figure_reference`` flag. The flag flows untouched through
``CommandLoader._resolve_versioned_doc`` (which does ``resolved.update(version_doc)``)
into the ``doc`` payload of ``itasca_browse_commands`` -- so the gap becomes
visible to agents at query time, for *every* figure-defined command, without
hand-authoring per-command content.

It does not invent the missing geometry; it marks the text as incomplete and
points at the reliable recovery path (probe the engine empirically).

Idempotent: re-running recomputes the flag from scratch (stale flags are
removed when the deferral text is gone).

Usage:
    uv run python scripts/corpus/flag_figure_defined.py
    uv run python scripts/corpus/flag_figure_defined.py --check   # exit 1 if stale (CI guard)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

RESOURCES = Path(__file__).resolve().parents[2] / "src" / "itasca_mcp" / "knowledge" / "resources"

FLAG_KEY = "figure_reference"

# Phrases in the extracted text that defer to a figure/image the corpus dropped.
# Case-insensitive. Kept deliberately specific so prose that merely mentions a
# "figure of merit" etc. is not swept in.
DEFERRAL_PATTERNS: tuple[str, ...] = (
    r"refer to the figures?\b",
    r"refer to figures?\b",
    r"see the figures?\b",
    r"\bfigures?\s+above\b",
    r"\breference images?\b",
    r"illustrated in the reference",
    r"shown in the reference image",
    r"click (?:on )?any thumbnail",
    r"\bthumbnails?\b",
)

_COMPILED = [re.compile(p, re.IGNORECASE) for p in DEFERRAL_PATTERNS]

NOTE = (
    "This command's documentation refers to figures/images in the source manual that "
    "are not captured in this text corpus. Geometric or parametric detail conveyed only "
    "by those figures -- e.g. reference-point ordering (point 0..N), the size -> direction "
    "mapping, dimension meaning, or split/subdivision patterns -- may therefore be missing "
    "below. Do not guess it: confirm the specifics from the engine itself, e.g. build the "
    "construct and read back the resulting gridpoints/zones via itasca_execute_code."
)

# Cap how many sample sentences we store, to keep the corpus from bloating.
MAX_DEFERRALS = 6


def _find_deferrals(text: str) -> list[str]:
    """Return the distinct sentences in ``text`` that defer to a figure."""
    hits: list[str] = []
    for sentence in re.split(r"(?<=[.;])\s+", text or ""):
        s = sentence.strip()
        if not s:
            continue
        if any(rx.search(s) for rx in _COMPILED):
            hits.append(s)
    return hits


def _collect_text(doc: dict[str, Any], version_doc: dict[str, Any]) -> list[str]:
    """Gather every free-text field that an agent would read for one version."""
    texts: list[str] = []
    # Top-level description is shared across versions.
    if isinstance(doc.get("description"), str):
        texts.append(doc["description"])
    if isinstance(version_doc.get("description"), str):
        texts.append(version_doc["description"])
    for kw in version_doc.get("keywords", []) or []:
        if isinstance(kw, dict) and isinstance(kw.get("description"), str):
            texts.append(kw["description"])
    return texts


def _build_flag(texts: list[str]) -> dict[str, Any] | None:
    """Return the figure_reference flag for the given texts, or None."""
    deferrals: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for hit in _find_deferrals(text):
            if hit not in seen:
                seen.add(hit)
                deferrals.append(hit)
    if not deferrals:
        return None
    return {
        "text_incomplete": True,
        "note": NOTE,
        "deferrals": deferrals[:MAX_DEFERRALS],
    }


def _apply_to_doc(doc: dict[str, Any]) -> bool:
    """Annotate ``doc`` in place. Return True if anything changed."""
    changed = False
    versions = doc.get("versions")

    if isinstance(versions, dict):
        # Versioned schema: flag each available version independently.
        for _ver, version_doc in versions.items():
            if not isinstance(version_doc, dict):
                continue
            if version_doc.get("available") is False:
                # No content for this version; never carries a flag.
                if version_doc.pop(FLAG_KEY, None) is not None:
                    changed = True
                continue
            flag = _build_flag(_collect_text(doc, version_doc))
            changed |= _set_or_clear(version_doc, flag)
    else:
        # Flat schema: flag at the top level.
        flag = _build_flag(_collect_text(doc, doc))
        changed |= _set_or_clear(doc, flag)

    return changed


def _set_or_clear(target: dict[str, Any], flag: dict[str, Any] | None) -> bool:
    """Set ``FLAG_KEY`` to ``flag`` or remove it. Return True if it changed."""
    if flag is None:
        return target.pop(FLAG_KEY, None) is not None
    if target.get(FLAG_KEY) == flag:
        return False
    target[FLAG_KEY] = flag
    return True


def iter_command_docs() -> list[Path]:
    """All command-doc JSON files across every engine corpus."""
    return sorted(RESOURCES.glob("*/command_docs/commands/**/*.json"))


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    stale: list[Path] = []
    flagged = 0

    for path in iter_command_docs():
        doc = json.loads(path.read_text(encoding="utf-8"))
        # Gate writes on a real content change so we never reflow (and churn the
        # trailing-newline of) docs whose flag state is unaffected.
        if _apply_to_doc(doc):
            stale.append(path)
            if not check_only:
                path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # Count docs that ended up flagged (any version).
        if _doc_is_flagged(doc):
            flagged += 1

    rel = RESOURCES
    if check_only:
        if stale:
            print(f"[STALE] {len(stale)} command doc(s) need re-flagging:")
            for p in stale:
                print(f"  {p.relative_to(rel.parents[0])}")
            print("Run: uv run python scripts/corpus/flag_figure_defined.py")
            return 1
        print(f"figure_reference flags up to date ({flagged} flagged docs).")
        return 0

    print(f"Updated {len(stale)} file(s); {flagged} command doc(s) now carry a figure_reference flag.")
    return 0


def _doc_is_flagged(doc: dict[str, Any]) -> bool:
    versions = doc.get("versions")
    if isinstance(versions, dict):
        return any(isinstance(v, dict) and FLAG_KEY in v for v in versions.values())
    return FLAG_KEY in doc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
