from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import yaml

from src.core.mistake_tags import tags_as_dicts
from src.core.mistakes import import_mistakes_payload, list_mistakes, validate_mistakes_payload
from src.core.parse_report import format_parse_error, save_parse_report
from src.core.stats import stats_summary
from src.core.student_profile import load_student_profile
from src.core.validation_report import format_validation_report, save_validation_report
from src.core.worksheets import get_worksheet_bundle, import_worksheet_payload, validate_worksheet_payload
from src.core.yaml_utils import safe_parse_yaml
from src.db import confirm_record, get_connection, init_db
from src.prompts.marking_prompt import build_marking_prompt, save_marking_prompt
from src.prompts.repair_prompt import build_validation_repair_prompt, build_yaml_parse_repair_prompt, save_repair_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt, save_worksheet_prompt
from src.render.html_renderer import save_answer_sheet_html, save_worksheet_html
from src.workflows.review_workflow import generate_weekly_review


ROOT = Path(__file__).resolve().parents[1]


def _conn():
    init_db()
    return get_connection()


def _show_report(report: dict) -> None:
    st.json(report)
    if report.get("errors"):
        st.error("存在错误，错误记录已跳过。")
    elif report.get("warnings"):
        st.warning("导入成功，但存在 warning，需要家长确认。")
    else:
        st.success("校验通过。")


def _sample_picker(prefix: str, default_name: str) -> str:
    sample_files = sorted((ROOT / "samples").glob(f"*{prefix}*.yaml"))
    names = [path.name for path in sample_files]
    default_index = names.index(default_name) if default_name in names else 0
    selected = st.selectbox("选择样例文件", names, index=default_index)
    if selected.startswith("uat_"):
        st.warning("这是 UAT 测试数据，不建议导入正式学习库；如需测试，请使用临时数据库或先备份数据库。")
    return (ROOT / "samples" / selected).read_text(encoding="utf-8")


def _show_parse_report(source_type: str, report: dict, original_text: str) -> None:
    st.error(report["human_message"])
    st.write(f"错误位置：第 {report.get('line') or '未知'} 行，第 {report.get('column') or '未知'} 列")
    st.write(f"问题：{report.get('problem') or '未知'}")
    st.info(report.get("suggestion") or "")
    st.write("错误行附近文本：")
    nearby = "\n".join(
        f"{'>' if row.get('is_error_line') else ' '} {row['line']:>4}: {row['text']}"
        for row in report.get("nearby_lines", [])
    )
    st.code(nearby, language="text")
    with st.expander("原始 PyYAML 错误"):
        st.code(report.get("raw_error") or "", language="text")
    prompt = build_yaml_parse_repair_prompt(source_type, report, original_text)
    st.text_area("GPT YAML 语法修复 Prompt", prompt, height=260, key=f"{source_type}_parse_repair_prompt")
    if st.button("保存 parse_report.md / parse_report.json", key=f"{source_type}_save_parse_report"):
        md_path, json_path = save_parse_report(report, source_type, ROOT / "outputs" / "prompts")
        st.success(f"已保存：{md_path}；{json_path}")
    if st.button("保存 repair prompt 到 outputs/prompts", key=f"{source_type}_save_parse_prompt"):
        path = save_repair_prompt(prompt, source_type, "parse")
        st.success(f"已保存：{path}")


def _show_validation_report(source_type: str, report: dict, original_text: str) -> None:
    if report["raw_validation"].get("errors"):
        st.error(report["summary"])
    elif report["raw_validation"].get("warnings"):
        st.warning(report["summary"])
    else:
        st.success(report["summary"])
    for item in report.get("readable_items", []):
        label = "错误" if item["level"] == "error" else "提醒"
        st.write(f"{label}：{item.get('position_label', item.get('path'))}")
        st.write(f"字段：`{item.get('field')}`，当前值：`{item.get('current_value')}`，建议值：`{item.get('suggested_value') or '无自动建议'}`")
        st.caption(item.get("human_message", ""))
    with st.expander("原始 validation JSON"):
        st.json(report.get("raw_validation", {}))
    if report.get("readable_items"):
        prompt = build_validation_repair_prompt(source_type, report, original_text)
        st.text_area("GPT 业务校验修复 Prompt", prompt, height=260, key=f"{source_type}_validation_repair_prompt")
        if st.button("保存 validation_report.md / validation_report.json", key=f"{source_type}_save_validation_report"):
            md_path, json_path = save_validation_report(report, source_type, ROOT / "outputs" / "prompts")
            st.success(f"已保存：{md_path}；{json_path}")
        if st.button("保存 validation repair prompt 到 outputs/prompts", key=f"{source_type}_save_validation_prompt"):
            path = save_repair_prompt(prompt, source_type, "validation")
            st.success(f"已保存：{path}")


