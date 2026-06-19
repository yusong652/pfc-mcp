"""Generate the 3DEC ``plot-items`` reference category.

Plot item types and their keyword sets are engine-specific (PFC has ball/clump/
wall; FLAC has zone/gridpoint; 3DEC has block / bzone / blockcontact /
subcontact / joint / structure / fracture(DFN) / fluid-flow). They cannot be
borrowed from another engine, so this authors a 3DEC-specific category.

Every keyword list here was probed live against 3DEC 9.0 via the running bridge
with ``plot item create <type> ?`` (and ``... <kw> ?`` to drill into contour /
label / colorby vocabularies) — nothing is hand-invented. The probe output is
baked in as constants below so generation does not need a live binary.

Output (3DEC-local):
    3dec/references/index.json                       (top index, category entry)
    3dec/references/plot-items/index.json            (category index)
    3dec/references/plot-items/<type>/index.json     (one per item type)
    3dec/references/plot-items/<type>/<sub>.json      (contour / label / colorby)

Usage:
    uv run python scripts/corpus/generate_3dec_plot_items.py
"""

import json
from pathlib import Path
from typing import Any

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
OUT = RES / "3dec/references"
CAT_DIR = OUT / "plot-items"

# ---------------------------------------------------------------------------
# Live-probed keyword sets (3DEC 9.0, `plot item create <type> ?`).
# ---------------------------------------------------------------------------

# block / blockface share this top-level set (geometry + zone-face field view).
BLOCK_TOP = [
    "active",
    "clip",
    "contour",
    "cut",
    "deformation-factor",
    "excavated",
    "fill",
    "label",
    "legend",
    "lighting",
    "map",
    "offset",
    "outline",
    "outline-transparency",
    "overlay",
    "polygon-transparency",
    "polygons",
    "range",
    "transparency",
    "walls",
    "zonefaces",
]
# bzone (deformable-block continuum zones) top-level set.
BZONE_TOP = [
    "active",
    "checkinnerzones",
    "clip",
    "color-list",
    "contour",
    "cut",
    "deformation-factor",
    "excavated",
    "label",
    "legend",
    "map",
    "polygons",
    "range",
    "transparency",
]
# Field attributes accepted by block/bzone `contour <attr>` (the scalar/vector/
# tensor you colour by). Modifier keywords (above/below/log/interval/...) live in
# CONTOUR_MODIFIERS.
ZONE_CONTOUR_ATTRS = [
    "displacement",
    "displacement-x",
    "displacement-y",
    "displacement-z",
    "velocity",
    "velocity-x",
    "velocity-y",
    "velocity-z",
    "acceleration",
    "acceleration-x",
    "acceleration-y",
    "acceleration-z",
    "stress",
    "stress-xx",
    "stress-yy",
    "stress-zz",
    "stress-xy",
    "stress-xz",
    "stress-yz",
    "stress-effective",
    "stress-effective-xx",
    "stress-effective-yy",
    "stress-effective-zz",
    "stress-effective-xy",
    "stress-effective-xz",
    "stress-effective-yz",
    "hostress",
    "hostress-xx",
    "hostress-yy",
    "hostress-zz",
    "hostress-xy",
    "hostress-xz",
    "hostress-yz",
    "strain-increment",
    "strain-increment-xx",
    "strain-increment-yy",
    "strain-increment-zz",
    "strain-increment-xy",
    "strain-increment-xz",
    "strain-increment-yz",
    "strain-rate",
    "strain-rate-xx",
    "strain-rate-yy",
    "strain-rate-zz",
    "strain-rate-xy",
    "strain-rate-xz",
    "strain-rate-yz",
    "pore-pressure",
    "temperature",
    "gpppressure",
    "factor-of-safety",
    "kinematic-fos",
    "fob",
    "fob-x",
    "fob-y",
    "fob-z",
    "strength-stress-ratio",
    "convergence",
    "ratio",
    "property",
    "property-fluid",
    "property-thermal",
    "extra",
    "block-extra",
    "gpextra",
    "face-extra",
]
CONTOUR_MODIFIERS = [
    "above",
    "below",
    "interval",
    "log",
    "maximum",
    "minimum",
    "method",
    "component",
    "compression-positive",
    "ramp",
    "reversed",
    "legend",
    "map",
    "deformation-factor",
    "range",
]
# block/bzone `label <type>` categorical colouring.
ZONE_LABEL_TYPES = [
    "bfixity",
    "block",
    "face",
    "id",
    "jointset",
    "model",
    "state",
    "uniform",
    "group-block",
    "group-face",
    "group-zone",
    "property",
    "property-fluid",
    "property-thermal",
    "extra-block",
    "extra-face",
    "extra-zone",
]

