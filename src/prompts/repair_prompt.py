from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.rule_registry import load_rule_registry


ROOT = Path(__file__).resolve().parents[2]

MISTAKES_SKELETON = """mistakes:
  - date: "2026-06-03"
    student_id: "daughter"
    subject_id: "math"
    grade_at_time: 6
    term_at_time: "grade_6_term_1"
    curriculum_version_at_time: "cn_k12_2022"
    textbook_version_at_time: "沪教版"
    question_type_code: "math_application"
    knowledge_point_id: "math_g6a_percentage_word_problem_model"
    primary_mistake_tag_code: "MATH_QUANTITATIVE_RELATION_ERROR"
    difficulty_code: "medium"
    question_summary: "..."
    wrong_answer_summary: "..."
    correct_answer_summary: "..."
    training_needed: true
    source: "GPT marking"
    note: "..."
"""

WORKSHEET_SKELETON = """worksheet:
  title: "Grade 6 math practice"
  date: "2026-06-03"
  student_id: "daughter"
  subject_id: "math"
  grade_at_time: 6
  term_at_time: "grade_6_term_1"
  curriculum_version_at_time: "cn_k12_2022"
  textbook_version_at_time: "沪教版"
  sections:
    - name: "Application modeling"
      layout: "single_column"
      questions:
        - question_type_code: "math_application"
          knowledge_point_id: "math_g6a_percentage_word_problem_model"
          target_mistake_tag_code: "MATH_QUANTITATIVE_RELATION_ERROR"
          difficulty_code: "medium"
          question: "..."
          answer: "..."
          explanation: "..."
"""


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates", encoding="utf-8"), autoescape=select_autoescape())


def build_yaml_parse_repair_prompt(source_type: str, parse_report: dict[str, Any], original_text: str) -> str:
    skeleton = MISTAKES_SKELETON if source_type == "mistakes" else WORKSHEET_SKELETON
    return _env().get_template("gpt_yaml_parse_repair_prompt.md.j2").render(
        source_type=source_type,
        source_type_root=source_type if source_type == "mistakes" else "worksheet",
        report=parse_report,
        skeleton=skeleton,
        original_text=original_text,
    )


def build_validation_repair_prompt(source_type: str, validation_report: dict[str, Any], original_text: str) -> str:
    registry = load_rule_registry()
    context = _extract_repair_context(source_type, original_text)
    subject_id = str(context.get("subject_id") or "")
    return _env().get_template("gpt_validation_repair_prompt.md.j2").render(
        source_type=source_type,
        readable_report_yaml=yaml.safe_dump(validation_report.get("readable_items", []), allow_unicode=True, sort_keys=False),
        raw_validation_yaml=yaml.safe_dump(validation_report.get("raw_validation", {}), allow_unicode=True, sort_keys=False),
        question_types_yaml=_render_repair_question_types(registry, subject_id),
        knowledge_points_yaml=_render_repair_knowledge_points(registry, context),
        mistake_tags_yaml=_render_repair_mistake_tags(registry, subject_id),
        difficulties_yaml=registry.render_difficulty_levels_for_prompt(),
        alias_mappings_yaml=_render_repair_alias_mappings(registry, subject_id),
        original_text=original_text,
    )


def save_repair_prompt(
    prompt: str,
    source_type: str,
    repair_type: str,
    output_dir: str | Path = ROOT / "outputs" / "prompts",
) -> Path:
    path = Path(output_dir) / f"{source_type}_{repair_type}_repair_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path


def _extract_repair_context(source_type: str, original_text: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(original_text) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(payload, dict):
        return {}
    if source_type == "worksheet":
        root = payload.get("worksheet")
        return dict(root) if isinstance(root, dict) else {}
    rows = payload.get("mistakes")
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        context = dict(payload)
        context.update(rows[0])
        return context
    return dict(payload)


def _render_repair_knowledge_points(registry: Any, context: dict[str, Any]) -> str:
    subject_id = context.get("subject_id")
    grade = context.get("grade_at_time") or context.get("grade")
    curriculum_version = context.get("curriculum_version_at_time") or context.get("curriculum_version") or "cn_k12_2022"
    student_id = context.get("student_id")
    term = context.get("term_at_time")
    if not subject_id or not grade:
        payload = {
            "scope_status": "missing_context",
            "message": (
                "Cannot determine subject/grade/curriculum scope. Add subject_id and grade_at_time, "
                "or use the MVP validation report suggested canonical id."
            ),
            "fallback": "not_injected_by_default",
        }
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    try:
        return registry.render_curriculum_scope_for_context(
            str(subject_id),
            int(grade),
            str(curriculum_version),
            student_id=str(student_id or ""),
            term=str(term or ""),
        )
    except Exception as exc:
        payload = {
            "scope_status": "invalid_context",
            "message": "Cannot load the current subject/grade/curriculum scope. Fix context fields first.",
            "detail": str(exc),
            "fallback": "not_injected_by_default",
        }
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _render_repair_question_types(registry: Any, subject_id: str) -> str:
    if not subject_id:
        return yaml.safe_dump(
            {
                "scope_status": "missing_subject_id",
                "message": "subject_id is required before injecting question_type_code options.",
            },
            allow_unicode=True,
            sort_keys=False,
        )
    return registry.render_question_types_for_prompt(subject_id)


def _render_repair_mistake_tags(registry: Any, subject_id: str) -> str:
    if not subject_id:
        return yaml.safe_dump(
            {
                "scope_status": "missing_subject_id",
                "message": "subject_id is required before injecting mistake_tag_code options.",
            },
            allow_unicode=True,
            sort_keys=False,
        )
    return registry.render_mistake_tags_for_prompt(subject_id)


def _render_repair_alias_mappings(registry: Any, subject_id: str) -> str:
    if not subject_id:
        return yaml.safe_dump(
            {
                "scope_status": "missing_subject_id",
                "message": "subject_id is required before injecting subject-scoped alias mappings.",
            },
            allow_unicode=True,
            sort_keys=False,
        )
    return registry.render_alias_mappings_for_prompt(subject_id)
