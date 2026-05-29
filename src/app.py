from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import yaml

from src.core.backup_export import (
    DEFAULT_BACKUP_DIR,
    DEFAULT_EXPORT_DIR,
    backup_database,
    export_mistakes_csv,
    export_mistakes_yaml,
    export_worksheet_items_csv,
    export_worksheets_yaml,
)
from src.core.data_governance import (
    batch_confirm_mistakes,
    batch_delete_mistakes,
    batch_revoke_mistakes,
    data_overview,
    filter_mistakes,
    scan_mistake_duplicates,
    scan_worksheet_duplicates,
)
from src.core.import_preview import (
    confirm_mistakes_dry_run,
    confirm_worksheet_dry_run,
    dry_run_mistakes_yaml,
    dry_run_worksheet_yaml,
)
from src.core.mistake_tags import tags_as_dicts
from src.core.parse_report import format_parse_error, save_parse_report
from src.core.rule_registry import RuleRegistryError, load_rule_registry
from src.core.sample_guard import detect_sample_data_warning
from src.core.stats import stats_summary
from src.core.student_profile import load_student_profile
from src.core.validation_report import format_validation_report, save_validation_report
from src.core.worksheets import get_worksheet_bundle
from src.core.yaml_utils import YamlParseResult
from src.db import get_connection, init_db
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


def _sample_picker(prefix: str, default_name: str) -> tuple[str, str]:
    sample_files = sorted((ROOT / "samples").glob(f"*{prefix}*.yaml"))
    names = [path.name for path in sample_files]
    default_index = names.index(default_name) if default_name in names else 0
    selected = st.selectbox("选择样例文件", names, index=default_index)
    warning = detect_sample_data_warning(file_name=selected)
    _show_sample_warning(warning)
    return selected, (ROOT / "samples" / selected).read_text(encoding="utf-8")


def _show_sample_warning(warning: dict | None) -> None:
    if warning and warning.get("is_sample"):
        st.warning(warning.get("message") or "这是测试 / 样例数据，不建议导入正式学习库。")
        if warning.get("reasons"):
            st.caption("；".join(warning["reasons"]))


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _show_import_numbers(preview: dict) -> None:
    cols = st.columns(6)
    cols[0].metric("总数量", preview.get("total_count", 0))
    cols[1].metric("将导入", preview.get("will_import_count", 0))
    cols[2].metric("错误", preview.get("error_count", 0))
    cols[3].metric("warning", preview.get("warning_count", 0))
    cols[4].metric("重复", preview.get("duplicate_count", 0))
    cols[5].metric("将跳过", preview.get("will_skip_count", 0))


def _show_mistake_duplicate_preview(preview: dict) -> None:
    duplicates = (preview.get("duplicate_scan") or {}).get("duplicates") or []
    if not duplicates:
        st.success("未发现 exact duplicate。")
        return
    st.warning("发现重复记录，请先确认导入策略。")
    st.dataframe(duplicates, use_container_width=True)


def _show_worksheet_duplicate_preview(preview: dict) -> None:
    duplicate_scan = preview.get("duplicate_scan") or {}
    if not duplicate_scan.get("is_duplicate"):
        st.success("未发现重复 worksheet。")
        return
    st.warning("发现重复 worksheet，请先确认导入策略。")
    st.dataframe(duplicate_scan.get("matches", []), use_container_width=True)


def _show_parse_report_from_preview(source_type: str, preview: dict, original_text: str) -> None:
    parse = YamlParseResult(**preview["parse"])
    _show_parse_report(source_type, format_parse_error(parse, source_type, original_text), original_text)


def _mistake_filter_controls(conn, key_prefix: str) -> dict:
    registry = load_rule_registry()
    source_rows = conn.execute("SELECT DISTINCT source FROM mistakes WHERE source IS NOT NULL AND source != '' ORDER BY source").fetchall()
    sources = [row["source"] for row in source_rows]
    cols = st.columns(4)
    status = cols[0].selectbox("status", ["全部", "needs_confirmation", "confirmed"], key=f"{key_prefix}_status")
    source = cols[1].selectbox("source", ["全部"] + sources, key=f"{key_prefix}_source")
    mistake_tag = cols[2].selectbox("mistake_tag", ["全部"] + registry.get_mistake_tag_codes(), key=f"{key_prefix}_tag")
    question_type = cols[3].selectbox("question_type", ["全部"] + registry.get_question_type_codes(), key=f"{key_prefix}_type")
    cols = st.columns(4)
    knowledge_point = cols[0].selectbox("knowledge_point", ["全部"] + registry.get_knowledge_point_codes(), key=f"{key_prefix}_knowledge")
    difficulty = cols[1].selectbox("difficulty", ["全部"] + registry.get_difficulty_codes(), key=f"{key_prefix}_difficulty")
    date_from = cols[2].text_input("date from", value="", placeholder="YYYY-MM-DD", key=f"{key_prefix}_date_from")
    date_to = cols[3].text_input("date to", value="", placeholder="YYYY-MM-DD", key=f"{key_prefix}_date_to")
    return {
        "status": None if status == "全部" else status,
        "source": None if source == "全部" else source,
        "mistake_tag": None if mistake_tag == "全部" else mistake_tag,
        "question_type": None if question_type == "全部" else question_type,
        "knowledge_point": None if knowledge_point == "全部" else knowledge_point,
        "difficulty": None if difficulty == "全部" else difficulty,
        "date_from": date_from or None,
        "date_to": date_to or None,
    }


