from __future__ import annotations

from pathlib import Path

import yaml

from src.core.display import difficulty_display, knowledge_point_display, mistake_tag_display, question_type_display
from src.core.mistakes import preview_mistakes_payload
from src.core.rule_registry import load_rule_registry
from src.core.schema_integrity import check_schema_integrity
from src.core.worksheets import preview_worksheet_payload
from src.db import seed_mistake_tags
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt


ROOT = Path(__file__).resolve().parents[1]


def test_v017_active_student_subject_grade_registry():
    registry = load_rule_registry(force_reload=True)
    student = registry.get_active_student()
    assert student["student_id"] == "daughter"
    assert student["current_grade"] == 6
    assert student["current_term"] == "六年级上"
    assert student["active_subjects"] == ["math", "chinese", "english"]
    supported = {item["subject_id"] for item in registry.get_supported_subjects()}
    assert {"math", "chinese", "english"}.issubset(supported)
    assert registry.get_grade_display_name(6) in {"六年级", "鍏勾绾?"}


def test_v017_question_types_are_subject_scoped_and_displayed():
    registry = load_rule_registry(force_reload=True)
    math_codes = {item["code"] for item in registry.get_question_types_for_subject("math")}
    chinese_codes = {item["code"] for item in registry.get_question_types_for_subject("chinese")}
    english_codes = {item["code"] for item in registry.get_question_types_for_subject("english")}
    assert {"math_calculation", "math_equation", "math_application", "math_reading_application"}.issubset(math_codes)
    assert {"chinese_reading", "chinese_text_evidence", "chinese_composition_fragment"}.issubset(chinese_codes)
    assert {"english_reading", "english_grammar", "english_writing_short"}.issubset(english_codes)
    assert "english_reading" not in chinese_codes
    assert "chinese_reading" not in english_codes
    assert question_type_display("chinese_reading", registry) == "阅读理解 (chinese_reading)"
    assert question_type_display("english_reading", registry) == "阅读理解 (english_reading)"


def test_v017_knowledge_points_are_subject_and_grade_scoped():
    registry = load_rule_registry(force_reload=True)
    math = {item["knowledge_point_id"] for item in registry.get_knowledge_points_for_context("math", 6)}
    chinese = {item["knowledge_point_id"] for item in registry.get_knowledge_points_for_context("chinese", 6)}
    english = {item["knowledge_point_id"] for item in registry.get_knowledge_points_for_context("english", 6)}
    assert "math_g6_number_operations" in math
    assert "chinese_g6_text_evidence" in chinese
    assert "english_g6_reading_detail" in english
    assert "english_g6_reading_inference" not in chinese
    assert "chinese_g6_reading_inference" not in english
    assert registry.validate_knowledge_point_for_context("阅读推断", "chinese", 6)["matches"][0]["knowledge_point_id"] == "chinese_g6_reading_inference"
    assert registry.validate_knowledge_point_for_context("阅读推断", "english", 6)["matches"][0]["knowledge_point_id"] == "english_g6_reading_inference"


def test_v017_mistake_tags_scope_and_seed_idempotent(conn):
    registry = load_rule_registry(force_reload=True)
    chinese_tags = {item["code"] for item in registry.get_mistake_tags_for_subject("chinese")}
    english_tags = {item["code"] for item in registry.get_mistake_tags_for_subject("english")}
    math_tags = {item["code"] for item in registry.get_mistake_tags_for_subject("math")}
    assert {"CHN_EVD_1", "CHN_SUM_1", "R4"}.issubset(chinese_tags)
    assert {"ENG_GRAM_1", "ENG_READ_1", "R4"}.issubset(english_tags)
    assert {"MATH_MODEL_1", "MATH_CHECK_1", "R4"}.issubset(math_tags)
    assert "CHN_EVD_1" not in english_tags
    assert "ENG_GRAM_1" not in chinese_tags
    before = conn.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0]
    seed_mistake_tags(conn, registry)
    seed_mistake_tags(conn, registry)
    after = conn.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0]
    assert after == before


def test_v017_alias_and_normalization_subject_scoped(conn):
    registry = load_rule_registry(force_reload=True)
    assert registry.resolve_alias("question_type_aliases", "阅读理解", "chinese").target == "chinese_reading"
    assert registry.resolve_alias("question_type_aliases", "阅读理解", "english").target == "english_reading"
    assert registry.resolve_alias("question_type_aliases", "阅读理解").ambiguous is True

    chinese_payload = {
        "mistakes": [{
            "student_id": "daughter",
            "subject_id": "chinese",
            "grade_at_time": 6,
            "date": "2026-06-03",
            "question_type": "阅读理解",
            "knowledge_point": "文本证据",
            "mistake_tag": "文本证据不足",
            "difficulty": "中等",
            "question_summary": "文本证据不足",
        }]
    }
    english_payload = {
        "mistakes": [{
            "student_id": "daughter",
            "subject_id": "english",
            "grade_at_time": 6,
            "date": "2026-06-03",
            "question_type": "阅读理解",
            "knowledge_point": "阅读细节定位",
            "mistake_tag": "时态错误",
            "difficulty": "中等",
            "question_summary": "时态错误",
        }]
    }
    chinese = preview_mistakes_payload(conn, chinese_payload)
    english = preview_mistakes_payload(conn, english_payload)
    assert chinese["valid"] is True
    assert english["valid"] is True
    assert chinese["valid_rows"][0]["question_type_code"] == "chinese_reading"
    assert chinese["valid_rows"][0]["knowledge_point_id"] == "chinese_g6_text_evidence"
    assert chinese["valid_rows"][0]["primary_mistake_tag_code"] == "CHN_EVD_1"
    assert english["valid_rows"][0]["question_type_code"] == "english_reading"
    assert english["valid_rows"][0]["knowledge_point_id"] == "english_g6_reading_detail"
    assert english["valid_rows"][0]["primary_mistake_tag_code"] == "ENG_GRAM_1"


