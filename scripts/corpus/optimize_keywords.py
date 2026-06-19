"""
optimize_keywords.py

Batch-optimize search_keywords for all 177 command JSON files.

Rules:
  A - Remove pure generic verbs that appear in all categories (no discriminating value)
  B - Add category prefix to generic-but-category-specific keywords (align with rblock/brick style)
  C - Keep semantically distinct keywords as-is (they already discriminate well)
  D - Keep 2-5 high-quality keywords per command

Run from repository root:
    py src/itasca_mcp/knowledge/resources/command_docs/optimize_keywords.py
"""

import json
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.join(os.path.dirname(__file__), "commands")

# Rule A: pure generic verbs to strip (stand-alone, no distinguishing value)
GENERIC_VERBS = {
    "create",
    "delete",
    "list",
    "history",
    "export",
    "import",
    "set",
    "assign",
    "remove",
    "modify",
    "update",
    "add",
    "clear",
    "query",
    "single",
    "multiple",
    "track",
    "monitor",
    "snapshot",
    "results",
    "activate",
    "active",
    "initialize",
}

# Rule C: always-keep words regardless of category (high intrinsic specificity)
ALWAYS_KEEP = {
    "porosity",
    "stress",
    "rigid block",
    "polyhedral",
    "angular",
    "inlet",
    "structured",
    "bond",
    "cemented",
    "BM25",
    "equilibrium",
    "convergence",
    "linear",
    "linearpbond",
    "linearcbond",
    "hertz",
    "flatjoint",
    "smoothjoint",
    "rrlinear",
    "arrlinear",
    "bilinear",
    "burger",
    "softbond",
    "hysteretic",
    "lineardipole",
    "bbm",
    "parallel bond",
    "contact bond",
    # fragment / measure specifics
    "connectivity",
    "coordination",
    # wall specifics
    "conveyor",
    "servo",
    # model specifics
    "timestep",
    "gravity",
    "domain",
    "thermal",
    "deterministic",
    "large-strain",
    "voronoi",
    # rblock specifics (already prefixed, keep as reference)
}

# ---------------------------------------------------------------------------
# Per-command keyword map
# (category, command_stem) -> list[str]
# Hand-curated based on description + optimization rules
# ---------------------------------------------------------------------------

