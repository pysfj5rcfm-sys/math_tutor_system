from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.llm.provider import LLMProvider


class ReplayProvider(LLMProvider):
    def __init__(self, cache_dir: str | Path = "outputs/prompts") -> None:
        self.cache_dir = Path(cache_dir)

    def _read_yaml(self, name: str) -> dict[str, Any]:
        path = self.cache_dir / name
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def extract_mistakes(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._read_yaml("replay_mistakes.yaml")

    def generate_worksheet(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._read_yaml("replay_worksheet.yaml")

    def generate_weekly_review(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._read_yaml("replay_weekly_review.yaml")

    def suggest_profile_updates(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._read_yaml("replay_profile_updates.yaml")
