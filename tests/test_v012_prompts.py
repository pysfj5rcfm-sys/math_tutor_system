from datetime import date

from src.core.mistake_tags import tags_as_dicts
from src.core.stats import stats_summary
from src.core.student_profile import load_student_profile
from src.prompts.worksheet_prompt import build_worksheet_prompt


def test_worksheet_prompt_contains_v012_yaml_rules(conn):
    prompt = build_worksheet_prompt(load_student_profile(), stats_summary(conn, today=date(2026, 5, 27)), tags_as_dicts())
    assert "worksheet 下字段缩进 2 个空格" in prompt
    assert "sections 列表项缩进 4 个空格" in prompt
    assert "questions 列表项缩进 8 个空格" in prompt
    assert "question_type 只能使用 MVP 合法枚举" in prompt
    assert "knowledge_point 必须优先使用 MVP 初始合法值" in prompt
    assert "target_mistake_tag 只能使用上方错因标签 code" in prompt
    assert "v0.1.2 暂不输出 diagram" in prompt
    assert "依据 confirmed 错因统计动态分配" in prompt
    assert "不得把 UAT 样例数据当成真实学生错因" in prompt
    assert "不得机械固定为 4+3+2+2+3" in prompt
    assert "不得机械固定 C3/F3/R4/U1/K3/G1 权重" in prompt