def _select_mistake_ids(rows: list[dict], key: str) -> list[int]:
    ids = [int(row["id"]) for row in rows]
    if not ids:
        return []
    select_all = st.checkbox("全选当前筛选结果", key=f"{key}_all")
    if select_all:
        st.caption(f"已选择当前筛选结果中的 {len(ids)} 条。")
        return ids
    return [int(value) for value in st.multiselect("选择记录 id", ids, key=key)]


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
    st.title("math_tutor_system v0.1.4")
    st.write("GPT 协作型家庭教培教务系统：本地负责记录、校验、统计、Prompt 和 HTML 排版。")
    st.info("v0.1.4 聚焦 Workflow UX + Data Governance：导入前预览、重复检测、批量治理、备份导出；仍不接 API、不做 OCR、不自动批改、不做几何 SVG。")


def page_profile() -> None:
    st.header("学生画像查看")
    profile = load_student_profile()
    st.code(
        yaml.safe_dump(profile, allow_unicode=True, sort_keys=False),
        language="yaml",
    )


def page_tags() -> None:
    st.header("错因标签库")
    st.info("v0.1.4 起，错因标签库已合并至“规则库查看”。下方显示合并后的规则库视图。")
    page_rule_registry()


def page_rule_registry() -> None:
    st.header("规则库查看")
    try:
        registry = load_rule_registry(force_reload=True)
        result = registry.validate_config()
    except RuleRegistryError as exc:
        st.error("Rule Registry 配置加载失败")
        st.code(str(exc), language="text")
        return

    if result["valid"]:
        st.success("Rule Registry 加载成功，配置校验通过。")
    else:
        st.error("Rule Registry 配置校验失败。")
    if result["errors"]:
        st.subheader("配置错误")
        st.write(result["errors"])
    if result["warnings"]:
        st.subheader("配置提醒")
        st.write(result["warnings"])

    st.subheader("question_types")
    st.dataframe(registry.get_question_types(active_only=False), use_container_width=True)

    st.subheader("knowledge_points")
    st.dataframe(registry.get_knowledge_points(active_only=False), use_container_width=True)

    st.subheader("difficulty_levels")
    st.dataframe(registry.get_difficulty_levels(active_only=False), use_container_width=True)

    st.subheader("mistake_tags")
    registry_tags = registry.get_mistake_tags(active_only=False)
    with _conn() as conn:
        db_count = conn.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0]
    cols = st.columns(3)
    cols[0].metric("registry mistake_tags", len(registry_tags))
    cols[1].metric("database mistake_tags", db_count)
    cols[2].metric("数量一致", "是" if len(registry_tags) == db_count else "否")
    if len(registry_tags) != db_count:
        st.warning("registry 与数据库 mistake_tags 数量不一致。请检查配置和 seed 状态；系统不会自动删除已有数据。")
    tag_rows = []
    for tag in registry_tags:
        symptoms = tag.get("typical_symptoms", "")
        tag_rows.append({
            "code": tag.get("code", ""),
            "category": tag.get("category", ""),
            "name": tag.get("name", ""),
            "description": tag.get("description", ""),
            "typical_symptoms": "；".join(symptoms) if isinstance(symptoms, list) else symptoms,
            "training_hint": tag.get("training_hint", ""),
            "default_question_types": tag.get("default_question_types", []),
            "active": tag.get("active", True),
        })
    st.dataframe(tag_rows, use_container_width=True)

    st.subheader("alias_mappings")
    alias_rows = []
    for group, values in registry.alias_mappings.items():
        for alias, canonical in values.items():
            alias_rows.append({"group": group, "alias": alias, "canonical": canonical})
    st.dataframe(alias_rows, use_container_width=True)

    st.subheader("worksheet_policies")
    policy_rows = []
    for name in registry.list_policies():
        policy = registry.get_policy(name) or {}
        policy_rows.append({
            "name": name,
            "description": policy.get("description", ""),
            "max_questions": policy.get("max_questions"),
            "sections": yaml.safe_dump(policy.get("sections", []), allow_unicode=True, sort_keys=False),
        })
    st.dataframe(policy_rows, use_container_width=True)
    with st.expander("worksheet_policy 原始 YAML"):
        st.code(registry.render_worksheet_policies_for_prompt(), language="yaml")


