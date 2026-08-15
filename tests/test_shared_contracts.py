from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from copy import deepcopy
from datetime import date
from pathlib import Path

from Levenshtein import ratio as indel_ratio

from utils.grading import GradingThresholds, grade_recall_deterministic
from utils.sm2 import map_grade_to_quality, update_sm2

CONTRACTS = Path(__file__).parents[1] / "contracts"


def _rows(name: str) -> list[dict[str, str]]:
    with (CONTRACTS / "fixtures" / name).open(newline="") as fixture:
        return list(csv.DictReader(fixture, delimiter="\t"))


def test_deterministic_grading_fixture_matches_python() -> None:
    rules = json.loads((CONTRACTS / "deterministic-rules-v1.json").read_text())
    thresholds = GradingThresholds(
        perfect=float(rules["grading"]["perfect_threshold"]),
        good=float(rules["grading"]["good_threshold"]),
    )
    for row in _rows("deterministic-grading-v1.tsv"):
        expected = row["full_text"].strip().lower()
        actual = row["user_text"].strip().lower()
        assert f"{indel_ratio(expected, actual):.6f}" == row["ratio_six"]
        assert grade_recall_deterministic(
            row["full_text"], row["user_text"], thresholds
        ).value == row["grade"]


def test_sm2_fixture_matches_python() -> None:
    for row in _rows("sm2-v1.tsv"):
        quality = map_grade_to_quality(row["grade"])
        assert quality == int(row["quality"])
        result = update_sm2(
            int(row["interval_days"]),
            float(row["ease_six"]),
            quality,
            int(row["streak"]),
            date.fromisoformat(row["base_date"]),
        )
        assert result[0] == int(row["next_interval_days"])
        assert f"{result[1]:.6f}" == row["next_ease_six"]
        assert result[2] == int(row["next_streak"])
        assert result[3].isoformat() == row["due_date"]


def _normalize_nfc(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_nfc(item) for key, item in value.items()}
    return value


def test_portable_golden_canonical_bytes_and_digest() -> None:
    document = json.loads(
        (CONTRACTS / "valid" / "memcoach-backup-v1.json").read_text()
    )
    payload = deepcopy(document)
    integrity = payload.pop("integrity")
    canonical = json.dumps(
        _normalize_nfc(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    stored = (
        CONTRACTS / "canonical" / "memcoach-backup-v1.payload.json"
    ).read_bytes()

    assert stored.endswith(b"\n")
    assert stored.removesuffix(b"\n") == canonical
    assert hashlib.sha256(canonical).hexdigest() == integrity["sha256"]
    assert integrity["alg"] == "sha256"


def test_portable_golden_core_graph_and_allow_lists() -> None:
    schema = json.loads(
        (CONTRACTS / "memcoach-backup-v1.schema.json").read_text()
    )
    document = json.loads(
        (CONTRACTS / "valid" / "memcoach-backup-v1.json").read_text()
    )
    library = document["library"]

    assert schema["additionalProperties"] is False
    for definition in ("kid", "deck", "card", "progress", "review"):
        assert schema["$defs"][definition]["additionalProperties"] is False
    assert document["counts"] == {
        name: len(library[name])
        for name in ("kids", "decks", "cards", "progress", "reviews")
    }
    for entities in library.values():
        ids = [entity["portable_id"] for entity in entities]
        assert ids == sorted(ids)
        assert len(ids) == len(set(ids))

    kid_ids = {kid["portable_id"] for kid in library["kids"]}
    deck_ids = {deck["portable_id"] for deck in library["decks"]}
    card_ids = {card["portable_id"] for card in library["cards"]}
    assert {card["deck_portable_id"] for card in library["cards"]} <= deck_ids
    assert {row["kid_portable_id"] for row in library["progress"]} <= kid_ids
    assert {row["card_portable_id"] for row in library["progress"]} <= card_ids
    assert {row["kid_portable_id"] for row in library["reviews"]} <= kid_ids
    assert {row["card_portable_id"] for row in library["reviews"]} <= card_ids

    serialized = json.dumps(document).lower()
    for forbidden in ("pin_hash", "config.toml", "session", "signing", "bible_verses"):
        assert forbidden not in serialized


def test_invalid_contract_cases_cover_required_rejections() -> None:
    cases = json.loads(
        (CONTRACTS / "invalid" / "invalid-cases-v1.json").read_text()
    )["cases"]
    assert {case["expected_error"] for case in cases} == {
        "unsupported_version",
        "digest_mismatch",
        "duplicate_id",
        "dangling_reference",
        "invalid_uuid",
        "unknown_property",
        "unsupported_section",
    }
