from __future__ import annotations

from pathlib import Path

from src.core.mistakes import preview_mistakes_payload
from src.core.rule_registry import load_rule_registry
from src.core.worksheets import preview_worksheet_payload
from src.prompts.repair_prompt import build_validation_repair_prompt


ROOT = Path(__file__).resolve().parents[1]


def _legacy_math_code() -> str:
    registry = load_rule_registry(force_reload=True)
    for item in registry.get_legacy_knowledge_points(active_only=True):
        if item.get("subject") == "math":
            return str(item["code"])
    raise AssertionError("expected at least one legacy math knowledge point")


def test_v0171_registry_separates_curriculum_and_legacy_knowledge_points():
    registry = load_rule_registry(force_reload=True)
    active_ids = {item["knowledge_point_id"] for item in registry.get_curriculum_knowledge_points()}
    legacy = registry.get_legacy_knowledge_points(active_only=False)
    legacy_codes = {item["code"] for item in legacy}
    assert {"math_g6_number_operations", "chinese_g6_text_evidence", "english_g6_reading_detail"}.issubset(active_ids)
    assert legacy
    assert all(item["source"] == "legacy_compatibility" for item in legacy)
    assert _legacy_math_code() in legacy_codes
    assert _legacy_math_code() not in registry.get_curriculum_knowledge_point_codes()
    assert _legacy_math_code() in registry.get_all_knowledge_point_codes(include_legacy=True)


def test_v0171_current_student_three_subject_scope_uses_curriculum_files():
    registry = load_rule_registry(force_reload=True)
    student = registry.get_active_student()
    scopes = {
        subject_id: {item["knowledge_point_id"] for item in registry.get_knowledge_points_for_student(student["student_id"], subject_id)}
        for subject_id in student["active_subjects"]
    }
    assert "math_g6_application_modeling" in scopes["math"]
    assert "chinese_g6_text_evidence" in scopes["chinese"]
    assert "english_g6_reading_detail" in scopes["english"]


def test_v0171_repair_prompt_uses_scoped_curriculum_for_three_subjects():
    legacy_code = _legacy_math_code()
    prompts = {
        "math": build_validation_repair_prompt("worksheet", {"readable_items": [], "raw_validation": {}}, """
worksheet:
  title: "math repair"
  student_id: "daughter"
  subject_id: "math"
  grade_at_time: 6
  curriculum_version_at_time: "cn_k12_2022"
  sections: []
"""),
        "chinese": build_validation_repair_prompt("mistakes", {"readable_items": [], "raw_validation": {}}, """
mistakes:
  - student_id: "daughter"
    subject_id: "chinese"
    grade_at_time: 6
    curriculum_version_at_time: "cn_k12_2022"
    question_summary: "repair"
"""),
        "english": build_validation_repair_prompt("worksheet", {"readable_items": [], "raw_validation": {}}, """
worksheet:
  title: "english repair"
  student_id: "daughter"
  subject_id: "english"
  grade_at_time: 6
  curriculum_version_at_time: "cn_k12_2022"
  sections: []
"""),
    }
    assert "math_g6_application_modeling" in prompts["math"]
    assert "chinese_g6_text_evidence" in prompts["chinese"]
    assert "english_g6_reading_detail" in prompts["english"]
    for prompt in prompts.values():
        assert "source_of_truth: config/curriculum/" in prompt
        assert "config/knowledge_points.yaml" not in prompt
        assert legacy_code not in prompt


def test_v0171_repair_prompt_missing_subject_does_not_fallback_to_legacy():
    legacy_code = _legacy_math_code()
    prompt = build_validation_repair_prompt("worksheet", {"readable_items": [], "raw_validation": {}}, """
worksheet:
  title: "missing subject"
  student_id: "daughter"
  grade_at_time: 6
  sections: []
""")
    assert "scope_status: missing_context" in prompt
    assert "legacy_fallback: not_injected_by_default" in prompt
    assert legacy_code not in prompt
    assert "config/knowledge_points.yaml" not in prompt


def test_v0171_preview_does_not_accept_legacy_math_point_in_chinese_or_english(conn):
    legacy_code = _legacy_math_code()
    chinese_payload = {
        "mistakes": [{
            "student_id": "daughter",
            "subject_id": "chinese",
            "grade_at_time": 6,
            "date": "2026-06-03",
            "question_type_code": "chinese_reading",
            "knowledge_point_id": legacy_code,
            "primary_mistake_tag_code": "CHN_EVD_1",
            "difficulty_code": "medium",
            "question_summary": "legacy point should not pass chinese scope",
        }]
    }
    english_payload = {
        "worksheet": {
            "title": "legacy point should not pass english scope",
            "student_id": "daughter",
            "subject_id": "english",
            "grade_at_time": 6,
            "date": "2026-06-03",
            "sections": [{
                "name": "I. Reading",
                "layout": "single_column",
                "questions": [{
                    "question_type_code": "english_reading",
                    "knowledge_point_id": legacy_code,
                    "target_mistake_tag_code": "ENG_READ_1",
                    "difficulty_code": "medium",
                    "question": "Read and answer.",
                    "answer": "Answer.",
                    "explanation": "Explanation.",
                }],
            }],
        }
    }
    chinese = preview_mistakes_payload(conn, chinese_payload)
    english = preview_worksheet_payload(conn, english_payload)
    assert chinese["valid"] is True
    assert chinese["valid_rows"][0]["knowledge_point_id"] is None
    assert any(item["code"] == "unknown_knowledge_point" for item in chinese["validation"]["warnings"])
    assert english["valid"] is True
    question = english["worksheet"]["sections"][0]["questions"][0]
    assert question["knowledge_point_id"] is None
    assert any(item["code"] == "unknown_knowledge_point" for item in english["validation"]["warnings"])


def test_v0171_rule_registry_page_labels_legacy_section():
    app_source = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
    assert 'st.subheader("knowledge_points")' not in app_source
    assert "Active Student Scope / 当前学生规则范围" in app_source
    assert "Global Curriculum Registry / 全局课程知识点" in app_source
    assert "Legacy Knowledge Points / 历史兼容知识点" in app_source
    assert "config/knowledge_points.yaml legacy compatibility" in app_source
