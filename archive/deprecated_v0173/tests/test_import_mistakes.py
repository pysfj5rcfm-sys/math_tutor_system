from pathlib import Path

from src.core.mistakes import import_mistakes_file, import_mistakes_payload


ROOT = Path(__file__).resolve().parents[1]


def test_sample_mistakes_can_import(conn):
    report = import_mistakes_file(conn, ROOT / "samples" / "sample_mistakes.yaml")
    assert report["valid"] is True
    assert report["imported_count"] == 2
    status = conn.execute("SELECT DISTINCT status FROM mistakes").fetchone()[0]
    assert status == "needs_confirmation"


def test_invalid_mistake_tag_rejected(conn):
    payload = {"mistakes": [_base_mistake() | {"mistake_tag": "BAD"}]}
    report = import_mistakes_payload(conn, payload)
    assert report["valid"] is False
    assert report["imported_count"] == 0
    assert report["errors"][0]["code"] == "invalid_mistake_tag"


def test_invalid_difficulty_rejected(conn):
    payload = {"mistakes": [_base_mistake() | {"difficulty": "很难"}]}
    report = import_mistakes_payload(conn, payload)
    assert report["valid"] is False
    assert report["imported_count"] == 0
    assert any(e["code"] == "invalid_difficulty" for e in report["errors"])


def test_unknown_knowledge_point_warns_but_imports_needs_confirmation(conn):
    payload = {"mistakes": [_base_mistake() | {"knowledge_point": "未知知识点"}]}
    report = import_mistakes_payload(conn, payload)
    assert report["valid"] is True
    assert report["warnings"][0]["code"] == "unknown_knowledge_point"
    row = conn.execute("SELECT status, knowledge_point_id FROM mistakes").fetchone()
    assert row["status"] == "needs_confirmation"
    assert row["knowledge_point_id"] in (None, "")


def _base_mistake():
    return {
        "date": "2026-05-27",
        "question_type": "递等式计算",
        "knowledge_point": "小数计算",
        "mistake_tag": "C3",
        "difficulty": "基础",
        "question_summary": "小数四则混合运算",
        "wrong_answer_summary": "小数点位置错误",
        "correct_answer_summary": "正确结果为 7.6",
        "training_needed": True,
    }
