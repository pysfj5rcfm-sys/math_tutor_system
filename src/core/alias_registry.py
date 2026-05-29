from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.rule_registry import RuleRegistryError, load_rule_registry


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALIAS_PATH = ROOT / "config" / "alias_mappings.yaml"

EMPTY_ALIASES = {
    "question_type_aliases": {},
    "knowledge_point_aliases": {},
    "difficulty_aliases": {},
    "mistake_tag_aliases": {},
}


def load_alias_mappings(path: str | Path = DEFAULT_ALIAS_PATH) -> dict[str, dict[str, str]]:
    if Path(path).resolve() != DEFAULT_ALIAS_PATH.resolve():
        from yaml import YAMLError, safe_load

        try:
            with Path(path).open("r", encoding="utf-8") as f:
                data = safe_load(f) or {}
        except (FileNotFoundError, YAMLError):
            return {key: {} for key in EMPTY_ALIASES}
        result: dict[str, dict[str, str]] = {}
        for key in EMPTY_ALIASES:
            section = data.get(key, {})
            result[key] = section if isinstance(section, dict) else {}
        return result

    try:
        return load_rule_registry().alias_mappings
    except RuleRegistryError:
        return {key: {} for key in EMPTY_ALIASES}


def suggest_value(field: str, current_value: Any, aliases: dict[str, dict[str, str]] | None = None) -> str | None:
    if current_value is None:
        return None
    aliases = aliases or load_alias_mappings()
    value = str(current_value).strip()
    field_to_alias_key = {
        "question_type": "question_type_aliases",
        "knowledge_point": "knowledge_point_aliases",
        "difficulty": "difficulty_aliases",
        "mistake_tag": "mistake_tag_aliases",
        "target_mistake_tag": "mistake_tag_aliases",
        "layout": {},
    }
    if field == "layout":
        return {"双列": "two_columns", "单列": "single_column"}.get(value)
    alias_key = field_to_alias_key.get(field)
    if not isinstance(alias_key, str):
        return None
    return aliases.get(alias_key, {}).get(value)
