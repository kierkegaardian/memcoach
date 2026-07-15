import io
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from config import CONFIG_PATH
from db.database import (
    BACKUP_DIR,
    DB_PATH,
    create_backup_archive_bytes,
    create_backup_archive_file,
    get_schema_version_from_db,
)
from db.schema import SCHEMA_VERSION
from utils.auth import require_parent_session
from config import load_config
from utils.uploads import UploadTooLargeError, read_upload_limited

router = APIRouter(dependencies=[Depends(require_parent_session)])
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/backup/manage", response_class=HTMLResponse)
async def backup_admin(request: Request):
    return templates.TemplateResponse(request, "admin/backup.html", {"request": request})

@router.get("/backup")
async def download_backup():
    schema_version = get_schema_version_from_db()
    try:
        data = create_backup_archive_bytes(schema_version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"memcoach-backup-{timestamp}.zip"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(io.BytesIO(data), media_type="application/zip", headers=headers)

@router.post("/restore")
async def restore_backup(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Backup file is required")
    config = load_config()
    max_bytes = int(config.get("uploads", {}).get("backup_restore_max_bytes", 20 * 1024 * 1024))
    try:
        data = await read_upload_limited(file, max_bytes=max_bytes)
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    if not data:
        raise HTTPException(status_code=400, detail="Backup file is empty")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zipf:
            names = set(zipf.namelist())
            if "manifest.json" not in names:
                raise HTTPException(status_code=400, detail="Backup manifest is missing")
            manifest = json.loads(zipf.read("manifest.json"))
            manifest_version = manifest.get("schema_version")
            if manifest_version is None or manifest_version > SCHEMA_VERSION:
                raise HTTPException(
                    status_code=400,
                    detail=f"Schema version mismatch (expected <= {SCHEMA_VERSION}, got {manifest_version})",
                )
            if "memcoach.db" not in names or "config.toml" not in names:
                raise HTTPException(status_code=400, detail="Backup missing required files")
            if DB_PATH.exists() and CONFIG_PATH.exists():
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                safety_path = BACKUP_DIR / f"safety-{timestamp}.zip"
                create_backup_archive_file(safety_path, get_schema_version_from_db())
            with tempfile.TemporaryDirectory() as tmpdir:
                zipf.extract("memcoach.db", tmpdir)
                zipf.extract("config.toml", tmpdir)
                temp_db = Path(tmpdir) / "memcoach.db"
                temp_config = Path(tmpdir) / "config.toml"
                if not temp_db.exists() or not temp_config.exists():
                    raise HTTPException(status_code=400, detail="Backup payload invalid")
                CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                # Validate extracted DB before touching current files.
                test_conn = None
                try:
                    test_conn = sqlite3.connect(temp_db)
                    result = test_conn.execute("PRAGMA integrity_check").fetchone()
                    if not result or str(result[0]).lower() != "ok":
                        raise HTTPException(status_code=400, detail="Backup database integrity check failed")
                except sqlite3.DatabaseError as exc:
                    raise HTTPException(status_code=400, detail="Backup database is invalid") from exc
                finally:
                    if test_conn is not None:
                        test_conn.close()
                staged_db = DB_PATH.with_suffix(".db.restore")
                staged_config = CONFIG_PATH.with_suffix(".toml.restore")
                shutil.copy2(temp_db, staged_db)
                shutil.copy2(temp_config, staged_config)
                original_db_backup = DB_PATH.with_suffix(".db.pre_restore")
                original_config_backup = CONFIG_PATH.with_suffix(".toml.pre_restore")
                db_exists = DB_PATH.exists()
                cfg_exists = CONFIG_PATH.exists()
                try:
                    if db_exists:
                        DB_PATH.with_suffix(".db-wal").unlink(missing_ok=True)
                        DB_PATH.with_suffix(".db-shm").unlink(missing_ok=True)
                        DB_PATH.replace(original_db_backup)
                    if cfg_exists:
                        CONFIG_PATH.replace(original_config_backup)
                    staged_db.replace(DB_PATH)
                    staged_config.replace(CONFIG_PATH)
                    DB_PATH.with_suffix(".db-wal").unlink(missing_ok=True)
                    DB_PATH.with_suffix(".db-shm").unlink(missing_ok=True)
                except OSError as exc:
                    if original_db_backup.exists():
                        original_db_backup.replace(DB_PATH)
                    if original_config_backup.exists():
                        original_config_backup.replace(CONFIG_PATH)
                    staged_db.unlink(missing_ok=True)
                    staged_config.unlink(missing_ok=True)
                    raise HTTPException(status_code=500, detail=f"Restore failed safely: {exc}") from exc
                else:
                    original_db_backup.unlink(missing_ok=True)
                    original_config_backup.unlink(missing_ok=True)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid zip archive") from exc
    return RedirectResponse(url="/admin/backup/manage", status_code=status.HTTP_303_SEE_OTHER)
