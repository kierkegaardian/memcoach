from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from utils.auth import require_parent_session

router = APIRouter(dependencies=[Depends(require_parent_session)])
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/", response_class=HTMLResponse)
async def trash_index(request: Request, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, deleted_at FROM kids WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC")
    kids = [dict(row) for row in cursor.fetchall()]
    cursor.execute(
        """
        SELECT d.id, d.name, d.deleted_at,
               (SELECT COUNT(*) FROM cards c WHERE c.deck_id = d.id) AS card_count
        FROM decks d
        WHERE d.deleted_at IS NOT NULL
        ORDER BY d.deleted_at DESC
        """
    )
    decks = [dict(row) for row in cursor.fetchall()]
    cursor.execute(
        """
        SELECT c.id, c.prompt, c.deleted_at, d.name AS deck_name
        FROM cards c
        JOIN decks d ON d.id = c.deck_id
        WHERE c.deleted_at IS NOT NULL
        ORDER BY c.deleted_at DESC
        """
    )
    cards = [dict(row) for row in cursor.fetchall()]
    cursor.execute(
        """
        SELECT t.id, t.title, t.deleted_at, d.name AS deck_name
        FROM texts t
        JOIN decks d ON d.id = t.deck_id
        WHERE t.deleted_at IS NOT NULL
        ORDER BY t.deleted_at DESC
        """
    )
    texts = [dict(row) for row in cursor.fetchall()]
    return templates.TemplateResponse(
        "trash/index.html",
        {"request": request, "kids": kids, "decks": decks, "cards": cards, "texts": texts},
    )

@router.post("/kids/{kid_id}/restore")
async def restore_kid(kid_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("UPDATE kids SET deleted_at = NULL WHERE id = ?", (kid_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Kid not found")
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/kids/{kid_id}/purge")
async def purge_kid(kid_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM kids WHERE id = ?", (kid_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Kid not found")
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/decks/{deck_id}/restore")
async def restore_deck(deck_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("UPDATE decks SET deleted_at = NULL WHERE id = ?", (deck_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Deck not found")
    cursor.execute("UPDATE cards SET deleted_at = NULL WHERE deck_id = ?", (deck_id,))
    cursor.execute("UPDATE texts SET deleted_at = NULL WHERE deck_id = ?", (deck_id,))
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/decks/{deck_id}/purge")
async def purge_deck(deck_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards WHERE deck_id = ?", (deck_id,))
    cursor.execute("DELETE FROM texts WHERE deck_id = ?", (deck_id,))
    cursor.execute("DELETE FROM deck_plans WHERE deck_id = ?", (deck_id,))
    cursor.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Deck not found")
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cards/{card_id}/restore")
async def restore_card(card_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT deck_id, text_id FROM cards WHERE id = ? AND deleted_at IS NOT NULL",
        (card_id,),
    )
    card = cursor.fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    cursor.execute("SELECT deleted_at FROM decks WHERE id = ?", (card["deck_id"],))
    deck = cursor.fetchone()
    if not deck or deck["deleted_at"] is not None:
        raise HTTPException(status_code=400, detail="Deck must be restored first")
    cursor.execute("UPDATE cards SET deleted_at = NULL WHERE id = ?", (card_id,))
    if card["text_id"]:
        cursor.execute("UPDATE texts SET deleted_at = NULL WHERE id = ?", (card["text_id"],))
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cards/{card_id}/purge")
async def purge_card(card_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Card not found")
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/texts/{text_id}/restore")
async def restore_text(text_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT deck_id FROM texts WHERE id = ? AND deleted_at IS NOT NULL", (text_id,))
    text = cursor.fetchone()
    if not text:
        raise HTTPException(status_code=404, detail="Text not found")
    cursor.execute("SELECT deleted_at FROM decks WHERE id = ?", (text["deck_id"],))
    deck = cursor.fetchone()
    if not deck or deck["deleted_at"] is not None:
        raise HTTPException(status_code=400, detail="Deck must be restored first")
    cursor.execute("UPDATE texts SET deleted_at = NULL WHERE id = ?", (text_id,))
    cursor.execute("UPDATE cards SET deleted_at = NULL WHERE text_id = ?", (text_id,))
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/texts/{text_id}/purge")
async def purge_text(text_id: int, conn = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards WHERE text_id = ?", (text_id,))
    cursor.execute("DELETE FROM texts WHERE id = ?", (text_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Text not found")
    conn.commit()
    return RedirectResponse(url="/trash", status_code=status.HTTP_303_SEE_OTHER)
