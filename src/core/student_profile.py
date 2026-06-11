from __future__ import annotations

from typing import Any

from src.core.current_student import resolve_current_student


def load_student_profile() -> dict[str, Any]:
    return load_active_student_profile()


def load_active_student_profile() -> dict[str, Any]:
    return resolve_current_student()
