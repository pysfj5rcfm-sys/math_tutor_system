from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.mistake_tags import tags_as_dicts
from src.core.rule_registry import load_rule_registry
from src.schemas.mistake_schema import MISTAKES_SCHEMA_EXAMPLE


ROOT = Path(__file__).resolve().parents[2]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())


def build_marking_prompt(student_profile: dict[str, Any], mistake_tags: list[dict[str, Any]] | None = None) -> str:
    registry = load_rule_registry()
    template = _env().get_template("gpt_marking_prompt.md.j2")
    return template.render(
        student_profile_yaml=yaml.safe_dump(student_profile, allow_unicode=True, sort_keys=False),
        mistake_tags_yaml=yaml.safe_dump(mistake_tags or tags_as_dicts(), allow_unicode=True, sort_keys=False),
        question_types_yaml=registry.render_question_types_for_prompt(),
        knowledge_points_yaml=registry.render_knowledge_points_for_prompt(),
        difficulties_yaml=registry.render_difficulty_levels_for_prompt(),
        alias_mappings_yaml=registry.render_alias_mappings_for_prompt(),
        mistake_schema_yaml=yaml.safe_dump(MISTAKES_SCHEMA_EXAMPLE, allow_unicode=True, sort_keys=False),
    )


def save_marking_prompt(prompt: str, output_dir: str | Path = ROOT / "outputs" / "prompts") -> Path:
    path = Path(output_dir) / "gpt_marking_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path
