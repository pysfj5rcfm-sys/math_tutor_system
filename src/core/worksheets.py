from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from src.core.duplicate_guard import detect_duplicate_worksheet
from src.core.rule_registry import RuleRegistry, load_rule_registry
from src.db import now_iso
from src.schemas.mistake_schema import (
    DEFAULT_CREATED_BY_USER_ID,
    DEFAULT_STUDENT_ID,
    DEFAULT_TENANT_ID,
    ValidationReport,
)
from src.schemas.worksheet_schema import SECTION_LAYOUTS


def load_worksheet_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_worksheet_payload(
    payload: dict[str, Any],
    registry: RuleRegistry | None = None,
) -> tuple[ValidationReport, dict[str, Any] | None]:
    registry = registry or load_rule_registry()
    difficulties = set(registry.get_difficulty_codes())
    report = ValidationReport()
    worksheet = payload.get("worksheet")
    if not isinstance(worksheet, dict):
        report.add_error("invalid_worksheet_root", "worksheet must be a mapping")
        return report, None
    context = _context_for_worksheet(registry, payload, worksheet, report)
    if context is None:
        report.skipped_count = 1
        return report, None
    worksheet = _apply_context(worksheet, context)
    subject_id = context["subject_id"]
    question_types = set(registry.get_question_type_values_for_subject(subject_id))
    mistake_tags = {item["code"] for item in registry.get_mistake_tags_for_subject(subject_id)}
    if not worksheet.get("title"):
        report.add_error("missing_title", "worksheet.title is required")
    if not worksheet.get("date"):
        report.add_error("missing_date", "worksheet.date is required")
    sections = worksheet.get("sections")
    if not isinstance(sections, list) or not sections:
        report.add_error("invalid_sections", "worksheet.sections must be a non-empty list")

    if report.errors:
        report.skipped_count = 1
        return report, None

    valid_sections: list[dict[str, Any]] = []
    skipped_questions = 0
    for section_idx, section in enumerate(sections):
        if not isinstance(section, dict):
            report.add_error("invalid_section", "section must be a mapping", section_idx)
            continue
        layout = section.get("layout")
        if layout not in SECTION_LAYOUTS:
            report.add_error("invalid_section_layout", "section.layout must be two_columns or single_column", section_idx)
            continue
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            report.add_error("invalid_questions", "section.questions must be a non-empty list", section_idx)
            continue
        valid_questions: list[dict[str, Any]] = []
        for q_idx, question in enumerate(questions):
            index = section_idx * 1000 + q_idx
            if not isinstance(question, dict):
                report.add_error("invalid_question", "question must be a mapping", index)
                skipped_questions += 1
                continue
            item_errors = 0
            if question.get("question_type") not in question_types:
                report.add_error("invalid_question_type", "question_type is not supported", index)
                item_errors += 1
            knowledge_point_result = registry.validate_knowledge_point_for_context(
                question.get("knowledge_point"),
                subject_id,
                context["grade_at_time"],
                context["curriculum_version_at_time"],
            )
            if knowledge_point_result["ambiguous"]:
                report.add_warning("ambiguous_knowledge_point", "knowledge_point matches multiple items in current curriculum scope", index)
            elif not knowledge_point_result["valid"]:
                report.add_warning("unknown_knowledge_point", "knowledge_point is not in initial values; imported as needs_confirmation", index)
            if question.get("target_mistake_tag") not in mistake_tags:
                report.add_error("invalid_mistake_tag", "target_mistake_tag must be one of the 24 core tags", index)
                item_errors += 1
            if question.get("difficulty") not in difficulties:
                report.add_error("invalid_difficulty", "difficulty is not supported", index)
                item_errors += 1
            if not question.get("question"):
                report.add_error("empty_question", "question must not be empty", index)
                item_errors += 1
            if not question.get("answer"):
                report.add_error("missing_answer", "answer is required", index)
                item_errors += 1
            if not question.get("explanation"):
                report.add_error("missing_explanation", "explanation is required", index)
                item_errors += 1
            if item_errors:
                skipped_questions += 1
                continue
            valid_questions.append(question)
        if valid_questions:
            valid_sections.append({**section, "questions": valid_questions})

    if report.errors:
        report.valid = False
        report.skipped_count = skipped_questions or 1
        return report, None
    return report, {**worksheet, "sections": valid_sections}


def import_worksheet_payload(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    tenant_id: str = DEFAULT_TENANT_ID,
    created_by_user_id: str = DEFAULT_CREATED_BY_USER_ID,
    source_prompt_id: int | None = None,
) -> tuple[dict[str, Any], int | None]:
    report, worksheet = validate_worksheet_payload(payload)
    if worksheet is None:
        return report.as_dict(), None
    return _insert_valid_worksheet(conn, report, worksheet, tenant_id, created_by_user_id, source_prompt_id)


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
    tenant_id: str = DEFAULT_TENANT_ID,
    created_by_user_id: str = DEFAULT_CREATED_BY_USER_ID,
    source_prompt_id: int | None = None,
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
    if duplicate_strategy in {"cancel", "取消导入"}:
        report_dict.update({
            "imported_count": 0,
            "duplicate_count": duplicate_scan.get("duplicate_count", 0),
            "skipped_duplicate_count": 1 if is_duplicate else 0,
            "skipped_count": int(report_dict.get("skipped_count", 0)) + (1 if is_duplicate else 0),
        })
        return report_dict, None
    if is_duplicate and duplicate_strategy in {"skip_duplicate", "跳过导入", "跳过重复"}:
        report_dict.update({
            "imported_count": 0,
            "duplicate_count": duplicate_scan.get("duplicate_count", 0),
            "skipped_duplicate_count": 1,
            "skipped_count": int(report_dict.get("skipped_count", 0)) + 1,
        })
        return report_dict, None
    if duplicate_strategy not in {"skip_duplicate", "import_all", "仍然导入", "仍然导入全部"}:
        raise ValueError(f"Unsupported duplicate strategy: {duplicate_strategy}")

    report = _report_from_dict(report_dict)
    inserted_report, worksheet_id = _insert_valid_worksheet(conn, report, worksheet, tenant_id, created_by_user_id, source_prompt_id)
    inserted_report.update({
        "duplicate_count": duplicate_scan.get("duplicate_count", 0),
        "skipped_duplicate_count": 0,
    })
    return inserted_report, worksheet_id


