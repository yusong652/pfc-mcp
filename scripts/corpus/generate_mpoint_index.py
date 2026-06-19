"""Generate resources/mpoint/command_docs/index.json.

Mirrors generate_3dec_index.py:

1. MPoint's one engine-specific family (``mpoint``) is scanned from the generated
   command JSON; each command's ``file`` pointer is RESOURCES-root-relative
   ("mpoint/command_docs/commands/mpoint/<stem>.json").

2. Shared-kernel commands are reused from the FLAC index: every command whose
   ``file`` points into ``_common/`` is copied verbatim (data/fish/geometry/
   history/plot/program/project/table + the shared ``model`` subset). MPoint is a
   9.0 unified-kernel product, so it supports the same _common command set.

Usage:
    uv run python scripts/corpus/generate_mpoint_index.py
"""

import json
from pathlib import Path
from typing import Any

RESOURCES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
COMMANDS_DIR = RESOURCES / "mpoint" / "command_docs" / "commands"
FLAC_INDEX = RESOURCES / "flac" / "command_docs" / "index.json"
OUT_INDEX = RESOURCES / "mpoint" / "command_docs" / "index.json"

CATEGORY_META: dict[str, dict[str, Any]] = {
    "mpoint": {
        "full_name": "Material Point Commands",
        "description": "Core MPoint (Material Point Method) commands: create/generate/import material points, assign constitutive models and properties, manage the background-grid nodes (fix/free/damping/dynamic/spacing/skin), convert between material points and zones, and drive PIC/FLIP blending, locking adjustment and volume limiting.",
        "command_prefix": "mpoint",
        "notes": [
            "Sub-namespaces are part of the JSON key: 'mpoint node fix' -> commands/mpoint/node-fix.json, 'mpoint zone-conversion' -> commands/mpoint/zone-conversion.json",
            "Material points carry state/history and move through a fixed background grid whose nodes are managed by the 'mpoint node ...' subcommands",
            "'mpoint zone-conversion' / 'mpoint generate' bridge MPM material points with the shared zone kernel",
        ],
    },
}

PROPRIETARY = list(CATEGORY_META.keys())


def _resolve_9_0(cmd_data: dict[str, Any]) -> dict[str, Any]:
    versions = cmd_data.get("versions")
    if isinstance(versions, dict) and "9.0" in versions:
        merged = dict(cmd_data)
        merged.update(versions["9.0"])
        return merged
    return cmd_data


def build_proprietary_category(category: str) -> dict[str, Any]:
    cat_dir = COMMANDS_DIR / category
    commands = []
    for cmd_path in sorted(cat_dir.glob("*.json")):
        data = _resolve_9_0(json.loads(cmd_path.read_text(encoding="utf-8")))
        description = data.get("description", "")
        short = description.split(".")[0] if description else ""
        if len(short) > 100:
            short = short[:97] + "..."
        python_alt = data.get("python_sdk_alternative", {})
        commands.append(
            {
                "name": cmd_path.stem,
                "file": f"mpoint/command_docs/commands/{category}/{cmd_path.name}",
                "short_description": short,
                "syntax": data.get("syntax", ""),
                "python_available": python_alt.get("available", False),
            }
        )
    meta = dict(CATEGORY_META[category])
    meta["commands"] = commands
    return meta


def borrow_common_categories() -> dict[str, dict[str, Any]]:
    """Copy every command from the FLAC index whose file points into _common/."""
    flac = json.loads(FLAC_INDEX.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for name, info in flac.get("categories", {}).items():
        common_cmds = [c for c in info.get("commands", []) if str(c.get("file", "")).startswith("_common/")]
        if not common_cmds:
            continue
        meta = {k: v for k, v in info.items() if k != "commands"}
        meta["commands"] = common_cmds
        out[name] = meta
    return out


def main() -> None:
    categories: dict[str, Any] = {}
    for category in PROPRIETARY:
        categories[category] = build_proprietary_category(category)
    common = borrow_common_categories()
    for name, meta in common.items():
        categories[name] = meta

    index = {
        "version": "1.0",
        "description": "MPoint (MPM) command documentation index for quick lookup and LLM-assisted command discovery",
        "categories": categories,
    }
    OUT_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    total = sum(len(c["commands"]) for c in categories.values())
    print(f"Wrote {OUT_INDEX}")
    print(f"  categories: {len(categories)}  total commands: {total}")
    print("  proprietary:", {c: len(categories[c]["commands"]) for c in PROPRIETARY})
    print("  reused _common:", {n: len(categories[n]["commands"]) for n in common})


if __name__ == "__main__":
    main()
