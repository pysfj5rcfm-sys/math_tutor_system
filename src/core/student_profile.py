from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.core.rule_registry import load_rule_registry


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE_PATH = ROOT / "config" / "student_profile.yaml"


def load_student_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    required = ["student_id", "display_name", "grade"]
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ValueError(f"student_profile missing required fields: {', '.join(missing)}")
    return data


def load_active_student_profile() -> dict[str, Any]:
    """Load the v0.1.5 active student while keeping load_student_profile legacy-safe."""
    registry = load_rule_registry()
    return registry.get_active_student()
