"""Generate the MPoint (MPM) ``fish-intrinsics`` reference category.

FISH intrinsics are engine-entity-specific (FLAC's set is zone/gridpoint, 3DEC's
is block/joint), so they can't be borrowed from _common — MPoint needs its own,
built around material points and the background-grid nodes. Mirrors the 3DEC
fish-intrinsics shape (curated ``intrinsic_families`` with real example names +
usage notes), authored for MPoint.

Every example intrinsic is validated against the actual MPoint 9.0 FISH doc pages
(``fish_<name>.html``); an unknown name aborts the run, so nothing is fabricated.

Output (MPoint-local, not a _common borrow):
    mpoint/references/index.json                     (top index, category entry)
    mpoint/references/fish-intrinsics/index.json     (category index)
    mpoint/references/fish-intrinsics/<item>.json    (one per family group)

Usage:
    uv run python scripts/corpus/generate_mpoint_fish_intrinsics.py
"""

import json
from pathlib import Path
from typing import Any

DOCROOT = Path("C:/Program Files/Itasca/Itasca Software Subscription/exe64/doc/mpm")
OUT = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources/mpoint/references")
CAT_DIR = OUT / "fish-intrinsics"

ITEMS: list[dict[str, Any]] = [
    {
        "name": "material-point",
        "full_name": "Material Point FISH Intrinsics",
        "description": (
            "Pointer-based FISH access to material points — the core MPM carriers of mass, stress and "
            "history. Best for scripted stress/strain probes, convergence checks, and validation reports "
            "after command-driven setup. MPoint is 3D."
        ),
        "intrinsic_families": [
            {
                "family": "iteration & identity",
                "examples": [
                    "mpoint.list",
                    "mpoint.num",
                    "mpoint.find",
                    "mpoint.id",
                    "mpoint.maxid",
                    "mpoint.near",
                    "mpoint.containing",
                    "mpoint.inbox",
                    "mpoint.typeid",
                ],
                "notes": [
                    "Loop with 'loop foreach' over mpoint.list rather than assuming contiguous IDs.",
                    "mpoint.containing(pos) / mpoint.near(pos) locate a point by position.",
                ],
            },
            {
                "family": "geometry & motion",
                "examples": ["mpoint.pos", "mpoint.vol", "mpoint.density", "mpoint.disp", "mpoint.vel"],
                "notes": ["mpoint.pos is the current material-point position; it moves through the fixed grid."],
            },
            {
                "family": "state (stress / strain)",
                "examples": ["mpoint.stress", "mpoint.strain", "mpoint.deformation", "mpoint.pp"],
                "notes": ["mpoint.stress / mpoint.strain are the carried tensors; mpoint.pp is pore pressure."],
            },
            {
                "family": "constitutive model & properties",
                "examples": ["mpoint.prop", "mpoint.prop.index", "mpoint.extra"],
                "notes": [
                    "mpoint.prop reads/writes the assigned cmodel's properties; see the 'constitutive-models' reference.",
                ],
            },
            {
                "family": "fixity & loading",
                "examples": [
                    "mpoint.fix",
                    "mpoint.pp.fix",
                    "mpoint.force.app",
                    "mpoint.mass.gravity",
                    "mpoint.fluid.prop",
                ],
                "notes": ["mpoint.force.app is the applied force; mpoint.fix flags fixed velocity components."],
            },
            {
                "family": "groups",
                "examples": [
                    "mpoint.group",
                    "mpoint.group.list",
                    "mpoint.group.remove",
                    "mpoint.groupmap",
                    "mpoint.isgroup",
                ],
                "notes": ["Use named groups + slots for stable selection."],
            },
            {
                "family": "convergence (unbalance)",
                "examples": [
                    "mpoint.mech.ratio.avg",
                    "mpoint.mech.ratio.local",
                    "mpoint.mech.ratio.max",
                    "mpoint.mech.unbal.max",
                ],
                "notes": ["The mech.ratio.* intrinsics are the MPM equilibrium-convergence measures."],
            },
        ],
    },
    {
        "name": "background-node",
        "full_name": "Background-Grid Node FISH Intrinsics",
        "description": (
            "Pointer-based FISH access to the background-grid nodes — the fixed computational mesh that "
            "material points move through and exchange momentum with. Use for grid-side velocity/force/"
            "pore-pressure probes and convergence checks."
        ),
        "intrinsic_families": [
            {
                "family": "iteration & identity",
                "examples": [
                    "mpoint.node.list",
                    "mpoint.node.num",
                    "mpoint.node.find",
                    "mpoint.node.id",
                    "mpoint.node.maxid",
                    "mpoint.node.near",
                    "mpoint.node.inbox",
                    "mpoint.node.typeid",
                ],
                "notes": ["Loop over mpoint.node.list; nodes are the fixed grid points (not material points)."],
            },
            {
                "family": "geometry",
                "examples": ["mpoint.node.pos", "mpoint.node.spacing"],
                "notes": ["mpoint.node.spacing is the background-grid cell spacing."],
            },
            {
                "family": "state & motion",
                "examples": ["mpoint.node.disp", "mpoint.node.vel", "mpoint.node.pp", "mpoint.node.stress"],
                "notes": ["Grid-node kinematics are interpolated to/from the material points each step."],
            },
            {
                "family": "convergence",
                "examples": ["mpoint.node.force.unbal"],
                "notes": ["mpoint.node.force.unbal is the per-node unbalanced force used for convergence."],
            },
            {
                "family": "groups",
                "examples": [
                    "mpoint.node.group",
                    "mpoint.node.group.list",
                    "mpoint.node.group.remove",
                    "mpoint.node.groupmap",
                    "mpoint.node.isgroup",
                ],
                "notes": [],
            },
        ],
    },
]


