from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


QUESTION_TYPES = [
    "递等式计算", "方程", "填空", "选择", "判断", "单位换算", "几何计算", "几何画图",
    "应用题", "阅读理解型数学题", "综合题", "其它",
]

KNOWLEDGE_POINTS = [
    "整数四则混合运算", "小数计算", "分数计算", "小数/分数互化", "方程", "单位换算",
    "长方形/正方形面积", "三角形面积", "梯形面积", "平行四边形面积", "组合图形面积",
    "长方体/正方体表面积", "长方体/正方体体积", "平均数", "倍数关系", "分数应用题",
    "行程问题", "工程问题", "线段图", "阅读理解型应用题",
]

DIFFICULTIES = ["基础", "中等", "提高", "浅奥"]

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
