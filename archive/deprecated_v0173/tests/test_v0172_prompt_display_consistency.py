from __future__ import annotations

from datetime import datetime

import pytest
import yaml

from src.core.backup_export import export_mistakes_csv, export_mistakes_yaml
from src.core.display import (
    difficulty_display,
    knowledge_point_display,
    mistake_tag_display,
    question_type_display,
)
from src.core.duplicate_guard import detect_duplicate_mistakes
from src.core.rule_registry import load_rule_registry
from src.prompts.marking_prompt import build_marking_prompt, save_marking_prompt
from src.prompts.repair_prompt import build_validation_repair_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt, save_worksheet_prompt


MOJIBAKE_PATTERNS = ("�", "Ã", "Â", "â€", "â€™", "ä¸", "çš", "ï»¿")


def test_marking_prompts_are_subject_scoped():
    profile = {"student_id": "daughter"}
    math_prompt = build_marking_prompt(profile, subject_id="math")
    chinese_prompt = build_marking_prompt(profile, subject_id="chinese")
    english_prompt = build_marking_prompt(profile, subject_id="english")

    assert "math_g6_number_operations" in math_prompt
    assert "chinese_g6_text_evidence" not in math_prompt
    assert "ENG_GRAM_1" not in math_prompt

    assert "chinese_g6_text_evidence" in chinese_prompt
    assert "CHN_EVD_1" in chinese_prompt
    assert "ENG_GRAM_1" not in chinese_prompt

    assert "english_g6_reading_detail" in english_prompt
    assert "ENG_GRAM_1" in english_prompt
    assert "CHN_EVD_1" not in english_prompt

    legacy_kp = load_rule_registry().get_legacy_knowledge_points(active_only=False)[0]["code"]
    for prompt in (math_prompt, chinese_prompt, english_prompt):
        assert "daughter_grade5" not in prompt
        assert legacy_kp not in prompt


def test_worksheet_prompts_are_subject_scoped_and_policy_filtered():
    profile = {"student_id": "daughter"}
    stats = {"recent_7_days": [], "recent_30_days": []}

    math_prompt = build_worksheet_prompt(profile, stats, subject_id="math")
    chinese_prompt = build_worksheet_prompt(profile, stats, subject_id="chinese")
    english_prompt = build_worksheet_prompt(profile, stats, subject_id="english")

    assert "math_g6_default" in math_prompt
    assert "chinese_g6_default" not in math_prompt
    assert "english_g6_default" not in math_prompt

    assert "chinese_g6_default" in chinese_prompt
    assert "english_g6_default" not in chinese_prompt
    assert "ENG_GRAM_1" not in chinese_prompt

    assert "english_g6_default" in english_prompt
    assert "chinese_g6_default" not in english_prompt
    assert "CHN_EVD_1" not in english_prompt


def test_missing_subject_does_not_generate_all_subject_prompt():
    with pytest.raises(ValueError, match="subject_id is required"):
        build_marking_prompt({"student_id": "daughter"})
    with pytest.raises(ValueError, match="subject_id is required"):
        build_worksheet_prompt({"student_id": "daughter"}, {"recent_7_days": [], "recent_30_days": []})


def test_prompts_and_templates_do_not_contain_common_mojibake():
    profile = {"student_id": "daughter"}
    stats = {"recent_7_days": [], "recent_30_days": []}
    original = """
mistakes:
  - student_id: daughter
    subject_id: chinese
    grade_at_time: 6
    curriculum_version_at_time: cn_k12_2022
"""
    prompts = [
        build_marking_prompt(profile, subject_id="chinese"),
        build_worksheet_prompt(profile, stats, subject_id="english"),
        build_validation_repair_prompt("mistakes", {"readable_items": [], "raw_validation": {}}, original),
    ]
    for prompt in prompts:
        assert_no_mojibake(prompt)


def test_saved_prompts_are_utf8_and_named_by_subject(tmp_path):
    prompt = build_worksheet_prompt(
        {"student_id": "daughter"},
        {"recent_7_days": [], "recent_30_days": []},
        subject_id="chinese",
    )
    path = save_worksheet_prompt(
        prompt,
        output_dir=tmp_path,
        student_id="daughter",
        subject_id="chinese",
        grade_at_time=6,
        now=datetime(2026, 6, 3, 15, 30, 0),
    )
    assert path.name == "worksheet_prompt_daughter_chinese_g6_20260603_153000.md"
    assert path.read_text(encoding="utf-8") == prompt
    assert_no_mojibake(path.read_text(encoding="utf-8"))

    marking_path = save_marking_prompt(
        build_marking_prompt({"student_id": "daughter"}, subject_id="english"),
        output_dir=tmp_path,
        student_id="daughter",
        subject_id="english",
        grade_at_time=6,
        now=datetime(2026, 6, 3, 15, 31, 0),
    )
    assert marking_path.name == "marking_prompt_daughter_english_g6_20260603_153100.md"
    assert marking_path.read_text(encoding="utf-8")


