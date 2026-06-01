from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.rule_registry import load_rule_registry


ROOT = Path(__file__).resolve().parents[2]

MISTAKES_SKELETON = """mistakes:
  - date: "2026-05-27"
    student_id: "daughter"
    subject_id: "math"
    grade_at_time: 6
    term_at_time: "六年级上"
    curriculum_version_at_time: "cn_k12_2022"
    question_type: "应用题"
    knowledge_point: "阅读理解型应用题"
    mistake_tag: "R4"
    difficulty: "中等"
    question_summary: "..."
    wrong_answer_summary: "..."
    correct_answer_summary: "..."
    training_needed: true
    source: "GPT批改"
    note: "..."
"""

WORKSHEET_SKELETON = """worksheet:
  title: "六年级数学专项训练"
  date: "2026-05-27"
  student_id: "daughter"
  subject_id: "math"
  grade_at_time: 6
  term_at_time: "六年级上"
  curriculum_version_at_time: "cn_k12_2022"
  sections:
    - name: "一、递等式计算"
      layout: "two_columns"
      questions:
        - question_type: "递等式计算"
          knowledge_point: "小数计算"
          target_mistake_tag: "C3"
          difficulty: "基础"
          question: "..."
          answer: "..."
          explanation: "..."
"""


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())


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
    return _env().get_template("gpt_validation_repair_prompt.md.j2").render(
        source_type=source_type,
        readable_report_yaml=yaml.safe_dump(validation_report.get("readable_items", []), allow_unicode=True, sort_keys=False),
        raw_validation_yaml=yaml.safe_dump(validation_report.get("raw_validation", {}), allow_unicode=True, sort_keys=False),
        question_types_yaml=registry.render_question_types_for_prompt(),
        knowledge_points_yaml=registry.render_knowledge_points_for_prompt(),
        mistake_tags_yaml=registry.render_mistake_tags_for_prompt(),
        difficulties_yaml=registry.render_difficulty_levels_for_prompt(),
        alias_mappings_yaml=registry.render_alias_mappings_for_prompt(),
        original_text=original_text,
    )


def save_repair_prompt(prompt: str, source_type: str, repair_type: str, output_dir: str | Path = ROOT / "outputs" / "prompts") -> Path:
    path = Path(output_dir) / f"{source_type}_{repair_type}_repair_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path
