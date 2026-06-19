"""Generate the 3DEC ``histories-and-results`` reference category.

History monitoring and results export are largely the shared 9.0 kernel, but the
*sampling targets* are engine-specific: FLAC samples ``zone history`` /
``gridpoint history``; 3DEC samples ``block history`` / ``block contact history``
(joints) / ``model history`` / ``fish history`` / ``structure history``. The
sampled field names are the same vocabulary as the plot-items contour attributes,
so this category points back to plot-items rather than re-listing them.

This is the lighter sibling of FLAC's category (FLAC's per-entity results
inclusion keywords don't exist in 3DEC — 3DEC's ``model results`` selects content
via a FISH-symbol/attribute ``map`` instead). Two topics: history-workflow and
results-export.

Every referenced ``... history`` / ``model results`` / ``history ...`` command is
validated against the 3DEC command corpus (longest-prefix match); sampling
sub-forms not carried as standalone corpus pages (block gridpoint / structure
history) were probed live via the bridge and appear only in notes.

Usage:
    uv run python scripts/corpus/generate_3dec_histories_and_results.py
"""

import json
from pathlib import Path
from typing import Any

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
OUT = RES / "3dec/references"
CAT_DIR = OUT / "histories-and-results"
CMD_INDEX = RES / "3dec/command_docs/index.json"
DOC = "https://docs.itascacg.com/itasca900/common/kernel/doc/manual/history_manual/history.html"

ITEMS: list[dict[str, Any]] = [
    {
        "name": "history-workflow",
        "full_name": "History Sampling & Monitoring Workflow",
        "description": (
            "Histories sample a single quantity at a common interval during cycling — used for convergence "
            "checks, load/displacement curves, joint force/slip response, pore-pressure and dynamic traces. "
            "3DEC samples from blocks, block contacts (joints), the global model, FISH symbols, and "
            "structural elements; results are listed/plotted (chart-history) and exported as time/step series."
        ),
        "primary_commands": [
            "block history",
            "block contact history",
            "model history",
            "fish history",
            "history interval",
            "history list",
            "history export",
            "history delete",
            "history purge",
            "history rename",
        ],
        "sampling_targets": [
            {
                "command": "block history <field>",
                "samples": "Deformable-block zone / gridpoint field at the nearest location — stress, displacement, velocity, strain-rate, pore-pressure, temperature, etc.",
                "field_names": "Same vocabulary as plot-items: see references/plot-items 'block contour' / 'bzone contour'.",
            },
            {
                "command": "block contact history <field>",
                "samples": "Joint (sub-contact) response — force-normal, force-shear, stress-normal, stress-shear, displacement-normal, displacement-shear[-x/-y/-z], area, *-sum aggregates.",
                "field_names": "force-normal, force-shear, force-normal-sum, force-shear-sum, stress-normal, stress-shear[-x/-y/-z], displacement-normal, displacement-shear[-maximum/-x/-y/-z], velocity-shear[-x/-y/-z], area, area-sum.",
            },
            {
                "command": "model history <type>",
                "samples": "Global scalars — mechanical (unbalanced force ratio), energy, timestep, damping, dynamic time, creep, fluid, thermal.",
                "field_names": "creep, damping, dynamic, energy, fluid, mechanical, thermal, timestep.",
            },
            {
                "command": "fish history <symbol>",
                "samples": "The value of a FISH symbol each interval — for custom/derived monitoring quantities.",
                "field_names": "Any FISH symbol name.",
            },
        ],
        "management_keywords": [
            {
                "keyword": "interval",
                "description": "Set the cycle/step interval at which all histories sample.",
                "syntax": "history interval <n>",
            },
            {
                "keyword": "list",
                "description": "List defined histories (ids, sampled quantity, location).",
                "syntax": "history list",
            },
            {
                "keyword": "export",
                "description": "Write history series to a table or text file (for validation/plotting).",
                "syntax": "history export <id...> [table '<name>' | file '<name>']",
            },
            {
                "keyword": "delete",
                "description": "Delete specific histories by id.",
                "syntax": "history delete <id...>",
            },
            {
                "keyword": "purge",
                "description": "Discard stored samples while keeping the history definitions.",
                "syntax": "history purge",
            },
            {"keyword": "rename", "description": "Rename a history.", "syntax": "history rename <id> '<name>'"},
        ],
        "notes": [
            "Sampling sub-forms 'block gridpoint history <field>' and 'structure history <type> ...' (beam/cable/liner/pile/shell/geogrid/node/link) also exist (bridge-probed); SELs are not standalone command-corpus pages.",
            "Field/quantity names for block sampling are the same set documented under plot-items contour — query references/plot-items instead of duplicating them here.",
            "Plot a history with 'plot item create chart-history'.",
        ],
    },
    {
        "name": "results-export",
        "full_name": "Results Files & Saved State",
        "description": (
            "Results files capture full model state for post-processing and restart. 3DEC's 'model results' "
            "selects which quantities to include via an attribute/FISH-symbol 'map' (not FLAC's per-entity "
            "inclusion keywords), then exports a .result file; 'model save' writes a full .sav restart state."
        ),
        "primary_commands": [
            "model results",
            "model save",
            "history results",
        ],
        "result_keywords": [
            {
                "keyword": "map",
                "description": "Select attributes / FISH symbols to include in the results file.",
                "syntax": "model results map <attribute|fish-symbol> ...",
            },
            {
                "keyword": "export",
                "description": "Write a results file.",
                "syntax": "model results export '<file>.result'",
            },
            {
                "keyword": "import",
                "description": "Read a previously exported results file back in.",
                "syntax": "model results import '<file>.result'",
            },
            {
                "keyword": "interval",
                "description": "Auto-export results every n cycles during a solve.",
                "syntax": "model results interval <n>",
            },
            {
                "keyword": "prefix",
                "description": "Set the filename prefix for interval/auto results files.",
                "syntax": "model results prefix '<name>'",
            },
            {
                "keyword": "list",
                "description": "List the current results-file configuration.",
                "syntax": "model results list",
            },
        ],
        "notes": [
            "'model save '<file>.sav'' stores the full restartable model state (all blocks, contacts, zones, histories).",
            "'history results active on' includes stored history series in the results/save stream.",
            "Use results files for large post-processing datasets; use .sav for restart and staged analysis.",
        ],
    },
]


