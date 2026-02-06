from __future__ import annotations

import re
from typing import Optional, List

_TOKEN_RE = re.compile(r"[\w']+")


def normalize_fts_query(raw: Optional[str]) -> Optional[str]:
    """Normalize user input into a safe FTS5 MATCH query.

    Returns:
        None if raw is empty/None,
        "" if raw contains no searchable tokens,
        otherwise a quoted-token query string.
    """
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    tokens: List[str] = _TOKEN_RE.findall(cleaned)
    if not tokens:
        return ""
    quoted_tokens = [f'"{token}"' for token in tokens]
    return " ".join(quoted_tokens)
