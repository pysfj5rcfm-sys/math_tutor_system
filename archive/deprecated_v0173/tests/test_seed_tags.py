from src.core.mistake_tags import MISTAKE_TAGS


def test_seed_tags(conn):
    count = conn.execute("SELECT COUNT(*) FROM mistake_tags").fetchone()[0]
    assert count >= 30
    assert len(MISTAKE_TAGS) >= 30
