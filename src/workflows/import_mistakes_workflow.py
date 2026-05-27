from __future__ import annotations

import sqlite3
from pathlib import Path

from src.core.mistakes import import_mistakes_file, import_mistakes_payload


def import_mistakes_from_file(conn: sqlite3.Connection, path: str | Path) -> dict:
    return import_mistakes_file(conn, path)


def import_mistakes_from_payload(conn: sqlite3.Connection, payload: dict) -> dict:
    return import_mistakes_payload(conn, payload)
