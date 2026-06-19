"""Wire range-elements references to a shared _common pool (PFC + FLAC + 3DEC).

Range elements (geometric/logical ``range ...`` filters: cylinder, sphere, plane,
position, group, id, ...) are a 9.0 kernel shared by every engine; their docs
live under ``common/`` in the product tree and were byte-identical across PFC and
FLAC. The item JSONs have been moved to ``_common/references/range-elements/``
(one copy); this script repoints each engine's category index there, the same
``_common`` borrow pattern command docs and zone constitutive-models already use.

Per-engine locals are preserved:
- PFC keeps ``contact`` (range by ball contact type — PFC-only) and ``sphere``
  (PFC adds a "ball" search keyword) as local item files.
- FLAC and 3DEC borrow all 22 shared elements from ``_common``.

Usage:
    uv run python scripts/corpus/wire_common_range_elements.py
"""

import json
from pathlib import Path

RES = Path("C:/Dev/Han/pfc-mcp/src/itasca_mcp/knowledge/resources")
COMMON_REL = "_common/references/range-elements"
COMMON_DIR = RES / COMMON_REL

# Items each engine keeps as a local (non-borrowed) file.
PFC_LOCAL = {"contact", "sphere"}


def _repoint(index_path: Path, local: set[str]) -> int:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    n = 0
    for el in data["elements"]:
        name = el["name"]
        if name in local:
            el["file"] = f"{name}.json"  # keep local
        else:
            el["file"] = f"{COMMON_REL}/{name}.json"
            n += 1
    index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return n


def main() -> None:
    common_items = {p.stem for p in COMMON_DIR.glob("*.json")}

    # 1. FLAC: borrow all (no locals).
    flac_idx = RES / "flac/references/range-elements/index.json"
    nf = _repoint(flac_idx, local=set())

    # 2. PFC: borrow all except its locals (contact, sphere).
    pfc_idx = RES / "pfc/references/range-elements/index.json"
    npfc = _repoint(pfc_idx, local=PFC_LOCAL)

    # 3. 3DEC: clone FLAC's (now-_common-pointing) index; all 22 are kernel.
    tdec_dir = RES / "3dec/references/range-elements"
    tdec_dir.mkdir(parents=True, exist_ok=True)
    flac_data = json.loads(flac_idx.read_text(encoding="utf-8"))
    # sanity: every borrowed element exists in _common
    missing = [e["name"] for e in flac_data["elements"] if e["name"] not in common_items]
    if missing:
        raise SystemExit(f"range elements missing from _common: {missing}")
    (tdec_dir / "index.json").write_text(json.dumps(flac_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 4. Register category in 3DEC top references index.
    top_path = RES / "3dec/references/index.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    top.setdefault("categories", {})["range-elements"] = {
        "name": "Range Elements",
        "description": (
            "Geometric and logical 'range ...' filters (cylinder, sphere, plane, position, group, id, "
            "polygon, union, not, ...) used to scope any 3DEC command. Shared 9.0 kernel."
        ),
        "directory": "range-elements",
        "index_file": "range-elements/index.json",
        "summary": f"{len(flac_data['elements'])} range filter elements (shared 9.0 kernel via _common)",
        "usage": "<any command> ... range <element> <args> [union|intersect|not ...]",
    }
    top_path.write_text(json.dumps(top, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"_common range-elements pool: {len(common_items)}")
    print(f"FLAC repointed: {nf}  | PFC repointed: {npfc} (locals kept: {sorted(PFC_LOCAL)})")
    print(f"3DEC registered: {len(flac_data['elements'])} elements")


if __name__ == "__main__":
    main()
