from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from src.core.duplicate_guard import detect_duplicate_mistakes
from src.core.rule_registry import RuleRegistry, load_rule_registry
from src.db import now_iso
from src.schemas.mistake_schema import (
    DEFAULT_CREATED_BY_USER_ID,
    DEFAULT_STUDENT_ID,
    DEFAULT_TENANT_ID,
    ValidationReport,
)


def load_mistakes_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_mistakes_payload(
    payload: dict[str, Any],
    registry: RuleRegistry | None = None,
) -> tuple[ValidationReport, list[dict[str, Any]]]:
    registry = registry or load_rule_registry()
    question_types = set(registry.get_question_type_codes())
    knowledge_points = set(registry.get_knowledge_point_codes())
    mistake_tags = set(registry.get_mistake_tag_codes())
    difficulties = set(registry.get_difficulty_codes())
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
        if row.get("question_type") not in question_types:
            report.add_error("invalid_question_type", "question_type is not supported", idx)
            item_errors += 1
        if row.get("mistake_tag") not in mistake_tags:
            report.add_error("invalid_mistake_tag", "mistake_tag must be one of the 24 core tags", idx)
            item_errors += 1
        if row.get("difficulty") not in difficulties:
            report.add_error("invalid_difficulty", "difficulty is not supported", idx)
            item_errors += 1
        if not row.get("question_summary"):
            report.add_error("empty_question_summary", "question_summary must not be empty", idx)
            item_errors += 1
        if row.get("knowledge_point") not in knowledge_points:
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
    if report.errors:
        return report.as_dict()
    report.imported_count = _insert_mistake_rows(conn, valid_rows, tenant_id, student_id, created_by_user_id)
    return report.as_dict()


def import_mistakes_file(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    return import_mistakes_payload(conn, load_mistakes_yaml(path))


def preview_mistakes_payload(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    student_id: str = DEFAULT_STUDENT_ID,
) -> dict[str, Any]:
    report, valid_rows = validate_mistakes_payload(payload)
    duplicate_scan = detect_duplicate_mistakes(conn, valid_rows, default_student_id=student_id) if not report.errors else {
        "total_count": len(valid_rows),
        "new_count": 0,
        "duplicate_count": 0,
        "new_indices": [],
        "duplicate_indices": [],
        "duplicates": [],
        "incoming_hashes": [],
    }
    total_count = len(payload.get("mistakes", [])) if isinstance(payload.get("mistakes"), list) else 0
    return {
        "source_type": "mistakes",
        "valid": not report.errors,
        "validation": report.as_dict(),
        "valid_rows": valid_rows,
        "total_count": total_count,
        "valid_count": len(valid_rows),
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "duplicate_scan": duplicate_scan,
        "duplicate_count": duplicate_scan["duplicate_count"],
        "new_count": duplicate_scan["new_count"],
        "will_import_count": duplicate_scan["new_count"] if not report.errors else 0,
        "will_skip_count": report.skipped_count + duplicate_scan["duplicate_count"],
    }


def confirm_mistakes_import(
    conn: sqlite3.Connection,
    preview: dict[str, Any],
    duplicate_strategy: str = "only_new",
    tenant_id: str = DEFAULT_TENANT_ID,
    student_id: str = DEFAULT_STUDENT_ID,
    created_by_user_id: str = DEFAULT_CREATED_BY_USER_ID,
) -> dict[str, Any]:
    report = dict(preview.get("validation") or {})
    if not preview.get("valid") or report.get("errors"):
        report.update({
            "imported_count": 0,
            "duplicate_count": preview.get("duplicate_count", 0),
            "skipped_duplicate_count": 0,
        })
        return report

    valid_rows = list(preview.get("valid_rows") or [])
    duplicate_scan = preview.get("duplicate_scan") or {}
    duplicate_indices = set(duplicate_scan.get("duplicate_indices") or [])
    if duplicate_strategy in {"cancel", "取消导入"}:
        rows_to_import: list[dict[str, Any]] = []
        skipped_duplicate_count = len(duplicate_indices)
    elif duplicate_strategy in {"import_all", "仍然导入全部"}:
        rows_to_import = valid_rows
        skipped_duplicate_count = 0
    elif duplicate_strategy in {"only_new", "skip_duplicates", "skip_all_duplicates", "只导入非重复", "跳过全部重复"}:
        rows_to_import = [row for idx, row in enumerate(valid_rows) if idx not in duplicate_indices]
        skipped_duplicate_count = len(duplicate_indices)
    else:
        raise ValueError(f"Unsupported duplicate strategy: {duplicate_strategy}")

    imported_count = _insert_mistake_rows(conn, rows_to_import, tenant_id, student_id, created_by_user_id)
    report.update({
        "valid": True,
        "imported_count": imported_count,
        "duplicate_count": duplicate_scan.get("duplicate_count", 0),
        "skipped_duplicate_count": skipped_duplicate_count,
        "skipped_count": int(report.get("skipped_count", 0)) + skipped_duplicate_count,
    })
    return report


def list_mistakes(conn: sqlite3.Connection, include_unconfirmed: bool = True) -> list[dict[str, Any]]:
    sql = "SELECT * FROM mistakes"
    params: tuple[Any, ...] = ()
    if not include_unconfirmed:
        sql += " WHERE status = ?"
        params = ("confirmed",)
    sql += " ORDER BY date DESC, id DESC"
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _insert_mistake_rows(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
    tenant_id: str,
    default_student_id: str,
    created_by_user_id: str,
) -> int:
    ts = now_iso()
    imported_count = 0
    for row in rows:
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
                row.get("student_id") or default_student_id,
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
        imported_count += 1
    conn.commit()
    return imported_count
