from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from typing import List, Optional

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))


@router.get("/search", response_class=HTMLResponse)
async def search_cards(
    request: Request,
    q: Optional[str] = None,
    deck_id: Optional[int] = None,
    tag: List[str] = Query(default=[]),
    due_today: bool = False,
    conn = Depends(get_db),
):
    cursor = conn.cursor()
    filters = ["c.deleted_at IS NULL", "d.deleted_at IS NULL"]
    params: List[object] = []

    if deck_id is not None:
        filters.append("c.deck_id = ?")
        params.append(deck_id)

    if due_today:
        filters.append("c.due_date <= date('now')")

    if q:
        filters.append("cards_fts MATCH ?")
        params.append(q)

    if tag:
        placeholders = ",".join("?" for _ in tag)
        filters.append(
            f"""
            c.id IN (
                SELECT ct.card_id
                FROM card_tags ct
                JOIN tags t ON t.id = ct.tag_id
                WHERE t.name IN ({placeholders})
                GROUP BY ct.card_id
                HAVING COUNT(DISTINCT t.name) = ?
            )
            """
        )
        params.extend(tag)
        params.append(len(tag))

    where_clause = " AND ".join(filters)
    fts_join = "JOIN cards_fts ON cards_fts.rowid = c.id" if q else ""

    cursor.execute(
        f"""
        SELECT
            c.id,
            c.prompt,
            c.full_text,
            c.due_date,
            c.mastery_status,
            c.deck_id,
            d.name AS deck_name,
            GROUP_CONCAT(t.name, ',') AS tags
        FROM cards c
        JOIN decks d ON d.id = c.deck_id
        {fts_join}
        LEFT JOIN card_tags ct ON ct.card_id = c.id
        LEFT JOIN tags t ON t.id = ct.tag_id
        WHERE {where_clause}
        GROUP BY c.id
        ORDER BY c.due_date ASC, c.id
        LIMIT 100
        """,
        params,
    )
    cards = []
    for row in cursor.fetchall():
        tags = [tag for tag in (row["tags"] or "").split(",") if tag]
        cards.append({**dict(row), "tags": tags})

    return templates.TemplateResponse(
        "partials/search_results.html",
        {
            "request": request,
            "cards": cards,
        },
    )
