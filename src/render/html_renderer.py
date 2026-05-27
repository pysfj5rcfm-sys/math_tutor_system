from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[2]


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())


def render_worksheet_html(bundle: dict[str, Any]) -> str:
    return _env().get_template("worksheet.html").render(
        worksheet=bundle["worksheet"],
        sections=bundle["sections"],
    )


def render_answer_sheet_html(bundle: dict[str, Any]) -> str:
    return _env().get_template("answer_sheet.html").render(
        worksheet=bundle["worksheet"],
        sections=bundle["sections"],
    )


def save_worksheet_html(bundle: dict[str, Any], output_dir: str | Path = ROOT / "outputs" / "worksheets") -> Path:
    worksheet = bundle["worksheet"]
    path = Path(output_dir) / f"worksheet_{worksheet['id']}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_worksheet_html(bundle), encoding="utf-8")
    return path


def save_answer_sheet_html(bundle: dict[str, Any], output_dir: str | Path = ROOT / "outputs" / "answer_sheets") -> Path:
    worksheet = bundle["worksheet"]
    path = Path(output_dir) / f"answer_sheet_{worksheet['id']}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_answer_sheet_html(bundle), encoding="utf-8")
    return path