KEYWORD_MAP = {
    # -----------------------------------------------------------------------
    # ball
    # -----------------------------------------------------------------------
    ("ball", "accumulate-stress"): ["ball stress accumulation", "incremental stress", "performance"],
    ("ball", "attribute"): ["ball attribute", "ball density", "ball velocity"],
    ("ball", "clump"): ["convert ball to clump", "ball clump conversion", "pebble"],
    ("ball", "create"): ["ball create", "single ball", "ball radius"],
    ("ball", "delete"): ["ball delete", "remove ball", "ball range"],
    ("ball", "distribute"): ["ball distribute", "porosity", "ball overlap packing"],
    ("ball", "export"): ["ball export", "ball geometry", "STL"],
    ("ball", "extra"): ["ball extra variable", "user-defined ball property"],
    ("ball", "fix"): ["ball fix", "fix velocity", "fix spin"],
    ("ball", "free"): ["ball free", "unfix ball", "release constraint"],
    ("ball", "generate"): ["ball generate", "ball packing", "cubic", "hexagonal"],
    ("ball", "group"): ["ball group", "ball group slot"],
    ("ball", "history"): ["ball history", "ball time history", "record ball property"],
    ("ball", "initialize"): ["ball initialize", "ball initial condition"],
    ("ball", "list"): ["ball list", "ball information", "print ball"],
    ("ball", "property"): ["ball property", "ball surface property"],
    ("ball", "results"): ["ball results", "ball post-processing"],
    ("ball", "tolerance"): ["ball tolerance", "ball contact detection"],
    ("ball", "trace"): ["ball trace", "ball path", "trajectory"],
    ("ball", "tractions"): ["ball tractions", "stress initialization", "voronoi"],
    # -----------------------------------------------------------------------
    # clump
    # -----------------------------------------------------------------------
    ("clump", "accumulate-stress"): ["clump stress accumulation", "incremental stress", "performance"],
    ("clump", "attribute"): ["clump attribute", "clump density", "clump velocity"],
    ("clump", "break"): ["clump break", "pebble fracture", "clump fragmentation"],
    ("clump", "create"): ["clump create", "single clump", "pebble template"],
    ("clump", "delete"): ["clump delete", "remove clump"],
    ("clump", "distribute"): ["clump distribute", "porosity", "clump overlap packing"],
    ("clump", "export"): ["clump export", "clump geometry", "STL"],
    ("clump", "extra"): ["clump extra variable", "user-defined clump property"],
    ("clump", "fix"): ["clump fix", "fix clump velocity", "fix clump spin"],
    ("clump", "free"): ["clump free", "unfix clump", "release clump"],
    ("clump", "generate"): ["clump generate", "clump packing", "clump template"],
    ("clump", "group"): ["clump group", "clump group slot"],
    ("clump", "history"): ["clump history", "clump time history", "record clump property"],
    ("clump", "initialize"): ["clump initialize", "clump initial condition"],
    ("clump", "list"): ["clump list", "clump information"],
    ("clump", "order"): ["clump rotation order", "accuracy EOM", "Euler EOM"],
    ("clump", "property"): ["clump property", "clump surface property"],
    ("clump", "replicate"): ["clump replicate", "clump copy", "pebble template"],
    ("clump", "results"): ["clump results", "clump post-processing"],
    ("clump", "rotate"): ["clump rotate", "clump orientation", "rotation axis"],
    ("clump", "scale"): ["clump scale", "clump resize", "clump volume"],
    ("clump", "template"): ["clump template", "bubblepack", "pebble assembly"],
    ("clump", "tolerance"): ["clump tolerance", "clump contact detection"],
    ("clump", "trace"): ["clump trace", "clump path", "trajectory"],
    # -----------------------------------------------------------------------
    # contact
    # -----------------------------------------------------------------------
    ("contact", "activate"): ["contact activate", "contact flag", "contact lifecycle"],
    ("contact", "apply-group"): ["contact apply group", "contact group propagation"],
    ("contact", "cmat-add"): ["cmat add", "cmat rule", "contact model assignment rule"],
    ("contact", "cmat-apply"): ["cmat apply", "contact model matrix apply"],
    ("contact", "cmat-default"): ["cmat default", "contact model default rule"],
    ("contact", "cmat-list"): ["cmat list", "contact model matrix"],
    ("contact", "cmat-modify"): ["cmat modify", "edit cmat rule"],
    ("contact", "cmat-proximity"): ["cmat proximity", "contact gap", "proximity distance"],
    ("contact", "cmat-remove"): ["cmat remove", "delete cmat rule"],
    ("contact", "delete"): ["contact delete", "remove contact"],
    ("contact", "detection"): ["contact detection", "contact lifecycle", "automatic contact"],
    ("contact", "fix"): ["contact fix", "freeze contact", "constant contact"],
    ("contact", "group"): ["contact group", "contact group slot"],
    ("contact", "inhibit"): ["contact inhibit", "disable contact"],
    ("contact", "method"): ["contact method", "bond activation", "parallel bond method"],
    ("contact", "model"): ["contact model", "linear", "linearpbond", "hertz", "flatjoint"],
    ("contact", "persist"): ["contact persist", "contact lifetime"],
    ("contact", "property"): ["contact property", "stiffness", "friction", "damping"],
    # -----------------------------------------------------------------------
    # fragment
    # -----------------------------------------------------------------------
    ("fragment", "activate"): ["fragment activate", "fragment auto-computation"],
    ("fragment", "clear"): ["fragment clear", "reset fragment data"],
    ("fragment", "compute"): ["fragment compute", "connectivity", "fragment analysis"],
    ("fragment", "deactivate"): ["fragment deactivate", "stop fragment tracking"],
    ("fragment", "list"): ["fragment list", "fragment information"],
    ("fragment", "register"): ["fragment register", "fragment type"],
    # -----------------------------------------------------------------------
    # measure
    # -----------------------------------------------------------------------
    ("measure", "create"): ["measure create", "measurement region", "porosity measurement"],
    ("measure", "delete"): ["measure delete", "remove measurement"],
    ("measure", "dump"): ["measure dump", "size distribution", "measurement export"],
    ("measure", "history"): ["measure history", "measurement time history"],
    ("measure", "list"): ["measure list", "measurement information"],
    ("measure", "modify"): ["measure modify", "update measurement"],
    # -----------------------------------------------------------------------
    # model
    # -----------------------------------------------------------------------
    ("model", "calm"): ["model calm", "zero velocity", "damp out kinetic energy"],
    ("model", "clean"): ["model clean", "contact update", "recalculate"],
    ("model", "configure"): ["model configure", "model settings", "module configuration"],
    ("model", "cycle"): ["model cycle", "timestep", "stepping"],
    ("model", "deterministic"): ["model deterministic", "reproducible simulation"],
    ("model", "display"): ["model display", "output format"],
    ("model", "domain"): ["model domain", "boundary", "domain extent"],
    ("model", "gravity"): ["model gravity", "gravitational acceleration"],
    ("model", "history"): ["model history", "global time history"],
    ("model", "large-strain"): ["model large-strain", "large deformation"],
    ("model", "mechanical"): ["model mechanical", "mechanical timestep"],
    ("model", "new"): ["model new", "reset model", "clear model"],
    ("model", "orientation-tracking"): ["orientation tracking", "Euler angles", "rigid body rotation"],
    ("model", "random"): ["model random", "random seed", "reproducible"],
    ("model", "range"): ["model range", "range filter", "named range"],
    ("model", "restore"): ["model restore", "load save file"],
    ("model", "results"): ["model results", "results file", "output snapshot"],
    ("model", "save"): ["model save", "save file"],
    ("model", "solve"): ["model solve", "equilibrium", "convergence criteria"],
    ("model", "thermal"): ["model thermal", "thermal module", "temperature"],
    ("model", "update-interval"): ["model update-interval", "display refresh interval"],
    # -----------------------------------------------------------------------
    # plot
    # -----------------------------------------------------------------------
    ("plot", "active"): ["plot active", "plot render toggle"],
    ("plot", "background"): ["plot background", "background color"],
    ("plot", "clear"): ["plot clear", "remove plot items"],
    ("plot", "copy"): ["plot copy", "duplicate plot"],
    ("plot", "create"): ["plot create", "new plot window"],
    ("plot", "current"): ["plot current", "select active plot"],
    ("plot", "delete"): ["plot delete", "remove plot"],
    ("plot", "export"): ["plot export", "save image", "PNG", "PDF", "SVG"],
    ("plot", "item"): ["plot item", "ball plot", "wall plot", "contact plot", "chart"],
    ("plot", "rename"): ["plot rename", "change plot name"],
    ("plot", "title"): ["plot title", "plot label", "heading"],
    ("plot", "update"): ["plot update", "auto refresh"],
    ("plot", "view"): ["plot view", "camera", "zoom", "perspective", "projection"],
    # -----------------------------------------------------------------------
    # wall
    # -----------------------------------------------------------------------
    ("wall", "active-sides"): ["wall active-sides", "one-sided facet", "wall facet side"],
    ("wall", "addfacet"): ["wall addfacet", "extend wall", "wall vertex"],
    ("wall", "attribute"): ["wall attribute", "wall velocity", "wall displacement"],
    ("wall", "create"): ["wall create", "wall vertices", "wall facet"],
    ("wall", "delete"): ["wall delete", "remove wall"],
    ("wall", "export"): ["wall export", "wall geometry", "STL"],
    ("wall", "extra"): ["wall extra variable", "user-defined wall property"],
    ("wall", "generate"): ["wall generate", "wall box", "wall cylinder"],
    ("wall", "group"): ["wall group", "wall group slot"],
    ("wall", "history"): ["wall history", "wall time history", "record wall property"],
    ("wall", "import"): ["wall import", "STL", "DXF"],
    ("wall", "initialize"): ["wall initialize", "wall initial condition"],
    ("wall", "list"): ["wall list", "wall information"],
    ("wall", "property"): ["wall property", "wall surface property"],
    ("wall", "resolution"): ["wall resolution", "contact resolution strategy"],
    ("wall", "results"): ["wall results", "wall post-processing"],
    ("wall", "rotate"): ["wall rotate", "wall orientation", "rotation axis"],
    ("wall", "servo"): ["wall servo", "servo force control", "force-controlled wall"],
    ("wall", "tolerance"): ["wall tolerance", "wall contact detection"],
    ("wall", "velocity-conveyor"): ["wall conveyor", "conveyor belt", "rotating drum"],
}

