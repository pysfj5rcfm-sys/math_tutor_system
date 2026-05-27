from __future__ import annotations

import sqlite3

import pytest

from src.db import create_tables, seed_mistake_tags


@pytest.fixture
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    create_tables(db)
    seed_mistake_tags(db)
    yield db
    db.close()