# Contacts.
BLOCKCONTACT_TOP = [
    "active",
    "clip",
    "color-list",
    "colorby",
    "cp",
    "cut",
    "legend",
    "map",
    "mark",
    "pixel-size",
    "range",
    "scale",
    "transparency",
]
SUBCONTACT_TOP = [
    "active",
    "clip",
    "color-list",
    "colorby",
    "cut",
    "hide-nforce0",
    "legend",
    "map",
    "mark",
    "pixel-size",
    "range",
    "scale",
    "transparency",
]
BLOCKCONTACT_COLORBY = [
    "contact-extra",
    "contact-group",
    "contact-type",
    "dfn",
    "fracture",
    "joint-set",
    "uniform",
]
SUBCONTACT_COLORBY = [
    "contact-extra",
    "contact-group",
    "contact-type",
    "dfn",
    "fracture",
    "joint-set",
    "model",
    "property",
    "state",
    "subcontact-extra",
    "subcontact-group",
    "uniform",
]

# Joint plane visualization.
JOINT_TOP = [
    "active",
    "clip",
    "color-list",
    "contour",
    "cracked",
    "cut",
    "cut-line",
    "deformation-factor",
    "joined",
    "label",
    "legend",
    "lines",
    "map",
    "polygons",
    "range",
    "stereonet",
    "threshold",
    "transparency",
]
JOINT_CONTOUR = [
    "property-name",
    "value",
    "extra",
    "above",
    "below",
    "interval",
    "log",
    "maximum",
    "minimum",
    "ramp",
    "reversed",
    "threshold",
    "cracked",
    "joined",
]
JOINT_LABEL = ["colorby", "cracked", "joined", "color-list"]

# Structural elements. beam/cable/pile carry `line`; geogrid/liner/shell carry
# `polygons` — otherwise the top-level set is identical.
STRUCT_LINE_TOP = [
    "active",
    "clip",
    "color-list",
    "contour",
    "cut",
    "deformation-factor",
    "label",
    "legend",
    "line",
    "map",
    "marker",
    "range",
    "shrink",
    "slot",
    "system",
    "transparency",
]
STRUCT_POLY_TOP = [
    "active",
    "clip",
    "color-list",
    "contour",
    "cut",
    "deformation-factor",
    "label",
    "legend",
    "map",
    "marker",
    "polygons",
    "range",
    "shrink",
    "slot",
    "system",
    "transparency",
]
STRUCT_BEAM_CONTOUR = [
    "force",
    "force-x",
    "force-y",
    "force-z",
    "force-shear",
    "force-magnitude",
    "moment",
    "moment-x",
    "moment-y",
    "moment-z",
    "moment-bending",
    "moment-magnitude",
    "displacement",
    "displacement-x",
    "displacement-y",
    "displacement-z",
    "displacement-magnitude",
    "displacement-angular",
    "velocity",
    "acceleration",
    "property",
    "extra",
    "stress-max-plastic",
    "stress-min-plastic",
    "area-plastic",
    "ratio-local",
    "ratio-target",
    "convergence",
]
STRUCT_SHELL_CONTOUR = [
    "resultants-mx",
    "resultants-my",
    "resultants-mxy",
    "resultants-nx",
    "resultants-ny",
    "resultants-nxy",
    "resultants-qx",
    "resultants-qy",
    "stress-elastic",
    "stress-elastic-maximum",
    "stress-elastic-minimum",
    "stress-plastic",
    "stress-plastic-maximum",
    "stress-plastic-minimum",
    "coupling-stress-normal-total",
    "coupling-stress-normal-effective",
    "coupling-stress-shear",
    "coupling-pore-pressure",
    "displacement",
    "displacement-magnitude",
    "velocity",
    "property",
    "extra",
]
STRUCT_LABEL = [
    "group",
    "group-node",
    "id",
    "model",
    "property",
    "type-element",
    "uniform",
    "plastic-int",
    "plastic-yield",
    "extra",
    "extra-node",
]

