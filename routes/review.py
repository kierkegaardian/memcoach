from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from utils.grading import grade_recall
from utils.sm2 import update_sm2, map_grade_to_quality
from utils.mastery import mastery_status_from_streak
from config import load_config
import sqlite3
from typing import Optional, Dict

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

def get_next_card_for_review(kid_id: int, deck_id: int, conn) -> Optional[Dict]:
    """Get next due card for kid and deck (simple: due and not reviewed today)."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.* FROM cards c
        WHERE c.deck_id = ? AND c.due_date <= date('now')
        AND NOT EXISTS (
            SELECT 1 FROM reviews r WHERE r.card_id = c.id AND r.kid_id = ? AND date(r.ts) = date('now')
        )
        ORDER BY c.due_date ASC, random()
        LIMIT 1
    """, (deck_id, kid_id))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None

@router.get("/{kid_id}/{deck_id}", response_class=HTMLResponse)
async def start_review(kid_id: int, deck_id: int, request: Request, conn = Depends(get_db)):
    """Start review session for kid and deck."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ?", (kid_id,))
    kid_row = cursor.fetchone()
    if not kid_row:
        raise HTTPException(status_code=404, detail="Kid not found")
    kid = {"id": kid_row[0], "name": kid_row[1]}
    cursor.execute("SELECT id, name FROM decks WHERE id = ?", (deck_id,))
    deck_row = cursor.fetchone()
    if not deck_row:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck = {"id": deck_row[0], "name": deck_row[1]}
    card = get_next_card_for_review(kid_id, deck_id, conn)
    return templates.TemplateResponse(
        "review.html",
        {"request": request, "kid": kid, "deck": deck, "card": card, "kid_id": kid_id, "deck_id": deck_id}
    )

@router.get("/next")
async def next_card(kid_id: int, deck_id: int, request: Request, conn = Depends(get_db)):
    """HTMX endpoint for next card partial."""
    card = get_next_card_for_review(kid_id, deck_id, conn)
    if card:
        return templates.TemplateResponse("partials/card.html", {"request": request, "card": card, "kid_id": kid_id, "deck_id": deck_id})
    else:
        return templates.TemplateResponse("partials/no_cards.html", {"request": request, "kid_id": kid_id, "deck_id": deck_id})

@router.post("/submit")
async def submit_review(
    kid_id: int,
    deck_id: int,
    card_id: int,
    request: Request,
    user_text: str = Form(...),
    conn = Depends(get_db),
):
    """HTMX endpoint to grade recall, update card/review, return result partial."""
    config = load_config()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    card_row = cursor.fetchone()
    if not card_row:
        raise HTTPException(status_code=404, detail="Card not found")
    card = dict(card_row)
    full_text = card['full_text']
    grade = grade_recall(full_text, user_text, config)
    quality = map_grade_to_quality(grade)
    new_interval, new_ef, new_streak, new_due = update_sm2(
        card['interval_days'], card['ease_factor'], quality, card['streak']
    )
    mastery_status = mastery_status_from_streak(new_streak)
    cursor.execute("""
        UPDATE cards
        SET interval_days = ?, ease_factor = ?, streak = ?, due_date = ?, mastery_status = ?
        WHERE id = ?
    """, (new_interval, new_ef, new_streak, new_due.isoformat(), mastery_status, card_id))
    cursor.execute("""
        INSERT INTO reviews (card_id, kid_id, grade, user_text) VALUES (?, ?, ?, ?)
    """, (card_id, kid_id, grade, user_text))
    conn.commit()
    color_class = {
        'perfect': 'bg-green-100 border-green-400 text-green-800',
        'good': 'bg-yellow-100 border-yellow-400 text-yellow-800',
        'fail': 'bg-red-100 border-red-400 text-red-800'
    }
    return templates.TemplateResponse(
        "partials/review_result.html",
        {
            "request": request,
            "grade": grade,
            "color_class": color_class.get(grade, "bg-gray-100"),
            "user_text": user_text,
            "full_text": full_text,
            "kid_id": kid_id,
            "deck_id": deck_id,
        },
    )
