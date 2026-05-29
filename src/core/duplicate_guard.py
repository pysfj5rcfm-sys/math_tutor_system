from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import defaultdict
from typing import Any

from src.schemas.mistake_schema import DEFAULT_STUDENT_ID


MISTAKE_HASH_FIELDS = [
    "student_id",
    "date",
    "question_type",
    "knowledge_point",
    "mistake_tag",
    "difficulty",
    "question_summary",
    "wrong_answer_summary",
    "correct_answer_summary",
]

WORKSHEET_QUESTION_FIELDS = [
    "question_type",
    "knowledge_point",
    "target_mistake_tag",
    "difficulty",
    "question",
    "answer",
    "explanation",
    "requires_diagram",
    "diagram_json",
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


def mistake_hash(row: dict[str, Any] | sqlite3.Row, default_student_id: str = DEFAULT_STUDENT_ID) -> str:
    canonical = canonical_mistake(row, default_student_id=default_student_id)
    return stable_hash(canonical)


def canonical_mistake(row: dict[str, Any] | sqlite3.Row, default_student_id: str = DEFAULT_STUDENT_ID) -> dict[str, Any]:
    return {
        field: normalize_value(_get(row, field, default_student_id if field == "student_id" else ""))
        for field in MISTAKE_HASH_FIELDS
    }


def detect_duplicate_mistakes(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
    default_student_id: str = DEFAULT_STUDENT_ID,
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
                "question_type": _get(row, "question_type", ""),
                "mistake_tag": _get(row, "mistake_tag", ""),
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
    worksheet = payload_or_worksheet.get("worksheet", payload_or_worksheet)
    if not isinstance(worksheet, dict):
        worksheet = {}
    sections = []
    for section in worksheet.get("sections") or []:
        if not isinstance(section, dict):
            continue
        questions = []
        for question in section.get("questions") or []:
            if not isinstance(question, dict):
                continue
            questions.append({
                field: normalize_value(question.get(field, False if field == "requires_diagram" else ""))
                for field in WORKSHEET_QUESTION_FIELDS
            })
        sections.append({
            "name": normalize_value(section.get("name", "")),
            "questions": questions,
        })
    return {
        "title": normalize_value(worksheet.get("title", "")),
        "date": normalize_value(worksheet.get("date", "")),
        "student_id": normalize_value(worksheet.get("student_id") or DEFAULT_STUDENT_ID),
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
        SELECT id, student_id, date, question_type, knowledge_point, mistake_tag,
               difficulty, question_summary, wrong_answer_summary,
               correct_answer_summary, status, source, created_at, updated_at
        FROM mistakes
        ORDER BY id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _existing_worksheet_payloads(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    worksheet_rows = conn.execute(
        "SELECT id, student_id, date, title, status, created_at, updated_at FROM worksheets ORDER BY id"
    ).fetchall()
    payloads = []
    for worksheet_row in worksheet_rows:
        items = conn.execute(
            """
            SELECT section, question_type, knowledge_point, target_mistake_tag,
                   difficulty, question, answer, explanation, requires_diagram,
                   diagram_json, sort_order
            FROM worksheet_items
            WHERE worksheet_id = ?
            ORDER BY sort_order
            """,
            (worksheet_row["id"],),
        ).fetchall()
        sections: list[dict[str, Any]] = []
        by_section: dict[str, dict[str, Any]] = {}
        for item in items:
            section_name = item["section"]
            if section_name not in by_section:
                by_section[section_name] = {"name": section_name, "questions": []}
                sections.append(by_section[section_name])
            question = {
                "question_type": item["question_type"],
                "knowledge_point": item["knowledge_point"],
                "target_mistake_tag": item["target_mistake_tag"],
                "difficulty": item["difficulty"],
                "question": item["question"],
                "answer": item["answer"],
                "explanation": item["explanation"],
                "requires_diagram": bool(item["requires_diagram"]),
                "diagram_json": item["diagram_json"] or "",
            }
            by_section[section_name]["questions"].append(question)
        payloads.append({
            "id": worksheet_row["id"],
            "status": worksheet_row["status"],
            "created_at": worksheet_row["created_at"],
            "updated_at": worksheet_row["updated_at"],
            "worksheet": {
                "title": worksheet_row["title"],
                "date": worksheet_row["date"],
                "student_id": worksheet_row["student_id"],
                "sections": sections,
            },
        })
    return payloads


def _duplicate_existing_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.get("id"),
        "date": row.get("date"),
        "question_summary": row.get("question_summary"),
        "status": row.get("status"),
        "source": row.get("source"),
        "question_type": row.get("question_type"),
        "mistake_tag": row.get("mistake_tag"),
        "created_at": row.get("created_at"),
    }


def _worksheet_summary(payload: dict[str, Any]) -> dict[str, Any]:
    worksheet = payload.get("worksheet", {})
    question_count = sum(len(section.get("questions", [])) for section in worksheet.get("sections", []))
    return {
        "id": payload.get("id"),
        "title": worksheet.get("title"),
        "date": worksheet.get("date"),
        "student_id": worksheet.get("student_id"),
        "status": payload.get("status"),
        "question_count": question_count,
        "created_at": payload.get("created_at"),
    }


def _get(row: dict[str, Any] | sqlite3.Row, key: str, default: Any = "") -> Any:
    if isinstance(row, sqlite3.Row):
        return row[key] if key in row.keys() else default
    return row.get(key, default)
