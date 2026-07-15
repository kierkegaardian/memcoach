from utils.hints import build_first_letters_text


def test_first_letters_uppercase_and_hyphen_split():
    text = "well-known grace-filled mercy"
    assert build_first_letters_text(text) == "W-K G-F M"


def test_first_letters_uses_uppercase_for_mixed_case_words():
    text = "Amazing grace How sweet"
    assert build_first_letters_text(text) == "A G H S"
