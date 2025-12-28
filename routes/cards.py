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

def get_next_card_position(cursor, deck_id: int) -> int:
    cursor.execute(
        "SELECT COALESCE(MAX(position), 0) FROM cards WHERE deck_id = ? AND deleted_at IS NULL",
        (deck_id,),
    )
    return int(cursor.fetchone()[0] or 0) + 1

def get_cards_for_deck(cursor, deck_id: int) -> List[dict]:
    cursor.execute(
        """
        SELECT id, prompt, mastery_status, streak, due_date, position
        FROM cards
        WHERE deck_id = ? AND deleted_at IS NULL
        ORDER BY position, id
        """,
        (deck_id,),
    )
    return [dict(row) for row in cursor.fetchall()]

def get_card_position_flags(cursor, deck_id: int, position: int) -> dict:
    cursor.execute(
        "SELECT 1 FROM cards WHERE deck_id = ? AND deleted_at IS NULL AND position < ? LIMIT 1",
        (deck_id, position),
    )
    has_prev = cursor.fetchone() is not None
    cursor.execute(
        "SELECT 1 FROM cards WHERE deck_id = ? AND deleted_at IS NULL AND position > ? LIMIT 1",
        (deck_id, position),
    )
    has_next = cursor.fetchone() is not None
    return {"is_first": not has_prev, "is_last": not has_next}

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
    cursor.execute("SELECT id, name FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
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
        cursor.execute("SELECT id FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Deck not found")
        if (long_text_title and not long_text_body) or (long_text_body and not long_text_title):
            raise HTTPException(status_code=400, detail="Provide both a title and full text for long text")
        if long_text_title and long_text_body:
            start_position = get_next_card_position(cursor, deck_id)
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
                    INSERT INTO cards (deck_id, prompt, full_text, text_id, chunk_index, interval_days, due_date, ease_factor, streak, mastery_status, position)
                    VALUES (?, ?, ?, ?, ?, 1, date('now'), 2.5, 0, 'new', ?)
                    """,
                    (deck_id, prompt_text, chunk, text_id, index, start_position + index - 1),
                )
            added = len(chunks)
        elif file and file.filename:
            start_position = get_next_card_position(cursor, deck_id)
            if not file.filename.endswith('.txt'):
                raise HTTPException(status_code=400, detail="File must be .txt")
            content = await file.read()
            text = content.decode('utf-8', errors='ignore')
            blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
            for i, block in enumerate(blocks, 1):
                p = f"{prompt_base}{i}: " if len(blocks) > 1 else prompt_base
                f_text = block
                cursor.execute("""
                    INSERT INTO cards (deck_id, prompt, full_text, interval_days, due_date, ease_factor, streak, mastery_status, position)
                    VALUES (?, ?, ?, 1, date('now'), 2.5, 0, 'new', ?)
                """, (deck_id, p, f_text, start_position + i - 1))
                added += 1
        elif prompt and full_text:
            position = get_next_card_position(cursor, deck_id)
            cursor.execute(
                """
                INSERT INTO cards (deck_id, prompt, full_text, interval_days, due_date, ease_factor, streak, mastery_status, position)
                VALUES (?, ?, ?, 1, date('now'), 2.5, 0, 'new', ?)
                """,
                (deck_id, prompt, full_text, position),
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

@router.get("/{deck_id}/cards/{card_id}/row", response_class=HTMLResponse)
async def card_row(deck_id: int, card_id: int, request: Request, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, prompt, mastery_status, streak, due_date, position
        FROM cards
        WHERE id = ? AND deck_id = ? AND deleted_at IS NULL
        """,
        (card_id, deck_id),
    )
    card = cursor.fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    flags = get_card_position_flags(cursor, deck_id, card["position"])
    return templates.TemplateResponse(
        "cards/card_row.html",
        {"request": request, "card": dict(card), "deck_id": deck_id, **flags},
    )

@router.get("/{deck_id}/cards/{card_id}/edit", response_class=HTMLResponse)
async def edit_card_form(deck_id: int, card_id: int, request: Request, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, prompt, full_text FROM cards WHERE id = ? AND deck_id = ? AND deleted_at IS NULL",
        (card_id, deck_id),
    )
    card = cursor.fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return templates.TemplateResponse("cards/card_edit_form.html", {"request": request, "card": dict(card), "deck_id": deck_id})

@router.post("/{deck_id}/cards/{card_id}/edit", response_class=HTMLResponse)
async def edit_card(deck_id: int, card_id: int, request: Request, prompt: str = Form(...), full_text: str = Form(...), conn = Depends(get_db)):
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")
    if not full_text or not full_text.strip():
        raise HTTPException(status_code=400, detail="Full text is required")
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE cards
        SET prompt = ?, full_text = ?
        WHERE id = ? AND deck_id = ? AND deleted_at IS NULL
        """,
        (prompt.strip(), full_text.strip(), card_id, deck_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Card not found")
    conn.commit()
    cursor.execute(
        """
        SELECT id, prompt, mastery_status, streak, due_date, position
        FROM cards
        WHERE id = ? AND deck_id = ? AND deleted_at IS NULL
        """,
        (card_id, deck_id),
    )
    card = cursor.fetchone()
    flags = get_card_position_flags(cursor, deck_id, card["position"])
    return templates.TemplateResponse(
        "cards/card_row.html",
        {"request": request, "card": dict(card), "deck_id": deck_id, **flags},
    )

@router.post("/{deck_id}/cards/{card_id}/delete", response_class=HTMLResponse)
async def delete_card(deck_id: int, card_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE cards SET deleted_at = datetime('now') WHERE id = ? AND deck_id = ? AND deleted_at IS NULL",
        (card_id, deck_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Card not found")
    conn.commit()
    return HTMLResponse("")

@router.post("/{deck_id}/cards/{card_id}/move", response_class=HTMLResponse)
async def move_card(deck_id: int, card_id: int, request: Request, direction: str = Form(...), conn = Depends(get_db)):
    if direction not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="Invalid direction")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, position FROM cards WHERE id = ? AND deck_id = ? AND deleted_at IS NULL",
        (card_id, deck_id),
    )
    current = cursor.fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="Card not found")
    if direction == "up":
        cursor.execute(
            """
            SELECT id, position FROM cards
            WHERE deck_id = ? AND deleted_at IS NULL AND position < ?
            ORDER BY position DESC, id DESC
            LIMIT 1
            """,
            (deck_id, current["position"]),
        )
    else:
        cursor.execute(
            """
            SELECT id, position FROM cards
            WHERE deck_id = ? AND deleted_at IS NULL AND position > ?
            ORDER BY position ASC, id ASC
            LIMIT 1
            """,
            (deck_id, current["position"]),
        )
    neighbor = cursor.fetchone()
    if neighbor:
        cursor.execute(
            "UPDATE cards SET position = ? WHERE id = ?",
            (neighbor["position"], current["id"]),
        )
        cursor.execute(
            "UPDATE cards SET position = ? WHERE id = ?",
            (current["position"], neighbor["id"]),
        )
        conn.commit()
    cards = get_cards_for_deck(cursor, deck_id)
    return templates.TemplateResponse(
        "cards/card_list.html",
        {"request": request, "cards": cards, "deck_id": deck_id},
    )
