from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from utils.mastery import get_deck_mastery_rules, mastery_status_from_rules
from utils.sm2 import map_grade_to_quality, update_sm2


@dataclass(frozen=True)
class CardProgressState:
    interval_days: int
    ease_factor: float
    streak: int
    mastery_status: str
    due_date: str
    last_review_ts: Optional[str] = None


def default_progress() -> CardProgressState:
    return CardProgressState(
        interval_days=1,
        ease_factor=2.5,
        streak=0,
        mastery_status="new",
        due_date=date.today().isoformat(),
    )


def _date_from_ts(ts_value: Optional[str]) -> date:
    if not ts_value:
        return date.today()
    try:
        return datetime.fromisoformat(ts_value).date()
    except ValueError:
        try:
            return date.fromisoformat(ts_value[:10])
        except ValueError:
            return date.today()


def get_card_progress(conn, kid_id: int, card_id: int) -> Optional[CardProgressState]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT interval_days, ease_factor, streak, mastery_status, due_date, last_review_ts
        FROM card_progress
        WHERE kid_id = ? AND card_id = ?
        """,
        (kid_id, card_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return CardProgressState(
        interval_days=int(row["interval_days"]),
        ease_factor=float(row["ease_factor"]),
        streak=int(row["streak"]),
        mastery_status=row["mastery_status"],
        due_date=row["due_date"],
        last_review_ts=row["last_review_ts"],
    )


def upsert_card_progress(
    conn,
    *,
    kid_id: int,
    card_id: int,
    interval_days: int,
    due_date: str,
    ease_factor: float,
    streak: int,
    mastery_status: str,
    last_review_ts: Optional[str],
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO card_progress (
            kid_id,
            card_id,
            interval_days,
            due_date,
            ease_factor,
            streak,
            mastery_status,
            last_review_ts
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(kid_id, card_id) DO UPDATE SET
            interval_days = excluded.interval_days,
            due_date = excluded.due_date,
            ease_factor = excluded.ease_factor,
            streak = excluded.streak,
            mastery_status = excluded.mastery_status,
            last_review_ts = excluded.last_review_ts
        """,
        (
            kid_id,
            card_id,
            interval_days,
            due_date,
            ease_factor,
            streak,
            mastery_status,
            last_review_ts,
        ),
    )


def compute_progress_from_reviews(conn, kid_id: int, card_id: int) -> Optional[CardProgressState]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.ts,
               COALESCE(r.final_grade, r.grade) AS grade,
               c.deck_id
        FROM reviews r
        JOIN cards c ON c.id = r.card_id
        WHERE r.kid_id = ? AND r.card_id = ?
        ORDER BY r.ts ASC, r.id ASC
        """,
        (kid_id, card_id),
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    base = default_progress()
    interval_days = base.interval_days
    ease_factor = base.ease_factor
    streak = base.streak
    mastery_status = base.mastery_status
    due_date = base.due_date
    last_review_ts: Optional[str] = None
    for row in rows:
        grade = row["grade"] or "fail"
        quality = map_grade_to_quality(grade)
        review_date = _date_from_ts(row["ts"])
        new_interval, new_ef, new_streak, new_due = update_sm2(
            interval_days,
            ease_factor,
            quality,
            streak,
            base_date=review_date,
        )
        mastery_rules = get_deck_mastery_rules(conn, row["deck_id"])
        mastery_status = mastery_status_from_rules(
            new_streak,
            new_ef,
            new_interval,
            mastery_rules,
        )
        interval_days = new_interval
        ease_factor = new_ef
        streak = new_streak
        due_date = new_due.isoformat()
        last_review_ts = row["ts"]
    return CardProgressState(
        interval_days=interval_days,
        ease_factor=ease_factor,
        streak=streak,
        mastery_status=mastery_status,
        due_date=due_date,
        last_review_ts=last_review_ts,
    )
