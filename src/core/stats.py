from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any


def _status_clause(include_unconfirmed: bool) -> tuple[str, tuple[Any, ...]]:
    if include_unconfirmed:
        return "", ()
    return " AND status = ?", ("confirmed",)


def tag_frequency(conn: sqlite3.Connection, days: int, include_unconfirmed: bool = False, today: date | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    start = (today - timedelta(days=days - 1)).isoformat()
    clause, params = _status_clause(include_unconfirmed)
    rows = conn.execute(
        f"""
        SELECT mistake_tag, COUNT(*) AS count
        FROM mistakes
        WHERE date >= ?{clause}
        GROUP BY mistake_tag
        ORDER BY count DESC, mistake_tag
        """,
        (start, *params),
    ).fetchall()
    return [dict(row) for row in rows]


def cross_stat(
    conn: sqlite3.Connection,
    column: str,
    include_unconfirmed: bool = False,
    days: int | None = None,
    today: date | None = None,
) -> list[dict[str, Any]]:
    if column not in {"question_type", "knowledge_point", "difficulty"}:
        raise ValueError("Unsupported cross stat column")
    where = ["1=1"]
    params: list[Any] = []
    if days:
        today = today or date.today()
        where.append("date >= ?")
        params.append((today - timedelta(days=days - 1)).isoformat())
    if not include_unconfirmed:
        where.append("status = ?")
        params.append("confirmed")
    rows = conn.execute(
        f"""
        SELECT mistake_tag, {column}, COUNT(*) AS count
        FROM mistakes
        WHERE {' AND '.join(where)}
        GROUP BY mistake_tag, {column}
        ORDER BY count DESC, mistake_tag, {column}
        """,
        tuple(params),
    ).fetchall()
    return [dict(row) for row in rows]


def top_tags(conn: sqlite3.Connection, limit: int = 5, include_unconfirmed: bool = False) -> list[dict[str, Any]]:
    clause, params = _status_clause(include_unconfirmed)
    rows = conn.execute(
        f"""
        SELECT mistake_tag, COUNT(*) AS count
        FROM mistakes
        WHERE 1=1{clause}
        GROUP BY mistake_tag
        ORDER BY count DESC, mistake_tag
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def missing_data_alerts(conn: sqlite3.Connection, include_unconfirmed: bool = False, today: date | None = None) -> list[str]:
    today = today or date.today()
    start = (today - timedelta(days=6)).isoformat()
    clause, params = _status_clause(include_unconfirmed)
    geometry_count = conn.execute(
        f"""
        SELECT COUNT(*) FROM mistakes
        WHERE date >= ? AND (question_type LIKE '几何%' OR knowledge_point LIKE '%面积%' OR knowledge_point LIKE '%体积%'){clause}
        """,
        (start, *params),
    ).fetchone()[0]
    alerts = []
    if geometry_count == 0:
        alerts.append("最近 7 天没有几何题记录，但学生画像中 geometry 是重点方向。")
    return alerts


def stats_summary(conn: sqlite3.Connection, include_unconfirmed: bool = False, today: date | None = None) -> dict[str, Any]:
    return {
        "recent_7_days": tag_frequency(conn, 7, include_unconfirmed, today),
        "recent_30_days": tag_frequency(conn, 30, include_unconfirmed, today),
        "mistake_tag_by_question_type": cross_stat(conn, "question_type", include_unconfirmed),
        "mistake_tag_by_knowledge_point": cross_stat(conn, "knowledge_point", include_unconfirmed),
        "mistake_tag_by_difficulty": cross_stat(conn, "difficulty", include_unconfirmed),
        "top_5": top_tags(conn, 5, include_unconfirmed),
        "missing_alerts": missing_data_alerts(conn, include_unconfirmed, today),
    }
