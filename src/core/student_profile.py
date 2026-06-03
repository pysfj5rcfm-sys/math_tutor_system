from __future__ import annotations

from typing import Any

from src.core.rule_registry import load_rule_registry


def load_student_profile() -> dict[str, Any]:
    return load_active_student_profile()


def load_active_student_profile() -> dict[str, Any]:
    registry = load_rule_registry()
    return registry.get_active_student()
