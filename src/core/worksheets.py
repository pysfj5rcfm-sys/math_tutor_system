from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

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
    question_types = set(registry.get_question_type_codes())
    knowledge_points = set(registry.get_knowledge_point_codes())
    mistake_tags = set(registry.get_mistake_tag_codes())
    difficulties = set(registry.get_difficulty_codes())
    report = ValidationReport()
    worksheet = payload.get("worksheet")
    if not isinstance(worksheet, dict):
        report.add_error("invalid_worksheet_root", "worksheet must be a mapping")
        return report, None
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
            if question.get("knowledge_point") not in knowledge_points:
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
    ts = now_iso()
    student_id = worksheet.get("student_id") or DEFAULT_STUDENT_ID
    tags = sorted({q["target_mistake_tag"] for s in worksheet["sections"] for q in s["questions"]})
    cur = conn.execute(
        """
        INSERT INTO worksheets (
            tenant_id, student_id, date, title, source_prompt_id, target_mistake_tags,
            status, version, created_by_user_id, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'needs_confirmation', 1, ?, ?, ?)
        """,
        (
            tenant_id,
            student_id,
            worksheet["date"],
            worksheet["title"],
            source_prompt_id,
            json.dumps(tags, ensure_ascii=False),
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
    layout_by_type = {
        item["code"]: item.get("default_layout", "single_column")
        for item in registry.get_question_types(active_only=False)
    }
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