# DFN fractures.
FRACTURE_TOP = [
    "active",
    "both-directions",
    "clip",
    "color-by",
    "color-options",
    "cut",
    "display",
    "ghosts",
    "intersections",
    "legend",
    "map",
    "orientation",
    "range",
    "rosette",
    "scale-by-magnitude",
    "selected-only",
    "shape",
    "stereonet",
    "transparency",
]
FRACTURE_COLORBY = [
    "numeric-attribute",
    "numeric-property",
    "tensor-attribute",
    "tensor-property",
    "text-attribute",
    "text-property",
    "vector-attribute",
    "vector-property",
    "add-numeric-property",
    "add-tensor-property",
    "add-text-property",
    "add-vector-property",
]

# Fracture-flow network.
FBLOCK_TOP = [
    "active",
    "axis",
    "clip",
    "color-list",
    "colorby",
    "cut",
    "legend",
    "polygons",
    "range",
    "rotate",
    "scale",
    "translate",
    "transparency",
    "value",
]
FKNOT_TOP = [
    "active",
    "clip",
    "color-by-value",
    "color-list",
    "colorby",
    "contour",
    "contourby",
    "cut",
    "legend",
    "map",
    "mark",
    "pixel-size",
    "range",
    "scale",
    "transparency",
]
FLOWPLANE_TOP = [
    "active",
    "clip",
    "color-list",
    "colorby",
    "contour",
    "cracked",
    "cut",
    "cut-line",
    "label",
    "legend",
    "polygons",
    "range",
    "transparency",
]


def _kw(name: str, desc: str, syntax: str) -> dict[str, str]:
    return {"keyword": name, "description": desc, "syntax": syntax}


# Common keyword descriptions reused across item types.
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
    "deformation-factor": _kw(
        "deformation-factor", "Exaggerate displacement when drawing.", "deformation-factor <float>"
    ),
    "map": _kw("map", "Configure the contour colour map (ranges, intervals, colours).", "map <sub-keyword> [<value>]"),
    "color-list": _kw(
        "color-list", "Set the discrete colour list used for categorical colouring.", "color-list <Color> [<Color> ...]"
    ),
    "contour": _kw(
        "contour",
        "Colour entities by a scalar/vector/tensor field attribute. See sub-item 'contour'.",
        "contour <attribute> [...]",
    ),
    "label": _kw(
        "label",
        "Categorical colour/label entities (group, model, state, id, ...). See sub-item 'label'.",
        "label <type> [...]",
    ),
    "colorby": _kw(
        "colorby",
        "Categorical colour entities by an attribute (group, type, state, ...). See sub-item 'colorby'.",
        "colorby <attribute> [...]",
    ),
    "polygons": _kw("polygons", "Draw filled polygons (faces) rather than wireframe.", "polygons <bool>"),
    "marker": _kw("marker", "Configure node markers on the element.", "marker <sub-keyword> [<value>]"),
    "slot": _kw("slot", "Restrict categorical colouring to one group slot.", "slot <slot-name>"),
    "system": _kw("system", "Choose the coordinate system used for component output.", "system <global|local>"),
    "mark": _kw("mark", "Mark contacts by type (point markers).", "mark type"),
    "scale": _kw("scale", "Scale the drawn force/marker vectors.", "scale <float>"),
    "cracked": _kw("cracked", "Restrict drawing to cracked (failed) joint segments.", "cracked <bool>"),
    "stereonet": _kw(
        "stereonet", "Render orientations on a stereonet projection.", "stereonet <sub-keyword> [<value>]"
    ),
}


