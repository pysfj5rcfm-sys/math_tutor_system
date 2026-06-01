from __future__ import annotations

import csv
from datetime import datetime

import yaml

import src.app as app
from src.core.backup_export import export_mistakes_csv, export_mistakes_yaml
from src.core.display import knowledge_point_display, question_type_display
from src.core.data_governance import filter_mistakes
from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload, validate_mistakes_payload


def test_explicit_physics_context_is_not_overwritten_in_preview(conn):
    preview = preview_mistakes_payload(conn, {"mistakes": [_physics_speed_mistake()]})
    row = preview["valid_rows"][0]
    assert row["subject_id"] == "physics"
    assert row["grade_at_time"] == 8


def test_missing_context_defaults_to_active_student(conn):
    preview = preview_mistakes_payload(conn, {"mistakes": [_legacy_math_mistake()]})
    row = preview["valid_rows"][0]
    assert row["subject_id"] == "math"
    assert row["grade_at_time"] == 6


def test_confirm_import_persists_explicit_physics_context(conn):
    preview = preview_mistakes_payload(conn, {"mistakes": [_physics_speed_mistake()]})
    report = confirm_mistakes_import(conn, preview)
    assert report["imported_count"] == 1

    row = dict(conn.execute("SELECT subject_id, grade_at_time FROM mistakes").fetchone())
    assert row["subject_id"] == "physics"
    assert row["grade_at_time"] == 8


def test_mistake_table_rows_show_real_context_and_display_labels(conn):
    confirm_mistakes_import(conn, preview_mistakes_payload(conn, {"mistakes": [_physics_speed_mistake()]}))

    rows = app._mistake_table_rows(filter_mistakes(conn))
    assert rows[0]["subject_id"] == "physics"
    assert rows[0]["grade_at_time"] == 8
    assert rows[0]["question_type_display"] == "物理计算 (physics_calculation)"
    assert rows[0]["knowledge_point_display"] == "速度 (physics_g8_speed)"


def test_filter_mistakes_uses_real_subject_and_grade(conn):
    confirm_mistakes_import(conn, preview_mistakes_payload(conn, {"mistakes": [_physics_speed_mistake()]}))
    confirm_mistakes_import(conn, preview_mistakes_payload(conn, {"mistakes": [_legacy_math_mistake()]}))

    physics_rows = filter_mistakes(conn, subject_id="physics")
    grade8_rows = filter_mistakes(conn, grade_at_time=8)
    assert len(physics_rows) == 1
    assert physics_rows[0]["subject_id"] == "physics"
    assert len(grade8_rows) == 1
    assert grade8_rows[0]["grade_at_time"] == 8


def test_export_mistakes_preserves_real_context(conn, tmp_path):
    confirm_mistakes_import(conn, preview_mistakes_payload(conn, {"mistakes": [_physics_speed_mistake()]}))

    csv_path = export_mistakes_csv(conn, tmp_path, now=datetime(2026, 6, 1, 16, 1, 0))
    yaml_path = export_mistakes_yaml(conn, tmp_path, now=datetime(2026, 6, 1, 16, 1, 1))

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        csv_row = next(csv.DictReader(f))
    assert csv_row["subject_id"] == "physics"
    assert csv_row["grade_at_time"] == "8"

    yaml_row = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["mistakes"][0]
    assert yaml_row["subject_id"] == "physics"
    assert yaml_row["grade_at_time"] == 8


def test_question_type_display_handles_code_and_legacy_name():
    assert question_type_display("math_application") == "应用题 (math_application)"
    assert question_type_display("应用题") == "应用题 (math_application)"


def test_knowledge_point_display_handles_id_and_name_in_current_scope():
    assert knowledge_point_display("physics_g8_speed", "physics", 8) == "速度 (physics_g8_speed)"
    assert knowledge_point_display("速度", "physics", 8) == "速度 (physics_g8_speed)"


def test_knowledge_point_name_scope_regression():
    physics_report, _ = validate_mistakes_payload({"mistakes": [_physics_speed_mistake()]})
    assert not any(warning["code"] == "unknown_knowledge_point" for warning in physics_report.warnings)

    chemistry_report, _ = validate_mistakes_payload({"mistakes": [_chemistry_speed_mistake()]})
    assert any(warning["code"] == "unknown_knowledge_point" for warning in chemistry_report.warnings)


def _physics_speed_mistake() -> dict:
    return {
        "date": "2026-06-01",
        "subject_id": "physics",
        "grade_at_time": 8,
        "term_at_time": "八年级上",
        "curriculum_version_at_time": "cn_k12_2022",
        "question_type": "physics_calculation",
        "knowledge_point": "速度",
        "mistake_tag": "PHY_F1",
        "difficulty": "基础",
        "question_summary": "速度计算题",
        "source": "pytest",
    }


def _legacy_math_mistake() -> dict:
    return {
        "date": "2026-06-01",
        "question_type": "math_application",
        "knowledge_point": "小数计算",
        "mistake_tag": "R4",
        "difficulty": "基础",
        "question_summary": "旧 YAML 缺少学科和年级上下文",
        "source": "pytest",
    }


def _chemistry_speed_mistake() -> dict:
    return {
        "date": "2026-06-01",
        "subject_id": "chemistry",
        "grade_at_time": 9,
        "term_at_time": "九年级上",
        "question_type": "chem_formula_writing",
        "knowledge_point": "速度",
        "mistake_tag": "CHEM_F1",
        "difficulty": "基础",
        "question_summary": "化学测试题",
    }
