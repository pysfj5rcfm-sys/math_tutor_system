from __future__ import annotations

from typing import Any

from src.core.rule_registry import RuleRegistry, RuleRegistryError, load_rule_registry


QUESTION_TYPE_LABELS = {
    "multiple_choice": "选择",
    "fill_blank": "填空",
    "judgement": "判断",
    "short_answer": "简答",
    "other": "其它",
    "math_calculation": "递等式计算",
    "math_equation": "方程",
    "math_unit_conversion": "单位换算",
    "math_geometry_calculation": "几何计算",
    "math_geometry_drawing": "几何画图",
    "math_application": "应用题",
    "math_reading": "阅读理解型数学题",
    "math_comprehensive": "综合题",
    "physics_calculation": "物理计算",
    "physics_experiment": "实验探究",
    "physics_graph_analysis": "图像分析",
    "chem_formula_writing": "化学式书写",
    "chem_equation_balancing": "化学方程式配平",
    "chem_experiment": "实验探究",
}

QUESTION_TYPE_ALIASES = {
    "应用题": "math_application",
    "文字题": "math_application",
    "递等式计算": "math_calculation",
    "计算题": "math_calculation",
    "方程": "math_equation",
    "单位换算": "math_unit_conversion",
    "几何计算": "math_geometry_calculation",
    "几何题": "math_geometry_calculation",
    "物理计算": "physics_calculation",
    "化学式书写": "chem_formula_writing",
    "化学方程式配平": "chem_equation_balancing",
}


def question_type_display(value: Any, registry: RuleRegistry | None = None) -> str:
    text = _text(value)
    if not text:
        return ""
    registry = registry or load_rule_registry()
    code = registry.canonicalize_question_type(text) or QUESTION_TYPE_ALIASES.get(text)
    if not code:
        return text
    return f"{_question_type_label(code, registry)} ({code})"


def knowledge_point_display(
    value: Any,
    subject_id: Any,
    grade_at_time: Any,
    curriculum_version_at_time: Any = "cn_k12_2022",
    registry: RuleRegistry | None = None,
) -> str:
    text = _text(value)
    if not text:
        return ""
    registry = registry or load_rule_registry()
    subject = _text(subject_id)
    grade = _text(grade_at_time)
    curriculum_version = _text(curriculum_version_at_time) or "cn_k12_2022"
    if not subject or not grade:
        return text
    try:
        result = registry.validate_knowledge_point_for_context(text, subject, grade, curriculum_version)
    except (RuleRegistryError, ValueError, TypeError):
        return text
    matches = result.get("matches") or []
    if not matches:
        return text
    match = matches[0]
    point_id = _text(match.get("knowledge_point_id"))
    name = _text(match.get("name")) or point_id
    return f"{name} ({point_id})" if point_id and point_id != name else name


def enrich_mistake_display_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry = load_rule_registry()
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["question_type_display"] = question_type_display(item.get("question_type"), registry)
        item["knowledge_point_display"] = knowledge_point_display(
            item.get("knowledge_point"),
            item.get("subject_id"),
            item.get("grade_at_time"),
            item.get("curriculum_version_at_time"),
            registry,
        )
        enriched.append(item)
    return enriched


def _question_type_label(code: str, registry: RuleRegistry) -> str:
    if code in QUESTION_TYPE_LABELS:
        return QUESTION_TYPE_LABELS[code]
    for item in registry.get_question_types(active_only=False):
        if item.get("code") == code:
            return str(item.get("name") or code)
    return code


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
