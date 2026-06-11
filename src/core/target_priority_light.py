from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any


def build_target_priority_light(
    conn: sqlite3.Connection,
    student_id: str,
    subject_id: str,
    grade_at_time: int | str,
    *,
    today: date | str | None = None,
) -> dict[str, Any]:
    anchor = _coerce_date(today) or date.today()
    rows = conn.execute(
        """
        SELECT knowledge_point_id, primary_mistake_tag_code, date, diagnosis_confidence
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
        (student_id, subject_id, int(grade_at_time)),
    ).fetchall()

    buckets: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {
        "mistakes_7d": 0,
        "mistakes_30d": 0,
        "latest_mistake_at": None,
        "confidences": [],
    })
    for row in rows:
        row_date = _coerce_date(row["date"])
        if row_date is None:
            continue
        if row_date < anchor - timedelta(days=30):
            continue
        key = (str(row["knowledge_point_id"]), str(row["primary_mistake_tag_code"]))
        bucket = buckets[key]
        if row_date >= anchor - timedelta(days=7):
            bucket["mistakes_7d"] += 1
        bucket["mistakes_30d"] += 1
        latest = bucket["latest_mistake_at"]
        if latest is None or row_date.isoformat() > latest:
            bucket["latest_mistake_at"] = row_date.isoformat()
        confidence = row["diagnosis_confidence"]
        if confidence is not None:
            bucket["confidences"].append(float(confidence))

    items: list[dict[str, Any]] = []
    for (knowledge_point_id, mistake_tag_code), bucket in buckets.items():
        confidence_avg = _average(bucket["confidences"])
        priority_band = _priority_band(bucket["mistakes_7d"], bucket["mistakes_30d"], confidence_avg)
        items.append({
            "target_id": f"{knowledge_point_id}::{mistake_tag_code}",
            "knowledge_point_id": knowledge_point_id,
            "mistake_tag_code": mistake_tag_code,
            "mistakes_7d": bucket["mistakes_7d"],
            "mistakes_30d": bucket["mistakes_30d"],
            "latest_mistake_at": bucket["latest_mistake_at"],
            "confidence_avg": confidence_avg,
            "priority_band": priority_band,
            "reason": _reason(priority_band, bucket["mistakes_7d"], bucket["mistakes_30d"], confidence_avg),
        })
    items.sort(key=lambda item: ({"high": 3, "medium": 2, "low": 1}[item["priority_band"]], item["mistakes_30d"], item["latest_mistake_at"] or ""), reverse=True)
    return {
        "protocol": "v0.1.9-pretrial target_priority_light",
        "student_id": student_id,
        "subject_id": subject_id,
        "grade_at_time": int(grade_at_time),
        "items": items,
        "message": "" if items else "No recent confirmed mistakes are available for target_priority_light.",
    }


def _priority_band(mistakes_7d: int, mistakes_30d: int, confidence_avg: float | None) -> str:
    if mistakes_30d >= 2:
        return "high"
    if mistakes_7d >= 1 and confidence_avg is not None and confidence_avg >= 0.7:
        return "high"
    if mistakes_30d == 1:
        return "medium"
    return "low"


def _reason(priority_band: str, mistakes_7d: int, mistakes_30d: int, confidence_avg: float | None) -> str:
    if priority_band == "high":
        return "Recent repeated confirmed mistakes or high-confidence recent mistake."
    if priority_band == "medium":
        return "One confirmed mistake in the last 30 days; worth observing."
    if confidence_avg is None:
        return "No recent confirmed evidence with confidence."
    return "Low recent evidence; use only for light mixed review."


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _coerce_date(value: date | str | None) -> date | None:
    if value in (None, ""):
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
