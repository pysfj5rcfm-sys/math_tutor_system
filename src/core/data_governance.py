from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.core.duplicate_guard import scan_duplicate_mistake_groups, scan_duplicate_worksheet_groups
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
    _add_filter(where, params, "status", status)
    _add_filter(where, params, "source", source)
    _add_filter(where, params, "mistake_tag", mistake_tag)
    _add_filter(where, params, "question_type", question_type)
    _add_filter(where, params, "knowledge_point", knowledge_point)
    _add_filter(where, params, "difficulty", difficulty)
    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to)
    sql = """
        SELECT id, date, status, source, question_type, knowledge_point,
               mistake_tag, difficulty, question_summary, created_at, updated_at
        FROM mistakes
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC"
    return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]


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


def _add_filter(where: list[str], params: list[Any], column: str, value: str | list[str] | None) -> None:
    if value is None or value == "" or value == "全部":
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
