"""Parse brick and rblock command HTML documentation for PFC 6.0, 7.0, and 9.0.

Generates JSON files under:
  commands/brick/   - brick and inlet subcommands
  commands/rblock/  - rblock subcommands

Usage:
    uv run python src/itasca_mcp/knowledge/resources/command_docs/parse_brick_rblock.py
"""

import json
import re
from pathlib import Path

try:
    from parse_pfc600 import CommandHTMLParser, normalize_syntax
except ModuleNotFoundError:  # pragma: no cover - fallback when imported as a package module
    from .parse_pfc600 import CommandHTMLParser, normalize_syntax

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

PFC600_DOC = Path("C:/Program Files/Itasca/PFC600/exe64/doc")
PFC700_DOC = Path("C:/Program Files/Itasca/PFC700/exe64/doc")
PFC900_DOC = Path("C:/Program Files/Itasca/ItascaSoftware900/exe64/doc")

COMMANDS_DIR = Path(__file__).parent / "commands"

BRICK_COMMANDS_DIRS = {
    "6.0": PFC600_DOC / "pfc/pfcmodule/doc/manual/brick_manual/brick_commands",
    "7.0": PFC700_DOC / "pfc/pfcmodule/doc/manual/brick_manual/brick_commands",
    "9.0": PFC900_DOC / "pfc/pfcmodule/doc/manual/brick_manual/brick_commands",
}

RBLOCK_COMMANDS_DIRS = {
    "6.0": PFC600_DOC / "pfc/rblock/doc/manual/commands",
    "7.0": PFC700_DOC / "pfc/rblock/doc/manual/commands",
    "9.0": PFC900_DOC / "pfc/rblock/doc/manual/commands",
}

# ---------------------------------------------------------------------------
# HTML filename -> (json_key, full_command_name) mapping helpers
# ---------------------------------------------------------------------------


def html_stem_to_brick_key(stem: str) -> tuple[str, str] | None:
    """Map HTML file stem to (json_key, full_command_name) for brick/inlet commands.

    Returns None for non-command files (e.g. brick_commands.html).
    """
    if stem.startswith("cmd_brick_"):
        sub = stem[len("cmd_brick_") :]
        return sub, f"brick {sub}"
    if stem.startswith("cmd_inlet_"):
        sub = stem[len("cmd_inlet_") :]
        return f"inlet-{sub}", f"inlet {sub}"
    return None


def html_stem_to_rblock_key(stem: str) -> tuple[str, str] | None:
    """Map HTML file stem to (json_key, full_command_name) for rblock commands.

    Handles both 'cmd_rblock_xxx' and 'cmd_rblock.xxx' naming.
    Returns None for non-command files.
    """
    # cmd_rblock.remap-interval (dot variant)
    if stem.startswith("cmd_rblock."):
        sub = stem[len("cmd_rblock.") :]
        # json key: replace dots with dashes
        json_key = sub.replace(".", "-")
        return json_key, f"rblock {sub}"
    # cmd_rblock_facet.apply etc. (underscore prefix, dot separator in sub)
    if stem.startswith("cmd_rblock_"):
        sub = stem[len("cmd_rblock_") :]
        # sub may contain dots: facet.apply -> facet-apply
        json_key = sub.replace(".", "-")
        return json_key, f"rblock {sub.replace('.', ' ')}"
    return None


# ---------------------------------------------------------------------------
# PFC 9.0 syntax fallback: extract from dt block using span text
# ---------------------------------------------------------------------------


