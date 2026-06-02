from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from src.core.paths import DEFAULT_DB_PATH, LEGACY_DB_PATH, ROOT
from src.core.schema_integrity import check_schema_integrity
from src.db import init_db


UAT_BACKUP_DIR = ROOT / "backups" / "uat_v016"


def main() -> None:
    parser = argparse.ArgumentParser(description="v0.1.6 UAT DB helper for edu_tutor_system")
    parser.add_argument("command", choices=["init", "restore", "status"])
    args = parser.parse_args()
    if args.command == "init":
        init_uat_db()
    elif args.command == "restore":
        restore_latest()
    else:
        print_status()


def init_uat_db() -> None:
    if DEFAULT_DB_PATH.exists():
        backup_current()
        DEFAULT_DB_PATH.unlink()
    if LEGACY_DB_PATH.exists():
        print(f"legacy DB detected and left untouched: {LEGACY_DB_PATH}")
    init_db(DEFAULT_DB_PATH)
    print(f"initialized clean UAT DB: {DEFAULT_DB_PATH}")


def restore_latest() -> None:
    backups = sorted(UAT_BACKUP_DIR.glob("edu_tutor_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        raise SystemExit("no UAT backups found")
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backups[0], DEFAULT_DB_PATH)
    print(f"restored {backups[0]} -> {DEFAULT_DB_PATH}")


def print_status() -> None:
    init_db(DEFAULT_DB_PATH)
    print(f"current_db_path: {DEFAULT_DB_PATH}")
    if LEGACY_DB_PATH.exists():
        print(f"legacy_db_path: {LEGACY_DB_PATH} (deprecated, not runtime)")
    with sqlite3.connect(DEFAULT_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM schema_meta").fetchall()}
        print(f"schema_version: {meta.get('schema_version')}")
        for table in _tables(conn):
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            print(f"{table}: rows={count}; columns={','.join(columns)}")
    report = check_schema_integrity(DEFAULT_DB_PATH)
    print(f"schema_integrity: errors={len(report['errors'])}; warnings={len(report['warnings'])}; info={len(report['info'])}")


def backup_current() -> Path:
    UAT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = UAT_BACKUP_DIR / f"edu_tutor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DEFAULT_DB_PATH, target)
    print(f"backed up current edu_tutor.db: {target}")
    return target


def _tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [row["name"] for row in rows]


if __name__ == "__main__":
    main()
