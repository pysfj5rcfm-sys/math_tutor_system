from __future__ import annotations

from typing import Any

from src.core.rule_registry import RuleRegistry, RuleRegistryError, load_rule_registry

CANONICAL_DISPLAY_LABELS = {
    "math_g6a_rational_add_different_sign": "有理数异号相加",
    "math_g6a_number_line_representation": "数轴表示",
    "math_g6a_rational_subtract_as_add_opposite": "减法转化为加相反数",
    "math_g6a_percentage_word_problem_model": "百分数应用模型",
    "math_g6a_one_step_equation_solving": "一元一次方程一步求解",
    "math_g6a_unit_conversion_measurement": "计量单位与换算",
    "chinese_g6_text_evidence": "\u6587\u672c\u8bc1\u636e",
    "english_g6_reading_detail": "\u9605\u8bfb\u7ec6\u8282\u5b9a\u4f4d",
    "chinese_reading": "\u9605\u8bfb\u7406\u89e3",
    "english_reading": "\u9605\u8bfb\u7406\u89e3",
    "MATH_SIGN_RULE_ERROR": "符号规则错误",
    "MATH_QUANTITATIVE_RELATION_ERROR": "数量关系提取错误",
    "MATH_EQUALITY_RELATION_ERROR": "等量关系理解错误",
    "MATH_REPRESENTATION_TRANSFER_ERROR": "表征转化错误",
    "MATH_UNIT_CONVERSION_ERROR": "单位换算错误",
    "CHN_EVD_1": "\u6587\u672c\u8bc1\u636e\u4e0d\u8db3",
    "ENG_GRAM_1": "\u65f6\u6001\u9519\u8bef",
    "basic": "\u57fa\u7840",
    "medium": "\u4e2d\u7b49",
    "advanced": "\u63d0\u9ad8",
    "challenge": "\u6311\u6218",
}


def question_type_display(value: Any, registry: RuleRegistry | None = None) -> str:
    code = _text(value)
    if not code:
        return ""
    registry = registry or load_rule_registry()
    for item in registry.get_question_types(active_only=False):
        accepted = {str(v) for v in [item.get("code"), item.get("name"), item.get("display_name")] if v}
        if code in accepted:
            canonical_code = str(item.get("code") or code)
            return _format(_label(canonical_code, item.get("name") or item.get("display_name")), canonical_code)
    return _unknown(code)


def knowledge_point_display(
    value: Any,
    subject_id: Any,
    grade_at_time: Any,
    curriculum_version_at_time: Any = "cn_k12_2022",
    registry: RuleRegistry | None = None,
) -> str:
    point_id = _text(value)
    if not point_id:
        return ""
    registry = registry or load_rule_registry()
    try:
        points = registry.get_knowledge_points_for_context(
            _text(subject_id),
            int(grade_at_time),
            _text(curriculum_version_at_time) or "cn_k12_2022",
        )
    except (RuleRegistryError, ValueError, TypeError):
        points = []
    for item in points:
        accepted = {str(v) for v in [item.get("knowledge_point_id"), item.get("name"), *(item.get("aliases") or [])] if v}
        if point_id in accepted:
            canonical_id = str(item.get("knowledge_point_id") or point_id)
            return _format(_label(canonical_id, item.get("name")), canonical_id)
    for item in registry.get_curriculum_knowledge_points():
        accepted = {str(v) for v in [item.get("knowledge_point_id"), item.get("name"), *(item.get("aliases") or [])] if v}
        if point_id in accepted:
            canonical_id = str(item.get("knowledge_point_id") or point_id)
            return _format(_label(canonical_id, item.get("name")), canonical_id)
    return _unknown(point_id)


def mistake_tag_display(value: Any, registry: RuleRegistry | None = None) -> str:
    code = _text(value)
    if not code:
        return ""
    registry = registry or load_rule_registry()
    for item in registry.get_mistake_tags(active_only=False):
        if item.get("code") == code:
            return _format(_label(code, item.get("name")), code)
    return _unknown(code)


def difficulty_display(value: Any, registry: RuleRegistry | None = None) -> str:
    code = _text(value)
    if not code:
        return ""
    registry = registry or load_rule_registry()
    for item in registry.get_difficulty_levels(active_only=False):
        if item.get("code") == code:
            return _format(_label(code, item.get("name")), code)
    return _unknown(code)


def enrich_mistake_display_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry = load_rule_registry()
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["question_type_display"] = question_type_display(item.get("question_type_code"), registry)
        item["knowledge_point_display"] = knowledge_point_display(
            item.get("knowledge_point_id"),
            item.get("subject_id"),
            item.get("grade_at_time"),
            item.get("curriculum_version_at_time"),
            registry,
        )
        item["mistake_tag_display"] = mistake_tag_display(item.get("primary_mistake_tag_code"), registry)
        item["difficulty_display"] = difficulty_display(item.get("difficulty_code"), registry)
        enriched.append(item)
    return enriched


def _format(name: Any, code: str) -> str:
    label = _text(name) or code
    return f"{label} ({code})" if label != code else code


def _unknown(code: str) -> str:
    return f"Unknown({code})"


def _label(code: str, fallback: Any) -> str:
    return CANONICAL_DISPLAY_LABELS.get(code) or _text(fallback) or code


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
