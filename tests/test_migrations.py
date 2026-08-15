from __future__ import annotations

import shutil
import sqlite3
from uuid import UUID
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from db.migrations import (
    MIGRATIONS,
    SchemaMigrationError,
    get_schema_version,
    migrate_database,
    validate_migration_registry,
)
from db.schema import SCHEMA_VERSION

FIXTURES = Path(__file__).parent / "fixtures"
CORE_TABLES = ("kids", "decks", "cards", "card_progress", "reviews")


@contextmanager
def _connect(path: Path | str = ":memory:") -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in CORE_TABLES
    }


def _index_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _assert_application_query(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        """
        SELECT k.name, d.name, c.prompt, p.last_review_ts, r.grade
        FROM card_progress p
        JOIN kids k ON k.id = p.kid_id
        JOIN cards c ON c.id = p.card_id
        JOIN decks d ON d.id = c.deck_id
        JOIN reviews r ON r.kid_id = k.id AND r.card_id = c.id
        """
    ).fetchone()
    assert row is not None
    assert str(row[4]) == "perfect"


def _assert_portable_columns(conn: sqlite3.Connection) -> None:
    for table in CORE_TABLES:
        values = [str(row[0]) for row in conn.execute(f"SELECT portable_id FROM {table}")]
        assert len(values) == len(set(values))
        assert all(str(UUID(value)) == value for value in values)
    for table in ("kids", "decks", "cards"):
        assert conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE updated_at IS NULL"
        ).fetchone()[0] == 0
    metadata = conn.execute(
        "SELECT installation_id, created_at FROM installation_metadata WHERE singleton_id = 1"
    ).fetchone()
    assert metadata is not None
    assert str(UUID(str(metadata[0]))) == str(metadata[0])
    assert str(metadata[1]).endswith("Z")


def test_migration_registry_has_every_monotonic_step() -> None:
    validate_migration_registry()
    assert set(MIGRATIONS) == set(range(1, SCHEMA_VERSION))


def test_schema_one_fixture_migrates_to_ten_without_loss() -> None:
    with _connect() as conn:
        conn.executescript((FIXTURES / "web_schema_1.sql").read_text())
        migrate_database(conn)

        assert get_schema_version(conn) == SCHEMA_VERSION == 10
        assert _counts(conn) == {
            "kids": 1,
            "decks": 1,
            "cards": 1,
            "card_progress": 1,
            "reviews": 1,
        }
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute(
            "SELECT COUNT(*) FROM cards_fts WHERE cards_fts MATCH 'first'"
        ).fetchone()[0] == 1
        progress = conn.execute(
            """
            SELECT interval_days, ease_factor, streak, mastery_status,
                   due_date, last_review_ts
            FROM card_progress
            """
        ).fetchone()
        assert tuple(progress) == (
            6,
            2.5,
            1,
            "learning",
            "2026-07-20",
            "2026-07-14 09:00:00",
        )
        _assert_application_query(conn)
        _assert_portable_columns(conn)


def test_sanitized_real_schema_nine_fixture_migrates_without_loss(tmp_path: Path) -> None:
    source = FIXTURES / "web_schema_9_sanitized.db"
    target = tmp_path / source.name
    shutil.copy2(source, target)

    with _connect(target) as conn:
        before_counts = _counts(conn)
        migrate_database(conn)

        assert get_schema_version(conn) == SCHEMA_VERSION == 10
        assert _counts(conn) == before_counts == {
            "kids": 1,
            "decks": 1,
            "cards": 1,
            "card_progress": 1,
            "reviews": 1,
        }
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert {
            "idx_kids_portable_id",
            "idx_decks_portable_id",
            "idx_cards_portable_id",
            "idx_card_progress_portable_id",
            "idx_reviews_portable_id",
        } <= _index_names(conn)
        _assert_application_query(conn)
        _assert_portable_columns(conn)


def test_empty_database_bootstraps_directly_to_current_schema() -> None:
    with _connect() as conn:
        migrate_database(conn)
        assert get_schema_version(conn) == SCHEMA_VERSION
        assert set(CORE_TABLES).issubset(
            {
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        )


def test_newer_database_is_rejected_without_rewriting_stamp() -> None:
    with _connect() as conn:
        conn.execute("PRAGMA user_version = 11")
        with pytest.raises(SchemaMigrationError, match="newer than supported"):
            migrate_database(conn)
        assert get_schema_version(conn) == 11


def test_unstamped_nonempty_database_is_rejected() -> None:
    with _connect() as conn:
        conn.execute("CREATE TABLE legacy_data (value TEXT NOT NULL)")
        with pytest.raises(SchemaMigrationError, match="unstamped but not empty"):
            migrate_database(conn)
        assert get_schema_version(conn) == 0
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'legacy_data'"
        ).fetchone() is not None


def test_failed_step_rolls_back_data_and_schema_stamp() -> None:
    def failing_migration(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE should_rollback (value TEXT)")
        raise RuntimeError("injected migration failure")

    with _connect() as conn:
        conn.execute("CREATE TABLE original_data (value TEXT NOT NULL)")
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
        with pytest.raises(RuntimeError, match="injected migration failure"):
            migrate_database(conn, migrations={1: failing_migration}, target_version=2)

        assert get_schema_version(conn) == 1
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'should_rollback'"
        ).fetchone() is None
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'original_data'"
        ).fetchone() is not None


def test_failed_nine_to_ten_rebuild_rolls_back_schema_and_rows(tmp_path: Path) -> None:
    source = FIXTURES / "web_schema_9_sanitized.db"
    target = tmp_path / source.name
    shutil.copy2(source, target)
    with _connect(target) as conn:
        before = _counts(conn)
        conn.execute("DROP TABLE cards_fts")
        conn.commit()

        with pytest.raises(sqlite3.OperationalError, match="cards_fts"):
            migrate_database(conn)

        assert get_schema_version(conn) == 9
        assert _counts(conn) == before
        assert "portable_id" not in {
            str(row[1]) for row in conn.execute("PRAGMA table_info(kids)")
        }


def test_orphaned_legacy_review_fails_closed_without_advancing_stamp() -> None:
    with _connect() as conn:
        conn.executescript((FIXTURES / "web_schema_1.sql").read_text())
        migrate_database(
            conn,
            migrations={version: MIGRATIONS[version] for version in range(1, 8)},
            target_version=8,
        )
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            """
            INSERT INTO reviews (
                id, card_id, kid_id, ts, grade, hint_mode, user_text,
                duration_seconds, review_mode, auto_grade, final_grade, graded_by
            ) VALUES (
                2, 1, 999, '2026-07-15 09:00:00', 'good', 'none', 'orphan',
                5, 'free_recall', 'good', 'good', 'auto'
            )
            """
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            migrate_database(conn)

        assert get_schema_version(conn) == 8
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'card_progress'"
        ).fetchone() is None
        assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 2
