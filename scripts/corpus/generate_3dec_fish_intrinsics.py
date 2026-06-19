"""Generate the 3DEC ``fish-intrinsics`` reference category.

FISH intrinsics are engine-entity-specific (FLAC's set is built around zone /
gridpoint / structure-interface), so they cannot be borrowed from _common — 3DEC
needs its own, built around blocks, joints (sub-contacts), deformable-block
zones/gridpoints, and the fracture-flow network. This mirrors FLAC's
fish-intrinsics shape (curated ``intrinsic_families`` with representative example
names + usage notes), authored for 3DEC.

Every example intrinsic is validated against the actual 9.0 FISH doc pages
(``fish_<name>.html``) so nothing is fabricated; an unknown name aborts the run.

Output (3DEC-local, like joint-models — not a _common borrow):
    3dec/references/index.json                      (top index, category entry)
    3dec/references/fish-intrinsics/index.json      (category index)
    3dec/references/fish-intrinsics/<item>.json     (one per family group)

Usage:
    uv run python scripts/corpus/generate_3dec_fish_intrinsics.py
"""

import json
from pathlib import Path
from typing import Any

DOCROOT = Path("C:/Program Files/Itasca/ItascaSoftware900/exe64/doc/3dec/block/doc/manual")
BLOCK_FISH = DOCROOT / "block_manual/block_fish"
FLOW_FISH = DOCROOT / "flow_manual/flow_fish"
OUT = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources/3dec/references")
CAT_DIR = OUT / "fish-intrinsics"

# Curated items. Each family's ``examples`` are real intrinsic names (validated
# below against the doc pages); descriptions/notes are authored for 3DEC.
ITEMS: list[dict[str, Any]] = [
    {
        "name": "block-and-joints",
        "full_name": "Block and Joint (Contact/Sub-contact) FISH Intrinsics",
        "description": (
            "Pointer-based FISH access to blocks and the joints between them (contacts and their "
            "sub-contacts). Best for scripted checks of joint forces/displacements/state and compact "
            "validation reports after command-driven setup. 3DEC is 3D."
        ),
        "intrinsic_families": [
            {
                "family": "block iteration & identity",
                "examples": ["block.list", "block.num", "block.find", "block.id", "block.index", "block.near"],
                "notes": [
                    "Loop with 'loop foreach' over block.list rather than assuming contiguous IDs.",
                    "Prefer named groups and ranges for stable selection.",
                ],
            },
            {
                "family": "block geometry & motion",
                "examples": ["block.pos", "block.vol", "block.area", "block.mass", "block.vel", "block.rvel"],
                "notes": ["block.pos is the centroid; block.rvel is angular velocity."],
            },
            {
                "family": "contact topology",
                "examples": [
                    "block.contact.list",
                    "block.contact.num",
                    "block.contact.b1",
                    "block.contact.b2",
                    "block.contact.normal",
                    "block.contact.subcontactlist",
                    "block.contact.type",
                ],
                "notes": ["A contact spans two blocks (b1/b2) and owns one or more sub-contacts."],
            },
            {
                "family": "sub-contact mechanics (joint behavior)",
                "examples": [
                    "block.subcontact.list",
                    "block.subcontact.model",
                    "block.subcontact.prop",
                    "block.subcontact.force.norm",
                    "block.subcontact.force.shear",
                    "block.subcontact.disp.norm",
                    "block.subcontact.disp.shear",
                    "block.subcontact.stress.norm",
                    "block.subcontact.stress.shear",
                    "block.subcontact.state",
                    "block.subcontact.area",
                ],
                "notes": [
                    "Joint constitutive behavior lives on sub-contacts; 'block.subcontact.model' is the jmodel name.",
                    "See the 'joint-models' reference for each model's property keywords.",
                ],
            },
        ],
    },
    {
        "name": "block-zone-gridpoint",
        "full_name": "Deformable-Block Zone and Gridpoint FISH Intrinsics",
        "description": (
            "Pointer-based FISH access to the continuum inside deformable blocks — zones (finite-volume "
            "elements) and their gridpoints. Use for scripted stress/strain probes and convergence checks."
        ),
        "intrinsic_families": [
            {
                "family": "zone iteration & topology",
                "examples": [
                    "block.zone.list",
                    "block.zone.num",
                    "block.zone.find",
                    "block.zone.containing",
                    "block.zone.gp",
                    "block.zone.hostblock",
                ],
                "notes": ["block.zone.containing(pos) finds the zone enclosing a point."],
            },
            {
                "family": "zone state",
                "examples": [
                    "block.zone.stress",
                    "block.zone.stress.prin",
                    "block.zone.strain.inc",
                    "block.zone.model",
                    "block.zone.prop",
                    "block.zone.pp",
                    "block.zone.vol",
                ],
                "notes": [
                    "'block.zone.model' / 'block.zone.prop' read the assigned zone constitutive model and its properties.",
                    "See the 'constitutive-models' reference for property keywords.",
                ],
            },
            {
                "family": "gridpoint",
                "examples": [
                    "block.gridpoint.list",
                    "block.gridpoint.num",
                    "block.gridpoint.pos",
                    "block.gridpoint.disp",
                    "block.gridpoint.vel",
                    "block.gridpoint.force.unbal",
                    "block.gridpoint.bc",
                ],
                "notes": ["block.gridpoint.force.unbal is the per-gridpoint unbalanced force used for convergence."],
            },
        ],
    },
    {
        "name": "fluid-flow",
        "full_name": "Fracture-Flow (Flow Knot / Flow Plane) FISH Intrinsics",
        "description": (
            "Pointer-based FISH access to 3DEC's fracture-flow network used in hydro-mechanical coupling — "
            "flow knots (nodal points) and flow planes (planar fracture-flow elements)."
        ),
        "intrinsic_families": [
            {
                "family": "flow knots",
                "examples": [
                    "flowknot.list",
                    "flowknot.find",
                    "flowknot.pos",
                    "flowknot.pp",
                    "flowknot.head",
                    "flowknot.flux.fluid.app",
                    "flowknot.vol",
                ],
                "notes": ["flowknot.pp / flowknot.head are pore pressure and hydraulic head at the knot."],
            },
            {
                "family": "flow planes",
                "examples": [
                    "flowplane.list",
                    "flowplane.find",
                    "flowplane.pos",
                    "flowplane.area",
                    "flowplane.contact",
                    "flowplane.prop",
                    "flowplane.vertexlist",
                    "flowplane.zonelist",
                ],
                "notes": ["A flow plane couples to the mechanical joint via 'flowplane.contact'."],
            },
        ],
    },
]