def _basic(keywords: list[str]) -> list[dict[str, str]]:
    """Curated basic_keyword entries for the keywords we have descriptions for."""
    return [SHARED_KW[k] for k in keywords if k in SHARED_KW]


ITEMS: list[dict[str, Any]] = [
    {
        "name": "block",
        "item_types": ["block", "blockface"],
        "search_keywords": ["block", "deformable", "rigid", "stress", "displacement", "contour", "group", "zonefaces"],
        "description": (
            "Whole-block visualization — draws blocks (and their outer zone faces) with field contouring "
            "and categorical labelling. 'plot item create blockface' shares the same keyword set but draws "
            "individual block faces. For the continuum field inside deformable blocks use 'bzone'."
        ),
        "base_syntax": "plot item create block <keywords...>",
        "top_level_keywords": BLOCK_TOP,
        "basic_keywords": _basic(BLOCK_TOP),
        "sub_items": [
            {
                "name": "contour",
                "file": "contour.json",
                "description": "Colour blocks by a scalar/vector/tensor field attribute (stress, displacement, ...).",
            },
            {
                "name": "label",
                "file": "label.json",
                "description": "Categorical colour blocks by group, model, state, id, jointset, ...",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "Blocks by group",
                "command": "plot item create block label group-block legend active on",
                "description": "One colour per block group.",
            },
            {
                "use_case": "Displacement field",
                "command": "plot item create block contour displacement legend active on",
                "description": "Continuous displacement-magnitude colour map.",
            },
            {
                "use_case": "Stress component",
                "command": "plot item create block contour stress-zz legend active on",
                "description": "Vertical stress; compression negative.",
            },
            {
                "use_case": "Model state (yield)",
                "command": "plot item create block label state legend active on",
                "description": "Highlight plastic / yielded zones by state.",
            },
        ],
        "_contour": ("block", ZONE_CONTOUR_ATTRS),
        "_label": ("block", ZONE_LABEL_TYPES),
    },
    {
        "name": "bzone",
        "item_types": ["bzone"],
        "search_keywords": [
            "zone",
            "continuum",
            "deformable",
            "stress",
            "strain",
            "pore pressure",
            "temperature",
            "contour",
        ],
        "description": (
            "Deformable-block continuum zones — the FLAC-style zone field view inside 3DEC blocks. Use "
            "'contour <attribute>' for scalar/tensor field maps (stress, strain, displacement, pore "
            "pressure, temperature) and 'label <type>' for categorical (group/model/state). 'checkinnerzones' "
            "draws interior zones, not just surface."
        ),
        "base_syntax": "plot item create bzone <keywords...>",
        "top_level_keywords": BZONE_TOP,
        "basic_keywords": _basic(BZONE_TOP),
        "sub_items": [
            {
                "name": "contour",
                "file": "contour.json",
                "description": "Colour zones by a scalar/vector/tensor field attribute.",
            },
            {
                "name": "label",
                "file": "label.json",
                "description": "Categorical colour zones by group, model, state, ...",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "Stress contour",
                "command": "plot item create bzone contour stress-zz checkinnerzones on legend active on",
                "description": "Vertical stress across the continuum, interior zones included.",
            },
            {
                "use_case": "Displacement",
                "command": "plot item create bzone contour displacement legend active on",
                "description": "Displacement magnitude interpolated from gridpoints.",
            },
            {
                "use_case": "Plastic state",
                "command": "plot item create bzone label state legend active on",
                "description": "Colour zones by constitutive-model state.",
            },
        ],
        "_contour": ("bzone", ZONE_CONTOUR_ATTRS),
        "_label": ("bzone", ZONE_LABEL_TYPES),
    },
    {
        "name": "blockcontact",
        "item_types": ["blockcontact"],
        "search_keywords": ["contact", "block contact", "force", "joint", "colorby", "mark"],
        "description": (
            "Block-block contacts (the contact between two blocks, parent of subcontacts). Colour by "
            "contact-type / group / joint-set / dfn via 'colorby', mark contact points, and scale drawn "
            "contact-force vectors. For per-segment joint mechanics (state, normal/shear force) use "
            "'subcontact'."
        ),
        "base_syntax": "plot item create blockcontact <keywords...>",
        "top_level_keywords": BLOCKCONTACT_TOP,
        "basic_keywords": _basic(BLOCKCONTACT_TOP),
        "sub_items": [
            {
                "name": "colorby",
                "file": "colorby.json",
                "description": "Categorical colour contacts by contact-type, group, joint-set, dfn, fracture.",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "Contacts by joint set",
                "command": "plot item create blockcontact colorby joint-set legend active on",
                "description": "Colour block contacts by their generating joint set.",
            },
            {
                "use_case": "Contact force vectors",
                "command": "plot item create blockcontact mark type scale 1.0",
                "description": "Mark contacts and scale force markers.",
            },
        ],
        "_colorby": ("blockcontact", BLOCKCONTACT_COLORBY),
    },
    {
        "name": "subcontact",
        "item_types": ["subcontact"],
        "search_keywords": ["subcontact", "joint", "state", "normal force", "shear force", "constitutive", "colorby"],
        "description": (
            "Sub-contacts — the discretized contact segments where the joint constitutive model acts. This "
            "is where joint state / model / property live: 'colorby state' shows slip/separation, "
            "'colorby model' shows the assigned jmodel. 'hide-nforce0' hides segments carrying no normal "
            "force."
        ),
        "base_syntax": "plot item create subcontact <keywords...>",
        "top_level_keywords": SUBCONTACT_TOP,
        "basic_keywords": _basic(SUBCONTACT_TOP),
        "sub_items": [
            {
                "name": "colorby",
                "file": "colorby.json",
                "description": "Categorical colour subcontacts by state, model, property, group, joint-set, dfn, ...",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "Joint slip/state",
                "command": "plot item create subcontact colorby state legend active on",
                "description": "Show which sub-contacts are slipping / open / bonded.",
            },
            {
                "use_case": "By joint model",
                "command": "plot item create subcontact colorby model legend active on",
                "description": "Colour by the assigned joint constitutive model.",
            },
            {
                "use_case": "Hide unloaded",
                "command": "plot item create subcontact colorby state hide-nforce0 on",
                "description": "Drop sub-contacts with zero normal force.",
            },
        ],
        "_colorby": ("subcontact", SUBCONTACT_COLORBY),
    },
    {
        "name": "joint",
        "item_types": ["joint"],
        "search_keywords": ["joint", "discontinuity", "cracked", "stereonet", "property", "contour"],
        "description": (
            "Joint-plane visualization across the model — draw joint surfaces, restrict to 'cracked' "
            "(failed) segments, 'contour' by a named joint property or value, project orientations on a "
            "'stereonet', and 'label' categorically. 'joined' merges coplanar segments; 'threshold' filters "
            "by value."
        ),
        "base_syntax": "plot item create joint <keywords...>",
        "top_level_keywords": JOINT_TOP,
        "basic_keywords": _basic(JOINT_TOP),
        "sub_items": [
            {
                "name": "contour",
                "file": "contour.json",
                "description": "Contour joints by a named property ('property-name <string>') or value.",
            },
            {
                "name": "label",
                "file": "label.json",
                "description": "Categorical colour/label joints (colorby, cracked, joined).",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "Cracked joints",
                "command": "plot item create joint cracked on legend active on",
                "description": "Show only failed joint segments.",
            },
            {
                "use_case": "Joint property contour",
                "command": "plot item create joint contour property-name 'friction' legend active on",
                "description": "Colour joints by a named property field.",
            },
            {
                "use_case": "Orientation stereonet",
                "command": "plot item create joint stereonet active on",
                "description": "Project joint orientations on a stereonet.",
            },
        ],
        "_contour": ("joint", JOINT_CONTOUR),
        "_label": ("joint", JOINT_LABEL),
    },
    {
        "name": "structure",
        "item_types": [
            "structure-beam",
            "structure-cable",
            "structure-pile",
            "structure-geogrid",
            "structure-liner",
            "structure-shell",
            "structure-vector",
        ],
        "search_keywords": [
            "structure",
            "sel",
            "beam",
            "cable",
            "pile",
            "liner",
            "shell",
            "geogrid",
            "force",
            "moment",
        ],
        "description": (
            "Structural-element (SEL) visualization, one item type per element: structure-beam / "
            "structure-cable / structure-pile (line elements, carry the 'line' keyword) and "
            "structure-geogrid / structure-liner / structure-shell (surface elements, carry 'polygons'). "
            "'contour <attribute>' maps forces/moments/resultants; 'label <type>' colours by group/model/"
            "state. 'structure-vector' draws nodal vectors."
        ),
        "base_syntax": "plot item create structure-<type> <keywords...>",
        "top_level_keywords": STRUCT_LINE_TOP,
        "basic_keywords": _basic(STRUCT_LINE_TOP),
        "sub_items": [
            {
                "name": "contour",
                "file": "contour.json",
                "description": "Contour attributes for line elements (force/moment) and shells (resultants/stress).",
            },
            {
                "name": "label",
                "file": "label.json",
                "description": "Categorical colour SELs by group, model, id, type-element, plastic state, ...",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "Cable axial force",
                "command": "plot item create structure-cable contour force legend active on",
                "description": "Colour cable elements by axial force.",
            },
            {
                "use_case": "Beam bending moment",
                "command": "plot item create structure-beam contour moment-bending legend active on",
                "description": "Bending-moment distribution along beams.",
            },
            {
                "use_case": "Shell resultants",
                "command": "plot item create structure-shell contour resultants-mx legend active on",
                "description": "Shell moment resultant Mx.",
            },
            {
                "use_case": "SELs by group",
                "command": "plot item create structure-liner label group legend active on",
                "description": "Colour liner elements by group.",
            },
        ],
        "notes_extra": [
            "Line elements (beam/cable/pile) accept 'line'; surface elements (geogrid/liner/shell) accept 'polygons' — otherwise the top-level keyword set is identical.",
            "structure-shell adds resultants-* and stress-elastic/plastic-* and coupling-* contour attributes that line elements do not have.",
        ],
        "_contour": ("structure", sorted(set(STRUCT_BEAM_CONTOUR + STRUCT_SHELL_CONTOUR))),
        "_label": ("structure", STRUCT_LABEL),
    },
    {
        "name": "fracture",
        "item_types": ["fracture"],
        "search_keywords": ["fracture", "dfn", "discrete fracture network", "orientation", "stereonet", "rosette"],
        "description": (
            "Discrete Fracture Network (DFN) fractures — draw fracture polygons/shapes, colour by numeric/"
            "tensor/text/vector property via 'color-by', show 'intersections' and 'ghosts', and analyse "
            "orientation with 'stereonet' / 'rosette'. 'scale-by-magnitude' sizes fractures by a property."
        ),
        "base_syntax": "plot item create fracture <keywords...>",
        "top_level_keywords": FRACTURE_TOP,
        "basic_keywords": [
            _kw(
                "color-by",
                "Colour fractures by a numeric/tensor/text/vector property or attribute. See sub-item 'color-by'.",
                "color-by <property|attribute spec>",
            ),
            _kw("orientation", "Colour/group fractures by their orientation.", "orientation <sub-keyword>"),
            SHARED_KW["stereonet"],
            _kw("rosette", "Render a strike/dip rosette of fracture orientations.", "rosette <sub-keyword>"),
            _kw("intersections", "Draw fracture-fracture intersection traces.", "intersections <bool>"),
            _kw("scale-by-magnitude", "Scale fracture size by a magnitude property.", "scale-by-magnitude <bool>"),
            SHARED_KW["range"],
            SHARED_KW["transparency"],
        ],
        "sub_items": [
            {
                "name": "color-by",
                "file": "color-by.json",
                "description": "Colour DFN fractures by numeric/tensor/text/vector property or attribute.",
            },
        ],
        "common_usage_patterns": [
            {
                "use_case": "DFN by orientation",
                "command": "plot item create fracture orientation dip legend active on",
                "description": "Colour fractures by dip.",
            },
            {
                "use_case": "Stereonet of DFN",
                "command": "plot item create fracture stereonet active on",
                "description": "Orientation density on a stereonet.",
            },
            {
                "use_case": "Colour by property",
                "command": "plot item create fracture color-by numeric-property aperture legend active on",
                "description": "Colour fractures by a numeric property (e.g. aperture).",
            },
        ],
        "_colorby_named": ("fracture", "color-by", FRACTURE_COLORBY),
    },
    {
        "name": "flow",
        "item_types": ["fblock", "fknot", "flowplane"],
        "search_keywords": [
            "fluid",
            "flow",
            "fracture flow",
            "flowplane",
            "fknot",
            "fblock",
            "pore pressure",
            "permeability",
        ],
        "description": (
            "Fracture-flow network items: 'flowplane' (the planar flow domain on joints — contour/label, "
            "cracked), 'fknot' (flow knots/nodes — contour pore pressure/head), and 'fblock' (flow blocks). "
            "Colour by domain attributes via 'colorby' / 'contour'. Used for hydro-mechanical (joint flow) "
            "analyses."
        ),
        "base_syntax": "plot item create <flowplane|fknot|fblock> <keywords...>",
        "top_level_keywords": sorted(set(FBLOCK_TOP + FKNOT_TOP + FLOWPLANE_TOP)),
        "basic_keywords": [
            SHARED_KW["active"],
            SHARED_KW["contour"],
            SHARED_KW["colorby"],
            SHARED_KW["cracked"],
            SHARED_KW["polygons"],
            SHARED_KW["range"],
            SHARED_KW["legend"],
            SHARED_KW["transparency"],
        ],
        "common_usage_patterns": [
            {
                "use_case": "Flowplane pore pressure",
                "command": "plot item create flowplane contour legend active on",
                "description": "Contour the joint flow plane field.",
            },
            {
                "use_case": "Flow knots",
                "command": "plot item create fknot contour legend active on",
                "description": "Colour flow knots by head/pressure.",
            },
        ],
        "notes_extra": [
            "flowplane top-level: " + ", ".join(FLOWPLANE_TOP) + ".",
            "fknot top-level: " + ", ".join(FKNOT_TOP) + ".",
            "fblock top-level: " + ", ".join(FBLOCK_TOP) + ".",
        ],
    },
]

