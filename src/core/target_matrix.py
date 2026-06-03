from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import yaml


def build_target_matrix_from_confirmed_mistakes(
    conn: sqlite3.Connection,
    student_id: str,
    subject_id: str,
    grade_at_time: int | str,
    *,
    today: date | str | None = None,
) -> dict[str, Any]:
    """Build a read-only X/Y target matrix from confirmed canonical mistake rows."""
    anchor = _coerce_date(today) or date.today()
    grade = int(grade_at_time)
    rows = conn.execute(
        """
        SELECT knowledge_point_id, primary_mistake_tag_code, date
        FROM mistakes
        WHERE student_id = ?
          AND subject_id = ?
          AND grade_at_time = ?
          AND status = 'confirmed'
          AND knowledge_point_id IS NOT NULL
          AND knowledge_point_id != ''
          AND primary_mistake_tag_code IS NOT NULL
          AND primary_mistake_tag_code != ''
        """,
        (student_id, subject_id, grade),
    ).fetchall()
    if not rows:
        return {
            "student_id": student_id,
            "subject_id": subject_id,
            "grade_at_time": grade,
            "items": [],
            "message": "No confirmed mistakes are available for this target matrix yet.",
        }

    buckets: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {
        "count_7d": 0,
        "count_30d": 0,
        "latest_date": "",
    })
    for row in rows:
        row_date = _coerce_date(row["date"])
        if row_date is None:
            continue
        key = (str(row["knowledge_point_id"]), str(row["primary_mistake_tag_code"]))
        bucket = buckets[key]
        if row_date >= anchor - timedelta(days=7):
            bucket["count_7d"] += 1
        if row_date >= anchor - timedelta(days=30):
            bucket["count_30d"] += 1
        if not bucket["latest_date"] or row_date.isoformat() > bucket["latest_date"]:
            bucket["latest_date"] = row_date.isoformat()

    items: list[dict[str, Any]] = []
    for (knowledge_point_id, mistake_tag_code), bucket in buckets.items():
        if bucket["count_30d"] <= 0 and bucket["count_7d"] <= 0:
            continue
        priority = _priority(bucket["count_7d"], bucket["count_30d"], bucket["latest_date"], anchor)
        items.append({
            "knowledge_point_id": knowledge_point_id,
            "primary_mistake_tag_code": mistake_tag_code,
            "count_7d": bucket["count_7d"],
            "count_30d": bucket["count_30d"],
            "latest_date": bucket["latest_date"],
            "priority": priority,
        })
    items.sort(key=lambda item: (item["priority"], item["count_30d"], item["latest_date"]), reverse=True)
    return {
        "student_id": student_id,
        "subject_id": subject_id,
        "grade_at_time": grade,
        "items": items,
        "message": "" if items else "No confirmed mistakes were found in the last 30 days.",
    }


def render_target_matrix_for_prompt(matrix: dict[str, Any]) -> str:
    payload = {
        "protocol": "v0.1.8 primary_mistake_tag_code only",
        "note": (
            "Use each knowledge_point_id x primary_mistake_tag_code pair as a target. "
            "secondary_mistake_tag_codes are explanation-only in v0.1.8."
        ),
        **matrix,
    }
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _coerce_date(value: date | str | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None


def _priority(count_7d: int, count_30d: int, latest_date: str, anchor: date) -> int:
    latest = _coerce_date(latest_date)
    recency_bonus = 0
    if latest is not None:
        age_days = max((anchor - latest).days, 0)
        recency_bonus = max(0, 10 - age_days)
    return min(100, count_30d * 2 + count_7d * 4 + recency_bonus)
