from __future__ import annotations

from pathlib import Path

import pytest

from src.prompts.marking_prompt import build_marking_prompt, save_marking_prompt
from src.prompts.repair_prompt import build_validation_repair_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt


MOJIBAKE_PATTERNS = ("�", "Ã", "Â", "â€", "â€™", "â€œ", "â€\x9d", "ä¸", "çš", "ï»¿")


def _assert_clean(text: str) -> None:
    for marker in MOJIBAKE_PATTERNS:
        assert marker not in text
    assert "daughter_grade5" not in text
    assert "config/knowledge_points.yaml" not in text
    assert "legacy_names" not in text
    assert "legacy_aliases" not in text


def test_marking_prompts_are_subject_scoped():
    math_prompt = build_marking_prompt({"student_id": "daughter"}, subject_id="math")
    chinese_prompt = build_marking_prompt({"student_id": "daughter"}, subject_id="chinese")
    english_prompt = build_marking_prompt({"student_id": "daughter"}, subject_id="english")

    assert "math_g6_application_modeling" in math_prompt
    assert "MATH_C3" in math_prompt
    assert "CHN_EVD_1" not in math_prompt
    assert "ENG_GRAM_1" not in math_prompt

    assert "chinese_g6_text_evidence" in chinese_prompt
    assert "CHN_EVD_1" in chinese_prompt
    assert "ENG_GRAM_1" not in chinese_prompt
    assert "MATH_C3" not in chinese_prompt

    assert "english_g6_reading_detail" in english_prompt
    assert "ENG_GRAM_1" in english_prompt
    assert "CHN_EVD_1" not in english_prompt
    assert "MATH_C3" not in english_prompt

    for prompt in (math_prompt, chinese_prompt, english_prompt):
        _assert_clean(prompt)


def test_worksheet_prompts_are_subject_scoped():
    stats = {"recent_7_days": [], "recent_30_days": [], "mistake_tag_by_question_type": [], "mistake_tag_by_knowledge_point": []}
    math_prompt = build_worksheet_prompt({"student_id": "daughter"}, stats, subject_id="math")
    chinese_prompt = build_worksheet_prompt({"student_id": "daughter"}, stats, subject_id="chinese")
    english_prompt = build_worksheet_prompt({"student_id": "daughter"}, stats, subject_id="english")

    assert "math_g6_equation_basic" in math_prompt
    assert "math_g6_default" in math_prompt
    assert "chinese_g6_text_evidence" not in math_prompt

    assert "chinese_g6_text_evidence" in chinese_prompt
    assert "chinese_g6_default" in chinese_prompt
    assert "ENG_GRAM_1" not in chinese_prompt

    assert "english_g6_reading_detail" in english_prompt
    assert "english_g6_default" in english_prompt
    assert "CHN_EVD_1" not in english_prompt

    for prompt in (math_prompt, chinese_prompt, english_prompt):
        _assert_clean(prompt)


def test_prompt_requires_subject_when_student_has_multiple_active_subjects():
    with pytest.raises(ValueError, match="subject_id is required"):
        build_marking_prompt({"student_id": "daughter"})
    with pytest.raises(ValueError, match="subject_id is required"):
        build_worksheet_prompt({"student_id": "daughter"}, {})


def test_repair_prompt_uses_curriculum_scope_and_missing_subject_has_no_fallback():
    chinese_yaml = """
mistakes:
  - student_id: daughter
    subject_id: chinese
    grade_at_time: 6
    question_type_code: chinese_reading
    knowledge_point_id: wrong
    primary_mistake_tag_code: CHN_Q_1
    difficulty_code: medium
    date: "2026-06-03"
    question_summary: x
"""
    prompt = build_validation_repair_prompt("mistakes", {"raw_validation": {}, "readable_items": []}, chinese_yaml)
    assert "chinese_g6_text_evidence" in prompt
    assert "math_g6_number_operations" not in prompt
    assert "english_g6_reading_detail" not in prompt
    _assert_clean(prompt)

    missing_subject_prompt = build_validation_repair_prompt(
        "mistakes",
        {"raw_validation": {}, "readable_items": []},
        "mistakes:\n  - student_id: daughter\n    grade_at_time: 6\n",
    )
    assert "not_injected_by_default" in missing_subject_prompt
    assert "math_g6_number_operations" not in missing_subject_prompt
    assert "config/knowledge_points.yaml" not in missing_subject_prompt


def test_saved_prompt_is_utf8_and_subject_named(tmp_path: Path):
    prompt = build_marking_prompt({"student_id": "daughter"}, subject_id="english")
    path = save_marking_prompt(prompt, output_dir=tmp_path, student_id="daughter", subject_id="english", grade_at_time=6)

    assert "marking_prompt_daughter_english_g6" in path.name
    assert path.read_text(encoding="utf-8") == prompt
    _assert_clean(path.read_text(encoding="utf-8"))
