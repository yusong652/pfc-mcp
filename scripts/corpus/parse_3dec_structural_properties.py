"""Generate the 3DEC ``structural-properties`` reference category.

Structural elements (SELs) are not in the 3DEC command corpus, but their property
command pages ship under ``common/sel/.../cmd_structure.<type>.property.html``
(the shared SEL kernel, same Sphinx command-page format). This parses the
per-type property keyword tables into one reference item per SEL type that 3DEC
exposes (beam, cable, geogrid, liner, pile, shell), dropping 2D-only keywords
since 3DEC is 3D. Property keywords/descriptions/types come straight from those
pages — nothing is hand-invented.

Output (3DEC-local):
    3dec/references/index.json                        (top index, category entry)
    3dec/references/structural-properties/index.json  (category index)
    3dec/references/structural-properties/<type>.json (one per SEL type)

Usage:
    uv run python scripts/corpus/parse_3dec_structural_properties.py
"""

import html
import json
import re
from pathlib import Path
from typing import Any

SEL = Path("C:/Program Files/Itasca/ItascaSoftware900/exe64/doc/common/sel/doc/manual/sel_manual")
SRC_BASE = "https://docs.itascacg.com/itasca900/common/sel/doc/manual/sel_manual"
OUT = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources/3dec/references")
CAT_DIR = OUT / "structural-properties"

# SEL types 3DEC exposes (itasca.structure: Beam/Cable/Geogrid/Liner/Pile/Shell).
TYPES = {
    "beam": ("beams", "Beam"),
    "cable": ("cables", "Cable"),
    "geogrid": ("geogrids", "Geogrid"),
    "liner": ("liners", "Liner"),
    "pile": ("piles", "Pile"),
    "shell": ("shells", "Shell"),
}
TYPE_MAP = {"f": "FLT", "v": "VEC", "i": "INT", "b": "BOOL", "s": "STR"}


def _txt(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", s))).strip()


def _despace(s: str) -> str:
    return re.sub(r"\s+", "", html.unescape(re.sub("<[^>]+>", "", s))).lower()


def _parse_type(stem: str) -> dict[str, Any]:
    plural, cls = TYPES[stem]
    page = SEL / plural / "commands" / f"cmd_structure.{stem}.property.html"
    h = page.read_text(encoding="utf-8")
    pairs = re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", h, re.S)

    keywords: list[str] = []
    for _dt, dd in pairs:
        m = re.search(r"Primary keywords:\s*([a-z0-9 \-]+)", _txt(dd))
        if m:
            keywords = m.group(1).split()
            break

    props = []
    for kw in keywords:
        matched = False
        for dt, dd in pairs:
            ds = _despace(dt)
            if not ds.startswith(kw.lower()):
                continue
            rest = ds[len(kw) :]
            # Guard against prefix collisions (kw 'moi' vs dt 'moi-y'): the char
            # right after the keyword must be a type letter or '(' (or nothing).
            if rest and rest[0] not in "fvibs(":
                continue
            matched = True
            if "(2donly)" in rest:  # 3DEC is 3D — drop 2D-only keywords
                break
            entry: dict[str, Any] = {"keyword": kw, "description": _txt(dd), "type": TYPE_MAP.get(rest[:1], "FLT")}
            if "(3donly)" in rest:
                entry["dim"] = "3D"
            props.append(entry)
            break
        if not matched:
            # Listed in "Primary keywords" but defined centrally (shared SEL
            # elastic/section property, e.g. cross-sectional-area / young / poisson).
            props.append({"keyword": kw, "description": "", "type": "FLT"})

    return {
        "name": stem,
        "dimension": "3D",
        "full_name": f"{cls} Structural-Element Properties",
        "description": (
            f"Property keywords for the 3DEC {cls.lower()} structural element. Assign with "
            f"'structure {stem} create ...', set elastic behavior with 'structure {stem} cmodel ...', "
            f"then set these with 'structure {stem} property <keyword> <value> [range ...]'."
        ),
        "primary_commands": [
            f"structure {stem} create",
            f"structure {stem} cmodel",
            f"structure {stem} property",
            f"structure {stem} list",
        ],
        "property_groups": [
            {
                "name": "Properties",
                "description": f"'structure {stem} property' keywords (2D-only keywords omitted; 3DEC is 3D).",
                "properties": props,
            }
        ],
        "source": f"{SRC_BASE}/{plural}/commands/cmd_structure.{stem}.property.html",
    }


def main() -> None:
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = []
    for stem in TYPES:
        item = _parse_type(stem)
        n = len(item["property_groups"][0]["properties"])
        if n == 0:
            raise SystemExit(f"{stem}: no properties parsed — check the source page.")
        (CAT_DIR / f"{stem}.json").write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", "utf-8")
        catalog.append({"name": stem, "file": f"{stem}.json", "full_name": item["full_name"], "property_count": n})
        print(f"  {stem:8} properties={n}")

    (CAT_DIR / "index.json").write_text(
        json.dumps(
            {
                "type": "structural_element_properties",
                "description": (
                    "Structural-element (SEL) property keyword reference for 3DEC — beam, cable, geogrid, liner, "
                    "pile, shell. Property vocabulary for 'structure <type> property'. Elastic moduli are set via "
                    "'structure <type> cmodel'. Parsed from the shared SEL command docs; 2D-only keywords omitted."
                ),
                "models": catalog,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        "utf-8",
    )

    top_path = OUT / "index.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top.setdefault("categories", {})["structural-properties"] = {
        "name": "Structural-Element Properties",
        "description": (
            "3DEC structural-element property keywords — beam, cable, geogrid, liner, pile, shell. Vocabulary "
            "for 'structure <type> property' (elastic behavior via 'structure <type> cmodel')."
        ),
        "directory": "structural-properties",
        "index_file": "structural-properties/index.json",
        "summary": f"{len(catalog)} 3DEC SEL types (beam/cable/geogrid/liner/pile/shell) — 'structure <type> property' keywords",
        "usage": "structure <type> create ... ; structure <type> cmodel ... ; structure <type> property <kw> <value> [range ...]",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"\nWrote {CAT_DIR} ({len(catalog)} SEL types)")


if __name__ == "__main__":
    main()
