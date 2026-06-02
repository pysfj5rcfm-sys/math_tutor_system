from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.core.paths import DEFAULT_DB_PATH
from src.core.rule_registry import RuleRegistryError, load_rule_registry
from src.db import SCHEMA_VERSION, get_connection


REQUIRED_TABLES = {
    "schema_meta",
    "import_batches",
    "mistake_tags",
    "mistakes",
    "worksheets",
    "worksheet_items",
}

FORBIDDEN_COLUMNS = {
    "mistakes": {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"},
    "worksheets": {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"},
    "worksheet_items": {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"},
}

REQUIRED_COLUMNS = {
    "mistakes": {"question_type_code", "knowledge_point_id", "primary_mistake_tag_code", "difficulty_code"},
    "worksheet_items": {"question_type_code", "knowledge_point_id", "target_mistake_tag_code", "difficulty_code"},
}


def check_schema_integrity(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, list[dict[str, Any]]]:
    report: dict[str, list[dict[str, Any]]] = {"errors": [], "warnings": [], "info": []}
    path = Path(db_path)
    if path.resolve() != DEFAULT_DB_PATH.resolve():
        _add(report, "errors", "invalid_db_path", f"Current DB path is not data/edu_tutor.db: {path}")
    else:
        _add(report, "info", "db_path", str(path))
    if not path.exists():
        _add(report, "errors", "missing_db", f"DB does not exist: {path}")
        return report

    with get_connection(path) as conn:
        _check_tables(conn, report)
        _check_schema_meta(conn, report)
        _check_columns(conn, report)
        _check_domain_values(conn, report)
        _check_orphans(conn, report)
        _check_duplicate_hashes(conn, report)
        _check_sample_confirmed(conn, report)
    return report


def _check_tables(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    tables = _tables(conn)
    missing = sorted(REQUIRED_TABLES - tables)
    for table in missing:
        _add(report, "errors", "missing_table", table)
    _add(report, "info", "tables", sorted(tables))


def _check_schema_meta(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    if "schema_meta" not in _tables(conn):
        return
    rows = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM schema_meta").fetchall()}
    if rows.get("schema_version") != SCHEMA_VERSION:
        _add(report, "errors", "invalid_schema_version", rows.get("schema_version"))
    if rows.get("project_name") != "edu_tutor_system":
        _add(report, "errors", "invalid_project_name", rows.get("project_name"))
    if rows.get("db_name") != "edu_tutor.db":
        _add(report, "errors", "invalid_db_name", rows.get("db_name"))
    _add(report, "info", "schema_meta", rows)


def _check_columns(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    for table, forbidden in FORBIDDEN_COLUMNS.items():
        if table not in _tables(conn):
            continue
        columns = _columns(conn, table)
        for column in sorted(forbidden & columns):
            _add(report, "errors", "legacy_column_present", f"{table}.{column}")
    for table, required in REQUIRED_COLUMNS.items():
        if table not in _tables(conn):
            continue
        columns = _columns(conn, table)
        for column in sorted(required - columns):
            _add(report, "errors", "missing_canonical_column", f"{table}.{column}")


def _check_domain_values(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    try:
        registry = load_rule_registry()
    except RuleRegistryError as exc:
        _add(report, "errors", "registry_load_failed", str(exc))
        return
    students = {item["student_id"] for item in registry.get_students(active_only=False)}
    subjects = {item["subject_id"] for item in registry.get_subjects(active_only=False)}
    difficulties = set(registry.get_difficulty_codes(active_only=True))
    for row in conn.execute("SELECT * FROM mistakes").fetchall():
        item = dict(row)
        label = f"mistakes[{item.get('id')}]"
        _check_common_record(item, label, students, subjects, difficulties, registry, report)
        tags = {tag["code"] for tag in registry.get_mistake_tags_for_subject(item.get("subject_id", ""))}
        if item.get("primary_mistake_tag_code") not in tags:
            _add(report, "errors", "invalid_mistake_tag_code", f"{label}.{item.get('primary_mistake_tag_code')}")
    for row in conn.execute(
        """
        SELECT wi.*, w.student_id, w.subject_id, w.grade_at_time, w.curriculum_version_at_time
        FROM worksheet_items wi JOIN worksheets w ON w.id = wi.worksheet_id
        """
    ).fetchall():
        item = dict(row)
        label = f"worksheet_items[{item.get('id')}]"
        _check_common_record(item, label, students, subjects, difficulties, registry, report)
        tags = {tag["code"] for tag in registry.get_mistake_tags_for_subject(item.get("subject_id", ""))}
        if item.get("target_mistake_tag_code") and item.get("target_mistake_tag_code") not in tags:
            _add(report, "errors", "invalid_mistake_tag_code", f"{label}.{item.get('target_mistake_tag_code')}")


def _check_common_record(
    item: dict[str, Any],
    label: str,
    students: set[str],
    subjects: set[str],
    difficulties: set[str],
    registry: Any,
    report: dict[str, list[dict[str, Any]]],
) -> None:
    if item.get("student_id") not in students:
        _add(report, "errors", "invalid_student_id", f"{label}.{item.get('student_id')}")
    if item.get("subject_id") not in subjects:
        _add(report, "errors", "invalid_subject_id", f"{label}.{item.get('subject_id')}")
    try:
        grade = int(item.get("grade_at_time"))
        if grade < 1 or grade > 12:
            raise ValueError
    except (TypeError, ValueError):
        _add(report, "errors", "invalid_grade_at_time", f"{label}.{item.get('grade_at_time')}")
        return
    qtypes = {qt["code"] for qt in registry.get_question_types_for_subject(item.get("subject_id", ""))}
    if item.get("question_type_code") not in qtypes:
        _add(report, "errors", "invalid_question_type_code", f"{label}.{item.get('question_type_code')}")
    if item.get("difficulty_code") not in difficulties:
        _add(report, "errors", "invalid_difficulty_code", f"{label}.{item.get('difficulty_code')}")
    kp = item.get("knowledge_point_id")
    if kp:
        points = {
            point["knowledge_point_id"]
            for point in registry.get_knowledge_points_for_context(
                item.get("subject_id", ""),
                grade,
                item.get("curriculum_version_at_time") or "cn_k12_2022",
            )
        }
        if kp not in points:
            _add(report, "errors", "invalid_knowledge_point_id", f"{label}.{kp}")


def _check_orphans(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM worksheet_items wi
        LEFT JOIN worksheets w ON w.id = wi.worksheet_id
        WHERE w.id IS NULL
        """
    ).fetchone()[0]
    if count:
        _add(report, "errors", "orphan_worksheet_items", int(count))


def _check_duplicate_hashes(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    for table, column in (("mistakes", "record_hash"), ("worksheets", "worksheet_hash")):
        rows = conn.execute(
            f"""
            SELECT {column} AS hash_value, COUNT(*) AS count
            FROM {table}
            WHERE {column} IS NOT NULL AND {column} != ''
            GROUP BY {column}
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        for row in rows:
            _add(report, "warnings", "duplicate_hash", f"{table}.{row['hash_value']} count={row['count']}")


def _check_sample_confirmed(conn: sqlite3.Connection, report: dict[str, list[dict[str, Any]]]) -> None:
    count = conn.execute(
        """
        SELECT COUNT(*) FROM mistakes
        WHERE status = 'confirmed'
          AND (source LIKE '%sample%' OR source LIKE '%UAT%' OR source LIKE '%uat%')
        """
    ).fetchone()[0]
    if count:
        _add(report, "warnings", "sample_data_confirmed", int(count))


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add(report: dict[str, list[dict[str, Any]]], level: str, code: str, detail: Any) -> None:
    report[level].append({"code": code, "detail": detail})
