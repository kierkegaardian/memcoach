import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .schema import SCHEMA_SQL, INDEXES_SQL

CONFIG_DIR = Path.home() / ".memcoach"
DB_PATH = CONFIG_DIR / "memcoach.db"

def init_db():
    """Initialize the database by creating tables and indexes if they don't exist."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        ensure_schema_updates(conn)
        conn.executescript(INDEXES_SQL)
        conn.commit()

@contextmanager
def get_conn():
    """Context manager for SQLite connection, using row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_db():
    """FastAPI dependency that yields a DB connection and closes it afterwards."""
    with get_conn() as conn:
        yield conn


def ensure_schema_updates(conn: sqlite3.Connection) -> None:
    """Apply lightweight schema updates for existing databases."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='texts'")
    if cursor.fetchone() is None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                full_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
            )
            """
        )
    cursor.execute("PRAGMA table_info(cards)")
    columns = {row[1] for row in cursor.fetchall()}
    if "text_id" not in columns:
        conn.execute("ALTER TABLE cards ADD COLUMN text_id INTEGER")
    if "chunk_index" not in columns:
        conn.execute("ALTER TABLE cards ADD COLUMN chunk_index INTEGER")
