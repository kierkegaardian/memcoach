import sqlite3


def has_enabled_assignment(
    conn: sqlite3.Connection,
    *,
    kid_id: int,
    deck_id: int,
) -> bool:
    """Return whether an active kid and deck have an enabled assignment."""
    row = conn.execute(
        """
        SELECT 1
        FROM assignments a
        JOIN kids k ON k.id = a.kid_id
        JOIN decks d ON d.id = a.deck_id
        WHERE a.kid_id = ?
          AND a.deck_id = ?
          AND a.enabled = 1
          AND k.deleted_at IS NULL
          AND d.deleted_at IS NULL
        """,
        (kid_id, deck_id),
    ).fetchone()
    return row is not None
