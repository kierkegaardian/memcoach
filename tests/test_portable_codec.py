from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from portable.codec import PortablePackageError, canonical_json_bytes, parse_package, serialize_package

CONTRACTS = Path(__file__).parents[1] / "contracts"
GOLDEN = CONTRACTS / "valid" / "memcoach-backup-v1.json"


def _resign(document: dict[str, object]) -> bytes:
    payload = deepcopy(document)
    payload.pop("integrity", None)
    document["integrity"] = {
        "alg": "sha256",
        "sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }
    return canonical_json_bytes(document)


def test_typed_parser_round_trips_canonical_package() -> None:
    package = parse_package(GOLDEN.read_bytes())
    encoded = serialize_package(package)

    reparsed = parse_package(encoded)

    assert reparsed == package
    assert encoded == serialize_package(reparsed)
    assert not encoded.endswith(b"\n")


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda doc: doc.update(version=2), "unsupported"),
        (lambda doc: doc["library"]["kids"].append(deepcopy(doc["library"]["kids"][0])), "duplicate"),
        (lambda doc: doc["library"]["cards"][0].update(deck_portable_id="66666666-6666-4666-8666-666666666666"), "dangling"),
        (lambda doc: doc["library"]["kids"][0].update(portable_id="AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"), "canonical UUID"),
        (lambda doc: doc["library"]["cards"][0].update(interval_days=6), "fields invalid"),
        (lambda doc: doc.update(extensions={"tags": []}), "unsupported section"),
    ],
)
def test_parser_rejects_resigned_semantic_invalid_cases(mutator, match: str) -> None:
    document = json.loads(GOLDEN.read_text())
    mutator(document)

    with pytest.raises(PortablePackageError, match=match):
        parse_package(_resign(document))


def test_parser_rejects_digest_utf8_duplicate_keys_and_size() -> None:
    document = json.loads(GOLDEN.read_text())
    document["integrity"]["sha256"] = "0" * 64
    with pytest.raises(PortablePackageError, match="digest mismatch"):
        parse_package(canonical_json_bytes(document))
    with pytest.raises(PortablePackageError, match="UTF-8"):
        parse_package(b"\xff")
    with pytest.raises(PortablePackageError, match="duplicate JSON key"):
        parse_package(b'{"format":"a","format":"b"}')
    with pytest.raises(PortablePackageError, match="byte limit"):
        parse_package(GOLDEN.read_bytes(), max_bytes=10)
