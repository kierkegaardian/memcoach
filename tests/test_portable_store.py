from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from db.migrations import migrate_database
from portable.codec import parse_package, serialize_package
from portable.export import export_package
from portable.importer import apply_package, preview_package

GOLDEN = Path(__file__).parents[1] / "contracts" / "valid" / "memcoach-backup-v1.json"


@contextmanager
def _database():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate_database(conn)
    conn.commit()
    try:
        yield conn
    finally:
        conn.close()


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in ("kids", "decks", "cards", "card_progress", "reviews")
    }


def test_preview_is_read_only_merge_is_idempotent_and_export_round_trips() -> None:
    package = parse_package(GOLDEN.read_bytes())
    with _database() as conn:
        changes_before = conn.total_changes
        preview = preview_package(conn, package, "merge")
        assert conn.total_changes == changes_before
        assert preview.can_apply
        assert preview.kids.creates == preview.decks.creates == preview.cards.creates == 1
        assert preview.progress.creates == preview.reviews.creates == 1

        apply_package(conn, package, "merge")
        assert _counts(conn) == {"kids": 1, "decks": 1, "cards": 1, "card_progress": 1, "reviews": 1}
        assert conn.execute("SELECT COUNT(*) FROM cards_fts WHERE cards_fts MATCH 'Fixture'").fetchone()[0] == 1

        second = apply_package(conn, package, "merge")
        assert _counts(conn) == {"kids": 1, "decks": 1, "cards": 1, "card_progress": 1, "reviews": 1}
        assert second.kids.skips == second.decks.skips == second.cards.skips == 1
        assert second.progress.skips == second.reviews.skips == 1

        exported = serialize_package(export_package(conn, exported_at="2026-07-16T00:00:00Z"))
        reparsed = parse_package(exported)
        assert reparsed.library.counts() == package.library.counts()
        lowered = exported.lower()
        for forbidden in (b"pin_hash", b"config.toml", b"bible_verses", b"graded_by"):
            assert forbidden not in lowered


def test_copy_rewrites_content_ids_and_omits_history() -> None:
    package = parse_package(GOLDEN.read_bytes())
    with _database() as conn:
        preview = apply_package(conn, package, "copy")
        assert preview.can_apply
        assert _counts(conn) == {"kids": 1, "decks": 1, "cards": 1, "card_progress": 0, "reviews": 0}
        assert conn.execute("SELECT portable_id FROM kids").fetchone()[0] != package.library.kids[0].portable_id
        assert conn.execute("SELECT portable_id FROM decks").fetchone()[0] != package.library.decks[0].portable_id
        assert conn.execute("SELECT portable_id FROM cards").fetchone()[0] != package.library.cards[0].portable_id


def test_merge_applies_newer_content_and_progress_but_never_rewrites_review() -> None:
    package = parse_package(GOLDEN.read_bytes())
    with _database() as conn:
        apply_package(conn, package, "merge")
        kid = replace(package.library.kids[0], name="Updated Kid", updated_at="2026-07-16T00:00:00Z")
        progress = replace(
            package.library.progress[0],
            portable_id="99999999-9999-4999-8999-999999999999",
            interval_days=12,
            last_review="2026-07-16T00:00:00Z",
        )
        review = replace(package.library.reviews[0], grade="fail")
        updated = replace(
            package,
            library=replace(package.library, kids=(kid,), progress=(progress,), reviews=(review,)),
        )

        preview = apply_package(conn, updated, "merge")

        assert preview.kids.updates == preview.progress.updates == 1
        assert preview.reviews.skips == 1
        assert conn.execute("SELECT name FROM kids").fetchone()[0] == "Updated Kid"
        row = conn.execute("SELECT portable_id, interval_days FROM card_progress").fetchone()
        assert tuple(row) == (progress.portable_id, 12)
        assert conn.execute("SELECT grade FROM reviews").fetchone()[0] == "perfect"


def test_unique_name_collision_blocks_preview_and_apply_without_writes() -> None:
    package = parse_package(GOLDEN.read_bytes())
    with _database() as conn:
        conn.execute("INSERT INTO kids (name) VALUES ('Fixture Kid')")
        conn.commit()
        before = _counts(conn)

        preview = preview_package(conn, package, "merge")
        assert not preview.can_apply
        assert preview.kids.collisions == 1
        with pytest.raises(ValueError, match="collisions"):
            apply_package(conn, package, "merge")
        assert _counts(conn) == before


def test_merge_rolls_back_all_tables_when_fts_rebuild_fails() -> None:
    package = parse_package(GOLDEN.read_bytes())

    def fail_rebuild(_conn: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError("injected FTS failure")

    with _database() as conn:
        before = _counts(conn)
        with pytest.raises(sqlite3.OperationalError, match="injected FTS"):
            apply_package(conn, package, "merge", rebuild_fts=fail_rebuild)
        assert _counts(conn) == before
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
