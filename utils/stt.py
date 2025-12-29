from __future__ import annotations

import asyncio
import shutil
import threading
from pathlib import Path
from typing import Optional

from config import load_config

_MODEL_LOCK = threading.Lock()
_TRANSCRIBE_LOCK = threading.Lock()
_BACKEND: Optional[dict] = None


def _resolve_stt_config() -> dict:
    config = load_config()
    stt_cfg = config.get("stt", {})
    return {
        "provider": (stt_cfg.get("provider") or "auto").lower(),
        "model": stt_cfg.get("model", "base"),
        "language": stt_cfg.get("language"),
        "device": stt_cfg.get("device", "cpu"),
        "compute_type": stt_cfg.get("compute_type", "int8"),
        "no_speech_threshold": stt_cfg.get("no_speech_threshold", 0.6),
        "log_prob_threshold": stt_cfg.get("log_prob_threshold", -1.0),
        "fallback_no_speech_threshold": stt_cfg.get(
            "fallback_no_speech_threshold", 0.9
        ),
        "fallback_log_prob_threshold": stt_cfg.get(
            "fallback_log_prob_threshold", -5.0
        ),
    }


def _normalize_language(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.lower() in {"auto", "detect", "none"}:
        return None
    return value


def _transcribe_faster_whisper(
    model,
    audio_path: Path,
    *,
    language: Optional[str],
    no_speech_threshold: float,
    log_prob_threshold: float,
) -> str:
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        no_speech_threshold=no_speech_threshold,
        log_prob_threshold=log_prob_threshold,
    )
    text = " ".join(segment.text.strip() for segment in segments if segment.text)
    return text.strip()


def _transcribe_whisper(
    model,
    audio_path: Path,
    *,
    language: Optional[str],
    no_speech_threshold: float,
    log_prob_threshold: float,
) -> str:
    result = model.transcribe(
        str(audio_path),
        fp16=False,
        language=language,
        no_speech_threshold=no_speech_threshold,
        logprob_threshold=log_prob_threshold,
    )
    return (result.get("text") or "").strip()


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required for local transcription.")


def _load_backend() -> dict:
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    with _MODEL_LOCK:
        if _BACKEND is not None:
            return _BACKEND
        cfg = _resolve_stt_config()
        provider = cfg["provider"]
        providers = (
            [provider]
            if provider != "auto"
            else ["faster-whisper", "whisper"]
        )
        last_error: Optional[Exception] = None
        for name in providers:
            if name in {"faster-whisper", "faster_whisper"}:
                try:
                    _require_ffmpeg()
                    from faster_whisper import WhisperModel
                except Exception as exc:  # pragma: no cover - optional dependency
                    last_error = exc
                    continue
                model = WhisperModel(
                    cfg["model"],
                    device=cfg["device"],
                    compute_type=cfg["compute_type"],
                )
                _BACKEND = {"name": "faster-whisper", "model": model, "config": cfg}
                return _BACKEND
            if name == "whisper":
                try:
                    _require_ffmpeg()
                    import whisper
                except Exception as exc:  # pragma: no cover - optional dependency
                    last_error = exc
                    continue
                model = whisper.load_model(cfg["model"])
                _BACKEND = {"name": "whisper", "model": model, "config": cfg}
                return _BACKEND
        if last_error:
            raise RuntimeError(
                "Local transcription is unavailable. Install faster-whisper "
                "or openai-whisper and ensure ffmpeg is installed."
            ) from last_error
        raise RuntimeError("Local transcription is unavailable.")


def _transcribe_sync(audio_path: Path) -> str:
    backend = _load_backend()
    cfg = backend["config"]
    language = _normalize_language(cfg.get("language"))
    with _TRANSCRIBE_LOCK:
        if backend["name"] == "faster-whisper":
            text = _transcribe_faster_whisper(
                backend["model"],
                audio_path,
                language=language,
                no_speech_threshold=cfg.get("no_speech_threshold", 0.6),
                log_prob_threshold=cfg.get("log_prob_threshold", -1.0),
            )
            if text:
                return text
            fallback_text = _transcribe_faster_whisper(
                backend["model"],
                audio_path,
                language=language,
                no_speech_threshold=cfg.get("fallback_no_speech_threshold", 0.9),
                log_prob_threshold=cfg.get("fallback_log_prob_threshold", -5.0),
            )
            return fallback_text
        if backend["name"] == "whisper":
            text = _transcribe_whisper(
                backend["model"],
                audio_path,
                language=language,
                no_speech_threshold=cfg.get("no_speech_threshold", 0.6),
                log_prob_threshold=cfg.get("log_prob_threshold", -1.0),
            )
            if text:
                return text
            fallback_text = _transcribe_whisper(
                backend["model"],
                audio_path,
                language=language,
                no_speech_threshold=cfg.get("fallback_no_speech_threshold", 0.9),
                log_prob_threshold=cfg.get("fallback_log_prob_threshold", -5.0),
            )
            return fallback_text
    raise RuntimeError("Unsupported transcription backend.")


async def transcribe_audio(audio_path: Path) -> str:
    return await asyncio.to_thread(_transcribe_sync, audio_path)
