from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from config import load_config

SESSION_COOKIE_NAME = "parent_session"
PIN_HASH_ALGO = "pbkdf2_sha256"
PIN_HASH_ITERATIONS = 200_000
DEFAULT_SESSION_MINUTES = 30


def _get_parent_config() -> dict:
    config = load_config()
    return config.get("parent", {})


def get_parent_pin_hash() -> Optional[str]:
    parent_cfg = _get_parent_config()
    pin_hash = parent_cfg.get("pin_hash")
    return pin_hash or None


def get_parent_session_minutes() -> int:
    parent_cfg = _get_parent_config()
    minutes = parent_cfg.get("session_minutes", DEFAULT_SESSION_MINUTES)
    try:
        return int(minutes)
    except (TypeError, ValueError):
        return DEFAULT_SESSION_MINUTES


def hash_pin(pin: str) -> str:
    pin_clean = pin.strip()
    if not pin_clean:
        raise ValueError("PIN cannot be empty")
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        pin_clean.encode("utf-8"),
        salt.encode("utf-8"),
        PIN_HASH_ITERATIONS,
    )
    digest = base64.urlsafe_b64encode(dk).decode("utf-8")
    return f"{PIN_HASH_ALGO}${PIN_HASH_ITERATIONS}${salt}${digest}"


def verify_pin(pin: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        algo, iterations_str, salt, digest = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algo != PIN_HASH_ALGO:
        return False
    try:
        iterations = int(iterations_str)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        pin.strip().encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    computed = base64.urlsafe_b64encode(dk).decode("utf-8")
    return hmac.compare_digest(computed, digest)


def _session_secret(pin_hash: str) -> bytes:
    return hashlib.sha256(pin_hash.encode("utf-8")).digest()


def create_parent_session_cookie(pin_hash: str, duration_minutes: int) -> str:
    expires_at = int(time.time()) + int(duration_minutes) * 60
    payload = str(expires_at)
    secret = _session_secret(pin_hash)
    signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_parent_session_cookie(cookie_value: Optional[str], pin_hash: Optional[str]) -> bool:
    if not cookie_value or not pin_hash:
        return False
    try:
        payload, signature = cookie_value.split(":", 1)
    except ValueError:
        return False
    secret = _session_secret(pin_hash)
    expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        expires_at = int(payload)
    except ValueError:
        return False
    return expires_at >= int(time.time())


def is_parent_unlocked(request: Request) -> bool:
    pin_hash = get_parent_pin_hash()
    if not pin_hash:
        return False
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    return verify_parent_session_cookie(cookie_value, pin_hash)


def require_parent_session(request: Request) -> None:
    if is_parent_unlocked(request):
        return None
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parent session required")
