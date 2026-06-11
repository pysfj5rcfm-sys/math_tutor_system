from __future__ import annotations

from datetime import date

from src.core.current_student import (
    clear_current_student,
    list_selectable_students,
    resolve_current_student,
    set_current_student,
)
from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload
from src.core.rule_registry import load_rule_registry
from src.core.stats import stats_summary
from src.core.target_priority_light import build_target_priority_light
from src.core.worksheets import confirm_worksheet_import, get_worksheet_bundle, preview_worksheet_payload
from src.db import confirm_record
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt
from src.render.html_renderer import render_worksheet_html


def teardown_function() -> None:
    clear_current_student()


def _mistake(student_id: str, grade: int, kp: str, tag: str = "MATH_CALCULATION_EXECUTION_ERROR") -> dict:
    term = "五年级下" if grade == 5 else "六年级上"
    return {
        "mistakes": [{
            "student_id": student_id,
            "subject_id": "math",
            "grade_at_time": grade,
            "term_at_time": term,
            "curriculum_version_at_time": "cn_k12_2022",
            "textbook_version_at_time": "generic",
            "date": "2026-06-10",
            "question_type_code": "math_calculation",
            "knowledge_point_id": kp,
            "primary_mistake_tag_code": tag,
            "difficulty_code": "medium",
            "question_summary": f"{student_id} mistake",
            "wrong_answer_summary": "wrong",
            "correct_answer_summary": "right",
            "training_needed": True,
            "source": "test",
        }]
    }


def _worksheet(student_id: str, grade: int, kp: str) -> dict:
    term = "五年级下" if grade == 5 else "六年级上"
    return {
        "worksheet": {
            "title": f"{student_id} worksheet",
            "student_id": student_id,
            "subject_id": "math",
            "grade_at_time": grade,
            "term_at_time": term,
            "curriculum_version_at_time": "cn_k12_2022",
            "textbook_version_at_time": "generic",
            "date": "2026-06-10",
            "source": "test",
            "sections": [{
                "name": "Practice",
                "layout": "single_column",
                "questions": [{
                    "question_no": "1",
                    "question_type_code": "math_calculation",
                    "knowledge_point_id": kp,
                    "target_mistake_tag_code": "MATH_CALCULATION_EXECUTION_ERROR",
                    "difficulty_code": "medium",
                    "question_role": "repair",
                    "teaching_purpose": "repair",
                    "expected_error_mechanism": "calculation",
                    "question": "1+1=?",
                    "answer": "2",
                    "explanation": "Add directly.",
                }],
            }],
        }
    }


def test_set_and_resolve_current_student_by_student_id():
    set_current_student("sally")
    assert resolve_current_student()["student_id"] == "sally"

    set_current_student("daughter")
    assert resolve_current_student()["student_id"] == "daughter"


def test_prompt_defaults_follow_current_student_scope():
    set_current_student("sally")
    sally_prompt = build_marking_prompt({}, subject_id="math")
    assert "student_id: sally" in sally_prompt
    assert "grade_at_time: 5" in sally_prompt
    assert "term_at_time: 五年级下" in sally_prompt
    assert "math_g5b_" in sally_prompt

    set_current_student("daughter")
    daughter_prompt = build_worksheet_prompt({}, {"recent_7_days": [], "recent_30_days": []}, subject_id="math")
    assert "student_id: daughter" in daughter_prompt
    assert "grade_at_time: 6" in daughter_prompt
    assert "math_g6a_" in daughter_prompt
    assert "math_g5b_" not in daughter_prompt


def test_rules_registry_filter_follows_current_student():
    registry = load_rule_registry(force_reload=True)
    set_current_student("sally", registry=registry)
    sally_points = registry.get_knowledge_points_for_student(registry.get_active_student_id(), "math")
    assert all(int(point["grade"]) == 5 for point in sally_points)
    assert any(point["knowledge_point_id"].startswith("math_g5b_") for point in sally_points)

    set_current_student("daughter", registry=registry)
    daughter_points = registry.get_knowledge_points_for_student(registry.get_active_student_id(), "math")
    assert any(point["knowledge_point_id"].startswith("math_g6a_") for point in daughter_points)
    assert not any(point["knowledge_point_id"].startswith("math_g5b_") for point in daughter_points)


