import io
import json
import sqlite3
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from config import CONFIG_PATH
from .schema import SCHEMA_SQL, INDEXES_SQL, SCHEMA_VERSION
from utils.progress import compute_progress_from_reviews, upsert_card_progress

CONFIG_DIR = Path.home() / ".memcoach"
DB_PATH = CONFIG_DIR / "memcoach.db"
BACKUP_DIR = CONFIG_DIR / "backups"
BACKUP_KEEP = 7

def init_db():
    """Initialize the database by creating tables and indexes if they don't exist."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        ensure_card_mastery_status(conn)
        ensure_card_chunk_fields(conn)
        ensure_soft_delete_columns(conn)
        ensure_card_position(conn)
        ensure_cards_fts(conn)
        ensure_review_duration(conn)
        ensure_review_hint_mode(conn)
        ensure_deck_review_mode(conn)
        ensure_review_review_mode(conn)
        ensure_review_grading_fields(conn)
        ensure_card_progress(conn)
        ensure_assignment_defaults(conn)
        ensure_deck_mastery_rules(conn)
        ensure_bible_verses_table(conn)
        ensure_schema_version(conn)
        conn.executescript(INDEXES_SQL)
        conn.commit()
    run_daily_backup()

def ensure_card_progress(conn: sqlite3.Connection) -> None:
    """Ensure card_progress table exists and backfill from reviews if empty."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='card_progress'"
    )
    if not cursor.fetchone():
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS card_progress (
                kid_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                interval_days INTEGER NOT NULL DEFAULT 1,
                due_date TEXT NOT NULL DEFAULT (date('now')),
                ease_factor REAL NOT NULL DEFAULT 2.5,
                streak INTEGER NOT NULL DEFAULT 0,
                mastery_status TEXT NOT NULL DEFAULT 'new' CHECK(mastery_status IN ('new', 'learning', 'mastered')),
                last_review_ts TEXT,
                PRIMARY KEY (kid_id, card_id),
                FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE,
                FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE
            )
            """
        )
    cursor.execute("SELECT COUNT(*) FROM card_progress")
    if (cursor.fetchone() or [0])[0]:
        return
    cursor.execute("SELECT DISTINCT kid_id, card_id FROM reviews")
    pairs = cursor.fetchall()
    if not pairs:
        return
    for row in pairs:
        progress = compute_progress_from_reviews(conn, row["kid_id"], row["card_id"])
        if not progress:
            continue
        upsert_card_progress(
            conn,
            kid_id=row["kid_id"],
            card_id=row["card_id"],
            interval_days=progress.interval_days,
            due_date=progress.due_date,
            ease_factor=progress.ease_factor,
            streak=progress.streak,
            mastery_status=progress.mastery_status,
            last_review_ts=progress.last_review_ts,
        )

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

def ensure_soft_delete_columns(conn: sqlite3.Connection) -> None:
    """Ensure tables have deleted_at columns for soft deletes."""
    cursor = conn.cursor()
    for table in ("kids", "decks", "cards", "texts"):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in cursor.fetchall()}
        if "deleted_at" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TEXT")

def ensure_card_position(conn: sqlite3.Connection) -> None:
    """Ensure cards table has position column and initialize existing rows."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(cards)")
    columns = {row[1] for row in cursor.fetchall()}
    if "position" not in columns:
        cursor.execute("ALTER TABLE cards ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    cursor.execute("UPDATE cards SET position = id WHERE position IS NULL OR position = 0")

def ensure_cards_fts(conn: sqlite3.Connection) -> None:
    """Ensure FTS table is populated for existing cards."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards_fts'")
    if not cursor.fetchone():
        return
    cursor.execute("SELECT COUNT(*) FROM cards_fts")
    fts_count = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM cards")
    cards_count = cursor.fetchone()[0] or 0
    if fts_count < cards_count:
        cursor.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")

def ensure_review_duration(conn: sqlite3.Connection) -> None:
    """Ensure reviews table has duration_seconds column."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(reviews)")
    columns = {row[1] for row in cursor.fetchall()}
    if "duration_seconds" not in columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN duration_seconds INTEGER")

def ensure_review_hint_mode(conn: sqlite3.Connection) -> None:
    """Ensure reviews table has hint_mode column."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(reviews)")
    columns = {row[1] for row in cursor.fetchall()}
    if "hint_mode" not in columns:
        cursor.execute(
            "ALTER TABLE reviews ADD COLUMN hint_mode TEXT NOT NULL DEFAULT 'none'"
        )

def ensure_deck_review_mode(conn: sqlite3.Connection) -> None:
    """Ensure decks table has review_mode column."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(decks)")
    columns = {row[1] for row in cursor.fetchall()}
    if "review_mode" not in columns:
        cursor.execute(
            "ALTER TABLE decks ADD COLUMN review_mode TEXT NOT NULL DEFAULT 'free_recall'"
        )

