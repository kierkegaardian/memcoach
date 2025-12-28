import io
import json
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

router = APIRouter(dependencies=[Depends(require_parent_session)])
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/backup/manage", response_class=HTMLResponse)
async def backup_admin(request: Request):
    return templates.TemplateResponse("admin/backup.html", {"request": request})

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
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Backup file is empty")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zipf:
            names = set(zipf.namelist())
            if "manifest.json" not in names:
                raise HTTPException(status_code=400, detail="Backup manifest is missing")
            manifest = json.loads(zipf.read("manifest.json"))
            manifest_version = manifest.get("schema_version")
            if manifest_version != SCHEMA_VERSION:
                raise HTTPException(
                    status_code=400,
                    detail=f"Schema version mismatch (expected {SCHEMA_VERSION}, got {manifest_version})",
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
                temp_db.replace(DB_PATH)
                temp_config.replace(CONFIG_PATH)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid zip archive") from exc
    return RedirectResponse(url="/admin/backup/manage", status_code=status.HTTP_303_SEE_OTHER)
