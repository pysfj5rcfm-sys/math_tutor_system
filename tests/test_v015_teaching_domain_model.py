from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from src.core.import_preview import dry_run_mistakes_yaml, dry_run_worksheet_yaml
from src.core.mistakes import validate_mistakes_payload
from src.core.rule_registry import load_rule_registry
from src.core.student_profile import load_student_profile
from src.core.worksheets import validate_worksheet_payload
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt


ROOT = Path(__file__).resolve().parents[1]
OLD_24_TAGS = {
    "C1", "C2", "C3", "C4", "C5", "C6",
    "K1", "K2", "K3", "K4",
    "F1", "F2", "F3",
    "R1", "R2", "R3", "R4",
    "M1", "M2", "M3", "M4",
    "U1", "G1", "H1",
}


def test_project_name_readme_and_app_title_are_v015():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    app_source = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
    assert "edu_tutor_system" in readme
    assert "Formerly math_tutor_system" in readme
    assert "edu_tutor_system v0.1.5" in app_source


def test_students_subjects_stages_and_grades_load():
    registry = load_rule_registry(force_reload=True)
    active = registry.get_active_student()
    assert active["student_id"] == "daughter"
    assert active["current_grade"] == 6
    assert active["current_term"] == "六年级上"
    assert active["curriculum_version"] == "cn_k12_2022"
    assert registry.get_student("daughter_grade5")["student_id"] == "daughter"
    assert load_student_profile()["student_id"] == "daughter_grade5"

    subjects = {item["subject_id"]: item for item in registry.get_subjects(active_only=False)}
    assert subjects["math"]["active"] is True
    assert subjects["physics"]["supported_now"] is True
    assert subjects["chemistry"]["supported_now"] is True
    assert len(registry.get_grades()) == 12
    assert registry.get_stage_for_grade(6)["stage_id"] == "primary"
    assert registry.get_stage_for_grade(7)["stage_id"] == "junior_high"
    assert registry.get_stage_for_grade(10)["stage_id"] == "senior_high"


def test_education_configs_are_generalized_by_subject():
    registry = load_rule_registry()
    question_types = registry.get_question_types(active_only=False)
    assert any(item["scope"] == "general" for item in question_types)
    assert any(item["scope"] == "subject_specific" for item in question_types)
    assert {"递等式计算", "方程", "单位换算", "几何计算", "应用题"}.issubset(registry.get_question_type_codes())
    assert "physics_calculation" in {item["code"] for item in registry.get_question_types_for_subject("physics")}
    assert "physics_experiment" in {item["code"] for item in registry.get_question_types_for_subject("physics")}
    assert "chem_formula_writing" in {item["code"] for item in registry.get_question_types_for_subject("chemistry")}
    assert "chem_equation_balancing" in {item["code"] for item in registry.get_question_types_for_subject("chemistry")}
    assert registry.get_skills_for_subject("math")

    tags = set(registry.get_mistake_tag_codes())
    assert OLD_24_TAGS.issubset(tags)
    assert {"PHY_F1", "PHY_U1", "PHY_E1", "CHEM_F1", "CHEM_E1", "CHEM_EXP1"}.issubset(tags)

    capabilities = {item["capability_id"]: item for item in registry.expression_capabilities}
    assert capabilities["plain_text"]["implemented"] is True
    assert capabilities["math_geometry_diagram"]["implemented"] is False
    assert capabilities["physics_formula"]["implemented"] is False
    assert capabilities["chemical_equation"]["implemented"] is False


def test_curriculum_files_and_integrity():
    registry = load_rule_registry()
    assert registry.validate_curriculum_config()["valid"] is True
    for grade in range(5, 13):
        assert (ROOT / "config" / "curriculum" / "cn_k12_2022" / "math" / f"grade_{grade}.yaml").exists()
        assert registry.get_curriculum_for("math", grade)["subject_id"] == "math"
    for grade in range(8, 13):
        assert (ROOT / "config" / "curriculum" / "cn_k12_2022" / "physics" / f"grade_{grade}.yaml").exists()
        assert registry.get_curriculum_for("physics", grade)["subject_id"] == "physics"
    for grade in range(9, 13):
        assert (ROOT / "config" / "curriculum" / "cn_k12_2022" / "chemistry" / f"grade_{grade}.yaml").exists()
        assert registry.get_curriculum_for("chemistry", grade)["subject_id"] == "chemistry"

    ids = [kp["knowledge_point_id"] for kp in registry._curriculum_knowledge_points()]
    assert len(ids) == len(set(ids))