def page_home() -> None:
    st.title("math_tutor_system v0.1.2")
    st.write("GPT 协作型家庭教培教务系统：本地负责记录、校验、统计、Prompt 和 HTML 排版。")
    st.info("v0.1 不接 API、不做 OCR、不自动批改、不自动出题。")


def page_profile() -> None:
    st.header("学生画像查看")
    profile = load_student_profile()
    st.code(
        yaml.safe_dump(profile, allow_unicode=True, sort_keys=False),
        language="yaml",
    )


def page_tags() -> None:
    st.header("错因标签库")
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM mistake_tags ORDER BY code").fetchall()
        st.dataframe([dict(row) for row in rows], use_container_width=True)


def page_import_mistakes() -> None:
    st.header("mistakes.yaml 导入与校验")
    st.caption("v0.1.2 暂允许重复导入，请家长确认时留意重复记录；正式去重策略留到后续版本。")
    sample = _sample_picker("mistakes", "sample_mistakes.yaml")
    text = st.text_area("YAML", value=sample, height=320)
    if st.button("校验并导入 mistakes.yaml"):
        parse_result = safe_parse_yaml(text)
        if not parse_result.ok:
            _show_parse_report("mistakes", format_parse_error(parse_result, "mistakes", text), text)
            return
        payload = parse_result.payload if isinstance(parse_result.payload, dict) else {}
        validation_result, _ = validate_mistakes_payload(payload)
        validation_view = format_validation_report(validation_result.as_dict(), "mistakes", payload, text)
        if validation_result.errors:
            _show_validation_report("mistakes", validation_view, text)
            return
        with _conn() as conn:
            report = import_mistakes_payload(conn, payload)
            _show_validation_report("mistakes", format_validation_report(report, "mistakes", payload, text), text)


def page_mistake_list() -> None:
    st.header("错题记录列表")
    include = st.checkbox("include_unconfirmed", value=True)
    with _conn() as conn:
        rows = list_mistakes(conn, include)
        st.dataframe(rows, use_container_width=True)
        ids = [row["id"] for row in rows if row["status"] == "needs_confirmation"]
        selected = st.selectbox("选择待确认记录", ids) if ids else None
        if selected and st.button("确认为 confirmed"):
            confirm_record(conn, "mistakes", int(selected))
            st.success("已确认。")


def page_stats() -> None:
    st.header("错因统计")
    include = st.checkbox("include_unconfirmed 调试选项", value=False)
    with _conn() as conn:
        summary = stats_summary(conn, include_unconfirmed=include, today=date.today())
        if not include and not summary["recent_7_days"] and not summary["recent_30_days"]:
            st.info("暂无 confirmed 错题记录。请先导入 mistakes.yaml，并在“错题记录列表”中确认记录。")
        st.json(summary)


def page_marking_prompt() -> None:
    st.header("GPT 批改 Prompt 生成")
    prompt = build_marking_prompt(load_student_profile(), tags_as_dicts())
    st.text_area("Prompt", prompt, height=420)
    if st.button("保存到 outputs/prompts"):
        path = save_marking_prompt(prompt)
        st.success(f"已保存：{path}")


def page_worksheet_prompt() -> None:
    st.header("GPT 出题 Prompt 生成")
    with _conn() as conn:
        stats = stats_summary(conn, include_unconfirmed=False, today=date.today())
    prompt = build_worksheet_prompt(load_student_profile(), stats, tags_as_dicts())
    st.text_area("Prompt", prompt, height=420)
    if st.button("保存到 outputs/prompts"):
        path = save_worksheet_prompt(prompt)
        st.success(f"已保存：{path}")


