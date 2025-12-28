from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from db.database import get_db

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))


@router.get("/", response_class=HTMLResponse)
async def kid_mode_home(request: Request, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE deleted_at IS NULL ORDER BY name")
    kids = [dict(row) for row in cursor.fetchall()]
    return templates.TemplateResponse("kid_mode.html", {"request": request, "kids": kids})


@router.get("/{kid_id}", response_class=HTMLResponse)
async def kid_mode_decks(kid_id: int, request: Request, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid_row = cursor.fetchone()
    if not kid_row:
        raise HTTPException(status_code=404, detail="Kid not found")
    kid = {"id": kid_row[0], "name": kid_row[1]}
    cursor.execute(
        """
        SELECT d.id, d.name
        FROM decks d
        WHERE d.deleted_at IS NULL
        ORDER BY d.name
        """
    )
    decks = [dict(row) for row in cursor.fetchall()]
    return templates.TemplateResponse(
        "kid_mode_decks.html",
        {"request": request, "kid": kid, "decks": decks},
    )