# ---------------------------------------------------------------------------
# Helper: apply rules to an existing keyword list (fallback for unknowns)
# ---------------------------------------------------------------------------


def clean_keywords(cat: str, stem: str, kws: list[str]) -> list[str]:
    """
    Fallback cleaner used for categories already well-formed (rblock, brick)
    or as a sanity pass.  Returns the same list untouched if all keywords
    look prefixed or semantically specific.
    """
    out = []
    for kw in kws:
        low = kw.lower().strip()
        # Keep if it's in always_keep set
        if any(ak in low for ak in ALWAYS_KEEP):
            out.append(kw)
            continue
        # Keep if already prefixed with cat or a proper noun / compound
        if cat in low or " " in kw:
            out.append(kw)
            continue
        # Drop pure generic verbs
        if low in GENERIC_VERBS:
            continue
        out.append(kw)
    return out or kws  # never return empty


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    changes = []  # list of (filepath, old_kws, new_kws)

    for cat in sorted(os.listdir(BASE_DIR)):
        cat_dir = os.path.join(BASE_DIR, cat)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            if not fname.endswith(".json"):
                continue
            stem = fname[:-5]
            fpath = os.path.join(cat_dir, fname)

            with open(fpath, encoding="utf-8") as fp:
                data = json.load(fp)

            old_kws = list(data.get("search_keywords", []))

            # Determine new keywords
            key = (cat, stem)
            if key in KEYWORD_MAP:
                new_kws = KEYWORD_MAP[key]
            else:
                # rblock and brick are already well-formed — apply light cleanup
                new_kws = clean_keywords(cat, stem, old_kws)

            # Only write if changed
            if new_kws != old_kws:
                data["search_keywords"] = new_kws
                with open(fpath, "w", encoding="utf-8", newline="\n") as fp:
                    json.dump(data, fp, indent=2, ensure_ascii=False)
                    fp.write("\n")
                changes.append((fpath, old_kws, new_kws))

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Optimized {len(changes)} files\n")
    for fpath, old, new in changes:
        rel = os.path.relpath(fpath, BASE_DIR)
        print(f"  {rel}")
        print(f"    before: {old}")
        print(f"    after:  {new}")
    print(f"\nDone. {len(changes)} files modified.")


if __name__ == "__main__":
    main()
