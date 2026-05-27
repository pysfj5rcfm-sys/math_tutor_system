from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    def extract_mistakes(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_worksheet(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_weekly_review(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def suggest_profile_updates(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError
