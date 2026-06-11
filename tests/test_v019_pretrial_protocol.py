from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import yaml

from src.core.import_preview import dry_run_mistakes_yaml, dry_run_worksheet_yaml
from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload
from src.core.target_priority_light import build_target_priority_light
from src.core.worksheets import confirm_worksheet_import, get_worksheet_bundle, preview_worksheet_payload
from src.db import migrate_schema
from src.render.html_renderer import render_answer_sheet_html, render_worksheet_html
from src.prompts.marking_prompt import build_marking_prompt
from src.prompts.worksheet_prompt import build_worksheet_prompt


ROOT = Path(__file__).resolve().parents[1]


def _load_sample(name: str) -> dict:
    return yaml.safe_load((ROOT / "samples" / name).read_text(encoding="utf-8"))


def test_v019_migration_adds_pretrial_columns_and_is_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            grade_at_time INTEGER NOT NULL,
            term_at_time TEXT,
            curriculum_version_at_time TEXT NOT NULL,
            textbook_version_at_time TEXT,
            date TEXT,
            question_type_code TEXT NOT NULL,
            knowledge_point_id TEXT,
            primary_mistake_tag_code TEXT NOT NULL,
            difficulty_code TEXT NOT NULL,
            question_summary TEXT NOT NULL,
            wrong_answer_summary TEXT,
            correct_answer_summary TEXT,
            training_needed INTEGER
        );
        CREATE TABLE worksheet_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worksheet_id INTEGER NOT NULL,
            question_type_code TEXT NOT NULL,
            knowledge_point_id TEXT,
            target_mistake_tag_code TEXT,
            difficulty_code TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        );
        INSERT INTO mistakes (
            student_id, subject_id, grade_at_time, curriculum_version_at_time,
            date, question_type_code, primary_mistake_tag_code,
            difficulty_code, question_summary
        )
        VALUES (
            'daughter', 'math', 6, 'cn_k12_2022',
            '2026-06-05', 'math_calculation', 'MATH_SIGN_RULE_ERROR',
            'basic', 'old row remains'
        );
        """
    )

    migrate_schema(conn)
    migrate_schema(conn)

    mistake_columns = {row["name"] for row in conn.execute("PRAGMA table_info(mistakes)").fetchall()}
    worksheet_columns = {row["name"] for row in conn.execute("PRAGMA table_info(worksheet_items)").fetchall()}
    assert {
        "diagnosis_confidence",
        "needs_human_review",
        "secondary_mistake_tags_json",
        "diagnosis_evidence_json",
        "alternative_diagnoses_json",
    } <= mistake_columns
    assert {
        "primary_target_id",
        "question_role",
        "teaching_purpose",
        "expected_error_mechanism",
    } <= worksheet_columns
    assert conn.execute("SELECT question_summary FROM mistakes").fetchone()[0] == "old row remains"
    conn.close()


def test_v019_samples_preview_and_import_store_evidence_and_roles(conn: sqlite3.Connection):
    mistakes = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")
    worksheet = _load_sample("uat_v019_pretrial_worksheet_roles.yaml")

    mistakes_preview = preview_mistakes_payload(conn, mistakes)
    worksheet_preview = preview_worksheet_payload(conn, worksheet)
    assert mistakes_preview["valid"], mistakes_preview["validation"]
    assert worksheet_preview["valid"], worksheet_preview["validation"]
    assert mistakes_preview["valid_rows"][0]["secondary_mistake_tags"] == ["MATH_CALCULATION_EXECUTION_ERROR"]
    assert worksheet_preview["worksheet"]["sections"][0]["questions"][0]["question_role"] == "repair"

    confirm_mistakes_import(conn, mistakes_preview, duplicate_strategy="import_all")
    _, worksheet_id = confirm_worksheet_import(conn, worksheet_preview, duplicate_strategy="import_all")

    row = conn.execute("SELECT * FROM mistakes ORDER BY id LIMIT 1").fetchone()
    assert row["diagnosis_confidence"] == 0.86
    assert row["needs_human_review"] == 0
    assert json.loads(row["secondary_mistake_tags_json"]) == ["MATH_CALCULATION_EXECUTION_ERROR"]
    assert json.loads(row["diagnosis_evidence_json"])["why_primary"]
    assert json.loads(row["alternative_diagnoses_json"])[0]["code"] == "MATH_CONDITION_JUDGEMENT_ERROR"

    item = conn.execute("SELECT * FROM worksheet_items ORDER BY id LIMIT 1").fetchone()
    assert item["primary_target_id"] == "math_g6a_rational_add_different_sign::MATH_SIGN_RULE_ERROR"
    assert item["question_role"] == "repair"
    assert item["teaching_purpose"]
    assert item["expected_error_mechanism"]

    bundle = get_worksheet_bundle(conn, int(worksheet_id))
    student_html = render_worksheet_html(bundle)
    answer_html = render_answer_sheet_html(bundle)
    assert "teaching_purpose" not in student_html
    assert "直接修复异号相加" not in student_html
    assert "Role: repair" in answer_html
    assert "直接修复异号相加" in answer_html


def test_v019_mistake_validation_rejects_bad_optional_fields(conn: sqlite3.Connection):
    base = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")

    too_many = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")
    too_many["mistakes"][0]["secondary_mistake_tags"] = [
        "MATH_SIGN_RULE_ERROR",
        "MATH_CALCULATION_EXECUTION_ERROR",
        "MATH_RULE_APPLICATION_ERROR",
        "MATH_SYMBOL_NOTATION_ERROR",
    ]
    preview = preview_mistakes_payload(conn, too_many)
    assert not preview["valid"]
    assert any(item["code"] == "too_many_secondary_mistake_tags" for item in preview["validation"]["errors"])

    unknown_secondary = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")
    unknown_secondary["mistakes"][0]["secondary_mistake_tags"] = ["UNKNOWN_CODE"]
    preview = preview_mistakes_payload(conn, unknown_secondary)
    assert not preview["valid"]
    assert any(item["code"] == "invalid_secondary_mistake_tag" for item in preview["validation"]["errors"])

    old_secondary = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")
    old_secondary["mistakes"][0]["secondary_mistake_tags"] = ["MATH_C3"]
    preview = preview_mistakes_payload(conn, old_secondary)
    assert not preview["valid"]
    assert any(item["code"] == "invalid_secondary_mistake_tag" for item in preview["validation"]["errors"])

    bad_alt = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")
    bad_alt["mistakes"][0]["alternative_diagnoses"] = [{"code": "UNKNOWN_CODE", "confidence": 0.2}]
    preview = preview_mistakes_payload(conn, bad_alt)
    assert not preview["valid"]
    assert any(item["code"] == "invalid_alternative_diagnosis_code" for item in preview["validation"]["errors"])

    bad_confidence = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")
    bad_confidence["mistakes"][0]["diagnosis_confidence"] = 1.2
    preview = preview_mistakes_payload(conn, bad_confidence)
    assert not preview["valid"]
    assert any(item["code"] == "diagnosis_confidence_out_of_range" for item in preview["validation"]["errors"])

    base["mistakes"][0]["needs_human_review"] = "true"
    preview = preview_mistakes_payload(conn, base)
    assert preview["valid"], preview["validation"]
    assert preview["valid_rows"][0]["needs_human_review"] is True


def test_v019_worksheet_role_validation(conn: sqlite3.Connection):
    good = dry_run_worksheet_yaml(
        conn,
        (ROOT / "samples" / "uat_v019_pretrial_worksheet_roles.yaml").read_text(encoding="utf-8"),
        "uat_v019_pretrial_worksheet_roles.yaml",
    )
    assert good["can_import"], good["validation"]

    payload = _load_sample("uat_v019_pretrial_worksheet_roles.yaml")
    payload["worksheet"]["sections"][0]["questions"][0]["question_role"] = "drill"
    preview = preview_worksheet_payload(conn, payload)
    assert not preview["valid"]
    assert any(item["code"] == "invalid_question_role" for item in preview["validation"]["errors"])

    payload = _load_sample("uat_v019_pretrial_worksheet_roles.yaml")
    payload["worksheet"]["sections"][0]["questions"][0]["primary_target_id"] = ""
    preview = preview_worksheet_payload(conn, payload)
    assert preview["valid"], preview["validation"]
    assert preview["worksheet"]["sections"][0]["questions"][0]["primary_target_id"] == ""


def test_v019_prompt_protocol_is_present_and_math_prompt_is_clean():
    marking_prompt = build_marking_prompt({"student_id": "daughter"}, subject_id="math")
    worksheet_prompt = build_worksheet_prompt(
        {"student_id": "daughter"},
        {
            "recent_7_days": [],
            "recent_30_days": [],
            "mistake_tag_by_question_type": [],
            "mistake_tag_by_knowledge_point": [],
            "target_matrix": {"items": []},
            "target_priority_light": {"items": []},
        },
        subject_id="math",
    )

    assert "diagnosis_evidence" in marking_prompt
    assert "secondary_mistake_tags" in marking_prompt
    assert "primary_mistake_tag_code" in marking_prompt
    assert "repair" in worksheet_prompt
    assert "variant" in worksheet_prompt
    assert "transfer" in worksheet_prompt
    assert "target_priority_light" in worksheet_prompt
    for forbidden in ("MATH_C3", "MATH_F3", "GEN_R4", "GEN_M2", "YV-"):
        assert forbidden not in marking_prompt
        assert forbidden not in worksheet_prompt


def test_v019_target_priority_light_uses_confirmed_primary_only(conn: sqlite3.Connection):
    payload = _load_sample("uat_v019_pretrial_mistakes_evidence.yaml")
    preview = preview_mistakes_payload(conn, payload)
    confirm_mistakes_import(conn, preview, duplicate_strategy="import_all")
    conn.execute("UPDATE mistakes SET status = 'confirmed'")
    conn.commit()

    priority = build_target_priority_light(conn, "daughter", "math", 6, today="2026-06-11")

    assert priority["protocol"] == "v0.1.9-pretrial target_priority_light"
    assert priority["items"][0]["target_id"]
    assert {item["priority_band"] for item in priority["items"]} <= {"high", "medium", "low"}
    assert all("mistake_tag_code" in item for item in priority["items"])


def test_v019_dry_run_mistakes_with_diagnosis_evidence(conn: sqlite3.Connection):
    preview = dry_run_mistakes_yaml(
        conn,
        (ROOT / "samples" / "uat_v019_pretrial_mistakes_evidence.yaml").read_text(encoding="utf-8"),
        "uat_v019_pretrial_mistakes_evidence.yaml",
    )
    assert preview["can_import"], preview["validation"]