PROBE_NOTE = (
    "Probe live with 'plot item create <type> ?' to list top-level keywords, then "
    "'plot item create <type> <kw> ?' for sub-options. Keyword sets here are binary-validated "
    "against 3DEC 9.0."
)


def _write_contour(item_dir: Path, name: str, attrs: list[str]) -> None:
    doc = {
        "name": "contour",
        "parent_item": name,
        "description": f"Field attributes accepted by 'plot item create {name} contour <attribute>' (3DEC 9.0).",
        "base_syntax": f"plot item create {name} contour <attribute> [modifiers...]",
        "attributes": attrs,
        "modifiers": CONTOUR_MODIFIERS,
        "notes": [
            "Append a single attribute after 'contour', then modifiers (above/below/interval/log/...).",
            "Vector/tensor attributes (displacement, stress, strain-*) accept a component suffix (-x/-y/-z, -xx/-xy/...).",
            PROBE_NOTE,
        ],
    }
    (item_dir / "contour.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")


def _write_label(item_dir: Path, name: str, types: list[str]) -> None:
    doc = {
        "name": "label",
        "parent_item": name,
        "description": f"Categorical 'label' types accepted by 'plot item create {name} label <type>' (3DEC 9.0).",
        "base_syntax": f"plot item create {name} label <type> [modifiers...]",
        "label_types": types,
        "notes": [PROBE_NOTE],
    }
    (item_dir / "label.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")


