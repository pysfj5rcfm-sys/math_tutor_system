from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from src.core.mistake_tags import TAG_CODES
from src.db import now_iso
from src.schemas.mistake_schema import (
    DEFAULT_CREATED_BY_USER_ID,
    DEFAULT_STUDENT_ID,
    DEFAULT_TENANT_ID,
    DIFFICULTIES,
    KNOWLEDGE_POINTS,
    QUESTION_TYPES,
    ValidationReport,
)


def load_mistakes_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_mistakes_payload(payload: dict[str, Any]) -> tuple[ValidationReport, list[dict[str, Any]]]:
    report = ValidationReport()
    rows = payload.get("mistakes")
    if not isinstance(rows, list):
        report.add_error("invalid_mistakes_root", "mistakes must be a list")
        return report, []

    valid_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            report.add_error("invalid_item", "Each mistake must be a mapping", idx)
            report.skipped_count += 1
            continue
        item_errors = 0
        if not row.get("date"):
            report.add_error("missing_date", "date is required", idx)
            item_errors += 1
        if row.get("question_type") not in QUESTION_TYPES:
            report.add_error("invalid_question_type", "question_type is not supported", idx)
            item_errors += 1
        if row.get("mistake_tag") not in TAG_CODES:
            report.add_error("invalid_mistake_tag", "mistake_tag must be one of the 24 core tags", idx)
            item_errors += 1
        if row.get("difficulty") not in DIFFICULTIES:
            report.add_error("invalid_difficulty", "difficulty is not supported", idx)
            item_errors += 1
        if not row.get("question_summary"):
            report.add_error("empty_question_summary", "question_summary must not be empty", idx)
            item_errors += 1
        if row.get("knowledge_point") not in KNOWLEDGE_POINTS:
            report.add_warning("unknown_knowledge_point", "knowledge_point is not in initial values; imported as needs_confirmation", idx)
        if item_errors:
            report.skipped_count += 1
            continue
        valid_rows.append(row)

    report.valid = not report.errors
    return report, valid_rows


def import_mistakes_payload(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    tenant_id: str = DEFAULT_TENANT_ID,
    student_id: str = DEFAULT_STUDENT_ID,
    created_by_user_id: str = DEFAULT_CREATED_BY_USER_ID,
) -> dict[str, Any]:
    report, valid_rows = validate_mistakes_payload(payload)
    ts = now_iso()
    for row in valid_rows:
        conn.execute(
            """
            INSERT INTO mistakes (
                tenant_id, student_id, date, question_type, knowledge_point,
                mistake_tag, difficulty, question_summary, wrong_answer_summary,
                correct_answer_summary, training_needed, source, note, status,
                created_by_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'needs_confirmation', ?, ?, ?)
            """,
            (
                tenant_id,
                student_id,
                row["date"],
                row["question_type"],
                row.get("knowledge_point", ""),
                row["mistake_tag"],
                row["difficulty"],
                row["question_summary"],
                row.get("wrong_answer_summary", ""),
                row.get("correct_answer_summary", ""),
                1 if row.get("training_needed", True) else 0,
                row.get("source", "GPT批改"),
                row.get("note", ""),
                created_by_user_id,
                ts,
                ts,
            ),
        )
        report.imported_count += 1
    conn.commit()
    return report.as_dict()


def import_mistakes_file(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    return import_mistakes_payload(conn, load_mistakes_yaml(path))


def list_mistakes(conn: sqlite3.Connection, include_unconfirmed: bool = True) -> list[dict[str, Any]]:
    sql = "SELECT * FROM mistakes"
    params: tuple[Any, ...] = ()
    if not include_unconfirmed:
        sql += " WHERE status = ?"
        params = ("confirmed",)
    sql += " ORDER BY date DESC, id DESC"
    return [dict(row) for row in conn.execute(sql, params).fetchall()]
