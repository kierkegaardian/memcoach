from fastapi import APIRouter, Depends, Form, Request, HTTPException, status, Query
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

@router.get("/", response_class=HTMLResponse)
async def list_kids(request: Request, conn = Depends(get_db)):
    """List all kids."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE deleted_at IS NULL ORDER BY name")
    kids = [dict(row) for row in cursor.fetchall()]
    return templates.TemplateResponse("kids/index.html", {"request": request, "kids": kids})

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
        kid_id = cursor.lastrowid
        cursor.execute(
            "INSERT OR IGNORE INTO assignments (kid_id, deck_id) SELECT ?, id FROM decks WHERE deleted_at IS NULL",
            (kid_id,),
        )
        conn.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Kid with this name already exists")

@router.get("/{kid_id}/decks", response_class=HTMLResponse)
async def kid_decks(
    kid_id: int,
    request: Request,
    tag: list[str] = Query(default=[]),
    conn = Depends(get_db),
):
    """List decks for a specific kid (global decks for now)."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid_row = cursor.fetchone()
    if not kid_row:
        raise HTTPException(status_code=404, detail="Kid not found")
    kid = {"id": kid_row[0], "name": kid_row[1]}
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
        "kids/decks.html",
        {
            "request": request,
            "kid": kid,
            "decks": decks,
            "deck_tags": deck_tags,
            "selected_tags": tag,
        },
    )

@router.get("/{kid_id}/row", response_class=HTMLResponse)
async def kid_row(kid_id: int, request: Request, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid = cursor.fetchone()
    if not kid:
        raise HTTPException(status_code=404, detail="Kid not found")
    return templates.TemplateResponse("kids/kid_row.html", {"request": request, "kid": dict(kid)})

@router.get("/{kid_id}/edit", response_class=HTMLResponse)
async def edit_kid_form(kid_id: int, request: Request, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid = cursor.fetchone()
    if not kid:
        raise HTTPException(status_code=404, detail="Kid not found")
    return templates.TemplateResponse("kids/kid_edit_form.html", {"request": request, "kid": dict(kid)})

@router.post("/{kid_id}/edit", response_class=HTMLResponse)
async def edit_kid(kid_id: int, request: Request, name: str = Form(...), conn = Depends(get_db)):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE kids SET name = ? WHERE id = ? AND deleted_at IS NULL",
            (name.strip(), kid_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Kid not found")
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Kid with this name already exists")
    cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid = cursor.fetchone()
    return templates.TemplateResponse("kids/kid_row.html", {"request": request, "kid": dict(kid)})

@router.post("/{kid_id}/delete", response_class=HTMLResponse)
async def delete_kid(kid_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE kids SET deleted_at = datetime('now') WHERE id = ? AND deleted_at IS NULL",
        (kid_id,),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Kid not found")
    conn.commit()
    return HTMLResponse("")
