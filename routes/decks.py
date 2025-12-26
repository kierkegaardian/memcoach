from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from models.deck import DeckCreate
import sqlite3

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/new", response_class=HTMLResponse)
async def new_deck_form(request: Request):
    """Form to create new deck."""
    return templates.TemplateResponse("decks/new.html", {"request": request})

@router.post("/new")
async def create_deck(name: str = Form(..., description="Deck name"), conn = Depends(get_db)):
    """Create new deck in DB."""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    name = name.strip()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO decks (name) VALUES (?)", (name,))
        conn.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Deck with this name already exists")

@router.get("/", response_class=HTMLResponse)
async def list_decks(request: Request, conn = Depends(get_db)):
    """List all decks."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM decks ORDER BY name")
    decks = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    return templates.TemplateResponse("decks/index.html", {"request": request, "decks": decks})
