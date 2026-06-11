from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from typing import Any

import yaml

from src.core.current_student import get_current_student_id
from src.core.duplicate_guard import detect_duplicate_mistakes, mistake_hash
from src.core.normalization import normalize_mistake_row
from src.core.rule_registry import RuleRegistry, load_rule_registry
from src.db import now_iso
from src.schemas.mistake_schema import ValidationReport

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
        normalized, errors, warnings = normalize_mistake_row(row, payload, idx, registry)
        report.errors.extend(errors)
        report.warnings.extend(warnings)
        if normalized is None:
            report.skipped_count += 1
            report.valid = False
            continue
        valid_rows.append(normalized)

    report.valid = not report.errors
    return report, valid_rows


def import_mistakes_payload(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    preview = preview_mistakes_payload(conn, payload)
    return confirm_mistakes_import(conn, preview, duplicate_strategy="import_all")


def import_mistakes_file(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    return import_mistakes_payload(conn, load_mistakes_yaml(path))


def preview_mistakes_payload(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    student_id: str | None = None,
) -> dict[str, Any]:
    report, valid_rows = validate_mistakes_payload(payload)
    default_student_id = student_id or get_current_student_id()
    duplicate_scan = detect_duplicate_mistakes(conn, valid_rows, default_student_id=default_student_id) if not report.errors else {
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
        "normalization": {"rows": valid_rows, "warnings": report.warnings},
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
    tenant_id: str | None = None,
    student_id: str | None = None,
    created_by_user_id: str | None = None,
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
    if duplicate_strategy == "cancel":
        rows_to_import: list[dict[str, Any]] = []
        skipped_duplicate_count = len(duplicate_indices)
    elif duplicate_strategy == "import_all":
        rows_to_import = valid_rows
        skipped_duplicate_count = 0
    elif duplicate_strategy in {"only_new", "skip_duplicates", "skip_all_duplicates"}:
        rows_to_import = [row for idx, row in enumerate(valid_rows) if idx not in duplicate_indices]
        skipped_duplicate_count = len(duplicate_indices)
    else:
        raise ValueError(f"Unsupported duplicate strategy: {duplicate_strategy}")

    import_batch_id = _create_import_batch(conn, "mistakes", rows_to_import, preview, skipped_duplicate_count)
    imported_count = _insert_mistake_rows(conn, rows_to_import, import_batch_id)
    _finish_import_batch(conn, import_batch_id, imported_count, skipped_duplicate_count)
    report.update({
        "valid": True,
        "imported_count": imported_count,
        "duplicate_count": duplicate_scan.get("duplicate_count", 0),
        "skipped_duplicate_count": skipped_duplicate_count,
        "skipped_count": int(report.get("skipped_count", 0)) + skipped_duplicate_count,
        "import_batch_id": import_batch_id,
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
    import_batch_id: int | None,
) -> int:
    ts = now_iso()
    imported_count = 0
    for row in rows:
        row_hash = mistake_hash(row)
        conn.execute(
            """
            INSERT INTO mistakes (
                student_id, subject_id, grade_at_time, term_at_time,
                curriculum_version_at_time, textbook_version_at_time, date,
                question_type_code, knowledge_point_id, primary_mistake_tag_code,
                difficulty_code, question_summary, wrong_answer_summary,
                correct_answer_summary, training_needed, diagnosis_confidence,
                needs_human_review, secondary_mistake_tags_json,
                diagnosis_evidence_json, alternative_diagnoses_json,
                source, status,
                import_batch_id, record_hash, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'needs_confirmation', ?, ?, ?, ?)
            """,
            (
                row["student_id"],
                row["subject_id"],
                row["grade_at_time"],
                row.get("term_at_time"),
                row["curriculum_version_at_time"],
                row.get("textbook_version_at_time"),
                row.get("date"),
                row["question_type_code"],
                row.get("knowledge_point_id"),
                row["primary_mistake_tag_code"],
                row["difficulty_code"],
                row["question_summary"],
                row.get("wrong_answer_summary", ""),
                row.get("correct_answer_summary", ""),
                1 if row.get("training_needed", True) else 0,
                row.get("diagnosis_confidence"),
                1 if row.get("needs_human_review", False) else 0,
                _json_or_none(row.get("secondary_mistake_tags")),
                _json_or_none(row.get("diagnosis_evidence")),
                _json_or_none(row.get("alternative_diagnoses")),
                row.get("source", "manual"),
                import_batch_id,
                row_hash,
                ts,
                ts,
            ),
        )
        imported_count += 1
    conn.commit()
    return imported_count


def _json_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _create_import_batch(
    conn: sqlite3.Connection,
    import_type: str,
    rows: list[dict[str, Any]],
    preview: dict[str, Any],
    skipped_duplicate_count: int,
) -> int | None:
    if not rows:
        return None
    first = rows[0]
    ts = now_iso()
    cur = conn.execute(
        """
        INSERT INTO import_batches (
            import_type, student_id, subject_id, grade_at_time, source_name,
            source_hash, status, total_count, imported_count,
            skipped_duplicate_count, warning_count, error_count, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, 0, ?, ?, ?, ?, ?)
        """,
        (
            import_type,
            first.get("student_id"),
            first.get("subject_id"),
            first.get("grade_at_time"),
            "preview_confirm",
            "",
            preview.get("total_count", len(rows)),
            skipped_duplicate_count,
            preview.get("warning_count", 0),
            preview.get("error_count", 0),
            ts,
            ts,
        ),
    )
    return int(cur.lastrowid)


def _finish_import_batch(conn: sqlite3.Connection, import_batch_id: int | None, imported_count: int, skipped_duplicate_count: int) -> None:
    if import_batch_id is None:
        return
    conn.execute(
        """
        UPDATE import_batches
        SET status = 'imported', imported_count = ?, skipped_duplicate_count = ?, updated_at = ?
        WHERE id = ?
        """,
        (imported_count, skipped_duplicate_count, now_iso(), import_batch_id),
    )
    conn.commit()
