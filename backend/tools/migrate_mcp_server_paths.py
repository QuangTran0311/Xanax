"""Move absolute MCP server paths in skill configs after the backend split.

The script is preview-only by default. Pass ``--apply`` to create a database
backup and update matching ``skills.config_json`` values in one transaction.

    python tools/migrate_mcp_server_paths.py
    python tools/migrate_mcp_server_paths.py --apply
"""
from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "xanax.db"
OLD_MCP_DIR = BACKEND_DIR.parent / "mcp_servers"
NEW_MCP_DIR = BACKEND_DIR / "mcp_servers"


@dataclass(frozen=True)
class Change:
    skill_id: int
    name: str
    config_json: str
    updated_json: str
    occurrences: int


def _path_pattern(path: Path) -> re.Pattern[str]:
    """Match plain or JSON-escaped absolute paths with either separator."""
    parts = path.resolve().parts
    return re.compile(r"[\\/]+".join(re.escape(part.rstrip("\\/")) for part in parts), re.I)


def _replacement_for(match: re.Match[str]) -> str:
    matched = match.group(0)
    replacement = str(NEW_MCP_DIR.resolve())
    if "/" in matched and "\\" not in matched:
        return NEW_MCP_DIR.resolve().as_posix()
    if "\\\\" in matched:
        return replacement.replace("\\", "\\\\")
    return replacement


def find_changes(connection: sqlite3.Connection) -> list[Change]:
    pattern = _path_pattern(OLD_MCP_DIR)
    changes: list[Change] = []
    for skill_id, name, config_json in connection.execute(
        "SELECT id, name, config_json FROM skills ORDER BY id"
    ):
        raw = config_json or ""
        updated, count = pattern.subn(_replacement_for, raw)
        if count:
            changes.append(Change(skill_id, name, raw, updated, count))
    return changes


def migrate(*, apply: bool) -> int:
    if not DB_PATH.is_file():
        print(f"Database not found: {DB_PATH}")
        return 1

    with sqlite3.connect(DB_PATH) as connection:
        changes = find_changes(connection)
        if not changes:
            print("No legacy MCP server paths found; nothing to change.")
            return 0

        total = sum(change.occurrences for change in changes)
        print(f"Found {total} path occurrence(s) in {len(changes)} skill(s):")
        for change in changes:
            print(f"  - #{change.skill_id} '{change.name}': {change.occurrences}")

        if not apply:
            print("\nPreview only; database was not changed. Run again with --apply.")
            return 0

        backup = DB_PATH.with_name(
            f"{DB_PATH.name}.bak_before_mcp_path_{datetime.now():%Y%m%d_%H%M%S}"
        )
        shutil.copy2(DB_PATH, backup)
        print(f"\nDatabase backup created: {backup.name}")

        try:
            connection.execute("BEGIN IMMEDIATE")
            for change in changes:
                connection.execute(
                    "UPDATE skills SET config_json = ? WHERE id = ? AND config_json = ?",
                    (change.updated_json, change.skill_id, change.config_json),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        remaining = find_changes(connection)
        if remaining:
            print("Migration verification failed; restore the database backup.")
            return 1

    print(f"Updated MCP paths to: {NEW_MCP_DIR.resolve()}")
    print("Verification passed: no legacy paths remain.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="backup and update the database")
    args = parser.parse_args()
    return migrate(apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
