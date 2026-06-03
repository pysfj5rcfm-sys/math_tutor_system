from pathlib import Path

from src.core.worksheets import get_worksheet_bundle, import_worksheet_file
from src.render.html_renderer import save_answer_sheet_html, save_worksheet_html


ROOT = Path(__file__).resolve().parents[1]


def test_html_student_and_answer_exports_are_separate(conn, tmp_path):
    _, worksheet_id = import_worksheet_file(conn, ROOT / "samples" / "sample_worksheet.yaml")
    bundle = get_worksheet_bundle(conn, worksheet_id)
    worksheet_path = save_worksheet_html(bundle, tmp_path / "worksheets")
    answer_path = save_answer_sheet_html(bundle, tmp_path / "answer_sheets")
    assert worksheet_path.exists()
    assert answer_path.exists()
    assert worksheet_path != answer_path
    assert "答案页" not in worksheet_path.read_text(encoding="utf-8")
    assert "答案页" in answer_path.read_text(encoding="utf-8")
