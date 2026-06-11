from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.current_student import get_current_student_id, resolve_task_scope
from src.core.rule_registry import load_rule_registry
from src.schemas.mistake_schema import MISTAKES_SCHEMA_EXAMPLE


ROOT = Path(__file__).resolve().parents[2]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates", encoding="utf-8"), autoescape=select_autoescape())


def build_marking_prompt(
    student_profile: dict[str, Any],
    mistake_tags: list[dict[str, Any]] | None = None,
    subject_id: str | None = None,
    confirmed_stats: dict[str, Any] | None = None,
    task_scope: dict[str, Any] | None = None,
) -> str:
    registry = load_rule_registry()
    student_id = _resolve_student_id(registry, student_profile)
    resolved_subject_id = _resolve_subject_id(registry, student_id, subject_id, student_profile)
    context = (
        resolve_task_scope({**task_scope, "student_id": task_scope.get("student_id") or student_id}, subject_id=resolved_subject_id, registry=registry)
        if task_scope
        else registry.resolve_learning_context(student_id, resolved_subject_id)
    )
    student_id = str(context["student_id"])
    resolved_subject_id = str(context["subject_id"])
    template = _env().get_template("gpt_marking_prompt.md.j2")
    return template.render(
        student_profile_yaml=registry.render_student_profile_for_prompt(student_id),
        student_profile_snapshot_yaml=yaml.safe_dump(_prompt_profile_snapshot(student_profile), allow_unicode=True, sort_keys=False),
        learning_context_yaml=yaml.safe_dump(context, allow_unicode=True, sort_keys=False),
        curriculum_scope_yaml=registry.render_curriculum_scope_for_context(
            resolved_subject_id,
            context["grade_at_time"],
            context["curriculum_version_at_time"],
            student_id=student_id,
            term=context["term_at_time"],
        ),
        mistake_tags_yaml=yaml.safe_dump(mistake_tags, allow_unicode=True, sort_keys=False)
        if mistake_tags is not None
        else registry.render_mistake_tags_for_prompt(resolved_subject_id),
        question_types_yaml=registry.render_question_types_for_prompt(resolved_subject_id),
        knowledge_points_yaml=registry.render_curriculum_scope_for_context(
            resolved_subject_id,
            context["grade_at_time"],
            context["curriculum_version_at_time"],
            student_id=student_id,
            term=context["term_at_time"],
        ),
        difficulties_yaml=registry.render_difficulty_levels_for_prompt(),
        expression_capabilities_yaml=registry.render_expression_capabilities_for_prompt(resolved_subject_id),
        confirmed_stats_yaml=yaml.safe_dump(confirmed_stats or {}, allow_unicode=True, sort_keys=False),
        alias_mappings_yaml=registry.render_alias_mappings_for_prompt(resolved_subject_id, context["grade_at_time"]),
        mistake_schema_yaml=yaml.safe_dump(MISTAKES_SCHEMA_EXAMPLE, allow_unicode=True, sort_keys=False),
    )


def save_marking_prompt(
    prompt: str,
    output_dir: str | Path = ROOT / "outputs" / "prompts",
    student_id: str = "daughter",
    subject_id: str = "math",
    grade_at_time: int | str = 6,
    now: datetime | None = None,
) -> Path:
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"marking_prompt_{student_id}_{subject_id}_g{grade_at_time}_{stamp}.md"
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
    return get_current_student_id(registry=registry)


def _resolve_subject_id(registry: Any, student_id: str, subject_id: str | None, student_profile: dict[str, Any]) -> str:
    if subject_id:
        return str(subject_id)
    if student_profile.get("subject_id"):
        return str(student_profile["subject_id"])
    student = registry.get_student(student_id)
    active_subjects = student.get("active_subjects") or student.get("default_subjects") or []
    if len(active_subjects) > 1:
        raise ValueError("subject_id is required for subject-scoped prompt generation")
    return str(active_subjects[0] if active_subjects else registry.get_default_subject_for_student(student_id))


def _prompt_profile_snapshot(student_profile: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(student_profile)
    return snapshot
