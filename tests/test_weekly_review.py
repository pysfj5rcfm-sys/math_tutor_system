from datetime import date

from src.core.mistakes import import_mistakes_payload
from src.core.student_profile import load_student_profile
from src.db import confirm_record
from src.workflows.review_workflow import generate_weekly_review


def test_weekly_review_markdown_can_generate(conn, tmp_path):
    import_mistakes_payload(conn, {"mistakes": [{
        "date": "2026-05-27",
        "question_type": "递等式计算",
        "knowledge_point": "小数计算",
        "mistake_tag": "C3",
        "difficulty": "基础",
        "question_summary": "摘要",
    }]})
    confirm_record(conn, "mistakes", 1)
    path = generate_weekly_review(conn, load_student_profile(), date(2026, 5, 27), tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.exists()
    assert "本周高频错因" in text
    assert "画像更新建议字段预留" in text