def _write_colorby(item_dir: Path, name: str, attrs: list[str], filename: str = "colorby") -> None:
    doc = {
        "name": filename,
        "parent_item": name,
        "description": f"Categorical attributes accepted by 'plot item create {name} {filename} <attribute>' (3DEC 9.0).",
        "base_syntax": f"plot item create {name} {filename} <attribute>",
        "attributes": attrs,
        "notes": [PROBE_NOTE],
    }
    (item_dir / f"{filename}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", "utf-8")


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
            "dimension": "3D",
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

        if "_contour" in item:
            _write_contour(item_dir, *item["_contour"])
        if "_label" in item:
            _write_label(item_dir, *item["_label"])
        if "_colorby" in item:
            _write_colorby(item_dir, *item["_colorby"])
        if "_colorby_named" in item:
            cb_name, cb_file, cb_attrs = item["_colorby_named"]
            _write_colorby(item_dir, cb_name, cb_attrs, cb_file)

        catalog.append(
            {
                "name": name,
                "file": f"{name}/index.json",
                "description": item["description"].split(".")[0] + ".",
                "common_use": ", ".join(item["item_types"]),
            }
        )
        print(
            f"  {name:<14} types={len(item['item_types'])} top_kw={len(item['top_level_keywords'])} subs={len(item.get('sub_items', []))}"
        )

    (CAT_DIR / "index.json").write_text(
        json.dumps(
            {
                "type": "plot_item_keywords",
                "description": (
                    "Configuration keywords for 3DEC plot item types created via 'plot item create <type>'. "
                    "Item types and keyword sets are binary-validated against 3DEC 9.0."
                ),
                "usage_context": "plot item create <type> <keyword> <keyword> ...",
                "items": catalog,
                "notes": [
                    "Plot-item keywords are appended after the item type.",
                    "Some compound settings are easier to apply with 'plot item modify <id> ...' after creating the item.",
                    PROBE_NOTE,
                    "3DEC accepts ~60 plot item types; this documents the core mechanical/flow/DFN entities. "
                    "Vector variants (block-vector, jointvector, structure-vector, flowplane-vector) and "
                    "chart/data/geometry items are accepted but not individually documented here.",
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        "utf-8",
    )

    top_path = OUT / "index.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top.setdefault("categories", {})["plot-items"] = {
        "name": "Plot Items",
        "description": (
            "3DEC plot item types and their keyword sets — block / bzone (continuum) / blockcontact / "
            "subcontact (joint mechanics) / joint / structure (SEL) / fracture (DFN) / flow. Vocabulary for "
            "'plot item create <type> ...'."
        ),
        "directory": "plot-items",
        "index_file": "plot-items/index.json",
        "summary": f"{len(catalog)} 3DEC plot item groups (block/bzone/contacts/joint/structure/fracture/flow)",
        "usage": "plot item create <type> contour <attr> | label <type> | colorby <attr> [range ...]",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} plot item groups)")


if __name__ == "__main__":
    main()
