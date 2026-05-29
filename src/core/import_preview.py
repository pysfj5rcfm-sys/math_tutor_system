from __future__ import annotations

import sqlite3
from typing import Any

from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload
from src.core.sample_guard import detect_sample_data_warning
from src.core.worksheets import confirm_worksheet_import, preview_worksheet_payload
from src.core.yaml_utils import safe_parse_yaml


def dry_run_mistakes_yaml(conn: sqlite3.Connection, text: str, file_name: str | None = None) -> dict[str, Any]:
    parse_result = safe_parse_yaml(text)
    if not parse_result.ok:
        return {
            "source_type": "mistakes",
            "stage": "parse",
            "can_import": False,
            "parse": parse_result.as_dict(),
            "sample_warning": detect_sample_data_warning(file_name=file_name, text=text),
            "validation": None,
            "duplicate_scan": None,
            "payload": None,
            "valid_rows": [],
        }
    payload = parse_result.payload if isinstance(parse_result.payload, dict) else {}
    preview = preview_mistakes_payload(conn, payload)
    preview.update({
        "stage": "preview",
        "can_import": preview["valid"],
        "parse": parse_result.as_dict(),
        "sample_warning": detect_sample_data_warning(file_name=file_name, payload=payload),
        "payload": payload,
        "original_text": text,
    })
    return preview


def confirm_mistakes_dry_run(
    conn: sqlite3.Connection,
    preview: dict[str, Any],
    duplicate_strategy: str = "only_new",
) -> dict[str, Any]:
    return confirm_mistakes_import(conn, preview, duplicate_strategy=duplicate_strategy)


def dry_run_worksheet_yaml(conn: sqlite3.Connection, text: str, file_name: str | None = None) -> dict[str, Any]:
    parse_result = safe_parse_yaml(text)
    if not parse_result.ok:
        return {
            "source_type": "worksheet",
            "stage": "parse",
            "can_import": False,
            "parse": parse_result.as_dict(),
            "sample_warning": detect_sample_data_warning(file_name=file_name, text=text),
            "validation": None,
            "duplicate_scan": None,
            "payload": None,
            "worksheet": None,
        }
    payload = parse_result.payload if isinstance(parse_result.payload, dict) else {}
    preview = preview_worksheet_payload(conn, payload)
    preview.update({
        "stage": "preview",
        "can_import": preview["valid"],
        "parse": parse_result.as_dict(),
        "sample_warning": detect_sample_data_warning(file_name=file_name, payload=payload),
        "payload": payload,
        "original_text": text,
    })
    return preview


def confirm_worksheet_dry_run(
    conn: sqlite3.Connection,
    preview: dict[str, Any],
    duplicate_strategy: str = "skip_duplicate",
) -> tuple[dict[str, Any], int | None]:
    return confirm_worksheet_import(conn, preview, duplicate_strategy=duplicate_strategy)
