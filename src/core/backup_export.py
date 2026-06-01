from __future__ import annotations

import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.core.rule_registry import RuleRegistryError, load_rule_registry
from src.db import DEFAULT_DB_PATH


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKUP_DIR = ROOT / "backups"
DEFAULT_EXPORT_DIR = ROOT / "outputs" / "exports"

MISTAKE_EXPORT_COLUMNS = [
    "id",
    "tenant_id",
    "student_id",
    "subject_id",
    "grade_at_time",
    "term_at_time",
    "curriculum_version_at_time",
    "date",
    "question_type",
    "knowledge_point",
    "mistake_tag",
    "difficulty",
    "question_summary",
    "wrong_answer_summary",
    "correct_answer_summary",
    "training_needed",
    "source",
    "note",
    "status",
    "created_by_user_id",
    "created_at",
    "updated_at",
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
        return {
            "ok": False,
            "path": None,
            "error": f"数据库文件不存在：{source}",
        }
    target = target_dir / f"math_tutor_{_timestamp(now)}.db"
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
    rows = [dict(row) for row in conn.execute("SELECT * FROM worksheet_items ORDER BY worksheet_id, sort_order").fetchall()]
    fieldnames = list(rows[0]) if rows else [
        "id",
        "tenant_id",
        "student_id",
        "worksheet_id",
        "section",
        "question_type",
        "knowledge_point",
        "target_mistake_tag",
        "difficulty",
        "question",
        "answer",
        "explanation",
        "sort_order",
        "requires_diagram",
        "diagram_json",
        "created_at",
        "updated_at",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _timestamped_export_path(output_dir: str | Path, prefix: str, suffix: str, now: datetime | None = None) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{prefix}_{_timestamp(now)}{suffix}"


def _timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d_%H%M%S")


def _all_mistakes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [_with_default_context(dict(row)) for row in conn.execute("SELECT * FROM mistakes ORDER BY date DESC, id DESC").fetchall()]


def _all_worksheets(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    worksheets = []
    for row in conn.execute("SELECT * FROM worksheets ORDER BY id").fetchall():
        worksheet = dict(row)
        items = [dict(item) for item in conn.execute(
            "SELECT * FROM worksheet_items WHERE worksheet_id = ? ORDER BY sort_order",
            (worksheet["id"],),
        ).fetchall()]
        sections: list[dict[str, Any]] = []
        by_section: dict[str, dict[str, Any]] = {}
        for item in items:
            section_name = item["section"]
            if section_name not in by_section:
                by_section[section_name] = {"name": section_name, "questions": []}
                sections.append(by_section[section_name])
            by_section[section_name]["questions"].append({
                "id": item["id"],
                "question_type": item["question_type"],
                "knowledge_point": item["knowledge_point"],
                "target_mistake_tag": item["target_mistake_tag"],
                "difficulty": item["difficulty"],
                "question": item["question"],
                "answer": item["answer"],
                "explanation": item["explanation"],
                "sort_order": item["sort_order"],
                "requires_diagram": bool(item["requires_diagram"]),
                "diagram_json": item["diagram_json"],
            })
        worksheets.append({"metadata": worksheet, "worksheet": {
            "title": worksheet["title"],
            "date": worksheet["date"],
            "student_id": worksheet["student_id"],
            "sections": sections,
        }})
    return worksheets


def _default_context() -> dict[str, Any]:
    try:
        return load_rule_registry().resolve_learning_context()
    except RuleRegistryError:
        return {
            "subject_id": "math",
            "grade_at_time": "",
            "term_at_time": "",
            "curriculum_version_at_time": "",
        }


def _with_default_context(row: dict[str, Any]) -> dict[str, Any]:
    context = _default_context()
    row.setdefault("subject_id", context.get("subject_id", "math"))
    row.setdefault("grade_at_time", context.get("grade_at_time", ""))
    row.setdefault("term_at_time", context.get("term_at_time", ""))
    row.setdefault("curriculum_version_at_time", context.get("curriculum_version_at_time", ""))
    return row
