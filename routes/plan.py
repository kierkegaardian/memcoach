from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Form, Request, Query, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db.database import get_db
from utils.auth import require_parent_session

router = APIRouter(dependencies=[Depends(require_parent_session)])
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _week_starts(anchor: date, weeks: int = 8) -> List[date]:
    week_start = anchor - timedelta(days=anchor.weekday())
    return [week_start + timedelta(weeks=offset) for offset in range(weeks)]


@router.get("/", response_class=HTMLResponse)
async def plan_view(
    request: Request,
    kid_id: Optional[int] = Query(default=None),
    conn=Depends(get_db),
):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE deleted_at IS NULL ORDER BY name")
    kids = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    selected_kid = None
    if kid_id is not None:
        cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Kid not found")
        selected_kid = {"id": row[0], "name": row[1]}
    cursor.execute("SELECT id, name FROM decks WHERE deleted_at IS NULL ORDER BY name")
    deck_rows = cursor.fetchall()
    decks = [{"id": row[0], "name": row[1]} for row in deck_rows]

    cursor.execute("SELECT deck_id, weekly_goal, target_date FROM deck_plans")
    plan_rows = cursor.fetchall()
    plan_map = {
        row[0]: {
            "weekly_goal": row[1],
            "target_date": row[2],
        }
        for row in plan_rows
    }

    card_rows = []
    if selected_kid:
        cursor.execute(
            """
            SELECT c.id, c.deck_id, c.prompt, c.full_text,
                   COALESCE(cp.due_date, date('now')) AS due_date,
                   d.name
            FROM cards c
            JOIN decks d ON c.deck_id = d.id
            LEFT JOIN card_progress cp ON cp.card_id = c.id AND cp.kid_id = ?
            WHERE date(COALESCE(cp.due_date, date('now'))) >= date('now')
            AND c.deleted_at IS NULL
            AND d.deleted_at IS NULL
            ORDER BY d.name, date(COALESCE(cp.due_date, date('now')))
            """,
            (kid_id,),
        )
        card_rows = cursor.fetchall()

    cards_by_deck: Dict[int, List[dict]] = {deck["id"]: [] for deck in decks}
    for row in card_rows:
        due = _parse_date(row[4])
        cards_by_deck.setdefault(row[1], []).append(
            {
                "id": row[0],
                "prompt": row[2],
                "full_text": row[3],
                "due_date": due,
                "deck_name": row[5],
            }
        )

    today = date.today()
    weeks = _week_starts(today, weeks=8)
    week_labels = [
        {
            "start": week_start,
            "end": week_start + timedelta(days=6),
        }
        for week_start in weeks
    ]

    deck_views = []
    for deck in decks:
        deck_cards = cards_by_deck.get(deck["id"], [])
        forecast = [0 for _ in weeks]
        for card in deck_cards:
            if not card["due_date"]:
                continue
            delta_days = (card["due_date"] - weeks[0]).days
            if delta_days < 0:
                continue
            index = delta_days // 7
            if 0 <= index < len(forecast):
                forecast[index] += 1

        plan = plan_map.get(deck["id"], {})
        deck_views.append(
            {
                "id": deck["id"],
                "name": deck["name"],
                "weekly_goal": plan.get("weekly_goal"),
                "target_date": plan.get("target_date"),
                "cards": deck_cards,
                "forecast": forecast,
            }
        )

    return templates.TemplateResponse(
        "plan.html",
        {
            "request": request,
            "deck_views": deck_views,
            "week_labels": week_labels,
            "kids": kids,
            "selected_kid": selected_kid,
        },
    )


@router.post("/settings")
async def update_plan_settings(
    deck_id: int = Form(...),
    weekly_goal: Optional[int] = Form(None),
    target_date: Optional[str] = Form(None),
    kid_id: Optional[int] = Form(None),
    conn=Depends(get_db),
):
    cleaned_goal = int(weekly_goal) if weekly_goal not in (None, "") else None
    cleaned_target = target_date or None
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO deck_plans (deck_id, weekly_goal, target_date)
        VALUES (?, ?, ?)
        ON CONFLICT(deck_id) DO UPDATE SET
            weekly_goal = excluded.weekly_goal,
            target_date = excluded.target_date
        """,
        (deck_id, cleaned_goal, cleaned_target),
    )
    conn.commit()
    redirect_url = f"/plan?kid_id={kid_id}" if kid_id else "/plan"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
