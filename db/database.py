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
