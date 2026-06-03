from pathlib import Path

from src.core.worksheets import get_worksheet_bundle, import_worksheet_file, import_worksheet_payload


ROOT = Path(__file__).resolve().parents[1]


def test_sample_worksheet_can_import_and_links_items(conn):
    report, worksheet_id = import_worksheet_file(conn, ROOT / "samples" / "sample_worksheet.yaml")
    assert report["valid"] is True
    assert worksheet_id is not None
    item_count = conn.execute("SELECT COUNT(*) FROM worksheet_items WHERE worksheet_id = ?", (worksheet_id,)).fetchone()[0]
    assert item_count == 2
    bundle = get_worksheet_bundle(conn, worksheet_id)
    assert bundle["worksheet"]["id"] == worksheet_id
    assert sum(len(s["questions"]) for s in bundle["sections"]) == 2


def test_missing_answer_rejected(conn):
    payload = _worksheet()
    del payload["worksheet"]["sections"][0]["questions"][0]["answer"]
    report, worksheet_id = import_worksheet_payload(conn, payload)
    assert report["valid"] is False
    assert worksheet_id is None
    assert any(e["code"] == "missing_answer" for e in report["errors"])


def test_invalid_section_layout_rejected(conn):
    payload = _worksheet()
    payload["worksheet"]["sections"][0]["layout"] = "grid"
    report, worksheet_id = import_worksheet_payload(conn, payload)
    assert report["valid"] is False
    assert worksheet_id is None
    assert any(e["code"] == "invalid_section_layout" for e in report["errors"])


def test_empty_question_rejected(conn):
    payload = _worksheet()
    payload["worksheet"]["sections"][0]["questions"][0]["question"] = ""
    report, worksheet_id = import_worksheet_payload(conn, payload)
    assert report["valid"] is False
    assert worksheet_id is None
    assert any(e["code"] == "empty_question" for e in report["errors"])


def test_worksheet_unknown_knowledge_point_warns(conn):
    payload = _worksheet()
    payload["worksheet"]["sections"][0]["questions"][0]["knowledge_point"] = "未知知识点"
    report, worksheet_id = import_worksheet_payload(conn, payload)
    assert report["valid"] is True
    assert worksheet_id is not None
    assert any(w["code"] == "unknown_knowledge_point" for w in report["warnings"])


def _worksheet():
    return {
        "worksheet": {
            "title": "测试卷",
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
                    "question": "3.6 ÷ 0.9",
                    "answer": "4",
                    "explanation": "小数除法。",
                }],
            }],
        }
    }
