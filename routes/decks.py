from fastapi import APIRouter, Depends, Form, Request, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from models.deck import DeckCreate
import sqlite3
from utils.mastery import mastery_percent
from utils.auth import require_parent_session
from typing import Optional
from utils.tags import parse_tag_names, set_deck_tags

router = APIRouter(dependencies=[Depends(require_parent_session)])
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
        deck_id = cursor.lastrowid
        cursor.execute(
            "INSERT OR IGNORE INTO assignments (kid_id, deck_id) SELECT id, ? FROM kids WHERE deleted_at IS NULL",
            (deck_id,),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO deck_mastery_rules (deck_id) VALUES (?)",
            (deck_id,),
        )
        conn.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Deck with this name already exists")

@router.get("/", response_class=HTMLResponse)
async def list_decks(
    request: Request,
    tag: list[str] = Query(default=[]),
    conn = Depends(get_db),
):
    """List all decks."""
    cursor = conn.cursor()
    filters = ["d.deleted_at IS NULL"]
    params: list[object] = []
    if tag:
        placeholders = ",".join("?" for _ in tag)
        filters.append(
            f"""
            d.id IN (
                SELECT dt.deck_id
                FROM deck_tags dt
                JOIN tags t ON t.id = dt.tag_id
                WHERE t.name IN ({placeholders})
                GROUP BY dt.deck_id
                HAVING COUNT(DISTINCT t.name) = ?
            )
            """
        )
        params.extend(tag)
        params.append(len(tag))
    where_clause = " AND ".join(filters)
    cursor.execute(
        f"""
        SELECT d.id, d.name, GROUP_CONCAT(t.name, ',') AS tags
        FROM decks d
        LEFT JOIN deck_tags dt ON dt.deck_id = d.id
        LEFT JOIN tags t ON t.id = dt.tag_id
        WHERE {where_clause}
        GROUP BY d.id
        ORDER BY d.name
        """,
        params,
    )
    decks = []
    for row in cursor.fetchall():
        deck = dict(row)
        deck["tags"] = [tag for tag in (deck.get("tags") or "").split(",") if tag]
        decks.append(deck)
    cursor.execute(
        """
        SELECT DISTINCT t.name
        FROM tags t
        JOIN deck_tags dt ON dt.tag_id = t.id
        ORDER BY t.name
        """
    )
    deck_tags = [row[0] for row in cursor.fetchall()]
    return templates.TemplateResponse(
        "decks/index.html",
        {"request": request, "decks": decks, "deck_tags": deck_tags, "selected_tags": tag},
    )

@router.get("/{deck_id}", response_class=HTMLResponse)
async def deck_detail(deck_id: int, request: Request, kid_id: Optional[int] = None, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
    deck_row = cursor.fetchone()
    if not deck_row:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck = {"id": deck_row[0], "name": deck_row[1]}
    cursor.execute(
        """
        SELECT t.name
        FROM deck_tags dt
        JOIN tags t ON t.id = dt.tag_id
        WHERE dt.deck_id = ?
        ORDER BY t.name
        """,
        (deck_id,),
    )
    deck_tag_names = [row[0] for row in cursor.fetchall()]
    deck_tags_text = ", ".join(deck_tag_names)
    cursor.execute("""
        SELECT
            c.id,
            c.prompt,
            c.mastery_status,
            c.streak,
            c.due_date,
            c.position,
            GROUP_CONCAT(t.name, ',') AS tags
        FROM cards c
        LEFT JOIN card_tags ct ON ct.card_id = c.id
        LEFT JOIN tags t ON t.id = ct.tag_id
        WHERE c.deck_id = ? AND c.deleted_at IS NULL
        GROUP BY c.id
        ORDER BY c.position, c.id
    """, (deck_id,))
    cards = []
    for row in cursor.fetchall():
        card = dict(row)
        card["tags"] = [tag for tag in (card.get("tags") or "").split(",") if tag]
        cards.append(card)
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
    card_tags = [row[0] for row in cursor.fetchall()]
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
            "deck_tags": deck_tag_names,
            "deck_tags_text": deck_tags_text,
            "card_tags": card_tags,
        },
    )

@router.get("/{deck_id}/row", response_class=HTMLResponse)
async def deck_row(deck_id: int, request: Request, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
    deck = cursor.fetchone()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return templates.TemplateResponse("decks/deck_row.html", {"request": request, "deck": dict(deck)})

@router.get("/{deck_id}/edit", response_class=HTMLResponse)
async def edit_deck_form(deck_id: int, request: Request, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
    deck = cursor.fetchone()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return templates.TemplateResponse("decks/deck_edit_form.html", {"request": request, "deck": dict(deck)})

@router.post("/{deck_id}/edit", response_class=HTMLResponse)
async def edit_deck(deck_id: int, request: Request, name: str = Form(...), conn = Depends(get_db)):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE decks SET name = ? WHERE id = ? AND deleted_at IS NULL",
            (name.strip(), deck_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Deck not found")
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Deck with this name already exists")
    cursor.execute("SELECT id, name FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
    deck = cursor.fetchone()
    return templates.TemplateResponse("decks/deck_row.html", {"request": request, "deck": dict(deck)})

@router.post("/{deck_id}/delete", response_class=HTMLResponse)
async def delete_deck(deck_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE decks SET deleted_at = datetime('now') WHERE id = ? AND deleted_at IS NULL",
        (deck_id,),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Deck not found")
    cursor.execute(
        "UPDATE cards SET deleted_at = datetime('now') WHERE deck_id = ? AND deleted_at IS NULL",
        (deck_id,),
    )
    cursor.execute(
        "UPDATE texts SET deleted_at = datetime('now') WHERE deck_id = ? AND deleted_at IS NULL",
        (deck_id,),
    )
    conn.commit()
    return HTMLResponse("")

@router.post("/{deck_id}/tags")
async def update_deck_tags(
    deck_id: int,
    tags: str = Form(""),
    kid_id: Optional[int] = Form(None),
    conn = Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM decks WHERE id = ? AND deleted_at IS NULL", (deck_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Deck not found")
    tag_names = parse_tag_names(tags)
    set_deck_tags(conn, deck_id, tag_names)
    conn.commit()
    redirect_target = f"/decks/{deck_id}?kid_id={kid_id}" if kid_id else f"/decks/{deck_id}"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)