def page_import_mistakes() -> None:
    st.header("mistakes.yaml 导入与校验")
    st.caption("先校验 / 预览，再确认导入。parse fail 或 business validation error 都不会写库。")
    sample_name, sample = _sample_picker("mistakes", "sample_mistakes.yaml")
    text = st.text_area("YAML", value=sample, height=320)
    text_hash = _text_hash(text)
    if st.button("校验 / 预览 mistakes.yaml"):
        with _conn() as conn:
            preview = dry_run_mistakes_yaml(conn, text, file_name=sample_name)
        preview["text_hash"] = text_hash
        st.session_state["mistakes_import_preview"] = preview

    preview = st.session_state.get("mistakes_import_preview")
    if not preview:
        return
    if preview.get("text_hash") != text_hash:
        st.info("YAML 内容已变化，请重新点击“校验 / 预览”。")
        return
    _show_sample_warning(preview.get("sample_warning"))
    if not preview.get("parse", {}).get("ok"):
        _show_parse_report_from_preview("mistakes", preview, text)
        return
    st.success("解析状态：YAML parse 通过。")
    _show_validation_report(
        "mistakes",
        format_validation_report(preview["validation"], "mistakes", preview.get("payload") or {}, text),
        text,
    )
    _show_import_numbers(preview)
    _show_mistake_duplicate_preview(preview)
    if not preview.get("valid"):
        st.error("存在业务校验 error，不能确认导入。")
        return

    strategy_label = st.radio(
        "重复记录处理",
        ["只导入非重复（推荐）", "跳过全部重复（只导入新记录）", "仍然导入全部", "取消导入"],
        index=0,
    )
    strategy_map = {
        "只导入非重复（推荐）": "only_new",
        "跳过全部重复（只导入新记录）": "skip_all_duplicates",
        "仍然导入全部": "import_all",
        "取消导入": "cancel",
    }
    if st.button("确认导入 mistakes.yaml"):
        with _conn() as conn:
            report = confirm_mistakes_dry_run(conn, preview, duplicate_strategy=strategy_map[strategy_label])
        st.success(
            f"导入完成：imported_count={report.get('imported_count', 0)}，"
            f"duplicate_count={report.get('duplicate_count', 0)}，"
            f"skipped_duplicate_count={report.get('skipped_duplicate_count', 0)}"
        )
        st.session_state.pop("mistakes_import_preview", None)


def page_mistake_list() -> None:
    st.header("错题记录列表")
    with _conn() as conn:
        filters = _mistake_filter_controls(conn, "mistake_list")
        rows = filter_mistakes(conn, **filters)
        st.dataframe(rows, use_container_width=True)
        selected_ids = _select_mistake_ids(rows, "mistake_list_ids")
        cols = st.columns(2)
        if cols[0].button("批量确认 selected needs_confirmation → confirmed"):
            count = batch_confirm_mistakes(conn, selected_ids)
            st.success(f"已确认 {count} 条。")
            st.rerun()
        if cols[1].button("批量撤销 selected confirmed → needs_confirmation"):
            count = batch_revoke_mistakes(conn, selected_ids)
            st.success(f"已撤销 {count} 条。")
            st.rerun()


def page_stats() -> None:
    st.header("错因统计")
    include = st.checkbox("include_unconfirmed 调试选项", value=False)
    with _conn() as conn:
        summary = stats_summary(conn, include_unconfirmed=include, today=date.today())
        if not include and not summary["recent_7_days"] and not summary["recent_30_days"]:
            st.info("暂无 confirmed 错题记录。请先导入 mistakes.yaml，并在“错题记录列表”中确认记录。")
        st.json(summary)


def page_marking_prompt() -> None:
    st.header("生成批改用 Prompt")
    prompt = build_marking_prompt(load_student_profile(), tags_as_dicts())
    st.text_area("Prompt", prompt, height=420)
    if st.button("保存到 outputs/prompts"):
        path = save_marking_prompt(prompt)
        st.success(f"已保存：{path}")


def page_worksheet_prompt() -> None:
    st.header("生成出题用 Prompt")
    with _conn() as conn:
        stats = stats_summary(conn, include_unconfirmed=False, today=date.today())
    prompt = build_worksheet_prompt(load_student_profile(), stats, tags_as_dicts())
    st.text_area("Prompt", prompt, height=420)
    if st.button("保存到 outputs/prompts"):
        path = save_worksheet_prompt(prompt)
        st.success(f"已保存：{path}")


def page_import_worksheet() -> None:
    st.header("worksheet.yaml 导入与校验")
    st.caption("先校验 / 预览，再确认导入。parse fail 或 business validation error 都不会写库。")
    sample_name, sample = _sample_picker("worksheet", "sample_worksheet.yaml")
    text = st.text_area("YAML", value=sample, height=360)
    text_hash = _text_hash(text)
    if st.button("校验 / 预览 worksheet.yaml"):
        with _conn() as conn:
            preview = dry_run_worksheet_yaml(conn, text, file_name=sample_name)
        preview["text_hash"] = text_hash
        st.session_state["worksheet_import_preview"] = preview

    preview = st.session_state.get("worksheet_import_preview")
    if not preview:
        return
    if preview.get("text_hash") != text_hash:
        st.info("YAML 内容已变化，请重新点击“校验 / 预览”。")
        return
    _show_sample_warning(preview.get("sample_warning"))
    if not preview.get("parse", {}).get("ok"):
        _show_parse_report_from_preview("worksheet", preview, text)
        return
    st.success("解析状态：YAML parse 通过。")
    _show_validation_report(
        "worksheet",
        format_validation_report(preview["validation"], "worksheet", preview.get("payload") or {}, text),
        text,
    )
    _show_import_numbers(preview)
    _show_worksheet_duplicate_preview(preview)
    if not preview.get("valid"):
        st.error("存在业务校验 error，不能确认导入。")
        return

    strategy_label = st.radio(
        "重复 worksheet 处理",
        ["跳过导入（推荐）", "仍然导入", "取消"],
        index=0,
    )
    strategy_map = {
        "跳过导入（推荐）": "skip_duplicate",
        "仍然导入": "import_all",
        "取消": "cancel",
    }
    if st.button("确认导入 worksheet.yaml"):
        with _conn() as conn:
            report, worksheet_id = confirm_worksheet_dry_run(conn, preview, duplicate_strategy=strategy_map[strategy_label])
        if worksheet_id:
            st.success(f"导入完成：worksheet_id={worksheet_id}，题目数={report.get('imported_count', 0)}")
        else:
            st.warning(
                f"未生成新 worksheet：duplicate_count={report.get('duplicate_count', 0)}，"
                f"skipped_duplicate_count={report.get('skipped_duplicate_count', 0)}"
            )
        st.session_state.pop("worksheet_import_preview", None)


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


