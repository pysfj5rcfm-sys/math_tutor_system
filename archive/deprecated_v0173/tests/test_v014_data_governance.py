from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from src.core.backup_export import backup_database, export_mistakes_csv, export_mistakes_yaml, export_worksheets_yaml
from src.core.data_governance import (
    batch_confirm_mistakes,
    batch_delete_mistakes,
    batch_revoke_mistakes,
    filter_mistakes,
)
from src.core.duplicate_guard import (
    detect_duplicate_mistakes,
    detect_duplicate_worksheet,
    mistake_hash,
    worksheet_hash,
)
from src.core.import_preview import (
    confirm_mistakes_dry_run,
    confirm_worksheet_dry_run,
    dry_run_mistakes_yaml,
    dry_run_worksheet_yaml,
)
from src.core.mistakes import import_mistakes_payload
from src.core.rule_registry import load_rule_registry
from src.core.sample_guard import detect_sample_data_warning
from src.core.worksheets import import_worksheet_payload
from src.db import init_db


ROOT = Path(__file__).resolve().parents[1]


def test_v014_pages_are_registered_in_workflow_order():
    import src.app as app

    pages = list(app.PAGES)
    assert "生成批改用 Prompt" in pages
    assert "生成出题用 Prompt" in pages
    assert "数据管理 / 备份 / 导出 / 重复检测" in pages
    assert "错因标签库" not in pages
    assert pages.index("生成批改用 Prompt") < pages.index("mistakes.yaml 导入与校验")
    assert pages.index("生成出题用 Prompt") < pages.index("worksheet.yaml 导入与校验")
    assert pages.index("出卷质量验收清单") < pages.index("生成批改用 Prompt")


def test_rule_registry_exposes_mistake_tags_for_merged_page():
    registry = load_rule_registry()
    tag = registry.get_mistake_tags(active_only=False)[0]
    assert {"code", "category", "name", "description", "typical_symptoms", "training_hint", "default_question_types", "active"}.issubset(tag)


def test_mistake_hash_is_stable_normalized_and_sensitive():
    row = _mistake(question_summary=" 小数四则混合运算 ")
    reordered = {
        "correct_answer_summary": row["correct_answer_summary"],
        "wrong_answer_summary": row["wrong_answer_summary"],
        "question_summary": "小数四则混合运算",
        "difficulty": row["difficulty"],
        "mistake_tag": row["mistake_tag"],
        "knowledge_point": row["knowledge_point"],
        "question_type": row["question_type"],
        "date": row["date"],
    }
    assert mistake_hash(row) == mistake_hash(reordered)
    assert mistake_hash(row) != mistake_hash(_mistake(question_summary="另一道题"))


def test_worksheet_hash_is_stable_and_sensitive():
    worksheet = _worksheet()
    assert worksheet_hash(worksheet) == worksheet_hash(_worksheet())
    changed = _worksheet()
    changed["worksheet"]["sections"][0]["questions"][0]["question"] = "9.9 ÷ 0.3"
    assert worksheet_hash(worksheet) != worksheet_hash(changed)


def test_duplicate_detection_finds_existing_mistake_and_worksheet(conn):
    import_mistakes_payload(conn, {"mistakes": [_mistake()]})
    mistake_scan = detect_duplicate_mistakes(conn, [_mistake()])
    assert mistake_scan["duplicate_count"] == 1
    assert mistake_scan["duplicates"][0]["existing_record_id"] == 1

    import_worksheet_payload(conn, _worksheet())
    worksheet_scan = detect_duplicate_worksheet(conn, _worksheet())
    assert worksheet_scan["is_duplicate"] is True
    assert worksheet_scan["matches"][0]["id"] == 1


def test_mistakes_dry_run_parse_validation_and_confirm_boundaries(conn):
    parse_preview = dry_run_mistakes_yaml(conn, "mistakes:\n  - date: [")
    assert parse_preview["can_import"] is False
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0

    invalid_preview = dry_run_mistakes_yaml(conn, yaml.safe_dump({"mistakes": [_mistake(mistake_tag="BAD")]}, allow_unicode=True))
    assert invalid_preview["can_import"] is False
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0

    preview = dry_run_mistakes_yaml(conn, yaml.safe_dump({"mistakes": [_mistake()]}, allow_unicode=True, sort_keys=False))
    assert preview["can_import"] is True
    assert preview["will_import_count"] == 1
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 0

    report = confirm_mistakes_dry_run(conn, preview)
    assert report["imported_count"] == 1
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 1


def test_worksheet_dry_run_parse_validation_duplicate_and_confirm_boundaries(conn):
    parse_preview = dry_run_worksheet_yaml(conn, "worksheet:\n  title: [")
    assert parse_preview["can_import"] is False
    assert conn.execute("SELECT COUNT(*) FROM worksheets").fetchone()[0] == 0

    invalid = _worksheet()
    invalid["worksheet"]["sections"][0]["questions"][0]["answer"] = ""
    invalid_preview = dry_run_worksheet_yaml(conn, yaml.safe_dump(invalid, allow_unicode=True, sort_keys=False))
    assert invalid_preview["can_import"] is False
    assert conn.execute("SELECT COUNT(*) FROM worksheets").fetchone()[0] == 0

    preview = dry_run_worksheet_yaml(conn, yaml.safe_dump(_worksheet(), allow_unicode=True, sort_keys=False))
    assert preview["can_import"] is True
    assert conn.execute("SELECT COUNT(*) FROM worksheets").fetchone()[0] == 0
    report, worksheet_id = confirm_worksheet_dry_run(conn, preview)
    assert worksheet_id == 1
    assert report["imported_count"] == 1

    duplicate_preview = dry_run_worksheet_yaml(conn, yaml.safe_dump(_worksheet(), allow_unicode=True, sort_keys=False))
    assert duplicate_preview["duplicate_count"] == 1
    report, skipped_id = confirm_worksheet_dry_run(conn, duplicate_preview)
    assert skipped_id is None
    assert report["skipped_duplicate_count"] == 1
    assert conn.execute("SELECT COUNT(*) FROM worksheets").fetchone()[0] == 1


