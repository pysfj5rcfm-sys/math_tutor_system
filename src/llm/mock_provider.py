from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.llm.provider import LLMProvider


ROOT = Path(__file__).resolve().parents[2]


class MockProvider(LLMProvider):
    def extract_mistakes(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return yaml.safe_load((ROOT / "samples" / "sample_mistakes.yaml").read_text(encoding="utf-8"))

    def generate_worksheet(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return yaml.safe_load((ROOT / "samples" / "sample_worksheet.yaml").read_text(encoding="utf-8"))

    def generate_weekly_review(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"review": "mock weekly review"}

    def suggest_profile_updates(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"profile_update_suggestions": []}
