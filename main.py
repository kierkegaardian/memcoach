import argparse
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager

import sys
from pathlib import Path

# Add project root to path for package imports
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from db.database import init_db
from config import load_config
from routes import kids, decks, cards, review, stats, plan, backups, trash, search, parent, kid_mode, today, reports, stt, bible  # Import routers
from utils.auth import is_parent_unlocked, get_parent_pin_hash
from utils.csrf import (
    CSRF_COOKIE_NAME,
    generate_csrf_token,
    validate_csrf_request,
)

templates = Jinja2Templates(directory=str(base_dir / "templates"))
app = FastAPI(title="MemCoach", description="Local-first memorization app for kids")

app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

# Include routers
app.include_router(kids.router, prefix="/kids", tags=["kids"])
app.include_router(decks.router, prefix="/decks", tags=["decks"])
app.include_router(cards.router, prefix="/decks", tags=["cards"])  # /decks/{deck_id}/cards
app.include_router(review.router, prefix="/review", tags=["review"])
app.include_router(today.router, tags=["today"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(plan.router, prefix="/plan", tags=["plan"])
app.include_router(backups.router, prefix="/admin", tags=["admin"])
app.include_router(trash.router, prefix="/trash", tags=["trash"])
app.include_router(search.router, tags=["search"])
app.include_router(parent.router, prefix="/parent", tags=["parent"])
app.include_router(kid_mode.router, prefix="/kid-mode", tags=["kid-mode"])
app.include_router(stt.router, tags=["stt"])
app.include_router(bible.router, tags=["bible"])

@app.middleware("http")
async def parent_session_middleware(request: Request, call_next):
    request.state.parent_unlocked = is_parent_unlocked(request)
    request.state.parent_pin_configured = bool(get_parent_pin_hash())
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or generate_csrf_token()
    request.state.csrf_token = csrf_token
    try:
        await validate_csrf_request(request)
    except HTTPException as exc:
        response = JSONResponse({"detail": getattr(exc, "detail", "Forbidden")}, status_code=403)
    else:
        response = await call_next(request)
    if request.cookies.get(CSRF_COOKIE_NAME) != csrf_token:
        response.set_cookie(
            CSRF_COOKIE_NAME,
            csrf_token,
            httponly=True,
            samesite="lax",
        )
    return response

# Home page - list kids
@app.get("/", response_class=HTMLResponse)
async def home() -> RedirectResponse:
    return RedirectResponse(url="/kid-mode", status_code=307)

# First-run init
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB and config
    load_config()  # Ensures config exists
    init_db()
    yield
    # Shutdown if needed

app.router.lifespan_context = lifespan  # For auto init on start

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MemCoach App")
    parser.add_argument("--init", action="store_true", help="Initialize DB and config")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode with reload")
    args = parser.parse_args()
    if args.init:
        load_config()  # Ensures config is copied if missing
        init_db()
        print("DB initialized and config copied to ~/.memcoach/")
        exit(0)
    # Run server
    port = 8000
    reload = args.dev
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=reload, log_level="info")
