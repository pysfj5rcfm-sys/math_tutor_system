from __future__ import annotations

import sqlite3
from pathlib import Path

from src.core.schema_integrity import check_schema_integrity
from src.db import create_tables, init_db, seed_mistake_tags


OLD_BARE_TAGS = {"C1", "C2", "C3", "F3", "R4", "M2", "U1", "G1"}
NEW_TAGS = {"MATH_SIGN_RULE_ERROR", "MATH_EQUALITY_RELATION_ERROR", "GEN_R4", "GEN_M2", "CHN_EVD_1", "ENG_GRAM_1"}


def test_db_seed_uses_no_legacy_namespaced_tags(conn: sqlite3.Connection):
    codes = {row["code"] for row in conn.execute("SELECT code FROM mistake_tags").fetchall()}

    assert NEW_TAGS <= codes
    assert OLD_BARE_TAGS.isdisjoint(codes)

    before = conn.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0]
    seed_mistake_tags(conn)
    after = conn.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0]
    assert before == after


def test_init_db_sets_registry_meta_without_changing_schema(tmp_path: Path):
    db_path = tmp_path / "edu_tutor.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        meta = dict(conn.execute("SELECT key, value FROM schema_meta").fetchall())
        codes = {row[0] for row in conn.execute("SELECT code FROM mistake_tags").fetchall()}
    finally:
        conn.close()

    assert meta["schema_version"] == "0.1.7"
    assert meta["project_name"] == "edu_tutor_system"
    assert meta["db_name"] == "edu_tutor.db"
    assert meta["registry_version"] == "0.1.8.1"
    assert meta["registry_mode"] == "no_legacy"
    assert NEW_TAGS <= codes
    assert OLD_BARE_TAGS.isdisjoint(codes)


def test_schema_integrity_reports_clean_default_db_after_init(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "edu_tutor.db"
    init_db(db_path)
    monkeypatch.setattr("src.core.schema_integrity.DEFAULT_DB_PATH", db_path)
    report = check_schema_integrity(db_path)

    assert report["errors"] == []
    assert not any(item["code"] == "unknown_difficulty" for item in report["warnings"])


def test_clean_schema_tables_do_not_have_old_free_text_columns(conn: sqlite3.Connection):
    for table in ("mistakes", "worksheets", "worksheet_items"):
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        assert {"question_type", "knowledge_point", "mistake_tag", "target_mistake_tag", "difficulty"}.isdisjoint(columns)
