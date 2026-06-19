"""Generate the MPoint (MPM) ``plot-items`` reference category.

Plot item types are engine-specific, so they cannot be borrowed from another
engine — this authors an MPoint-specific category. MPoint's distinctive
plottable entities are the material points and the background grid:
``mpoint`` (material points), ``mpoint-vector`` / ``meshnode-vector`` (vector
fields), ``mpoint-tensor`` (tensor glyphs), ``mpoint-hybrid`` (hybrid points),
``meshpoint`` (background-grid mesh points).

Every keyword list was probed live against MPoint 3D 9 via the bridge with
``plot item create <type> ?`` (and ``... <kw> ?`` to drill into color-by /
value / draw-as), then baked in here as constants so generation needs no live
binary.

This is the first MPoint reference category, so it also creates
``mpoint/references/index.json``.

Output (MPoint-local):
    mpoint/references/index.json                    (top index, category entry)
    mpoint/references/plot-items/index.json         (category index)
    mpoint/references/plot-items/<type>/index.json  (one per item type)
    mpoint/references/plot-items/mpoint/color-by.json (sub-item)

Usage:
    uv run python scripts/corpus/generate_mpoint_plot_items.py
"""

import json
from pathlib import Path
from typing import Any

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
OUT = RES / "mpoint/references"
CAT_DIR = OUT / "plot-items"

# ---------------------------------------------------------------------------
# Live-probed keyword sets (MPoint 3D 9, `plot item create <type> ?`).
# ---------------------------------------------------------------------------

MPOINT_TOP = [
    "active",
    "clear",
    "clip",
    "color-by",
    "cut",
    "extra",
    "fixity",
    "global",
    "group",
    "hide-null",
    "label",
    "legend",
    "map",
    "model",
    "pixel-size",
    "quality",
    "range",
    "state",
    "transparency",
    "uniform",
    # contour-shaping modifiers (also valid at top level): above below interval
    # log maximum minimum ramp reversed
    "above",
    "below",
    "interval",
    "log",
    "maximum",
    "minimum",
    "ramp",
    "reversed",
]
# `mpoint color-by` chooses between a continuous contour and categorical label.
MPOINT_COLORBY = ["contour", "label"]
# `mpoint color-by contour <...>`: the contoured quantity is given via
# `value <name>` or `property <name>` (a string), with these display modifiers.
MPOINT_CONTOUR_MODIFIERS = [
    "value",
    "property",
    "component",
    "compression-positive",
    "above",
    "below",
    "interval",
    "log",
    "maximum",
    "minimum",
    "ramp",
    "reversed",
    "hide-null",
    "legend",
    "map",
    "range",
]
# Categorical colouring keywords accepted directly on the mpoint item.
MPOINT_CATEGORICAL = ["state", "model", "fixity", "group", "label", "uniform", "extra"]

MPOINT_VECTOR_TOP = [
    "active",
    "by-magnitude",
    "clip",
    "color",
    "cut",
    "draw-as",
    "legend",
    "map",
    "maxnumber",
    "point-to-base",
    "quality",
    "range",
    "scale",
    "shape",
    "skip",
    "transparency",
    "value",
]
VECTOR_VALUES = ["discharge", "displacement", "fob", "velocity", "velocity-applied"]
VECTOR_DRAW_AS = ["arrow", "disk", "line"]

MPOINT_TENSOR_TOP = ["strain", "strainrate", "stress"]

# mpoint-hybrid and meshpoint share this lighter grid-point keyword set.
GRIDPOINT_TOP = [
    "active",
    "clear",
    "clip",
    "cut",
    "global",
    "label",
    "legend",
    "map",
    "pixel-size",
    "quality",
    "range",
    "transparency",
]


def _kw(name: str, desc: str, syntax: str) -> dict[str, str]:
    return {"keyword": name, "description": desc, "syntax": syntax}


