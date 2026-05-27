from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import yaml


@dataclass
class YamlParseResult:
    ok: bool
    payload: object | None
    error_type: str | None = None
    message: str | None = None
    line: int | None = None
    column: int | None = None
    problem: str | None = None
    context: str | None = None
    human_message: str | None = None
    suggestion: str | None = None
    raw_error: str | None = None
    has_markdown_fence: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_parse_yaml(text: str) -> YamlParseResult:
    has_fence = "```yaml" in text or "```" in text
    try:
        payload = yaml.safe_load(text) or {}
        return YamlParseResult(ok=True, payload=payload, has_markdown_fence=has_fence)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
        problem = getattr(exc, "problem", None)
        context = getattr(exc, "context", None)
        human_message, suggestion = _messages(text, problem, has_fence)
        return YamlParseResult(
            ok=False,
            payload=None,
            error_type=exc.__class__.__name__,
            message=str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__,
            line=(mark.line + 1) if mark else None,
            column=(mark.column + 1) if mark else None,
            problem=problem,
            context=context,
            human_message=human_message,
            suggestion=suggestion,
            raw_error=str(exc),
            has_markdown_fence=has_fence,
        )
    except Exception as exc:
        return YamlParseResult(
            ok=False,
            payload=None,
            error_type=exc.__class__.__name__,
            message=str(exc),
            human_message="YAML 解析失败，尚未进入 MVP 字段校验。",
            suggestion="请检查输入是否为纯 YAML 文本。",
            raw_error=str(exc),
            has_markdown_fence=has_fence,
        )


def _messages(text: str, problem: str | None, has_fence: bool) -> tuple[str, str]:
    default_human = "YAML 语法错误，尚未进入 MVP 字段校验。"
    default_suggestion = "请检查缩进、冒号、列表项 '-'、代码块标记和字符串引号。"
    if has_fence:
        return (
            "检测到可能包含 Markdown 代码块标记。请删除 ```yaml 和 ```，只保留 YAML 正文。",
            "请删除代码块围栏后重新导入，只让内容直接从 mistakes: 或 worksheet: 开始。",
        )
    problem_text = problem or ""
    if "found '-'" in problem_text:
        return (
            default_human,
            "检测到列表项 '-' 可能出现在错误层级。请检查该行是否缺少缩进。如果根节点是 mistakes:，每条记录应写成缩进两个空格的 '  - ...'。如果根节点是 worksheet:，sections 和 questions 必须逐层缩进。",
        )
    if "could not find expected ':'" in problem_text:
        return (
            default_human,
            "检测到缺少冒号。请检查字段名后是否有 ':'，例如 question_type:。",
        )
    if "mapping values are not allowed here" in problem_text:
        return (
            default_human,
            "检测到冒号或缩进位置异常。请检查该行前后是否有多余冒号、中文冒号或缩进错误。",
        )
    return default_human, default_suggestion
