from __future__ import annotations

import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.core.display_contract import format_export_row
from src.core.paths import DEFAULT_DB_PATH, ROOT


DEFAULT_BACKUP_DIR = ROOT / "backups"
DEFAULT_EXPORT_DIR = ROOT / "outputs" / "exports"

MISTAKE_EXPORT_COLUMNS = [
    "student_id",
    "subject_id",
    "grade_at_time",
    "term_at_time",
    "curriculum_version_at_time",
    "date",
    "question_type_code",
    "question_type_display",
    "knowledge_point_id",
    "knowledge_point_display",
    "primary_mistake_tag_code",
    "mistake_tag_display",
    "difficulty_code",
    "difficulty_display",
    "question_summary",
    "wrong_answer_summary",
    "correct_answer_summary",
    "status",
    "source",
]

WORKSHEET_ITEM_EXPORT_COLUMNS = [
    "student_id",
    "subject_id",
    "grade_at_time",
    "question_type_code",
    "question_type_display",
    "knowledge_point_id",
    "knowledge_point_display",
    "target_mistake_tag_code",
    "mistake_tag_display",
    "difficulty_code",
    "difficulty_display",
    "primary_target_id",
    "question_role",
    "teaching_purpose",
    "expected_error_mechanism",
    "question",
    "answer",
    "explanation",
]


def backup_database(
    db_path: str | Path = DEFAULT_DB_PATH,
    backup_dir: str | Path = DEFAULT_BACKUP_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    source = Path(db_path)
    target_dir = Path(backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return {"ok": False, "path": None, "error": f"database file does not exist: {source}"}
    target = target_dir / f"edu_tutor_{_timestamp(now)}.db"
    shutil.copy2(source, target)
    return {"ok": True, "path": target, "error": ""}


def export_mistakes_csv(
    conn: sqlite3.Connection,
    output_dir: str | Path = DEFAULT_EXPORT_DIR,
    now: datetime | None = None,
) -> Path:
    output_path = _timestamped_export_path(output_dir, "mistakes", ".csv", now)
    rows = _all_mistakes(conn)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MISTAKE_EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in MISTAKE_EXPORT_COLUMNS})
    return output_path


def export_mistakes_yaml(
    conn: sqlite3.Connection,
    output_dir: str | Path = DEFAULT_EXPORT_DIR,
    now: datetime | None = None,
) -> Path:
    output_path = _timestamped_export_path(output_dir, "mistakes", ".yaml", now)
    output_path.write_text(
        yaml.safe_dump({"mistakes": _all_mistakes(conn)}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return output_path


def export_worksheets_yaml(
    conn: sqlite3.Connection,
    output_dir: str | Path = DEFAULT_EXPORT_DIR,
    now: datetime | None = None,
) -> Path:
    output_path = _timestamped_export_path(output_dir, "worksheets", ".yaml", now)
    output_path.write_text(
        yaml.safe_dump({"worksheets": _all_worksheets(conn)}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return output_path


def export_worksheet_items_csv(
    conn: sqlite3.Connection,
    output_dir: str | Path = DEFAULT_EXPORT_DIR,
    now: datetime | None = None,
) -> Path:
    output_path = _timestamped_export_path(output_dir, "worksheet_items", ".csv", now)
    rows = _worksheet_item_rows(conn)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=WORKSHEET_ITEM_EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in WORKSHEET_ITEM_EXPORT_COLUMNS})
    return output_path


def _timestamped_export_path(output_dir: str | Path, prefix: str, suffix: str, now: datetime | None = None) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{prefix}_{_timestamp(now)}{suffix}"


def _timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d_%H%M%S")


def _all_mistakes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = [dict(row) for row in conn.execute("SELECT * FROM mistakes ORDER BY date DESC, id DESC").fetchall()]
    for row in rows:
        _add_mistake_displays(row)
    return rows


def _all_worksheets(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    worksheets = []
    for row in conn.execute("SELECT * FROM worksheets ORDER BY id").fetchall():
        worksheet = dict(row)
        sections: list[dict[str, Any]] = []
        by_section: dict[str, dict[str, Any]] = {}
        for item in _items_for_worksheet(conn, worksheet["id"]):
            section_name = item.get("section_name") or ""
            if section_name not in by_section:
                by_section[section_name] = {"name": section_name, "layout": item.get("section_layout") or "single_column", "questions": []}
                sections.append(by_section[section_name])
            by_section[section_name]["questions"].append(_worksheet_item_export(item, worksheet))
        worksheets.append({"metadata": worksheet, "worksheet": {
            "title": worksheet["title"],
            "date": worksheet["date"],
            "student_id": worksheet["student_id"],
            "subject_id": worksheet["subject_id"],
            "grade_at_time": worksheet["grade_at_time"],
            "term_at_time": worksheet.get("term_at_time"),
            "curriculum_version_at_time": worksheet["curriculum_version_at_time"],
            "sections": sections,
        }})
    return worksheets


def _worksheet_item_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for worksheet in conn.execute("SELECT * FROM worksheets ORDER BY id").fetchall():
        worksheet_dict = dict(worksheet)
        for item in _items_for_worksheet(conn, worksheet_dict["id"]):
            rows.append(_worksheet_item_export(item, worksheet_dict))
    return rows


def _items_for_worksheet(conn: sqlite3.Connection, worksheet_id: int) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(
        "SELECT * FROM worksheet_items WHERE worksheet_id = ? ORDER BY id",
        (worksheet_id,),
    ).fetchall()]


def _add_mistake_displays(row: dict[str, Any]) -> None:
    row.update(format_export_row(row))


def _worksheet_item_export(item: dict[str, Any], worksheet: dict[str, Any]) -> dict[str, Any]:
    row = {
        "student_id": worksheet.get("student_id"),
        "subject_id": worksheet.get("subject_id"),
        "grade_at_time": worksheet.get("grade_at_time"),
        "curriculum_version_at_time": worksheet.get("curriculum_version_at_time"),
        "question_type_code": item.get("question_type_code"),
        "knowledge_point_id": item.get("knowledge_point_id"),
        "target_mistake_tag_code": item.get("target_mistake_tag_code"),
        "difficulty_code": item.get("difficulty_code"),
        "primary_target_id": item.get("primary_target_id"),
        "question_role": item.get("question_role"),
        "teaching_purpose": item.get("teaching_purpose"),
        "expected_error_mechanism": item.get("expected_error_mechanism"),
        "question": item.get("question"),
        "answer": item.get("answer"),
        "explanation": item.get("explanation"),
    }
    return format_export_row(row)