def test_display_resolver_uses_curriculum_and_marks_legacy():
    assert knowledge_point_display("chinese_g6_text_evidence", "chinese", 6) == "文本证据 (chinese_g6_text_evidence)"
    assert knowledge_point_display("english_g6_reading_detail", "english", 6) == "阅读细节定位 (english_g6_reading_detail)"
    assert knowledge_point_display("math_g6_number_operations", "math", 6) == "数与运算 (math_g6_number_operations)"
    assert knowledge_point_display("missing_code", "math", 6) == "Unknown(missing_code)"
    legacy_code = load_rule_registry().get_legacy_knowledge_points(active_only=False)[0]["code"]
    assert knowledge_point_display(legacy_code, "math", 6).startswith("[legacy]")

    assert question_type_display("chinese_reading") == "阅读理解 (chinese_reading)"
    assert mistake_tag_display("CHN_EVD_1") == "文本证据不足 (CHN_EVD_1)"
    assert mistake_tag_display("ENG_GRAM_1") == "时态错误 (ENG_GRAM_1)"
    assert difficulty_display("basic") == "基础 (basic)"


def test_mistakes_page_formatter_outputs_canonical_display_columns():
    import src.app as app

    rows = app._mistake_table_rows([
        {
            "student_id": "daughter",
            "subject_id": "chinese",
            "grade_at_time": 6,
            "curriculum_version_at_time": "cn_k12_2022",
            "date": "2026-06-03",
            "question_type_code": "chinese_reading",
            "knowledge_point_id": "chinese_g6_text_evidence",
            "primary_mistake_tag_code": "CHN_EVD_1",
            "difficulty_code": "medium",
            "question_summary": "sample",
        }
    ])
    row = rows[0]
    assert row["knowledge_point_id"] == "chinese_g6_text_evidence"
    assert row["knowledge_point_display"] == "文本证据 (chinese_g6_text_evidence)"
    assert "knowledge_point" not in row
    assert "type" not in row
    assert "display" not in row


def test_exports_include_display_columns_and_utf8(conn, tmp_path):
    conn.execute(
        """
        INSERT INTO mistakes (
            student_id, subject_id, grade_at_time, curriculum_version_at_time, date,
            question_type_code, knowledge_point_id, primary_mistake_tag_code,
            difficulty_code, question_summary, status, created_at, updated_at
        )
        VALUES ('daughter', 'english', 6, 'cn_k12_2022', '2026-06-03',
            'english_reading', 'english_g6_reading_detail', 'ENG_GRAM_1',
            'medium', 'sample', 'needs_confirmation', 'now', 'now')
        """
    )
    csv_path = export_mistakes_csv(conn, output_dir=tmp_path, now=datetime(2026, 6, 3, 15, 32, 0))
    yaml_path = export_mistakes_yaml(conn, output_dir=tmp_path, now=datetime(2026, 6, 3, 15, 32, 0))

    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "knowledge_point_display" in csv_text
    assert "阅读细节定位 (english_g6_reading_detail)" in csv_text
    assert_no_mojibake(csv_text)

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    row = data["mistakes"][0]
    assert row["knowledge_point_display"] == "阅读细节定位 (english_g6_reading_detail)"
    assert row["mistake_tag_display"] == "时态错误 (ENG_GRAM_1)"


def test_duplicate_detection_summary_contains_display_columns(conn):
    conn.execute(
        """
        INSERT INTO mistakes (
            student_id, subject_id, grade_at_time, curriculum_version_at_time, date,
            question_type_code, knowledge_point_id, primary_mistake_tag_code,
            difficulty_code, question_summary, status, created_at, updated_at
        )
        VALUES ('daughter', 'chinese', 6, 'cn_k12_2022', '2026-06-03',
            'chinese_reading', 'chinese_g6_text_evidence', 'CHN_EVD_1',
            'medium', 'sample', 'needs_confirmation', 'now', 'now')
        """
    )
    result = detect_duplicate_mistakes(conn, [{
        "student_id": "daughter",
        "subject_id": "chinese",
        "grade_at_time": 6,
        "curriculum_version_at_time": "cn_k12_2022",
        "date": "2026-06-03",
        "question_type_code": "chinese_reading",
        "knowledge_point_id": "chinese_g6_text_evidence",
        "primary_mistake_tag_code": "CHN_EVD_1",
        "difficulty_code": "medium",
        "question_summary": "sample",
    }])
    duplicate = result["duplicates"][0]
    assert duplicate["knowledge_point_id"] == "chinese_g6_text_evidence"
    assert duplicate["knowledge_point_display"] == "文本证据 (chinese_g6_text_evidence)"
    assert duplicate["question_type_display"] == "阅读理解 (chinese_reading)"
    assert duplicate["mistake_tag_display"] == "文本证据不足 (CHN_EVD_1)"


def test_repair_prompt_missing_subject_does_not_fallback_to_legacy():
    prompt = build_validation_repair_prompt(
        "worksheet",
        {"readable_items": [], "raw_validation": {}},
        """
worksheet:
  title: missing subject
  grade_at_time: 6
""",
    )
    assert "missing_subject_id" in prompt
    assert "legacy_fallback: not_injected_by_default" in prompt
    assert "decimal_calculation" not in prompt


def assert_no_mojibake(text: str) -> None:
    assert not any(pattern in text for pattern in MOJIBAKE_PATTERNS)
