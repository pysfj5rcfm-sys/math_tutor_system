from datetime import date

from src.core.mistake_tags import tags_as_dicts
from src.core.mistakes import import_mistakes_payload
from src.core.stats import stats_summary
from src.core.student_profile import load_student_profile
from src.db import confirm_record
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt


def test_prompt_generation_contains_required_context(conn):
    import_mistakes_payload(conn, {"mistakes": [{
        "date": "2026-05-27",
        "question_type": "递等式计算",
        "knowledge_point": "小数计算",
        "mistake_tag": "C3",
        "difficulty": "基础",
        "question_summary": "摘要",
    }]})
    confirm_record(conn, "mistakes", 1)
    profile = load_student_profile()
    stats = stats_summary(conn, today=date(2026, 5, 27))
    marking = build_marking_prompt(profile, tags_as_dicts(), subject_id="math")
    worksheet = build_worksheet_prompt(profile, stats, tags_as_dicts(), subject_id="math")
    assert "student_profile" in marking
    assert "mistake_tags" in marking
    assert "合法 question_type_code 枚举" in marking
    assert "mistakes.yaml schema" in marking
    assert "student_profile" in worksheet
    assert "mistake_tags" in worksheet
    assert "question_type_code" in worksheet
    assert "recent_7_days_stats" in worksheet
    assert "recent_30_days_stats" in worksheet
    assert "worksheet.yaml schema" in worksheet
    assert "试卷格式要求" in worksheet
    assert "worksheet_policy" in worksheet
    assert "C3" in worksheet