SHARED_KW = {
    "active": _kw("active", "Show or hide the item without removing it.", "active <bool>"),
    "range": _kw(
        "range",
        "Filter which entities are drawn using range elements (see references/range-elements).",
        "range <range-element> [...]",
    ),
    "legend": _kw("legend", "Show/configure the item legend.", "legend <sub-keyword> [<value>]"),
    "transparency": _kw(
        "transparency", "Set item transparency (0 opaque .. 100 fully transparent).", "transparency <0-100>"
    ),
    "cut": _kw("cut", "Apply a 3D cutting plane to the item.", "cut active on origin (x,y,z) normal (nx,ny,nz)"),
    "clip": _kw("clip", "Clip the item against the global model clip box.", "clip <bool>"),
    "map": _kw("map", "Configure the contour colour map (ranges, intervals, colours).", "map <sub-keyword> [<value>]"),
    "color-by": _kw(
        "color-by",
        "Choose continuous (contour) or categorical (label) colouring. See sub-item 'color-by'.",
        "color-by <contour|label> ...",
    ),
    "label": _kw("label", "Categorical colour/label by a named attribute.", "label <string>"),
    "state": _kw("state", "Colour material points by constitutive-model state (elastic/plastic/yielded).", "state ..."),
    "model": _kw("model", "Colour material points by the assigned constitutive model.", "model ..."),
    "fixity": _kw("fixity", "Colour material points by velocity/fluid fixity condition.", "fixity ..."),
    "group": _kw("group", "Colour material points by group (optionally a slot).", "group [slot <slot>]"),
    "value": _kw(
        "value", "Vector quantity to draw (discharge/displacement/fob/velocity/velocity-applied).", "value <quantity>"
    ),
    "draw-as": _kw("draw-as", "Glyph used to draw each vector.", "draw-as <arrow|disk|line>"),
    "scale": _kw("scale", "Scale the drawn vectors.", "scale <float>"),
    "by-magnitude": _kw("by-magnitude", "Colour vectors by their magnitude.", "by-magnitude <bool>"),
    "skip": _kw("skip", "Draw every Nth vector to thin a dense field.", "skip <int>"),
    "global": _kw("global", "Draw across the whole model (ignore per-plot clipping).", "global <bool>"),
    "quality": _kw("quality", "Rendering quality / point tessellation level.", "quality <int>"),
}


def _basic(keywords: list[str]) -> list[dict[str, str]]:
    return [SHARED_KW[k] for k in keywords if k in SHARED_KW]


PROBE_NOTE = (
    "Probe live with 'plot item create <type> ?' to list top-level keywords, then "
    "'plot item create <type> <kw> ?' for sub-options. Keyword sets here are binary-validated "
    "against MPoint 3D 9."
)

