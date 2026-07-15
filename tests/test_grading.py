from utils import grading


def test_borderline_llm_failure_stays_good(monkeypatch):
    monkeypatch.setattr(grading, "grade_with_llm", lambda *_args, **_kwargs: None)
    config = {
        "grading": {
            "levenshtein_perfect_threshold": 0.98,
            "levenshtein_good_threshold": 0.85,
            "use_llm_on_borderline": True,
        }
    }
    grade = grading.grade_recall("the quick brown fox", "the quick brwn fox", config)
    assert grade == "good"