def test_mistake_duplicate_default_does_not_silently_import(conn):
    first = dry_run_mistakes_yaml(conn, yaml.safe_dump({"mistakes": [_mistake()]}, allow_unicode=True, sort_keys=False))
    confirm_mistakes_dry_run(conn, first)
    duplicate = dry_run_mistakes_yaml(conn, yaml.safe_dump({"mistakes": [_mistake()]}, allow_unicode=True, sort_keys=False))
    assert duplicate["duplicate_count"] == 1
    report = confirm_mistakes_dry_run(conn, duplicate)
    assert report["imported_count"] == 0
    assert report["skipped_duplicate_count"] == 1
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 1


def test_batch_confirm_revoke_delete_and_filter(conn):
    import_mistakes_payload(conn, {"mistakes": [_mistake(source="GPT批改"), _mistake(question_summary="第二题", source="UAT测试")]})
    rows = filter_mistakes(conn, source="GPT批改")
    assert [row["question_summary"] for row in rows] == ["小数四则混合运算"]

    assert batch_confirm_mistakes(conn, []) == 0
    assert batch_confirm_mistakes(conn, [1, 2]) == 2
    assert conn.execute("SELECT COUNT(*) FROM mistakes WHERE status = 'confirmed'").fetchone()[0] == 2
    assert batch_revoke_mistakes(conn, [1]) == 1
    assert conn.execute("SELECT status FROM mistakes WHERE id = 1").fetchone()[0] == "needs_confirmation"
    with pytest.raises(ValueError):
        batch_delete_mistakes(conn, [2], confirm_delete=False)
    assert batch_delete_mistakes(conn, [2], confirm_delete=True) == 1
    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 1


def test_backup_and_exports_create_expected_files(conn, tmp_path):
    db_path = tmp_path / "data" / "edu_tutor.db"
    init_db(db_path)
    backup = backup_database(db_path, tmp_path / "backups", now=datetime(2026, 5, 29, 8, 9, 10))
    assert backup["ok"] is True
    assert backup["path"].name == "edu_tutor_20260529_080910.db"
    assert backup["path"].exists()

    missing = backup_database(tmp_path / "missing.db", tmp_path / "backups")
    assert missing["ok"] is False
    assert "database file does not exist" in missing["error"]

    import_mistakes_payload(conn, {"mistakes": [_mistake()]})
    import_worksheet_payload(conn, _worksheet())
    export_dir = tmp_path / "exports"
    csv_path = export_mistakes_csv(conn, export_dir, now=datetime(2026, 5, 29, 8, 9, 11))
    mistakes_yaml = export_mistakes_yaml(conn, export_dir, now=datetime(2026, 5, 29, 8, 9, 12))
    worksheets_yaml = export_worksheets_yaml(conn, export_dir, now=datetime(2026, 5, 29, 8, 9, 13))
    assert csv_path.name == "mistakes_20260529_080911.csv"
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "小数四则混合运算" in mistakes_yaml.read_text(encoding="utf-8")
    assert "五年级数学专项训练" in worksheets_yaml.read_text(encoding="utf-8")
    assert export_dir.exists()


def test_sample_warning_detects_file_name_and_source_without_blocking():
    by_file = detect_sample_data_warning(file_name="uat_valid_worksheet_v012.yaml")
    assert by_file["is_sample"] is True
    assert by_file["blocks_import"] is False

    by_source = detect_sample_data_warning(payload={"mistakes": [_mistake(source="UAT sample 测试")]})
    assert by_source["is_sample"] is True
    assert by_source["blocks_import"] is False


def _mistake(
    question_summary: str = "小数四则混合运算",
    mistake_tag: str = "C3",
    source: str = "GPT批改",
) -> dict:
    return {
        "date": "2026-05-27",
        "question_type": "递等式计算",
        "knowledge_point": "小数计算",
        "mistake_tag": mistake_tag,
        "difficulty": "基础",
        "question_summary": question_summary,
        "wrong_answer_summary": "小数点位置错误",
        "correct_answer_summary": "正确结果为 7.6",
        "training_needed": True,
        "source": source,
    }


def _worksheet() -> dict:
    return {
        "worksheet": {
            "title": "五年级数学专项训练",
            "date": "2026-05-27",
            "student_id": "daughter_grade5",
            "sections": [{
                "name": "一、递等式计算",
                "layout": "two_columns",
                "questions": [{
                    "question_type": "递等式计算",
                    "knowledge_point": "小数计算",
                    "target_mistake_tag": "C3",
                    "difficulty": "基础",
                    "question": "3.6 ÷ 0.9 + 2.4 × 1.5",
                    "answer": "7.6",
                    "explanation": "先算除法和乘法，再相加。",
                }],
            }],
        }
    }
