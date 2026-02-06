from fastapi import APIRouter, Depends, Form, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from utils.grading import grade_recall, token_diff
from utils.hints import (
    build_hint_text,
    build_cloze_text,
    build_first_letters_text,
    normalize_hint_mode,
    HINT_MODE_OPTIONS,
)
from utils.sm2 import update_sm2, map_grade_to_quality
from utils.mastery import mastery_status_from_rules, get_deck_mastery_rules
from utils.progress import (
    compute_progress_from_reviews,
    default_progress,
    get_card_progress,
    upsert_card_progress,
)
from config import load_config
from utils.auth import require_parent_session
from utils.search import normalize_fts_query
import sqlite3
from typing import Optional, Dict, List
from datetime import datetime, timezone

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))
templates.env.globals["token_diff"] = token_diff

def get_deck_review_mode(conn, deck_id: int) -> str:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT review_mode FROM decks WHERE id = ? AND deleted_at IS NULL",
        (deck_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deck not found")
    return row[0] or "free_recall"

def get_next_card_for_review(
    kid_id: int,
    deck_id: int,
    conn,
    group_texts: bool = False,
    search_query: Optional[str] = None,
    tag_filters: Optional[List[str]] = None,
) -> Optional[Dict]:
    """Get next due card for kid and deck (simple: due and not reviewed today)."""
    cursor = conn.cursor()
    filters = [
        "c.deck_id = ?",
        "date(COALESCE(cp.due_date, date('now'))) <= date('now')",
        "c.deleted_at IS NULL",
        "(c.text_id IS NULL OR t.deleted_at IS NULL)",
        "NOT EXISTS (SELECT 1 FROM reviews r WHERE r.card_id = c.id AND r.kid_id = ? AND date(r.ts) = date('now'))",
    ]
    params: List[object] = [deck_id, kid_id]
    fts_join = ""
    if search_query:
        fts_query = normalize_fts_query(search_query)
        if fts_query == "":
            return None
        if fts_query:
            filters.append("cards_fts MATCH ?")
            params.append(fts_query)
            fts_join = "JOIN cards_fts ON cards_fts.rowid = c.id"
    if tag_filters:
        placeholders = ",".join("?" for _ in tag_filters)
        filters.append(
            f"""
            c.id IN (
                SELECT ct2.card_id
                FROM card_tags ct2
                JOIN tags t2 ON t2.id = ct2.tag_id
                WHERE t2.name IN ({placeholders})
                GROUP BY ct2.card_id
                HAVING COUNT(DISTINCT t2.name) = ?
            )
            """
        )
        params.extend(tag_filters)
        params.append(len(tag_filters))
    where_clause = " AND ".join(filters)
    order_clause = (
        "ORDER BY date(COALESCE(cp.due_date, date('now'))) ASC, (c.text_id IS NULL), c.text_id, c.chunk_index"
        if group_texts
        else "ORDER BY date(COALESCE(cp.due_date, date('now'))) ASC, random()"
    )
    cursor.execute(
        f"""
        SELECT
            c.*,
            COALESCE(cp.due_date, date('now')) AS due_date,
            COALESCE(cp.interval_days, 1) AS interval_days,
            COALESCE(cp.ease_factor, 2.5) AS ease_factor,
            COALESCE(cp.streak, 0) AS streak,
            COALESCE(cp.mastery_status, 'new') AS mastery_status,
            t.title AS text_title,
            (
                SELECT COUNT(*) FROM cards c2 WHERE c2.text_id = c.text_id
            ) AS text_total,
            (
                SELECT GROUP_CONCAT(t2.name, ',')
                FROM card_tags ct2
                JOIN tags t2 ON t2.id = ct2.tag_id
                WHERE ct2.card_id = c.id
            ) AS tags
        FROM cards c
        LEFT JOIN texts t ON t.id = c.text_id
        LEFT JOIN card_progress cp ON cp.card_id = c.id AND cp.kid_id = ?
        {fts_join}
        WHERE {where_clause}
        {order_clause}
        LIMIT 1
        """,
        [kid_id, *params],
    )
    row = cursor.fetchone()
    if row:
        card = dict(row)
        card["tags"] = [tag for tag in (card.get("tags") or "").split(",") if tag]
        return card
    return None

@router.get("/{kid_id}/{deck_id}", response_class=HTMLResponse)
async def start_review(kid_id: int, deck_id: int, request: Request, conn = Depends(get_db)):
    """Start review session for kid and deck."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid_row = cursor.fetchone()
    if not kid_row:
        raise HTTPException(status_code=404, detail="Kid not found")
    kid = {"id": kid_row[0], "name": kid_row[1]}
    cursor.execute("SELECT id, name, review_mode FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
    deck_row = cursor.fetchone()
    if not deck_row:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck = {"id": deck_row[0], "name": deck_row[1], "review_mode": deck_row[2] or "free_recall"}
    cursor.execute(
        """
        SELECT DISTINCT t.name
        FROM tags t
        JOIN card_tags ct ON ct.tag_id = t.id
        JOIN cards c ON c.id = ct.card_id
        WHERE c.deck_id = ? AND c.deleted_at IS NULL
        ORDER BY t.name
        """,
        (deck_id,),
    )
    deck_tags = [row[0] for row in cursor.fetchall()]
    hint_mode = normalize_hint_mode(request.query_params.get("hint_mode"))
    group_texts = request.query_params.get("group_texts") == "1"
    apply_filters = request.query_params.get("apply_filters") == "1"
    search_query = (request.query_params.get("q") or "").strip()
    selected_tags = [tag for tag in request.query_params.getlist("tag") if tag]
    review_mode = deck["review_mode"]
    card = get_next_card_for_review(
        kid_id,
        deck_id,
        conn,
        group_texts=group_texts,
        search_query=search_query if apply_filters else None,
        tag_filters=selected_tags if apply_filters else None,
    )
    hint_text = build_hint_text(card["full_text"], hint_mode) if card and review_mode == "free_recall" else ""
    masked_text = build_cloze_text(card["full_text"]) if card and review_mode == "cloze" else ""
    initials_text = build_first_letters_text(card["full_text"]) if card and review_mode == "first_letters" else ""
    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "kid": kid,
            "deck": deck,
            "card": card,
            "kid_id": kid_id,
            "deck_id": deck_id,
            "hint_mode": hint_mode,
            "hint_text": hint_text,
            "hint_modes": HINT_MODE_OPTIONS,
            "group_texts": group_texts,
            "deck_tags": deck_tags,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "review_mode": review_mode,
            "masked_text": masked_text,
            "initials_text": initials_text,
            "apply_filters": apply_filters,
            "search_query": search_query,
            "selected_tags": selected_tags,
        },
    )

@router.get("/next")
async def next_card(kid_id: int, deck_id: int, request: Request, conn = Depends(get_db)):
    """HTMX endpoint for next card partial."""
    hint_mode = normalize_hint_mode(request.query_params.get("hint_mode"))
    group_texts = request.query_params.get("group_texts") == "1"
    apply_filters = request.query_params.get("apply_filters") == "1"
    search_query = (request.query_params.get("q") or "").strip()
    selected_tags = [tag for tag in request.query_params.getlist("tag") if tag]
    review_mode = get_deck_review_mode(conn, deck_id)
    card = get_next_card_for_review(
        kid_id,
        deck_id,
        conn,
        group_texts=group_texts,
        search_query=search_query if apply_filters else None,
        tag_filters=selected_tags if apply_filters else None,
    )
    if card:
        return templates.TemplateResponse(
            "partials/card.html",
            {
                "request": request,
                "card": card,
                "kid_id": kid_id,
                "deck_id": deck_id,
                "hint_mode": hint_mode,
                "hint_text": build_hint_text(card["full_text"], hint_mode) if review_mode == "free_recall" else "",
                "hint_modes": HINT_MODE_OPTIONS,
                "group_texts": group_texts,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "review_mode": review_mode,
                "masked_text": build_cloze_text(card["full_text"]) if review_mode == "cloze" else "",
                "initials_text": build_first_letters_text(card["full_text"]) if review_mode == "first_letters" else "",
                "apply_filters": apply_filters,
                "search_query": search_query,
                "selected_tags": selected_tags,
            },
        )
    else:
        return templates.TemplateResponse(
            "partials/no_cards.html",
            {"request": request, "kid_id": kid_id, "deck_id": deck_id, "group_texts": group_texts},
        )


@router.get("/hint", response_class=HTMLResponse)
async def hint_text(card_id: int, hint_mode: str = "none", conn = Depends(get_db)):
    """HTMX endpoint for hint text updates."""
    cursor = conn.cursor()
    cursor.execute("SELECT full_text FROM cards WHERE id = ? AND deleted_at IS NULL", (card_id,))
    card_row = cursor.fetchone()
    if not card_row:
        raise HTTPException(status_code=404, detail="Card not found")
    full_text = card_row[0]
    hint_mode = normalize_hint_mode(hint_mode)
    hint_text_value = build_hint_text(full_text, hint_mode)
    return HTMLResponse(hint_text_value or "No hint is shown for this card.")

@router.post("/submit")
async def submit_review(
    kid_id: int,
    deck_id: int,
    card_id: int,
    request: Request,
    user_text: str = Form(""),
    hint_mode: str = Form("none"),
    parent_grade: Optional[str] = Form(None),
    group_texts: str = Form("0"),
    started_at: Optional[str] = Form(None),
    apply_filters: str = Form("0"),
    q: Optional[str] = Form(None),
    tag: List[str] = Form([]),
    conn = Depends(get_db),
):
    """HTMX endpoint to grade recall, update card/review, return result partial."""
    config = load_config()
    cursor = conn.cursor()
    cursor.execute("SELECT review_mode FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
    deck_row = cursor.fetchone()
    if not deck_row:
        raise HTTPException(status_code=404, detail="Deck not found")
    review_mode = deck_row[0] or "free_recall"
    cursor.execute("SELECT * FROM cards WHERE id = ? AND deleted_at IS NULL", (card_id,))
    card_row = cursor.fetchone()
    if not card_row:
        raise HTTPException(status_code=404, detail="Card not found")
    card = dict(card_row)
    full_text = card['full_text']
    hint_mode = normalize_hint_mode(hint_mode)
    if review_mode == "recitation":
        require_parent_session(request)
        if parent_grade is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent grade required")
        try:
            quality = int(parent_grade)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent grade")
        if quality < 0 or quality > 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent grade")
        if quality >= 4:
            grade = "perfect"
        elif quality >= 3:
            grade = "good"
        else:
            grade = "fail"
        user_text = user_text or ""
        auto_grade = None
        final_grade = grade
        graded_by = "parent"
    else:
        auto_grade = grade_recall(full_text, user_text, config)
        final_grade = auto_grade
        graded_by = "auto"
        quality = map_grade_to_quality(final_grade)
    progress = get_card_progress(conn, kid_id, card_id) or default_progress()
    new_interval, new_ef, new_streak, new_due = update_sm2(
        progress.interval_days, progress.ease_factor, quality, progress.streak
    )
    mastery_rules = get_deck_mastery_rules(conn, deck_id)
    mastery_status = mastery_status_from_rules(
        new_streak,
        new_ef,
        new_interval,
        mastery_rules,
    )
    review_ts = datetime.now(timezone.utc).isoformat()
    duration_seconds = None
    if started_at:
        try:
            started = datetime.fromisoformat(started_at)
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            duration_seconds = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
        except ValueError:
            duration_seconds = None
    cursor.execute("""
        INSERT INTO reviews (
            card_id,
            kid_id,
            grade,
            auto_grade,
            final_grade,
            graded_by,
            review_mode,
            user_text,
            hint_mode,
            duration_seconds
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        card_id,
        kid_id,
        final_grade,
        auto_grade,
        final_grade,
        graded_by,
        review_mode,
        user_text,
        hint_mode,
        duration_seconds,
    ))
    review_id = cursor.lastrowid
    upsert_card_progress(
        conn,
        kid_id=kid_id,
        card_id=card_id,
        interval_days=new_interval,
        due_date=new_due.isoformat(),
        ease_factor=new_ef,
        streak=new_streak,
        mastery_status=mastery_status,
        last_review_ts=review_ts,
    )
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
            "grade": final_grade,
            "auto_grade": auto_grade,
            "final_grade": final_grade,
            "graded_by": graded_by,
            "color_class": color_class.get(final_grade, "bg-gray-100"),
            "user_text": user_text,
            "full_text": full_text,
            "kid_id": kid_id,
            "deck_id": deck_id,
            "hint_mode": hint_mode,
            "group_texts": group_texts == "1",
            "review_id": review_id,
            "apply_filters": apply_filters == "1",
            "search_query": (q or "").strip(),
            "selected_tags": [t for t in tag if t],
        },
    )

