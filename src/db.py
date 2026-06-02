from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.paths import DEFAULT_DB_PATH, LEGACY_DB_PATH, OUTPUT_DIRS, PRE_V016_BACKUP_DIR, ROOT
from src.core.rule_registry import RuleRegistry, load_rule_registry


SCHEMA_VERSION = "0.1.6"
PROJECT_NAME = "edu_tutor_system"
DB_NAME = "edu_tutor.db"


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
    ensure_pre_v016_legacy_backup(db_path)
    with get_connection(db_path) as conn:
        create_tables(conn)
        seed_schema_meta(conn)
        seed_mistake_tags(conn)


def ensure_output_dirs() -> None:
    for path in OUTPUT_DIRS:
        path.mkdir(parents=True, exist_ok=True)


def ensure_pre_v016_legacy_backup(db_path: str | Path = DEFAULT_DB_PATH) -> Path | None:
    """Archive the old v0.1.x runtime DB before the clean cutover creates edu_tutor.db."""
    target_db = Path(db_path)
    if target_db.resolve() != DEFAULT_DB_PATH.resolve():
        return None
    if not LEGACY_DB_PATH.exists() or DEFAULT_DB_PATH.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PRE_V016_BACKUP_DIR / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / LEGACY_DB_PATH.name
    shutil.copy2(LEGACY_DB_PATH, target)
    return target


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_type TEXT NOT NULL,
            student_id TEXT,
            subject_id TEXT,
            grade_at_time INTEGER,
            source_name TEXT,
            source_hash TEXT,
            status TEXT NOT NULL,
            total_count INTEGER NOT NULL DEFAULT 0,
            imported_count INTEGER NOT NULL DEFAULT 0,
            skipped_duplicate_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mistake_tags (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            scope TEXT NOT NULL,
            subjects TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mistakes (
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
            training_needed INTEGER,
            source TEXT,
            status TEXT,
            import_batch_id INTEGER,
            record_hash TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (import_batch_id) REFERENCES import_batches(id),
            FOREIGN KEY (primary_mistake_tag_code) REFERENCES mistake_tags(code)
        );

        CREATE TABLE IF NOT EXISTS worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            grade_at_time INTEGER NOT NULL,
            term_at_time TEXT,
            curriculum_version_at_time TEXT NOT NULL,
            textbook_version_at_time TEXT,
            title TEXT NOT NULL,
            date TEXT,
            source TEXT,
            status TEXT,
            worksheet_hash TEXT,
            import_batch_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (import_batch_id) REFERENCES import_batches(id)
        );

        CREATE TABLE IF NOT EXISTS worksheet_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worksheet_id INTEGER NOT NULL,
            question_no TEXT,
            section_name TEXT,
            section_layout TEXT,
            question_type_code TEXT NOT NULL,
            knowledge_point_id TEXT,
            target_mistake_tag_code TEXT,
            difficulty_code TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            explanation TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (worksheet_id) REFERENCES worksheets(id) ON DELETE CASCADE,
            FOREIGN KEY (target_mistake_tag_code) REFERENCES mistake_tags(code)
        );

        CREATE TABLE IF NOT EXISTS training_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_id TEXT,
            grade_at_time INTEGER,
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

        CREATE TABLE IF NOT EXISTS weekly_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            student_id TEXT NOT NULL,
            subject_id TEXT,
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


def seed_schema_meta(conn: sqlite3.Connection) -> None:
    ts = now_iso()
    rows = {
        "project_name": PROJECT_NAME,
        "schema_version": SCHEMA_VERSION,
        "db_name": DB_NAME,
    }
    conn.executemany(
        """
        INSERT INTO schema_meta (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
        """,
        [(key, value, ts) for key, value in rows.items()],
    )
    conn.commit()


def seed_mistake_tags(conn: sqlite3.Connection, registry: RuleRegistry | None = None) -> None:
    ts = now_iso()
    tags = (registry or load_rule_registry()).get_mistake_tags(active_only=False)
    conn.executemany(
        """
        INSERT INTO mistake_tags (
            code, name, scope, subjects, active, description, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            name=excluded.name,
            scope=excluded.scope,
            subjects=excluded.subjects,
            active=excluded.active,
            description=excluded.description,
            updated_at=excluded.updated_at
        """,
        [
            (
                str(tag.get("code", "")),
                str(tag.get("name", "")),
                str(tag.get("scope", "")),
                ",".join(str(subject) for subject in (tag.get("subjects") or [])),
                1 if tag.get("active", True) else 0,
                str(tag.get("description", "")),
                ts,
                ts,
            )
            for tag in tags
        ],
    )
    conn.commit()


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