def _insert_valid_worksheet(
    conn: sqlite3.Connection,
    report: ValidationReport,
    worksheet: dict[str, Any],
    tenant_id: str = DEFAULT_TENANT_ID,
    created_by_user_id: str = DEFAULT_CREATED_BY_USER_ID,
    source_prompt_id: int | None = None,
) -> tuple[dict[str, Any], int | None]:
    ts = now_iso()
    student_id = worksheet.get("student_id") or DEFAULT_STUDENT_ID
    tags = sorted({q["target_mistake_tag"] for s in worksheet["sections"] for q in s["questions"]})
    cur = conn.execute(
        """
        INSERT INTO worksheets (
            tenant_id, student_id, date, title, source_prompt_id, target_mistake_tags,
            status, version, subject_id, grade_at_time, term_at_time,
            curriculum_version_at_time, created_by_user_id, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'needs_confirmation', 1, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            student_id,
            worksheet["date"],
            worksheet["title"],
            source_prompt_id,
            json.dumps(tags, ensure_ascii=False),
            worksheet.get("subject_id"),
            worksheet.get("grade_at_time"),
            worksheet.get("term_at_time"),
            worksheet.get("curriculum_version_at_time"),
            created_by_user_id,
            ts,
            ts,
        ),
    )
    worksheet_id = int(cur.lastrowid)
    sort_order = 1
    for section in worksheet["sections"]:
        for question in section["questions"]:
            conn.execute(
                """
                INSERT INTO worksheet_items (
                    tenant_id, student_id, worksheet_id, section, question_type,
                    knowledge_point, target_mistake_tag, difficulty, question,
                    answer, explanation, sort_order, requires_diagram, diagram_json,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    student_id,
                    worksheet_id,
                    section.get("name", ""),
                    question["question_type"],
                    question.get("knowledge_point", ""),
                    question["target_mistake_tag"],
                    question["difficulty"],
                    question["question"],
                    question["answer"],
                    question["explanation"],
                    sort_order,
                    1 if question.get("requires_diagram", False) else 0,
                    json.dumps(question.get("diagram_json"), ensure_ascii=False) if question.get("diagram_json") is not None else None,
                    ts,
                    ts,
                ),
            )
            sort_order += 1
            report.imported_count += 1
    conn.commit()
    return report.as_dict(), worksheet_id


def import_worksheet_file(conn: sqlite3.Connection, path: str | Path) -> tuple[dict[str, Any], int | None]:
    return import_worksheet_payload(conn, load_worksheet_yaml(path))


def get_worksheet_bundle(conn: sqlite3.Connection, worksheet_id: int) -> dict[str, Any]:
    registry = load_rule_registry()
    layout_by_type: dict[str, str] = {}
    for item in registry.get_question_types(active_only=False):
        layout = item.get("default_layout", "single_column")
        for value in [item.get("code"), item.get("name"), item.get("display_name"), *(item.get("legacy_names") or [])]:
            if value:
                layout_by_type[str(value)] = layout
    worksheet = conn.execute("SELECT * FROM worksheets WHERE id = ?", (worksheet_id,)).fetchone()
    if worksheet is None:
        raise ValueError(f"worksheet not found: {worksheet_id}")
    items = [dict(row) for row in conn.execute(
        "SELECT * FROM worksheet_items WHERE worksheet_id = ? ORDER BY sort_order",
        (worksheet_id,),
    ).fetchall()]
    sections: dict[str, dict[str, Any]] = {}
    for item in items:
        section_name = item["section"]
        layout = layout_by_type.get(item["question_type"], "single_column")
        sections.setdefault(section_name, {"name": section_name, "layout": layout, "questions": []})
        sections[section_name]["questions"].append(item)
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


def _context_for_worksheet(
    registry: RuleRegistry,
    payload: dict[str, Any],
    worksheet: dict[str, Any],
    report: ValidationReport,
) -> dict[str, Any] | None:
    student_id = worksheet.get("student_id") or payload.get("student_id")
    subject_id = worksheet.get("subject_id") or payload.get("subject_id")
    try:
        context = registry.resolve_learning_context(student_id=student_id, subject_id=subject_id)
    except Exception as exc:
        report.add_error("invalid_learning_context", str(exc))
        return None
    for source in (payload, worksheet):
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


def _apply_context(worksheet: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    result = dict(worksheet)
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
