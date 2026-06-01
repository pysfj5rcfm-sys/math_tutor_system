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

__all__ = [
    "load_mistakes_yaml",
    "validate_mistakes_payload",
    "import_mistakes_payload",
    "import_mistakes_file",
    "preview_mistakes_payload",
    "confirm_mistakes_import",
    "list_mistakes",
]


def load_mistakes_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_mistakes_payload(
    payload: dict[str, Any],
    registry: RuleRegistry | None = None,
) -> tuple[ValidationReport, list[dict[str, Any]]]:
    registry = registry or load_rule_registry()
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
        context = _context_for_row(registry, payload, row, report, idx)
        if context is None:
            report.skipped_count += 1
            continue
        subject_id = context["subject_id"]
        question_types = set(registry.get_question_type_values_for_subject(subject_id))
        mistake_tags = {item["code"] for item in registry.get_mistake_tags_for_subject(subject_id)}
        normalized_row = _apply_context(row, context)
        item_errors = 0
        if not normalized_row.get("date"):
            report.add_error("missing_date", "date is required", idx)
            item_errors += 1
        if normalized_row.get("question_type") not in question_types:
            report.add_error("invalid_question_type", "question_type is not supported", idx)
            item_errors += 1
        if normalized_row.get("mistake_tag") not in mistake_tags:
            report.add_error("invalid_mistake_tag", "mistake_tag must be valid for the current subject", idx)
            item_errors += 1
        if normalized_row.get("difficulty") not in difficulties:
            report.add_error("invalid_difficulty", "difficulty is not supported", idx)
            item_errors += 1
        if not normalized_row.get("question_summary"):
            report.add_error("empty_question_summary", "question_summary must not be empty", idx)
            item_errors += 1
        knowledge_point_result = registry.validate_knowledge_point_for_context(
            normalized_row.get("knowledge_point"),
            subject_id,
            context["grade_at_time"],
            context["curriculum_version_at_time"],
        )
        if knowledge_point_result["ambiguous"]:
            report.add_warning("ambiguous_knowledge_point", "knowledge_point matches multiple items in current curriculum scope", idx)
        elif not knowledge_point_result["valid"]:
            report.add_warning("unknown_knowledge_point", "knowledge_point is not in initial values; imported as needs_confirmation", idx)
        if item_errors:
            report.skipped_count += 1
            continue
        valid_rows.append(normalized_row)

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
                subject_id, grade_at_time, term_at_time, curriculum_version_at_time,
                created_by_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'needs_confirmation', ?, ?, ?, ?, ?, ?, ?)
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
                row.get("subject_id"),
                row.get("grade_at_time"),
                row.get("term_at_time"),
                row.get("curriculum_version_at_time"),
                created_by_user_id,
                ts,
                ts,
            ),
        )
        imported_count += 1
    conn.commit()
    return imported_count


def _context_for_row(
    registry: RuleRegistry,
    payload: dict[str, Any],
    row: dict[str, Any],
    report: ValidationReport,
    idx: int,
) -> dict[str, Any] | None:
    student_id = row.get("student_id") or payload.get("student_id")
    subject_id = row.get("subject_id") or payload.get("subject_id")
    try:
        context = registry.resolve_learning_context(student_id=student_id, subject_id=subject_id)
    except Exception as exc:
        report.add_error("invalid_learning_context", str(exc), idx)
        return None
    for source in (payload, row):
        if source.get("grade_at_time"):
            context["grade_at_time"] = int(source["grade_at_time"])
            context["grade_display_name"] = registry.get_grade_display_name(context["grade_at_time"])
            stage = registry.get_stage_for_grade(context["grade_at_time"])
            context["stage_id"] = str(stage.get("stage_id", ""))
            context["stage_name"] = str(stage.get("name", ""))
        if source.get("term_at_time"):
            context["term_at_time"] = str(source["term_at_time"])
        if source.get("curriculum_version_at_time"):
            context["curriculum_version_at_time"] = str(source["curriculum_version_at_time"])
    return context


def _apply_context(row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for field, value in {
        "student_id": context["student_id"],
        "subject_id": context["subject_id"],
        "grade_at_time": context["grade_at_time"],
        "term_at_time": context["term_at_time"],
        "curriculum_version_at_time": context["curriculum_version_at_time"],
    }.items():
        if not result.get(field):
            result[field] = value
    return result
