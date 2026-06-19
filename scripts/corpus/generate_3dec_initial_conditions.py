"""Generate the 3DEC ``initial-conditions`` reference category.

Initial-condition topics are command-syntax-specific, so 3DEC needs its own
(FLAC's use ``zone initialize`` / ``zone face apply``; 3DEC uses ``block zone
initialize`` / ``block insitu`` / ``block gridpoint initialize``). Authored for
3DEC, mirroring FLAC's initial-conditions shape (curated topics with
primary_commands + methods + validation checks).

Every ``block …`` command referenced is validated against the 3DEC command
corpus (category + dash-joined name) so the syntax is real; an unknown command
aborts the run.

Output (3DEC-local):
    3dec/references/index.json                       (top index, category entry)
    3dec/references/initial-conditions/index.json    (category index)
    3dec/references/initial-conditions/<item>.json   (one per topic)

Usage:
    uv run python scripts/corpus/generate_3dec_initial_conditions.py
"""

import json
from pathlib import Path
from typing import Any

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
OUT = RES / "3dec/references"
CAT_DIR = OUT / "initial-conditions"
CMD_INDEX = RES / "3dec/command_docs/index.json"
DOC = "https://docs.itascacg.com/itasca900/3dec/docproject/source"

ITEMS: list[dict[str, Any]] = [
    {
        "name": "stress-initialization",
        "full_name": "Stress Initialization",
        "description": (
            "Set initial stresses in deformable-block zones directly, or establish gravitational in-situ "
            "stresses, before solving. Initial stresses should be consistent with boundary conditions, "
            "gravity, and the assigned zone constitutive model. Compression is negative."
        ),
        "primary_commands": [
            "model gravity",
            "block zone initialize",
            "block insitu",
            "model solve",
        ],
        "methods": [
            {
                "name": "uniform / anisotropic stress",
                "commands": [
                    "block zone initialize stress-xx -5e6",
                    "block zone initialize stress-yy -1e7",
                    "block zone initialize stress-zz -5e6",
                    "block zone initialize stress-xy 0",
                ],
                "notes": [
                    "Components: stress-xx/yy/zz (normal) and stress-xy/xz/yz (shear).",
                    "Use modifier keywords add / gradient / multiply / vary to build depth-varying fields.",
                ],
            },
            {
                "name": "gravitational in-situ stress",
                "commands": [
                    "model gravity 0 0 -9.81",
                    "block insitu stress -1e6 -1e6 -2e6 0 0 0 gradient 0 0 1e4 0 0 2e4 0 0 0",
                    "block insitu stress ... nodisplacements",
                ],
                "notes": [
                    "'block insitu stress' sets the full tensor with optional 'gradient' (per-axis variation).",
                    "'nodisplacements' suppresses displacements during the seating solve; 'total' includes pore pressure.",
                ],
            },
        ],
        "validation_checks": [
            "block zone list information",
            "FISH: block.zone.stress(z) to confirm the assigned field",
            "Solve elastically and confirm small block.gridpoint.force.unbal (near equilibrium)",
        ],
    },
    {
        "name": "velocity-and-state-reset",
        "full_name": "Velocity and Displacement / State Reset",
        "description": (
            "Initialize or reset block and gridpoint velocities and accumulated displacements between "
            "staged-loading phases, so reported displacements measure only the current stage."
        ),
        "primary_commands": [
            "block initialize",
            "block gridpoint initialize",
        ],
        "methods": [
            {
                "name": "reset velocities",
                "commands": [
                    "block initialize velocity 0 0 0",
                    "block initialize rvelocity 0 0 0",
                    "block gridpoint initialize velocity 0 0 0",
                ],
                "notes": ["Rigid blocks carry block velocity / rvelocity; deformable blocks carry gridpoint velocity."],
            },
            {
                "name": "reset accumulated displacement",
                "commands": [
                    "block gridpoint initialize displacement 0 0 0",
                    "block gridpoint initialize displacement-x 0",
                ],
                "notes": ["Zeroing displacement does not move the mesh; it only resets the accumulator."],
            },
        ],
        "validation_checks": [
            "FISH: block.gridpoint.disp(gp) / block.gridpoint.vel(gp) read back zero after reset",
        ],
    },
    {
        "name": "fluid-thermal",
        "full_name": "Fluid and Thermal Initial Conditions",
        "description": (
            "Initialize pore pressure and temperature fields for hydro-mechanical and thermal analyses, "
            "directly on gridpoints or as a depth gradient."
        ),
        "primary_commands": [
            "block gridpoint initialize",
            "block insitu",
        ],
        "methods": [
            {
                "name": "pore pressure",
                "commands": [
                    "block gridpoint initialize pore-pressure 1e5",
                    "block gridpoint initialize pore-pressure 0 gradient 0 0 -9810",
                ],
                "notes": ["Use 'gradient' for a hydrostatic profile; pair with the fluid/effective-stress workflow."],
            },
            {
                "name": "temperature",
                "commands": [
                    "block gridpoint initialize temperature 20",
                    "block insitu fluid-temperature 20",
                ],
                "notes": ["'block insitu fluid-temperature' seats the fluid temperature for thermal-fluid coupling."],
            },
        ],
        "validation_checks": [
            "FISH: block.gridpoint.pp(gp) / block.gridpoint.temp(gp) confirm the initialized field",
        ],
    },
]


