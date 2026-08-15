from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from copy import deepcopy
from datetime import date, datetime
from typing import TypeVar, cast

from portable.models import (
    PortableCard,
    PortableDeck,
    PortableKid,
    PortableLibrary,
    PortablePackage,
    PortableProgress,
    PortableReview,
    PortableSource,
    Platform,
)

MAX_PACKAGE_BYTES = 20 * 1024 * 1024
MAX_NESTING = 12
MAX_COUNTS = {"kids": 10_000, "decks": 10_000, "cards": 100_000, "progress": 200_000, "reviews": 500_000}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EASE_RE = re.compile(r"^\d+\.\d{6}$")
T = TypeVar("T")


class PortablePackageError(ValueError):
    """Raised when portable bytes fail the strict v1 contract."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PortablePackageError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nfc(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _nfc(item) for key, item in value.items()}
    return value


def _check_depth(value: object, depth: int = 0) -> None:
    if depth > MAX_NESTING:
        raise PortablePackageError("package nesting exceeds limit")
    if isinstance(value, dict):
        for item in value.values():
            _check_depth(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_depth(item, depth + 1)


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(_nfc(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_payload_bytes(package: PortablePackage) -> bytes:
    return canonical_json_bytes(package.payload_dict())


def serialize_package(package: PortablePackage) -> bytes:
    payload = package.payload_dict()
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return canonical_json_bytes({**payload, "integrity": {"alg": "sha256", "sha256": digest}})


def _exact(obj: object, required: set[str], *, where: str) -> dict[str, object]:
    if not isinstance(obj, dict):
        raise PortablePackageError(f"{where} must be an object")
    actual = set(obj)
    if actual != required:
        unknown = sorted(actual - required)
        missing = sorted(required - actual)
        raise PortablePackageError(f"{where} fields invalid; unknown={unknown}, missing={missing}")
    return obj


def _string(obj: dict[str, object], key: str, *, maximum: int, nullable: bool = False) -> str | None:
    value = obj[key]
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise PortablePackageError(f"{key} must be a non-empty string up to {maximum} characters")
    return unicodedata.normalize("NFC", value)


def _integer(obj: dict[str, object], key: str, *, minimum: int = 0, nullable: bool = False) -> int | None:
    value = obj[key]
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PortablePackageError(f"{key} must be an integer >= {minimum}")
    return value


def _uuid(obj: dict[str, object], key: str) -> str:
    value = _string(obj, key, maximum=36)
    assert isinstance(value, str)
    if not UUID_RE.fullmatch(value):
        raise PortablePackageError(f"{key} is not a canonical UUID")
    return value


def _timestamp(obj: dict[str, object], key: str, *, nullable: bool = False) -> str | None:
    value = _string(obj, key, maximum=20, nullable=nullable)
    if value is None:
        return None
    if not TIMESTAMP_RE.fullmatch(value):
        raise PortablePackageError(f"{key} is not a UTC second-precision timestamp")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise PortablePackageError(f"{key} is not a real timestamp") from exc
    return value


def _date(obj: dict[str, object], key: str) -> str:
    value = _string(obj, key, maximum=10)
    assert isinstance(value, str)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PortablePackageError(f"{key} is not a real date") from exc
    return value


def _items(
    library: dict[str, object],
    name: str,
    parser: Callable[[dict[str, object]], T],
) -> tuple[T, ...]:
    raw = library[name]
    if not isinstance(raw, list) or len(raw) > MAX_COUNTS[name]:
        raise PortablePackageError(f"{name} must be an array within its count limit")
    parsed = tuple(parser(item) for item in raw)
    ids = [getattr(item, "portable_id") for item in parsed]
    if ids != sorted(ids):
        raise PortablePackageError(f"{name} must be sorted by portable_id")
    if len(ids) != len(set(ids)):
        raise PortablePackageError(f"{name} contains duplicate portable IDs")
    return parsed


def parse_package(raw: bytes, *, max_bytes: int = MAX_PACKAGE_BYTES) -> PortablePackage:
    if len(raw) > max_bytes:
        raise PortablePackageError("package exceeds byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PortablePackageError("package is not valid UTF-8") from exc
    try:
        document = json.loads(text, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as exc:
        raise PortablePackageError("package is not valid JSON") from exc
    _check_depth(document)
    if isinstance(document, dict) and "extensions" in document:
        raise PortablePackageError("unsupported section: extensions")
    top = _exact(
        document,
        {"format", "version", "exported_at", "source", "scope", "counts", "library", "integrity"},
        where="package",
    )
    if top["format"] != "memcoach.portable" or top["scope"] != "library" or top["version"] != 1:
        raise PortablePackageError("unsupported portable format, scope, or version")
    integrity = _exact(top["integrity"], {"alg", "sha256"}, where="integrity")
    digest = _string(integrity, "sha256", maximum=64)
    if integrity["alg"] != "sha256" or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise PortablePackageError("invalid integrity metadata")
    payload = deepcopy(document)
    del payload["integrity"]
    if hashlib.sha256(canonical_json_bytes(payload)).hexdigest() != digest:
        raise PortablePackageError("digest mismatch")
    return _parse_validated_payload(top)


def _parse_validated_payload(top: dict[str, object]) -> PortablePackage:
    source_obj = _exact(top["source"], {"app", "app_version", "installation_id", "platform"}, where="source")
    platform = source_obj["platform"]
    if platform not in ("web", "android"):
        raise PortablePackageError("invalid source platform")
    source = PortableSource(
        app=str(_string(source_obj, "app", maximum=64)),
        app_version=str(_string(source_obj, "app_version", maximum=64)),
        installation_id=_uuid(source_obj, "installation_id"),
        platform=cast(Platform, platform),
    )
    library_obj = _exact(top["library"], {"kids", "decks", "cards", "progress", "reviews"}, where="library")
    library = PortableLibrary(
        kids=_items(library_obj, "kids", _parse_kid),
        decks=_items(library_obj, "decks", _parse_deck),
        cards=_items(library_obj, "cards", _parse_card),
        progress=_items(library_obj, "progress", _parse_progress),
        reviews=_items(library_obj, "reviews", _parse_review),
    )
    counts = _exact(top["counts"], set(MAX_COUNTS), where="counts")
    for name, actual in library.counts().items():
        if _integer(counts, name) != actual:
            raise PortablePackageError(f"count mismatch for {name}")
    _validate_graph(library)
    exported_at = _timestamp(top, "exported_at")
    assert exported_at is not None
    return PortablePackage(exported_at=exported_at, source=source, library=library)


def _parse_kid(raw: dict[str, object]) -> PortableKid:
    obj = _exact(raw, {"portable_id", "name", "updated_at"}, where="kid")
    updated_at = _timestamp(obj, "updated_at")
    assert updated_at is not None
    return PortableKid(_uuid(obj, "portable_id"), str(_string(obj, "name", maximum=200)), updated_at)


def _parse_deck(raw: dict[str, object]) -> PortableDeck:
    obj = _exact(raw, {"portable_id", "name", "updated_at"}, where="deck")
    updated_at = _timestamp(obj, "updated_at")
    assert updated_at is not None
    return PortableDeck(_uuid(obj, "portable_id"), str(_string(obj, "name", maximum=200)), updated_at)


def _parse_card(raw: dict[str, object]) -> PortableCard:
    fields = {"portable_id", "deck_portable_id", "prompt", "full_text", "updated_at"}
    obj = _exact(raw, fields, where="card")
    updated_at = _timestamp(obj, "updated_at")
    assert updated_at is not None
    return PortableCard(
        _uuid(obj, "portable_id"), _uuid(obj, "deck_portable_id"),
        str(_string(obj, "prompt", maximum=2_000)),
        str(_string(obj, "full_text", maximum=100_000)), updated_at,
    )


def _parse_progress(raw: dict[str, object]) -> PortableProgress:
    fields = {
        "portable_id", "kid_portable_id", "card_portable_id", "interval_days",
        "due_date", "ease_factor", "streak", "last_review",
    }
    obj = _exact(raw, fields, where="progress")
    ease = _string(obj, "ease_factor", maximum=32)
    if not isinstance(ease, str) or not EASE_RE.fullmatch(ease):
        raise PortablePackageError("ease_factor must have six decimal places")
    return PortableProgress(
        _uuid(obj, "portable_id"), _uuid(obj, "kid_portable_id"),
        _uuid(obj, "card_portable_id"), int(_integer(obj, "interval_days", minimum=1)),
        _date(obj, "due_date"), ease, int(_integer(obj, "streak")),
        _timestamp(obj, "last_review", nullable=True),
    )


def _parse_review(raw: dict[str, object]) -> PortableReview:
    fields = {
        "portable_id", "card_portable_id", "kid_portable_id", "grade",
        "user_text", "duration_seconds", "ts",
    }
    obj = _exact(raw, fields, where="review")
    grade = obj["grade"]
    if grade not in ("perfect", "good", "fail"):
        raise PortablePackageError("invalid review grade")
    ts = _timestamp(obj, "ts")
    assert ts is not None
    return PortableReview(
        _uuid(obj, "portable_id"), _uuid(obj, "card_portable_id"),
        _uuid(obj, "kid_portable_id"), grade,
        _string(obj, "user_text", maximum=100_000, nullable=True),
        _integer(obj, "duration_seconds", nullable=True), ts,
    )


def _validate_graph(library: PortableLibrary) -> None:
    kid_ids = {item.portable_id for item in library.kids}
    deck_ids = {item.portable_id for item in library.decks}
    card_ids = {item.portable_id for item in library.cards}
    if any(item.deck_portable_id not in deck_ids for item in library.cards):
        raise PortablePackageError("dangling card-to-deck reference")
    if any(item.kid_portable_id not in kid_ids or item.card_portable_id not in card_ids for item in library.progress):
        raise PortablePackageError("dangling progress reference")
    if any(item.kid_portable_id not in kid_ids or item.card_portable_id not in card_ids for item in library.reviews):
        raise PortablePackageError("dangling review reference")
    pairs = [(item.kid_portable_id, item.card_portable_id) for item in library.progress]
    if len(pairs) != len(set(pairs)):
        raise PortablePackageError("duplicate progress kid/card pair")
