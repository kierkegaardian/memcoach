from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from utils.auth import (
    SESSION_COOKIE_NAME,
    create_parent_session_cookie,
    get_parent_pin_hash,
    get_parent_session_minutes,
    is_parent_unlocked,
    verify_pin,
)

router = APIRouter()


@router.post("/unlock")
async def unlock_parent(pin: str = Form(...), next_path: str = Form("/")):
    pin_hash = get_parent_pin_hash()
    if not pin_hash or not verify_pin(pin, pin_hash):
        return RedirectResponse(url=next_path or "/", status_code=status.HTTP_303_SEE_OTHER)
    duration = get_parent_session_minutes()
    cookie_value = create_parent_session_cookie(pin_hash, duration)
    response = RedirectResponse(url=next_path or "/", status_code=status.HTTP_303_SEE_OTHER)
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
    response = RedirectResponse(url=next_path or "/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/status")
async def parent_status(request: Request):
    return {"unlocked": is_parent_unlocked(request)}
