from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = ROOT / "config"
VALID_LAYOUTS = {"two_columns", "single_column"}


class RuleRegistryError(RuntimeError):
    """Raised when rule registry config is missing or invalid."""


@dataclass(frozen=True)
class RuleRegistry:
    question_types: list[dict[str, Any]]
    knowledge_points: list[dict[str, Any]]
    difficulty_levels: list[dict[str, Any]]
    mistake_tags: list[dict[str, Any]]
    alias_mappings: dict[str, dict[str, str]]
    worksheet_policy: dict[str, Any]
    students: list[dict[str, Any]]
    subjects: list[dict[str, Any]]
    stages: list[dict[str, Any]]
    grades: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    expression_capabilities: list[dict[str, Any]]
    curriculum: dict[str, dict[str, Any]]
    config_dir: Path = DEFAULT_CONFIG_DIR

    def get_question_type_codes(self, active_only: bool = True) -> list[str]:
        values: list[str] = []
        for item in self.get_question_types(active_only):
            values.extend(_question_type_accepted_values(item))
        return _unique(values)

    def get_question_type_canonical_codes(self, active_only: bool = True) -> list[str]:
        return [item["code"] for item in self.get_question_types(active_only)]

    def get_knowledge_point_codes(self, active_only: bool = True) -> list[str]:
        values = [item["code"] for item in self.get_knowledge_points(active_only)]
        for item in self._curriculum_knowledge_points():
            values.append(str(item.get("knowledge_point_id", "")))
            values.append(str(item.get("name", "")))
        return _unique([value for value in values if value])

    def get_difficulty_codes(self, active_only: bool = True) -> list[str]:
        return [item["code"] for item in self.get_difficulty_levels(active_only)]

    def get_mistake_tag_codes(self, active_only: bool = True) -> list[str]:
        return [item["code"] for item in self.get_mistake_tags(active_only)]

    def get_question_types(self, active_only: bool = True) -> list[dict[str, Any]]:
        return _filter_active(self.question_types, active_only)

    def get_knowledge_points(self, active_only: bool = True) -> list[dict[str, Any]]:
        return _filter_active(self.knowledge_points, active_only)

    def get_difficulty_levels(self, active_only: bool = True) -> list[dict[str, Any]]:
        return _filter_active(sorted(self.difficulty_levels, key=lambda item: item.get("order", 0)), active_only)

    def get_mistake_tags(self, active_only: bool = True) -> list[dict[str, Any]]:
        return _filter_active(self.mistake_tags, active_only)

    def get_students(self, active_only: bool = False) -> list[dict[str, Any]]:
        return _filter_active(self.students, active_only)

    def get_active_student(self) -> dict[str, Any]:
        active = self.get_students(active_only=True)
        if not active:
            raise RuleRegistryError("No active student configured in config/students/*.yaml")
        return active[0]

    def get_active_student_id(self) -> str:
        return str(self.get_active_student()["student_id"])

    def get_student(self, student_id: str) -> dict[str, Any]:
        for student in self.students:
            if _student_matches(student, student_id):
                return student
        raise RuleRegistryError(f"Unknown student_id: {student_id}")

    def get_subjects(self, active_only: bool = True) -> list[dict[str, Any]]:
        return _filter_active(self.subjects, active_only)

    def get_subject(self, subject_id: str) -> dict[str, Any]:
        for subject in self.subjects:
            if subject.get("subject_id") == subject_id:
                return subject
        raise RuleRegistryError(f"Unknown subject_id: {subject_id}")

    def get_supported_subjects(self) -> list[dict[str, Any]]:
        return [item for item in self.get_subjects(active_only=True) if item.get("supported_now") is True]

    def get_stages(self) -> list[dict[str, Any]]:
        return list(self.stages)

    def get_grades(self) -> list[dict[str, Any]]:
        return sorted(self.grades, key=lambda item: int(item.get("grade", 0)))

    def get_stage_for_grade(self, grade: int | str) -> dict[str, Any]:
        grade_int = int(grade)
        for stage in self.stages:
            if int(stage.get("grade_min", 0)) <= grade_int <= int(stage.get("grade_max", 0)):
                return stage
        raise RuleRegistryError(f"No stage configured for grade: {grade}")

    def get_grade_display_name(self, grade: int | str) -> str:
        grade_int = int(grade)
        for item in self.grades:
            if int(item.get("grade", 0)) == grade_int:
                return str(item.get("display_name", grade_int))
        return str(grade)

    def get_curriculum_versions(self) -> list[str]:
        return sorted({item.get("curriculum_version", "") for item in self.curriculum.values() if item.get("curriculum_version")})

    def get_curriculum_for(
        self,
        subject_id: str,
        grade: int | str,
        curriculum_version: str = "cn_k12_2022",
    ) -> dict[str, Any]:
        key = _curriculum_key(curriculum_version, subject_id, int(grade))
        item = self.curriculum.get(key)
        if item is None:
            raise RuleRegistryError(
                f"Missing curriculum config for curriculum_version={curriculum_version}, "
                f"subject_id={subject_id}, grade={grade}"
            )
        return item

    def get_curriculum_for_student(self, student_id: str, subject_id: str | None = None) -> dict[str, Any]:
        student = self.get_student(student_id)
        subject = subject_id or self.get_default_subject_for_student(student_id)
        return self.get_curriculum_for(subject, int(student["current_grade"]), str(student.get("curriculum_version", "cn_k12_2022")))

    def get_units_for_student(self, student_id: str, subject_id: str | None = None) -> list[dict[str, Any]]:
        return list(self.get_curriculum_for_student(student_id, subject_id).get("units", []))

    def get_knowledge_points_for_student(self, student_id: str, subject_id: str | None = None) -> list[dict[str, Any]]:
        curriculum = self.get_curriculum_for_student(student_id, subject_id)
        return self._knowledge_points_from_curriculum(curriculum)

    def get_knowledge_points_for_subject_grade(self, subject_id: str, grade: int | str) -> list[dict[str, Any]]:
        curriculum = self.get_curriculum_for(subject_id, int(grade))
        return self._knowledge_points_from_curriculum(curriculum)

    def get_knowledge_point_values_for_context(
        self,
        subject_id: str,
        grade: int | str,
        curriculum_version: str = "cn_k12_2022",
    ) -> list[str]:
        values: list[str] = []
        for item in self.get_knowledge_points_for_context(subject_id, grade, curriculum_version):
            values.append(str(item.get("knowledge_point_id", "")))
            values.append(str(item.get("name", "")))
        values.extend(self._legacy_knowledge_point_values_for_subject(subject_id))
        return _unique([value for value in values if value])

    def get_knowledge_points_for_context(
        self,
        subject_id: str,
        grade: int | str,
        curriculum_version: str = "cn_k12_2022",
    ) -> list[dict[str, Any]]:
        curriculum = self.get_curriculum_for(subject_id, int(grade), curriculum_version)
        return self._knowledge_points_from_curriculum(curriculum)

    def validate_knowledge_point_for_context(
        self,
        value: Any,
        subject_id: str,
        grade: int | str,
        curriculum_version: str = "cn_k12_2022",
    ) -> dict[str, Any]:
        if value is None or str(value).strip() == "":
            return {"valid": False, "ambiguous": False, "matches": []}
        text = str(value).strip()
        try:
            scoped_points = self.get_knowledge_points_for_context(subject_id, grade, curriculum_version)
        except RuleRegistryError:
            scoped_points = []
        matches = [
            item
            for item in scoped_points
            if text in {str(item.get("knowledge_point_id", "")), str(item.get("name", ""))}
        ]
        alias = self.suggest_knowledge_point(text)
        if alias and not matches:
            matches.extend([
                item
                for item in scoped_points
                if alias in {str(item.get("knowledge_point_id", "")), str(item.get("name", ""))}
            ])
        legacy_values = set(self._legacy_knowledge_point_values_for_subject(subject_id))
        if not matches and (text in legacy_values or (alias and alias in legacy_values)):
            matches.append({"knowledge_point_id": alias or text, "name": alias or text, "source": "legacy_compatibility"})
        unique_matches = _unique_matches(matches)
        return {
            "valid": bool(unique_matches),
            "ambiguous": len(unique_matches) > 1,
            "matches": unique_matches,
        }

    def get_question_types_for_subject(self, subject_id: str) -> list[dict[str, Any]]:
        return [
            _with_accepted_inputs(item)
            for item in self.get_question_types(active_only=True)
            if _applies_to_subject(item, subject_id, field="subjects")
        ]

    def get_question_type_values_for_subject(self, subject_id: str) -> list[str]:
        values: list[str] = []
        for item in self.get_question_types_for_subject(subject_id):
            values.extend(_question_type_accepted_values(item))
        return _unique(values)

    def canonicalize_question_type(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        for item in self.get_question_types(active_only=False):
            if text in _question_type_accepted_values(item):
                return str(item["code"])
        return None

    def get_mistake_tags_for_subject(self, subject_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self.get_mistake_tags(active_only=True)
            if _applies_to_subject(item, subject_id, field="subjects")
        ]

    def get_skills_for_subject(self, subject_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in _filter_active(self.skills, True)
            if _applies_to_subject(item, subject_id, field="applies_to_subjects")
        ]

    def get_expression_capabilities_for_subject(self, subject_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in _filter_active(self.expression_capabilities, True)
            if _applies_to_subject(item, subject_id, field="subjects")
        ]

    def get_default_subject_for_student(self, student_id: str) -> str:
        student = self.get_student(student_id)
        subjects = student.get("default_subjects") or []
        if not subjects:
            return "math"
        return str(subjects[0])

    def resolve_learning_context(
        self,
        student_id: str | None = None,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        student = self.get_student(student_id) if student_id else self.get_active_student()
        resolved_subject = subject_id or self.get_default_subject_for_student(str(student["student_id"]))
        grade = int(student.get("current_grade"))
        stage = self.get_stage_for_grade(grade)
        return {
            "student_id": str(student_id or student["student_id"]),
            "canonical_student_id": str(student["student_id"]),
            "subject_id": resolved_subject,
            "grade_at_time": grade,
            "term_at_time": str(student.get("current_term", "")),
            "curriculum_version_at_time": str(student.get("curriculum_version", "cn_k12_2022")),
            "textbook_version_at_time": str(student.get("textbook_version", "generic")),
            "stage_id": str(stage.get("stage_id", "")),
            "stage_name": str(stage.get("name", "")),
            "grade_display_name": self.get_grade_display_name(grade),
        }

    def suggest_question_type(self, value: Any) -> str | None:
        return self._suggest("question_type_aliases", value)

    def suggest_knowledge_point(self, value: Any) -> str | None:
        return self._suggest("knowledge_point_aliases", value)

    def suggest_difficulty(self, value: Any) -> str | None:
        text = "" if value is None else str(value).strip()
        if not text:
            return None
        alias = self._suggest("difficulty_aliases", text)
        if alias:
            return alias
        for item in self.get_difficulty_levels(active_only=False):
            accepted = [item.get("code", ""), item.get("name", ""), *(item.get("legacy_names") or [])]
            if text in {str(v) for v in accepted if v}:
                return str(item.get("code"))
        return None

    def suggest_mistake_tag(self, value: Any) -> str | None:
        return self._suggest("mistake_tag_aliases", value)

    def suggest_field_value(self, field: str, value: Any) -> str | None:
        if field == "question_type":
            return self.suggest_question_type(value)
        if field == "knowledge_point":
            return self.suggest_knowledge_point(value)
        if field == "difficulty":
            return self.suggest_difficulty(value)
        if field in {"mistake_tag", "target_mistake_tag"}:
            return self.suggest_mistake_tag(value)
        if field == "layout" and value is not None:
            return {"双列": "two_columns", "单列": "single_column"}.get(str(value).strip())
        return None

    def render_student_profile_for_prompt(self, student_id: str | None = None) -> str:
        student = self.get_student(student_id) if student_id else self.get_active_student()
        context = self.resolve_learning_context(str(student["student_id"]))
        return yaml.safe_dump({"student": student, "resolved_context": context}, allow_unicode=True, sort_keys=False)

    def render_curriculum_scope_for_prompt(self, student_id: str, subject_id: str | None = None) -> str:
        context = self.resolve_learning_context(student_id, subject_id)
        curriculum = self.get_curriculum_for(
            context["subject_id"],
            context["grade_at_time"],
            context["curriculum_version_at_time"],
        )
        scope = {
            "student_id": context["student_id"],
            "subject_id": context["subject_id"],
            "grade": context["grade_at_time"],
            "grade_display_name": context["grade_display_name"],
            "term": context["term_at_time"],
            "stage_id": context["stage_id"],
            "stage_name": context["stage_name"],
            "curriculum_version": context["curriculum_version_at_time"],
            "textbook_version": curriculum.get("textbook_version", "generic"),
            "coverage_note": curriculum.get("coverage_note", ""),
            "units": curriculum.get("units", []),
        }
        return yaml.safe_dump(scope, allow_unicode=True, sort_keys=False)

    def render_question_types_for_prompt(self, subject_id: str | None = None) -> str:
        items = self.get_question_types_for_subject(subject_id) if subject_id else [
            _with_accepted_inputs(item) for item in self.get_question_types()
        ]
        return yaml.safe_dump(items, allow_unicode=True, sort_keys=False)

    def render_knowledge_points_for_prompt(self) -> str:
        return yaml.safe_dump(self.get_knowledge_points(), allow_unicode=True, sort_keys=False)

    def render_difficulty_levels_for_prompt(self) -> str:
        return yaml.safe_dump(self.get_difficulty_levels(), allow_unicode=True, sort_keys=False)

    def render_mistake_tags_for_prompt(self, subject_id: str | None = None) -> str:
        items = self.get_mistake_tags_for_subject(subject_id) if subject_id else self.get_mistake_tags()
        return yaml.safe_dump(items, allow_unicode=True, sort_keys=False)

    def render_expression_capabilities_for_prompt(self, subject_id: str | None = None) -> str:
        items = self.get_expression_capabilities_for_subject(subject_id) if subject_id else _filter_active(self.expression_capabilities, True)
        return yaml.safe_dump(items, allow_unicode=True, sort_keys=False)

    def render_alias_mappings_for_prompt(self) -> str:
        return yaml.safe_dump(self.alias_mappings, allow_unicode=True, sort_keys=False)

    def render_worksheet_policies_for_prompt(self) -> str:
        return yaml.safe_dump(self.worksheet_policy, allow_unicode=True, sort_keys=False)

    def list_policies(self) -> list[str]:
        policies = self.worksheet_policy.get("policies", {})
        return list(policies) if isinstance(policies, dict) else []

    def get_policy(self, policy_name: str) -> dict[str, Any] | None:
        policies = self.worksheet_policy.get("policies", {})
        if not isinstance(policies, dict):
            return None
        policy = policies.get(policy_name)
        return policy if isinstance(policy, dict) else None

    def validate_config(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []

        _validate_items("question_types", self.question_types, errors)
        _validate_items("knowledge_points", self.knowledge_points, errors)
        _validate_items("difficulty_levels", self.difficulty_levels, errors)
        _validate_items("mistake_tags", self.mistake_tags, errors)

        for item in self.question_types:
            layout = item.get("default_layout")
            if layout not in VALID_LAYOUTS:
                errors.append(f"question_types[{item.get('code')}].default_layout must be one of {sorted(VALID_LAYOUTS)}")

        orders = [item.get("order") for item in self.difficulty_levels]
        if len(orders) != len(set(orders)):
            errors.append("difficulty_levels.order must be unique")

        active_question_types = set(self.get_question_type_codes())
        active_knowledge_points = set(self.get_knowledge_point_codes())
        active_difficulties = set(self.get_difficulty_codes())
        active_tags = set(self.get_mistake_tag_codes())

        for tag in self.mistake_tags:
            for question_type in tag.get("default_question_types") or []:
                if question_type not in active_question_types:
                    errors.append(f"mistake_tags[{tag.get('code')}].default_question_types references inactive or unknown question_type: {question_type}")

        alias_targets = {
            "question_type_aliases": active_question_types,
            "knowledge_point_aliases": active_knowledge_points,
            "difficulty_aliases": active_difficulties,
            "mistake_tag_aliases": active_tags,
        }
        for alias_key, valid_targets in alias_targets.items():
            section = self.alias_mappings.get(alias_key, {})
            if not isinstance(section, dict):
                errors.append(f"alias_mappings.{alias_key} must be a mapping")
                continue
            for alias, target in section.items():
                if target not in valid_targets:
                    errors.append(f"alias_mappings.{alias_key}.{alias} targets unknown or inactive value: {target}")

        policies = self.worksheet_policy.get("policies", {})
        if not isinstance(policies, dict):
            errors.append("worksheet_policy.policies must be a mapping")
        else:
            for name, policy in policies.items():
                if not isinstance(policy, dict):
                    errors.append(f"worksheet_policy.policies.{name} must be a mapping")
                    continue
                max_questions = policy.get("max_questions")
                if not isinstance(max_questions, int) or max_questions <= 0:
                    errors.append(f"worksheet_policy.policies.{name}.max_questions must be a positive integer")
                sections = policy.get("sections")
                if not isinstance(sections, list) or not sections:
                    errors.append(f"worksheet_policy.policies.{name}.sections must be a non-empty list")
                    continue
                for idx, section in enumerate(sections):
                    prefix = f"worksheet_policy.policies.{name}.sections[{idx}]"
                    if not isinstance(section, dict):
                        errors.append(f"{prefix} must be a mapping")
                        continue
                    if section.get("question_type") not in active_question_types:
                        errors.append(f"{prefix}.question_type references inactive or unknown question_type: {section.get('question_type')}")
                    if section.get("layout") not in VALID_LAYOUTS:
                        errors.append(f"{prefix}.layout must be one of {sorted(VALID_LAYOUTS)}")
                    min_count = section.get("min_count")
                    max_count = section.get("max_count")
                    if not isinstance(min_count, int) or not isinstance(max_count, int):
                        errors.append(f"{prefix}.min_count and max_count must be integers")
                    elif min_count > max_count:
                        errors.append(f"{prefix}.min_count must be <= max_count")

        difficulty_policy = self.worksheet_policy.get("difficulty_policy", {})
        if isinstance(difficulty_policy, dict):
            for difficulty in difficulty_policy:
                if difficulty not in active_difficulties:
                    warnings.append(f"worksheet_policy.difficulty_policy contains inactive or unknown difficulty: {difficulty}")

        for section_result in (self.validate_student_config(), self.validate_education_config(), self.validate_curriculum_config()):
            errors.extend(section_result["errors"])
            warnings.extend(section_result["warnings"])

        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def validate_student_config(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        active = self.get_students(active_only=True)
        if not active:
            errors.append("students: at least one active=true student is required")
        if len(active) > 1:
            warnings.append("students: multiple active=true students configured; the first one will be used as default")
        subject_ids = {item.get("subject_id") for item in self.subjects}
        stage_ids = {item.get("stage_id") for item in self.stages}
        for student in self.students:
            prefix = f"students[{student.get('student_id', '?')}]"
            for field in ("student_id", "display_name", "current_grade", "current_term", "curriculum_version"):
                if student.get(field) in (None, ""):
                    errors.append(f"{prefix}.{field} is required")
            try:
                grade = int(student.get("current_grade"))
                stage = self.get_stage_for_grade(grade)
                if student.get("current_stage") and student.get("current_stage") != stage.get("stage_id"):
                    errors.append(f"{prefix}.current_stage does not match current_grade={grade}")
            except (TypeError, ValueError, RuleRegistryError):
                errors.append(f"{prefix}.current_grade must be a grade number from 1 to 12")
            if student.get("current_stage") not in stage_ids:
                errors.append(f"{prefix}.current_stage references unknown stage_id: {student.get('current_stage')}")
            for subject_id in student.get("default_subjects") or []:
                if subject_id not in subject_ids:
                    errors.append(f"{prefix}.default_subjects references unknown subject_id: {subject_id}")
        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def validate_education_config(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        subject_ids = _unique_required("subjects.subject_id", self.subjects, "subject_id", errors)
        stage_ids = _unique_required("stages.stage_id", self.stages, "stage_id", errors)
        grade_values = _unique_required("grades.grade", self.grades, "grade", errors)
        if sorted(int(value) for value in grade_values if str(value).isdigit()) != list(range(1, 13)):
            errors.append("grades.yaml must define grades 1 through 12")
        for grade in self.grades:
            if grade.get("stage_id") not in stage_ids:
                errors.append(f"grades[{grade.get('grade')}].stage_id references unknown stage_id: {grade.get('stage_id')}")
        for item in self.question_types:
            for subject_id in item.get("subjects") or []:
                if subject_id not in subject_ids:
                    errors.append(f"question_types[{item.get('code')}].subjects references unknown subject_id: {subject_id}")
        for tag in self.mistake_tags:
            for subject_id in tag.get("subjects") or []:
                if subject_id not in subject_ids:
                    errors.append(f"mistake_tags[{tag.get('code')}].subjects references unknown subject_id: {subject_id}")
        for skill in self.skills:
            for subject_id in skill.get("applies_to_subjects") or []:
                if subject_id not in subject_ids:
                    errors.append(f"skills[{skill.get('skill_id')}].applies_to_subjects references unknown subject_id: {subject_id}")
        for capability in self.expression_capabilities:
            for subject_id in capability.get("subjects") or []:
                if subject_id not in subject_ids:
                    errors.append(f"expression_capabilities[{capability.get('capability_id')}].subjects references unknown subject_id: {subject_id}")
        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def validate_curriculum_config(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        subject_ids = {item.get("subject_id") for item in self.subjects}
        stage_ids = {item.get("stage_id") for item in self.stages}
        canonical_question_types = set(self.get_question_type_canonical_codes(active_only=True))
        skill_ids = {item.get("skill_id") for item in self.skills if item.get("active", True)}
        knowledge_point_ids: list[str] = []
        for curriculum in self.curriculum.values():
            subject_id = curriculum.get("subject_id")
            grade = curriculum.get("grade")
            stage_id = curriculum.get("stage_id")
            label = f"curriculum[{curriculum.get('curriculum_version')}:{subject_id}:grade_{grade}]"
            if subject_id not in subject_ids:
                errors.append(f"{label}.subject_id references unknown subject_id: {subject_id}")
            if stage_id not in stage_ids:
                errors.append(f"{label}.stage_id references unknown stage_id: {stage_id}")
            try:
                expected_stage = self.get_stage_for_grade(int(grade))
                if expected_stage.get("stage_id") != stage_id:
                    errors.append(f"{label}.stage_id does not match grade range")
            except (TypeError, ValueError, RuleRegistryError):
                errors.append(f"{label}.grade must be a valid grade number")
            units = curriculum.get("units")
            if not isinstance(units, list) or not units:
                errors.append(f"{label}.units must be a non-empty list")
                continue
            for unit in units:
                for kp in unit.get("knowledge_points") or []:
                    kp_id = kp.get("knowledge_point_id")
                    if not kp_id:
                        errors.append(f"{label}.{unit.get('unit_id')}.knowledge_point_id is required")
                    else:
                        knowledge_point_ids.append(str(kp_id))
                    for question_type in kp.get("question_types") or []:
                        if question_type not in canonical_question_types:
                            errors.append(f"{label}.{kp_id}.question_types references unknown question_type code: {question_type}")
                    for skill_id in kp.get("skills") or []:
                        if skill_id not in skill_ids:
                            errors.append(f"{label}.{kp_id}.skills references unknown skill_id: {skill_id}")
        duplicates = sorted({value for value in knowledge_point_ids if knowledge_point_ids.count(value) > 1})
        for duplicate in duplicates:
            errors.append(f"curriculum knowledge_point_id must be globally unique; duplicate: {duplicate}")
        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def _suggest(self, alias_key: str, value: Any) -> str | None:
        if value is None:
            return None
        return self.alias_mappings.get(alias_key, {}).get(str(value).strip())

    def _curriculum_knowledge_points(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for curriculum in self.curriculum.values():
            result.extend(self._knowledge_points_from_curriculum(curriculum))
        return result

    def _knowledge_points_from_curriculum(self, curriculum: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for unit in curriculum.get("units") or []:
            for kp in unit.get("knowledge_points") or []:
                result.append({
                    **kp,
                    "unit_id": unit.get("unit_id"),
                    "unit_name": unit.get("name"),
                    "domain": unit.get("domain"),
                    "term": unit.get("term"),
                    "subject_id": curriculum.get("subject_id"),
                    "grade": curriculum.get("grade"),
                    "stage_id": curriculum.get("stage_id"),
                    "curriculum_version": curriculum.get("curriculum_version"),
                })
        return result

    def _legacy_knowledge_point_values_for_subject(self, subject_id: str) -> list[str]:
        values: list[str] = []
        for item in self.get_knowledge_points(active_only=True):
            item_subject = item.get("subject")
            if item_subject in (None, "", subject_id):
                values.append(str(item.get("code", "")))
        return _unique([value for value in values if value])


def load_rule_registry(config_dir: str | Path = DEFAULT_CONFIG_DIR, force_reload: bool = False) -> RuleRegistry:
    path = Path(config_dir).resolve()
    if force_reload:
        _load_rule_registry_cached.cache_clear()
    return _load_rule_registry_cached(str(path))


@lru_cache(maxsize=8)
def _load_rule_registry_cached(config_dir: str) -> RuleRegistry:
    path = Path(config_dir)
    registry = RuleRegistry(
        question_types=_load_question_types(path),
        knowledge_points=_load_section(path, "knowledge_points.yaml", "knowledge_points", list),
        difficulty_levels=_load_difficulty_levels(path),
        mistake_tags=_load_mistake_tags(path),
        alias_mappings=_load_alias_mappings(path),
        worksheet_policy=_load_yaml_file(path / "worksheet_policy.yaml", dict),
        students=_load_students(path),
        subjects=_load_education_section(path, "subjects.yaml", "subjects"),
        stages=_load_education_section(path, "stages.yaml", "stages"),
        grades=_load_education_section(path, "grades.yaml", "grades"),
        skills=_load_education_section(path, "skills.yaml", "skills"),
        expression_capabilities=_load_education_section(path, "expression_capabilities.yaml", "expression_capabilities"),
        curriculum=_load_curriculum(path),
        config_dir=path,
    )
    result = registry.validate_config()
    if not result["valid"]:
        joined = "\n".join(f"- {error}" for error in result["errors"])
        raise RuleRegistryError(f"Rule registry config validation failed:\n{joined}")
    return registry


def _filter_active(items: list[dict[str, Any]], active_only: bool) -> list[dict[str, Any]]:
    if not active_only:
        return list(items)
    return [item for item in items if item.get("active", True) is True]


def _unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def _unique_matches(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (str(item.get("knowledge_point_id", "")), str(item.get("name", "")))
        if key in seen:
            continue
        result.append(item)
        seen.add(key)
    return result


def _question_type_accepted_values(item: dict[str, Any]) -> list[str]:
    values = [item.get("code", ""), item.get("name", ""), item.get("display_name", "")]
    values.extend(item.get("legacy_names") or [])
    return _unique([value for value in values if value])


def _with_accepted_inputs(item: dict[str, Any]) -> dict[str, Any]:
    return {**item, "accepted_inputs": _question_type_accepted_values(item)}


def _applies_to_subject(item: dict[str, Any], subject_id: str, field: str) -> bool:
    subjects = item.get(field) or []
    if not subjects:
        return True
    return subject_id in subjects


def _student_matches(student: dict[str, Any], student_id: str) -> bool:
    return student.get("student_id") == student_id or student_id in (student.get("legacy_student_ids") or [])


def _curriculum_key(curriculum_version: str, subject_id: str, grade: int) -> str:
    return f"{curriculum_version}:{subject_id}:{grade}"


def _load_alias_mappings(config_dir: Path) -> dict[str, dict[str, str]]:
    data = _load_yaml_file(config_dir / "alias_mappings.yaml", dict)
    result: dict[str, dict[str, str]] = {}
    for key in ("question_type_aliases", "knowledge_point_aliases", "difficulty_aliases", "mistake_tag_aliases"):
        section = data.get(key, {})
        if section is None:
            section = {}
        if not isinstance(section, dict):
            raise RuleRegistryError(f"alias_mappings.yaml: {key} must be a mapping")
        result[key] = {str(alias): str(target) for alias, target in section.items()}
    return result


def _load_question_types(config_dir: Path) -> list[dict[str, Any]]:
    education_path = config_dir / "education" / "question_types.yaml"
    if education_path.exists():
        education_items = _load_section(config_dir / "education", "question_types.yaml", "question_types", list)
        if (config_dir / "question_types.yaml").exists():
            legacy_items = _load_section(config_dir, "question_types.yaml", "question_types", list)
            return _merge_legacy_question_types(education_items, legacy_items)
        return education_items
    return _load_section(config_dir, "question_types.yaml", "question_types", list)


def _load_mistake_tags(config_dir: Path) -> list[dict[str, Any]]:
    education_path = config_dir / "education" / "mistake_taxonomy.yaml"
    if education_path.exists():
        education_items = _load_section(config_dir / "education", "mistake_taxonomy.yaml", "mistake_tags", list)
        if (config_dir / "mistake_tags.yaml").exists():
            legacy_items = _load_section(config_dir, "mistake_tags.yaml", "mistake_tags", list)
            return _merge_by_code(education_items, legacy_items)
        return education_items
    return _load_section(config_dir, "mistake_tags.yaml", "mistake_tags", list)


def _load_difficulty_levels(config_dir: Path) -> list[dict[str, Any]]:
    education_path = config_dir / "education" / "difficulty_levels.yaml"
    if education_path.exists():
        return _load_section(config_dir / "education", "difficulty_levels.yaml", "difficulty_levels", list)
    return _load_section(config_dir, "difficulty_levels.yaml", "difficulty_levels", list)


def _load_education_section(config_dir: Path, file_name: str, section_name: str) -> list[dict[str, Any]]:
    return _load_section(config_dir / "education", file_name, section_name, list)


def _load_students(config_dir: Path) -> list[dict[str, Any]]:
    students_dir = config_dir / "students"
    students: list[dict[str, Any]] = []
    if students_dir.exists():
        for path in sorted(students_dir.glob("*.yaml")):
            data = _load_yaml_file(path, dict)
            students.append(data)
    if students:
        return students
    legacy_path = config_dir / "student_profile.yaml"
    if legacy_path.exists():
        legacy = _load_yaml_file(legacy_path, dict)
        return [{
            "student_id": legacy.get("student_id", "legacy_student"),
            "display_name": legacy.get("display_name", "Legacy Student"),
            "active": True,
            "current_stage": "primary",
            "current_grade": 5,
            "current_term": legacy.get("grade", "小学五年级"),
            "curriculum_version": "cn_k12_2022",
            "textbook_version": "generic",
            "default_subjects": ["math"],
            "profile": legacy,
            "compatibility_source": "config/student_profile.yaml",
        }]
    return []


def _load_curriculum(config_dir: Path) -> dict[str, dict[str, Any]]:
    root = config_dir / "curriculum"
    if not root.exists():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("*/*/grade_*.yaml")):
        data = _load_yaml_file(path, dict)
        key = _curriculum_key(
            str(data.get("curriculum_version", path.parents[1].name)),
            str(data.get("subject_id", path.parent.name)),
            int(data.get("grade", 0)),
        )
        result[key] = data
    return result


def _merge_by_code(primary: list[dict[str, Any]], extras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    codes = {item.get("code") for item in primary}
    result = list(primary)
    for item in extras:
        if item.get("code") not in codes:
            result.append(item)
            codes.add(item.get("code"))
    return result


def _merge_legacy_question_types(primary: list[dict[str, Any]], legacy: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accepted = {value for item in primary for value in _question_type_accepted_values(item)}
    result = list(primary)
    for item in legacy:
        code = item.get("code")
        if code in accepted:
            continue
        result.append({
            "code": code,
            "name": item.get("display_name") or code,
            "scope": "legacy_compatibility",
            "subjects": item.get("subjects", []),
            "active": item.get("active", True),
            "default_layout": item.get("default_layout", "single_column"),
            "description": item.get("description", ""),
            "legacy_names": [code],
        })
        accepted.add(code)
    return result


def _load_section(config_dir: Path, file_name: str, section_name: str, expected_type: type) -> Any:
    data = _load_yaml_file(config_dir / file_name, dict)
    if section_name not in data:
        raise RuleRegistryError(f"{file_name}: missing top-level section '{section_name}'")
    section = data[section_name]
    if not isinstance(section, expected_type):
        raise RuleRegistryError(f"{file_name}: section '{section_name}' must be {expected_type.__name__}")
    return section


def _load_yaml_file(path: Path, expected_type: type) -> Any:
    if not path.exists():
        raise RuleRegistryError(f"Missing rule registry config file: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise RuleRegistryError(f"Invalid YAML in rule registry config file {path}: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, expected_type):
        raise RuleRegistryError(f"{path.name}: expected {expected_type.__name__}, got {type(data).__name__}")
    return data


def _validate_items(section_name: str, items: list[dict[str, Any]], errors: list[str]) -> None:
    if not isinstance(items, list):
        errors.append(f"{section_name} must be a list")
        return
    codes: list[str] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{section_name}[{idx}] must be a mapping")
            continue
        code = item.get("code")
        if not isinstance(code, str) or not code.strip():
            errors.append(f"{section_name}[{idx}].code must be a non-empty string")
            continue
        codes.append(code)
    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    for code in duplicates:
        errors.append(f"{section_name}.code must be unique; duplicate: {code}")


def _unique_required(section_name: str, items: list[dict[str, Any]], field: str, errors: list[str]) -> list[str]:
    values: list[str] = []
    for idx, item in enumerate(items):
        value = item.get(field)
        if value in (None, ""):
            errors.append(f"{section_name}[{idx}].{field} is required")
            continue
        values.append(str(value))
    duplicates = sorted({value for value in values if values.count(value) > 1})
    for duplicate in duplicates:
        errors.append(f"{section_name}.{field} must be unique; duplicate: {duplicate}")
    return values
