from __future__ import annotations

from typing import Any

from src.core.display import difficulty_display, knowledge_point_display, mistake_tag_display, question_type_display


def resolve_display(field_name: str, code: Any, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    if field_name == "question_type_code":
        return question_type_display(code)
    if field_name == "knowledge_point_id":
        return knowledge_point_display(
            code,
            context.get("subject_id"),
            context.get("grade_at_time"),
            context.get("curriculum_version_at_time", "cn_k12_2022"),
        )
    if field_name in {"primary_mistake_tag_code", "target_mistake_tag_code"}:
        return mistake_tag_display(code)
    if field_name == "difficulty_code":
        return difficulty_display(code)
    return f"Unknown({code})" if code else ""


def format_code_display(field_name: str, code: Any, context: dict[str, Any] | None = None) -> str:
    return resolve_display(field_name, code, context)


def make_filter_option(field_name: str, code: Any, context: dict[str, Any] | None = None) -> dict[str, str]:
    value = "" if code is None else str(code)
    return {"value": value, "label": resolve_display(field_name, value, context)}


def make_filter_options(field_name: str, codes: list[Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    return [make_filter_option(field_name, code, context) for code in codes]


def format_mistake_row_for_display(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    context = _context(item)
    item["question_type_display"] = resolve_display("question_type_code", item.get("question_type_code"), context)
    item["knowledge_point_display"] = resolve_display("knowledge_point_id", item.get("knowledge_point_id"), context)
    item["mistake_tag_display"] = resolve_display("primary_mistake_tag_code", item.get("primary_mistake_tag_code"), context)
    item["difficulty_display"] = resolve_display("difficulty_code", item.get("difficulty_code"), context)
    return _drop_ambiguous_fields(item)


def format_worksheet_item_row_for_display(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    context = _context(item)
    item["question_type_display"] = resolve_display("question_type_code", item.get("question_type_code"), context)
    item["knowledge_point_display"] = resolve_display("knowledge_point_id", item.get("knowledge_point_id"), context)
    item["mistake_tag_display"] = resolve_display("target_mistake_tag_code", item.get("target_mistake_tag_code"), context)
    item["difficulty_display"] = resolve_display("difficulty_code", item.get("difficulty_code"), context)
    return _drop_ambiguous_fields(item)


def format_duplicate_row_for_display(row: dict[str, Any]) -> dict[str, Any]:
    return format_mistake_row_for_display(row)


def format_export_row(row: dict[str, Any]) -> dict[str, Any]:
    if "target_mistake_tag_code" in row:
        return format_worksheet_item_row_for_display(row)
    return format_mistake_row_for_display(row)


def _context(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject_id": row.get("subject_id"),
        "grade_at_time": row.get("grade_at_time"),
        "curriculum_version_at_time": row.get("curriculum_version_at_time", "cn_k12_2022"),
    }


def _drop_ambiguous_fields(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty", "type", "display", "name"):
        row.pop(key, None)
    return row
