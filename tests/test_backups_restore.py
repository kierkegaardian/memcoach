from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

import config
from db import database
from db.schema import SCHEMA_VERSION
from main import app
from routes import backups
from utils.auth import require_parent_session


def _write_config(config_path: Path) -> None:
    config_path.write_text(
        "\n".join(
            [
                "[uploads]",
                "backup_restore_max_bytes = 20971520",
                "stt_audio_max_bytes = 26214400",
                "cards_txt_max_bytes = 5242880",
            ]
        ),
        encoding="utf-8",
    )


def _make_zip(db_bytes: bytes, config_text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("manifest.json", json.dumps({"schema_version": SCHEMA_VERSION}))
        zipf.writestr("memcoach.db", db_bytes)
        zipf.writestr("config.toml", config_text)
    return buf.getvalue()


def _make_sqlite_bytes(marker_value: str) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp_path = Path(tmp.name)
    try:
        with sqlite3.connect(tmp_path) as conn:
            conn.execute("CREATE TABLE marker (value TEXT)")
            conn.execute("INSERT INTO marker (value) VALUES (?)", (marker_value,))
            conn.commit()
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def _prepare_env(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    db_path = config_dir / "memcoach.db"
    backup_dir = config_dir / "backups"
    backup_dir.mkdir()
    _write_config(config_path)
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(database, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(backups, "CONFIG_PATH", config_path)
    monkeypatch.setattr(backups, "DB_PATH", db_path)
    monkeypatch.setattr(backups, "BACKUP_DIR", backup_dir)
    database.init_db()
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS marker (value TEXT)")
        conn.execute("DELETE FROM marker")
        conn.execute("INSERT INTO marker (value) VALUES ('original')")
        conn.commit()


def _csrf_headers(client: TestClient) -> dict[str, str]:
    client.get("/__csrf_probe__")
    token = client.cookies.get("memcoach_csrf_token")
    assert token
    return {"x-csrf-token": token}


def test_restore_rejects_invalid_db_payload(tmp_path, monkeypatch):
    _prepare_env(tmp_path, monkeypatch)
    app.dependency_overrides[require_parent_session] = lambda: None
    try:
        client = TestClient(app)
        headers = _csrf_headers(client)
        payload = _make_zip(b"not-a-sqlite-db", "[uploads]\nbackup_restore_max_bytes=20971520\n")
        response = client.post(
            "/admin/restore",
            files={"file": ("backup.zip", payload, "application/zip")},
            headers=headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] in {
            "Backup database is invalid",
            "Backup database integrity check failed",
        }
    finally:
        app.dependency_overrides.clear()


def test_restore_rolls_back_on_replace_failure(tmp_path, monkeypatch):
    _prepare_env(tmp_path, monkeypatch)
    app.dependency_overrides[require_parent_session] = lambda: None
    original_replace = Path.replace

    def failing_replace(self: Path, target: Path) -> Path:
        if self.name.endswith(".db.restore"):
            raise OSError("simulated replace failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", failing_replace)
    try:
        client = TestClient(app)
        headers = _csrf_headers(client)
        restored_db = _make_sqlite_bytes("restored")
        payload = _make_zip(restored_db, "[uploads]\nbackup_restore_max_bytes=20971520\n")
        response = client.post(
            "/admin/restore",
            files={"file": ("backup.zip", payload, "application/zip")},
            headers=headers,
        )
        assert response.status_code == 500
        assert "Restore failed safely" in response.json()["detail"]
        db_path = tmp_path / ".memcoach" / "memcoach.db"
        assert db_path.exists()
        assert not db_path.with_suffix(".db.pre_restore").exists()
        assert not db_path.with_suffix(".db.restore").exists()
        assert db_path.stat().st_size > 0
    finally:
        app.dependency_overrides.clear()