def _extract_900_syntax(content: str) -> str:
    """Extract command syntax from PFC 9.0 HTML format.

    9.0 uses 'sig-name descname cmdname' compound class names and wraps each
    character in its own <span class="pre">.  The standard CommandHTMLParser
    cannot match these spans, so we fall back to stripping all HTML tags from
    the main dt block and normalizing the result.
    """
    m = re.search(r'<dt[^>]*id="command:[^"]*"[^>]*>(.*?)</dt>', content, re.DOTALL)
    if not m:
        return ""
    dt_block = m.group(1)
    # Remove <a>...</a> entirely (range cross-reference links whose text we
    # do NOT want to keep — the link text repeats "range").
    clean = re.sub(r"<a[^>]*>.*?</a>", "", dt_block, flags=re.DOTALL)
    # Decode common HTML entities before stripping tags so that < / > survive.
    clean = clean.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    # Strip remaining HTML tags (but not < / > literal chars already decoded).
    text = re.sub(r"<[^>]+>", "", clean)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_command_name_from_h1(content: str) -> str:
    """Derive command name from h1 plain text (no fishcmd span in brick/rblock)."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL)
    if m:
        raw = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        return re.sub(r"\s+command\s*$", "", raw, flags=re.IGNORECASE).strip()
    return ""


# ---------------------------------------------------------------------------
# Parse a single HTML file; returns dict with parsed data or error
# ---------------------------------------------------------------------------


def parse_html_file(html_path: Path) -> dict:
    """Parse a command HTML file using CommandHTMLParser.

    Falls back to extracting command name / syntax from dt id / h1 plain text
    when the h1 has no fishcmd span (brick/rblock HTML structure), and uses a
    regex-based approach for PFC 9.0 files where span class names have changed.
    """
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)}

    parser = CommandHTMLParser()
    parser.feed(content)

    # command_name may be empty for brick/rblock (no fishcmd span in h1)
    command_name = parser.command_name
    if not command_name:
        command_name = _extract_command_name_from_h1(content)

    syntax = _cleanup_syntax(normalize_syntax(parser.command_syntax))
    # A syntax of only brackets (e.g. "[]") means the parser collected the
    # optional-range delimiters but not the command text — happens with PFC 9.0
    # HTML where span class names are compound ("sig-name descname cmdname").
    _syntax_stripped = syntax.replace("[", "").replace("]", "").strip()
    if not _syntax_stripped:
        # PFC 9.0 HTML uses different span class names; fall back to regex extraction
        syntax = _cleanup_syntax(_extract_900_syntax(content))

    keywords = []
    for keyword in parser.keywords:
        cleaned_keyword = dict(keyword)
        cleaned_keyword["syntax"] = _cleanup_keyword_syntax(cleaned_keyword.get("syntax", ""))
        keywords.append(cleaned_keyword)

    return {
        "command": command_name,
        "syntax": syntax,
        "keywords": keywords,
        "description": parser.description,
    }


def _cleanup_syntax(syntax: str) -> str:
    """Remove obvious internal fragments from command syntax."""
    syntax = syntax.replace("[rbmodblock]", "")
    syntax = syntax.replace("[<range>]", "[range]")
    syntax = syntax.replace("<range>", "range")
    syntax = syntax.replace("3D ONLY", "").replace("3D-only", "").replace("3D-ONLY", "")
    syntax = syntax.replace("2D ONLY", "").replace("2D-only", "").replace("2D-ONLY", "")
    syntax = syntax.replace("y- and z- components are", "")
    syntax = syntax.replace("z-components are", "")
    syntax = syntax.replace("`z`-components are", "")
    syntax = syntax.replace("z`-components are", "")
    syntax = syntax.replace("`z-components are", "")
    return normalize_syntax(syntax)


def _cleanup_keyword_syntax(syntax: str) -> str:
    """Remove obvious internal fragments from keyword syntax."""
    syntax = syntax.replace("[rbmodblock]", "")
    syntax = syntax.replace("[<range>]", "[range]")
    syntax = syntax.replace("<range>", "range")
    syntax = syntax.replace("3D ONLY", "").replace("3D-only", "").replace("3D-ONLY", "")
    syntax = syntax.replace("2D ONLY", "").replace("2D-only", "").replace("2D-ONLY", "")
    syntax = syntax.replace("y- and z- components are", "")
    syntax = syntax.replace("z-components are", "")
    syntax = syntax.replace("`z`-components are", "")
    syntax = syntax.replace("z`-components are", "")
    syntax = syntax.replace("`z-components are", "")
    return normalize_syntax(syntax)


# ---------------------------------------------------------------------------
# Collect all HTML files per version for a category
# ---------------------------------------------------------------------------


def collect_html_files(dirs: dict[str, Path], stem_to_key_fn) -> dict[str, dict[str, Path]]:
    """Return mapping: json_key -> {version: html_path}.

    Only includes files where stem_to_key_fn returns a non-None result.
    """
    result: dict[str, dict[str, Path]] = {}
    for version, html_dir in dirs.items():
        if not html_dir.exists():
            print(f"  [WARN] HTML dir not found for {version}: {html_dir}")
            continue
        for html_file in sorted(html_dir.glob("*.html")):
            mapping = stem_to_key_fn(html_file.stem)
            if mapping is None:
                continue
            json_key, _ = mapping
            result.setdefault(json_key, {})[version] = html_file
    return result


# ---------------------------------------------------------------------------
# Search keyword generators
# ---------------------------------------------------------------------------

_BRICK_KEYWORDS: dict[str, list[str]] = {
    "assemble": ["assemble", "activate", "place brick", "brick assembly"],
    "delete": ["delete brick", "remove brick", "brick deletion"],
    "export": ["export brick", "save brick", "brick file"],
    "import": ["import brick", "load brick", "brick file"],
    "make": ["make brick", "create brick geometry", "brick generation"],
    "inlet-create": ["inlet", "create inlet", "brick inlet", "particle generation", "flow"],
    "inlet-modify": ["inlet", "modify inlet", "update inlet", "brick inlet settings"],
}

_RBLOCK_SEARCH_KEYWORDS: dict[str, list[str]] = {
    "apply-facet-groups": ["apply facet groups", "rblock group facets", "facet group assignment"],
    "attribute": ["rblock attribute", "position", "velocity", "displacement", "rblock properties"],
    "clump": ["rblock clump", "convert rblock to clump", "clump replacement"],
    "configure": ["rblock configure", "bbm", "bond block model configuration"],
    "construct": ["construct rblock", "rblock assembly", "build rblock"],
    "contact-resolution": ["contact resolution", "rblock contact", "facet contact settings"],
    "create": ["create rblock", "single rblock creation", "rigid block"],
    "cut": ["cut rblock", "slice rblock", "rblock cutting"],
    "damping": ["rblock damping", "damping coefficient", "energy dissipation"],
    "delete": ["delete rblock", "remove rblock", "rblock deletion"],
    "densify": ["densify rblock", "rblock mesh densification", "facet refinement"],
    "dilate": ["dilate rblock", "rblock dilation", "block expansion"],
    "distribute": ["distribute rblock", "rblock packing", "fill domain"],
    "erode": ["erode rblock", "rblock erosion", "surface removal"],
    "export": ["export rblock", "save rblock", "rblock file output"],
    "extra": ["extra variable", "rblock extra", "user-defined variable"],
    "facet-apply": ["facet apply", "apply surface", "rblock facet contact"],
    "facet-apply-remove": ["facet apply remove", "remove facet contact", "rblock facet"],
    "facet-group": ["facet group", "rblock facet group", "surface group assignment"],
    "fix": ["fix rblock", "constrain rblock", "immobilize rblock"],
    "free": ["free rblock", "unfix rblock", "release constraint"],
    "generate": ["generate rblock", "rblock packing", "multiple rblocks"],
    "group": ["rblock group", "assign group", "group slot"],
    "hide": ["hide rblock", "rblock visibility", "display control"],
    "history": ["rblock history", "record property", "time history"],
    "import": ["import rblock", "load rblock", "rblock file input"],
    "initialize": ["initialize rblock", "set initial conditions", "rblock state"],
    "list": ["list rblock", "rblock information", "print properties"],
    "merge": ["merge rblock", "combine rblocks", "rblock merging"],
    "property": ["rblock property", "contact model property", "material property"],
    "refine": ["refine rblock", "mesh refinement", "rblock resolution"],
    "reflect": ["reflect rblock", "mirror rblock", "rblock symmetry"],
    "remap-interval": ["remap interval", "rblock remapping", "periodic boundary remap"],
    "replicate": ["replicate rblock", "copy rblock", "rblock duplication"],
    "result": ["rblock result", "output result", "rblock data export"],
    "rotate": ["rotate rblock", "rblock rotation", "orientation"],
    "scale": ["scale rblock", "rblock scaling", "resize rblock"],
    "select": ["select rblock", "rblock selection", "highlight rblock"],
    "template": ["rblock template", "template creation", "shape template"],
    "tolerance": ["rblock tolerance", "contact detection tolerance", "overlap tolerance"],
    "trace": ["rblock trace", "trace property", "monitor rblock"],
    "tractions": ["rblock tractions", "surface traction", "boundary force"],
}

_BRICK_DESCRIPTIONS: dict[str, str] = {
    "assemble": (
        "Assemble an existing brick in the model. If a range is specified, only elements "
        "falling in that range are activated."
    ),
    "delete": (
        "Delete bricks from the model. If a range is specified, only bricks falling within the range are deleted."
    ),
    "export": ("Export brick data to a file for later import or post-processing."),
    "import": ("Import brick data from a previously exported file."),
    "make": ("Create brick geometry by specifying a box region subdivided into elements for rigid body simulation."),
    "inlet-create": (
        "Create an inlet with the specified ID. An inlet uses data stored in a brick "
        "to generate bodies (balls, clumps, or rblocks) during cycling."
    ),
    "inlet-modify": ("Modify the properties of an existing inlet identified by ID."),
}

_RBLOCK_DESCRIPTIONS: dict[str, str] = {
    "apply-facet-groups": ("Apply group assignments to rblock facets based on contact or geometric criteria."),
    "attribute": ("Set kinematic attributes (position, velocity, displacement, spin) on rblocks within a range."),
    "clump": ("Convert selected rblocks into clump objects."),
    "configure": ("Configure rblock-specific model parameters such as bond-block model (BBM) settings."),
    "construct": ("Construct rblocks by assembling existing geometry or template data."),
    "contact-resolution": ("Control the contact detection resolution for rblock facets."),
    "create": (
        "Create a single rigid block (rblock) with specified geometry and attributes. "
        "A model domain must be configured before rblock creation."
    ),
    "cut": ("Cut rblocks along a plane or surface, splitting them into sub-blocks."),
    "damping": ("Set damping parameters for rblocks to control energy dissipation during cycling."),
    "delete": ("Delete rblocks from the model. If a range is specified, only rblocks within the range are removed."),
    "densify": ("Densify rblock surface meshes by subdividing facets to improve contact resolution."),
    "dilate": ("Apply dilation to rblock surfaces, expanding or contracting facet positions."),
    "distribute": (
        "Distribute rblocks throughout a domain region, similar to ball distribute, "
        "allowing overlap to achieve a target porosity."
    ),
    "erode": ("Erode rblock surface facets, removing material from surfaces based on criteria."),
    "export": ("Export rblock data to a file for later import or post-processing."),
    "extra": ("Set or modify extra (user-defined) variables on rblocks within a range."),
    "facet-apply": ("Apply contact surface properties to rblock facets."),
    "facet-apply-remove": ("Remove applied contact surface properties from rblock facets."),
    "facet-group": ("Assign group labels to rblock facets for contact model application and filtering."),
    "fix": ("Fix (constrain) rblock degrees of freedom to prevent motion during cycling."),
    "free": ("Free (release) previously fixed rblock degrees of freedom."),
    "generate": ("Generate multiple rblocks within a domain region using template-based packing."),
    "group": ("Assign rblocks to named groups (with optional slot) for range-based operations."),
    "hide": ("Hide rblocks from visualization without deleting them from the model."),
    "history": ("Record rblock properties over time for plotting and post-processing."),
    "import": ("Import rblock geometry from an external file (e.g., STL or rblock format)."),
    "initialize": ("Set initial state variables (stress, displacement, velocity) for rblocks."),
    "list": ("List rblock properties and state information to the console or a file."),
    "merge": ("Merge multiple rblocks into a single rigid body."),
    "property": ("Set contact model properties on rblock contacts within a range."),
    "refine": ("Refine rblock surface mesh resolution for improved contact accuracy."),
    "reflect": ("Reflect (mirror) rblocks about a specified plane."),
    "remap-interval": ("Set the interval at which rblock positions are remapped for periodic boundary conditions."),
    "replicate": ("Replicate existing rblocks to create copies at offset positions or orientations."),
    "result": ("Export or configure rblock result output for post-processing."),
    "rotate": ("Rotate rblocks about a specified axis and origin."),
    "scale": ("Scale rblock geometry by a specified factor."),
    "select": ("Select rblocks for interactive highlighting or subsequent operations."),
    "template": ("Create or manage rblock shape templates used for rblock generate operations."),
    "tolerance": ("Set tolerance parameters for rblock contact detection and overlap calculations."),
    "trace": ("Configure trace monitoring of rblock properties for debugging and analysis."),
    "tractions": ("Apply surface tractions (forces per unit area) to rblock facets."),
}


# ---------------------------------------------------------------------------
# Build the JSON for a single command
# ---------------------------------------------------------------------------


def build_command_json(
    json_key: str,
    category: str,
    version_files: dict[str, Path],
    all_versions: list[str],
    descriptions: dict[str, str],
    search_kw_map: dict[str, list[str]],
) -> dict:
    """Build a full command JSON dict by parsing each version's HTML."""
    versions = {}
    for ver in all_versions:
        html_path = version_files.get(ver)
        if html_path is None:
            versions[ver] = {"available": False}
        else:
            parsed = parse_html_file(html_path)
            if "error" in parsed:
                print(f"    [ERROR] {ver}: {parsed['error']}")
                versions[ver] = {"available": False}
            else:
                entry: dict = {}
                entry["command"] = parsed["command"] or f"{category} {json_key}"
                entry["syntax"] = parsed["syntax"]
                entry["keywords"] = parsed["keywords"]
                entry["examples"] = []
                versions[ver] = entry

    # Description: prefer parsed from any available version, else use fallback
    description = ""
    for ver in all_versions:
        v = versions.get(ver, {})
        if v.get("available") is not False:
            # Try to get from parsed (not stored in versions, use fallback map)
            break
    description = descriptions.get(json_key, "")

    return {
        "category": category,
        "description": description,
        "search_keywords": search_kw_map.get(json_key, [json_key, category]),
        "python_sdk_alternative": {
            "available": False,
            "workaround": f"Use itasca.command('{category} {json_key.replace('-', ' ')} ...') via command interface",
        },
        "versions": versions,
    }


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


