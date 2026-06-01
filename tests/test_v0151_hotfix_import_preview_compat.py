from __future__ import annotations

from pathlib import Path

import yaml

import src.app  # noqa: F401
import src.core.import_preview  # noqa: F401
from src.core.import_preview import (
    confirm_mistakes_dry_run,
    confirm_worksheet_dry_run,
    dry_run_mistakes_yaml,
    dry_run_worksheet_yaml,
)
from src.core.mistakes import confirm_mistakes_import, preview_mistakes_payload


ROOT = Path(__file__).resolve().parents[1]


def test_public_import_preview_compatibility_functions_are_importable():
    assert callable(preview_mistakes_payload)
    assert callable(confirm_mistakes_import)


def test_preview_mistakes_payload_keeps_dry_run_boundary_and_confirm_writes(conn):
    payload = yaml.safe_load((ROOT / "samples" / "sample_mistakes.yaml").read_text(encoding="utf-8"))
    preview = preview_mistakes_payload(conn, payload)

    assert preview["valid"] is True
    assert preview["will_import_count"] == 2
    assert preview["warning_count"] == 0
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0
    assert preview["valid_rows"][0]["student_id"] == "daughter"
    assert preview["valid_rows"][0]["subject_id"] == "math"
    assert preview["valid_rows"][0]["grade_at_time"] == 6
    assert preview["valid_rows"][0]["term_at_time"] == "六年级上"
    assert preview["valid_rows"][0]["curriculum_version_at_time"] == "cn_k12_2022"

    report = confirm_mistakes_import(conn, preview)
    assert report["imported_count"] == 2
    assert report["skipped_duplicate_count"] == 0
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 2


def test_import_preview_parse_validation_duplicate_and_worksheet_paths_still_work(conn):
    parse_preview = dry_run_mistakes_yaml(conn, "mistakes:\n  - date: [")
    assert parse_preview["can_import"] is False
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0

    invalid_payload = {"mistakes": [{
        "date": "2026-06-01",
        "question_type": "递等式计算",
        "knowledge_point": "小数计算",
        "mistake_tag": "BAD",
        "difficulty": "基础",
        "question_summary": "invalid",
    }]}
    invalid_preview = dry_run_mistakes_yaml(conn, yaml.safe_dump(invalid_payload, allow_unicode=True, sort_keys=False))
    assert invalid_preview["can_import"] is False
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0

    valid_text = (ROOT / "samples" / "sample_mistakes.yaml").read_text(encoding="utf-8")
    preview = dry_run_mistakes_yaml(conn, valid_text)
    assert preview["can_import"] is True
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0
    confirm_mistakes_dry_run(conn, preview)

    duplicate_preview = dry_run_mistakes_yaml(conn, valid_text)
    assert duplicate_preview["duplicate_count"] == 2
    duplicate_report = confirm_mistakes_dry_run(conn, duplicate_preview)
    assert duplicate_report["imported_count"] == 0
    assert duplicate_report["skipped_duplicate_count"] == 2
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 2

    worksheet_text = (ROOT / "samples" / "sample_worksheet.yaml").read_text(encoding="utf-8")
    worksheet_preview = dry_run_worksheet_yaml(conn, worksheet_text)
    assert worksheet_preview["can_import"] is True
    worksheet_report, worksheet_id = confirm_worksheet_dry_run(conn, worksheet_preview)
    assert worksheet_id is not None
    assert worksheet_report["imported_count"] == 2
