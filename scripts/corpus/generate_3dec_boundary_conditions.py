"""Generate the 3DEC ``boundary-conditions`` reference category.

Boundary-condition topics are command-syntax-specific. FLAC applies them with
``zone face apply`` / ``zone gridpoint fix``; 3DEC uses the ``block ...`` family:
``block face apply`` (deformable-block faces), ``block gridpoint apply`` /
``block fix`` (gridpoints & rigid blocks), ``block contact apply`` (joint pore
pressure). Authored for 3DEC, mirroring FLAC's shape (topics with
condition_families of keywords + notes).

Keyword families are taken from the 3DEC command docs (block face apply / block
gridpoint apply / block apply / block fix); referenced commands are validated
against the 3DEC command corpus, so the syntax is real.

Usage:
    uv run python scripts/corpus/generate_3dec_boundary_conditions.py
"""

import json
from pathlib import Path
from typing import Any

RES = Path("C:/Dev/Han/itasca-mcp/src/itasca_mcp/knowledge/resources")
OUT = RES / "3dec/references"
CAT_DIR = OUT / "boundary-conditions"
CMD_INDEX = RES / "3dec/command_docs/index.json"
DOC = "https://docs.itascacg.com/itasca900/3dec/docproject/source/modeling/problemsolving/boundaryconditions.html"

ITEMS: list[dict[str, Any]] = [
    {
        "name": "mechanical-face",
        "full_name": "Mechanical Face Boundary Conditions",
        "description": (
            "Mechanical conditions applied to deformable-block boundary faces with 'block face apply' — "
            "stress (traction), point loads, and prescribed normal velocity."
        ),
        "primary_commands": ["block face apply", "block face apply-remove"],
        "condition_families": [
            {
                "family": "stress (traction)",
                "keywords": ["stress-xx", "stress-yy", "stress-zz", "stress-xy", "stress-xz", "stress-yz"],
                "notes": ["Applied as a face traction over the selected faces; compression is negative."],
            },
            {
                "family": "point load",
                "keywords": ["point-load", "point-load-x", "point-load-y", "point-load-z"],
                "notes": ["A concentrated load distributed to the face."],
            },
            {
                "family": "prescribed motion",
                "keywords": ["velocity-normal"],
                "notes": ["Prescribes the face-normal velocity component."],
            },
        ],
    },
    {
        "name": "gridpoint-and-block-fixity",
        "full_name": "Gridpoint and Rigid-Block Fixity / Prescribed Motion",
        "description": (
            "Constrain or drive motion at gridpoints (deformable blocks) with 'block gridpoint apply', and at "
            "rigid blocks with 'block fix' / 'block apply'. Velocity/force here are the workhorse mechanical BCs."
        ),
        "primary_commands": ["block gridpoint apply", "block gridpoint apply-remove", "block fix", "block apply"],
        "condition_families": [
            {
                "family": "gridpoint velocity (prescribed)",
                "keywords": ["velocity", "velocity-x", "velocity-y", "velocity-z", "velocity-normal"],
                "notes": ["Applying a velocity fixes that component; use 0 to pin a boundary."],
            },
            {
                "family": "gridpoint force / reaction",
                "keywords": [
                    "force",
                    "force-x",
                    "force-y",
                    "force-z",
                    "reaction",
                    "reaction-x",
                    "reaction-y",
                    "reaction-z",
                ],
                "notes": ["'reaction' reports/holds the reaction force at constrained gridpoints."],
            },
            {
                "family": "rigid-block fixity",
                "keywords": [
                    "velocity",
                    "velocity-x",
                    "velocity-y",
                    "velocity-z",
                    "rotation",
                    "rotation-x",
                    "rotation-y",
                    "rotation-z",
                ],
                "notes": [
                    "'block fix velocity|rotation ...' fixes rigid-block translation/rotation;",
                    "'block apply velocity ...' drives rigid-block translation.",
                ],
            },
        ],
    },
    {
        "name": "fluid-flow",
        "full_name": "Fluid-Flow Boundary Conditions",
        "description": (
            "Hydraulic boundary conditions for the fracture-flow / pore-pressure model — fluid flux and "
            "sources, plus pore pressure applied to joints via 'block contact apply'."
        ),
        "primary_commands": ["block face apply", "block gridpoint apply", "block contact apply"],
        "condition_families": [
            {
                "family": "flux & sources",
                "keywords": ["flux", "source"],
                "notes": [
                    "'block face apply flux ...' for boundary inflow; 'block gridpoint apply source ...' for point sources."
                ],
            },
            {
                "family": "pore pressure (joints)",
                "keywords": ["pore-pressure"],
                "notes": [
                    "'block contact apply pore-pressure <f>' sets joint pore pressure for hydro-mechanical coupling."
                ],
            },
        ],
    },
    {
        "name": "thermal-and-dynamic",
        "full_name": "Thermal and Dynamic (Absorbing) Boundary Conditions",
        "description": (
            "Thermal conditions (temperature, convection, heat flux) and dynamic absorbing/quiet boundaries "
            "that prevent reflection of outgoing waves in dynamic analyses."
        ),
        "primary_commands": ["block face apply", "block gridpoint apply"],
        "condition_families": [
            {
                "family": "thermal",
                "keywords": ["temperature", "convection", "flux"],
                "notes": [
                    "'block gridpoint apply temperature ...' fixes temperature; 'block face apply convection ...' sets film coefficient."
                ],
            },
            {
                "family": "dynamic absorbing (quiet / viscous)",
                "keywords": [
                    "quiet",
                    "quiet-x",
                    "quiet-y",
                    "quiet-z",
                    "viscous",
                    "viscous-x",
                    "viscous-y",
                    "viscous-z",
                ],
                "notes": ["Viscous (quiet) gridpoint boundaries absorb outgoing waves in dynamic runs."],
            },
        ],
    },
    {
        "name": "apply-modifiers",
        "full_name": "Apply Modifiers (Spatial / Functional Variation, Removal)",
        "description": (
            "Modifier keywords shared across the 'block ... apply' family to vary a condition in space or time "
            "and to remove it: spatial gradients, FISH/table functions, history attachment, and apply-remove."
        ),
        "primary_commands": [
            "block face apply",
            "block gridpoint apply",
            "block face apply-remove",
            "block gridpoint apply-remove",
        ],
        "condition_families": [
            {
                "family": "spatial variation",
                "keywords": ["gradient-z", "origin"],
                "notes": ["'gradient-z' varies the value with depth about 'origin'."],
            },
            {
                "family": "functional variation",
                "keywords": ["fish", "table"],
                "notes": ["'fish <fn>' or 'table <name>' make the applied value a function of time/state."],
            },
            {
                "family": "removal",
                "keywords": ["apply-remove"],
                "notes": ["'block face apply-remove ...' / 'block gridpoint apply-remove ...' clears conditions."],
            },
        ],
    },
]


