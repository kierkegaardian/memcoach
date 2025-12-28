DEFAULT_MASTERY_RULES = {
    "consecutive_grades": 3,
    "min_ease_factor": 2.5,
    "min_interval_days": 7,
}

def mastery_status_from_rules(
    streak: int,
    ease_factor: float,
    interval_days: int,
    rules: dict,
) -> str:
    if streak <= 0:
        return "new"
    if (
        streak >= rules["consecutive_grades"]
        and ease_factor >= rules["min_ease_factor"]
        and interval_days >= rules["min_interval_days"]
    ):
        return "mastered"
    return "learning"

def get_deck_mastery_rules(conn, deck_id: int) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT consecutive_grades, min_ease_factor, min_interval_days
        FROM deck_mastery_rules
        WHERE deck_id = ?
        """,
        (deck_id,),
    )
    row = cursor.fetchone()
    if not row:
        return DEFAULT_MASTERY_RULES.copy()
    return {
        "consecutive_grades": int(row[0]),
        "min_ease_factor": float(row[1]),
        "min_interval_days": int(row[2]),
    }

def mastery_percent(mastered: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((mastered / total) * 100, 1)
