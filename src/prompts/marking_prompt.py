from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.rule_registry import load_rule_registry
from src.schemas.mistake_schema import MISTAKES_SCHEMA_EXAMPLE


ROOT = Path(__file__).resolve().parents[2]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())


def build_marking_prompt(
    student_profile: dict[str, Any],
    mistake_tags: list[dict[str, Any]] | None = None,
    subject_id: str | None = None,
    confirmed_stats: dict[str, Any] | None = None,
) -> str:
    registry = load_rule_registry()
    student_id = _resolve_student_id(registry, student_profile)
    resolved_subject_id = subject_id or registry.get_default_subject_for_student(student_id)
    template = _env().get_template("gpt_marking_prompt.md.j2")
    return template.render(
        student_profile_yaml=registry.render_student_profile_for_prompt(student_id),
        legacy_student_profile_yaml=yaml.safe_dump(student_profile, allow_unicode=True, sort_keys=False),
        learning_context_yaml=yaml.safe_dump(registry.resolve_learning_context(student_id, resolved_subject_id), allow_unicode=True, sort_keys=False),
        curriculum_scope_yaml=registry.render_curriculum_scope_for_prompt(student_id, resolved_subject_id),
        mistake_tags_yaml=yaml.safe_dump(mistake_tags, allow_unicode=True, sort_keys=False)
        if mistake_tags is not None
        else registry.render_mistake_tags_for_prompt(resolved_subject_id),
        question_types_yaml=registry.render_question_types_for_prompt(resolved_subject_id),
        knowledge_points_yaml=registry.render_curriculum_scope_for_prompt(student_id, resolved_subject_id),
        difficulties_yaml=registry.render_difficulty_levels_for_prompt(),
        expression_capabilities_yaml=registry.render_expression_capabilities_for_prompt(resolved_subject_id),
        confirmed_stats_yaml=yaml.safe_dump(confirmed_stats or {}, allow_unicode=True, sort_keys=False),
        alias_mappings_yaml=registry.render_alias_mappings_for_prompt(),
        mistake_schema_yaml=yaml.safe_dump(MISTAKES_SCHEMA_EXAMPLE, allow_unicode=True, sort_keys=False),
    )


def save_marking_prompt(prompt: str, output_dir: str | Path = ROOT / "outputs" / "prompts") -> Path:
    path = Path(output_dir) / "gpt_marking_prompt.md"
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