def page_data_management() -> None:
    st.header("数据管理 / 备份 / 导出 / 重复检测")
    with _conn() as conn:
        st.subheader("数据概览")
        overview = data_overview(conn, DEFAULT_BACKUP_DIR)
        cols = st.columns(6)
        cols[0].metric("mistakes", overview["mistakes_total"])
        cols[1].metric("needs_confirmation", overview["needs_confirmation"])
        cols[2].metric("confirmed", overview["confirmed"])
        cols[3].metric("worksheets", overview["worksheets_total"])
        cols[4].metric("worksheet_items", overview["worksheet_items_total"])
        cols[5].metric("最近 7 天导入", overview["recent_imports_7_days"])
        if overview["recent_backups"]:
            st.caption("最近备份文件：" + "；".join(overview["recent_backups"]))
        else:
            st.caption("暂无备份文件。")

        st.subheader("筛选错因记录")
        filters = _mistake_filter_controls(conn, "data_management")
        rows = filter_mistakes(conn, **filters)
        st.dataframe(rows, use_container_width=True)
        selected_ids = _select_mistake_ids(rows, "data_management_ids")

        st.subheader("批量操作")
        cols = st.columns(3)
        if cols[0].button("批量确认"):
            count = batch_confirm_mistakes(conn, selected_ids)
            st.success(f"影响 {count} 条。")
            st.rerun()
        if cols[1].button("批量撤销"):
            count = batch_revoke_mistakes(conn, selected_ids)
            st.success(f"影响 {count} 条。")
            st.rerun()
        delete_confirmed = st.checkbox("我已备份数据库，并确认删除 selected records")
        if cols[2].button("批量删除"):
            st.warning("建议先备份数据库；删除不可自动恢复。")
            try:
                count = batch_delete_mistakes(conn, selected_ids, confirm_delete=delete_confirmed)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"已删除 {count} 条。")
                st.rerun()

        st.subheader("重复检测")
        cols = st.columns(2)
        if cols[0].button("扫描重复 mistakes"):
            groups = scan_mistake_duplicates(conn)
            if groups:
                st.warning(f"发现 {len(groups)} 个 exact duplicate group。系统不会自动删除，请筛选后手动批量处理。")
                for group in groups:
                    st.write(f"hash={group['hash']}，记录数={group['count']}")
                    st.dataframe(group["records"], use_container_width=True)
            else:
                st.success("未发现重复 mistakes。")
        if cols[1].button("扫描重复 worksheets"):
            groups = scan_worksheet_duplicates(conn)
            if groups:
                st.warning(f"发现 {len(groups)} 个重复 worksheet group。系统不会自动删除。")
                for group in groups:
                    st.write(f"hash={group['hash']}，记录数={group['count']}")
                    st.dataframe(group["worksheets"], use_container_width=True)
            else:
                st.success("未发现重复 worksheets。")

        st.subheader("数据备份")
        if st.button("一键备份 data/math_tutor.db"):
            result = backup_database()
            if result["ok"]:
                st.success(f"备份成功：{result['path']}")
            else:
                st.error(result["error"])
        recent = data_overview(conn, DEFAULT_BACKUP_DIR)["recent_backups"]
        if recent:
            st.write("最近备份：")
            st.write(recent)

        st.subheader("数据导出")
        cols = st.columns(4)
        if cols[0].button("导出 mistakes CSV"):
            st.success(f"已导出：{export_mistakes_csv(conn)}")
        if cols[1].button("导出 mistakes YAML"):
            st.success(f"已导出：{export_mistakes_yaml(conn)}")
        if cols[2].button("导出 worksheets YAML"):
            st.success(f"已导出：{export_worksheets_yaml(conn)}")
        if cols[3].button("导出 worksheet_items CSV"):
            st.success(f"已导出：{export_worksheet_items_csv(conn)}")
        st.caption(f"导出目录：{DEFAULT_EXPORT_DIR}")


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
    try:
        registry = load_rule_registry()
        policies = registry.list_policies()
    except RuleRegistryError as exc:
        st.error("无法加载 worksheet policies，请先修复 Rule Registry 配置。")
        st.code(str(exc), language="text")
        policies = []
    if policies:
        selected_policy = st.selectbox("可选 worksheet_policy（用于人工核对，不是全局硬规则）", ["未指定"] + policies)
        if selected_policy != "未指定":
            st.code(yaml.safe_dump(registry.get_policy(selected_policy), allow_unicode=True, sort_keys=False), language="yaml")
    st.markdown(
        """
        - 是否依据 confirmed 错因统计分配题型。
        - 是否覆盖最高频错因。
        - 是否没有让低频错因挤占核心训练。
        - 是否符合当前学生画像。
        - 是否 question_type 合法。
        - 是否 knowledge_point 合法或可解释 warning。
        - 是否 target_mistake_tag 只用 active mistake_tag code。
        - 是否 difficulty 合法。
        - 是否没有 diagram。
        - 是否没有 svg_primitives。
        - 是否没有 Markdown。
        - 是否每题都有 question、answer、explanation。
        - 是否适合当前 v0.1.x HTML 打印。
        - 如果选择了某个 worksheet_policy，是否大致符合该 policy 的题型与数量范围。
        """
    )


PAGES = {
    "首页 / 使用说明": page_home,
    "学生画像查看": page_profile,
    "规则库查看": page_rule_registry,
    "出卷质量验收清单": page_worksheet_quality_checklist,
    "生成批改用 Prompt": page_marking_prompt,
    "mistakes.yaml 导入与校验": page_import_mistakes,
    "错题记录列表": page_mistake_list,
    "错因统计": page_stats,
    "生成出题用 Prompt": page_worksheet_prompt,
    "worksheet.yaml 导入与校验": page_import_worksheet,
    "学生卷 HTML 导出": page_export_student,
    "答案页 HTML 导出": page_export_answer,
    "周复盘生成": page_weekly_review,
    "数据管理 / 备份 / 导出 / 重复检测": page_data_management,
    "系统扩展预留说明": page_extension_notes,
}


def main() -> None:
    st.set_page_config(page_title="math_tutor_system v0.1.4", layout="wide")
    choice = st.sidebar.radio("页面", list(PAGES))
    PAGES[choice]()


if __name__ == "__main__":
    main()
