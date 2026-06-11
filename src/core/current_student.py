from __future__ import annotations

from typing import Any


DEFAULT_FALLBACK_STUDENT_ID = "daughter"
SESSION_STATE_KEY = "current_student_id"

_runtime_current_student_id: str | None = None


def get_current_student_id(
    task_scope: dict[str, Any] | None = None,
    registry: Any | None = None,
) -> str:
    """Resolve the runtime current student id from one canonical path."""
    if task_scope and task_scope.get("student_id"):
        return str(task_scope["student_id"])

    session_value = _read_streamlit_session_student_id()
    if session_value:
        return session_value

    if _runtime_current_student_id:
        return _runtime_current_student_id

    registry = registry or _load_registry()
    active = _first_active_real_student(registry)
    if active:
        return str(active["student_id"])
    return DEFAULT_FALLBACK_STUDENT_ID


def resolve_current_student(
    task_scope: dict[str, Any] | None = None,
    registry: Any | None = None,
) -> dict[str, Any]:
    registry = registry or _load_registry()
    student_id = get_current_student_id(task_scope=task_scope, registry=registry)
    return dict(registry.get_student(student_id))


def set_current_student(
    student_id: str,
    *,
    allow_uat: bool = False,
    registry: Any | None = None,
) -> dict[str, Any]:
    registry = registry or _load_registry(force_reload=True)
    student = dict(registry.get_student(str(student_id)))
    if is_uat_student(student) and not allow_uat:
        raise ValueError(f"Cannot set UAT student as current student by default: {student_id}")

    global _runtime_current_student_id
    _runtime_current_student_id = str(student["student_id"])
    _write_streamlit_session_student_id(_runtime_current_student_id)
    return student


def clear_current_student() -> None:
    global _runtime_current_student_id
    _runtime_current_student_id = None
    session = _get_streamlit_session_state()
    if session is not None and SESSION_STATE_KEY in session:
        del session[SESSION_STATE_KEY]


def list_selectable_students(
    *,
    show_uat_students: bool = False,
    registry: Any | None = None,
) -> list[dict[str, Any]]:
    registry = registry or _load_registry()
    students = [dict(student) for student in registry.get_students(active_only=False)]
    if show_uat_students:
        return students
    return [student for student in students if not is_uat_student(student)]


def is_uat_student(student: dict[str, Any]) -> bool:
    student_type = str(student.get("student_type") or "").lower()
    student_id = str(student.get("student_id") or "")
    display_name = str(student.get("display_name") or "")
    return (
        student.get("is_uat") is True
        or student_type == "uat"
        or student_id.startswith("uat_")
        or display_name.upper().startswith("UAT ")
    )


def resolve_task_scope(
    task_scope: dict[str, Any] | None = None,
    *,
    subject_id: str | None = None,
    registry: Any | None = None,
) -> dict[str, Any]:
    registry = registry or _load_registry()
    student = resolve_current_student(task_scope=task_scope, registry=registry)
    scope_subject = (
        (task_scope or {}).get("subject_id")
        or subject_id
        or registry.get_default_subject_for_student(str(student["student_id"]))
    )
    context = registry.resolve_learning_context(str(student["student_id"]), str(scope_subject))
    if not task_scope:
        context["task_scope_override"] = False
        return context

    override_fields = {
        "student_id",
        "subject_id",
        "grade_at_time",
        "term_at_time",
        "curriculum_version_at_time",
        "textbook_version_at_time",
    }
    for field in override_fields:
        if task_scope.get(field) not in (None, ""):
            context[field] = task_scope[field]

    if "grade_at_time" in context:
        grade = int(context["grade_at_time"])
        stage = registry.get_stage_for_grade(grade)
        context["grade_at_time"] = grade
        context["stage_id"] = str(stage.get("stage_id", ""))
        context["stage_name"] = str(stage.get("name", ""))
        context["grade_display_name"] = registry.get_grade_display_name(grade)
    context["task_scope_override"] = True
    return context


def _first_active_real_student(registry: Any) -> dict[str, Any] | None:
    for student in registry.get_students(active_only=True):
        if not is_uat_student(student):
            return student
    return None


def _load_registry(force_reload: bool = False) -> Any:
    from src.core.rule_registry import load_rule_registry

    return load_rule_registry(force_reload=force_reload)


def _read_streamlit_session_student_id() -> str | None:
    session = _get_streamlit_session_state()
    if session is None:
        return None
    value = session.get(SESSION_STATE_KEY)
    return str(value) if value else None


def _write_streamlit_session_student_id(student_id: str) -> None:
    session = _get_streamlit_session_state()
    if session is not None:
        session[SESSION_STATE_KEY] = student_id


def _get_streamlit_session_state() -> Any | None:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
    except Exception:
        return None
    try:
        if get_script_run_ctx() is None:
            return None
    except Exception:
        return None
    try:
        import streamlit as st  # type: ignore
    except Exception:
        return None
    try:
        return st.session_state
    except Exception:
        return None
