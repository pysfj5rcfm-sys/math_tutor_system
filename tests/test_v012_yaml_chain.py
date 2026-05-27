from __future__ import annotations

from pathlib import Path

from src.core.mistakes import import_mistakes_payload, validate_mistakes_payload
from src.core.parse_report import format_parse_error
from src.core.validation_report import format_validation_report
from src.core.worksheets import import_worksheet_payload, validate_worksheet_payload
from src.core.yaml_utils import safe_parse_yaml
from src.prompts.repair_prompt import build_validation_repair_prompt, build_yaml_parse_repair_prompt


ROOT = Path(__file__).resolve().parents[1]


def _sample(name: str) -> str:
    return (ROOT / "samples" / name).read_text(encoding="utf-8")


def test_malformed_mistakes_yaml_returns_parse_result_without_exception():
    result = safe_parse_yaml(_sample("uat_invalid_mistakes_parse_error.yaml"))
    assert result.ok is False
    assert result.line is not None
    assert result.column is not None
    assert result.human_message
    assert result.suggestion


def test_malformed_worksheet_yaml_returns_parse_result_without_exception():
    result = safe_parse_yaml(_sample("uat_invalid_worksheet_parse_error.yaml"))
    assert result.ok is False
    assert result.line is not None
    assert result.column is not None
    assert result.human_message
    assert result.suggestion


def test_parse_repair_prompts_for_mistakes_and_worksheet():
    for source_type, sample_name in [
        ("mistakes", "uat_invalid_mistakes_parse_error.yaml"),
        ("worksheet", "uat_invalid_worksheet_parse_error.yaml"),
    ]:
        text = _sample(sample_name)
        result = safe_parse_yaml(text)
        report = format_parse_error(result, source_type, text)
        prompt = build_yaml_parse_repair_prompt(source_type, report, text)
        assert "只修复 YAML 语法和缩进" in prompt
        assert "不重新出题" in prompt
        assert "不重新批改" in prompt
        assert "不输出 Markdown" in prompt
        assert f"source_type: {source_type}" in prompt


def test_worksheet_readable_validation_report_suggests_aliases():
    text = _sample("uat_invalid_worksheet_for_validation_repair.yaml")
    payload = safe_parse_yaml(text).payload
    validation, _ = validate_worksheet_payload(payload)
    report = format_validation_report(validation.as_dict(), "worksheet", payload, text)
    suggestions = {(item["field"], item["current_value"]): item["suggested_value"] for item in report["readable_items"]}
    assert suggestions[("question_type", "解方程")] == "方程"
    assert suggestions[("knowledge_point", "小数混合运算")] == "小数计算"
    assert suggestions[("difficulty", "简单")] == "基础"
    assert suggestions[("target_mistake_tag", "R4 关键词理解弱")] == "R4"
    assert any(item.get("position_label") for item in report["readable_items"])
    assert any(item.get("field") for item in report["readable_items"])
    assert any(item.get("current_value") is not None for item in report["readable_items"])


def test_mistakes_readable_validation_report_errors_and_warnings():
    text = _sample("uat_invalid_mistakes_for_validation_repair.yaml")
    payload = safe_parse_yaml(text).payload
    validation, _ = validate_mistakes_payload(payload)
    report = format_validation_report(validation.as_dict(), "mistakes", payload, text)
    levels = {item["level"] for item in report["readable_items"]}
    codes = {item["code"] for item in report["readable_items"]}
    assert "warning" in levels
    assert "error" in levels
    assert "unknown_knowledge_point" in codes
    assert "invalid_mistake_tag" in codes
    assert any("第 1 条错因记录" in item.get("position_label", "") for item in report["readable_items"])


def test_validation_repair_prompt_contains_required_constraints():
    text = _sample("uat_invalid_worksheet_for_validation_repair.yaml")
    payload = safe_parse_yaml(text).payload
    validation, _ = validate_worksheet_payload(payload)
    report = format_validation_report(validation.as_dict(), "worksheet", payload, text)
    prompt = build_validation_repair_prompt("worksheet", report, text)
    assert "不重新出题，只修复字段和枚举" in prompt
    assert "不输出 Markdown" in prompt
    assert "合法 question_type 枚举" in prompt
    assert "合法 knowledge_point 枚举" in prompt
    assert "合法 mistake_tag / target_mistake_tag 枚举" in prompt
    assert "只输出修复后的完整 YAML" in prompt


def test_uat_valid_worksheet_v012_passes_validation(conn):
    payload = safe_parse_yaml(_sample("uat_valid_worksheet_v012.yaml")).payload
    validation, worksheet = validate_worksheet_payload(payload)
    assert validation.errors == []
    assert worksheet is not None


def test_uat_invalid_samples_generate_readable_reports():
    mistakes_text = _sample("uat_invalid_mistakes_for_validation_repair.yaml")
    mistakes_payload = safe_parse_yaml(mistakes_text).payload
    mistakes_validation, _ = validate_mistakes_payload(mistakes_payload)
    mistakes_report = format_validation_report(mistakes_validation.as_dict(), "mistakes", mistakes_payload, mistakes_text)
    assert mistakes_report["readable_items"]

    worksheet_text = _sample("uat_invalid_worksheet_for_validation_repair.yaml")
    worksheet_payload = safe_parse_yaml(worksheet_text).payload
    worksheet_validation, _ = validate_worksheet_payload(worksheet_payload)
    worksheet_report = format_validation_report(worksheet_validation.as_dict(), "worksheet", worksheet_payload, worksheet_text)
    assert worksheet_report["readable_items"]


def test_parse_fail_and_validation_fail_do_not_write(conn):
    parse_result = safe_parse_yaml(_sample("uat_invalid_mistakes_parse_error.yaml"))
    assert parse_result.ok is False
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0

    payload = safe_parse_yaml(_sample("uat_invalid_mistakes_for_validation_repair.yaml")).payload
    report = import_mistakes_payload(conn, payload)
    assert report["valid"] is False
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0

    worksheet_payload = safe_parse_yaml(_sample("uat_invalid_worksheet_for_validation_repair.yaml")).payload
    worksheet_report, worksheet_id = import_worksheet_payload(conn, worksheet_payload)
    assert worksheet_report["valid"] is False
    assert worksheet_id is None
    assert conn.execute("SELECT COUNT(*) FROM worksheets").fetchone()[0] == 0


def test_warning_only_imports_as_needs_confirmation(conn):
    payload = {
        "mistakes": [{
            "date": "2026-05-27",
            "question_type": "递等式计算",
            "knowledge_point": "未知知识点",
            "mistake_tag": "C3",
            "difficulty": "基础",
            "question_summary": "warning only",
        }]
    }
    report = import_mistakes_payload(conn, payload)
    assert report["valid"] is True
    assert report["warnings"]
    row = conn.execute("SELECT status FROM mistakes").fetchone()
    assert row["status"] == "needs_confirmation"
