from __future__ import annotations

import sqlite3
from pathlib import Path

from src.core.worksheets import get_worksheet_bundle, import_worksheet_file, import_worksheet_payload
from src.render.html_renderer import save_answer_sheet_html, save_worksheet_html


def import_worksheet_from_file(conn: sqlite3.Connection, path: str | Path) -> tuple[dict, int | None]:
    return import_worksheet_file(conn, path)


def import_worksheet_from_payload(conn: sqlite3.Connection, payload: dict) -> tuple[dict, int | None]:
    return import_worksheet_payload(conn, payload)


def export_worksheet_and_answer(conn: sqlite3.Connection, worksheet_id: int) -> tuple[Path, Path]:
    bundle = get_worksheet_bundle(conn, worksheet_id)
    return save_worksheet_html(bundle), save_answer_sheet_html(bundle)