def _valid_names() -> set[str]:
    """All real 3DEC FISH intrinsic names from the doc pages (fish_<name>.html)."""
    names: set[str] = set()
    for root in (BLOCK_FISH, FLOW_FISH):
        for p in root.rglob("fish_*.html"):
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
            raise SystemExit(f"{item['name']}: example intrinsics not found in 9.0 docs: {bad}")
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
        print(f"  {item['name']:<22} families={len(item['intrinsic_families'])} examples={n}")

    cat_index = {
        "type": "fish_intrinsics",
        "description": (
            "3DEC FISH intrinsic families for scripted model inspection, validation, and data extraction — "
            "blocks & joints (sub-contacts), deformable-block zones/gridpoints, and the fracture-flow network."
        ),
        "items": catalog,
        "official_sources": [
            "https://docs.itascacg.com/itasca900/3dec/block/doc/manual/block_manual/block_fish/block_fish.html",
            "https://docs.itascacg.com/itasca900/3dec/block/doc/manual/flow_manual/flow_fish/flow_fish.html",
        ],
    }
    (CAT_DIR / "index.json").write_text(json.dumps(cat_index, indent=2, ensure_ascii=False) + "\n", "utf-8")

    top_path = OUT / "index.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top.setdefault("categories", {})["fish-intrinsics"] = {
        "name": "FISH Intrinsics",
        "description": (
            "3DEC FISH intrinsic families for scripted inspection — blocks & joints (sub-contacts), "
            "deformable-block zones/gridpoints, fracture-flow network."
        ),
        "directory": "fish-intrinsics",
        "index_file": "fish-intrinsics/index.json",
        "summary": f"{len(catalog)} 3DEC FISH intrinsic family groups (block/joint, zone/gridpoint, fluid-flow)",
        "usage": "Use in FISH: loop foreach over <entity>.list; read with <entity>.<intrinsic>(ptr)",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} family groups); validated against {len(valid)} real FISH intrinsics")


if __name__ == "__main__":
    main()
