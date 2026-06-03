from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from src.core.mistakes import import_mistakes_file
from src.core.worksheets import import_worksheet_file
from src.db import create_tables, ensure_output_dirs, init_db, seed_mistake_tags


ROOT = Path(__file__).resolve().parents[1]


def test_init_db_is_idempotent_and_preserves_user_data(tmp_path):
    db_path = tmp_path / "edu_tutor.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO mistakes (
                student_id, subject_id, grade_at_time, curriculum_version_at_time, date,
                question_type_code, knowledge_point_id, primary_mistake_tag_code,
                difficulty_code, question_summary, status, created_at, updated_at
            )
            VALUES (
                'daughter', 'math', 6, 'cn_k12_2022', '2026-05-27',
                'math_calculation', 'math_g6_fraction_operations', 'C3',
                'basic', '幂等测试', 'needs_confirmation',
                '2026-05-27T00:00:00', '2026-05-27T00:00:00'
            )
            """
        )
        conn.commit()

    init_db(db_path)
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        tag_count = conn.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0]
        mistake_count = conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0]
    assert tag_count >= 30
    assert mistake_count == 1


def test_invalid_mistakes_sample_reports_errors_and_warning(conn):
    report = import_mistakes_file(conn, ROOT / "samples" / "sample_invalid_mistakes.yaml")
    error_codes = {error["code"] for error in report["errors"]}
    warning_codes = {warning["code"] for warning in report["warnings"]}
    assert report["valid"] is False
    assert "invalid_mistake_tag" in error_codes
    assert "invalid_difficulty" in error_codes
    assert "invalid_question_type" in error_codes
    assert "empty_question_summary" in error_codes
    assert "unknown_knowledge_point" in warning_codes
    assert report["imported_count"] == 0
    assert report["skipped_count"] == 4


def test_invalid_worksheet_sample_reports_errors(conn):
    report, worksheet_id = import_worksheet_file(conn, ROOT / "samples" / "sample_invalid_worksheet.yaml")
    error_codes = {error["code"] for error in report["errors"]}
    assert report["valid"] is False
    assert worksheet_id is None
    assert "invalid_section_layout" in error_codes
    assert "missing_answer" in error_codes
    assert "empty_question" in error_codes
    assert "invalid_mistake_tag" in error_codes
    assert "invalid_difficulty" in error_codes


def test_outputs_directories_auto_create(tmp_path, monkeypatch):
    import src.db as db

    dirs = [
        tmp_path / "outputs" / "worksheets",
        tmp_path / "outputs" / "answer_sheets",
        tmp_path / "outputs" / "prompts",
        tmp_path / "outputs" / "reviews",
    ]
    monkeypatch.setattr(db, "OUTPUT_DIRS", dirs)
    ensure_output_dirs()
    assert all(path.exists() and path.is_dir() for path in dirs)


def test_streamlit_profile_page_source_does_not_use_st_yaml():
    app_source = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
    assert "st.yaml" not in app_source
    assert "yaml.safe_dump(active, allow_unicode=True, sort_keys=False)" in app_source