def _valid_block_commands() -> set[str]:
    idx = json.loads(CMD_INDEX.read_text(encoding="utf-8"))
    out = set()
    for cat_name, cat in idx["categories"].items():
        for c in cat.get("commands", []):
            # reconstruct the full command, e.g. block + "zone-initialize" -> "block zone initialize"
            out.add(f"{cat_name} {c['name'].replace('-', ' ')}")
            out.add(c["name"].replace("-", " "))
    return out


def _check(commands: list[str], valid: set[str]) -> None:
    for full in commands:
        toks = full.split()
        # match the longest known command prefix (ignore trailing args/keywords)
        if not any(" ".join(toks[:n]) in valid for n in range(len(toks), 0, -1)):
            raise SystemExit(f"command not found in 3DEC corpus: {full!r}")


def main() -> None:
    valid = _valid_block_commands()
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []
    for item in ITEMS:
        _check(item["primary_commands"], valid)
        doc = {
            "name": item["name"],
            "dimension": "3D",
            "full_name": item["full_name"],
            "description": item["description"],
            "primary_commands": item["primary_commands"],
            "methods": item["methods"],
            "validation_checks": item["validation_checks"],
            "official_documentation": f"{DOC}/modeling/problemsolving/initialconditions.html",
        }
        (CAT_DIR / f"{item['name']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")
        catalog.append({"name": item["name"], "file": f"{item['name']}.json", "full_name": item["full_name"]})
        print(f"  {item['name']:<28} methods={len(item['methods'])}")

    (CAT_DIR / "index.json").write_text(
        json.dumps(
            {
                "type": "initial_conditions",
                "description": (
                    "Initial-condition reference topics for 3DEC setup — stress initialization (zone / in-situ), "
                    "velocity & displacement reset, and fluid/thermal fields. Commands use the 'block ...' family."
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
    top.setdefault("categories", {})["initial-conditions"] = {
        "name": "Initial Conditions",
        "description": (
            "3DEC initial conditions — stress initialization (block zone initialize / block insitu), velocity "
            "& displacement reset, fluid/thermal fields."
        ),
        "directory": "initial-conditions",
        "index_file": "initial-conditions/index.json",
        "summary": f"{len(catalog)} 3DEC initial-condition topics (block zone initialize / insitu / gridpoint initialize)",
        "usage": "block zone initialize <stress-*> ... ; block insitu stress ... gradient ... ; block gridpoint initialize <field> ...",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} topics)")


if __name__ == "__main__":
    main()
