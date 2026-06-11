from __future__ import annotations

from typing import Any

from src.core.current_student import get_current_student_id
from src.core.rule_registry import RuleRegistry, RuleRegistryError, load_rule_registry

QUESTION_ROLES = {"repair", "variant", "transfer", "mixed_review"}


def resolve_context(
    payload: dict[str, Any],
    row: dict[str, Any],
    registry: RuleRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or load_rule_registry()
    student_id = row.get("student_id") or payload.get("student_id") or get_current_student_id(registry=registry)
    subject_id = row.get("subject_id") or payload.get("subject_id")
    if not subject_id:
        subject_id = _infer_subject_from_ambiguous_fields(payload, row, registry)
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
    _add_current_student_warnings(payload, row, context, registry, warnings, index)

    normalized = _base_row(row, context)
    _normalize_question_type(normalized, row, context, registry, errors, warnings, index)
    _normalize_knowledge_point(normalized, row, context, registry, warnings, index)
    _normalize_mistake_tag(normalized, row, context, registry, errors, warnings, index, "primary_mistake_tag_code")
    _normalize_difficulty(normalized, row, registry, errors, warnings, index)
    _normalize_diagnosis_fields(normalized, row, context, registry, errors, warnings, index)

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
    _add_current_student_warnings(payload, worksheet, context, registry, warnings, None)

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
            _normalize_mistake_tag(item, question, context, registry, item_errors, warnings, item_index, "target_mistake_tag_code")
            _normalize_difficulty(item, question, registry, item_errors, warnings, item_index)
            _normalize_worksheet_optional_fields(item, question, item_errors, item_index)
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


def _add_current_student_warnings(
    payload: dict[str, Any],
    row: dict[str, Any],
    context: dict[str, Any],
    registry: RuleRegistry,
    warnings: list[dict[str, Any]],
    index: int | None,
) -> None:
    current_student_id = get_current_student_id(registry=registry)
    explicit_student_id = row.get("student_id") or payload.get("student_id")
    if explicit_student_id and str(explicit_student_id) != current_student_id:
        warnings.append(_item(
            "yaml_student_id_differs_from_current_student",
            (
                f"YAML student_id={explicit_student_id} differs from current_student_id={current_student_id}; "
                "preview and confirm will keep the YAML student_id."
            ),
            index,
        ))
    if not explicit_student_id:
        warnings.append(_item(
            "missing_student_id_defaulted_to_current_student",
            f"YAML student_id is missing; defaulted to current_student_id={context['student_id']}.",
            index,
        ))


def _normalize_question_type(
    target: dict[str, Any],
    source: dict[str, Any],
    context: dict[str, Any],
    registry: RuleRegistry,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    index: int | None,
) -> None:
    raw = source.get("question_type_code")
    code, ambiguous = _match_question_type(raw, context["subject_id"], registry)
    if ambiguous:
        errors.append(_item("ambiguous_question_type_alias", "question_type alias is ambiguous without a matching subject scope; use subject_id or canonical question_type_code", index))
    elif not code:
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
    raw = source.get("knowledge_point_id")
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
        alias_result = registry.resolve_alias("knowledge_point_aliases", text, context["subject_id"])
        if alias_result.ambiguous:
            target["knowledge_point_id"] = None
            warnings.append(_item("ambiguous_knowledge_point", "knowledge_point alias is ambiguous; use canonical knowledge_point_id", index))
            return
        alias = alias_result.target
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
) -> None:
    raw = source.get(target_field)
    code, ambiguous = _match_mistake_tag(raw, context["subject_id"], registry)
    if ambiguous:
        errors.append(_item("ambiguous_mistake_tag_alias", f"{target_field} alias is ambiguous; use canonical code", index))
    elif not code:
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
    raw = source.get("difficulty_code")
    code = registry.suggest_difficulty(raw)
    if not code or code not in registry.get_difficulty_codes():
        errors.append(_item("invalid_difficulty", "difficulty_code is not supported", index))
    else:
        target["difficulty_code"] = code