def _valid_block_commands() -> set[str]:
    idx = json.loads(CMD_INDEX.read_text(encoding="utf-8"))
    out = set()
    for cat_name, cat in idx["categories"].items():
        for c in cat.get("commands", []):
            out.add(f"{cat_name} {c['name'].replace('-', ' ')}")
    return out


def main() -> None:
    valid = _valid_block_commands()
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []
    for item in ITEMS:
        for cmd in item["primary_commands"]:
            # Validate against the corpus' dash-joined names: normalise hyphens
            # (e.g. 'block face apply-remove' -> tokens 'block face apply remove').
            toks = cmd.replace("-", " ").split()
            if not any(" ".join(toks[:n]) in valid for n in range(len(toks), 0, -1)):
                raise SystemExit(f"command not in 3DEC corpus: {cmd!r}")
        doc = {
            "name": item["name"],
            "dimension": "3D",
            "full_name": item["full_name"],
            "description": item["description"],
            "primary_commands": item["primary_commands"],
            "condition_families": item["condition_families"],
            "official_documentation": DOC,
        }
        (CAT_DIR / f"{item['name']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")
        catalog.append({"name": item["name"], "file": f"{item['name']}.json", "full_name": item["full_name"]})
        print(f"  {item['name']:<28} families={len(item['condition_families'])}")

    (CAT_DIR / "index.json").write_text(
        json.dumps(
            {
                "type": "boundary_conditions",
                "description": (
                    "Boundary-condition reference topics for 3DEC — mechanical face tractions, gridpoint & "
                    "rigid-block fixity, fluid flow, thermal/dynamic, and shared apply modifiers. Commands use "
                    "the 'block ...' family (block face apply / block gridpoint apply / block fix / block apply)."
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
    top.setdefault("categories", {})["boundary-conditions"] = {
        "name": "Boundary Conditions",
        "description": (
            "3DEC boundary conditions — mechanical face tractions, gridpoint & rigid-block fixity, fluid-flow, "
            "thermal/dynamic, apply modifiers. Uses 'block face apply' / 'block gridpoint apply' / 'block fix'."
        ),
        "directory": "boundary-conditions",
        "index_file": "boundary-conditions/index.json",
        "summary": f"{len(catalog)} 3DEC boundary-condition topics (block face/gridpoint apply, block fix)",
        "usage": "block face apply <cond> ... range ... ; block gridpoint apply <cond> ... ; block fix <velocity|rotation> ...",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} topics)")


if __name__ == "__main__":
    main()
