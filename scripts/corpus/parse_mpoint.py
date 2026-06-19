"""Generate MPoint (MPM) command documentation JSON from local HTML docs.

MPoint is the Material Point Method product in the Itasca Software Subscription.
Like 3DEC/FLAC it ships only the 9.x unified kernel, so this builds fresh
9.0-only command files (same shape as parse_3dec900.py):

    {
      "category": "mpoint",
      "search_keywords": [...],
      "description": "...",
      "python_sdk_alternative": {"available": false},
      "versions": {"9.0": {"command", "syntax", "keywords", "examples"}}
    }

MPoint's only engine-specific command family is ``mpoint`` (material points,
their background-grid nodes, conversion to/from zones). Everything else
(model/data/fish/geometry/history/plot/program/project/table) is the shared 9.0
kernel reused from ``_common/`` via generate_mpoint_index.py.

File-name prefix -> category:
    cmd_mpoint.*  -> mpoint   (incl. cmd_mpoint.node.* -> node-* subcommands)

Usage:
    uv run python scripts/corpus/parse_mpoint.py
"""

import json
from pathlib import Path

try:
    from parse_pfc600 import CommandHTMLParser, normalize_syntax
except ModuleNotFoundError:
    from .parse_pfc600 import CommandHTMLParser, normalize_syntax

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

MPM_DOC = Path("C:/Program Files/Itasca/Itasca Software Subscription/exe64/doc/mpm")
COMMANDS_DIR = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources/mpoint/command_docs/commands")

PREFIX_TO_CATEGORY = {
    "cmd_mpoint.": "mpoint",
}


def classify(stem: str) -> tuple[str, str] | None:
    """Map an HTML stem to (category, json_stem).

    >>> classify("cmd_mpoint.create")
    ('mpoint', 'create')
    >>> classify("cmd_mpoint.node.fix")
    ('mpoint', 'node-fix')
    """
    for prefix, category in PREFIX_TO_CATEGORY.items():
        if stem.startswith(prefix):
            sub = stem[len(prefix) :].replace(".", "-")
            return category, sub
    return None


def build_doc(category: str, parsed: dict) -> dict:
    """Assemble a 9.0-only command doc in the FLAC/3DEC corpus shape."""
    command = parsed["command"]
    syntax = normalize_syntax(parsed["syntax"])
    return {
        "category": category,
        "search_keywords": command.split(),
        "description": parsed["description"],
        "python_sdk_alternative": {"available": False},
        "versions": {
            "9.0": {
                "command": command,
                "syntax": syntax,
                "keywords": parsed["keywords"],
                "examples": [],
            }
        },
    }


def parse_html_file(html_path: Path) -> dict:
    parser = CommandHTMLParser()
    parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    return {
        "command": parser.command_name,
        "syntax": parser.command_syntax,
        "keywords": parser.keywords,
        "description": parser.description,
    }


def main() -> None:
    print("=== MPoint (MPM) 9.0 command documentation generator ===\n")
    if not MPM_DOC.exists():
        print(f"[ERROR] MPoint doc root not found: {MPM_DOC}")
        return

    counts: dict[str, int] = {}
    skipped: list[str] = []

    for html_path in sorted(MPM_DOC.rglob("cmd_*.html")):
        mapped = classify(html_path.stem)
        if mapped is None:
            continue
        category, json_stem = mapped

        parsed = parse_html_file(html_path)
        command = parsed["command"]
        # FISH-intrinsic pages (id="function:...") have a dotted h1 ("mpoint.disp")
        # rather than a space-separated command. Skip them.
        if not command or "." in command:
            skipped.append(html_path.name)
            print(f"  [SKIP] not a command page: {html_path.name}")
            continue

        doc = build_doc(category, parsed)

        out_dir = COMMANDS_DIR / category
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{json_stem}.json"
        out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        counts[category] = counts.get(category, 0) + 1
        print(f"  [OK] {command:40s} -> {category}/{json_stem}.json")

    print("\n--- per-category counts ---")
    for category in PREFIX_TO_CATEGORY.values():
        print(f"  {category:12s}: {counts.get(category, 0)}")
    print(f"  total       : {sum(counts.values())}")
    if skipped:
        print(f"  skipped     : {len(skipped)} -> {skipped}")
    print("\nDone.")


if __name__ == "__main__":
    main()
