from __future__ import annotations

import re
from pathlib import Path

import yaml

from src.core.rule_registry import load_rule_registry


ROOT = Path(__file__).resolve().parents[1]
OLD_BARE_TAGS = {"C1", "C2", "C3", "C4", "F1", "F2", "F3", "R1", "R2", "R3", "R4", "M1", "M2", "M3", "U1", "G1", "K3"}
MOJIBAKE_PATTERNS = ("�", "Ã", "Â", "â€", "â€™", "â€œ", "â€\x9d", "ä¸", "çš", "ï»¿", "å\x90", "æ\x98", "è¯", "ä½", "å­¦")


def test_registry_no_longer_loads_legacy_knowledge_points_file():
    registry = load_rule_registry(force_reload=True)

    assert not (ROOT / "config" / "knowledge_points.yaml").exists()
    assert not hasattr(registry, "get_legacy_knowledge_points")
    assert not hasattr(registry, "render_legacy_knowledge_points_for_prompt")
    assert "math_g6_number_operations" in registry.get_curriculum_knowledge_point_codes()
    assert registry.get_all_knowledge_point_codes() == registry.get_curriculum_knowledge_point_codes()


def test_active_student_subjects_and_curriculum_scope():
    registry = load_rule_registry()
    student = registry.get_student("daughter")

    assert student["current_grade"] == 6
    assert student["active_subjects"] == ["math", "chinese", "english"]
    assert registry.get_knowledge_points_for_student("daughter", "math")[0]["subject_id"] == "math"
    assert any(p["knowledge_point_id"] == "chinese_g6_text_evidence" for p in registry.get_knowledge_points_for_student("daughter", "chinese"))
    assert any(p["knowledge_point_id"] == "english_g6_reading_detail" for p in registry.get_knowledge_points_for_student("daughter", "english"))


def test_question_types_have_no_legacy_names():
    registry = load_rule_registry()

    for item in registry.get_question_types(active_only=False):
        assert "legacy_names" not in item
    assert "chinese_reading" in registry.get_question_type_canonical_codes()
    assert "english_reading" in registry.get_question_type_canonical_codes()


def test_namespaced_mistake_taxonomy_replaces_old_bare_tags():
    registry = load_rule_registry()
    active_codes = {tag["code"] for tag in registry.get_mistake_tags(active_only=True)}

    assert {"MATH_C3", "MATH_F3", "GEN_R4", "GEN_M2", "CHN_EVD_1", "ENG_GRAM_1"} <= active_codes
    assert OLD_BARE_TAGS.isdisjoint(active_codes)
    assert "GEN_R4" in {tag["code"] for tag in registry.get_mistake_tags_for_subject("math")}
    assert "GEN_R4" in {tag["code"] for tag in registry.get_mistake_tags_for_subject("chinese")}
    assert "CHN_EVD_1" not in {tag["code"] for tag in registry.get_mistake_tags_for_subject("english")}
    assert "ENG_GRAM_1" not in {tag["code"] for tag in registry.get_mistake_tags_for_subject("chinese")}


def test_subject_difficulty_policy_shape_has_no_unknown_difficulty_warning():
    registry = load_rule_registry(force_reload=True)
    validation = registry.validate_config()
    policy = registry.worksheet_policy["subject_difficulty_policy"]

    assert validation["errors"] == []
    assert validation["warnings"] == []
    assert set(policy) == {"math", "chinese", "english"}
    assert set(policy["math"]) == {"basic", "medium", "advanced", "challenge"}


def test_alias_mappings_are_subject_scoped_and_clean():
    registry = load_rule_registry()

    assert registry.resolve_alias("mistake_tag_aliases", "小数点错误", "math").target == "MATH_C3"
    assert registry.resolve_alias("mistake_tag_aliases", "文本证据不足", "chinese").target == "CHN_EVD_1"
    assert registry.resolve_alias("mistake_tag_aliases", "时态错误", "english").target == "ENG_GRAM_1"
    assert registry.resolve_alias("question_type_aliases", "阅读理解", "chinese").target == "chinese_reading"
    assert registry.resolve_alias("question_type_aliases", "阅读理解", "english").target == "english_reading"
    assert registry.resolve_alias("question_type_aliases", "阅读理解", None).ambiguous
    assert registry.resolve_alias("mistake_tag_aliases", "C3", "math").target is None


def test_active_config_and_samples_have_no_mojibake_or_old_bare_tags():
    paths = []
    for pattern in ("config/**/*.yaml", "templates/**/*.j2", "templates/**/*.html", "src/prompts/**/*.py", "src/core/**/*.py", "samples/*.yaml"):
        paths.extend(ROOT.glob(pattern))

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for marker in MOJIBAKE_PATTERNS:
            assert marker not in text, f"{path} contains mojibake marker {marker!r}"
        if "samples" in path.parts or path.match("config/education/mistake_taxonomy.yaml"):
            for tag in OLD_BARE_TAGS:
                assert not re.search(rf"(?<![A-Z0-9_]){re.escape(tag)}(?![A-Z0-9_])", text), f"{path} contains old bare tag {tag}"


def test_alias_targets_exist_in_active_registry_only():
    registry = load_rule_registry()
    alias_file = yaml.safe_load((ROOT / "config" / "alias_mappings.yaml").read_text(encoding="utf-8"))
    qtypes = set(registry.get_question_type_canonical_codes())
    points = set(registry.get_curriculum_knowledge_point_codes())
    tags = {tag["code"] for tag in registry.get_mistake_tags(active_only=True)}
    difficulties = set(registry.get_difficulty_codes())

    for scope in alias_file["question_type_aliases"].values():
        assert set(scope.values()) <= qtypes
    for scope in alias_file["knowledge_point_aliases"].values():
        assert set(scope.values()) <= points
    for scope in alias_file["mistake_tag_aliases"].values():
        assert set(scope.values()) <= tags
    assert set(alias_file["difficulty_aliases"].values()) <= difficulties
