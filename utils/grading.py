import asyncio
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Any

from Levenshtein import ratio as lev_ratio

from config import load_config
from .ollama import grade_with_llm
from .sm2 import map_grade_to_quality


class RecallGrade(StrEnum):
    FAIL = "fail"
    GOOD = "good"
    PERFECT = "perfect"


@dataclass(frozen=True)
class GradingThresholds:
    perfect: float = 0.98
    good: float = 0.85


def grade_recall_deterministic(
    full_text: str,
    user_text: str,
    thresholds: GradingThresholds = GradingThresholds(),
) -> RecallGrade:
    """Grade recall using only the shared normalized-indel contract."""
    if not user_text or not user_text.strip():
        return RecallGrade.FAIL
    ratio = lev_ratio(user_text.strip().lower(), full_text.strip().lower())
    if ratio >= thresholds.perfect:
        return RecallGrade.PERFECT
    if ratio >= thresholds.good:
        return RecallGrade.GOOD
    return RecallGrade.FAIL


def grade_recall(
    full_text: str,
    user_text: str,
    config: dict[str, Any] | None = None,
) -> str:
    """Grade user recall using Levenshtein + optional LLM for borderline."""
    if not config:
        config = load_config()
    grading_config = config.get("grading", {})
    thresholds = GradingThresholds(
        perfect=float(grading_config.get("levenshtein_perfect_threshold", 0.98)),
        good=float(grading_config.get("levenshtein_good_threshold", 0.85)),
    )
    deterministic_grade = grade_recall_deterministic(full_text, user_text, thresholds)
    if deterministic_grade is RecallGrade.GOOD:
        provider = str(config.get("ollama", {}).get("provider", "disabled"))
        if (
            bool(grading_config.get("use_llm_on_borderline", False))
            and provider == "local_cli"
        ):
            llm_grade = grade_with_llm(full_text, user_text, config)
            if llm_grade in {RecallGrade.PERFECT, RecallGrade.GOOD}:
                return llm_grade
    return deterministic_grade.value


async def grade_recall_async(
    full_text: str,
    user_text: str,
    config: dict[str, Any] | None = None,
) -> str:
    return await asyncio.to_thread(grade_recall, full_text, user_text, config)

def get_quality_score(grade: str) -> int:
    """Map grade to SM-2 quality (0-5)."""
    return map_grade_to_quality(grade)

def token_diff(
    expected_text: str,
    actual_text: str,
) -> dict[str, list[dict[str, str]]]:
    """Compute a whitespace-token diff for display in templates."""
    expected_tokens = expected_text.split() if expected_text else []
    actual_tokens = actual_text.split() if actual_text else []
    matcher = SequenceMatcher(None, expected_tokens, actual_tokens)
    expected: list[dict[str, str]] = []
    actual: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for token in expected_tokens[i1:i2]:
                expected.append({"token": token, "status": "match"})
            for token in actual_tokens[j1:j2]:
                actual.append({"token": token, "status": "match"})
        elif tag == "delete":
            for token in expected_tokens[i1:i2]:
                expected.append({"token": token, "status": "missing"})
        elif tag == "insert":
            for token in actual_tokens[j1:j2]:
                actual.append({"token": token, "status": "extra"})
        elif tag == "replace":
            for token in expected_tokens[i1:i2]:
                expected.append({"token": token, "status": "substitution"})
            for token in actual_tokens[j1:j2]:
                actual.append({"token": token, "status": "substitution"})
    return {"expected": expected, "actual": actual}
