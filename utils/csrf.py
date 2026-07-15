from __future__ import annotations

import secrets
from fastapi import HTTPException, Request, status

CSRF_COOKIE_NAME = "memcoach_csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_FORM_FIELD = "csrf_token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


async def validate_csrf_request(request: Request) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if header_token and secrets.compare_digest(header_token, cookie_token):
        return
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("application/x-www-form-urlencoded"):
        form = await request.form()
        form_token = form.get(CSRF_FORM_FIELD)
        if isinstance(form_token, str) and secrets.compare_digest(form_token, cookie_token):
            return
    elif content_type.startswith("multipart/form-data"):
        query_token = request.query_params.get(CSRF_FORM_FIELD)
        # Avoid eagerly parsing large multipart payloads in middleware.
        if isinstance(query_token, str) and secrets.compare_digest(query_token, cookie_token):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")
