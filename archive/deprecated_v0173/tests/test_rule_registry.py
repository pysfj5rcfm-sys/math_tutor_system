from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
import yaml

from src.core.rule_registry import DEFAULT_CONFIG_DIR, RuleRegistryError, load_rule_registry
from src.core.validation_report import format_validation_report
from src.core.worksheets import validate_worksheet_payload
from src.db import create_tables, seed_mistake_tags
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.repair_prompt import build_validation_repair_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt


def test_rule_registry_loads_all_configs_and_core_values():
    registry = load_rule_registry(force_reload=True)
    assert registry.validate_config()["valid"] is True
    assert {"递等式计算", "方程", "应用题"}.issubset(registry.get_question_type_codes())
    assert {"小数计算", "长方体/正方体体积", "阅读理解型应用题"}.issubset(registry.get_knowledge_point_codes())
    assert registry.get_difficulty_codes() == ["basic", "medium", "advanced", "challenge"]
    assert {"C1", "C3", "F3", "R4", "U1", "G1", "H1"}.issubset(registry.get_mistake_tag_codes())
    assert len(registry.get_mistake_tag_codes()) >= 30
    assert registry.list_policies()


def test_registry_alias_suggestions():
    registry = load_rule_registry()
    assert registry.suggest_question_type("解方程") == "math_equation"
    assert registry.suggest_knowledge_point("速度") == "physics_g8_speed"
    assert registry.suggest_difficulty("简单") == "basic"
    assert registry.suggest_mistake_tag("R4 关键词理解弱") == "R4"


def test_validator_accepts_question_type_added_to_temp_registry(tmp_path: Path):
    config_dir = _copy_config(tmp_path)
    data = _read_yaml(config_dir / "question_types.yaml")
    data["question_types"].append({
        "code": "新题型",
        "display_name": "新题型",
        "active": True,
        "default_layout": "single_column",
    })
    _write_yaml(config_dir / "question_types.yaml", data)

    registry = load_rule_registry(config_dir, force_reload=True)
    payload = _worksheet(question_type="新题型")
    report, worksheet = validate_worksheet_payload(payload, registry=registry)
    assert report.errors == []
    assert worksheet is not None


def test_invalid_values_still_error_and_unknown_knowledge_warns():
    payload = _worksheet(
        question_type="不存在题型",
        knowledge_point="未知知识点",
        difficulty="很难",
        target_mistake_tag="BAD",
    )
    report, worksheet = validate_worksheet_payload(payload)
    assert worksheet is None
    codes = {item["code"] for item in report.errors}
    assert {"invalid_question_type", "invalid_difficulty", "invalid_mistake_tag"}.issubset(codes)
    assert any(item["code"] == "unknown_knowledge_point" for item in report.warnings)


def test_validation_report_uses_registry_suggestion():
    payload = _worksheet(question_type="不存在题型")
    report, _ = validate_worksheet_payload(payload)
    readable = format_validation_report(report.as_dict(), "worksheet", payload, "")
    item = next(item for item in readable["readable_items"] if item["field"] == "question_type")
    assert item["suggested_value"] in (None, "")
    assert "方程" in item["legal_values"]


def test_alias_target_must_exist(tmp_path: Path):
    config_dir = _copy_config(tmp_path)
    aliases = _read_yaml(config_dir / "alias_mappings.yaml")
    aliases["question_type_aliases"]["坏别名"] = "不存在题型"
    _write_yaml(config_dir / "alias_mappings.yaml", aliases)
    with pytest.raises(RuleRegistryError, match="坏别名"):
        load_rule_registry(config_dir, force_reload=True)


def test_prompts_use_registry_content(conn):
    registry = load_rule_registry()
    worksheet_prompt = build_worksheet_prompt({}, {"recent_7_days": [], "recent_30_days": []}, subject_id="math")
    marking_prompt = build_marking_prompt({}, subject_id="math")
    repair_prompt = build_validation_repair_prompt(
        "worksheet",
        {"readable_items": [], "raw_validation": {}},
        "worksheet: {}",
    )
    assert registry.get_question_type_codes()[0] in worksheet_prompt
    assert "question_type_code" in worksheet_prompt
    assert "C3" in worksheet_prompt
    assert "基础" in worksheet_prompt
    assert "math_g6_default" in worksheet_prompt
    assert "chinese_g6_default" not in worksheet_prompt
    assert "alias 映射提示" in repair_prompt
    assert "合法 question_type_code 枚举" in marking_prompt
    assert "UAT" not in registry.render_worksheet_policies_for_prompt()
    assert "4+3+2+2+3" not in registry.render_worksheet_policies_for_prompt()


def test_db_seed_uses_registry_and_is_idempotent(tmp_path: Path):
    config_dir = _copy_config(tmp_path)
    data = _read_yaml(config_dir / "mistake_tags.yaml")
    data["mistake_tags"].append({
        "code": "T1",
        "category": "测试分类",
        "name": "测试标签",
        "description": "测试新增配置标签。",
        "typical_symptoms": ["测试症状"],
        "training_hint": "测试训练建议。",
        "default_question_types": ["递等式计算"],
        "active": True,
    })
    _write_yaml(config_dir / "mistake_tags.yaml", data)
    registry = load_rule_registry(config_dir, force_reload=True)

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_tables(db)
    seed_mistake_tags(db, registry=registry)
    seed_mistake_tags(db, registry=registry)
    assert db.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0] == len(registry.get_mistake_tag_codes())
    assert db.execute("SELECT COUNT(*) FROM mistake_tags WHERE code = 'T1'").fetchone()[0] == 1
    db.execute(
        """
        INSERT INTO mistakes (
            student_id, subject_id, grade_at_time, curriculum_version_at_time, date,
            question_type_code, knowledge_point_id, primary_mistake_tag_code,
            difficulty_code, question_summary, status, created_at, updated_at
        )
        VALUES ('daughter', 'math', 6, 'cn_k12_2022', '2026-05-27',
            'math_calculation', 'math_g6_fraction_operations', 'C3',
            'basic', 'keep me', 'needs_confirmation', 'now', 'now')
        """
    )
    seed_mistake_tags(db, registry=registry)
    assert db.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 1
    db.close()


def test_streamlit_pages_expose_rule_registry_and_policies():
    import src.app as app

    assert "规则库查看" in app.PAGES
    assert "出卷质量验收清单" in app.PAGES
    assert load_rule_registry().list_policies()


def _copy_config(tmp_path: Path) -> Path:
    target = tmp_path / "config"
    shutil.copytree(DEFAULT_CONFIG_DIR, target)
    return target


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _worksheet(
    question_type: str = "递等式计算",
    knowledge_point: str = "小数计算",
    target_mistake_tag: str = "C3",
    difficulty: str = "基础",
) -> dict:
    return {
        "worksheet": {
            "title": "测试卷",
            "date": "2026-05-27",
            "student_id": "daughter_grade5",
            "sections": [{
                "name": "一、测试",
                "layout": "single_column",
                "questions": [{
                    "question_type": question_type,
                    "knowledge_point": knowledge_point,
                    "target_mistake_tag": target_mistake_tag,
                    "difficulty": difficulty,
                    "question": "1+1=",
                    "answer": "2",
                    "explanation": "计算即可。",
                }],
            }],
        }
    }
