from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from db.migrations_portable import migrate_9_to_10
from db.schema import INDEXES_SQL, SCHEMA_SQL, SCHEMA_VERSION
from utils.progress import compute_progress_from_reviews, upsert_card_progress

Migration = Callable[[sqlite3.Connection], None]


class SchemaMigrationError(RuntimeError):
    """Raised when a database cannot be migrated without guessing."""


def get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    if version < 0:
        raise ValueError("schema version must be non-negative")
    conn.execute(f"PRAGMA user_version = {version:d}")


def _execute_all(conn: sqlite3.Connection, statements: tuple[str, ...]) -> None:
    for statement in statements:
        conn.execute(statement)


def migrate_1_to_2(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "ALTER TABLE kids ADD COLUMN deleted_at TEXT",
            "ALTER TABLE decks ADD COLUMN deleted_at TEXT",
            "ALTER TABLE texts ADD COLUMN deleted_at TEXT",
            "ALTER TABLE cards ADD COLUMN position INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE cards ADD COLUMN deleted_at TEXT",
            "UPDATE cards SET position = id",
            "CREATE INDEX idx_cards_deleted ON cards (deleted_at)",
            "CREATE INDEX idx_cards_deck_position ON cards (deck_id, position)",
            "CREATE INDEX idx_texts_deleted ON texts (deleted_at)",
            "CREATE INDEX idx_kids_deleted ON kids (deleted_at)",
            "CREATE INDEX idx_decks_deleted ON decks (deleted_at)",
        ),
    )


def migrate_2_to_3(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "CREATE VIRTUAL TABLE cards_fts USING fts5("
            "prompt, full_text, content='cards', content_rowid='id')",
            "CREATE TRIGGER cards_ai AFTER INSERT ON cards BEGIN "
            "INSERT INTO cards_fts(rowid, prompt, full_text) "
            "VALUES (new.id, new.prompt, new.full_text); END",
            "CREATE TRIGGER cards_ad AFTER DELETE ON cards BEGIN "
            "INSERT INTO cards_fts(cards_fts, rowid, prompt, full_text) "
            "VALUES ('delete', old.id, old.prompt, old.full_text); END",
            "CREATE TRIGGER cards_au AFTER UPDATE ON cards BEGIN "
            "INSERT INTO cards_fts(cards_fts, rowid, prompt, full_text) "
            "VALUES ('delete', old.id, old.prompt, old.full_text); "
            "INSERT INTO cards_fts(rowid, prompt, full_text) "
            "VALUES (new.id, new.prompt, new.full_text); END",
            "INSERT INTO cards_fts(cards_fts) VALUES('rebuild')",
            "CREATE TABLE tags (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT UNIQUE NOT NULL)",
            "CREATE TABLE deck_tags (deck_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, "
            "PRIMARY KEY (deck_id, tag_id), "
            "FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE, "
            "FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE)",
            "CREATE TABLE card_tags (card_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, "
            "PRIMARY KEY (card_id, tag_id), "
            "FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE, "
            "FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE)",
            "CREATE INDEX idx_tags_name ON tags (name)",
            "CREATE INDEX idx_deck_tags_deck ON deck_tags (deck_id)",
            "CREATE INDEX idx_deck_tags_tag ON deck_tags (tag_id)",
            "CREATE INDEX idx_card_tags_card ON card_tags (card_id)",
            "CREATE INDEX idx_card_tags_tag ON card_tags (tag_id)",
        ),
    )


def migrate_3_to_4(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "CREATE TABLE assignments (kid_id INTEGER NOT NULL, deck_id INTEGER NOT NULL, "
            "enabled INTEGER NOT NULL DEFAULT 1, days_of_week TEXT, new_cap INTEGER, "
            "review_cap INTEGER, paused_until TEXT, PRIMARY KEY (kid_id, deck_id), "
            "FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE, "
            "FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE)",
            "ALTER TABLE reviews ADD COLUMN duration_seconds INTEGER",
            "INSERT INTO assignments (kid_id, deck_id) SELECT k.id, d.id FROM kids k "
            "CROSS JOIN decks d WHERE k.deleted_at IS NULL AND d.deleted_at IS NULL",
            "CREATE INDEX idx_assignments_kid ON assignments (kid_id)",
            "CREATE INDEX idx_assignments_deck ON assignments (deck_id)",
        ),
    )


def migrate_4_to_5(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "ALTER TABLE decks ADD COLUMN review_mode TEXT NOT NULL DEFAULT 'free_recall' "
            "CHECK(review_mode IN ('free_recall', 'recitation', 'cloze', 'first_letters'))",
            "ALTER TABLE reviews ADD COLUMN review_mode TEXT NOT NULL DEFAULT 'free_recall' "
            "CHECK(review_mode IN ('free_recall', 'recitation', 'cloze', 'first_letters'))",
        ),
    )


def migrate_5_to_6(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "ALTER TABLE reviews ADD COLUMN auto_grade TEXT "
            "CHECK(auto_grade IN ('perfect', 'good', 'fail'))",
            "ALTER TABLE reviews ADD COLUMN final_grade TEXT "
            "CHECK(final_grade IN ('perfect', 'good', 'fail'))",
            "ALTER TABLE reviews ADD COLUMN graded_by TEXT NOT NULL DEFAULT 'auto' "
            "CHECK(graded_by IN ('auto', 'parent'))",
        ),
    )


