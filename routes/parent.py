from fastapi import APIRouter, Form, Request, status, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from urllib.parse import urlsplit

from utils.auth import (
    SESSION_COOKIE_NAME,
    create_parent_session_cookie,
    get_parent_pin_hash,
    get_parent_session_minutes,
    is_parent_unlocked,
    hash_pin,
    verify_pin,
)
from config import set_parent_pin_hash

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))


def sanitize_next_path(next_path: str) -> str:
    candidate = (next_path or "").strip()
    if "\\" in candidate or not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return "/"
    return candidate


@router.post("/unlock")
async def unlock_parent(pin: str = Form(...), next_path: str = Form("/")):
    safe_next_path = sanitize_next_path(next_path)
    pin_hash = get_parent_pin_hash()
    if not pin_hash or not verify_pin(pin, pin_hash):
        return RedirectResponse(url=safe_next_path, status_code=status.HTTP_303_SEE_OTHER)
    duration = get_parent_session_minutes()
    cookie_value = create_parent_session_cookie(pin_hash, duration)
    response = RedirectResponse(url=safe_next_path, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        cookie_value,
        max_age=duration * 60,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/lock")
async def lock_parent(request: Request, next_path: str = Form("/")):
    response = RedirectResponse(
        url=sanitize_next_path(next_path),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/status")
async def parent_status(request: Request):
    return {"unlocked": is_parent_unlocked(request)}


@router.get("/setup", response_class=HTMLResponse)
async def setup_parent_pin(request: Request):
    pin_hash = get_parent_pin_hash()
    configured = bool(pin_hash)
    if configured and not is_parent_unlocked(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parent session required")
    return templates.TemplateResponse(
        request,
        "parent/setup.html",
        {"request": request, "configured": configured, "error": None},
    )


@router.post("/setup")
async def save_parent_pin(
    request: Request,
    pin: str = Form(...),
    pin_confirm: str = Form(...),
    next_path: str = Form("/"),
):
    safe_next_path = sanitize_next_path(next_path)
    pin_hash_existing = get_parent_pin_hash()
    if pin_hash_existing and not is_parent_unlocked(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parent session required")
    if pin != pin_confirm:
        return templates.TemplateResponse(
            request,
            "parent/setup.html",
            {
                "request": request,
                "configured": bool(pin_hash_existing),
                "error": "PIN entries do not match.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        new_hash = hash_pin(pin)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "parent/setup.html",
            {
                "request": request,
                "configured": bool(pin_hash_existing),
                "error": str(exc),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    set_parent_pin_hash(new_hash)
    duration = get_parent_session_minutes()
    cookie_value = create_parent_session_cookie(new_hash, duration)
    response = RedirectResponse(url=safe_next_path, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        cookie_value,
        max_age=duration * 60,
        httponly=True,
        samesite="lax",
    )
    return response
