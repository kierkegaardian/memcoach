from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from db.schema import INDEXES_SQL, PORTABLE_ID_DEFAULT_SQL, UTC_TIMESTAMP_DEFAULT_SQL


def _portable_id() -> str:
    return str(uuid4())


def _migration_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rebuild(
    conn: sqlite3.Connection,
    table: str,
    create_sql: str,
    columns: tuple[str, ...],
) -> None:
    old_table = f"_{table}_schema9"
    conn.execute("PRAGMA legacy_alter_table = ON")
    try:
        conn.execute(f"ALTER TABLE {table} RENAME TO {old_table}")
        conn.execute(create_sql)
        column_list = ", ".join(columns)
        conn.execute(f"INSERT INTO {table} ({column_list}) SELECT {column_list} FROM {old_table}")
        conn.execute(f"DROP TABLE {old_table}")
    finally:
        conn.execute("PRAGMA legacy_alter_table = OFF")


def _backfill_columns(conn: sqlite3.Connection, migrated_at: str) -> None:
    portable_columns = {
        "kids": ("portable_id", "updated_at"),
        "decks": ("portable_id", "updated_at"),
        "cards": ("portable_id", "updated_at"),
        "card_progress": ("portable_id",),
        "reviews": ("portable_id",),
    }
    for table, columns in portable_columns.items():
        for column in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
        for row in conn.execute(f"SELECT rowid FROM {table}").fetchall():
            values = [_portable_id(), *([migrated_at] if "updated_at" in columns else [])]
            assignments = ", ".join(f"{column} = ?" for column in columns)
            conn.execute(f"UPDATE {table} SET {assignments} WHERE rowid = ?", (*values, int(row[0])))


def _rebuild_content_tables(conn: sqlite3.Connection) -> None:
    _rebuild(
        conn,
        "kids",
        f"""CREATE TABLE kids (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
            portable_id TEXT NOT NULL DEFAULT {PORTABLE_ID_DEFAULT_SQL},
            updated_at TEXT NOT NULL DEFAULT {UTC_TIMESTAMP_DEFAULT_SQL}, deleted_at TEXT
        )""",
        ("id", "name", "portable_id", "updated_at", "deleted_at"),
    )
    _rebuild(
        conn,
        "decks",
        f"""CREATE TABLE decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
            portable_id TEXT NOT NULL DEFAULT {PORTABLE_ID_DEFAULT_SQL},
            updated_at TEXT NOT NULL DEFAULT {UTC_TIMESTAMP_DEFAULT_SQL},
            review_mode TEXT NOT NULL DEFAULT 'free_recall'
                CHECK(review_mode IN ('free_recall', 'recitation', 'cloze', 'first_letters')),
            deleted_at TEXT
        )""",
        ("id", "name", "portable_id", "updated_at", "review_mode", "deleted_at"),
    )
    _rebuild(
        conn,
        "cards",
        f"""CREATE TABLE cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, deck_id INTEGER NOT NULL,
            prompt TEXT NOT NULL, full_text TEXT NOT NULL,
            portable_id TEXT NOT NULL DEFAULT {PORTABLE_ID_DEFAULT_SQL},
            updated_at TEXT NOT NULL DEFAULT {UTC_TIMESTAMP_DEFAULT_SQL},
            text_id INTEGER, chunk_index INTEGER, interval_days INTEGER NOT NULL DEFAULT 1,
            due_date TEXT NOT NULL DEFAULT (date('now')), ease_factor REAL NOT NULL DEFAULT 2.5,
            streak INTEGER NOT NULL DEFAULT 0,
            mastery_status TEXT NOT NULL DEFAULT 'new'
                CHECK(mastery_status IN ('new', 'learning', 'mastered')),
            position INTEGER NOT NULL DEFAULT 0, deleted_at TEXT,
            FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE,
            FOREIGN KEY (text_id) REFERENCES texts (id) ON DELETE SET NULL
        )""",
        (
            "id", "deck_id", "prompt", "full_text", "portable_id", "updated_at",
            "text_id", "chunk_index", "interval_days", "due_date", "ease_factor",
            "streak", "mastery_status", "position", "deleted_at",
        ),
    )


