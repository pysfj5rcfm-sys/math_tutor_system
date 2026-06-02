from __future__ import annotations

from typing import Any

from src.core.rule_registry import RuleRegistry, RuleRegistryError, load_rule_registry


LEGACY_MISTAKE_FIELDS = {"question_type", "knowledge_point", "mistake_tag", "difficulty"}
LEGACY_WORKSHEET_FIELDS = {"question_type", "knowledge_point", "target_mistake_tag", "difficulty"}


def resolve_context(
    payload: dict[str, Any],
    row: dict[str, Any],
    registry: RuleRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or load_rule_registry()
    student_id = row.get("student_id") or payload.get("student_id")
    subject_id = row.get("subject_id") or payload.get("subject_id")
    context = registry.resolve_learning_context(student_id=student_id, subject_id=subject_id)
    for source in (payload, row):
        if source.get("student_id"):
            context["student_id"] = str(source["student_id"])
        if source.get("subject_id"):
            context["subject_id"] = str(source["subject_id"])
        if source.get("grade_at_time"):
            grade = int(source["grade_at_time"])
            context["grade_at_time"] = grade
            context["grade_display_name"] = registry.get_grade_display_name(grade)
            stage = registry.get_stage_for_grade(grade)
            context["stage_id"] = str(stage.get("stage_id", ""))
            context["stage_name"] = str(stage.get("name", ""))
        if source.get("term_at_time"):
            context["term_at_time"] = str(source["term_at_time"])
        if source.get("curriculum_version_at_time"):
            context["curriculum_version_at_time"] = str(source["curriculum_version_at_time"])
        if source.get("textbook_version_at_time"):
            context["textbook_version_at_time"] = str(source["textbook_version_at_time"])
    context.setdefault("textbook_version_at_time", context.get("textbook_version_at_time") or "generic")
    return context


def normalize_mistake_row(
    row: dict[str, Any],
    payload: dict[str, Any],
    index: int | None = None,
    registry: RuleRegistry | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    registry = registry or load_rule_registry()
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    try:
        context = resolve_context(payload, row, registry)
    except (RuleRegistryError, ValueError, TypeError) as exc:
        return None, [_item("invalid_learning_context", str(exc), index)], warnings

    normalized = _base_row(row, context)
    _normalize_question_type(normalized, row, context, registry, errors, warnings, index)
    _normalize_knowledge_point(normalized, row, context, registry, warnings, index)
    _normalize_mistake_tag(normalized, row, context, registry, errors, warnings, index, "primary_mistake_tag_code", "mistake_tag")
    _normalize_difficulty(normalized, row, registry, errors, warnings, index)

    if not normalized.get("date"):
        errors.append(_item("missing_date", "date is required", index))
    if not normalized.get("question_summary"):
        errors.append(_item("empty_question_summary", "question_summary must not be empty", index))
    if errors:
        return None, errors, warnings
    return normalized, errors, warnings


def normalize_worksheet_payload(
    payload: dict[str, Any],
    registry: RuleRegistry | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    registry = registry or load_rule_registry()
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    worksheet = payload.get("worksheet")
    if not isinstance(worksheet, dict):
        return None, [_item("invalid_worksheet_root", "worksheet must be a mapping")], warnings
    try:
        context = resolve_context(payload, worksheet, registry)
    except (RuleRegistryError, ValueError, TypeError) as exc:
        return None, [_item("invalid_learning_context", str(exc))], warnings

    normalized = _base_row(worksheet, context)
    normalized["title"] = worksheet.get("title", "")
    normalized["source"] = worksheet.get("source", "")
    if not normalized.get("title"):
        errors.append(_item("missing_title", "worksheet.title is required"))
    if not normalized.get("date"):
        errors.append(_item("missing_date", "worksheet.date is required"))

    sections = worksheet.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append(_item("invalid_sections", "worksheet.sections must be a non-empty list"))
        return None, errors, warnings

    normalized_sections: list[dict[str, Any]] = []
    for section_idx, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(_item("invalid_section", "section must be a mapping", section_idx))
            continue
        layout = section.get("layout")
        if layout not in {"two_columns", "single_column"}:
            errors.append(_item("invalid_section_layout", "section.layout must be two_columns or single_column", section_idx))
            continue
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            errors.append(_item("invalid_questions", "section.questions must be a non-empty list", section_idx))
            continue
        normalized_questions: list[dict[str, Any]] = []
        for q_idx, question in enumerate(questions):
            item_index = section_idx * 1000 + q_idx
            if not isinstance(question, dict):
                errors.append(_item("invalid_question", "question must be a mapping", item_index))
                continue
            item = {
                "question_no": str(question.get("question_no") or q_idx + 1),
                "question": question.get("question", ""),
                "answer": question.get("answer", ""),
                "explanation": question.get("explanation", ""),
            }
            item_errors: list[dict[str, Any]] = []
            _normalize_question_type(item, question, context, registry, item_errors, warnings, item_index)
            _normalize_knowledge_point(item, question, context, registry, warnings, item_index)
            _normalize_mistake_tag(item, question, context, registry, item_errors, warnings, item_index, "target_mistake_tag_code", "target_mistake_tag")
            _normalize_difficulty(item, question, registry, item_errors, warnings, item_index)
            if not item.get("question"):
                item_errors.append(_item("empty_question", "question must not be empty", item_index))
            if not item.get("answer"):
                item_errors.append(_item("missing_answer", "answer is required", item_index))
            if item_errors:
                errors.extend(item_errors)
                continue
            normalized_questions.append(item)
        if normalized_questions:
            normalized_sections.append({
                "name": section.get("name", ""),
                "layout": layout,
                "questions": normalized_questions,
            })
    if errors:
        return None, errors, warnings
    return {**normalized, "sections": normalized_sections}, errors, warnings


def _base_row(row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "student_id": context["student_id"],
        "subject_id": context["subject_id"],
        "grade_at_time": int(context["grade_at_time"]),
        "term_at_time": context.get("term_at_time", ""),
        "curriculum_version_at_time": context.get("curriculum_version_at_time", "cn_k12_2022"),
        "textbook_version_at_time": context.get("textbook_version_at_time", "generic"),
        "date": row.get("date", ""),
        "question_summary": row.get("question_summary", ""),
        "wrong_answer_summary": row.get("wrong_answer_summary", ""),
        "correct_answer_summary": row.get("correct_answer_summary", ""),
        "training_needed": row.get("training_needed", True),
        "source": row.get("source", ""),
    }


def _normalize_question_type(
    target: dict[str, Any],
    source: dict[str, Any],
    context: dict[str, Any],
    registry: RuleRegistry,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    index: int | None,
) -> None:
    raw = source.get("question_type_code") or source.get("question_type")
    code = _match_question_type(raw, context["subject_id"], registry)
    if not code:
        errors.append(_item("invalid_question_type", "question_type_code is not supported in current subject scope", index))
    else:
        target["question_type_code"] = code


def _normalize_knowledge_point(
    target: dict[str, Any],
    source: dict[str, Any],
    context: dict[str, Any],
    registry: RuleRegistry,
    warnings: list[dict[str, Any]],
    index: int | None,
) -> None:
    raw = source.get("knowledge_point_id") or source.get("knowledge_point")
    if raw in (None, ""):
        target["knowledge_point_id"] = None
        return
    text = str(raw).strip()
    try:
        points = registry.get_knowledge_points_for_context(
            context["subject_id"],
            context["grade_at_time"],
            context["curriculum_version_at_time"],
        )
    except RuleRegistryError:
        points = []
    matches = [
        item for item in points
        if text in _accepted_knowledge_point_values(item)
    ]
    if not matches:
        alias = registry.suggest_knowledge_point(text)
        if alias:
            matches = [item for item in points if alias in _accepted_knowledge_point_values(item)]
    unique = _unique_by(matches, "knowledge_point_id")
    if len(unique) == 1:
        point_id = str(unique[0]["knowledge_point_id"])
        target["knowledge_point_id"] = point_id
        return
    target["knowledge_point_id"] = None
    if len(unique) > 1:
        warnings.append(_item("ambiguous_knowledge_point", "knowledge_point matches multiple items in current scope; use knowledge_point_id", index))
    else:
        warnings.append(_item("unknown_knowledge_point", "knowledge_point is unknown in current scope; canonical id was left empty", index))


def _normalize_mistake_tag(
    target: dict[str, Any],
    source: dict[str, Any],
    context: dict[str, Any],
    registry: RuleRegistry,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    index: int | None,
    target_field: str,
    legacy_field: str,
) -> None:
    raw = source.get(target_field) or source.get(legacy_field)
    code = _match_mistake_tag(raw, context["subject_id"], registry)
    if not code:
        errors.append(_item("invalid_mistake_tag", f"{target_field} must be valid for the current subject", index))
    else:
        target[target_field] = code


def _normalize_difficulty(
    target: dict[str, Any],
    source: dict[str, Any],
    registry: RuleRegistry,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    index: int | None,
) -> None:
    raw = source.get("difficulty_code") or source.get("difficulty")
    code = registry.suggest_difficulty(raw)
    if not code or code not in registry.get_difficulty_codes():
        errors.append(_item("invalid_difficulty", "difficulty_code is not supported", index))
    else:
        target["difficulty_code"] = code


def _match_question_type(value: Any, subject_id: str, registry: RuleRegistry) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    alias = registry.suggest_question_type(text)
    candidates = [text, alias] if alias else [text]
    for item in registry.get_question_types_for_subject(subject_id):
        accepted = {str(v) for v in [item.get("code"), item.get("name"), item.get("display_name"), *(item.get("legacy_names") or [])] if v}
        if any(candidate in accepted for candidate in candidates if candidate):
            return str(item["code"])
    return None


def _match_mistake_tag(value: Any, subject_id: str, registry: RuleRegistry) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    alias = registry.suggest_mistake_tag(text)
    candidates = [text, alias] if alias else [text]
    for item in registry.get_mistake_tags_for_subject(subject_id):
        accepted = {str(v) for v in [item.get("code"), item.get("name")] if v}
        if any(candidate in accepted for candidate in candidates if candidate):
            return str(item["code"])
    return None


def _accepted_knowledge_point_values(item: dict[str, Any]) -> set[str]:
    values = [item.get("knowledge_point_id"), item.get("name"), *(item.get("aliases") or [])]
    return {str(value).strip() for value in values if value not in (None, "")}


def _unique_by(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        value = str(item.get(key, ""))
        if value and value not in seen:
            seen.add(value)
            result.append(item)
    return result


def _item(code: str, message: str, index: int | None = None) -> dict[str, Any]:
    item = {"code": code, "message": message}
    if index is not None:
        item["index"] = index
    return item
