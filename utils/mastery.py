MASTERED_STREAK = 3

def mastery_status_from_streak(streak: int) -> str:
    if streak >= MASTERED_STREAK:
        return "mastered"
    if streak > 0:
        return "learning"
    return "new"

def mastery_percent(mastered: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((mastered / total) * 100, 1)
