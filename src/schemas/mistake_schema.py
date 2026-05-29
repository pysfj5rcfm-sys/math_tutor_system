from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.rule_registry import load_rule_registry

_REGISTRY = load_rule_registry()

QUESTION_TYPES = _REGISTRY.get_question_type_codes()
KNOWLEDGE_POINTS = _REGISTRY.get_knowledge_point_codes()
DIFFICULTIES = _REGISTRY.get_difficulty_codes()

DEFAULT_TENANT_ID = "personal"
DEFAULT_STUDENT_ID = "daughter_grade5"
DEFAULT_CREATED_BY_USER_ID = "parent"


@dataclass
class ValidationReport:
    valid: bool = True
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    imported_count: int = 0
    skipped_count: int = 0

    def add_error(self, code: str, message: str, index: int | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if index is not None:
            item["index"] = index
        self.errors.append(item)
        self.valid = False

    def add_warning(self, code: str, message: str, index: int | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if index is not None:
            item["index"] = index
        self.warnings.append(item)

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
        }


MISTAKES_SCHEMA_EXAMPLE = {
    "mistakes": [
        {
            "date": "YYYY-MM-DD",
            "question_type": "递等式计算",
            "knowledge_point": "小数计算",
            "mistake_tag": "C3",
            "difficulty": "基础",
            "question_summary": "题目摘要",
            "wrong_answer_summary": "错误答案摘要",
            "correct_answer_summary": "正确答案摘要",
            "training_needed": True,
            "source": "GPT批改",
            "note": "备注",
        }
    ]
}
