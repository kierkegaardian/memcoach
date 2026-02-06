from datetime import date, timedelta
from typing import Optional, Tuple

def map_grade_to_quality(grade: str) -> int:
    """Map grade to SM-2 quality score (0-5)."""
    mapping = {
        'fail': 0,
        'good': 3,
        'perfect': 4
    }
    return mapping.get(grade, 0)

def update_sm2(
    card_interval: int,
    card_ef: float,
    quality: int,
    streak: int,
    base_date: Optional[date] = None,
) -> Tuple[int, float, int, date]:
    """Update SM-2 parameters and compute new due date."""
    if quality < 3:
        new_streak = 0
        new_interval = 1
    else:
        new_streak = streak + 1
        if card_interval == 1:
            new_interval = 6 if quality >= 4 else 1
        else:
            new_interval = max(1, round(card_interval * card_ef))
    new_ef = max(1.3, card_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    anchor = base_date or date.today()
    new_due = anchor + timedelta(days=new_interval)
    return new_interval, new_ef, new_streak, new_due

def get_next_interval(quality: int, previous_interval: int = 1, ef: float = 2.5) -> int:
    """Helper for initial intervals."""
    new_interval, _, _, _ = update_sm2(previous_interval, ef, quality, 0)
    return new_interval
