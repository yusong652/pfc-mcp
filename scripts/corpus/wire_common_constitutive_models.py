"""Wire FLAC + 3DEC zone constitutive-model references to a shared _common pool.

Zone (continuum / deformable-block) constitutive models are a 9.0 kernel shared
by FLAC3D and 3DEC; their per-model property docs are byte-identical. The item
JSONs have been moved to ``_common/references/constitutive-models/`` (one copy);
this script wires each engine's category index to point there instead of holding
its own copy — the same ``_common`` borrow pattern command docs already use.

- FLAC keeps all 38 models; each model's ``file`` is repointed into ``_common/``.
- 3DEC registers the 26 models it actually exposes (``block zone cmodel list``),
  filtered from FLAC's catalog, also pointing into ``_common/``. PFC has no zones
  and does not register this category.

ReferenceLoader resolves a RESOURCES-root-relative ``file`` (``_common/...``) via
resolve(); a bare filename still falls back to the engine-local directory.

Usage:
    uv run python scripts/corpus/wire_common_constitutive_models.py
"""

import json
from pathlib import Path

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
COMMON_REL = "_common/references/constitutive-models"
FLAC_CAT = RES / "flac/references/constitutive-models/index.json"
TDEC_REFS = RES / "3dec/references"
TDEC_CAT = TDEC_REFS / "constitutive-models/index.json"

# The 26 zone constitutive models 3DEC exposes (block zone cmodel list, 9.0).
# Truncated bridge keywords resolved against FLAC's catalog filenames.
THREEDEC_ZONE = [
    "anisotropic",
    "burgers",
    "burgers-mohr",
    "columnar-basalt",
    "concrete",
    "double-yield",
    "drucker-prager",
    "elastic",
    "hoek-brown",
    "imass",
    "maxwell",
    "modified-cam-clay",
    "mohr-coulomb",
    "mohr-coulomb-tension",
    "null",
    "orthotropic",
    "power",
    "power-mohr",
    "softening-ubiquitous",
    "strain-softening",
    "ubiquitous-anisotropic",
    "ubiquitous-joint",
    "von-mises",
    "wipp",
    "wipp-drucker",
    "wipp-salt",
]


def _common_file(filename: str) -> str:
    # filename may already be a bare name ("mohr-coulomb.json") or a pointer.
    return f"{COMMON_REL}/{Path(filename).name}"


def main() -> None:
    flac = json.loads(FLAC_CAT.read_text(encoding="utf-8"))

    # 1. Repoint FLAC's 38 models into _common (idempotent).
    for m in flac["models"]:
        m["file"] = _common_file(m["file"])
    FLAC_CAT.write_text(json.dumps(flac, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 2. Build 3DEC's category index: FLAC's catalog filtered to the 26 it exposes.
    by_name = {m["name"]: m for m in flac["models"]}
    missing = [k for k in THREEDEC_ZONE if k not in by_name]
    if missing:
        raise SystemExit(f"3DEC zone models not found in FLAC catalog: {missing}")
    tdec_models = [dict(by_name[k]) for k in THREEDEC_ZONE]  # already point into _common

    tdec_cat = {
        "type": "constitutive_model_properties",
        "description": (
            "3DEC zone (deformable-block) constitutive model properties — the property vocabulary "
            "for 'block zone cmodel assign' + 'block zone property'. Shared 9.0 kernel with FLAC3D "
            "(docs live in _common); 3DEC exposes the 26 models listed here."
        ),
        "usage_contexts": [
            "block zone cmodel assign <name> [range ...]",
            "block zone property <prop> <value> [range cmodel-name <name>]",
            "Python: itasca.block.zone.Zone.set_prop('<prop>', value)",
        ],
        "property_metadata_fields": {
            "keyword": "Property name used in 'block zone property' commands",
            "symbol": "Mathematical symbol used in the model documentation",
            "description": "Description including physical meaning and units",
            "type": "Coarse data type (FLT=float, BOOL=boolean) — heuristic",
        },
        "models": tdec_models,
    }
    TDEC_CAT.parent.mkdir(parents=True, exist_ok=True)
    TDEC_CAT.write_text(json.dumps(tdec_cat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 3. Register the category in 3DEC's top references index (keep joint-models).
    top = json.loads((TDEC_REFS / "index.json").read_text(encoding="utf-8"))
    top.setdefault("categories", {})["constitutive-models"] = {
        "name": "Constitutive Models (Zone)",
        "description": (
            "3DEC zone (deformable-block) constitutive material model properties — mohr-coulomb, "
            "drucker-prager, hoek-brown, ubiquitous-joint, creep models, etc. Property vocabulary for "
            "'block zone cmodel assign' + 'block zone property'. Shared 9.0 kernel with FLAC3D."
        ),
        "directory": "constitutive-models",
        "index_file": "constitutive-models/index.json",
        "summary": f"{len(tdec_models)} 3DEC zone material models (subset of FLAC3D's set; docs shared via _common)",
        "usage": "block zone cmodel assign <name> ; block zone property <prop> <value> [range cmodel-name <name>]",
    }
    (TDEC_REFS / "index.json").write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"FLAC models repointed into _common: {len(flac['models'])}")
    print(f"3DEC constitutive-models registered: {len(tdec_models)} (filtered subset)")
    print(f"_common item pool: {len(list((RES / COMMON_REL).glob('*.json')))} files")


if __name__ == "__main__":
    main()
