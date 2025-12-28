from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from models.deck import DeckCreate
import sqlite3
from utils.mastery import mastery_percent
from typing import Optional

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

@router.get("/{deck_id}", response_class=HTMLResponse)
async def deck_detail(deck_id: int, request: Request, kid_id: Optional[int] = None, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM decks WHERE id = ?", (deck_id,))
    deck_row = cursor.fetchone()
    if not deck_row:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck = {"id": deck_row[0], "name": deck_row[1]}
    cursor.execute("""
        SELECT id, prompt, mastery_status, streak, due_date
        FROM cards
        WHERE deck_id = ?
        ORDER BY id
    """, (deck_id,))
    cards = [dict(row) for row in cursor.fetchall()]
    mastered = sum(1 for card in cards if card["mastery_status"] == "mastered")
    total = len(cards)
    percent_mastered = mastery_percent(mastered, total)
    return templates.TemplateResponse(
        "decks/detail.html",
        {
            "request": request,
            "deck": deck,
            "cards": cards,
            "percent_mastered": percent_mastered,
            "mastered_count": mastered,
            "total_cards": total,
            "kid_id": kid_id,
        },
    )
