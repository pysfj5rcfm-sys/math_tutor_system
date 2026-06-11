from __future__ import annotations

from pathlib import Path

from src.core.import_preview import dry_run_mistakes_yaml, dry_run_worksheet_yaml
from src.core.rule_registry import load_rule_registry
from src.core.schema_integrity import check_schema_integrity
from src.core.target_matrix import build_target_matrix_from_confirmed_mistakes, render_target_matrix_for_prompt
from src.db import REGISTRY_MODE, REGISTRY_VERSION, SCHEMA_VERSION, init_db
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt
from scripts.audit_registry_health import run_audit


ROOT = Path(__file__).resolve().parents[1]
OLD_BARE_TAGS = {"C3", "R4", "M2", "F3", "U1", "G1"}
MATH_CATEGORIES = {
    "concept_definition",
    "rule_application",
    "calculation_execution",
    "sign_symbol",
    "condition_judgement",
    "representation_transfer",
    "modeling_relation",
    "method_formula_selection",
    "unit_measurement",
    "geometry_spatial",
    "data_graph_reading",
    "process_expression",
    "checking_estimation",
    "reading_comprehension",
}


def test_math_g6a_hujiao_curriculum_metadata_is_preserved():
    registry = load_rule_registry(force_reload=True)
    curriculum = registry.get_curriculum_for("math", 6)
    points = registry.get_knowledge_points_for_context("math", 6)
    active_tags = {tag["code"] for tag in registry.get_mistake_tags_for_subject("math")}
    difficulties = set(registry.get_difficulty_codes())

    assert curriculum["registry_version"] == "v0.1.8.1"
    assert curriculum["textbook_version"] == "沪教版"
    assert len(points) == 18
    assert all(point["knowledge_point_id"].startswith("math_g6a_") for point in points)
    assert all(isinstance(point["active"], bool) for point in points)
    assert {point["usage_status"] for point in points} >= {"core_active", "review_active", "intro_active", "reserved_inactive"}
    assert all(set(point["suitable_difficulty"]) <= difficulties for point in points)
    assert all(set(point["suitable_mistake_tags"]) <= active_tags for point in points)

    target = next(point for point in points if point["knowledge_point_id"] == "math_g6a_rational_add_different_sign")
    assert target["micro_skill"]
    assert "计算题" in target["typical_question_forms"]
    assert "MATH_SIGN_RULE_ERROR" in target["suitable_mistake_tags"]


def test_v018_research_sources_are_full_reports_not_placeholders():
    source_dir = ROOT / "docs" / "research" / "source"
    x_source = source_dir / "沪教版六年级上数学知识点体系深度研究报告(2).md"
    y_source = source_dir / "edu_tutor_system 数学 Mistake Tag Taxonomy 深度研究.md"
    x_text = x_source.read_text(encoding="utf-8")
    y_text = y_source.read_text(encoding="utf-8")

    assert len(x_text) > 5000
    assert len(y_text) > 5000
    assert "沪教版六年级上数学知识点体系深度研究报告" in x_text
    assert "候选 registry 共 35 个知识点" in x_text
    assert "edu_tutor_system 数学 Mistake Tag Taxonomy 深度研究" in y_text
    assert "我建议第一版 active taxonomy 采用 **28 个标签**" in y_text
    assert "source placeholder" not in x_text.lower()
    assert "source placeholder" not in y_text.lower()


def test_math_v018_taxonomy_active_tags_and_categories():
    registry = load_rule_registry()
    math_tags = registry.get_mistake_tags_for_subject("math")
    codes = {tag["code"] for tag in math_tags}

    assert len(math_tags) == 28
    assert all(code.startswith(("MATH_", "GEN_")) for code in codes)
    assert OLD_BARE_TAGS.isdisjoint(codes)
    assert not any(code.startswith("YV-") for code in codes)
    assert {tag["category"] for tag in math_tags} == MATH_CATEGORIES
    assert "GEN_CONDITION_OMISSION" in codes
    assert "GEN_READING_KEYWORD_MISUNDERSTANDING" in codes
    assert "GEN_CHECKING_OMISSION" in codes
    assert "MATH_EQUALITY_RELATION_ERROR" in codes
    assert "MATH_QUANTITATIVE_RELATION_ERROR" in codes
    assert "MATH_MODEL_CONSTRUCTION_ERROR" in codes
    assert "MATH_UNIT_MEANING_ERROR" in codes
    assert "MATH_UNIT_CONVERSION_ERROR" in codes
    assert all(tag["definition"] and tag["use_when"] and tag["do_not_use_when"] for tag in math_tags)
    assert all(isinstance(tag["allowed_secondary"], bool) for tag in math_tags)
    assert all(isinstance(tag["conflict_with"], list) for tag in math_tags)
    assert all(isinstance(tag["primary_priority"], int) and 1 <= tag["primary_priority"] <= 100 for tag in math_tags)
    assert not any("old_code_reference_only" in tag for tag in math_tags)


