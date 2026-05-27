from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostRecord:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0


class CostTracker:
    def estimate(self, _: CostRecord) -> float:
        return 0.0
