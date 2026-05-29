from __future__ import annotations

from typing import Any


FILE_MARKERS = ("uat_", "sample_", "invalid_")
SOURCE_MARKERS = ("uat", "sample", "测试")
SAMPLE_WARNING_MESSAGE = (
    "这是测试 / 样例数据，不建议导入正式学习库。"
    "如果只是验收功能，请使用临时数据库或先备份数据库。"
)


def detect_sample_data_warning(
    file_name: str | None = None,
    payload: dict[str, Any] | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    if file_name:
        lowered = file_name.lower()
        for marker in FILE_MARKERS:
            if marker in lowered:
                reasons.append(f"文件名包含 {marker}")

    for source in _source_values(payload):
        source_text = str(source)
        lowered = source_text.lower()
        if any(marker in lowered for marker in SOURCE_MARKERS) or "测试" in source_text:
            reasons.append(f"source 字段疑似测试数据：{source_text}")

    if text and not payload:
        lowered_text = text.lower()
        if any(f"source:" in lowered_text and marker in lowered_text for marker in SOURCE_MARKERS):
            reasons.append("YAML 文本中的 source 字段疑似测试数据")

    return {
        "is_sample": bool(reasons),
        "blocks_import": False,
        "reasons": sorted(set(reasons)),
        "message": SAMPLE_WARNING_MESSAGE if reasons else "",
    }


def _source_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        values = [value["source"]] if "source" in value else []
        for child in value.values():
            values.extend(_source_values(child))
        return values
    if isinstance(value, list):
        values: list[Any] = []
        for child in value:
            values.extend(_source_values(child))
        return values
    return []
