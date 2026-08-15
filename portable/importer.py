from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from portable.models import ChangeCounts, ImportPreview, PortablePackage

ImportMode = Literal["merge", "copy"]


def _rows(conn: sqlite3.Connection, query: str) -> list[dict[str, object]]:
    cursor = conn.execute(query)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _count(**changes: int) -> ChangeCounts:
    return ChangeCounts(**changes)


def _entity_preview(
    incoming: tuple[object, ...],
    local: list[dict[str, object]],
    *,
    names_are_unique: bool,
) -> tuple[ChangeCounts, list[str]]:
    by_id = {str(row["portable_id"]): row for row in local}
    names = {str(row["name"]): str(row["portable_id"]) for row in local} if names_are_unique else {}
    creates = updates = skips = collisions = 0
    warnings: list[str] = []
    package_names: dict[str, str] = {}
    for item in incoming:
        portable_id = str(getattr(item, "portable_id"))
        name = getattr(item, "name", None)
        if names_are_unique and isinstance(name, str):
            conflicting = names.get(name) or package_names.get(name)
            if conflicting is not None and conflicting != portable_id:
                collisions += 1
                continue
            package_names[name] = portable_id
        current = by_id.get(portable_id)
        if current is None:
            creates += 1
        elif str(getattr(item, "updated_at")) > str(current["updated_at"]):
            updates += 1
        else:
            skips += 1
            if str(getattr(item, "updated_at")) == str(current["updated_at"]):
                warnings.append(f"{portable_id}: equal updated_at kept local")
    return _count(creates=creates, updates=updates, skips=skips, collisions=collisions), warnings


def preview_package(conn: sqlite3.Connection, package: PortablePackage, mode: ImportMode) -> ImportPreview:
    if mode not in ("merge", "copy"):
        raise ValueError("mode must be merge or copy")
    library = package.library
    if mode == "copy":
        local_kid_names = {str(row["name"]) for row in _rows(conn, "SELECT name FROM kids")}
        local_deck_names = {str(row["name"]) for row in _rows(conn, "SELECT name FROM decks")}
        kid_names = [item.name for item in library.kids]
        deck_names = [item.name for item in library.decks]
        kid_collisions = sum(name in local_kid_names for name in kid_names) + len(kid_names) - len(set(kid_names))
        deck_collisions = sum(name in local_deck_names for name in deck_names) + len(deck_names) - len(set(deck_names))
        return ImportPreview(
            mode="copy",
            kids=_count(creates=len(library.kids), collisions=kid_collisions),
            decks=_count(creates=len(library.decks), collisions=deck_collisions),
            cards=_count(creates=len(library.cards)),
            progress=_count(skips=len(library.progress)),
            reviews=_count(skips=len(library.reviews)),
            warnings=("copy imports content only; progress and reviews are omitted",),
        )
    kids, kid_warnings = _entity_preview(
        library.kids,
        _rows(conn, "SELECT portable_id, name, updated_at FROM kids"),
        names_are_unique=True,
    )
    decks, deck_warnings = _entity_preview(
        library.decks,
        _rows(conn, "SELECT portable_id, name, updated_at FROM decks"),
        names_are_unique=True,
    )
    cards, card_warnings = _entity_preview(
        library.cards,
        _rows(conn, "SELECT portable_id, updated_at FROM cards"),
        names_are_unique=False,
    )
    local_progress = {
        (str(row["kid_portable_id"]), str(row["card_portable_id"])): row
        for row in _rows(
            conn,
            """SELECT p.portable_id, p.last_review_ts, k.portable_id AS kid_portable_id,
                      c.portable_id AS card_portable_id
               FROM card_progress p JOIN kids k ON k.id=p.kid_id JOIN cards c ON c.id=p.card_id""",
        )
    }
    progress_creates = progress_updates = progress_skips = progress_collisions = 0
    local_progress_ids = {
        str(row["portable_id"]): pair for pair, row in local_progress.items()
    }
    warnings = kid_warnings + deck_warnings + card_warnings
    for item in library.progress:
        pair = (item.kid_portable_id, item.card_portable_id)
        if item.portable_id in local_progress_ids and local_progress_ids[item.portable_id] != pair:
            progress_collisions += 1
            continue
        current = local_progress.get(pair)
        if current is None:
            progress_creates += 1
        elif item.last_review is not None and (
            current["last_review_ts"] is None or item.last_review > str(current["last_review_ts"])
        ):
            progress_updates += 1
        else:
            progress_skips += 1
            if item.last_review == current["last_review_ts"]:
                warnings.append(f"{item.portable_id}: equal last_review kept local")
    local_review_ids = {
        str(row["portable_id"]) for row in _rows(conn, "SELECT portable_id FROM reviews")
    }
    review_creates = sum(item.portable_id not in local_review_ids for item in library.reviews)
    return ImportPreview(
        mode="merge", kids=kids, decks=decks, cards=cards,
        progress=_count(
            creates=progress_creates,
            updates=progress_updates,
            skips=progress_skips,
            collisions=progress_collisions,
        ),
        reviews=_count(creates=review_creates, skips=len(library.reviews) - review_creates),
        warnings=tuple(warnings),
    )


