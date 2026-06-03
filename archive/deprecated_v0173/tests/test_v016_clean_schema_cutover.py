from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from src.core.backup_export import export_mistakes_csv, export_mistakes_yaml, export_worksheets_yaml
from src.core.display import difficulty_display, knowledge_point_display, mistake_tag_display, question_type_display
from src.core.import_preview import dry_run_mistakes_yaml, dry_run_worksheet_yaml
from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload
from src.core.schema_integrity import check_schema_integrity
from src.core.worksheets import confirm_worksheet_import, get_worksheet_bundle, preview_worksheet_payload
from src.db import DEFAULT_DB_PATH, SCHEMA_VERSION, create_tables, init_db, seed_mistake_tags, seed_schema_meta
from src.render.html_renderer import save_answer_sheet_html, save_worksheet_html


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"}


def test_clean_schema_has_meta_and_no_legacy_columns(tmp_path):
    db_path = tmp_path / "edu_tutor.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM schema_meta").fetchall()}
        assert meta["project_name"] == "edu_tutor_system"
        assert meta["schema_version"] == SCHEMA_VERSION
        assert meta["db_name"] == "edu_tutor.db"
        for table in ("mistakes", "worksheets", "worksheet_items"):
            columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            assert not (FORBIDDEN & columns)
        assert {"question_type_code", "knowledge_point_id", "primary_mistake_tag_code", "difficulty_code"}.issubset(
            {row["name"] for row in conn.execute("PRAGMA table_info(mistakes)").fetchall()}
        )


def test_legacy_db_is_archived_before_default_cutover(tmp_path, monkeypatch):
    import src.db as db

    legacy = tmp_path / "data" / "math_tutor.db"
    default = tmp_path / "data" / "edu_tutor.db"
    backups = tmp_path / "backups" / "pre_v016_clean_cutover"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy")
    monkeypatch.setattr(db, "LEGACY_DB_PATH", legacy)
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", default)
    monkeypatch.setattr(db, "PRE_V016_BACKUP_DIR", backups)
    archived = db.ensure_pre_v016_legacy_backup(default)
    assert archived is not None
    assert archived.name == "math_tutor.db"
    assert archived.read_bytes() == b"legacy"
    assert legacy.exists()


def test_normalize_legacy_input_to_canonical_without_writing_free_text(conn):
    payload = {
        "mistakes": [{
            "student_id": "uat_physics_g8",
            "subject_id": "physics",
            "grade_at_time": 8,
            "term_at_time": "八年级上",
            "curriculum_version_at_time": "cn_k12_2022",
            "date": "2026-06-01",
            "question_type": "物理计算",
            "knowledge_point": "速度",
            "mistake_tag": "物理公式选错",
            "difficulty": "基础",
            "question_summary": "速度公式选择错误",
        }]
    }
    preview = preview_mistakes_payload(conn, payload)
    assert preview["valid"] is True
    row = preview["valid_rows"][0]
    assert row["question_type_code"] == "physics_calculation"
    assert row["knowledge_point_id"] == "physics_g8_speed"
    assert row["primary_mistake_tag_code"] == "PHY_F1"
    assert row["difficulty_code"] == "basic"
    report = confirm_mistakes_import(conn, preview)
    assert report["imported_count"] == 1
    stored = dict(conn.execute("SELECT * FROM mistakes").fetchone())
    assert stored["knowledge_point_id"] == "physics_g8_speed"
    assert "速度" not in stored.values()


def test_unknown_knowledge_point_warning_does_not_store_free_text(conn):
    payload = {
        "mistakes": [{
            "student_id": "uat_chemistry_g9",
            "subject_id": "chemistry",
            "grade_at_time": 9,
            "date": "2026-06-01",
            "question_type_code": "chem_formula_writing",
            "knowledge_point": "速度",
            "primary_mistake_tag_code": "CHEM_F1",
            "difficulty_code": "basic",
            "question_summary": "跨学科知识点不应匹配",
        }]
    }
    preview = preview_mistakes_payload(conn, payload)
    assert any(w["code"] == "unknown_knowledge_point" for w in preview["validation"]["warnings"])
    confirm_mistakes_import(conn, preview)
    assert conn.execute("SELECT knowledge_point_id FROM mistakes").fetchone()[0] is None


