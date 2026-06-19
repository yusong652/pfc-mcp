"""Generate MPoint's ``boundary-conditions`` and ``initial-conditions`` references.

Condition commands are engine-syntax-specific, so these are authored MPoint-
specific (not borrowed). MPoint applies boundary fixity with ``mpoint fix`` /
``mpoint free`` (material points) and ``mpoint node fix`` / ``mpoint node free``
(background-grid nodes); it seeds state with ``mpoint initialize <field>`` and
gravitational stresses with ``mpoint initialize-stresses``.

Every keyword set was probed live against MPoint 3D 9 via the bridge
(``mpoint fix ?``, ``mpoint node fix ?``, ``mpoint initialize ?``,
``mpoint initialize-stresses ?``) and baked in as constants. Every referenced
command is validated against the MPoint command corpus.

Output (MPoint-local):
    mpoint/references/index.json                          (top index, 2 entries)
    mpoint/references/boundary-conditions/{index,<item>}.json
    mpoint/references/initial-conditions/{index,<item>}.json

Usage:
    uv run python scripts/corpus/generate_mpoint_conditions.py
"""

import json
from pathlib import Path
from typing import Any

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
OUT = RES / "mpoint/references"
CMD_INDEX = RES / "mpoint/command_docs/index.json"

BOUNDARY_ITEMS: list[dict[str, Any]] = [
    {
        "name": "material-point-fixity",
        "full_name": "Material-Point Fixity / Prescribed Motion",
        "description": (
            "Fix or release degrees of freedom on material points with 'mpoint fix' / 'mpoint free'. "
            "Applying a velocity component fixes it (use 0 to pin a boundary); pore-pressure fixity drives "
            "the hydraulic boundary. 'multiplier' scales the fixed value over time."
        ),
        "primary_commands": ["mpoint fix", "mpoint free"],
        "condition_families": [
            {
                "family": "prescribed velocity",
                "keywords": ["velocity", "velocity-x", "velocity-y", "velocity-z"],
                "notes": ["'mpoint fix velocity-x 0 range ...' pins the x-motion of the selected material points."],
            },
            {
                "family": "pore pressure (fluid)",
                "keywords": ["pore-pressure"],
                "notes": ["Fix pore pressure for the hydro-mechanical / fluid-coupled solution."],
            },
            {
                "family": "modifiers",
                "keywords": ["multiplier", "range"],
                "notes": [
                    "'multiplier' applies a time-varying factor; 'range' scopes which material points are affected."
                ],
            },
        ],
    },
    {
        "name": "grid-node-fixity",
        "full_name": "Background-Grid Node Fixity",
        "description": (
            "Fix or release the background-grid nodes with 'mpoint node fix' / 'mpoint node free'. Grid-node "
            "fixity is the workhorse mechanical BC in MPM — material points exchange momentum with the grid, "
            "so pinning grid-node velocity sets the domain boundary. Fluid velocity has its own components."
        ),
        "primary_commands": ["mpoint node fix", "mpoint node free"],
        "condition_families": [
            {
                "family": "prescribed velocity",
                "keywords": ["velocity", "velocity-x", "velocity-y", "velocity-z"],
                "notes": ["Pin a wall/floor by fixing the relevant grid-node velocity component to 0 over a range."],
            },
            {
                "family": "prescribed fluid velocity",
                "keywords": ["fluid-velocity", "fluid-velocity-x", "fluid-velocity-y", "fluid-velocity-z"],
                "notes": ["Fluid-phase grid-node velocity for coupled fluid-flow analyses."],
            },
            {
                "family": "modifiers",
                "keywords": ["range"],
                "notes": ["'range' scopes which grid nodes are affected (e.g. a boundary plane)."],
            },
        ],
    },
]