def _valid_commands() -> set[str]:
    idx = json.loads(CMD_INDEX.read_text(encoding="utf-8"))
    out = set()
    for cat_name, cat in idx["categories"].items():
        for c in cat.get("commands", []):
            out.add(f"{cat_name} {c['name'].replace('-', ' ')}")
    return out


def _check(commands: list[str], valid: set[str]) -> None:
    for full in commands:
        toks = full.replace("-", " ").split()
        if not any(" ".join(toks[:n]) in valid for n in range(len(toks), 0, -1)):
            raise SystemExit(f"command not in 3DEC corpus: {full!r}")


def main() -> None:
    valid = _valid_commands()
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []
    for item in ITEMS:
        _check(item["primary_commands"], valid)
        doc = {"name": item["name"], "dimension": "3D", **{k: v for k, v in item.items() if k != "name"}}
        doc["official_documentation"] = DOC
        (CAT_DIR / f"{item['name']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")
        catalog.append({"name": item["name"], "file": f"{item['name']}.json", "full_name": item["full_name"]})
        print(f"  {item['name']:<20} cmds={len(item['primary_commands'])}")

    (CAT_DIR / "index.json").write_text(
        json.dumps(
            {
                "type": "histories_and_results",
                "description": (
                    "Monitoring, field-query, and results-export reference topics for 3DEC. History sampling "
                    "targets are 3DEC-specific (block / block contact / model / fish / structure history); "
                    "sampled field names share the plot-items contour vocabulary."
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
    top.setdefault("categories", {})["histories-and-results"] = {
        "name": "Histories & Results",
        "description": (
            "3DEC history sampling (block / block contact / model / fish / structure history), management "
            "(interval/list/export), and results files (model results map/export, model save). Sampled field "
            "names share the plot-items contour vocabulary."
        ),
        "directory": "histories-and-results",
        "index_file": "histories-and-results/index.json",
        "summary": f"{len(catalog)} topics: history-workflow (sampling targets + management), results-export",
        "usage": "block history <field> ; block contact history <field> ; history interval <n> ; model results map ... export '<f>.result'",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} topics)")


if __name__ == "__main__":
    main()
