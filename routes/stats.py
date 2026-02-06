from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from db.database import get_db
from utils.mastery import mastery_percent

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/{kid_id}", response_class=HTMLResponse)
async def kid_stats(kid_id: int, request: Request, conn = Depends(get_db)):
    """Stats dashboard for kid: reviews count, success rate, decks activity."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid_row = cursor.fetchone()
    if not kid_row:
        raise HTTPException(status_code=404, detail="Kid not found")
    kid_name = kid_row[0]
    cursor.execute("""
        SELECT grade, COUNT(*) FROM reviews WHERE kid_id = ? GROUP BY grade
    """, (kid_id,))
    grades = dict(cursor.fetchall() or [])
    total_reviews = sum(grades.values())
    perfect = grades.get('perfect', 0)
    good = grades.get('good', 0)
    fail = grades.get('fail', 0)
    success_rate = ((perfect + good) / total_reviews * 100) if total_reviews else 0
    cursor.execute("""
        SELECT d.name, COUNT(r.id) as review_count FROM reviews r 
        JOIN cards c ON r.card_id = c.id 
        JOIN decks d ON c.deck_id = d.id 
        WHERE r.kid_id = ?
        AND c.deleted_at IS NULL
        AND d.deleted_at IS NULL
        GROUP BY d.id, d.name ORDER BY review_count DESC
    """, (kid_id,))
    deck_stats = [{"deck": row[0], "reviews": row[1]} for row in cursor.fetchall()]
    cursor.execute(
        "SELECT MAX(streak) FROM card_progress WHERE kid_id = ?",
        (kid_id,),
    )
    max_streak = cursor.fetchone()[0] or 0
    cursor.execute(
        """
        SELECT d.id, d.name,
            SUM(CASE WHEN COALESCE(cp.mastery_status, 'new') = 'mastered' THEN 1 ELSE 0 END) AS mastered,
            SUM(CASE WHEN COALESCE(cp.mastery_status, 'new') = 'learning' THEN 1 ELSE 0 END) AS learning,
            SUM(CASE WHEN COALESCE(cp.mastery_status, 'new') = 'new' THEN 1 ELSE 0 END) AS new_count,
            COUNT(c.id) AS total
        FROM decks d
        LEFT JOIN cards c ON c.deck_id = d.id AND c.deleted_at IS NULL
        LEFT JOIN card_progress cp ON cp.card_id = c.id AND cp.kid_id = ?
        WHERE d.deleted_at IS NULL
        GROUP BY d.id, d.name
        ORDER BY d.name
        """,
        (kid_id,),
    )
    deck_mastery = []
    for row in cursor.fetchall():
        total = row["total"] or 0
        mastered = row["mastered"] or 0
        deck_mastery.append({
            "deck": row["name"],
            "mastered": mastered,
            "learning": row["learning"] or 0,
            "new": row["new_count"] or 0,
            "total": total,
            "percent_mastered": mastery_percent(mastered, total),
        })
    return templates.TemplateResponse("stats.html", {
        "request": request, 
        "kid_name": kid_name, 
        "total_reviews": total_reviews, 
        "success_rate": round(success_rate, 1), 
        "grades": grades, 
        "deck_stats": deck_stats, 
        "max_streak": max_streak,
        "deck_mastery": deck_mastery,
    })
