#!/usr/bin/env python3
"""Migrate command JSON files from flat schema to versioned schema.

Moves version-specific fields (command, syntax, keywords, examples) into
a "versions" dict keyed by PFC version string. All other fields remain
at the top level.

Usage:
    python migrate_to_versioned.py [--dry-run]
"""

import json
import sys
from pathlib import Path

VERSION = "7.0"
VERSIONED_FIELDS = {"command", "syntax", "keywords", "examples"}


def migrate_file(path: Path, dry_run: bool = False) -> bool:
    """Migrate a single JSON file. Returns True if file was changed."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Already migrated?
    if "versions" in data:
        return False

    version_data = {k: data.pop(k) for k in VERSIONED_FIELDS if k in data}
    data["versions"] = {VERSION: version_data}

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return True


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    commands_dir = Path(__file__).parent / "commands"

    changed = 0
    skipped = 0
    errors = 0

    for path in sorted(commands_dir.rglob("*.json")):
        try:
            if migrate_file(path, dry_run):
                changed += 1
                if dry_run:
                    print(f"  would migrate: {path.relative_to(commands_dir)}")
            else:
                skipped += 1
        except Exception as e:
            print(f"ERROR {path}: {e}")
            errors += 1

    label = "[DRY RUN] " if dry_run else ""
    print(f"{label}Done: {changed} migrated, {skipped} already versioned, {errors} errors")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
