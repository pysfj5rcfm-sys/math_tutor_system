from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.mistake_tags import tags_as_dicts
from src.core.rule_registry import load_rule_registry
from src.schemas.worksheet_schema import WORKSHEET_SCHEMA_EXAMPLE


ROOT = Path(__file__).resolve().parents[2]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())


def build_worksheet_prompt(
    student_profile: dict[str, Any],
    stats: dict[str, Any],
    mistake_tags: list[dict[str, Any]] | None = None,
) -> str:
    registry = load_rule_registry()
    template = _env().get_template("gpt_worksheet_prompt.md.j2")
    constraints = student_profile.get("default_training_constraints", {})
    return template.render(
        student_profile_yaml=yaml.safe_dump(student_profile, allow_unicode=True, sort_keys=False),
        mistake_tags_yaml=yaml.safe_dump(mistake_tags or tags_as_dicts(), allow_unicode=True, sort_keys=False),
        stats_7_yaml=yaml.safe_dump(stats.get("recent_7_days", []), allow_unicode=True, sort_keys=False),
        stats_30_yaml=yaml.safe_dump(stats.get("recent_30_days", []), allow_unicode=True, sort_keys=False),
        by_type_yaml=yaml.safe_dump(stats.get("mistake_tag_by_question_type", []), allow_unicode=True, sort_keys=False),
        by_knowledge_yaml=yaml.safe_dump(stats.get("mistake_tag_by_knowledge_point", []), allow_unicode=True, sort_keys=False),
        constraints_yaml=yaml.safe_dump(constraints, allow_unicode=True, sort_keys=False),
        question_types_yaml=registry.render_question_types_for_prompt(),
        knowledge_points_yaml=registry.render_knowledge_points_for_prompt(),
        mistake_tag_codes_yaml=yaml.safe_dump(registry.get_mistake_tag_codes(), allow_unicode=True, sort_keys=False),
        difficulties_yaml=registry.render_difficulty_levels_for_prompt(),
        alias_mappings_yaml=registry.render_alias_mappings_for_prompt(),
        worksheet_policies_yaml=registry.render_worksheet_policies_for_prompt(),
        worksheet_schema_yaml=yaml.safe_dump(WORKSHEET_SCHEMA_EXAMPLE, allow_unicode=True, sort_keys=False),
    )


def save_worksheet_prompt(prompt: str, output_dir: str | Path = ROOT / "outputs" / "prompts") -> Path:
    path = Path(output_dir) / "gpt_worksheet_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path