def test_registry_filtering_and_prompt_scope():
    registry = load_rule_registry()
    active_id = registry.get_active_student_id()
    kps = registry.get_knowledge_points_for_student(active_id, "math")
    assert kps
    assert {kp["grade"] for kp in kps} == {6}
    assert "chem_formula_writing" not in {item["code"] for item in registry.get_question_types_for_subject("math")}
    assert "PHY_F1" in {item["code"] for item in registry.get_mistake_tags_for_subject("physics")}
    assert "CHEM_F1" in {item["code"] for item in registry.get_mistake_tags_for_subject("chemistry")}
    assert "C3" not in {item["code"] for item in registry.get_mistake_tags_for_subject("physics")}
    scope = registry.render_curriculum_scope_for_prompt(active_id, "math")
    assert "六年级上" in scope
    assert "math_g6" in scope


def test_prompts_include_v015_scope_and_rendering_boundaries(conn):
    registry = load_rule_registry()
    student = registry.get_active_student()
    marking = build_marking_prompt(student, confirmed_stats={"recent_7_days": []})
    worksheet = build_worksheet_prompt(student, {"recent_7_days": [], "recent_30_days": []})

    assert "daughter" in marking
    assert "六年级上" in marking
    assert "subject_id: math" in marking
    assert "current_curriculum_scope" in worksheet
    assert "不要求输出 diagram / visuals" in marking
    assert "不默认跨年级" in worksheet
    assert "不默认跨学科" in worksheet
    assert "不输出 visuals / diagram" in worksheet


def test_yaml_context_defaults_and_legacy_samples(conn):
    old_mistakes = (ROOT / "samples" / "sample_mistakes.yaml").read_text(encoding="utf-8")
    old_worksheet = (ROOT / "samples" / "sample_worksheet.yaml").read_text(encoding="utf-8")
    assert dry_run_mistakes_yaml(conn, old_mistakes)["can_import"] is True
    assert dry_run_worksheet_yaml(conn, old_worksheet)["can_import"] is True

    mistakes_payload = {
        "mistakes": [{
            "date": "2026-06-01",
            "subject_id": "math",
            "question_type": "递等式计算",
            "knowledge_point": "小数计算",
            "mistake_tag": "C3",
            "difficulty": "基础",
            "question_summary": "v0.1.5 context",
        }]
    }
    report, rows = validate_mistakes_payload(mistakes_payload)
    assert report.errors == []
    assert rows[0]["student_id"] == "daughter"
    assert rows[0]["subject_id"] == "math"
    assert rows[0]["grade_at_time"] == 6

    worksheet_payload = {
        "worksheet": {
            "title": "v0.1.5 数学文字卷",
            "date": "2026-06-01",
            "subject_id": "math",
            "sections": [{
                "name": "一、计算",
                "layout": "two_columns",
                "questions": [{
                    "question_type": "递等式计算",
                    "knowledge_point": "分数四则运算",
                    "target_mistake_tag": "C1",
                    "difficulty": "基础",
                    "question": "1/2 + 1/3 = ?",
                    "answer": "5/6",
                    "explanation": "通分后相加。",
                }],
            }],
        }
    }
    worksheet_report, worksheet = validate_worksheet_payload(worksheet_payload)
    assert worksheet_report.errors == []
    assert worksheet["student_id"] == "daughter"
    assert worksheet["subject_id"] == "math"
    assert worksheet["curriculum_version_at_time"] == "cn_k12_2022"


def test_handoff_exists_and_has_next_steps():
    handoff = ROOT / "docs" / "HANDOFF_v0.1.5.md"
    assert handoff.exists()
    text = handoff.read_text(encoding="utf-8")
    assert "edu_tutor_system" in text
    assert "math_tutor_system" in text
    assert "v0.1.6" in text
    assert "Subject Rendering Layer" in text
