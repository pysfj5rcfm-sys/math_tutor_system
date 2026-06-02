from datetime import date

from src.core.mistakes import import_mistakes_payload
from src.core.stats import cross_stat, tag_frequency
from src.db import confirm_record


def test_recent_7_days_stats_only_confirmed_by_default(conn):
    import_mistakes_payload(conn, {"mistakes": [_mistake("2026-05-27", "C3"), _mistake("2026-05-20", "M3")]})
    first_id = conn.execute("SELECT id FROM mistakes WHERE primary_mistake_tag_code = 'C3'").fetchone()[0]
    confirm_record(conn, "mistakes", first_id)
    rows = tag_frequency(conn, 7, include_unconfirmed=False, today=date(2026, 5, 27))
    assert rows == [{"mistake_tag": "C3", "count": 1}]
    debug_rows = tag_frequency(conn, 30, include_unconfirmed=True, today=date(2026, 5, 27))
    assert {row["mistake_tag"] for row in debug_rows} == {"C3", "M3"}


def test_cross_stat_by_question_type(conn):
    import_mistakes_payload(conn, {"mistakes": [_mistake("2026-05-27", "C3")]})
    first_id = conn.execute("SELECT id FROM mistakes").fetchone()[0]
    confirm_record(conn, "mistakes", first_id)
    rows = cross_stat(conn, "question_type")
    assert rows[0]["mistake_tag"] == "C3"
    assert rows[0]["question_type"] == "math_calculation"
    assert rows[0]["count"] == 1


def _mistake(day: str, tag: str):
    return {
        "date": day,
        "question_type": "递等式计算" if tag == "C3" else "应用题",
        "knowledge_point": "小数计算" if tag == "C3" else "倍数关系",
        "mistake_tag": tag,
        "difficulty": "基础",
        "question_summary": "摘要",
    }