def migrate_6_to_7(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "CREATE TABLE deck_mastery_rules (deck_id INTEGER PRIMARY KEY, "
            "consecutive_grades INTEGER NOT NULL DEFAULT 3, "
            "min_ease_factor REAL NOT NULL DEFAULT 2.5, "
            "min_interval_days INTEGER NOT NULL DEFAULT 7, "
            "FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE)",
            "INSERT INTO deck_mastery_rules (deck_id) "
            "SELECT id FROM decks WHERE deleted_at IS NULL",
            "CREATE INDEX idx_deck_mastery_rules_deck ON deck_mastery_rules (deck_id)",
        ),
    )


def migrate_7_to_8(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "CREATE TABLE bible_verses (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "translation TEXT NOT NULL, book TEXT NOT NULL, chapter INTEGER NOT NULL, "
            "verse INTEGER NOT NULL, text TEXT NOT NULL)",
            "CREATE INDEX idx_bible_verses_lookup "
            "ON bible_verses (translation, book, chapter, verse)",
            "CREATE INDEX idx_bible_verses_book ON bible_verses (book, chapter, verse)",
        ),
    )


def migrate_8_to_9(conn: sqlite3.Connection) -> None:
    _execute_all(
        conn,
        (
            "CREATE TABLE card_progress (kid_id INTEGER NOT NULL, card_id INTEGER NOT NULL, "
            "interval_days INTEGER NOT NULL DEFAULT 1, "
            "due_date TEXT NOT NULL DEFAULT (date('now')), "
            "ease_factor REAL NOT NULL DEFAULT 2.5, streak INTEGER NOT NULL DEFAULT 0, "
            "mastery_status TEXT NOT NULL DEFAULT 'new' "
            "CHECK(mastery_status IN ('new', 'learning', 'mastered')), "
            "last_review_ts TEXT, "
            "PRIMARY KEY (kid_id, card_id), "
            "FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE, "
            "FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE)",
        ),
    )
    pairs = conn.execute("SELECT DISTINCT kid_id, card_id FROM reviews").fetchall()
    for kid_id, card_id in pairs:
        progress = compute_progress_from_reviews(conn, int(kid_id), int(card_id))
        if progress is None:
            continue
        upsert_card_progress(
            conn,
            kid_id=int(kid_id),
            card_id=int(card_id),
            interval_days=progress.interval_days,
            due_date=progress.due_date,
            ease_factor=progress.ease_factor,
            streak=progress.streak,
            mastery_status=progress.mastery_status,
            last_review_ts=progress.last_review_ts,
        )
    _execute_all(
        conn,
        (
            "CREATE INDEX idx_card_progress_kid_due ON card_progress (kid_id, due_date)",
            "CREATE INDEX idx_card_progress_card ON card_progress (card_id)",
        ),
    )
MIGRATIONS: dict[int, Migration] = {
    1: migrate_1_to_2,
    2: migrate_2_to_3,
    3: migrate_3_to_4,
    4: migrate_4_to_5,
    5: migrate_5_to_6,
    6: migrate_6_to_7,
    7: migrate_7_to_8,
    8: migrate_8_to_9,
    9: migrate_9_to_10,
}

MIGRATIONS_REQUIRING_FOREIGN_KEYS_OFF = frozenset({9})


def validate_migration_registry(
    migrations: Mapping[int, Migration] = MIGRATIONS,
    target_version: int = SCHEMA_VERSION,
) -> None:
    expected = set(range(1, target_version))
    if set(migrations) != expected:
        raise SchemaMigrationError(
            f"migration registry must contain exactly {sorted(expected)}"
        )


def _has_application_objects(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
    ).fetchone()
    return row is not None


def _bootstrap_current_schema(conn: sqlite3.Connection) -> None:
    if _has_application_objects(conn):
        raise SchemaMigrationError(
            "database is unstamped but not empty; refusing to infer its schema"
        )
    script = (
        "BEGIN IMMEDIATE;\n"
        f"{SCHEMA_SQL}\n{INDEXES_SQL}\n"
        f"PRAGMA user_version = {SCHEMA_VERSION:d};\n"
        "COMMIT;"
    )
    try:
        conn.executescript(script)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise


def migrate_database(
    conn: sqlite3.Connection,
    *,
    migrations: Mapping[int, Migration] = MIGRATIONS,
    target_version: int = SCHEMA_VERSION,
) -> None:
    """Bring a stamped database forward one tested transaction at a time."""
    current = get_schema_version(conn)
    if current > target_version:
        raise SchemaMigrationError(
            f"database schema {current} is newer than supported schema {target_version}"
        )
    if current == 0:
        if target_version != SCHEMA_VERSION:
            raise SchemaMigrationError("custom targets cannot bootstrap a new database")
        _bootstrap_current_schema(conn)
        return

    validate_migration_registry(migrations, target_version)
    while current < target_version:
        migration = migrations[current]
        disable_foreign_keys = (
            migration is MIGRATIONS.get(current)
            and current in MIGRATIONS_REQUIRING_FOREIGN_KEYS_OFF
        )
        if disable_foreign_keys:
            conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            if get_schema_version(conn) != current:
                raise SchemaMigrationError("schema version changed during migration")
            migration(conn)
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise SchemaMigrationError(
                    f"migration {current}->{current + 1} created foreign-key violations"
                )
            _set_schema_version(conn, current + 1)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if disable_foreign_keys:
                conn.execute("PRAGMA foreign_keys = ON")
        current += 1
