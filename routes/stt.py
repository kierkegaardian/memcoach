from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from utils.stt import transcribe_audio

router = APIRouter()


@router.post("/stt")
async def stt_transcribe(audio: UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required")
    suffix = Path(audio.filename).suffix or ".webm"
    data = await audio.read()
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
