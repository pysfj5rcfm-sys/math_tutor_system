from __future__ import annotations

from typing import Any

from src.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """v0.1 stub only. No real API calls are implemented."""

    def extract_mistakes(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("OpenAI API calls are out of scope for v0.1")

    def generate_worksheet(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("OpenAI API calls are out of scope for v0.1")

    def generate_weekly_review(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("OpenAI API calls are out of scope for v0.1")

    def suggest_profile_updates(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("OpenAI API calls are out of scope for v0.1")
