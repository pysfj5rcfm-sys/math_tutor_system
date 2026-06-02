from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.core.stats import cross_stat, missing_data_alerts, tag_frequency, top_tags
from src.db import now_iso
from src.prompts.review_prompt import build_review_analysis_prompt
from src.schemas.mistake_schema import DEFAULT_STUDENT_ID, DEFAULT_TENANT_ID


ROOT = Path(__file__).resolve().parents[2]


def generate_weekly_review(
    conn: sqlite3.Connection,
    profile: dict[str, Any],
    week_end: date | None = None,
    output_dir: str | Path = ROOT / "outputs" / "reviews",
) -> Path:
    week_end = week_end or date.today()
    week_start = week_end - timedelta(days=6)
    stats = {
        "top_tags": top_tags(conn, include_unconfirmed=False),
        "tag_by_type": cross_stat(conn, "question_type_code", include_unconfirmed=False, days=7, today=week_end),
        "tag_by_knowledge": cross_stat(conn, "knowledge_point_id", include_unconfirmed=False, days=7, today=week_end),
        "missing_alerts": missing_data_alerts(conn, include_unconfirmed=False, today=week_end),
    }
    prompt = build_review_analysis_prompt(profile, stats)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"))
    md = env.get_template("weekly_review.md.j2").render(
        profile=profile,
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        top_tags=stats["top_tags"],
        tag_by_type=stats["tag_by_type"],
        tag_by_knowledge=stats["tag_by_knowledge"],
        coverage=["已统计 confirmed 错题记录；未确认记录默认不纳入复盘。"],
        missing_alerts=stats["missing_alerts"],
        gpt_prompt=prompt,
    )
    out = Path(output_dir) / f"weekly_review_{week_start.isoformat()}_{week_end.isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO weekly_reviews (
            student_id, week_start, week_end, stats_summary,
            gpt_analysis_imported, profile_update_suggestions, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, '', '[]', 'generated', ?, ?)
        """,
        (
            profile.get("student_id", DEFAULT_STUDENT_ID),
            week_start.isoformat(),
            week_end.isoformat(),
            json.dumps(stats, ensure_ascii=False),
            ts,
            ts,
        ),
    )
    conn.commit()
    return out