def process_category(
    category: str,
    html_dirs: dict[str, Path],
    stem_to_key_fn,
    descriptions: dict[str, str],
    search_kw_map: dict[str, list[str]],
):
    cat_dir = COMMANDS_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    all_versions = ["6.0", "7.0", "9.0"]

    # Collect: json_key -> {version: html_path}
    version_files = collect_html_files(html_dirs, stem_to_key_fn)
    print(f"  Commands found: {sorted(version_files.keys())}")

    created = 0
    for json_key in sorted(version_files.keys()):
        json_path = cat_dir / f"{json_key}.json"
        data = build_command_json(
            json_key=json_key,
            category=category,
            version_files=version_files[json_key],
            all_versions=all_versions,
            descriptions=descriptions,
            search_kw_map=search_kw_map,
        )

        # Count keywords parsed
        kwd_counts = {
            ver: len(v.get("keywords", [])) for ver, v in data["versions"].items() if v.get("available") is not False
        }
        json_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"    {json_path.name}: {kwd_counts}")
        created += 1

    print(f"  => {created} files written to {cat_dir}")


def main():
    print("=== Brick and RBlock documentation parser ===\n")

    print("[brick]")
    process_category(
        category="brick",
        html_dirs=BRICK_COMMANDS_DIRS,
        stem_to_key_fn=html_stem_to_brick_key,
        descriptions=_BRICK_DESCRIPTIONS,
        search_kw_map=_BRICK_KEYWORDS,
    )
    print()

    print("[rblock]")
    process_category(
        category="rblock",
        html_dirs=RBLOCK_COMMANDS_DIRS,
        stem_to_key_fn=html_stem_to_rblock_key,
        descriptions=_RBLOCK_DESCRIPTIONS,
        search_kw_map=_RBLOCK_SEARCH_KEYWORDS,
    )
    print()
    print("Done.")


if __name__ == "__main__":
    main()