def test_stats_worksheet_history_and_target_priority_filter_by_student(conn):
    daughter_preview = preview_mistakes_payload(
        conn,
        _mistake("daughter", 6, "math_g6a_rational_number_concept", "MATH_CONCEPT_DEFINITION_ERROR"),
    )
    sally_preview = preview_mistakes_payload(
        conn,
        _mistake("sally", 5, "math_g5b_speed_time_distance_relation"),
    )
    confirm_mistakes_import(conn, daughter_preview, duplicate_strategy="import_all")
    confirm_mistakes_import(conn, sally_preview, duplicate_strategy="import_all")
    confirm_record(conn, "mistakes", 1)
    confirm_record(conn, "mistakes", 2)

    daughter_stats = stats_summary(conn, today=date(2026, 6, 11), student_id="daughter")
    sally_stats = stats_summary(conn, today=date(2026, 6, 11), student_id="sally")
    assert daughter_stats["recent_7_days"] == [{"mistake_tag": "MATH_CONCEPT_DEFINITION_ERROR", "count": 1}]
    assert sally_stats["recent_7_days"] == [{"mistake_tag": "MATH_CALCULATION_EXECUTION_ERROR", "count": 1}]

    daughter_priority = build_target_priority_light(conn, "daughter", "math", 6, today="2026-06-11")
    sally_priority = build_target_priority_light(conn, "sally", "math", 5, today="2026-06-11")
    assert daughter_priority["items"][0]["knowledge_point_id"].startswith("math_g6a_")
    assert sally_priority["items"][0]["knowledge_point_id"].startswith("math_g5b_")

    _, daughter_worksheet_id = confirm_worksheet_import(
        conn,
        preview_worksheet_payload(conn, _worksheet("daughter", 6, "math_g6a_rational_number_concept")),
        duplicate_strategy="import_all",
    )
    _, sally_worksheet_id = confirm_worksheet_import(
        conn,
        preview_worksheet_payload(conn, _worksheet("sally", 5, "math_g5b_speed_time_distance_relation")),
        duplicate_strategy="import_all",
    )
    daughter_rows = conn.execute("SELECT id FROM worksheets WHERE student_id = ?", ("daughter",)).fetchall()
    sally_rows = conn.execute("SELECT id FROM worksheets WHERE student_id = ?", ("sally",)).fetchall()
    assert [row["id"] for row in daughter_rows] == [daughter_worksheet_id]
    assert [row["id"] for row in sally_rows] == [sally_worksheet_id]


def test_yaml_mismatch_warns_and_confirm_keeps_yaml_student_id(conn):
    set_current_student("daughter")
    preview = preview_mistakes_payload(conn, _mistake("sally", 5, "math_g5b_speed_time_distance_relation"))
    warning_codes = {item["code"] for item in preview["validation"]["warnings"]}
    assert "yaml_student_id_differs_from_current_student" in warning_codes

    report = confirm_mistakes_import(conn, preview, duplicate_strategy="import_all")
    assert report["imported_count"] == 1
    row = conn.execute("SELECT student_id FROM mistakes").fetchone()
    assert row["student_id"] == "sally"


def test_uat_students_are_excluded_and_not_set_by_default():
    registry = load_rule_registry(force_reload=True)
    selectable_ids = {student["student_id"] for student in list_selectable_students(registry=registry)}
    assert "daughter" in selectable_ids
    assert "sally" in selectable_ids
    assert not any(str(student_id).startswith("uat_") for student_id in selectable_ids)

    try:
        set_current_student("uat_math_g6", registry=registry)
    except ValueError:
        pass
    else:
        raise AssertionError("UAT student should not be set as current by default")


def test_html_export_uses_worksheet_record_student_not_current_student(conn):
    _, worksheet_id = confirm_worksheet_import(
        conn,
        preview_worksheet_payload(conn, _worksheet("sally", 5, "math_g5b_speed_time_distance_relation")),
        duplicate_strategy="import_all",
    )
    set_current_student("daughter")
    bundle = get_worksheet_bundle(conn, int(worksheet_id))
    html = render_worksheet_html(bundle)

    assert bundle["worksheet"]["student_id"] == "sally"
    assert "sally" in html
    assert "(sally)" in html
