from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import load_config
from utils.stt import transcribe_audio
from utils.uploads import UploadTooLargeError, read_upload_limited

router = APIRouter()


def _infer_suffix(filename: str, content_type: str | None) -> str:
    suffix = Path(filename or "").suffix
    if suffix:
        return suffix
    content_type = (content_type or "").lower()
    if "mp4" in content_type or "m4a" in content_type:
        return ".m4a"
    if "ogg" in content_type:
        return ".ogg"
    if "mpeg" in content_type or "mp3" in content_type:
        return ".mp3"
    if "wav" in content_type:
        return ".wav"
    if "webm" in content_type:
        return ".webm"
    return ".webm"


@router.post("/stt")
async def stt_transcribe(audio: UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required")
    suffix = _infer_suffix(audio.filename, audio.content_type)
    config = load_config()
    max_bytes = int(config.get("uploads", {}).get("stt_audio_max_bytes", 25 * 1024 * 1024))
    try:
        data = await read_upload_limited(audio, max_bytes=max_bytes)
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    if not data:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            temp_path = Path(tmp.name)
        text = await transcribe_audio(temp_path)
        return JSONResponse({"text": text})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
