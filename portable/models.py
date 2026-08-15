from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Grade = Literal["perfect", "good", "fail"]
Platform = Literal["web", "android"]


@dataclass(frozen=True)
class PortableSource:
    app: str
    app_version: str
    installation_id: str
    platform: Platform


@dataclass(frozen=True)
class PortableKid:
    portable_id: str
    name: str
    updated_at: str


@dataclass(frozen=True)
class PortableDeck:
    portable_id: str
    name: str
    updated_at: str


@dataclass(frozen=True)
class PortableCard:
    portable_id: str
    deck_portable_id: str
    prompt: str
    full_text: str
    updated_at: str


@dataclass(frozen=True)
class PortableProgress:
    portable_id: str
    kid_portable_id: str
    card_portable_id: str
    interval_days: int
    due_date: str
    ease_factor: str
    streak: int
    last_review: str | None


@dataclass(frozen=True)
class PortableReview:
    portable_id: str
    card_portable_id: str
    kid_portable_id: str
    grade: Grade
    user_text: str | None
    duration_seconds: int | None
    ts: str


@dataclass(frozen=True)
class PortableLibrary:
    kids: tuple[PortableKid, ...]
    decks: tuple[PortableDeck, ...]
    cards: tuple[PortableCard, ...]
    progress: tuple[PortableProgress, ...]
    reviews: tuple[PortableReview, ...]

    def counts(self) -> dict[str, int]:
        return {
            "kids": len(self.kids),
            "decks": len(self.decks),
            "cards": len(self.cards),
            "progress": len(self.progress),
            "reviews": len(self.reviews),
        }

    def to_dict(self) -> dict[str, list[dict[str, object]]]:
        return {
            "kids": [asdict(item) for item in self.kids],
            "decks": [asdict(item) for item in self.decks],
            "cards": [asdict(item) for item in self.cards],
            "progress": [asdict(item) for item in self.progress],
            "reviews": [asdict(item) for item in self.reviews],
        }


@dataclass(frozen=True)
class PortablePackage:
    exported_at: str
    source: PortableSource
    library: PortableLibrary

    def payload_dict(self) -> dict[str, object]:
        return {
            "format": "memcoach.portable",
            "version": 1,
            "exported_at": self.exported_at,
            "source": asdict(self.source),
            "scope": "library",
            "counts": self.library.counts(),
            "library": self.library.to_dict(),
        }


@dataclass(frozen=True)
class ChangeCounts:
    creates: int = 0
    updates: int = 0
    skips: int = 0
    collisions: int = 0


@dataclass(frozen=True)
class ImportPreview:
    mode: Literal["merge", "copy"]
    kids: ChangeCounts
    decks: ChangeCounts
    cards: ChangeCounts
    progress: ChangeCounts
    reviews: ChangeCounts
    warnings: tuple[str, ...] = ()

    @property
    def can_apply(self) -> bool:
        return not any(
            counts.collisions
            for counts in (self.kids, self.decks, self.cards, self.progress, self.reviews)
        )
