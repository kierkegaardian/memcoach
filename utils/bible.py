from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from db import get_conn

_DATASET_CACHE: Optional[List[Dict[str, Any]]] = None
_INDEX_CACHE: Dict[str, Dict[str, Any]] = {}
_DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "kjv.json"


def load_kjv_dataset() -> List[Dict[str, Any]]:
    """Load the KJV dataset from disk once and return the in-memory list."""
    global _DATASET_CACHE
    if _DATASET_CACHE is None:
        with _DATASET_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        _DATASET_CACHE = payload.get("verses", [])
    return _DATASET_CACHE


def _seed_db_if_empty(translation: str) -> None:
    data = load_kjv_dataset()
    if not data:
        return
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM bible_verses WHERE translation = ?",
            (translation,),
        )
        if (cursor.fetchone() or [0])[0]:
            return
        cursor.executemany(
            """
            INSERT INTO bible_verses (translation, book, chapter, verse, text)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    translation,
                    entry["book"],
                    entry["chapter"],
                    entry["verse"],
                    entry["text"],
                )
                for entry in data
            ],
        )
        conn.commit()


def _query_from_db(
    translation: str, book: str, chapter: int, start_verse: int, end_verse: int
) -> Optional[List[Dict[str, Any]]]:
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT verse, text
            FROM bible_verses
            WHERE translation = ?
              AND book = ?
              AND chapter = ?
              AND verse BETWEEN ? AND ?
            ORDER BY verse
            """,
            (translation, book, chapter, start_verse, end_verse),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return [{"verse": row["verse"], "text": row["text"]} for row in rows]


def _query_from_json(
    translation: str, book: str, chapter: int, start_verse: int, end_verse: int
) -> List[Dict[str, Any]]:
    data = load_kjv_dataset()
    verses = [
        {"verse": entry["verse"], "text": entry["text"]}
        for entry in data
        if entry["translation"] == translation
        and entry["book"] == book
        and entry["chapter"] == chapter
        and start_verse <= entry["verse"] <= end_verse
    ]
    return sorted(verses, key=lambda verse: verse["verse"])


def get_passage(
    translation: str,
    book: str,
    chapter: int,
    start_verse: int,
    end_verse: int,
    include_verses: bool = False,
) -> Dict[str, Any]:
    """Return a formatted passage string and optional per-verse breakdown."""
    _seed_db_if_empty(translation)
    verses = _query_from_db(translation, book, chapter, start_verse, end_verse)
    if verses is None:
        verses = _query_from_json(translation, book, chapter, start_verse, end_verse)
    formatted = " ".join(verse["text"] for verse in verses)
    response = {
        "text": formatted,
        "reference": f"{book} {chapter}:{start_verse}-{end_verse}",
        "translation": translation,
    }
    if include_verses:
        response["verses"] = verses
    return response


def get_translation_index(translation: str) -> Dict[str, Any]:
    """Return ordered book/chapter metadata for a translation."""
    cached = _INDEX_CACHE.get(translation)
    if cached is not None:
        return cached
    data = load_kjv_dataset()
    books: List[str] = []
    chapters_by_book: Dict[str, Dict[int, int]] = {}
    for entry in data:
        if entry["translation"] != translation:
            continue
        book = entry["book"]
        if book not in chapters_by_book:
            chapters_by_book[book] = {}
            books.append(book)
        chapter = entry["chapter"]
        verse = entry["verse"]
        current_max = chapters_by_book[book].get(chapter, 0)
        if verse > current_max:
            chapters_by_book[book][chapter] = verse
    index = {"books": books, "chapters": chapters_by_book}
    _INDEX_CACHE[translation] = index
    return index