def test_v016_samples_preview_confirm_and_html_export(conn, tmp_path):
    for name in [
        "uat_v016_math_g6_mistakes.yaml",
        "uat_v016_math_g7_mistakes.yaml",
        "uat_v016_physics_g8_mistakes.yaml",
        "uat_v016_chemistry_g9_mistakes.yaml",
    ]:
        payload = _sample(name)
        preview = preview_mistakes_payload(conn, payload)
        assert preview["valid"] is True, name
        assert preview["will_import_count"] >= 1
        confirm_mistakes_import(conn, preview)

    worksheet_ids = []
    for name in [
        "uat_v016_math_g6_worksheet.yaml",
        "uat_v016_math_g7_worksheet.yaml",
        "uat_v016_physics_g8_worksheet.yaml",
        "uat_v016_chemistry_g9_worksheet.yaml",
    ]:
        payload = _sample(name)
        preview = preview_worksheet_payload(conn, payload)
        assert preview["valid"] is True, name
        report, worksheet_id = confirm_worksheet_import(conn, preview)
        assert report["imported_count"] >= 2
        worksheet_ids.append(worksheet_id)
    bundle = get_worksheet_bundle(conn, int(worksheet_ids[-1]))
    assert save_worksheet_html(bundle, tmp_path).exists()
    assert save_answer_sheet_html(bundle, tmp_path).exists()


def test_display_and_export_use_code_plus_display(conn, tmp_path):
    preview = preview_mistakes_payload(conn, _sample("uat_v016_physics_g8_mistakes.yaml"))
    confirm_mistakes_import(conn, preview)
    w_preview = preview_worksheet_payload(conn, _sample("uat_v016_physics_g8_worksheet.yaml"))
    confirm_worksheet_import(conn, w_preview)
    assert question_type_display("physics_calculation") == "物理计算 (physics_calculation)"
    assert knowledge_point_display("physics_g8_speed", "physics", 8) == "速度 (physics_g8_speed)"
    assert mistake_tag_display("PHY_F1") == "物理公式选错 (PHY_F1)"
    assert difficulty_display("basic") == "基础 (basic)"
    csv_text = export_mistakes_csv(conn, tmp_path).read_text(encoding="utf-8-sig")
    mistakes_yaml = export_mistakes_yaml(conn, tmp_path).read_text(encoding="utf-8")
    worksheets_yaml = export_worksheets_yaml(conn, tmp_path).read_text(encoding="utf-8")
    assert "question_type_code,question_type_display" in csv_text
    assert "physics_calculation" in mistakes_yaml
    assert "question_type_display" in worksheets_yaml
    assert "question_type:" not in mistakes_yaml
    assert "difficulty:" not in worksheets_yaml


def test_schema_integrity_reports_errors_warnings_info(tmp_path):
    db_path = tmp_path / "edu_tutor.db"
    init_db(db_path)
    report = check_schema_integrity(db_path)
    assert set(report) == {"errors", "warnings", "info"}
    assert any(item["code"] == "invalid_db_path" for item in report["errors"])
    report = check_schema_integrity(DEFAULT_DB_PATH)
    assert set(report) == {"errors", "warnings", "info"}


def test_public_api_imports_remain_available():
    from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload
    from src.core.worksheets import confirm_worksheet_import, preview_worksheet_payload

    assert preview_mistakes_payload
    assert confirm_mistakes_import
    assert preview_worksheet_payload
    assert confirm_worksheet_import


def _sample(name: str) -> dict:
    return yaml.safe_load((ROOT / "samples" / name).read_text(encoding="utf-8"))