def _rebuild_history_tables(conn: sqlite3.Connection) -> None:
    _rebuild(
        conn,
        "card_progress",
        f"""CREATE TABLE card_progress (
            kid_id INTEGER NOT NULL, card_id INTEGER NOT NULL,
            portable_id TEXT UNIQUE NOT NULL DEFAULT {PORTABLE_ID_DEFAULT_SQL},
            interval_days INTEGER NOT NULL DEFAULT 1,
            due_date TEXT NOT NULL DEFAULT (date('now')), ease_factor REAL NOT NULL DEFAULT 2.5,
            streak INTEGER NOT NULL DEFAULT 0,
            mastery_status TEXT NOT NULL DEFAULT 'new'
                CHECK(mastery_status IN ('new', 'learning', 'mastered')),
            last_review_ts TEXT, PRIMARY KEY (kid_id, card_id),
            FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE,
            FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE
        )""",
        (
            "kid_id", "card_id", "portable_id", "interval_days", "due_date",
            "ease_factor", "streak", "mastery_status", "last_review_ts",
        ),
    )
    _rebuild(
        conn,
        "reviews",
        f"""CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT, card_id INTEGER NOT NULL,
            kid_id INTEGER NOT NULL,
            portable_id TEXT UNIQUE NOT NULL DEFAULT {PORTABLE_ID_DEFAULT_SQL},
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            grade TEXT NOT NULL CHECK(grade IN ('perfect', 'good', 'fail')),
            auto_grade TEXT CHECK(auto_grade IN ('perfect', 'good', 'fail')),
            final_grade TEXT CHECK(final_grade IN ('perfect', 'good', 'fail')),
            graded_by TEXT NOT NULL DEFAULT 'auto' CHECK(graded_by IN ('auto', 'parent')),
            review_mode TEXT NOT NULL DEFAULT 'free_recall'
                CHECK(review_mode IN ('free_recall', 'recitation', 'cloze', 'first_letters')),
            hint_mode TEXT NOT NULL DEFAULT 'none', user_text TEXT, duration_seconds INTEGER,
            FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE,
            FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE
        )""",
        (
            "id", "card_id", "kid_id", "portable_id", "ts", "grade", "auto_grade",
            "final_grade", "graded_by", "review_mode", "hint_mode", "user_text",
            "duration_seconds",
        ),
    )


def _restore_indexes_and_triggers(conn: sqlite3.Connection) -> None:
    for statement in INDEXES_SQL.split(";"):
        if statement.strip():
            conn.execute(statement)
    for statement in (
        """CREATE TRIGGER cards_ai AFTER INSERT ON cards BEGIN
            INSERT INTO cards_fts(rowid, prompt, full_text) VALUES (new.id, new.prompt, new.full_text);
        END""",
        """CREATE TRIGGER cards_ad AFTER DELETE ON cards BEGIN
            INSERT INTO cards_fts(cards_fts, rowid, prompt, full_text)
            VALUES ('delete', old.id, old.prompt, old.full_text);
        END""",
        """CREATE TRIGGER cards_au AFTER UPDATE ON cards BEGIN
            INSERT INTO cards_fts(cards_fts, rowid, prompt, full_text)
            VALUES ('delete', old.id, old.prompt, old.full_text);
            INSERT INTO cards_fts(rowid, prompt, full_text) VALUES (new.id, new.prompt, new.full_text);
        END""",
    ):
        conn.execute(statement)
    conn.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")


def migrate_9_to_10(conn: sqlite3.Connection) -> None:
    migrated_at = _migration_timestamp()
    _backfill_columns(conn, migrated_at)
    conn.execute("PRAGMA defer_foreign_keys = ON")
    _rebuild_content_tables(conn)
    _rebuild_history_tables(conn)
    conn.execute(
        """CREATE TABLE installation_metadata (
            singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
            installation_id TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
        )"""
    )
    conn.execute("INSERT INTO installation_metadata VALUES (1, ?, ?)", (_portable_id(), migrated_at))
    _restore_indexes_and_triggers(conn)
