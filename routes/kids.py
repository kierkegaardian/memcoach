from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from models.kid import KidCreate
from config import load_config  # For future use
import sqlite3

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/new", response_class=HTMLResponse)
async def new_kid_form(request: Request):
    """Form to add new kid."""
    return templates.TemplateResponse("kids/new.html", {"request": request})

@router.post("/new")
async def create_kid(name: str = Form(..., description="Kid's name"), conn = Depends(get_db)):
    """Create a new kid in DB."""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    name = name.strip()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO kids (name) VALUES (?)", (name,))
        conn.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Kid with this name already exists")

@router.get("/{kid_id}/decks", response_class=HTMLResponse)
async def kid_decks(kid_id: int, request: Request, conn = Depends(get_db)):
    """List decks for a specific kid (global decks for now)."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ?", (kid_id,))
    kid_row = cursor.fetchone()
    if not kid_row:
        raise HTTPException(status_code=404, detail="Kid not found")
    kid = {"id": kid_row[0], "name": kid_row[1]}
    cursor.execute("SELECT id, name FROM decks ORDER BY name")
    decks = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    return templates.TemplateResponse("kids/decks.html", {"request": request, "kid": kid, "decks": decks})
