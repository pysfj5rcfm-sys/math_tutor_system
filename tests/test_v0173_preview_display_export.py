from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from src.core.backup_export import export_mistakes_csv, export_mistakes_yaml, export_worksheet_items_csv
from src.core.display import difficulty_display, knowledge_point_display, mistake_tag_display, question_type_display
from src.core.display_contract import (
    format_duplicate_row_for_display,
    format_export_row,
    format_mistake_row_for_display,
    make_filter_option,
)
from src.core.duplicate_guard import detect_duplicate_mistakes
from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload
from src.core.worksheets import confirm_worksheet_import, preview_worksheet_payload


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return yaml.safe_load((ROOT / "samples" / name).read_text(encoding="utf-8"))


def test_v0173_mistake_samples_preview_success(conn):
    for name in (
        "uat_v0173_math_g6_mistakes.yaml",
        "uat_v0173_chinese_g6_mistakes.yaml",
        "uat_v0173_english_g6_mistakes.yaml",
    ):
        preview = preview_mistakes_payload(conn, _load(name))
        assert preview["valid"], (name, preview["validation"])
        assert preview["will_import_count"] == 2


def test_v0173_worksheet_samples_preview_success(conn):
    for name in (
        "uat_v0173_math_g6_worksheet.yaml",
        "uat_v0173_chinese_g6_worksheet.yaml",
        "uat_v0173_english_g6_worksheet.yaml",
    ):
        preview = preview_worksheet_payload(conn, _load(name))
        assert preview["valid"], (name, preview["validation"])
        assert preview["question_count"] >= 3


def test_invalid_cross_subject_and_ambiguous_alias_samples_do_not_silently_pass(conn):
    invalid = preview_mistakes_payload(conn, _load("uat_v0173_invalid_cross_subject_knowledge_point.yaml"))
    assert invalid["valid"]
    assert invalid["valid_rows"][0]["knowledge_point_id"] is None
    assert any(item["code"] == "unknown_knowledge_point" for item in invalid["validation"]["warnings"])

    ambiguous = preview_mistakes_payload(conn, _load("uat_v0173_cross_subject_alias_ambiguous.yaml"))
    assert not ambiguous["valid"]
    assert any(item["code"] == "invalid_learning_context" for item in ambiguous["validation"]["errors"])


def test_old_field_names_are_not_accepted_as_no_legacy_input(conn):
    payload = {
        "mistakes": [
            {
                "student_id": "daughter",
                "subject_id": "math",
                "grade_at_time": 6,
                "curriculum_version_at_time": "cn_k12_2022",
                "date": "2026-06-03",
                "question_type": "计算题",
                "knowledge_point": "数与运算",
                "mistake_tag": "小数点错误",
                "difficulty": "基础",
                "question_summary": "old field names should fail",
            }
        ]
    }
    preview = preview_mistakes_payload(conn, payload)
    assert not preview["valid"]
    assert any(item["code"] == "invalid_question_type" for item in preview["validation"]["errors"])


def test_display_resolver_and_filter_contract():
    assert knowledge_point_display("chinese_g6_text_evidence", "chinese", 6) == "文本证据 (chinese_g6_text_evidence)"
    assert knowledge_point_display("english_g6_reading_detail", "english", 6) == "阅读细节定位 (english_g6_reading_detail)"
    assert knowledge_point_display("math_g6_number_operations", "math", 6) == "数与运算 (math_g6_number_operations)"
    assert knowledge_point_display("old_unknown", "math", 6) == "Unknown(old_unknown)"
    assert question_type_display("chinese_reading") == "阅读理解 (chinese_reading)"
    assert mistake_tag_display("MATH_C3") == "小数点 / 位数错误 (MATH_C3)"
    assert difficulty_display("basic") == "基础 (basic)"

    option = make_filter_option("knowledge_point_id", "chinese_g6_text_evidence", {"subject_id": "chinese", "grade_at_time": 6})
    assert option == {"value": "chinese_g6_text_evidence", "label": "文本证据 (chinese_g6_text_evidence)"}


def test_business_row_formatters_use_code_and_display_columns():
    row = {
        "subject_id": "english",
        "grade_at_time": 6,
        "curriculum_version_at_time": "cn_k12_2022",
        "question_type_code": "english_reading",
        "knowledge_point_id": "english_g6_reading_detail",
        "primary_mistake_tag_code": "ENG_READ_1",
        "difficulty_code": "medium",
        "type": "bad",
        "display": "bad",
        "name": "bad",
    }
    formatted = format_mistake_row_for_display(row)
    assert formatted["knowledge_point_display"] == "阅读细节定位 (english_g6_reading_detail)"
    assert formatted["mistake_tag_display"] == "阅读定位不准 (ENG_READ_1)"
    assert "type" not in formatted
    assert "display" not in formatted
    assert "name" not in formatted
    assert format_duplicate_row_for_display(row)["question_type_display"] == "阅读理解 (english_reading)"
    assert format_export_row(row)["difficulty_display"] == "中等 (medium)"


def test_export_contains_display_columns_and_utf8(conn, tmp_path: Path):
    preview = preview_mistakes_payload(conn, _load("uat_v0173_chinese_g6_mistakes.yaml"))
    confirm_mistakes_import(conn, preview, duplicate_strategy="import_all")
    worksheet_preview = preview_worksheet_payload(conn, _load("uat_v0173_english_g6_worksheet.yaml"))
    confirm_worksheet_import(conn, worksheet_preview, duplicate_strategy="import_all")

    csv_path = export_mistakes_csv(conn, tmp_path)
    yaml_path = export_mistakes_yaml(conn, tmp_path)
    worksheet_csv = export_worksheet_items_csv(conn, tmp_path)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert {row["knowledge_point_display"] for row in rows} >= {
        "文本证据 (chinese_g6_text_evidence)",
        "阅读概括 (chinese_g6_reading_summary)",
    }
    assert "question_type" not in rows[0]

    dumped = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert dumped["mistakes"][0]["knowledge_point_display"]
    worksheet_rows = list(csv.DictReader(worksheet_csv.open("r", encoding="utf-8-sig", newline="")))
    assert worksheet_rows[0]["knowledge_point_display"]
    assert json.dumps(dumped, ensure_ascii=False)


def test_duplicate_detection_uses_display_contract(conn):
    payload = _load("uat_v0173_math_g6_mistakes.yaml")
    preview = preview_mistakes_payload(conn, payload)
    confirm_mistakes_import(conn, preview, duplicate_strategy="import_all")
    duplicate_preview = preview_mistakes_payload(conn, payload)

    assert duplicate_preview["duplicate_count"] == 2
    duplicate = duplicate_preview["duplicate_scan"]["duplicates"][0]
    assert duplicate["knowledge_point_id"] == "math_g6_application_modeling"
    assert duplicate["knowledge_point_display"] == "应用题建模 (math_g6_application_modeling)"
    assert duplicate["mistake_tag_display"] == "等量关系找不到 (MATH_MODEL_1)"
