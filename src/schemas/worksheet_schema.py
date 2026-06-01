from __future__ import annotations

from src.schemas.mistake_schema import DIFFICULTIES, KNOWLEDGE_POINTS, QUESTION_TYPES

SECTION_LAYOUTS = ["two_columns", "single_column"]

WORKSHEET_SCHEMA_EXAMPLE = {
    "worksheet": {
        "title": "五年级数学专项训练",
        "date": "YYYY-MM-DD",
        "student_id": "daughter",
        "subject_id": "math",
        "grade_at_time": 6,
        "term_at_time": "六年级上",
        "curriculum_version_at_time": "cn_k12_2022",
        "sections": [
            {
                "name": "一、递等式计算",
                "layout": "two_columns",
                "questions": [
                    {
                        "question_type": "递等式计算",
                        "knowledge_point": "小数计算",
                        "target_mistake_tag": "C3",
                        "difficulty": "基础",
                        "question": "题目",
                        "answer": "答案",
                        "explanation": "解析",
                        "requires_diagram": False,
                        "diagram_json": None,
                    }
                ],
            }
        ],
    }
}

__all__ = [
    "QUESTION_TYPES",
    "KNOWLEDGE_POINTS",
    "DIFFICULTIES",
    "SECTION_LAYOUTS",
    "WORKSHEET_SCHEMA_EXAMPLE",
]
