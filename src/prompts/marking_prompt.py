from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.mistake_tags import tags_as_dicts
from src.schemas.mistake_schema import MISTAKES_SCHEMA_EXAMPLE


ROOT = Path(__file__).resolve().parents[2]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())


def build_marking_prompt(student_profile: dict[str, Any], mistake_tags: list[dict[str, Any]] | None = None) -> str:
    template = _env().get_template("gpt_marking_prompt.md.j2")
    return template.render(
        student_profile_yaml=yaml.safe_dump(student_profile, allow_unicode=True, sort_keys=False),
        mistake_tags_yaml=yaml.safe_dump(mistake_tags or tags_as_dicts(), allow_unicode=True, sort_keys=False),
        mistake_schema_yaml=yaml.safe_dump(MISTAKES_SCHEMA_EXAMPLE, allow_unicode=True, sort_keys=False),
    )


def save_marking_prompt(prompt: str, output_dir: str | Path = ROOT / "outputs" / "prompts") -> Path:
    path = Path(output_dir) / "gpt_marking_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path
