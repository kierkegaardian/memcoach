import io
import json
import sqlite3
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from config import CONFIG_PATH
from db.migrations import get_schema_version, migrate_database
from db.schema import SCHEMA_VERSION

CONFIG_DIR = Path.home() / ".memcoach"
DB_PATH = CONFIG_DIR / "memcoach.db"
BACKUP_DIR = CONFIG_DIR / "backups"
BACKUP_KEEP = 7

def init_db() -> None:
    """Initialize or monotonically migrate the database."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with get_conn() as conn:
        migrate_database(conn)
        reconcile_current_data(conn)
        conn.commit()
    run_daily_backup()

def reconcile_current_data(conn: sqlite3.Connection) -> None:
    """Preserve current idempotent data seeding without repairing schema."""
    conn.execute(
        "INSERT INTO cards_fts(cards_fts) "
        "SELECT 'rebuild' WHERE (SELECT COUNT(*) FROM cards_fts) < "
        "(SELECT COUNT(*) FROM cards)"
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO assignments (kid_id, deck_id)
        SELECT k.id, d.id
        FROM kids k
        CROSS JOIN decks d
        WHERE k.deleted_at IS NULL AND d.deleted_at IS NULL
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO deck_mastery_rules (deck_id)
        SELECT id FROM decks WHERE deleted_at IS NULL
        """
    )

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


def create_database_snapshot(destination: Path) -> None:
    """Write a transactionally consistent SQLite snapshot to ``destination``."""
    destination.unlink(missing_ok=True)
    with get_conn() as source_conn:
        with closing(sqlite3.connect(destination)) as destination_conn:
            source_conn.backup(destination_conn)


def create_backup_archive_bytes(schema_version: int) -> bytes:
    """Create a backup zip archive in memory."""
    if not DB_PATH.exists():
        raise FileNotFoundError("memcoach.db not found")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.toml not found")
    manifest = build_backup_manifest(schema_version)
    buffer = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = Path(tmpdir) / "memcoach.db"
        create_database_snapshot(snapshot_path)
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zipf.write(snapshot_path, arcname="memcoach.db")
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
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_path = Path(tmpdir) / "memcoach.db"
        create_database_snapshot(snapshot_path)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zipf.write(snapshot_path, arcname="memcoach.db")
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
def get_conn() -> Iterator[sqlite3.Connection]:
    """Context manager for SQLite connection, using row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
    finally:
        conn.close()

def get_db():
    """FastAPI dependency that yields a DB connection and closes it afterwards."""
    with get_conn() as conn:
        yield conn