def page_import_worksheet() -> None:
    st.header("worksheet.yaml 导入与校验")
    st.caption("v0.1.2 暂允许重复导入 worksheet；正式去重策略留到后续版本。")
    sample = _sample_picker("worksheet", "sample_worksheet.yaml")
    text = st.text_area("YAML", value=sample, height=360)
    if st.button("校验并导入 worksheet.yaml"):
        parse_result = safe_parse_yaml(text)
        if not parse_result.ok:
            _show_parse_report("worksheet", format_parse_error(parse_result, "worksheet", text), text)
            return
        payload = parse_result.payload if isinstance(parse_result.payload, dict) else {}
        validation_result, _ = validate_worksheet_payload(payload)
        validation_view = format_validation_report(validation_result.as_dict(), "worksheet", payload, text)
        if validation_result.errors:
            _show_validation_report("worksheet", validation_view, text)
            return
        with _conn() as conn:
            report, worksheet_id = import_worksheet_payload(conn, payload)
            _show_validation_report("worksheet", format_validation_report(report, "worksheet", payload, text), text)
            if worksheet_id:
                st.success(f"worksheet_id={worksheet_id}")


def _worksheet_ids(conn) -> list[int]:
    return [row["id"] for row in conn.execute("SELECT id FROM worksheets ORDER BY id DESC").fetchall()]


def page_export_student() -> None:
    st.header("学生卷 HTML 导出")
    with _conn() as conn:
        ids = _worksheet_ids(conn)
        if not ids:
            st.info("暂无 worksheet，请先在“worksheet.yaml 导入与校验”页面导入 sample_worksheet.yaml。")
            return
        selected = st.selectbox("worksheet_id", ids)
        if selected and st.button("生成学生卷 HTML"):
            path = save_worksheet_html(get_worksheet_bundle(conn, int(selected)))
            st.success(f"已输出：{path}")


def page_export_answer() -> None:
    st.header("答案页 HTML 导出")
    with _conn() as conn:
        ids = _worksheet_ids(conn)
        if not ids:
            st.info("暂无 worksheet，请先在“worksheet.yaml 导入与校验”页面导入 sample_worksheet.yaml。")
            return
        selected = st.selectbox("worksheet_id", ids)
        if selected and st.button("生成答案页 HTML"):
            path = save_answer_sheet_html(get_worksheet_bundle(conn, int(selected)))
            st.success(f"已输出：{path}")


def page_weekly_review() -> None:
    st.header("周复盘生成")
    if st.button("生成 weekly_review.md"):
        with _conn() as conn:
            path = generate_weekly_review(conn, load_student_profile(), date.today())
            st.success(f"已输出：{path}")


def page_extension_notes() -> None:
    st.header("系统扩展预留说明")
    st.markdown(
        """
        - v0.2：基础几何 SVG。
        - v0.3：PDF、趋势、能力雷达。
        - v0.4+：API 半自动、多用户服务端、客户端付费、Agent SDK 候选。
        - v0.1 已预留 provider、llm_call_logs、tenant_id、student_id、status、version 字段。
        """
    )


def page_worksheet_quality_checklist() -> None:
    st.header("出卷质量验收清单")
    st.markdown(
        """
        - 是否总题量适合本次训练目标。
        - 是否依据 confirmed 错因统计分配题型。
        - 是否覆盖最高频错因。
        - 是否没有让低频错因挤占核心训练。
        - 是否符合当前学生画像。
        - 是否基础/中等为主。
        - 是否浅奥题数量可控。
        - 是否 question_type 合法。
        - 是否 knowledge_point 合法或可解释 warning。
        - 是否 target_mistake_tag 只用代码。
        - 是否 difficulty 合法。
        - 是否没有 diagram。
        - 是否没有 svg_primitives。
        - 是否没有 Markdown。
        - 是否每题都有 question、answer、explanation。
        - 是否适合当前 v0.1.x HTML 打印。
        """
    )


PAGES = {
    "首页 / 项目说明": page_home,
    "学生画像查看": page_profile,
    "错因标签库": page_tags,
    "mistakes.yaml 导入与校验": page_import_mistakes,
    "错题记录列表": page_mistake_list,
    "错因统计": page_stats,
    "GPT 批改 Prompt 生成": page_marking_prompt,
    "GPT 出题 Prompt 生成": page_worksheet_prompt,
    "worksheet.yaml 导入与校验": page_import_worksheet,
    "学生卷 HTML 导出": page_export_student,
    "答案页 HTML 导出": page_export_answer,
    "周复盘生成": page_weekly_review,
    "出卷质量验收清单": page_worksheet_quality_checklist,
    "系统扩展预留说明": page_extension_notes,
}


def main() -> None:
    st.set_page_config(page_title="math_tutor_system v0.1.2", layout="wide")
    choice = st.sidebar.radio("页面", list(PAGES))
    PAGES[choice]()


if __name__ == "__main__":
    main()