def ensure_review_review_mode(conn: sqlite3.Connection) -> None:
    """Ensure reviews table has review_mode column."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(reviews)")
    columns = {row[1] for row in cursor.fetchall()}
    if "review_mode" not in columns:
        cursor.execute(
            "ALTER TABLE reviews ADD COLUMN review_mode TEXT NOT NULL DEFAULT 'free_recall'"
        )

def ensure_review_grading_fields(conn: sqlite3.Connection) -> None:
    """Ensure reviews table has grading metadata columns."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(reviews)")
    columns = {row[1] for row in cursor.fetchall()}
    if "auto_grade" not in columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN auto_grade TEXT")
    if "final_grade" not in columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN final_grade TEXT")
    if "graded_by" not in columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN graded_by TEXT NOT NULL DEFAULT 'auto'")

def ensure_assignment_defaults(conn: sqlite3.Connection) -> None:
    """Ensure default assignments exist for all kid/deck pairs."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO assignments (kid_id, deck_id)
        SELECT k.id, d.id
        FROM kids k
        CROSS JOIN decks d
        WHERE k.deleted_at IS NULL AND d.deleted_at IS NULL
        """
    )

def ensure_deck_mastery_rules(conn: sqlite3.Connection) -> None:
    """Ensure deck mastery rules table exists and defaults are seeded."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='deck_mastery_rules'"
    )
    if not cursor.fetchone():
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deck_mastery_rules (
                deck_id INTEGER PRIMARY KEY,
                consecutive_grades INTEGER NOT NULL DEFAULT 3,
                min_ease_factor REAL NOT NULL DEFAULT 2.5,
                min_interval_days INTEGER NOT NULL DEFAULT 7,
                FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
            )
            """
        )
    cursor.execute(
        """
        INSERT OR IGNORE INTO deck_mastery_rules (deck_id)
        SELECT id FROM decks WHERE deleted_at IS NULL
        """
    )

def ensure_bible_verses_table(conn: sqlite3.Connection) -> None:
    """Ensure bible_verses table exists for local scripture lookups."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='bible_verses'"
    )
    if cursor.fetchone():
        return
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bible_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL
        )
        """
    )

def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the SQLite schema version from PRAGMA user_version."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    row = cursor.fetchone()
    return int(row[0]) if row else 0

def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Set the SQLite schema version via PRAGMA user_version."""
    conn.execute(f"PRAGMA user_version = {int(version)}")

def ensure_schema_version(conn: sqlite3.Connection) -> None:
    """Ensure the current schema version is written to the database."""
    current = get_schema_version(conn)
    if current != SCHEMA_VERSION:
        set_schema_version(conn, SCHEMA_VERSION)

def get_schema_version_from_db() -> int:
    """Get the schema version from the on-disk database."""
    if not DB_PATH.exists():
        return SCHEMA_VERSION
    with get_conn() as conn:
        return get_schema_version(conn)

def build_backup_manifest(schema_version: int) -> dict:
    """Build a manifest for backups with timestamp and schema version."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": schema_version,
    }

def create_backup_archive_bytes(schema_version: int) -> bytes:
    """Create a backup zip archive in memory."""
    if not DB_PATH.exists():
        raise FileNotFoundError("memcoach.db not found")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.toml not found")
    manifest = build_backup_manifest(schema_version)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zipf.write(DB_PATH, arcname="memcoach.db")
        zipf.write(CONFIG_PATH, arcname="config.toml")
    buffer.seek(0)
    return buffer.read()

def create_backup_archive_file(destination: Path, schema_version: int) -> None:
    """Create a backup zip archive at the given destination."""
    if not DB_PATH.exists():
        raise FileNotFoundError("memcoach.db not found")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.toml not found")
    manifest = build_backup_manifest(schema_version)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zipf.write(DB_PATH, arcname="memcoach.db")
        zipf.write(CONFIG_PATH, arcname="config.toml")

def run_daily_backup() -> None:
    """Create a daily rolling backup of the DB/config and prune old archives."""
    if not DB_PATH.exists() or not CONFIG_PATH.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    existing = sorted(BACKUP_DIR.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    if existing:
        latest_date = date.fromtimestamp(existing[0].stat().st_mtime)
        if latest_date == today:
            return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"backup-{timestamp}.zip"
    schema_version = get_schema_version_from_db()
    create_backup_archive_file(backup_path, schema_version)
    existing = sorted(BACKUP_DIR.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    for old_backup in existing[BACKUP_KEEP:]:
        old_backup.unlink(missing_ok=True)

@contextmanager
def get_conn():
    """Context manager for SQLite connection, using row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def get_db():
    """FastAPI dependency that yields a DB connection and closes it afterwards."""
    with get_conn() as conn:
        yield conn
