import re
from typing import List, Tuple

DEFAULT_HINT_MODE = "none"
EVERY_NTH_WORD_DEFAULT = 3
HINT_MODE_OPTIONS: List[Tuple[str, str]] = [
    ("none", "No hints"),
    ("first_letters", "First letters"),
    ("every_nth_word", f"Every {EVERY_NTH_WORD_DEFAULT}rd word"),
    ("line_by_line", "Line by line"),
]


def normalize_hint_mode(mode: str) -> str:
    if not mode:
        return DEFAULT_HINT_MODE
    mode = mode.strip().lower()
    valid_modes = {option[0] for option in HINT_MODE_OPTIONS}
    return mode if mode in valid_modes else DEFAULT_HINT_MODE


def _mask_words_every_nth(text: str, nth: int) -> str:
    if nth <= 0:
        return text
    tokens = re.split(r"(\s+)", text)
    word_index = 0
    masked_tokens = []
    for token in tokens:
        if not token or token.isspace():
            masked_tokens.append(token)
            continue
        word_index += 1
        if word_index % nth == 0:
            masked_tokens.append(token)
        else:
            masked_tokens.append("____")
    return "".join(masked_tokens)


def _first_letters(text: str) -> str:
    tokens = re.split(r"(\s+)", text)
    initials = []
    for token in tokens:
        if not token or token.isspace():
            initials.append(token)
        else:
            initials.append(token[0])
    return "".join(initials).strip()


def _line_by_line(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    return "\n".join([lines[0]] + ["…" for _ in lines[1:]])


def build_hint_text(full_text: str, mode: str) -> str:
    mode = normalize_hint_mode(mode)
    if mode == "none":
        return ""
    if mode == "first_letters":
        return _first_letters(full_text)
    if mode == "every_nth_word":
        return _mask_words_every_nth(full_text, EVERY_NTH_WORD_DEFAULT)
    if mode == "line_by_line":
        return _line_by_line(full_text)
    return ""
