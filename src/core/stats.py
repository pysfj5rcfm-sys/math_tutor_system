from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any


def _status_clause(include_unconfirmed: bool) -> tuple[str, tuple[Any, ...]]:
    if include_unconfirmed:
        return "", ()
    return " AND status = ?", ("confirmed",)


def _student_clause(student_id: str | None) -> tuple[str, tuple[Any, ...]]:
    if not student_id:
        return "", ()
    return " AND student_id = ?", (student_id,)


def tag_frequency(
    conn: sqlite3.Connection,
    days: int,
    include_unconfirmed: bool = False,
    today: date | None = None,
    student_id: str | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    start = (today - timedelta(days=days - 1)).isoformat()
    clause, params = _status_clause(include_unconfirmed)
    student_clause, student_params = _student_clause(student_id)
    rows = conn.execute(
        f"""
        SELECT primary_mistake_tag_code AS mistake_tag, COUNT(*) AS count
        FROM mistakes
        WHERE date >= ?{clause}{student_clause}
        GROUP BY primary_mistake_tag_code
        ORDER BY count DESC, primary_mistake_tag_code
        """,
        (start, *params, *student_params),
    ).fetchall()
    return [dict(row) for row in rows]


def cross_stat(
    conn: sqlite3.Connection,
    column: str,
    include_unconfirmed: bool = False,
    days: int | None = None,
    today: date | None = None,
    student_id: str | None = None,
) -> list[dict[str, Any]]:
    column_map = {
        "question_type": "question_type_code",
        "knowledge_point": "knowledge_point_id",
        "difficulty": "difficulty_code",
        "question_type_code": "question_type_code",
        "knowledge_point_id": "knowledge_point_id",
        "difficulty_code": "difficulty_code",
    }
    if column not in column_map:
        raise ValueError("Unsupported cross stat column")
    db_column = column_map[column]
    where = ["1=1"]
    params: list[Any] = []
    if days:
        today = today or date.today()
        where.append("date >= ?")
        params.append((today - timedelta(days=days - 1)).isoformat())
    if not include_unconfirmed:
        where.append("status = ?")
        params.append("confirmed")
    if student_id:
        where.append("student_id = ?")
        params.append(student_id)
    rows = conn.execute(
        f"""
        SELECT primary_mistake_tag_code AS mistake_tag, {db_column} AS {column}, COUNT(*) AS count
        FROM mistakes
        WHERE {' AND '.join(where)}
        GROUP BY primary_mistake_tag_code, {db_column}
        ORDER BY count DESC, primary_mistake_tag_code, {db_column}
        """,
        tuple(params),
    ).fetchall()
    return [dict(row) for row in rows]


def top_tags(
    conn: sqlite3.Connection,
    limit: int = 5,
    include_unconfirmed: bool = False,
    student_id: str | None = None,
) -> list[dict[str, Any]]:
    clause, params = _status_clause(include_unconfirmed)
    student_clause, student_params = _student_clause(student_id)
    rows = conn.execute(
        f"""
        SELECT primary_mistake_tag_code AS mistake_tag, COUNT(*) AS count
        FROM mistakes
        WHERE 1=1{clause}{student_clause}
        GROUP BY primary_mistake_tag_code
        ORDER BY count DESC, primary_mistake_tag_code
        LIMIT ?
        """,
        (*params, *student_params, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def missing_data_alerts(
    conn: sqlite3.Connection,
    include_unconfirmed: bool = False,
    today: date | None = None,
    student_id: str | None = None,
) -> list[str]:
    today = today or date.today()
    start = (today - timedelta(days=6)).isoformat()
    clause, params = _status_clause(include_unconfirmed)
    student_clause, student_params = _student_clause(student_id)
    geometry_count = conn.execute(
        f"""
        SELECT COUNT(*) FROM mistakes
        WHERE date >= ? AND (question_type_code LIKE 'math_geometry%' OR knowledge_point_id LIKE '%area%' OR knowledge_point_id LIKE '%volume%'){clause}{student_clause}
        """,
        (start, *params, *student_params),
    ).fetchone()[0]
    alerts = []
    if geometry_count == 0:
        alerts.append("最近 7 天没有几何题记录，但学生画像中 geometry 是重点方向。")
    return alerts


def stats_summary(
    conn: sqlite3.Connection,
    include_unconfirmed: bool = False,
    today: date | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    return {
        "student_id": student_id,
        "recent_7_days": tag_frequency(conn, 7, include_unconfirmed, today, student_id),
        "recent_30_days": tag_frequency(conn, 30, include_unconfirmed, today, student_id),
        "mistake_tag_by_question_type": cross_stat(conn, "question_type", include_unconfirmed, student_id=student_id),
        "mistake_tag_by_knowledge_point": cross_stat(conn, "knowledge_point", include_unconfirmed, student_id=student_id),
        "mistake_tag_by_difficulty": cross_stat(conn, "difficulty", include_unconfirmed, student_id=student_id),
        "top_5": top_tags(conn, 5, include_unconfirmed, student_id),
        "missing_alerts": missing_data_alerts(conn, include_unconfirmed, today, student_id),
    }
