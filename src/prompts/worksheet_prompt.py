from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.rule_registry import load_rule_registry
from src.schemas.worksheet_schema import WORKSHEET_SCHEMA_EXAMPLE


ROOT = Path(__file__).resolve().parents[2]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())


def build_worksheet_prompt(
    student_profile: dict[str, Any],
    stats: dict[str, Any],
    mistake_tags: list[dict[str, Any]] | None = None,
    subject_id: str | None = None,
) -> str:
    registry = load_rule_registry()
    student_id = _resolve_student_id(registry, student_profile)
    resolved_subject_id = subject_id or registry.get_default_subject_for_student(student_id)
    template = _env().get_template("gpt_worksheet_prompt.md.j2")
    active_student = registry.get_student(student_id)
    constraints = (
        active_student.get("profile", {}).get("worksheet_preferences")
        or student_profile.get("default_training_constraints", {})
    )
    return template.render(
        student_profile_yaml=registry.render_student_profile_for_prompt(student_id),
        legacy_student_profile_yaml=yaml.safe_dump(student_profile, allow_unicode=True, sort_keys=False),
        learning_context_yaml=yaml.safe_dump(registry.resolve_learning_context(student_id, resolved_subject_id), allow_unicode=True, sort_keys=False),
        curriculum_scope_yaml=registry.render_curriculum_scope_for_prompt(student_id, resolved_subject_id),
        mistake_tags_yaml=yaml.safe_dump(mistake_tags, allow_unicode=True, sort_keys=False)
        if mistake_tags is not None
        else registry.render_mistake_tags_for_prompt(resolved_subject_id),
        stats_7_yaml=yaml.safe_dump(stats.get("recent_7_days", []), allow_unicode=True, sort_keys=False),
        stats_30_yaml=yaml.safe_dump(stats.get("recent_30_days", []), allow_unicode=True, sort_keys=False),
        by_type_yaml=yaml.safe_dump(stats.get("mistake_tag_by_question_type", []), allow_unicode=True, sort_keys=False),
        by_knowledge_yaml=yaml.safe_dump(stats.get("mistake_tag_by_knowledge_point", []), allow_unicode=True, sort_keys=False),
        constraints_yaml=yaml.safe_dump(constraints, allow_unicode=True, sort_keys=False),
        question_types_yaml=registry.render_question_types_for_prompt(resolved_subject_id),
        knowledge_points_yaml=registry.render_curriculum_scope_for_prompt(student_id, resolved_subject_id),
        mistake_tag_codes_yaml=yaml.safe_dump(
            [item["code"] for item in registry.get_mistake_tags_for_subject(resolved_subject_id)],
            allow_unicode=True,
            sort_keys=False,
        ),
        difficulties_yaml=registry.render_difficulty_levels_for_prompt(),
        expression_capabilities_yaml=registry.render_expression_capabilities_for_prompt(resolved_subject_id),
        alias_mappings_yaml=registry.render_alias_mappings_for_prompt(),
        worksheet_policies_yaml=registry.render_worksheet_policies_for_prompt(),
        worksheet_schema_yaml=yaml.safe_dump(WORKSHEET_SCHEMA_EXAMPLE, allow_unicode=True, sort_keys=False),
    )


def save_worksheet_prompt(prompt: str, output_dir: str | Path = ROOT / "outputs" / "prompts") -> Path:
    path = Path(output_dir) / "gpt_worksheet_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path


def _resolve_student_id(registry: Any, student_profile: dict[str, Any]) -> str:
    student_id = student_profile.get("student_id")
    if student_id:
        try:
            registry.get_student(str(student_id))
            return str(student_id)
        except Exception:
            pass
    return registry.get_active_student_id()