def _valid_names() -> set[str]:
    """All real MPoint FISH intrinsic names from the doc pages (fish_<name>.html)."""
    names: set[str] = set()
    for p in DOCROOT.rglob("fish_*.html"):
        names.add(p.name[len("fish_") : -len(".html")])
    return names


def main() -> None:
    valid = _valid_names()
    if not valid:
        raise SystemExit("No FISH doc pages found — check DOCROOT.")

    CAT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []
    for item in ITEMS:
        bad = [ex for fam in item["intrinsic_families"] for ex in fam["examples"] if ex not in valid]
        if bad:
            raise SystemExit(f"{item['name']}: example intrinsics not found in MPoint 9.0 docs: {bad}")
        doc = {
            "name": item["name"],
            "dimension": "3D",
            **{k: item[k] for k in ("full_name", "description")},
            "intrinsic_families": item["intrinsic_families"],
        }
        (CAT_DIR / f"{item['name']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")
        n = sum(len(f["examples"]) for f in item["intrinsic_families"])
        catalog.append(
            {"name": item["name"], "file": f"{item['name']}.json", "full_name": item["full_name"], "intrinsic_count": n}
        )
        print(f"  {item['name']:<18} families={len(item['intrinsic_families'])} examples={n}")

    cat_index = {
        "type": "fish_intrinsics",
        "description": (
            "MPoint (MPM) FISH intrinsic families for scripted model inspection, validation, and data "
            "extraction — material points and the background-grid nodes."
        ),
        "items": catalog,
        "official_sources": [
            "https://docs.itascacg.com/itasca900/mpm/mpm/doc/source/manual/fish/fish.html",
        ],
    }
    (CAT_DIR / "index.json").write_text(json.dumps(cat_index, indent=2, ensure_ascii=False) + "\n", "utf-8")

    top_path = OUT / "index.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top.setdefault("categories", {})["fish-intrinsics"] = {
        "name": "FISH Intrinsics",
        "description": (
            "MPoint FISH intrinsic families for scripted inspection — material points and background-grid "
            "nodes (iteration, geometry, stress/strain/state, properties, groups, convergence)."
        ),
        "directory": "fish-intrinsics",
        "index_file": "fish-intrinsics/index.json",
        "summary": f"{len(catalog)} MPoint FISH intrinsic family groups (material-point, background-node)",
        "usage": "Use in FISH: loop foreach over mpoint.list / mpoint.node.list; read with mpoint.<intrinsic>(ptr)",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} family groups); validated against {len(valid)} real FISH intrinsics")


if __name__ == "__main__":
    main()
