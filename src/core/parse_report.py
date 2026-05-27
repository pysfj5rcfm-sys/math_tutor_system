from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import yaml

from src.core.yaml_utils import YamlParseResult


def format_parse_error(parse_result: YamlParseResult, source_type: str, original_text: str) -> dict[str, Any]:
    return {
        "stage": "yaml_parse",
        "valid": False,
        "source_type": source_type,
        "error_type": parse_result.error_type,
        "line": parse_result.line,
        "column": parse_result.column,
        "problem": parse_result.problem,
        "context": parse_result.context,
        "human_message": parse_result.human_message,
        "suggestion": parse_result.suggestion,
        "nearby_lines": nearby_lines(original_text, parse_result.line),
        "raw_error": parse_result.raw_error,
        "has_markdown_fence": parse_result.has_markdown_fence,
    }


def nearby_lines(text: str, line: int | None, radius: int = 3) -> list[dict[str, Any]]:
    lines = text.splitlines()
    if not lines:
        return []
    if line is None:
        start, end = 1, min(len(lines), radius * 2 + 1)
    else:
        start = max(1, line - radius)
        end = min(len(lines), line + radius)
    return [
        {"line": no, "text": lines[no - 1], "is_error_line": no == line}
        for no in range(start, end + 1)
    ]


def report_to_markdown(report: dict[str, Any]) -> str:
    nearby = "\n".join(
        f"{'>' if row.get('is_error_line') else ' '} {row['line']:>4}: {row['text']}"
        for row in report.get("nearby_lines", [])
    )
    return f"""# YAML Parse Report

source_type: {report.get("source_type")}
stage: yaml_parse
valid: false

## 中文解释

{report.get("human_message") or ""}

## 错误位置

第 {report.get("line") or "未知"} 行，第 {report.get("column") or "未知"} 列

## problem

{report.get("problem") or ""}

## 建议修复

{report.get("suggestion") or ""}

## 附近文本

```text
{nearby}
```

## 原始错误

```text
{report.get("raw_error") or ""}
```
"""


def save_parse_report(report: dict[str, Any], source_type: str, output_dir: str | Path) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    md_path = output_path / f"{source_type}_parse_report.md"
    json_path = output_path / f"{source_type}_parse_report.json"
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path