def test_v017_ambiguous_alias_and_cross_subject_knowledge_point(conn):
    ambiguous = preview_mistakes_payload(conn, _sample("uat_v017_cross_subject_alias_ambiguous.yaml"))
    assert ambiguous["valid"] is False
    assert any(error["code"] == "invalid_learning_context" for error in ambiguous["validation"]["errors"])

    invalid = preview_mistakes_payload(conn, _sample("uat_v017_invalid_cross_subject_knowledge_point.yaml"))
    assert invalid["valid"] is True
    assert invalid["valid_rows"][0]["knowledge_point_id"] is None
    assert any(warning["code"] == "unknown_knowledge_point" for warning in invalid["validation"]["warnings"])

    chemistry = {
        "mistakes": [{
            "student_id": "uat_chemistry_g9",
            "subject_id": "chemistry",
            "grade_at_time": 9,
            "date": "2026-06-03",
            "question_type_code": "chem_formula_writing",
            "knowledge_point": "速度",
            "primary_mistake_tag_code": "CHEM_F1",
            "difficulty_code": "basic",
            "question_summary": "不得静默匹配物理速度。",
        }]
    }
    preview = preview_mistakes_payload(conn, chemistry)
    assert preview["valid"] is True
    assert preview["valid_rows"][0]["knowledge_point_id"] is None


def test_v017_display_resolver_three_subjects():
    registry = load_rule_registry(force_reload=True)
    assert knowledge_point_display("chinese_g6_text_evidence", "chinese", 6, registry=registry) == "文本证据 (chinese_g6_text_evidence)"
    assert knowledge_point_display("english_g6_reading_detail", "english", 6, registry=registry) == "阅读细节定位 (english_g6_reading_detail)"
    assert mistake_tag_display("CHN_EVD_1", registry) == "文本证据不足 (CHN_EVD_1)"
    assert mistake_tag_display("ENG_GRAM_1", registry) == "时态错误 (ENG_GRAM_1)"
    assert difficulty_display("basic", registry) == "基础 (basic)"
    assert question_type_display("not_a_code", registry) == "Unknown(not_a_code)"


def test_v017_prompts_are_subject_specific_and_plain_text_only():
    profile = {"student_id": "daughter"}
    stats = {}
    math_prompt = build_worksheet_prompt(profile, stats, subject_id="math")
    chinese_prompt = build_worksheet_prompt(profile, stats, subject_id="chinese")
    english_prompt = build_worksheet_prompt(profile, stats, subject_id="english")
    marking_prompt = build_marking_prompt(profile, subject_id="chinese")
    assert "math_g6_number_operations" in math_prompt
    assert "chinese_g6_text_evidence" in chinese_prompt
    assert "english_g6_reading_detail" in english_prompt
    assert "ENG_GRAM_1" not in chinese_prompt.split("current_subject_mistake_tags:", 1)[1].split("recent_7_days_stats:", 1)[0]
    assert "CHN_EVD_1" not in english_prompt.split("current_subject_mistake_tags:", 1)[1].split("recent_7_days_stats:", 1)[0]
    for prompt in (math_prompt, chinese_prompt, english_prompt, marking_prompt):
        assert "daughter_grade5" not in prompt
        assert "question_type_code" in prompt
        assert "knowledge_point_id" in prompt
        assert "difficulty_code" in prompt
        assert "    question_type:" not in prompt
        assert "          question_type:" not in prompt
        assert "render_blocks" in prompt
        assert "Do not output visuals" in prompt


def test_v017_uat_samples_preview_success_and_not_auto_imported(conn):
    mistake_samples = [
        "uat_v017_math_g6_mistakes.yaml",
        "uat_v017_chinese_g6_mistakes.yaml",
        "uat_v017_english_g6_mistakes.yaml",
    ]
    worksheet_samples = [
        "uat_v017_math_g6_worksheet.yaml",
        "uat_v017_chinese_g6_worksheet.yaml",
        "uat_v017_english_g6_worksheet.yaml",
    ]
    for name in mistake_samples:
        preview = preview_mistakes_payload(conn, _sample(name))
        assert preview["valid"] is True, name
        assert preview["valid_count"] >= 1
    for name in worksheet_samples:
        preview = preview_worksheet_payload(conn, _sample(name))
        assert preview["valid"] is True, name
        assert preview["question_count"] >= 1
    assert conn.execute("SELECT COUNT(*) FROM mistakes WHERE source LIKE '%uat_v017%'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM worksheets WHERE source LIKE '%uat_v017%'").fetchone()[0] == 0


def test_v017_schema_integrity_current_db_shape():
    report = check_schema_integrity()
    assert set(report) == {"errors", "warnings", "info"}
    assert not [item for item in report["errors"] if item["code"] != "missing_db"]


def _sample(name: str) -> dict:
    return yaml.safe_load((ROOT / "samples" / name).read_text(encoding="utf-8"))
