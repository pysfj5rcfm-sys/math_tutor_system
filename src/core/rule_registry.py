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
    config_dir: Path = DEFAULT_CONFIG_DIR

    def get_question_type_codes(self, active_only: bool = True) -> list[str]:
        return [item["code"] for item in self.get_question_types(active_only)]

    def get_knowledge_point_codes(self, active_only: bool = True) -> list[str]:
        return [item["code"] for item in self.get_knowledge_points(active_only)]

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

    def suggest_question_type(self, value: Any) -> str | None:
        return self._suggest("question_type_aliases", value)

    def suggest_knowledge_point(self, value: Any) -> str | None:
        return self._suggest("knowledge_point_aliases", value)

    def suggest_difficulty(self, value: Any) -> str | None:
        return self._suggest("difficulty_aliases", value)

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

    def render_question_types_for_prompt(self) -> str:
        return yaml.safe_dump(self.get_question_types(), allow_unicode=True, sort_keys=False)

    def render_knowledge_points_for_prompt(self) -> str:
        return yaml.safe_dump(self.get_knowledge_points(), allow_unicode=True, sort_keys=False)

    def render_difficulty_levels_for_prompt(self) -> str:
        return yaml.safe_dump(self.get_difficulty_levels(), allow_unicode=True, sort_keys=False)

    def render_mistake_tags_for_prompt(self) -> str:
        return yaml.safe_dump(self.get_mistake_tags(), allow_unicode=True, sort_keys=False)

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

        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def _suggest(self, alias_key: str, value: Any) -> str | None:
        if value is None:
            return None
        return self.alias_mappings.get(alias_key, {}).get(str(value).strip())


def load_rule_registry(config_dir: str | Path = DEFAULT_CONFIG_DIR, force_reload: bool = False) -> RuleRegistry:
    path = Path(config_dir).resolve()
    if force_reload:
        _load_rule_registry_cached.cache_clear()
    return _load_rule_registry_cached(str(path))


@lru_cache(maxsize=8)
def _load_rule_registry_cached(config_dir: str) -> RuleRegistry:
    path = Path(config_dir)
    registry = RuleRegistry(
        question_types=_load_section(path, "question_types.yaml", "question_types", list),
        knowledge_points=_load_section(path, "knowledge_points.yaml", "knowledge_points", list),
        difficulty_levels=_load_section(path, "difficulty_levels.yaml", "difficulty_levels", list),
        mistake_tags=_load_section(path, "mistake_tags.yaml", "mistake_tags", list),
        alias_mappings=_load_alias_mappings(path),
        worksheet_policy=_load_yaml_file(path / "worksheet_policy.yaml", dict),
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
