"""Generate the 3DEC ``geometry-data-table`` reference category.

geometry / data / table are 9.0 kernel commands present in every engine, but the
*workflow* around geometry differs (FLAC imports geometry to guide zone meshing;
3DEC uses it to guide block cutting and selection). Rather than borrow FLAC's
FLAC-flavoured topic docs, these are authored for 3DEC with verified 3DEC
commands. data / table content mirrors the shared kernel.

Referenced commands are validated against the 3DEC command corpus.

Usage:
    uv run python scripts/corpus/generate_3dec_geometry_data_table.py
"""

import json
from pathlib import Path
from typing import Any

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
OUT = RES / "3dec/references"
CAT_DIR = OUT / "geometry-data-table"
CMD_INDEX = RES / "3dec/command_docs/index.json"

ITEMS: list[dict[str, Any]] = [
    {
        "name": "geometry-workflow",
        "full_name": "Geometry Import / Generation Workflow",
        "description": (
            "Geometry sets (nodes, edges, polygons) describe surfaces and structures used to guide block "
            "cutting and selection in 3DEC, and to import external CAD/measured geometry. Distinct from the "
            "blocks themselves — geometry is a construction/selection aid."
        ),
        "primary_commands": [
            "geometry import",
            "geometry generate",
            "geometry export",
            "geometry edge create",
            "block cut",
        ],
        "common_patterns": [
            "geometry import '<file>.stl' — bring in an external surface",
            "block cut ... — cut blocks along joints/planes (imported geometry guides placement)",
            "range ... — geometry-based selection scopes downstream commands",
        ],
        "notes": [
            "Geometry is a construction aid; it does not itself create blocks or zones.",
            "Use 'block densify' to refine cut blocks where finer resolution is needed.",
        ],
    },
    {
        "name": "data-sets",
        "full_name": "Data Set Workflows",
        "description": (
            "Data commands manage model-space scalar, vector, tensor, and label data — useful for imported "
            "measurements, interpreted geology, and overlaying external results with model plots. Shared 9.0 "
            "kernel (same syntax across engines)."
        ),
        "primary_commands": [
            "data scalar create",
            "data scalar import",
            "data scalar export",
            "data vector create",
            "data tensor create",
            "data label create",
        ],
        "data_types": [
            {"type": "scalar", "use": "Point measurements such as pore pressure, elevation, or material index."},
            {"type": "vector", "use": "Directional measurements such as displacement or velocity vectors."},
            {"type": "tensor", "use": "Full stress/strain tensors at points."},
            {"type": "label", "use": "Text annotations placed in model space."},
        ],
        "notes": ["Imported data sets can be grouped and exported; pair with plots to overlay external results."],
    },
    {
        "name": "table-curves",
        "full_name": "Table Curves",
        "description": (
            "Tables store x-y pairs used for load histories, property curves, boundary-condition modifiers, and "
            "exported history data. Shared 9.0 kernel."
        ),
        "primary_commands": [
            "table add",
            "table insert",
            "table import",
            "table export",
            "table list",
            "history export",
        ],
        "syntax_note": (
            "Every table subcommand except 'table list' takes a table name first: "
            "\"table '<name>' add (x,y) ...\". Reference a table from 'apply ... table '<name>'' "
            "or 'fish' for time/space-varying values."
        ),
        "notes": ["History results can be written to a table via 'history export ... table '<name>''."],
    },
]


def _valid_commands() -> set[str]:
    idx = json.loads(CMD_INDEX.read_text(encoding="utf-8"))
    out = set()
    for cat_name, cat in idx["categories"].items():
        for c in cat.get("commands", []):
            out.add(f"{cat_name} {c['name'].replace('-', ' ')}")
    return out


def main() -> None:
    valid = _valid_commands()
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []
    for item in ITEMS:
        for cmd in item["primary_commands"]:
            toks = cmd.replace("-", " ").split()
            if not any(" ".join(toks[:n]) in valid for n in range(len(toks), 0, -1)):
                raise SystemExit(f"command not in 3DEC corpus: {cmd!r}")
        doc = {"name": item["name"], "dimension": "3D", **{k: v for k, v in item.items() if k != "name"}}
        (CAT_DIR / f"{item['name']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")
        catalog.append({"name": item["name"], "file": f"{item['name']}.json", "full_name": item["full_name"]})
        print(f"  {item['name']:<20} cmds={len(item['primary_commands'])}")

    (CAT_DIR / "index.json").write_text(
        json.dumps(
            {
                "type": "geometry_data_table",
                "description": (
                    "Geometry, data, and table references for 3DEC model setup, imported measurements, and "
                    "time/property curves. geometry guides block cutting; data/table are shared 9.0 kernel."
                ),
                "items": catalog,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        "utf-8",
    )

    top_path = OUT / "index.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top.setdefault("categories", {})["geometry-data-table"] = {
        "name": "Geometry, Data & Tables",
        "description": (
            "3DEC geometry import/generation (guides block cutting), data sets (scalar/vector/tensor/label), "
            "and table curves (load histories, property curves)."
        ),
        "directory": "geometry-data-table",
        "index_file": "geometry-data-table/index.json",
        "summary": f"{len(catalog)} topics: geometry workflow, data sets, table curves",
        "usage": "geometry import '<file>' ; data scalar create ... ; table '<name>' add (x,y) ...",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} topics)")


if __name__ == "__main__":
    main()