def _normalize_diagnosis_fields(
    target: dict[str, Any],
    source: dict[str, Any],
    context: dict[str, Any],
    registry: RuleRegistry,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    index: int | None,
) -> None:
    confidence = _optional_number(source.get("diagnosis_confidence"), "diagnosis_confidence", errors, index)
    if confidence is not None:
        target["diagnosis_confidence"] = confidence

    review = _optional_bool(source.get("needs_human_review"), "needs_human_review", errors, index)
    if review is not None:
        target["needs_human_review"] = review

    secondary = source.get("secondary_mistake_tags")
    if secondary not in (None, ""):
        if not isinstance(secondary, list):
            errors.append(_item("invalid_secondary_mistake_tags", "secondary_mistake_tags must be a list", index))
        elif len(secondary) > 3:
            errors.append(_item("too_many_secondary_mistake_tags", "secondary_mistake_tags supports at most 3 items", index))
        else:
            normalized_tags: list[str] = []
            for raw in secondary:
                code, ambiguous = _match_mistake_tag(raw, context["subject_id"], registry)
                if ambiguous or not code:
                    errors.append(_item("invalid_secondary_mistake_tag", "secondary_mistake_tags must use current allowed mistake tags", index))
                    continue
                normalized_tags.append(code)
            target["secondary_mistake_tags"] = normalized_tags

    evidence = source.get("diagnosis_evidence")
    if evidence not in (None, ""):
        if not isinstance(evidence, dict):
            errors.append(_item("invalid_diagnosis_evidence", "diagnosis_evidence must be a mapping", index))
        else:
            target["diagnosis_evidence"] = evidence

    alternatives = source.get("alternative_diagnoses")
    if alternatives not in (None, ""):
        if not isinstance(alternatives, list):
            errors.append(_item("invalid_alternative_diagnoses", "alternative_diagnoses must be a list", index))
        else:
            normalized_alternatives: list[dict[str, Any]] = []
            for item in alternatives:
                if not isinstance(item, dict):
                    errors.append(_item("invalid_alternative_diagnosis", "each alternative_diagnoses item must be a mapping", index))
                    continue
                code, ambiguous = _match_mistake_tag(item.get("code"), context["subject_id"], registry)
                if ambiguous or not code:
                    errors.append(_item("invalid_alternative_diagnosis_code", "alternative_diagnoses.code must use current allowed mistake tags", index))
                    continue
                alt_confidence = _optional_number(item.get("confidence"), "alternative_diagnoses.confidence", errors, index)
                normalized = dict(item)
                normalized["code"] = code
                if alt_confidence is not None:
                    normalized["confidence"] = alt_confidence
                normalized_alternatives.append(normalized)
            target["alternative_diagnoses"] = normalized_alternatives


def _normalize_worksheet_optional_fields(
    target: dict[str, Any],
    source: dict[str, Any],
    errors: list[dict[str, Any]],
    index: int | None,
) -> None:
    for field in ("primary_target_id", "teaching_purpose", "expected_error_mechanism"):
        value = source.get(field)
        if value in (None, ""):
            target[field] = ""
        elif isinstance(value, str):
            target[field] = value
        else:
            errors.append(_item(f"invalid_{field}", f"{field} must be a string", index))

    role = source.get("question_role")
    if role in (None, ""):
        target["question_role"] = ""
    elif str(role) in QUESTION_ROLES:
        target["question_role"] = str(role)
    else:
        errors.append(_item("invalid_question_role", "question_role must be repair, variant, transfer, or mixed_review", index))


def _optional_number(
    value: Any,
    field_name: str,
    errors: list[dict[str, Any]],
    index: int | None,
) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        errors.append(_item(f"invalid_{field_name}", f"{field_name} must be a number from 0.0 to 1.0", index))
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(_item(f"invalid_{field_name}", f"{field_name} must be a number from 0.0 to 1.0", index))
        return None
    if number < 0.0 or number > 1.0:
        errors.append(_item(f"{field_name}_out_of_range", f"{field_name} must be between 0.0 and 1.0", index))
        return None
    return number


def _optional_bool(
    value: Any,
    field_name: str,
    errors: list[dict[str, Any]],
    index: int | None,
) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    errors.append(_item(f"invalid_{field_name}", f"{field_name} must be boolean", index))
    return None


def _match_question_type(value: Any, subject_id: str, registry: RuleRegistry) -> tuple[str | None, bool]:
    if value in (None, ""):
        return None, False
    text = str(value).strip()
    alias_result = registry.resolve_alias("question_type_aliases", text, subject_id)
    if alias_result.ambiguous:
        return None, True
    alias = alias_result.target
    candidates = [text, alias] if alias else [text]
    for item in registry.get_question_types_for_subject(subject_id):
        accepted = {str(v) for v in [item.get("code"), item.get("name"), item.get("display_name")] if v}
        if any(candidate in accepted for candidate in candidates if candidate):
            return str(item["code"]), False
    return None, False


def _match_mistake_tag(value: Any, subject_id: str, registry: RuleRegistry) -> tuple[str | None, bool]:
    if value in (None, ""):
        return None, False
    text = str(value).strip()
    alias_result = registry.resolve_alias("mistake_tag_aliases", text, subject_id)
    if alias_result.ambiguous:
        return None, True
    alias = alias_result.target
    candidates = [text, alias] if alias else [text]
    for item in registry.get_mistake_tags_for_subject(subject_id):
        accepted = {str(v) for v in [item.get("code"), item.get("name")] if v}
        if any(candidate in accepted for candidate in candidates if candidate):
            return str(item["code"]), False
    return None, False


def _infer_subject_from_ambiguous_fields(payload: dict[str, Any], row: dict[str, Any], registry: RuleRegistry) -> str | None:
    for alias_key, fields in (
        ("question_type_aliases", ("question_type_code",)),
        ("knowledge_point_aliases", ("knowledge_point_id",)),
        ("mistake_tag_aliases", ("primary_mistake_tag_code", "target_mistake_tag_code")),
    ):
        for source in (payload, row):
            for field in fields:
                if source.get(field):
                    result = registry.resolve_alias(alias_key, source.get(field), None)
                    if result.ambiguous:
                        raise RuleRegistryError(f"Ambiguous alias without subject_id: {source.get(field)}")
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
