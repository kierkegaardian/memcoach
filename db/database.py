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
        conn.executescript(INDEXES_SQL)
        ensure_card_mastery_status(conn)
        ensure_card_chunk_fields(conn)
        conn.commit()

def ensure_card_mastery_status(conn: sqlite3.Connection) -> None:
    """Ensure cards table has mastery_status column for existing installs."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cards)")
    columns = {row[1] for row in cursor.fetchall()}
    if "mastery_status" not in columns:
        cursor.execute(
            "ALTER TABLE cards ADD COLUMN mastery_status TEXT NOT NULL DEFAULT 'new'"
        )

def ensure_card_chunk_fields(conn: sqlite3.Connection) -> None:
    """Ensure cards table has chunking columns for long texts."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cards)")
    columns = {row[1] for row in cursor.fetchall()}
    if "text_id" not in columns:
        cursor.execute("ALTER TABLE cards ADD COLUMN text_id INTEGER")
    if "chunk_index" not in columns:
        cursor.execute("ALTER TABLE cards ADD COLUMN chunk_index INTEGER")

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
