from __future__ import annotations

from pathlib import Path

import yaml

from src.core.import_preview import dry_run_mistakes_yaml, dry_run_worksheet_yaml
from src.core.rule_registry import load_rule_registry
from src.core.schema_integrity import check_schema_integrity
from src.db import init_db
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt


ROOT = Path(__file__).resolve().parents[1]


def _g5b_points():
    registry = load_rule_registry(force_reload=True)
    return [
        point
        for point in registry.get_knowledge_points_for_context("math", 5)
        if point["knowledge_point_id"].startswith("math_g5b_")
    ]


def test_v0191_math_g5b_registry_loads_with_expected_contract():
    registry = load_rule_registry(force_reload=True)
    curriculum = registry.get_curriculum_for("math", 5)
    points = _g5b_points()
    active_tags = {tag["code"] for tag in registry.get_mistake_tags_for_subject("math")}
    difficulties = set(registry.get_difficulty_codes())

    assert curriculum["metadata"]["registry_version"] == "v0.1.9.1-pretrial"
    assert len(points) == 23
    assert len({point["unit_id"] for point in points}) == 6
    assert len({point["lesson"] for point in points}) == 15
    assert all(point["knowledge_point_id"].startswith("math_g5b_") for point in points)
    assert all(point["subject_id"] == "math" for point in points)
    assert all(point["grade"] == 5 for point in points)
    assert all(point["term"] == "五年级下" for point in points)
    assert all(point["textbook_version"] == "沪教版" for point in points)
    assert all(isinstance(point["active"], bool) for point in points)
    assert all(set(point["suitable_difficulty"]) <= difficulties for point in points)
    assert all(set(point["suitable_mistake_tags"]) <= active_tags for point in points)
    assert {point["usage_status"] for point in points} == {"core_active", "review_active"}
    assert sum(point["usage_status"] == "core_active" for point in points) == 16
    assert sum(point["usage_status"] == "review_active" for point in points) == 7


def test_v0191_review_only_scope_is_preserved():
    review_only = [
        point
        for point in _g5b_points()
        if (point.get("metadata") or {}).get("scope_note") == "review_only_for_hujiao_g5b"
    ]

    assert {point["knowledge_point_id"] for point in review_only} == {
        "math_g5b_data_table_reading_review",
        "math_g5b_fraction_concept_calculation_review",
    }
    assert all(point["active"] is True for point in review_only)
    assert all(point["usage_status"] == "review_active" for point in review_only)


def test_v0191_prompt_scope_and_alias_boundary():
    registry = load_rule_registry(force_reload=True)

    grade5_scope = registry.render_curriculum_scope_for_context("math", 5, term="五年级下")
    grade5_scope_data = yaml.safe_load(grade5_scope)
    grade5_scope_ids = {
        point["knowledge_point_id"]
        for unit in grade5_scope_data["units"]
        for point in unit.get("knowledge_points", [])
    }
    assert "math_g5b_speed_time_distance_relation" in grade5_scope
    assert not any(point_id.startswith("math_g6a_") for point_id in grade5_scope_ids)

    grade5_aliases = registry.render_alias_mappings_for_prompt("math", 5)
    grade6_aliases = registry.render_alias_mappings_for_prompt("math", 6)
    assert "math_g5b_speed_time_distance_relation" in grade5_aliases
    assert "math_g5b_speed_time_distance_relation" not in grade6_aliases
    assert "math_g6a_rational_add_different_sign" in grade6_aliases

    marking_prompt = build_marking_prompt({"student_id": "daughter"}, subject_id="math")
    worksheet_prompt = build_worksheet_prompt(
        {"student_id": "daughter"},
        {
            "recent_7_days": [],
            "recent_30_days": [],
            "mistake_tag_by_question_type": [],
            "mistake_tag_by_knowledge_point": [],
            "target_matrix": {"items": []},
            "target_priority_light": {"items": []},
        },
        subject_id="math",
    )
    for prompt in (marking_prompt, worksheet_prompt):
        assert "math_g6a_rational_number_concept" in prompt
        assert "math_g5b_speed_time_distance_relation" not in prompt


def test_v0191_g5b_samples_preview_success(conn):
    mistakes_text = (ROOT / "samples" / "uat_v0191_math_g5b_mistakes.yaml").read_text(encoding="utf-8")
    worksheet_text = (ROOT / "samples" / "uat_v0191_math_g5b_worksheet.yaml").read_text(encoding="utf-8")

    mistakes_preview = dry_run_mistakes_yaml(conn, mistakes_text, "uat_v0191_math_g5b_mistakes.yaml")
    worksheet_preview = dry_run_worksheet_yaml(conn, worksheet_text, "uat_v0191_math_g5b_worksheet.yaml")

    assert mistakes_preview["can_import"], mistakes_preview["validation"]
    assert worksheet_preview["can_import"], worksheet_preview["validation"]
    assert mistakes_preview["total_count"] == 3
    assert worksheet_preview["question_count"] == 4
    roles = {
        question["question_role"]
        for section in worksheet_preview["worksheet"]["sections"]
        for question in section["questions"]
    }
    assert {"repair", "variant", "transfer"} <= roles


def test_v0191_schema_integrity_g5b_contract(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "edu_tutor.db"
    init_db(db_path)
    monkeypatch.setattr("src.core.schema_integrity.DEFAULT_DB_PATH", db_path)
    report = check_schema_integrity(db_path)

    assert report["errors"] == []


def test_v0191_docs_record_g5b_audit_and_boundaries():
    audit = (ROOT / "docs" / "research" / "math_g5b_knowledge_registry_audit_v0.1.9.1.md").read_text(encoding="utf-8")
    handoff = (ROOT / "docs" / "HANDOFF_v0.1.9.1-pretrial.md").read_text(encoding="utf-8")

    assert "Registered `math_g5b_*` knowledge_point count: 23" in audit
    assert "review_only_for_hujiao_g5b" in audit
    assert "No Y-axis math mistake taxonomy change" in handoff
    assert "No DB schema change" in handoff
