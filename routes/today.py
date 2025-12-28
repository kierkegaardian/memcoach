from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db.database import get_db
from utils.grading import grade_recall
from utils.hints import HINT_MODE_OPTIONS, build_hint_text, normalize_hint_mode
from utils.mastery import mastery_status_from_streak
from utils.sm2 import map_grade_to_quality, update_sm2
from config import load_config

router = APIRouter()
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_days_of_week(value: Optional[str]) -> Optional[List[int]]:
    if not value:
        return None
    days: List[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            day = int(item)
        except ValueError:
            continue
        if 0 <= day <= 6:
            days.append(day)
    return days or None


def format_days_of_week(value: Optional[str]) -> str:
    days = parse_days_of_week(value)
    if not days:
        return "Every day"
    labels = [DAY_LABELS[day] for day in sorted(set(days))]
    return ", ".join(labels)


def assignment_is_active(assignment: Dict, today: date) -> bool:
    if not assignment.get("enabled"):
        return False
    paused_until = assignment.get("paused_until")
    if paused_until:
        try:
            paused_date = date.fromisoformat(paused_until.split("T")[0])
        except ValueError:
            paused_date = None
        if paused_date and paused_date > today:
            return False
    days = parse_days_of_week(assignment.get("days_of_week"))
    if days and today.weekday() not in days:
        return False
    return True


def fetch_assignments(conn, kid_id: int) -> List[Dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            a.kid_id,
            a.deck_id,
            a.enabled,
            a.days_of_week,
            a.new_cap,
            a.review_cap,
            a.paused_until,
            d.name AS deck_name
        FROM assignments a
        JOIN decks d ON d.id = a.deck_id
        WHERE a.kid_id = ? AND d.deleted_at IS NULL
        ORDER BY d.name
        """,
        (kid_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def fetch_due_cards(conn, kid_id: int, deck_id: int) -> List[Dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            c.*,
            d.name AS deck_name,
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
        JOIN decks d ON d.id = c.deck_id
        LEFT JOIN texts t ON t.id = c.text_id
        WHERE c.deck_id = ?
            AND c.due_date <= date('now')
            AND c.deleted_at IS NULL
            AND (c.text_id IS NULL OR t.deleted_at IS NULL)
            AND NOT EXISTS (
                SELECT 1 FROM reviews r
                WHERE r.card_id = c.id
                    AND r.kid_id = ?
                    AND date(r.ts) = date('now')
            )
        ORDER BY c.due_date ASC, c.id ASC
        """,
        (deck_id, kid_id),
    )
    cards = []
    for row in cursor.fetchall():
        card = dict(row)
        card["tags"] = [tag for tag in (card.get("tags") or "").split(",") if tag]
        cards.append(card)
    return cards


def apply_caps(cards: List[Dict], new_cap: Optional[int], review_cap: Optional[int]) -> Tuple[List[Dict], int, int]:
    new_cards = [card for card in cards if card.get("mastery_status") == "new"]
    review_cards = [card for card in cards if card.get("mastery_status") != "new"]
    if new_cap is not None:
        new_cards = new_cards[: max(new_cap, 0)]
    if review_cap is not None:
        review_cards = review_cards[: max(review_cap, 0)]
    selected = new_cards + review_cards
    selected.sort(key=lambda card: (card.get("due_date") or "", card.get("deck_name") or "", card["id"]))
    return selected, len(new_cards), len(review_cards)


def build_today_queue(conn, kid_id: int) -> Tuple[List[Dict], List[Dict]]:
    today = date.today()
    assignments = fetch_assignments(conn, kid_id)
    queue_cards: List[Dict] = []
    assignment_summaries: List[Dict] = []
    for assignment in assignments:
        active = assignment_is_active(assignment, today)
        deck_cards: List[Dict] = []
        new_count = 0
        review_count = 0
        if active:
            due_cards = fetch_due_cards(conn, kid_id, assignment["deck_id"])
            deck_cards, new_count, review_count = apply_caps(
                due_cards,
                assignment.get("new_cap"),
                assignment.get("review_cap"),
            )
            queue_cards.extend(deck_cards)
        assignment_summaries.append(
            {
                "deck_id": assignment["deck_id"],
                "deck_name": assignment["deck_name"],
                "enabled": bool(assignment.get("enabled")),
                "active": active,
                "days_of_week": format_days_of_week(assignment.get("days_of_week")),
                "new_cap": assignment.get("new_cap"),
                "review_cap": assignment.get("review_cap"),
                "paused_until": assignment.get("paused_until"),
                "new_count": new_count,
                "review_count": review_count,
                "total_count": new_count + review_count,
            }
        )
    queue_cards.sort(key=lambda card: (card.get("due_date") or "", card.get("deck_name") or "", card["id"]))
    return assignment_summaries, queue_cards


def get_recent_avg_duration(conn, kid_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT AVG(duration_seconds) AS avg_duration
        FROM (
            SELECT duration_seconds
            FROM reviews
            WHERE kid_id = ? AND duration_seconds IS NOT NULL
            ORDER BY ts DESC
            LIMIT 20
        )
        """,
        (kid_id,),
    )
    row = cursor.fetchone()
    if not row or row[0] is None:
        return 30
    return max(int(row[0]), 1)


@router.get("/today/{kid_id}", response_class=HTMLResponse)
async def today_view(kid_id: int, request: Request, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM kids WHERE id = ? AND deleted_at IS NULL", (kid_id,))
    kid_row = cursor.fetchone()
    if not kid_row:
        raise HTTPException(status_code=404, detail="Kid not found")
    kid = {"id": kid_row[0], "name": kid_row[1]}
    assignments, queue_cards = build_today_queue(conn, kid_id)
    total_due = len(queue_cards)
    avg_duration = get_recent_avg_duration(conn, kid_id)
    estimated_seconds = total_due * avg_duration
    return templates.TemplateResponse(
        "today.html",
        {
            "request": request,
            "kid": kid,
            "kid_id": kid_id,
            "assignments": assignments,
            "total_due": total_due,
            "estimated_seconds": estimated_seconds,
            "avg_duration": avg_duration,
        },
    )


@router.get("/today/{kid_id}/queue", response_class=HTMLResponse)
async def today_queue(kid_id: int, request: Request, conn=Depends(get_db)):
    assignments, queue_cards = build_today_queue(conn, kid_id)
    return templates.TemplateResponse(
        "partials/today_queue.html",
        {
            "request": request,
            "assignments": assignments,
            "total_due": len(queue_cards),
        },
    )


@router.get("/today/{kid_id}/next", response_class=HTMLResponse)
async def today_next_card(kid_id: int, request: Request, conn=Depends(get_db)):
    hint_mode = normalize_hint_mode(request.query_params.get("hint_mode"))
    assignments, queue_cards = build_today_queue(conn, kid_id)
    if not queue_cards:
        return templates.TemplateResponse(
            "partials/today_no_cards.html",
            {"request": request, "kid_id": kid_id},
        )
    card = queue_cards[0]
    hint_text = build_hint_text(card["full_text"], hint_mode)
    return templates.TemplateResponse(
        "partials/today_card.html",
        {
            "request": request,
            "card": card,
            "kid_id": kid_id,
            "deck_id": card["deck_id"],
            "hint_mode": hint_mode,
            "hint_text": hint_text,
            "hint_modes": HINT_MODE_OPTIONS,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "assignments": assignments,
        },
    )


@router.post("/today/{kid_id}/submit")
async def submit_today_review(
    kid_id: int,
    deck_id: int,
    card_id: int,
    request: Request,
    user_text: str = Form(...),
    hint_mode: str = Form("none"),
    started_at: Optional[str] = Form(None),
    conn=Depends(get_db),
):
    config = load_config()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards WHERE id = ? AND deleted_at IS NULL", (card_id,))
    card_row = cursor.fetchone()
    if not card_row:
        raise HTTPException(status_code=404, detail="Card not found")
    card = dict(card_row)
    full_text = card["full_text"]
    hint_mode = normalize_hint_mode(hint_mode)
    grade = grade_recall(full_text, user_text, config)
    quality = map_grade_to_quality(grade)
    new_interval, new_ef, new_streak, new_due = update_sm2(
        card["interval_days"], card["ease_factor"], quality, card["streak"]
    )
    mastery_status = mastery_status_from_streak(new_streak)
    cursor.execute(
        """
        UPDATE cards
        SET interval_days = ?, ease_factor = ?, streak = ?, due_date = ?, mastery_status = ?
        WHERE id = ?
        """,
        (new_interval, new_ef, new_streak, new_due.isoformat(), mastery_status, card_id),
    )
    duration_seconds = None
    if started_at:
        try:
            started = datetime.fromisoformat(started_at)
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            duration_seconds = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
        except ValueError:
            duration_seconds = None
    cursor.execute(
        """
        INSERT INTO reviews (
            card_id,
            kid_id,
            grade,
            auto_grade,
            final_grade,
            graded_by,
            user_text,
            hint_mode,
            duration_seconds
        )
        VALUES (?, ?, ?, ?, ?, 'auto', ?, ?, ?)
        """,
        (card_id, kid_id, grade, grade, grade, user_text, hint_mode, duration_seconds),
    )
    conn.commit()
    color_class = {
        "perfect": "bg-green-100 border-green-400 text-green-800",
        "good": "bg-yellow-100 border-yellow-400 text-yellow-800",
        "fail": "bg-red-100 border-red-400 text-red-800",
    }
    return templates.TemplateResponse(
        "partials/today_review_result.html",
        {
            "request": request,
            "grade": grade,
            "color_class": color_class.get(grade, "bg-gray-100"),
            "user_text": user_text,
            "full_text": full_text,
            "kid_id": kid_id,
            "deck_id": deck_id,
            "hint_mode": hint_mode,
        },
    )
