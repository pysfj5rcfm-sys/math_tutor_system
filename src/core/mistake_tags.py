from __future__ import annotations

from dataclasses import dataclass

from src.core.rule_registry import load_rule_registry


@dataclass(frozen=True)
class MistakeTag:
    code: str
    category: str
    name: str
    description: str
    typical_symptoms: str
    training_hint: str


def _tag_from_config(item: dict[str, object]) -> MistakeTag:
    symptoms = item.get("typical_symptoms", "")
    if isinstance(symptoms, list):
        symptoms = "；".join(str(value) for value in symptoms)
    return MistakeTag(
        code=str(item.get("code", "")),
        category=str(item.get("category", "")),
        name=str(item.get("name", "")),
        description=str(item.get("description", "")),
        typical_symptoms=str(symptoms),
        training_hint=str(item.get("training_hint", "")),
    )


MISTAKE_TAGS = [_tag_from_config(item) for item in load_rule_registry().get_mistake_tags()]
TAG_CODES = {tag.code for tag in MISTAKE_TAGS}


def tags_as_dicts() -> list[dict[str, object]]:
    return [
        _tag_from_config(item).__dict__ | {
            "is_active": bool(item.get("active", True)),
            "default_question_types": item.get("default_question_types", []),
        }
        for item in load_rule_registry().get_mistake_tags(active_only=False)
    ]
