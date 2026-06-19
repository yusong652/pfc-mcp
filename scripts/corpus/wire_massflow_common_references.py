"""Wire MassFlow's shared references (constitutive-models + range-elements) to _common.

MassFlow runs on the FLAC3D zone engine for coupled mechanical analysis, so it
assigns the same 9.0-kernel zone constitutive models (``zone cmodel assign``)
and uses the same ``range ...`` filters as FLAC3D / 3DEC / MPoint. Both are
borrowed from the shared ``_common`` pool created in the 3DEC references PR — no
duplication.

- range-elements: all 22 kernel filters; MassFlow has no engine-local range
  items, so it clones FLAC's (already _common-pointing) index verbatim.
- constitutive-models: MassFlow's ``zone cmodel list`` exposes 43 models, a
  superset of FLAC's 38 (identical set to MPoint). The 38 with a _common doc are
  registered pointing into _common; the 5 without a shared doc (cavehoek,
  clay-and-sand, curved-mohr-coulomb, jones-wilkins-lee, munson-dawson) are
  disclosed in a ``note`` rather than fabricated.

Model/range membership was probed live against MassFlow 3D 9 via the bridge
(``zone cmodel list``, inline ``range`` filter).

Usage:
    uv run python scripts/corpus/wire_massflow_common_references.py
"""

import json
from pathlib import Path

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
COMMON_CM_REL = "_common/references/constitutive-models"
COMMON_CM_DIR = RES / COMMON_CM_REL
FLAC_CM = RES / "flac/references/constitutive-models/index.json"
FLAC_RE = RES / "flac/references/range-elements/index.json"
MF_REFS = RES / "massflow/references"

# The 43 models MassFlow exposes (zone cmodel list, MassFlow 3D 9).
MASSFLOW_CMODELS = [
    "anisotropic",
    "burgers",
    "burgers-mohr",
    "cap-yield",
    "cap-yield-simplified",
    "cavehoek",
    "clay-and-sand",
    "columnar-basalt",
    "concrete",
    "curved-mohr-coulomb",
    "double-yield",
    "drucker-prager",
    "elastic",
    "finn",
    "hoek-brown",
    "hoek-brown-pac",
    "hydration-drucker-prager",
    "imass",
    "jones-wilkins-lee",
    "maxwell",
    "modified-cam-clay",
    "mohr-coulomb",
    "mohr-coulomb-tension",
    "munson-dawson",
    "norsand",
    "null",
    "orthotropic",
    "p2psand",
    "plastic-hardening",
    "power",
    "power-mohr",
    "power-ubiquitous",
    "soft-soil",
    "soft-soil-creep",
    "softening-ubiquitous",
    "strain-softening",
    "swell",
    "ubiquitous-anisotropic",
    "ubiquitous-joint",
    "von-mises",
    "wipp",
    "wipp-drucker",
    "wipp-salt",
]


def _wire_constitutive_models() -> tuple[int, list[str]]:
    flac = json.loads(FLAC_CM.read_text(encoding="utf-8"))
    by_name = {m["name"]: m for m in flac["models"]}
    common_pool = {p.stem for p in COMMON_CM_DIR.glob("*.json") if p.stem != "index"}

    borrowed = [dict(by_name[k]) for k in MASSFLOW_CMODELS if k in by_name and k in common_pool]
    undocumented = [k for k in MASSFLOW_CMODELS if k not in common_pool]
    for m in borrowed:
        m["file"] = f"{COMMON_CM_REL}/{Path(m['file']).name}"  # ensure _common pointer

    cat = {
        "type": "constitutive_model_properties",
        "description": (
            "MassFlow zone constitutive model properties — the property vocabulary for 'zone cmodel assign' + "
            "'zone property' in coupled mechanical analysis. Shared 9.0 FLAC3D kernel with FLAC3D/3DEC/MPoint "
            "(docs live in _common). MassFlow exposes a superset of FLAC's models; the models documented here "
            "are the 38 with a shared _common doc."
        ),
        "usage_contexts": [
            "zone cmodel assign <name> [range ...]",
            "zone property <prop> <value> [range ...]",
        ],
        "models": borrowed,
        "note": (
            "MassFlow also exposes these models which do not yet have a shared _common doc and are therefore "
            "not listed above: " + ", ".join(undocumented) + ". They are valid in 'zone cmodel assign'."
        ),
    }
    (MF_REFS / "constitutive-models").mkdir(parents=True, exist_ok=True)
    (MF_REFS / "constitutive-models/index.json").write_text(
        json.dumps(cat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return len(borrowed), undocumented


def _wire_range_elements() -> int:
    flac = json.loads(FLAC_RE.read_text(encoding="utf-8"))
    common_pool = {p.stem for p in (RES / "_common/references/range-elements").glob("*.json") if p.stem != "index"}
    missing = [e["name"] for e in flac["elements"] if e["name"] not in common_pool]
    if missing:
        raise SystemExit(f"range elements missing from _common: {missing}")
    (MF_REFS / "range-elements").mkdir(parents=True, exist_ok=True)
    (MF_REFS / "range-elements/index.json").write_text(
        json.dumps(flac, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return len(flac["elements"])


def main() -> None:
    n_cm, undoc = _wire_constitutive_models()
    n_re = _wire_range_elements()

    top_path = MF_REFS / "index.json"
    top = json.loads(top_path.read_text(encoding="utf-8")) if top_path.exists() else {}
    top.setdefault("type", "reference_index")
    top.setdefault(
        "description",
        "MassFlow (gravity flow / caving) reference documentation: shared 9.0 kernel "
        "constitutive models and range filters used in coupled mechanical analysis.",
    )
    cats = top.setdefault("categories", {})
    cats["constitutive-models"] = {
        "name": "Constitutive Models (Zone)",
        "description": (
            "MassFlow zone constitutive material model properties for coupled mechanical analysis — "
            "mohr-coulomb, drucker-prager, hoek-brown, cam-clay, creep models, etc. Property vocabulary for "
            "'zone cmodel assign' + 'zone property'. Shared 9.0 FLAC3D kernel (docs via _common)."
        ),
        "directory": "constitutive-models",
        "index_file": "constitutive-models/index.json",
        "summary": f"{n_cm} zone material models (shared with FLAC3D via _common; {len(undoc)} models not yet documented)",
        "usage": "zone cmodel assign <name> ; zone property <prop> <value> [range ...]",
    }
    cats["range-elements"] = {
        "name": "Range Elements",
        "description": (
            "Geometric and logical 'range ...' filters (cylinder, sphere, plane, position, group, id, "
            "polygon, union, not, ...) used to scope any MassFlow command. Shared 9.0 kernel."
        ),
        "directory": "range-elements",
        "index_file": "range-elements/index.json",
        "summary": f"{n_re} range filter elements (shared 9.0 kernel via _common)",
        "usage": "<any command> ... range <element> <args> [union|intersect|not ...]",
    }
    top_path.parent.mkdir(parents=True, exist_ok=True)
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"MassFlow constitutive-models registered: {n_cm} borrowed from _common")
    print(f"  MassFlow-only (undocumented, disclosed in note): {undoc}")
    print(f"MassFlow range-elements registered: {n_re} (shared _common)")


if __name__ == "__main__":
    main()
