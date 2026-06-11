from __future__ import annotations

from src.schemas.mistake_schema import DIFFICULTIES, KNOWLEDGE_POINTS, QUESTION_TYPES

SECTION_LAYOUTS = ["two_columns", "single_column"]

WORKSHEET_SCHEMA_EXAMPLE = {
    "worksheet": {
        "title": "六年级数学专项训练",
        "date": "YYYY-MM-DD",
        "student_id": "daughter",
        "subject_id": "math",
        "grade_at_time": 6,
        "term_at_time": "六年级上",
        "curriculum_version_at_time": "cn_k12_2022",
        "textbook_version_at_time": "沪教版",
        "sections": [
            {
                "name": "一、应用题建模",
                "layout": "single_column",
                "questions": [
                    {
                        "question_type_code": "math_application",
                        "knowledge_point_id": "math_g6a_percentage_word_problem_model",
                        "target_mistake_tag_code": "MATH_QUANTITATIVE_RELATION_ERROR",
                        "difficulty_code": "medium",
                        "primary_target_id": "math_g6a_percentage_word_problem_model::MATH_QUANTITATIVE_RELATION_ERROR",
                        "question_role": "repair",
                        "teaching_purpose": "直接修复目标错因",
                        "expected_error_mechanism": "暴露或修复目标错因机制",
                        "question": "题目",
                        "answer": "答案",
                        "explanation": "解析",
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
