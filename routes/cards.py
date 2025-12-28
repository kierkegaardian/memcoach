from fastapi import APIRouter, Depends, Form, Request, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from models.card import CardCreate
import sqlite3
from typing import Optional, List
import re

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

def split_long_text(text: str, strategy: str, delimiter: Optional[str]) -> List[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if strategy == "sentences":
        parts = re.split(r"(?<=[.!?])\\s+", cleaned)
    elif strategy == "stanzas":
        parts = re.split(r"\\n\\s*\\n+", cleaned)
    elif strategy == "custom":
        if not delimiter:
            return []
        parts = [part for part in cleaned.split(delimiter)]
    else:
        parts = cleaned.splitlines()
    return [part.strip() for part in parts if part.strip()]

@router.get("/{deck_id}/add", response_class=HTMLResponse)
async def add_card_form(deck_id: int, request: Request, kid_id: Optional[int] = None, conn = Depends(get_db)):
    """Form to add card manually or upload txt file to deck."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM decks WHERE id = ?", (deck_id,))
    deck_row = cursor.fetchone()
    if not deck_row:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck = {"id": deck_row[0], "name": deck_row[1]}
    return templates.TemplateResponse("decks/add_card.html", {"request": request, "deck": deck, "kid_id": kid_id})

@router.post("/{deck_id}/add")
async def add_cards(
    deck_id: int,
    prompt: Optional[str] = Form(None, description="Prompt for manual card"),
    full_text: Optional[str] = Form(None, description="Full text for manual card"),
    long_text_title: Optional[str] = Form(None, description="Title for long text"),
    long_text_body: Optional[str] = Form(None, description="Full long text content"),
    chunk_strategy: Optional[str] = Form("lines", description="Chunking strategy"),
    chunk_delimiter: Optional[str] = Form(None, description="Custom delimiter"),
    file: Optional[UploadFile] = File(None, description="TXT file for multiple cards"),
    prompt_base: Optional[str] = Form("Recite: ", description="Prompt base for uploaded cards"),
    kid_id: Optional[int] = Form(None, description="Kid ID for redirect"),
    conn = Depends(get_db)
):
    """Add single manual card, long text chunks, or multiple from uploaded TXT file (split on blank lines)."""
    cursor = conn.cursor()
    added = 0
    try:
        if (long_text_title and not long_text_body) or (long_text_body and not long_text_title):
            raise HTTPException(status_code=400, detail="Provide both a title and full text for long text")
        if long_text_title and long_text_body:
            strategy = (chunk_strategy or "lines").lower()
            if strategy not in {"lines", "sentences", "stanzas", "custom"}:
                raise HTTPException(status_code=400, detail="Invalid chunking strategy")
            chunks = split_long_text(long_text_body, strategy, chunk_delimiter)
            if not chunks:
                raise HTTPException(status_code=400, detail="Long text could not be split into chunks")
            cursor.execute(
                """
                INSERT INTO texts (deck_id, title, full_text, chunk_strategy, delimiter)
                VALUES (?, ?, ?, ?, ?)
                """,
                (deck_id, long_text_title.strip(), long_text_body.strip(), strategy, chunk_delimiter),
            )
            text_id = cursor.lastrowid
            for index, chunk in enumerate(chunks, 1):
                prompt_text = f"{long_text_title.strip()} (Part {index})"
                cursor.execute(
                    """
                    INSERT INTO cards (deck_id, prompt, full_text, text_id, chunk_index, interval_days, due_date, ease_factor, streak, mastery_status)
                    VALUES (?, ?, ?, ?, ?, 1, date('now'), 2.5, 0, 'new')
                    """,
                    (deck_id, prompt_text, chunk, text_id, index),
                )
            added = len(chunks)
        elif file and file.filename:
            if not file.filename.endswith('.txt'):
                raise HTTPException(status_code=400, detail="File must be .txt")
            content = await file.read()
            text = content.decode('utf-8', errors='ignore')
            blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
            for i, block in enumerate(blocks, 1):
                p = f"{prompt_base}{i}: " if len(blocks) > 1 else prompt_base
                f_text = block
                cursor.execute("""
                    INSERT INTO cards (deck_id, prompt, full_text, interval_days, due_date, ease_factor, streak, mastery_status)
                    VALUES (?, ?, ?, 1, date('now'), 2.5, 0, 'new')
                """, (deck_id, p, f_text))
                added += 1
        elif prompt and full_text:
            cursor.execute(
                """
                INSERT INTO cards (deck_id, prompt, full_text, interval_days, due_date, ease_factor, streak, mastery_status)
                VALUES (?, ?, ?, 1, date('now'), 2.5, 0, 'new')
                """,
                (deck_id, prompt, full_text),
            )
            added = 1
        else:
            raise HTTPException(status_code=400, detail="Provide manual card details, long text, or upload a file")
        conn.commit()
        redirect_target = f"/kids/{kid_id}/decks" if kid_id else "/decks"
        return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add cards: {str(e)}")
