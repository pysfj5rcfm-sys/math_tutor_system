from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from src.core.duplicate_guard import detect_duplicate_worksheet, worksheet_hash
from src.core.normalization import normalize_worksheet_payload
from src.core.rule_registry import RuleRegistry, load_rule_registry
from src.db import now_iso
from src.schemas.mistake_schema import ValidationReport


def load_worksheet_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_worksheet_payload(
    payload: dict[str, Any],
    registry: RuleRegistry | None = None,
) -> tuple[ValidationReport, dict[str, Any] | None]:
    report = ValidationReport()
    worksheet, errors, warnings = normalize_worksheet_payload(payload, registry or load_rule_registry())
    report.errors.extend(errors)
    report.warnings.extend(warnings)
    report.valid = not errors
    if worksheet is None:
        report.skipped_count = 1
    return report, worksheet


def import_worksheet_payload(conn: sqlite3.Connection, payload: dict[str, Any], **_: Any) -> tuple[dict[str, Any], int | None]:
    preview = preview_worksheet_payload(conn, payload)
    return confirm_worksheet_import(conn, preview, duplicate_strategy="import_all")


def preview_worksheet_payload(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    report, worksheet = validate_worksheet_payload(payload)
    duplicate_scan = detect_duplicate_worksheet(conn, {"worksheet": worksheet}) if worksheet is not None else {
        "hash": "",
        "is_duplicate": False,
        "duplicate_count": 0,
        "matches": [],
    }
    question_count = _question_count(worksheet) if worksheet is not None else 0
    return {
        "source_type": "worksheet",
        "valid": worksheet is not None and not report.errors,
        "validation": report.as_dict(),
        "worksheet": worksheet,
        "normalization": {"worksheet": worksheet, "warnings": report.warnings},
        "total_count": 1 if isinstance(payload.get("worksheet"), dict) else 0,
        "question_count": question_count,
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "duplicate_scan": duplicate_scan,
        "duplicate_count": duplicate_scan["duplicate_count"],
        "new_count": 0 if duplicate_scan["is_duplicate"] else (1 if worksheet is not None else 0),
        "will_import_count": 0 if report.errors or duplicate_scan["is_duplicate"] else 1,
        "will_skip_count": 1 if duplicate_scan["is_duplicate"] else int(worksheet is None),
    }


def confirm_worksheet_import(
    conn: sqlite3.Connection,
    preview: dict[str, Any],
    duplicate_strategy: str = "skip_duplicate",
    **_: Any,
) -> tuple[dict[str, Any], int | None]:
    report_dict = dict(preview.get("validation") or {})
    worksheet = preview.get("worksheet")
    if not preview.get("valid") or worksheet is None or report_dict.get("errors"):
        report_dict.update({
            "imported_count": 0,
            "duplicate_count": preview.get("duplicate_count", 0),
            "skipped_duplicate_count": 0,
        })
        return report_dict, None

    duplicate_scan = preview.get("duplicate_scan") or {}
    is_duplicate = bool(duplicate_scan.get("is_duplicate"))
    if duplicate_strategy == "cancel":
        report_dict.update({
            "imported_count": 0,
            "duplicate_count": duplicate_scan.get("duplicate_count", 0),
            "skipped_duplicate_count": 1 if is_duplicate else 0,
            "skipped_count": int(report_dict.get("skipped_count", 0)) + (1 if is_duplicate else 0),
        })
        return report_dict, None
    if is_duplicate and duplicate_strategy == "skip_duplicate":
        report_dict.update({
            "imported_count": 0,
            "duplicate_count": duplicate_scan.get("duplicate_count", 0),
            "skipped_duplicate_count": 1,
            "skipped_count": int(report_dict.get("skipped_count", 0)) + 1,
        })
        return report_dict, None
    if duplicate_strategy not in {"skip_duplicate", "import_all"}:
        raise ValueError(f"Unsupported duplicate strategy: {duplicate_strategy}")

    report = _report_from_dict(report_dict)
    import_batch_id = _create_import_batch(conn, worksheet, preview)
    inserted_report, worksheet_id = _insert_valid_worksheet(conn, report, worksheet, import_batch_id)
    inserted_report.update({
        "duplicate_count": duplicate_scan.get("duplicate_count", 0),
        "skipped_duplicate_count": 0,
        "import_batch_id": import_batch_id,
    })
    return inserted_report, worksheet_id


def _insert_valid_worksheet(
    conn: sqlite3.Connection,
    report: ValidationReport,
    worksheet: dict[str, Any],
    import_batch_id: int | None = None,
) -> tuple[dict[str, Any], int | None]:
    ts = now_iso()
    cur = conn.execute(
        """
        INSERT INTO worksheets (
            student_id, subject_id, grade_at_time, term_at_time,
            curriculum_version_at_time, textbook_version_at_time, title,
            date, source, status, worksheet_hash, import_batch_id, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'needs_confirmation', ?, ?, ?, ?)
        """,
        (
            worksheet["student_id"],
            worksheet["subject_id"],
            worksheet["grade_at_time"],
            worksheet.get("term_at_time"),
            worksheet["curriculum_version_at_time"],
            worksheet.get("textbook_version_at_time"),
            worksheet["title"],
            worksheet.get("date"),
            worksheet.get("source", "manual"),
            worksheet_hash({"worksheet": worksheet}),
            import_batch_id,
            ts,
            ts,
        ),
    )
    worksheet_id = int(cur.lastrowid)
    for section in worksheet["sections"]:
        for question in section["questions"]:
            conn.execute(
                """
                INSERT INTO worksheet_items (
                    worksheet_id, question_no, section_name, section_layout,
                    question_type_code, knowledge_point_id, target_mistake_tag_code,
                    difficulty_code, primary_target_id, question_role,
                    teaching_purpose, expected_error_mechanism,
                    question, answer, explanation, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    worksheet_id,
                    question.get("question_no"),
                    section.get("name", ""),
                    section.get("layout", "single_column"),
                    question["question_type_code"],
                    question.get("knowledge_point_id"),
                    question.get("target_mistake_tag_code"),
                    question["difficulty_code"],
                    question.get("primary_target_id", ""),
                    question.get("question_role", ""),
                    question.get("teaching_purpose", ""),
                    question.get("expected_error_mechanism", ""),
                    question["question"],
                    question["answer"],
                    question.get("explanation", ""),
                    ts,
                    ts,
                ),
            )
            report.imported_count += 1
    if import_batch_id is not None:
        conn.execute(
            "UPDATE import_batches SET status = 'imported', imported_count = ?, updated_at = ? WHERE id = ?",
            (report.imported_count, ts, import_batch_id),
        )
    conn.commit()
    return report.as_dict(), worksheet_id


def import_worksheet_file(conn: sqlite3.Connection, path: str | Path) -> tuple[dict[str, Any], int | None]:
    return import_worksheet_payload(conn, load_worksheet_yaml(path))


def get_worksheet_bundle(conn: sqlite3.Connection, worksheet_id: int) -> dict[str, Any]:
    worksheet = conn.execute("SELECT * FROM worksheets WHERE id = ?", (worksheet_id,)).fetchone()
    if worksheet is None:
        raise ValueError(f"worksheet not found: {worksheet_id}")
    items = [dict(row) for row in conn.execute(
        "SELECT * FROM worksheet_items WHERE worksheet_id = ? ORDER BY id",
        (worksheet_id,),
    ).fetchall()]
    sections: dict[str, dict[str, Any]] = {}
    for item in items:
        section_name = item.get("section_name") or ""
        layout = item.get("section_layout") or "single_column"
        rendered_item = {
            **item,
            "requires_diagram": False,
            "diagram_json": None,
        }
        sections.setdefault(section_name, {"name": section_name, "layout": layout, "questions": []})
        sections[section_name]["questions"].append(rendered_item)
    return {"worksheet": dict(worksheet), "sections": list(sections.values())}


def _question_count(worksheet: dict[str, Any] | None) -> int:
    if worksheet is None:
        return 0
    return sum(len(section.get("questions", [])) for section in worksheet.get("sections", []))


def _report_from_dict(report_dict: dict[str, Any]) -> ValidationReport:
    report = ValidationReport()
    report.valid = bool(report_dict.get("valid", True))
    report.errors = list(report_dict.get("errors", []))
    report.warnings = list(report_dict.get("warnings", []))
    report.imported_count = int(report_dict.get("imported_count", 0))
    report.skipped_count = int(report_dict.get("skipped_count", 0))
    return report


def _create_import_batch(conn: sqlite3.Connection, worksheet: dict[str, Any], preview: dict[str, Any]) -> int:
    ts = now_iso()
    cur = conn.execute(
        """
        INSERT INTO import_batches (
            import_type, student_id, subject_id, grade_at_time, source_name,
            source_hash, status, total_count, imported_count,
            skipped_duplicate_count, warning_count, error_count, created_at, updated_at
        )
        VALUES ('worksheet', ?, ?, ?, ?, ?, 'pending', ?, 0, 0, ?, ?, ?, ?)
        """,
        (
            worksheet.get("student_id"),
            worksheet.get("subject_id"),
            worksheet.get("grade_at_time"),
            worksheet.get("source", "preview_confirm"),
            worksheet_hash({"worksheet": worksheet}),
            preview.get("question_count", 0),
            preview.get("warning_count", 0),
            preview.get("error_count", 0),
            ts,
            ts,
        ),
    )
    return int(cur.lastrowid)
