from utils.search import normalize_fts_query


def test_normalize_fts_query_tokenizes_punctuation():
    assert normalize_fts_query("John 3:16") == '"John" "3" "16"'


def test_normalize_fts_query_empty_tokens():
    assert normalize_fts_query("!!!") == ""
    assert normalize_fts_query("   ") is None
