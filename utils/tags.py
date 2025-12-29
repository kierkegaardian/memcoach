from __future__ import annotations

import re
from typing import Iterable, List


_TAG_SPLIT_RE = re.compile(r"[,\n]+")


def parse_tag_names(raw: str) -> List[str]:
    if not raw:
        return []
    parts = _TAG_SPLIT_RE.split(raw)
    seen = set()
    tags: List[str] = []
    for part in parts:
        name = part.strip()
        if not name:
            continue
        normalized = name.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        tags.append(normalized)
    return tags


def upsert_tags(conn, tag_names: Iterable[str]) -> List[int]:
    names = list(tag_names)
    if not names:
        return []
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT OR IGNORE INTO tags (name) VALUES (?)",
        [(name,) for name in names],
    )
    placeholders = ",".join("?" for _ in names)
    cursor.execute(
        f"SELECT id, name FROM tags WHERE name IN ({placeholders})",
        names,
    )
    id_map = {row["name"]: row["id"] for row in cursor.fetchall()}
    return [id_map[name] for name in names if name in id_map]


def set_card_tags(conn, card_id: int, tag_names: Iterable[str]) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM card_tags WHERE card_id = ?", (card_id,))
    tag_ids = upsert_tags(conn, tag_names)
    if not tag_ids:
        return
    cursor.executemany(
        "INSERT OR IGNORE INTO card_tags (card_id, tag_id) VALUES (?, ?)",
        [(card_id, tag_id) for tag_id in tag_ids],
    )


def set_deck_tags(conn, deck_id: int, tag_names: Iterable[str]) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deck_tags WHERE deck_id = ?", (deck_id,))
    tag_ids = upsert_tags(conn, tag_names)
    if not tag_ids:
        return
    cursor.executemany(
        "INSERT OR IGNORE INTO deck_tags (deck_id, tag_id) VALUES (?, ?)",
        [(deck_id, tag_id) for tag_id in tag_ids],
    )
