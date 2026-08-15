from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from portable.models import (
    PortableCard,
    PortableDeck,
    PortableKid,
    PortableLibrary,
    PortablePackage,
    PortableProgress,
    PortableReview,
    PortableSource,
)


def utc_timestamp(value: str | None = None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed = parsed.astimezone(timezone.utc)
    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dict_rows(conn: sqlite3.Connection, query: str) -> list[dict[str, object]]:
    cursor = conn.execute(query)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def export_package(
    conn: sqlite3.Connection,
    *,
    app_version: str = "0.1.0",
    exported_at: str | None = None,
) -> PortablePackage:
    metadata = conn.execute(
        "SELECT installation_id FROM installation_metadata WHERE singleton_id = 1"
    ).fetchone()
    if metadata is None:
        raise RuntimeError("installation metadata is missing")
    kids = tuple(
        PortableKid(str(row["portable_id"]), str(row["name"]), utc_timestamp(str(row["updated_at"])))
        for row in _dict_rows(
            conn,
            "SELECT portable_id, name, updated_at FROM kids WHERE deleted_at IS NULL ORDER BY portable_id",
        )
    )
    decks = tuple(
        PortableDeck(str(row["portable_id"]), str(row["name"]), utc_timestamp(str(row["updated_at"])))
        for row in _dict_rows(
            conn,
            "SELECT portable_id, name, updated_at FROM decks WHERE deleted_at IS NULL ORDER BY portable_id",
        )
    )
    cards = tuple(
        PortableCard(
            str(row["portable_id"]), str(row["deck_portable_id"]), str(row["prompt"]),
            str(row["full_text"]), utc_timestamp(str(row["updated_at"])),
        )
        for row in _dict_rows(
            conn,
            """SELECT c.portable_id, d.portable_id AS deck_portable_id, c.prompt,
                      c.full_text, c.updated_at
               FROM cards c JOIN decks d ON d.id = c.deck_id
               WHERE c.deleted_at IS NULL AND d.deleted_at IS NULL
               ORDER BY c.portable_id""",
        )
    )
    progress = tuple(
        PortableProgress(
            str(row["portable_id"]), str(row["kid_portable_id"]), str(row["card_portable_id"]),
            int(row["interval_days"]), str(row["due_date"]), f"{float(row['ease_factor']):.6f}",
            int(row["streak"]), utc_timestamp(str(row["last_review_ts"])) if row["last_review_ts"] else None,
        )
        for row in _dict_rows(
            conn,
            """SELECT p.portable_id, k.portable_id AS kid_portable_id,
                      c.portable_id AS card_portable_id, p.interval_days, p.due_date,
                      p.ease_factor, p.streak, p.last_review_ts
               FROM card_progress p
               JOIN kids k ON k.id = p.kid_id
               JOIN cards c ON c.id = p.card_id
               JOIN decks d ON d.id = c.deck_id
               WHERE k.deleted_at IS NULL AND c.deleted_at IS NULL AND d.deleted_at IS NULL
               ORDER BY p.portable_id""",
        )
    )
    reviews = tuple(
        PortableReview(
            str(row["portable_id"]), str(row["card_portable_id"]), str(row["kid_portable_id"]),
            row["grade"], row["user_text"], row["duration_seconds"], utc_timestamp(str(row["ts"])),
        )
        for row in _dict_rows(
            conn,
            """SELECT r.portable_id, c.portable_id AS card_portable_id,
                      k.portable_id AS kid_portable_id, COALESCE(r.final_grade, r.grade) AS grade,
                      r.user_text, r.duration_seconds, r.ts
               FROM reviews r
               JOIN kids k ON k.id = r.kid_id
               JOIN cards c ON c.id = r.card_id
               JOIN decks d ON d.id = c.deck_id
               WHERE k.deleted_at IS NULL AND c.deleted_at IS NULL AND d.deleted_at IS NULL
               ORDER BY r.portable_id""",
        )
    )
    return PortablePackage(
        exported_at=utc_timestamp(exported_at),
        source=PortableSource("memcoach-web", app_version, str(metadata[0]), "web"),
        library=PortableLibrary(kids, decks, cards, progress, reviews),
    )