@router.post("/override", response_class=HTMLResponse)
async def override_review_grade(
    request: Request,
    review_id: int = Form(...),
    grade: str = Form(...),
    group_texts: str = Form("0"),
    apply_filters: str = Form("0"),
    q: Optional[str] = Form(None),
    tag: List[str] = Form([]),
    conn = Depends(get_db),
):
    """HTMX endpoint to override auto-grade with parent input."""
    require_parent_session(request)
    if grade not in {"perfect", "good", "fail"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grade")
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE reviews
        SET final_grade = ?, grade = ?, graded_by = 'parent'
        WHERE id = ?
        """,
        (grade, grade, review_id),
    )
    cursor.execute(
        """
        SELECT r.card_id,
               r.user_text,
               r.hint_mode,
               r.kid_id,
               r.auto_grade,
               r.final_grade,
               r.graded_by,
               c.full_text,
               c.deck_id
        FROM reviews r
        JOIN cards c ON c.id = r.card_id
        WHERE r.id = ?
        """,
        (review_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    progress = compute_progress_from_reviews(conn, row["kid_id"], row["card_id"])
    if progress:
        upsert_card_progress(
            conn,
            kid_id=row["kid_id"],
            card_id=row["card_id"],
            interval_days=progress.interval_days,
            due_date=progress.due_date,
            ease_factor=progress.ease_factor,
            streak=progress.streak,
            mastery_status=progress.mastery_status,
            last_review_ts=progress.last_review_ts,
        )
    conn.commit()
    color_class = {
        "perfect": "bg-green-100 border-green-400 text-green-800",
        "good": "bg-yellow-100 border-yellow-400 text-yellow-800",
        "fail": "bg-red-100 border-red-400 text-red-800",
    }
    return templates.TemplateResponse(
        "partials/review_result.html",
        {
            "request": request,
            "grade": row["final_grade"],
            "auto_grade": row["auto_grade"],
            "final_grade": row["final_grade"],
            "graded_by": row["graded_by"],
            "color_class": color_class.get(row["final_grade"], "bg-gray-100"),
            "user_text": row["user_text"] or "",
            "full_text": row["full_text"],
            "kid_id": row["kid_id"],
            "deck_id": row["deck_id"],
            "hint_mode": row["hint_mode"],
            "group_texts": group_texts == "1",
            "review_id": review_id,
            "apply_filters": apply_filters == "1",
            "search_query": (q or "").strip(),
            "selected_tags": [t for t in tag if t],
        },
    )
