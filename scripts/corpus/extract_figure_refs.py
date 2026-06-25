"""Extract real figure references from the Itasca command HTML (build-time).

`flag_figure_defined.py` v1 keyed off text phrases ("refer to the figures
above"), which both under-catches (figure-defined commands worded differently)
and gives no actual link to the figure. This tool replaces that signal with the
ground truth: the `<img>` / thumbnail markup in the source HTML that the text
corpus dropped.

It walks the local Itasca documentation tree, and for every command page
(`cmd_*.html`) records the command name (from the page `<h1>`) and the
real reference figures it embeds (the `_images/*.png|svg|gif` it links, minus
`_static` logos, math/equation images, and `thumb_` duplicates). Each figure
path is verified to exist on disk.

Output is a committed, machine-independent manifest
(`scripts/corpus/figure_manifest.json`) mapping

    "<command name>": [ {"name": "sector-quad.png", "doc_path": "_images/sector-quad.png"}, ... ]

`flag_figure_defined.py` then consumes this manifest with NO dependency on a
local install, so the flag-application pass (and its CI freshness check) runs
anywhere. This tool is the install-dependent half; re-run it when regenerating
the corpus against a new engine release (mirrors `parse_pfc*.py`).

Usage:
    uv run python scripts/corpus/extract_figure_refs.py
    uv run python scripts/corpus/extract_figure_refs.py --doc-root "C:/Program Files/Itasca/PFC700/exe64/doc"
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[1]
MANIFEST_PATH = _HERE / "figure_manifest.json"

# Default doc tree: the unified 9.0 install carries every engine's docs, and the
# primitive reference figures are version-stable. Override with --doc-root to add
# older installs if a version ever diverges.
DEFAULT_DOC_ROOTS = [
    Path("C:/Program Files/Itasca/ItascaSoftware900/exe64/doc"),
]

# Reuse the corpus parser's <h1> -> command-name logic (handles the fishcmd span).
_spec = importlib.util.spec_from_file_location("parse_pfc600", _HERE / "parse_pfc600.py")
assert _spec and _spec.loader
_pp600 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pp600)
CommandHTMLParser = _pp600.CommandHTMLParser

# src=/href= pointing into the _images gallery. Captures the basename.
_IMG_RE = re.compile(r'(?:src|href)="[^"]*/_images/([^"/]+\.(?:png|svg|gif))"', re.IGNORECASE)

# Basenames that are not reference figures: rendered equations and UI chrome.
_NON_FIGURE_RE = re.compile(r"^(math|equation|eq\d|gear|icglogo|logo_blank)", re.IGNORECASE)


def _command_name(html: str) -> str:
    parser = CommandHTMLParser()
    parser.feed(html)
    return (parser.command_name or "").strip()


def _figures_in(html: str) -> set[str]:
    """Distinct full-size figure basenames referenced by the page."""
    names: set[str] = set()
    for raw in _IMG_RE.findall(html):
        # Collapse thumb_X.png -> X.png; the full-size is what we want to point at.
        name = raw[len("thumb_") :] if raw.lower().startswith("thumb_") else raw
        if _NON_FIGURE_RE.match(name):
            continue
        names.add(name)
    return names


def _resolve_on_disk(doc_root: Path, name: str) -> Path | None:
    """Verify the figure exists; figures live flat under <doc_root>/_images/."""
    candidate = doc_root / "_images" / name
    return candidate if candidate.exists() else None


def build_manifest(doc_roots: list[Path]) -> dict[str, list[dict[str, str]]]:
    manifest: dict[str, set[str]] = {}
    missing: list[str] = []
    pages = 0

    for doc_root in doc_roots:
        if not doc_root.exists():
            print(f"  [SKIP] doc root not found: {doc_root}")
            continue
        for html_path in doc_root.rglob("cmd_*.html"):
            html = html_path.read_text(encoding="utf-8", errors="replace")
            figures = _figures_in(html)
            if not figures:
                continue
            command = _command_name(html)
            if not command:
                continue
            pages += 1
            for name in figures:
                if _resolve_on_disk(doc_root, name) is None:
                    missing.append(f"{command}: {name} (referenced by {html_path.name})")
                    continue
                manifest.setdefault(command, set()).add(name)

    if missing:
        print(f"  [WARN] {len(missing)} referenced figure(s) not found on disk:")
        for m in missing[:10]:
            print(f"    {m}")

    print(f"  Scanned {pages} figure-bearing command page(s) -> {len(manifest)} distinct command(s).")

    return {
        command: [{"name": n, "doc_path": f"_images/{n}"} for n in sorted(names)]
        for command, names in sorted(manifest.items())
    }


def main(argv: list[str]) -> int:
    doc_roots = DEFAULT_DOC_ROOTS
    if "--doc-root" in argv:
        doc_roots = [Path(argv[argv.index("--doc-root") + 1])]

    manifest = build_manifest(doc_roots)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH.relative_to(REPO_ROOT)} ({len(manifest)} commands).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
