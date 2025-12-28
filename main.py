import argparse
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

import sys
from pathlib import Path

# Add project root to path for package imports
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from db.database import init_db, get_db
from config import load_config, CONFIG_DIR
from routes import kids, decks, cards, review, stats, plan, backups  # Import routers

templates = Jinja2Templates(directory=str(base_dir / "templates"))
app = FastAPI(title="MemCoach", description="Local-first memorization app for kids")

app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

# Include routers
app.include_router(kids.router, prefix="/kids", tags=["kids"])
app.include_router(decks.router, prefix="/decks", tags=["decks"])
app.include_router(cards.router, prefix="/decks", tags=["cards"])  # /decks/{deck_id}/cards
app.include_router(review.router, prefix="/review", tags=["review"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(plan.router, prefix="/plan", tags=["plan"])
app.include_router(backups.router, prefix="/admin", tags=["admin"])

# Dependency for DB connection
def get_db_conn():
    yield from get_db()

# Home page - list kids
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, conn = Depends(get_db_conn)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids ORDER BY name")
    kids_list = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    return templates.TemplateResponse("index.html", {"request": request, "kids": kids_list})

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
