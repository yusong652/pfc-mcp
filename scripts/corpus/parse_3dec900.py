"""Generate 3DEC 9.0 command documentation JSON from local HTML docs.

Unlike parse_pfc{600,700,900}.py (which *inject* a 9.0 version block into
pre-existing PFC command JSON), 3DEC has no prior corpus, so this script builds
fresh 9.0-only command files -- the same shape FLAC uses:

    {
      "category": "block",
      "search_keywords": [...],
      "description": "...",
      "python_sdk_alternative": {"available": false},
      "versions": {"9.0": {"command", "syntax", "keywords", "examples"}}
    }

CommandLoader._resolve_versioned_doc treats a missing requested version as a
KeyError, which the tools surface as "not available in this version" -- so a
9.0-only doc correctly answers only version="9.0".

Engine-specific command families (file-name prefix -> category):
    cmd_block.*      -> block
    cmd_feblock.*    -> feblock
    cmd_fblock.*     -> fblock
    cmd_flowknot.*   -> flowknot
    cmd_flowplane.*  -> flowplane

Shared-kernel commands (model/fish/geometry/data/...) are NOT produced here;
the 3DEC command index reuses the _common/ corpus for those.

Usage:
    uv run python scripts/corpus/parse_3dec900.py
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

DEC900_DOC = Path("C:/Program Files/Itasca/ItascaSoftware900/exe64/doc/3dec")
COMMANDS_DIR = Path("C:/Dev/Han/itasca-mcp/src/itasca_mcp/knowledge/resources/3dec/command_docs/commands")

# File-name prefix -> 3DEC-proprietary category. Order matters only for clarity;
# prefixes are mutually exclusive ("cmd_block." never matches cmd_feblock.*).
PREFIX_TO_CATEGORY = {
    "cmd_block.": "block",
    "cmd_feblock.": "feblock",
    "cmd_fblock.": "fblock",
    "cmd_flowknot.": "flowknot",
    "cmd_flowplane.": "flowplane",
}


def classify(stem: str) -> tuple[str, str] | None:
    """Map an HTML stem to (category, json_stem).

    >>> classify("cmd_block.create")
    ('block', 'create')
    >>> classify("cmd_block.contact.apply")
    ('block', 'contact-apply')
    >>> classify("cmd_flowplane.zone.list")
    ('flowplane', 'zone-list')
    """
    for prefix, category in PREFIX_TO_CATEGORY.items():
        if stem.startswith(prefix):
            sub = stem[len(prefix) :].replace(".", "-")
            return category, sub
    return None


def build_doc(category: str, parsed: dict) -> dict:
    """Assemble a 9.0-only command doc in the FLAC corpus shape."""
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
    print("=== 3DEC 9.0 command documentation generator ===\n")
    if not DEC900_DOC.exists():
        print(f"[ERROR] 3DEC doc root not found: {DEC900_DOC}")
        return

    counts: dict[str, int] = {}
    skipped: list[str] = []

    for html_path in sorted(DEC900_DOC.rglob("cmd_*.html")):
        mapped = classify(html_path.stem)
        if mapped is None:
            continue
        category, json_stem = mapped

        parsed = parse_html_file(html_path)
        command = parsed["command"]
        # Some HTML files in the command tree are actually FISH-intrinsic pages
        # (id="function:..."), not commands. Their h1 is the dotted function
        # name ("block.disp") rather than a space-separated command. Skip them.
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

    print("\n--- per-category counts ---")
    for category in PREFIX_TO_CATEGORY.values():
        print(f"  {category:12s}: {counts.get(category, 0)}")
    print(f"  total       : {sum(counts.values())}")
    if skipped:
        print(f"  skipped     : {len(skipped)} -> {skipped}")
    print("\nDone.")


if __name__ == "__main__":
    main()