def _merge_entities(conn: sqlite3.Connection, package: PortablePackage) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    library = package.library
    for item in library.kids:
        row = conn.execute("SELECT id, updated_at FROM kids WHERE portable_id=?", (item.portable_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO kids (name, portable_id, updated_at) VALUES (?, ?, ?)", (item.name, item.portable_id, item.updated_at))
        elif item.updated_at > str(row[1]):
            conn.execute("UPDATE kids SET name=?, updated_at=? WHERE id=?", (item.name, item.updated_at, int(row[0])))
    for item in library.decks:
        row = conn.execute("SELECT id, updated_at FROM decks WHERE portable_id=?", (item.portable_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO decks (name, portable_id, updated_at) VALUES (?, ?, ?)", (item.name, item.portable_id, item.updated_at))
        elif item.updated_at > str(row[1]):
            conn.execute("UPDATE decks SET name=?, updated_at=? WHERE id=?", (item.name, item.updated_at, int(row[0])))
    deck_ids = {str(row[1]): int(row[0]) for row in conn.execute("SELECT id, portable_id FROM decks")}
    for item in library.cards:
        row = conn.execute("SELECT id, updated_at FROM cards WHERE portable_id=?", (item.portable_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO cards (deck_id, prompt, full_text, portable_id, updated_at) VALUES (?, ?, ?, ?, ?)",
                (deck_ids[item.deck_portable_id], item.prompt, item.full_text, item.portable_id, item.updated_at),
            )
        elif item.updated_at > str(row[1]):
            conn.execute(
                "UPDATE cards SET deck_id=?, prompt=?, full_text=?, updated_at=? WHERE id=?",
                (deck_ids[item.deck_portable_id], item.prompt, item.full_text, item.updated_at, int(row[0])),
            )
    kid_ids = {str(row[1]): int(row[0]) for row in conn.execute("SELECT id, portable_id FROM kids")}
    card_ids = {str(row[1]): int(row[0]) for row in conn.execute("SELECT id, portable_id FROM cards")}
    return kid_ids, deck_ids, card_ids


def _merge_history(conn: sqlite3.Connection, package: PortablePackage, kid_ids: dict[str, int], card_ids: dict[str, int]) -> None:
    for item in package.library.progress:
        kid_id, card_id = kid_ids[item.kid_portable_id], card_ids[item.card_portable_id]
        row = conn.execute("SELECT last_review_ts FROM card_progress WHERE kid_id=? AND card_id=?", (kid_id, card_id)).fetchone()
        if row is None:
            conn.execute(
                """INSERT INTO card_progress (kid_id, card_id, portable_id, interval_days,
                       due_date, ease_factor, streak, last_review_ts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (kid_id, card_id, item.portable_id, item.interval_days, item.due_date, float(item.ease_factor), item.streak, item.last_review),
            )
        elif item.last_review is not None and (row[0] is None or item.last_review > str(row[0])):
            conn.execute(
                """UPDATE card_progress SET portable_id=?, interval_days=?, due_date=?,
                       ease_factor=?, streak=?, last_review_ts=? WHERE kid_id=? AND card_id=?""",
                (item.portable_id, item.interval_days, item.due_date, float(item.ease_factor), item.streak, item.last_review, kid_id, card_id),
            )
    for item in package.library.reviews:
        conn.execute(
            """INSERT OR IGNORE INTO reviews
               (card_id, kid_id, portable_id, grade, user_text, duration_seconds, ts)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (card_ids[item.card_portable_id], kid_ids[item.kid_portable_id], item.portable_id,
             item.grade, item.user_text, item.duration_seconds, item.ts),
        )


def _copy_content(conn: sqlite3.Connection, package: PortablePackage) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    kid_ids: dict[str, int] = {}
    deck_ids: dict[str, int] = {}
    for item in package.library.kids:
        cursor = conn.execute("INSERT INTO kids (name, portable_id, updated_at) VALUES (?, ?, ?)", (item.name, str(uuid4()), now))
        kid_ids[item.portable_id] = int(cursor.lastrowid)
    for item in package.library.decks:
        cursor = conn.execute("INSERT INTO decks (name, portable_id, updated_at) VALUES (?, ?, ?)", (item.name, str(uuid4()), now))
        deck_ids[item.portable_id] = int(cursor.lastrowid)
    for item in package.library.cards:
        conn.execute(
            "INSERT INTO cards (deck_id, prompt, full_text, portable_id, updated_at) VALUES (?, ?, ?, ?, ?)",
            (deck_ids[item.deck_portable_id], item.prompt, item.full_text, str(uuid4()), now),
        )


def apply_package(
    conn: sqlite3.Connection,
    package: PortablePackage,
    mode: ImportMode,
    *,
    rebuild_fts: Callable[[sqlite3.Connection], None] | None = None,
) -> ImportPreview:
    if conn.in_transaction:
        raise RuntimeError("portable import requires an idle connection")
    conn.execute("BEGIN IMMEDIATE")
    try:
        preview = preview_package(conn, package, mode)
        if not preview.can_apply:
            raise ValueError("portable import has unique-name collisions")
        if mode == "copy":
            _copy_content(conn, package)
        else:
            kid_ids, _, card_ids = _merge_entities(conn, package)
            _merge_history(conn, package, kid_ids, card_ids)
        conn.execute(
            "INSERT OR IGNORE INTO assignments (kid_id, deck_id) SELECT k.id, d.id FROM kids k CROSS JOIN decks d WHERE k.deleted_at IS NULL AND d.deleted_at IS NULL"
        )
        conn.execute("INSERT OR IGNORE INTO deck_mastery_rules (deck_id) SELECT id FROM decks WHERE deleted_at IS NULL")
        (rebuild_fts or (lambda db: db.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")))(conn)
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError("portable import created foreign-key violations")
        conn.commit()
        return preview
    except Exception:
        conn.rollback()
        raise