ITEMS: list[dict[str, Any]] = [
    {
        "name": "mpoint",
        "item_types": ["mpoint"],
        "search_keywords": ["material point", "mpoint", "stress", "displacement", "state", "model", "contour"],
        "description": (
            "Material points — the core MPM entity. Colour by a continuous field via 'color-by contour "
            "value <quantity>' (or 'property <name>'), or categorically by 'state' (constitutive-model "
            "state), 'model' (assigned cmodel), 'fixity', or 'group'."
        ),
        "base_syntax": "plot item create mpoint <keywords...>",
        "top_level_keywords": sorted(set(MPOINT_TOP)),
        "basic_keywords": _basic(
            [
                "active",
                "color-by",
                "state",
                "model",
                "fixity",
                "group",
                "label",
                "range",
                "legend",
                "map",
                "cut",
                "transparency",
            ]
        ),
        "sub_items": [
            {
                "name": "color-by",
                "file": "color-by.json",
                "description": "Continuous contour (value/property) vs categorical label colouring of material points.",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "Stress field",
                "command": "plot item create mpoint color-by contour value stress-zz legend active on",
                "description": "Contour material points by a stress component.",
            },
            {
                "use_case": "Displacement",
                "command": "plot item create mpoint color-by contour value displacement legend active on",
                "description": "Continuous displacement-magnitude colour map.",
            },
            {
                "use_case": "Model state",
                "command": "plot item create mpoint state legend active on",
                "description": "Colour points by constitutive-model state (elastic/plastic).",
            },
            {
                "use_case": "By constitutive model",
                "command": "plot item create mpoint model legend active on",
                "description": "Colour points by their assigned cmodel.",
            },
        ],
        "_colorby": True,
    },
    {
        "name": "mpoint-vector",
        "item_types": ["mpoint-vector", "meshnode-vector"],
        "search_keywords": ["vector", "velocity", "displacement", "discharge", "material point", "background node"],
        "description": (
            "Vector field drawn at material points. 'value' selects the quantity (velocity, displacement, "
            "discharge, fob, velocity-applied); 'draw-as' picks the glyph (arrow/disk/line). The "
            "'meshnode-vector' item draws the same vector quantities at background-grid nodes with an "
            "identical keyword set."
        ),
        "base_syntax": "plot item create mpoint-vector <keywords...>",
        "top_level_keywords": MPOINT_VECTOR_TOP,
        "basic_keywords": _basic(
            ["active", "value", "draw-as", "scale", "by-magnitude", "skip", "range", "legend", "map", "transparency"]
        ),
        "sub_items": [],
        "common_usage_patterns": [
            {
                "use_case": "Velocity arrows",
                "command": "plot item create mpoint-vector value velocity draw-as arrow scale 1.0",
                "description": "Velocity vectors at material points.",
            },
            {
                "use_case": "Displacement field",
                "command": "plot item create mpoint-vector value displacement by-magnitude on",
                "description": "Displacement vectors coloured by magnitude.",
            },
            {
                "use_case": "Grid-node velocity",
                "command": "plot item create meshnode-vector value velocity draw-as arrow",
                "description": "Same vectors at the background-grid nodes.",
            },
        ],
        "notes_extra": [
            "value quantities: " + ", ".join(VECTOR_VALUES) + ".",
            "draw-as glyphs: " + ", ".join(VECTOR_DRAW_AS) + ".",
            "meshnode-vector shares this exact keyword set (drawn at grid nodes instead of material points).",
        ],
    },
    {
        "name": "mpoint-tensor",
        "item_types": ["mpoint-tensor"],
        "search_keywords": ["tensor", "stress", "strain", "strainrate", "material point", "glyph"],
        "description": (
            "Tensor glyphs at material points. Pick the tensor field: 'stress', 'strain', or 'strainrate'. "
            "Useful for visualising principal-stress orientation and magnitude across the MPM body."
        ),
        "base_syntax": "plot item create mpoint-tensor <stress|strain|strainrate> [...]",
        "top_level_keywords": MPOINT_TENSOR_TOP,
        "basic_keywords": [
            _kw("stress", "Draw the stress tensor glyph at each material point.", "stress [...]"),
            _kw("strain", "Draw the strain tensor glyph.", "strain [...]"),
            _kw("strainrate", "Draw the strain-rate tensor glyph.", "strainrate [...]"),
        ],
        "sub_items": [],
        "common_usage_patterns": [
            {
                "use_case": "Stress tensor",
                "command": "plot item create mpoint-tensor stress legend active on",
                "description": "Principal-stress glyphs at material points.",
            },
        ],
    },
    {
        "name": "mpoint-hybrid",
        "item_types": ["mpoint-hybrid"],
        "search_keywords": ["hybrid", "coupled", "material point", "gridpoint coupling"],
        "description": (
            "Hybrid material points — points coupled to the background grid via 'mpoint hybrid-points'. "
            "Lighter keyword set (geometry/label/clip), for showing where MPM couples to gridpoints."
        ),
        "base_syntax": "plot item create mpoint-hybrid <keywords...>",
        "top_level_keywords": GRIDPOINT_TOP,
        "basic_keywords": _basic(["active", "label", "global", "range", "legend", "map", "cut", "transparency"]),
        "sub_items": [],
        "common_usage_patterns": [
            {
                "use_case": "Show hybrid points",
                "command": "plot item create mpoint-hybrid active on",
                "description": "Render the coupled hybrid material points.",
            },
        ],
    },
    {
        "name": "meshpoint",
        "item_types": ["meshpoint"],
        "search_keywords": ["mesh point", "background grid", "node", "grid"],
        "description": (
            "Background-grid mesh points — the fixed computational grid through which material points move. "
            "Use to inspect the grid resolution and extent relative to the material-point body."
        ),
        "base_syntax": "plot item create meshpoint <keywords...>",
        "top_level_keywords": GRIDPOINT_TOP,
        "basic_keywords": _basic(["active", "label", "global", "range", "legend", "map", "cut", "transparency"]),
        "sub_items": [],
        "common_usage_patterns": [
            {
                "use_case": "Show background grid",
                "command": "plot item create meshpoint active on",
                "description": "Render the background-grid mesh points.",
            },
        ],
    },
]