def test_v018_aliases_and_prompts_are_metadata_rich_and_clean():
    registry = load_rule_registry()
    assert registry.resolve_alias("knowledge_point_aliases", "异号两数相加", "math").target == "math_g6a_rational_add_different_sign"
    assert registry.resolve_alias("mistake_tag_aliases", "等量关系理解错误", "math").target == "MATH_EQUALITY_RELATION_ERROR"
    assert registry.resolve_alias("mistake_tag_aliases", "C3", "math").target is None

    marking_prompt = build_marking_prompt({"student_id": "daughter"}, subject_id="math")
    worksheet_prompt = build_worksheet_prompt(
        {"student_id": "daughter"},
        {
            "recent_7_days": [],
            "recent_30_days": [],
            "mistake_tag_by_question_type": [],
            "mistake_tag_by_knowledge_point": [],
            "target_matrix": {
                "items": [
                    {
                        "knowledge_point_id": "math_g6a_rational_add_different_sign",
                        "primary_mistake_tag_code": "MATH_SIGN_RULE_ERROR",
                        "count_7d": 1,
                        "count_30d": 2,
                        "latest_date": "2026-06-03",
                        "priority": 10,
                    }
                ]
            },
        },
        subject_id="math",
    )
    for prompt in (marking_prompt, worksheet_prompt):
        assert "math_g6a_rational_add_different_sign" in prompt
        assert "MATH_SIGN_RULE_ERROR" in prompt
        assert "micro_skill" in prompt
        assert "typical_question_forms" in prompt
        assert "definition" in prompt
        assert "use_when" in prompt
        assert "do_not_use_when" in prompt
        assert "primary_priority" in prompt
        assert "MATH_C3" not in prompt
        assert "YV-" not in prompt
    assert "school training examples" in worksheet_prompt
    assert "target_matrix" in worksheet_prompt


def test_target_matrix_empty_data_is_friendly(conn):
    matrix = build_target_matrix_from_confirmed_mistakes(conn, "daughter", "math", 6, today="2026-06-03")
    rendered = render_target_matrix_for_prompt(matrix)

    assert matrix["items"] == []
    assert "No confirmed mistakes" in matrix["message"]
    assert "primary_mistake_tag_code only" in rendered


def test_v018_samples_preview_success(conn):
    mistakes_text = (ROOT / "samples" / "uat_v018_math_g6a_xy_mistakes.yaml").read_text(encoding="utf-8")
    worksheet_text = (ROOT / "samples" / "uat_v018_math_g6a_xy_worksheet.yaml").read_text(encoding="utf-8")

    mistakes_preview = dry_run_mistakes_yaml(conn, mistakes_text, "uat_v018_math_g6a_xy_mistakes.yaml")
    worksheet_preview = dry_run_worksheet_yaml(conn, worksheet_text, "uat_v018_math_g6a_xy_worksheet.yaml")
    assert mistakes_preview["can_import"], mistakes_preview["validation"]
    assert worksheet_preview["can_import"], worksheet_preview["validation"]
    assert mistakes_preview["total_count"] == 4
    assert worksheet_preview["question_count"] == 4


def test_v018_schema_integrity_and_version_contract(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "edu_tutor.db"
    init_db(db_path)
    monkeypatch.setattr("src.core.schema_integrity.DEFAULT_DB_PATH", db_path)
    report = check_schema_integrity(db_path)

    assert report["errors"] == []
    assert SCHEMA_VERSION == "0.1.7"
    assert REGISTRY_VERSION == "0.1.8.1"
    assert REGISTRY_MODE == "no_legacy"


def test_v0181_audit_docs_match_registry_counts():
    x_audit = (ROOT / "docs" / "research" / "math_g6a_x_registry_audit_v0.1.8.1.md").read_text(encoding="utf-8")
    y_audit = (ROOT / "docs" / "research" / "math_y_taxonomy_audit_v0.1.8.1.md").read_text(encoding="utf-8")

    assert "Source candidate knowledge points: 35" in x_audit
    assert "Current registered knowledge point rows: 18" in x_audit
    assert "too_coarse_needs_split_later" in x_audit
    assert "25 `MATH_*` tags" in y_audit
    assert "3 `GEN_*` tags" in y_audit
    assert "`MATH_EQUALITY_RELATION_ERROR` | yes" in y_audit


def test_audit_registry_health_has_no_active_unfixed_hits():
    hits = run_audit()
    assert [hit for hit in hits if hit.active and not hit.fixed] == []
