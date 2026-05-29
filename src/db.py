from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.rule_registry import RuleRegistry, load_rule_registry


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "math_tutor.db"
OUTPUT_DIRS = [
    ROOT / "outputs" / "worksheets",
    ROOT / "outputs" / "answer_sheets",
    ROOT / "outputs" / "prompts",
    ROOT / "outputs" / "reviews",
]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    ensure_output_dirs()
    with get_connection(db_path) as conn:
        create_tables(conn)
        seed_mistake_tags(conn)


def ensure_output_dirs() -> None:
    for path in OUTPUT_DIRS:
        path.mkdir(parents=True, exist_ok=True)


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mistake_tags (
            code TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            typical_symptoms TEXT NOT NULL,
            training_hint TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            question_type TEXT NOT NULL,
            knowledge_point TEXT NOT NULL,
            mistake_tag TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question_summary TEXT NOT NULL,
            wrong_answer_summary TEXT,
            correct_answer_summary TEXT,
            training_needed INTEGER NOT NULL DEFAULT 1,
            source TEXT,
            note TEXT,
            status TEXT NOT NULL DEFAULT 'needs_confirmation',
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (mistake_tag) REFERENCES mistake_tags(code)
        );

        CREATE TABLE IF NOT EXISTS training_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            stats_summary TEXT NOT NULL,
            student_profile_snapshot TEXT NOT NULL,
            constraints TEXT NOT NULL,
            generated_prompt TEXT NOT NULL,
            gpt_response_imported INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'generated',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            source_prompt_id INTEGER,
            target_mistake_tags TEXT,
            status TEXT NOT NULL DEFAULT 'needs_confirmation',
            version INTEGER NOT NULL DEFAULT 1,
            created_by_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS worksheet_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            worksheet_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            question_type TEXT NOT NULL,
            knowledge_point TEXT NOT NULL,
            target_mistake_tag TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            explanation TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            requires_diagram INTEGER NOT NULL DEFAULT 0,
            diagram_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (worksheet_id) REFERENCES worksheets(id) ON DELETE CASCADE,
            FOREIGN KEY (target_mistake_tag) REFERENCES mistake_tags(code)
        );

        CREATE TABLE IF NOT EXISTS weekly_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            stats_summary TEXT NOT NULL,
            gpt_analysis_imported TEXT,
            profile_update_suggestions TEXT,
            status TEXT NOT NULL DEFAULT 'generated',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS llm_call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            workflow_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            estimated_cost REAL,
            mode TEXT NOT NULL,
            request_hash TEXT,
            response_cache_path TEXT,
            created_at TEXT NOT NULL
        );
        """
    )


def seed_mistake_tags(conn: sqlite3.Connection, registry: RuleRegistry | None = None) -> None:
    ts = now_iso()
    tags = (registry or load_rule_registry()).get_mistake_tags(active_only=False)
    conn.executemany(
        """
        INSERT INTO mistake_tags (
            code, category, name, description, typical_symptoms, training_hint,
            is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            category=excluded.category,
            name=excluded.name,
            description=excluded.description,
            typical_symptoms=excluded.typical_symptoms,
            training_hint=excluded.training_hint,
            is_active=excluded.is_active,
            updated_at=excluded.updated_at
        """,
        [
            (
                str(tag.get("code", "")),
                str(tag.get("category", "")),
                str(tag.get("name", "")),
                str(tag.get("description", "")),
                _symptoms_to_text(tag.get("typical_symptoms", "")),
                str(tag.get("training_hint", "")),
                1 if tag.get("active", True) else 0,
                ts,
                ts,
            )
            for tag in tags
        ],
    )
    conn.commit()


def _symptoms_to_text(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    return str(value)


def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def confirm_record(conn: sqlite3.Connection, table: str, record_id: int) -> None:
    if table not in {"mistakes", "worksheets"}:
        raise ValueError("Only mistakes and worksheets support confirmation in v0.1")
    conn.execute(
        f"UPDATE {table} SET status = 'confirmed', updated_at = ? WHERE id = ?",
        (now_iso(), record_id),
    )
    conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database: {DEFAULT_DB_PATH}")
