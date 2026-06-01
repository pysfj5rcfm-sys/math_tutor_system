from __future__ import annotations

import csv
from datetime import datetime

import yaml

import src.app  # noqa: F401
from src.core.backup_export import export_mistakes_csv, export_mistakes_yaml
from src.core.data_governance import filter_mistakes
from src.core.mistakes import import_mistakes_payload, validate_mistakes_payload


def test_create_tables_adds_mistake_context_columns(conn):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(mistakes)").fetchall()}
    assert {"subject_id", "grade_at_time", "term_at_time", "curriculum_version_at_time"}.issubset(columns)


def test_physics_mistakes_import_persists_subject_context(conn):
    report = import_mistakes_payload(conn, {"mistakes": [_physics_speed_mistake()]})
    assert report["errors"] == []
    assert report["imported_count"] == 1

    stored = dict(conn.execute("SELECT * FROM mistakes").fetchone())
    assert stored["student_id"] == "daughter"
    assert stored["subject_id"] == "physics"
    assert stored["grade_at_time"] == 8
    assert stored["term_at_time"] == "\u516b\u5e74\u7ea7\u4e0a"
    assert stored["curriculum_version_at_time"] == "cn_k12_2022"

    rows = filter_mistakes(conn, subject_id="physics", grade_at_time="8")
    assert len(rows) == 1
    assert rows[0]["subject_id"] == "physics"


def test_mistake_list_rows_include_learning_context(conn):
    import_mistakes_payload(conn, {"mistakes": [_math_mistake()]})

    rows = filter_mistakes(conn)
    assert rows
    row = rows[0]
    assert row["student_id"] == "daughter"
    assert row["subject_id"] == "math"
    assert row["grade_at_time"] == 6
    assert row["term_at_time"] == "六年级上"


def test_data_management_filter_rows_include_and_filter_context(conn):
    import_mistakes_payload(conn, {"mistakes": [_math_mistake()]})

    rows = filter_mistakes(conn, student_id="daughter", subject_id="math", grade_at_time="6")
    assert len(rows) == 1
    assert {"student_id", "subject_id", "grade_at_time", "term_at_time"}.issubset(rows[0])


def test_export_mistakes_csv_and_yaml_include_context_fields(conn, tmp_path):
    import_mistakes_payload(conn, {"mistakes": [_math_mistake()]})

    csv_path = export_mistakes_csv(conn, tmp_path, now=datetime(2026, 6, 1, 15, 1, 0))
    yaml_path = export_mistakes_yaml(conn, tmp_path, now=datetime(2026, 6, 1, 15, 1, 1))

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        row = next(csv.DictReader(f))
    assert row["student_id"] == "daughter"
    assert row["subject_id"] == "math"
    assert row["grade_at_time"] == "6"
    assert row["term_at_time"] == "六年级上"

    exported = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    item = exported["mistakes"][0]
    assert item["student_id"] == "daughter"
    assert item["subject_id"] == "math"
    assert item["grade_at_time"] == 6
    assert item["term_at_time"] == "六年级上"


def test_physics_grade8_knowledge_point_name_is_valid_in_scope():
    report, rows = validate_mistakes_payload({"mistakes": [{
        "date": "2026-06-01",
        "subject_id": "physics",
        "grade_at_time": 8,
        "term_at_time": "八年级上",
        "question_type": "physics_calculation",
        "knowledge_point": "速度",
        "mistake_tag": "PHY_F1",
        "difficulty": "基础",
        "question_summary": "速度计算题",
    }]})

    assert report.errors == []
    assert not any(item["code"] == "unknown_knowledge_point" for item in report.warnings)
    assert rows[0]["subject_id"] == "physics"
    assert rows[0]["grade_at_time"] == 8


def test_math_legacy_knowledge_point_name_still_valid():
    report, _ = validate_mistakes_payload({"mistakes": [_math_mistake()]})
    assert report.errors == []
    assert not any(item["code"] == "unknown_knowledge_point" for item in report.warnings)


def test_unknown_knowledge_point_still_warns():
    item = _math_mistake()
    item["knowledge_point"] = "不存在知识点"
    report, _ = validate_mistakes_payload({"mistakes": [item]})
    assert any(warning["code"] == "unknown_knowledge_point" for warning in report.warnings)


def test_knowledge_point_name_does_not_cross_subject_match():
    report, _ = validate_mistakes_payload({"mistakes": [{
        "date": "2026-06-01",
        "subject_id": "chemistry",
        "grade_at_time": 9,
        "term_at_time": "九年级上",
        "question_type": "chem_formula_writing",
        "knowledge_point": "速度",
        "mistake_tag": "CHEM_F1",
        "difficulty": "基础",
        "question_summary": "化学测试题",
    }]})

    assert any(warning["code"] == "unknown_knowledge_point" for warning in report.warnings)


def _physics_speed_mistake() -> dict:
    return {
        "date": "2026-06-01",
        "subject_id": "physics",
        "grade_at_time": 8,
        "term_at_time": "\u516b\u5e74\u7ea7\u4e0a",
        "curriculum_version_at_time": "cn_k12_2022",
        "question_type": "physics_calculation",
        "knowledge_point": "\u901f\u5ea6",
        "mistake_tag": "PHY_F1",
        "difficulty": "\u57fa\u7840",
        "question_summary": "\u901f\u5ea6\u8ba1\u7b97\u9898",
        "source": "pytest",
    }


def _math_mistake() -> dict:
    return {
        "date": "2026-06-01",
        "question_type": "递等式计算",
        "knowledge_point": "小数计算",
        "mistake_tag": "C3",
        "difficulty": "基础",
        "question_summary": "小数计算上下文测试",
    }
