from __future__ import annotations

from typing import Any

from src.core.rule_registry import RuleRegistry, RuleRegistryError, load_rule_registry


def question_type_display(value: Any, registry: RuleRegistry | None = None) -> str:
    code = _text(value)
    if not code:
        return ""
    registry = registry or load_rule_registry()
    for item in registry.get_question_types(active_only=False):
        accepted = {str(v) for v in [item.get("code"), item.get("name"), item.get("display_name"), *(item.get("legacy_names") or [])] if v}
        if code in accepted:
            canonical_code = str(item.get("code") or code)
            return _format(item.get("name") or item.get("display_name") or canonical_code, canonical_code)
    return code


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
        return point_id
    for item in points:
        accepted = {str(v) for v in [item.get("knowledge_point_id"), item.get("name"), *(item.get("aliases") or [])] if v}
        if point_id in accepted:
            canonical_id = str(item.get("knowledge_point_id") or point_id)
            return _format(item.get("name") or canonical_id, canonical_id)
    return point_id


def mistake_tag_display(value: Any, registry: RuleRegistry | None = None) -> str:
    code = _text(value)
    if not code:
        return ""
    registry = registry or load_rule_registry()
    for item in registry.get_mistake_tags(active_only=False):
        if item.get("code") == code:
            return _format(item.get("name") or code, code)
    return code


def difficulty_display(value: Any, registry: RuleRegistry | None = None) -> str:
    code = _text(value)
    if not code:
        return ""
    registry = registry or load_rule_registry()
    for item in registry.get_difficulty_levels(active_only=False):
        if item.get("code") == code:
            return _format(item.get("name") or code, code)
    return code


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
        return_legacy_aliases(item)
        enriched.append(item)
    return enriched


def return_legacy_aliases(item: dict[str, Any]) -> None:
    """Keep in-memory aliases for old helper callers; DB/export schema stays canonical."""
    item.setdefault("question_type", item.get("question_type_code", ""))
    item.setdefault("knowledge_point", item.get("knowledge_point_id", ""))
    item.setdefault("mistake_tag", item.get("primary_mistake_tag_code", ""))
    item.setdefault("difficulty", item.get("difficulty_code", ""))


def _format(name: Any, code: str) -> str:
    label = _text(name) or code
    return f"{label} ({code})" if label != code else code


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