INITIAL_ITEMS: list[dict[str, Any]] = [
    {
        "name": "field-initialization",
        "full_name": "Material-Point Field Initialization",
        "description": (
            "Seed material-point state directly with 'mpoint initialize <field> <value> [range ...]' before "
            "solving. Covers stress/strain, velocity/displacement, pore pressure and the fluid/biot "
            "poromechanical properties, plus density/porosity/volume. Compression is negative."
        ),
        "primary_commands": ["mpoint initialize"],
        "field_groups": [
            {
                "group": "stress & strain",
                "fields": ["stress", "stress-effective", "strain", "deformation"],
                "notes": [
                    "'stress' / 'stress-effective' set the carried tensor; pair with 'mpoint initialize-stresses' for gravitational fields."
                ],
            },
            {
                "group": "kinematics",
                "fields": ["velocity", "displacement", "position"],
                "notes": [
                    "Reset velocity/displacement between staged-loading phases so reported values measure the current stage."
                ],
            },
            {
                "group": "fluid / poromechanics",
                "fields": [
                    "pore-pressure",
                    "porosity",
                    "fluid-density",
                    "fluid-modulus",
                    "fluid-tension",
                    "fluid-flow",
                    "biot-coefficient",
                    "biot-modulus",
                    "mobility-coefficient",
                ],
                "notes": ["Initialize the poromechanical field for hydro-mechanical (Biot) coupling."],
            },
            {
                "group": "mass & identity",
                "fields": ["density", "volume", "applied-force", "fixity", "state", "model", "id", "index"],
                "notes": [
                    "'model' / 'state' seed the constitutive model and its state; see the 'constitutive-models' reference."
                ],
            },
        ],
    },
    {
        "name": "gravitational-stress",
        "full_name": "Gravitational (In-Situ) Stress Initialization",
        "description": (
            "Establish a gravitational in-situ stress field over the material points with "
            "'mpoint initialize-stresses'. Requires 'model gravity' to be set first. Builds a depth-varying "
            "field from the overburden and a lateral stress ratio (k0-style)."
        ),
        "primary_commands": ["model gravity", "mpoint initialize-stresses"],
        "field_groups": [
            {
                "group": "in-situ stress controls",
                "fields": ["overburden", "ratio", "direction-x", "total"],
                "notes": [
                    "'overburden' sets the surface stress; 'ratio' is the lateral/vertical stress ratio (k0).",
                    "'direction-x' orients the field; 'total' includes pore pressure in the total stress.",
                    "'model gravity 0 0 -9.81' must be defined before 'mpoint initialize-stresses'.",
                ],
            },
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
            raise SystemExit(f"command not in MPoint corpus: {full!r}")


def _write_category(
    directory: str,
    items: list[dict[str, Any]],
    cat_type: str,
    cat_desc: str,
    valid: set[str],
) -> list[dict[str, Any]]:
    cat_dir = OUT / directory
    cat_dir.mkdir(parents=True, exist_ok=True)
    catalog = []
    for item in items:
        _check(item["primary_commands"], valid)
        doc = {"name": item["name"], "dimension": "3D", **{k: v for k, v in item.items() if k != "name"}}
        (cat_dir / f"{item['name']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")
        catalog.append({"name": item["name"], "file": f"{item['name']}.json", "full_name": item["full_name"]})
        print(f"  {directory}/{item['name']}")
    (cat_dir / "index.json").write_text(
        json.dumps({"type": cat_type, "description": cat_desc, "items": catalog}, indent=2, ensure_ascii=False) + "\n",
        "utf-8",
    )
    return catalog


def main() -> None:
    valid = _valid_commands()

    bc = _write_category(
        "boundary-conditions",
        BOUNDARY_ITEMS,
        "boundary_conditions",
        "Boundary-condition reference topics for MPoint — material-point fixity ('mpoint fix'/'free') and "
        "background-grid node fixity ('mpoint node fix'/'free'). Grid-node velocity fixity is the primary "
        "mechanical BC in MPM.",
        valid,
    )
    ic = _write_category(
        "initial-conditions",
        INITIAL_ITEMS,
        "initial_conditions",
        "Initial-condition reference topics for MPoint — direct material-point field initialization "
        "('mpoint initialize') and gravitational in-situ stress ('mpoint initialize-stresses').",
        valid,
    )

    top_path = OUT / "index.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    cats = top.setdefault("categories", {})
    cats["boundary-conditions"] = {
        "name": "Boundary Conditions",
        "description": (
            "MPoint boundary conditions — material-point fixity ('mpoint fix'/'free': velocity, pore-pressure) "
            "and background-grid node fixity ('mpoint node fix'/'free': velocity, fluid-velocity)."
        ),
        "directory": "boundary-conditions",
        "index_file": "boundary-conditions/index.json",
        "summary": f"{len(bc)} MPoint boundary-condition topics (material-point + grid-node fixity)",
        "usage": "mpoint fix velocity-x 0 range ... ; mpoint node fix velocity 0 range ...",
    }
    cats["initial-conditions"] = {
        "name": "Initial Conditions",
        "description": (
            "MPoint initial conditions — material-point field initialization ('mpoint initialize': stress, "
            "velocity, pore-pressure, biot/fluid props) and gravitational in-situ stress "
            "('mpoint initialize-stresses')."
        ),
        "directory": "initial-conditions",
        "index_file": "initial-conditions/index.json",
        "summary": f"{len(ic)} MPoint initial-condition topics (field init + gravitational stress)",
        "usage": "mpoint initialize stress-zz -1e5 range ... ; model gravity 0 0 -9.81 ; mpoint initialize-stresses overburden ... ratio ...",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote boundary-conditions ({len(bc)}) + initial-conditions ({len(ic)})")


if __name__ == "__main__":
    main()