def _write_colorby(item_dir: Path) -> None:
    doc = {
        "name": "color-by",
        "parent_item": "mpoint",
        "description": "Colour material points continuously ('contour') or categorically ('label'), probed against MPoint 3D 9.",
        "base_syntax": "plot item create mpoint color-by <contour|label> ...",
        "modes": [
            {
                "mode": "contour",
                "syntax": "color-by contour value <quantity> | color-by contour property <name>",
                "description": "Continuous field colouring. The quantity is given by 'value <name>' (built-in field) or 'property <name>' (named property), not a fixed keyword enum.",
                "modifiers": MPOINT_CONTOUR_MODIFIERS,
            },
            {
                "mode": "label",
                "syntax": "color-by label <string>",
                "description": "Categorical colouring by a named attribute (takes a string).",
            },
        ],
        "categorical_keywords": MPOINT_CATEGORICAL,
        "notes": [
            "For built-in vector quantities (velocity, displacement) prefer the 'mpoint-vector' item.",
            "'state' / 'model' / 'fixity' / 'group' are accepted directly on the mpoint item for categorical colouring.",
            PROBE_NOTE,
        ],
    }
    (item_dir / "color-by.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")


def main() -> None:
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []
    for item in ITEMS:
        name = item["name"]
        item_dir = CAT_DIR / name
        item_dir.mkdir(exist_ok=True)
        doc: dict[str, Any] = {
            "name": name,
            "item_type": name,
            "item_types": item["item_types"],
            "dimension": "mixed",
            "search_keywords": item["search_keywords"],
            "description": item["description"],
            "base_syntax": item["base_syntax"],
            "top_level_keywords": item["top_level_keywords"],
            "basic_keywords": item["basic_keywords"],
            "sub_items": item.get("sub_items", []),
            "common_usage_patterns": item["common_usage_patterns"],
            "notes": [PROBE_NOTE, *item.get("notes_extra", [])],
        }
        (item_dir / "index.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")
        if item.get("_colorby"):
            _write_colorby(item_dir)
        catalog.append(
            {
                "name": name,
                "file": f"{name}/index.json",
                "description": item["description"].split(".")[0] + ".",
                "common_use": ", ".join(item["item_types"]),
            }
        )
        print(
            f"  {name:<16} types={len(item['item_types'])} top_kw={len(item['top_level_keywords'])} subs={len(item.get('sub_items', []))}"
        )

    (CAT_DIR / "index.json").write_text(
        json.dumps(
            {
                "type": "plot_item_keywords",
                "description": (
                    "Configuration keywords for MPoint (MPM) plot item types created via "
                    "'plot item create <type>'. Item types and keyword sets are binary-validated against "
                    "MPoint 3D 9."
                ),
                "usage_context": "plot item create <type> <keyword> <keyword> ...",
                "items": catalog,
                "notes": [
                    "Plot-item keywords are appended after the item type.",
                    PROBE_NOTE,
                    "MPoint also accepts the shared/other-engine plot items (zone, structure-*, fracture, "
                    "geometry, chart-*, ...); this documents the MPoint-specific material-point and "
                    "background-grid entities.",
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        "utf-8",
    )

    # First MPoint reference category — create the top references index.
    top_path = OUT / "index.json"
    if top_path.exists():
        top = json.loads(top_path.read_text(encoding="utf-8"))
    else:
        top = {
            "type": "mpoint_references",
            "description": "MPoint (MPM) reference documentation: syntax elements (property vocabularies) used within commands.",
            "categories": {},
            "navigation": {
                "root": "List all reference categories",
                "category": "List items in category (e.g., 'plot-items')",
                "item": "Full documentation (e.g., 'plot-items mpoint')",
            },
            "notes": [
                "References are syntax elements used within commands, not standalone commands",
                "Use pfc_browse_commands (software='mpoint') for command syntax",
                "Use pfc_browse_reference (software='mpoint') for reference documentation",
            ],
        }
    top.setdefault("categories", {})["plot-items"] = {
        "name": "Plot Items",
        "description": (
            "MPoint plot item types — material points (mpoint), vector/tensor fields "
            "(mpoint-vector/meshnode-vector, mpoint-tensor), hybrid points (mpoint-hybrid) and the "
            "background grid (meshpoint). Vocabulary for 'plot item create <type> ...'."
        ),
        "directory": "plot-items",
        "index_file": "plot-items/index.json",
        "summary": f"{len(catalog)} MPoint plot item groups (mpoint/vector/tensor/hybrid/meshpoint)",
        "usage": "plot item create mpoint color-by contour value <q> | plot item create mpoint-vector value velocity ...",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} plot item groups) + top references index")


if __name__ == "__main__":
    main()
