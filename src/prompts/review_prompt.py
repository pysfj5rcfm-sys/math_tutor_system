from __future__ import annotations

from typing import Any

import yaml


def build_review_analysis_prompt(profile: dict[str, Any], stats: dict[str, Any]) -> str:
    return (
        "请基于以下学生画像和本周统计，给出温柔、具体、可执行的下周训练建议。"
        "不要自动修改学生画像，只输出建议。\n\n"
        "student_profile:\n"
        f"{yaml.safe_dump(profile, allow_unicode=True, sort_keys=False)}\n"
        "stats_summary:\n"
        f"{yaml.safe_dump(stats, allow_unicode=True, sort_keys=False)}"
    )
