from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.core.duplicate_guard import scan_duplicate_mistake_groups, scan_duplicate_worksheet_groups
from src.core.rule_registry import RuleRegistryError, load_rule_registry
from src.db import now_iso


SUPPORTED_STATUSES = {"needs_confirmation", "confirmed"}


def data_overview(conn: sqlite3.Connection, backup_dir: str | Path | None = None) -> dict[str, Any]:
    backup_files = latest_backup_files(backup_dir) if backup_dir else []
    seven_days_ago = (datetime.now() - timedelta(days=7)).replace(microsecond=0).isoformat()
    return {
        "mistakes_total": _count(conn, "mistakes"),
        "needs_confirmation": _count_where(conn, "mistakes", "status = ?", ("needs_confirmation",)),
        "confirmed": _count_where(conn, "mistakes", "status = ?", ("confirmed",)),
        "worksheets_total": _count(conn, "worksheets"),
        "worksheet_items_total": _count(conn, "worksheet_items"),
        "recent_imports_7_days": _count_where(conn, "mistakes", "created_at >= ?", (seven_days_ago,)),
        "recent_backups": [str(path) for path in backup_files],
    }


def filter_mistakes(
    conn: sqlite3.Connection,
    student_id: str | list[str] | None = None,
    subject_id: str | list[str] | None = None,
    grade_at_time: str | int | list[str] | None = None,
    status: str | list[str] | None = None,
    source: str | list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    mistake_tag: str | list[str] | None = None,
    question_type: str | list[str] | None = None,
    knowledge_point: str | list[str] | None = None,
    difficulty: str | list[str] | None = None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    existing_columns = _table_columns(conn, "mistakes")
    _add_filter(where, params, "student_id", student_id, existing_columns)
    _add_filter(where, params, "subject_id", subject_id, existing_columns)
    _add_filter(where, params, "grade_at_time", grade_at_time, existing_columns)
    _add_filter(where, params, "status", status, existing_columns)
    _add_filter(where, params, "source", source, existing_columns)
    _add_filter(where, params, "mistake_tag", mistake_tag, existing_columns)
    _add_filter(where, params, "question_type", question_type, existing_columns)
    _add_filter(where, params, "knowledge_point", knowledge_point, existing_columns)
    _add_filter(where, params, "difficulty", difficulty, existing_columns)
    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to)
    select_columns = [
        "id",
        "student_id",
        "subject_id",
        "grade_at_time",
        "term_at_time",
        "curriculum_version_at_time",
        "date",
        "status",
        "source",
        "question_type",
        "knowledge_point",
        "mistake_tag",
        "difficulty",
        "question_summary",
        "created_at",
        "updated_at",
    ]
    selected = [column for column in select_columns if column in existing_columns]
    sql = f"SELECT {', '.join(selected)} FROM mistakes"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC"
    rows = [_with_default_context(dict(row)) for row in conn.execute(sql, tuple(params)).fetchall()]
    return _apply_virtual_context_filters(rows, subject_id=subject_id, grade_at_time=grade_at_time, existing_columns=existing_columns)


def missing_mistake_context_columns(conn: sqlite3.Connection) -> list[str]:
    existing_columns = _table_columns(conn, "mistakes")
    return [
        column
        for column in ("subject_id", "grade_at_time", "term_at_time", "curriculum_version_at_time")
        if column not in existing_columns
    ]


def batch_confirm_mistakes(conn: sqlite3.Connection, ids: list[int]) -> int:
    return _batch_update_status(conn, ids, "confirmed", current_status="needs_confirmation")


def batch_revoke_mistakes(conn: sqlite3.Connection, ids: list[int]) -> int:
    return _batch_update_status(conn, ids, "needs_confirmation", current_status="confirmed")


def batch_delete_mistakes(conn: sqlite3.Connection, ids: list[int], confirm_delete: bool = False) -> int:
    normalized_ids = _normalize_ids(ids)
    if not normalized_ids:
        return 0
    if not confirm_delete:
        raise ValueError("批量删除需要显式二次确认；建议先备份数据库。")
    placeholders = ", ".join("?" for _ in normalized_ids)
    cur = conn.execute(f"DELETE FROM mistakes WHERE id IN ({placeholders})", tuple(normalized_ids))
    conn.commit()
    return int(cur.rowcount)


def scan_mistake_duplicates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return scan_duplicate_mistake_groups(conn)


def scan_worksheet_duplicates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return scan_duplicate_worksheet_groups(conn)


def latest_backup_files(backup_dir: str | Path, limit: int = 5) -> list[Path]:
    path = Path(backup_dir)
    if not path.exists():
        return []
    return sorted(path.glob("math_tutor_*.db"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]


def _batch_update_status(
    conn: sqlite3.Connection,
    ids: list[int],
    target_status: str,
    current_status: str | None = None,
) -> int:
    if target_status not in SUPPORTED_STATUSES:
        raise ValueError(f"Unsupported status: {target_status}")
    normalized_ids = _normalize_ids(ids)
    if not normalized_ids:
        return 0
    placeholders = ", ".join("?" for _ in normalized_ids)
    params: list[Any] = [target_status, now_iso(), *normalized_ids]
    sql = f"UPDATE mistakes SET status = ?, updated_at = ? WHERE id IN ({placeholders})"
    if current_status:
        sql += " AND status = ?"
        params.append(current_status)
    cur = conn.execute(sql, tuple(params))
    conn.commit()
    return int(cur.rowcount)


def _normalize_ids(ids: list[int]) -> list[int]:
    result: list[int] = []
    for value in ids:
        record_id = int(value)
        if record_id not in result:
            result.append(record_id)
    return result


def _add_filter(
    where: list[str],
    params: list[Any],
    column: str,
    value: str | int | list[str] | None,
    existing_columns: set[str],
) -> None:
    if value is None or value == "" or value == "全部":
        return
    if column not in existing_columns:
        return
    if isinstance(value, list):
        values = [item for item in value if item and item != "全部"]
        if not values:
            return
        placeholders = ", ".join("?" for _ in values)
        where.append(f"{column} IN ({placeholders})")
        params.extend(values)
        return
    where.append(f"{column} = ?")
    params.append(value)


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _count_where(conn: sqlite3.Connection, table: str, where: str, params: tuple[Any, ...]) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0])


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


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
    row.setdefault("student_id", "")
    row.setdefault("subject_id", context.get("subject_id", "math"))
    row.setdefault("grade_at_time", context.get("grade_at_time", ""))
    row.setdefault("term_at_time", context.get("term_at_time", ""))
    row.setdefault("curriculum_version_at_time", context.get("curriculum_version_at_time", ""))
    return row


def _apply_virtual_context_filters(
    rows: list[dict[str, Any]],
    subject_id: str | list[str] | None,
    grade_at_time: str | int | list[str] | None,
    existing_columns: set[str],
) -> list[dict[str, Any]]:
    result = rows
    if subject_id not in (None, "", "全部") and "subject_id" not in existing_columns:
        subject_values = set(subject_id if isinstance(subject_id, list) else [subject_id])
        result = [row for row in result if str(row.get("subject_id", "")) in {str(value) for value in subject_values}]
    if grade_at_time not in (None, "", "全部") and "grade_at_time" not in existing_columns:
        grade_values = set(grade_at_time if isinstance(grade_at_time, list) else [grade_at_time])
        result = [row for row in result if str(row.get("grade_at_time", "")) in {str(value) for value in grade_values}]
    return result
