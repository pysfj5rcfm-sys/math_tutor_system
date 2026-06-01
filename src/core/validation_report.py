from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import yaml

from src.core.rule_registry import RuleRegistry, load_rule_registry


ERROR_FIELD_MAP = {
    "invalid_question_type": "question_type",
    "unknown_knowledge_point": "knowledge_point",
    "ambiguous_knowledge_point": "knowledge_point",
    "invalid_difficulty": "difficulty",
    "invalid_mistake_tag": "mistake_tag",
    "empty_question_summary": "question_summary",
    "missing_date": "date",
    "empty_question": "question",
    "missing_answer": "answer",
    "missing_explanation": "explanation",
    "invalid_section_layout": "layout",
    "invalid_mistakes_root": "mistakes",
    "invalid_worksheet_root": "worksheet",
    "invalid_sections": "sections",
    "invalid_questions": "questions",
}


def format_validation_report(
    validation_result: dict[str, Any],
    source_type: str,
    original_payload: dict[str, Any],
    original_text: str,
    registry: RuleRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or load_rule_registry()
    items: list[dict[str, Any]] = []
    for level in ("errors", "warnings"):
        for raw in validation_result.get(level, []):
            items.append(_readable_item(raw, level[:-1], source_type, original_payload, registry))
    return {
        "stage": "business_validation",
        "valid": validation_result.get("valid", False),
        "source_type": source_type,
        "summary": _summary(validation_result),
        "readable_items": items,
        "raw_validation": validation_result,
        "original_text": original_text,
    }


def _summary(validation_result: dict[str, Any]) -> str:
    errors = len(validation_result.get("errors", []))
    warnings = len(validation_result.get("warnings", []))
    if errors:
        return f"发现 {errors} 个业务校验错误，已阻止写库；另有 {warnings} 个 warning。"
    if warnings:
        return f"发现 {warnings} 个 warning，可导入为 needs_confirmation，但需要家长确认。"
    return "业务校验通过。"


def _readable_item(
    raw: dict[str, Any],
    level: str,
    source_type: str,
    payload: dict[str, Any],
    registry: RuleRegistry,
) -> dict[str, Any]:
    code = raw.get("code", "")
    field = _field_for(code, source_type)
    index = raw.get("index")
    position = _position(source_type, payload, index, code)
    current_value = _current_value(source_type, payload, field, index, code)
    suggested = registry.suggest_field_value(field, current_value)
    human = _human_message(level, field, current_value, suggested, raw.get("message", ""))
    return {
        "level": level,
        "code": code,
        "field": field,
        "current_value": current_value,
        "suggested_value": suggested,
        "message": raw.get("message", ""),
        "human_message": human,
        "legal_values": _legal_values(field, registry),
        "index": index,
        **position,
        "path": _path(source_type, field, position),
    }


def _legal_values(field: str, registry: RuleRegistry) -> list[str]:
    if field == "question_type":
        return registry.get_question_type_codes()
    if field == "knowledge_point":
        return registry.get_knowledge_point_codes()
    if field == "difficulty":
        return registry.get_difficulty_codes()
    if field in {"mistake_tag", "target_mistake_tag"}:
        return registry.get_mistake_tag_codes()
    if field == "layout":
        return ["two_columns", "single_column"]
    return []


def _field_for(code: str, source_type: str) -> str:
    field = ERROR_FIELD_MAP.get(code, "")
    if code == "invalid_mistake_tag" and source_type == "worksheet":
        return "target_mistake_tag"
    return field


def _position(source_type: str, payload: dict[str, Any], index: Any, code: str) -> dict[str, Any]:
    if index is None:
        return {}
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return {"index": index}
    if source_type == "mistakes":
        row = _mistake_row(payload, idx)
        label = f"第 {idx + 1} 条错因记录"
        if isinstance(row, dict) and row.get("question_summary"):
            label += f"：「{row['question_summary']}」"
        if isinstance(row, dict) and row.get("question_no"):
            label += f"，题号：{row['question_no']}"
        return {"mistake_index": idx, "position_label": label}

    sections = (((payload.get("worksheet") or {}).get("sections")) or [])
    section_level_codes = {"invalid_section_layout", "invalid_questions", "invalid_section"}
    if code in section_level_codes:
        section_idx = idx
        section = sections[section_idx] if isinstance(sections, list) and section_idx < len(sections) else {}
        name = section.get("name") if isinstance(section, dict) else None
        return {
            "section_index": section_idx,
            "section_name": name,
            "position_label": f"第 {section_idx + 1} 个部分" + (f"「{name}」" if name else ""),
        }

    section_idx = idx // 1000
    question_idx = idx % 1000
    section = sections[section_idx] if isinstance(sections, list) and section_idx < len(sections) else {}
    section_name = section.get("name") if isinstance(section, dict) else None
    global_no = _global_question_no(sections, section_idx, question_idx)
    return {
        "section_index": section_idx,
        "section_name": section_name,
        "question_index": question_idx,
        "global_question_no": global_no,
        "position_label": f"第 {section_idx + 1} 个部分「{section_name or '未命名'}」第 {question_idx + 1} 题，整卷第 {global_no} 题。",
    }


def _mistake_row(payload: dict[str, Any], idx: int) -> Any:
    rows = payload.get("mistakes")
    if isinstance(rows, list) and idx < len(rows):
        return rows[idx]
    return None


def _question(payload: dict[str, Any], index: Any) -> dict[str, Any] | None:
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return None
    sections = (((payload.get("worksheet") or {}).get("sections")) or [])
    section_idx = idx // 1000
    question_idx = idx % 1000
    if not isinstance(sections, list) or section_idx >= len(sections):
        return None
    questions = (sections[section_idx] or {}).get("questions", [])
    if not isinstance(questions, list) or question_idx >= len(questions):
        return None
    item = questions[question_idx]
    return item if isinstance(item, dict) else None


def _current_value(source_type: str, payload: dict[str, Any], field: str, index: Any, code: str) -> Any:
    if source_type == "mistakes":
        row = _mistake_row(payload, int(index)) if index is not None else None
        return row.get(field) if isinstance(row, dict) else None
    if code == "invalid_section_layout" and index is not None:
        sections = (((payload.get("worksheet") or {}).get("sections")) or [])
        try:
            section = sections[int(index)]
        except (TypeError, ValueError, IndexError):
            return None
        return section.get("layout") if isinstance(section, dict) else None
    question = _question(payload, index)
    return question.get(field) if isinstance(question, dict) else None


def _global_question_no(sections: Any, section_idx: int, question_idx: int) -> int:
    total = 0
    if isinstance(sections, list):
        for idx, section in enumerate(sections[:section_idx]):
            questions = section.get("questions", []) if isinstance(section, dict) else []
            total += len(questions) if isinstance(questions, list) else 0
    return total + question_idx + 1


def _path(source_type: str, field: str, position: dict[str, Any]) -> str:
    if source_type == "mistakes":
        idx = position.get("mistake_index")
        return f"mistakes[{idx}].{field}" if idx is not None else field
    if "question_index" in position:
        return f"worksheet.sections[{position['section_index']}].questions[{position['question_index']}].{field}"
    if "section_index" in position:
        return f"worksheet.sections[{position['section_index']}].{field}"
    return field


def _human_message(level: str, field: str, current: Any, suggested: Any, message: str) -> str:
    prefix = "错误" if level == "error" else "提醒"
    if suggested:
        return f"{prefix}：字段 {field} 当前值为「{current}」，建议改为「{suggested}」。"
    if current is not None:
        return f"{prefix}：字段 {field} 当前值为「{current}」。{message}"
    return f"{prefix}：字段 {field} 缺失或为空。{message}"


def report_to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Business Validation Report",
        "",
        f"source_type: {report.get('source_type')}",
        "stage: business_validation",
        f"valid: {str(report.get('valid')).lower()}",
        "",
        f"## 总览\n\n{report.get('summary')}",
        "",
        "## 可读问题",
    ]
    for item in report.get("readable_items", []):
        lines.append(
            f"- [{item.get('level')}] {item.get('position_label', item.get('path'))} | "
            f"{item.get('field')} = {item.get('current_value')} | 建议：{item.get('suggested_value') or '无自动建议'} | "
            f"{item.get('human_message')}"
        )
    lines.extend(["", "## 原始校验 JSON", "```yaml", yaml.safe_dump(report.get("raw_validation"), allow_unicode=True, sort_keys=False), "```"])
    return "\n".join(lines)


def save_validation_report(report: dict[str, Any], source_type: str, output_dir: str | Path) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    md_path = output_path / f"{source_type}_validation_report.md"
    json_path = output_path / f"{source_type}_validation_report.json"
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path
