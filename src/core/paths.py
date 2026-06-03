from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "edu_tutor.db"

OUTPUT_DIRS = [
    ROOT / "outputs" / "worksheets",
    ROOT / "outputs" / "answer_sheets",
    ROOT / "outputs" / "prompts",
    ROOT / "outputs" / "reviews",
    ROOT / "outputs" / "exports",
]
