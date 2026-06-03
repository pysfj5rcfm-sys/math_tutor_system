from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from typing import Any

from src.core.display_contract import format_duplicate_row_for_display
from src.core.rule_registry import load_rule_registry


MISTAKE_HASH_FIELDS = [
    "student_id",
    "subject_id",
    "grade_at_time",
    "date",
    "question_type_code",
    "knowledge_point_id",
    "primary_mistake_tag_code",
    "difficulty_code",
    "question_summary",
    "wrong_answer_summary",
    "correct_answer_summary",
]

WORKSHEET_QUESTION_FIELDS = [
    "question_type_code",
    "knowledge_point_id",
    "target_mistake_tag_code",
    "difficulty_code",
    "question",
    "answer",
    "explanation",
]


def normalize_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.strip().split())
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_value(value[key]) for key in sorted(value)}
    return value


def stable_hash(value: Any) -> str:
    canonical = json.dumps(normalize_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def mistake_hash(row: dict[str, Any] | sqlite3.Row, default_student_id: str = "daughter") -> str:
    return stable_hash(canonical_mistake(row, default_student_id=default_student_id))


def canonical_mistake(row: dict[str, Any] | sqlite3.Row, default_student_id: str = "daughter") -> dict[str, Any]:
    registry = load_rule_registry()
    context = registry.resolve_learning_context(_get(row, "student_id", default_student_id) or default_student_id, _get(row, "subject_id", None) or None)
    return {
        "student_id": normalize_value(_get(row, "student_id", default_student_id)),
        "subject_id": normalize_value(_get(row, "subject_id", context.get("subject_id", ""))),
        "grade_at_time": normalize_value(_get(row, "grade_at_time", context.get("grade_at_time", ""))),
        "date": normalize_value(_get(row, "date", "")),
        "question_type_code": normalize_value(_get(row, "question_type_code", "")),
        "knowledge_point_id": normalize_value(_get(row, "knowledge_point_id", "")),
        "primary_mistake_tag_code": normalize_value(_get(row, "primary_mistake_tag_code", "")),
        "difficulty_code": normalize_value(_get(row, "difficulty_code", "")),
        "question_summary": normalize_value(_get(row, "question_summary", "")),
        "wrong_answer_summary": normalize_value(_get(row, "wrong_answer_summary", "")),
        "correct_answer_summary": normalize_value(_get(row, "correct_answer_summary", "")),
    }


def detect_duplicate_mistakes(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
    default_student_id: str = "daughter",
) -> dict[str, Any]:
    existing_by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for existing in _existing_mistake_rows(conn):
        existing_by_hash[mistake_hash(existing, default_student_id)].append(existing)

    duplicates: list[dict[str, Any]] = []
    duplicate_indices: list[int] = []
    new_indices: list[int] = []
    incoming_seen: dict[str, int] = {}
    incoming_hashes: list[str] = []

    for idx, row in enumerate(rows):
        item_hash = mistake_hash(row, default_student_id)
        incoming_hashes.append(item_hash)
        existing_matches = existing_by_hash.get(item_hash, [])
        previous_idx = incoming_seen.get(item_hash)
        if existing_matches or previous_idx is not None:
            first_existing = existing_matches[0] if existing_matches else None
            duplicates.append({
                "index": idx,
                "hash": item_hash,
                "date": _get(row, "date", ""),
                **format_duplicate_row_for_display({
                    "subject_id": _get(row, "subject_id", ""),
                    "grade_at_time": _get(row, "grade_at_time", ""),
                    "curriculum_version_at_time": _get(row, "curriculum_version_at_time", "cn_k12_2022"),
                    "question_type_code": _get(row, "question_type_code", ""),
                    "knowledge_point_id": _get(row, "knowledge_point_id", ""),
                    "primary_mistake_tag_code": _get(row, "primary_mistake_tag_code", ""),
                }),
                "question_summary": _get(row, "question_summary", ""),
                "existing_record_id": first_existing.get("id") if first_existing else None,
                "existing": _duplicate_existing_summary(first_existing) if first_existing else None,
                "incoming_duplicate_of_index": previous_idx,
            })
            duplicate_indices.append(idx)
        else:
            new_indices.append(idx)
        incoming_seen.setdefault(item_hash, idx)

    return {
        "total_count": len(rows),
        "new_count": len(new_indices),
        "duplicate_count": len(duplicate_indices),
        "new_indices": new_indices,
        "duplicate_indices": duplicate_indices,
        "duplicates": duplicates,
        "incoming_hashes": incoming_hashes,
    }


def scan_duplicate_mistake_groups(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _existing_mistake_rows(conn):
        groups[mistake_hash(row)].append(row)
    return [
        {
            "hash": hash_value,
            "count": len(records),
            "records": [_duplicate_existing_summary(record) for record in records],
        }
        for hash_value, records in sorted(groups.items())
        if len(records) > 1
    ]


def worksheet_hash(payload_or_worksheet: dict[str, Any]) -> str:
    return stable_hash(canonical_worksheet(payload_or_worksheet))


def canonical_worksheet(payload_or_worksheet: dict[str, Any]) -> dict[str, Any]:
    registry = load_rule_registry()
    worksheet = payload_or_worksheet.get("worksheet", payload_or_worksheet)
    if not isinstance(worksheet, dict):
        worksheet = {}
    context = registry.resolve_learning_context(worksheet.get("student_id") or "daughter", worksheet.get("subject_id") or None)
    sections = []
    for section in worksheet.get("sections") or []:
        if not isinstance(section, dict):
            continue
        questions = []
        for question in section.get("questions") or []:
            if not isinstance(question, dict):
                continue
            questions.append({
                "question_type_code": normalize_value(question.get("question_type_code")),
                "knowledge_point_id": normalize_value(question.get("knowledge_point_id", "")),
                "target_mistake_tag_code": normalize_value(question.get("target_mistake_tag_code")),
                "difficulty_code": normalize_value(question.get("difficulty_code")),
                "question": normalize_value(question.get("question", "")),
                "answer": normalize_value(question.get("answer", "")),
                "explanation": normalize_value(question.get("explanation", "")),
            })
        sections.append({
            "name": normalize_value(section.get("name", "")),
            "layout": normalize_value(section.get("layout", "")),
            "questions": questions,
        })
    return {
        "title": normalize_value(worksheet.get("title", "")),
        "date": normalize_value(worksheet.get("date", "")),
        "student_id": normalize_value(worksheet.get("student_id") or "daughter"),
        "subject_id": normalize_value(worksheet.get("subject_id") or context.get("subject_id", "")),
        "grade_at_time": normalize_value(worksheet.get("grade_at_time") or context.get("grade_at_time", "")),
        "sections": sections,
    }


def detect_duplicate_worksheet(conn: sqlite3.Connection, payload_or_worksheet: dict[str, Any]) -> dict[str, Any]:
    incoming_hash = worksheet_hash(payload_or_worksheet)
    matches = []
    for existing in _existing_worksheet_payloads(conn):
        if worksheet_hash(existing) == incoming_hash:
            matches.append(_worksheet_summary(existing))
    return {
        "hash": incoming_hash,
        "is_duplicate": bool(matches),
        "duplicate_count": len(matches),
        "matches": matches,
    }


def scan_duplicate_worksheet_groups(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for existing in _existing_worksheet_payloads(conn):
        groups[worksheet_hash(existing)].append(existing)
    return [
        {
            "hash": hash_value,
            "count": len(records),
            "worksheets": [_worksheet_summary(record) for record in records],
        }
        for hash_value, records in sorted(groups.items())
        if len(records) > 1
    ]


def _existing_mistake_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, student_id, subject_id, grade_at_time, date, question_type_code,
               knowledge_point_id, primary_mistake_tag_code, difficulty_code,
               question_summary, wrong_answer_summary, correct_answer_summary,
               status, source, record_hash, created_at, updated_at
        FROM mistakes
        ORDER BY id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _existing_worksheet_payloads(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    worksheet_rows = conn.execute(
        "SELECT id, student_id, subject_id, grade_at_time, curriculum_version_at_time, date, title, status, created_at, updated_at FROM worksheets ORDER BY id"
    ).fetchall()
    payloads = []
    for worksheet_row in worksheet_rows:
        items = conn.execute(
            """
            SELECT section_name, section_layout, question_type_code, knowledge_point_id,
                   target_mistake_tag_code, difficulty_code, question, answer,
                   explanation
            FROM worksheet_items
            WHERE worksheet_id = ?
            ORDER BY id
            """,
            (worksheet_row["id"],),
        ).fetchall()
        sections: list[dict[str, Any]] = []
        by_section: dict[str, dict[str, Any]] = {}
        for item in items:
            section_name = item["section_name"] or ""
            if section_name not in by_section:
                by_section[section_name] = {
                    "name": section_name,
                    "layout": item["section_layout"] or "single_column",
                    "questions": [],
                }
                sections.append(by_section[section_name])
            by_section[section_name]["questions"].append({
                "question_type_code": item["question_type_code"],
                "knowledge_point_id": item["knowledge_point_id"],
                "target_mistake_tag_code": item["target_mistake_tag_code"],
                "difficulty_code": item["difficulty_code"],
                "question": item["question"],
                "answer": item["answer"],
                "explanation": item["explanation"] or "",
            })
        payloads.append({
            "id": worksheet_row["id"],
            "status": worksheet_row["status"],
            "created_at": worksheet_row["created_at"],
            "updated_at": worksheet_row["updated_at"],
            "worksheet": {
                "title": worksheet_row["title"],
                "date": worksheet_row["date"],
                "student_id": worksheet_row["student_id"],
                "subject_id": worksheet_row["subject_id"],
                "grade_at_time": worksheet_row["grade_at_time"],
                "curriculum_version_at_time": worksheet_row["curriculum_version_at_time"],
                "sections": sections,
            },
        })
    return payloads


def _duplicate_existing_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return format_duplicate_row_for_display({
        "id": row.get("id"),
        "date": row.get("date"),
        "subject_id": row.get("subject_id"),
        "grade_at_time": row.get("grade_at_time"),
        "curriculum_version_at_time": row.get("curriculum_version_at_time") or "cn_k12_2022",
        "question_summary": row.get("question_summary"),
        "status": row.get("status"),
        "source": row.get("source"),
        "question_type_code": row.get("question_type_code"),
        "knowledge_point_id": row.get("knowledge_point_id"),
        "primary_mistake_tag_code": row.get("primary_mistake_tag_code"),
        "created_at": row.get("created_at"),
    })


def _worksheet_summary(payload: dict[str, Any]) -> dict[str, Any]:
    worksheet = payload.get("worksheet", {})
    question_count = sum(len(section.get("questions", [])) for section in worksheet.get("sections", []))
    first_question = {}
    for section in worksheet.get("sections", []):
        questions = section.get("questions") or []
        if questions:
            first_question = questions[0]
            break
    return format_duplicate_row_for_display({
        "id": payload.get("id"),
        "title": worksheet.get("title"),
        "date": worksheet.get("date"),
        "student_id": worksheet.get("student_id"),
        "subject_id": worksheet.get("subject_id"),
        "grade_at_time": worksheet.get("grade_at_time"),
        "curriculum_version_at_time": worksheet.get("curriculum_version_at_time") or "cn_k12_2022",
        "question_type_code": first_question.get("question_type_code"),
        "knowledge_point_id": first_question.get("knowledge_point_id"),
        "status": payload.get("status"),
        "question_count": question_count,
        "created_at": payload.get("created_at"),
    })


def _get(row: dict[str, Any] | sqlite3.Row, key: str, default: Any = "") -> Any:
    if isinstance(row, sqlite3.Row):
        return row[key] if key in row.keys() else default
    return row.get(key, default)

