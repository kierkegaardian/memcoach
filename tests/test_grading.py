from utils import grading


def test_borderline_does_not_try_llm_by_default(monkeypatch):
    def unexpected_llm_call(*_args, **_kwargs):
        raise AssertionError("LLM grading must be explicitly enabled")

    monkeypatch.setattr(grading, "grade_with_llm", unexpected_llm_call)
    config = {
        "grading": {
            "levenshtein_perfect_threshold": 0.98,
            "levenshtein_good_threshold": 0.85,
        }
    }

    grade = grading.grade_recall("the quick brown fox", "the quick brwn fox", config)

    assert grade == "good"


def test_borderline_llm_failure_stays_good(monkeypatch):
    monkeypatch.setattr(grading, "grade_with_llm", lambda *_args, **_kwargs: None)
    config = {
        "grading": {
            "levenshtein_perfect_threshold": 0.98,
            "levenshtein_good_threshold": 0.85,
            "use_llm_on_borderline": True,
        },
        "ollama": {"provider": "local_cli"},
    }
    grade = grading.grade_recall("the quick brown fox", "the quick brwn fox", config)
    assert grade == "good"


def test_enabled_flag_with_disabled_provider_does_not_try_llm(monkeypatch):
    def unexpected_llm_call(*_args, **_kwargs):
        raise AssertionError("disabled provider must not attempt LLM grading")

    monkeypatch.setattr(grading, "grade_with_llm", unexpected_llm_call)
    config = {
        "grading": {
            "levenshtein_perfect_threshold": 0.98,
            "levenshtein_good_threshold": 0.85,
            "use_llm_on_borderline": True,
        },
        "ollama": {"provider": "disabled"},
    }

    grade = grading.grade_recall("the quick brown fox", "the quick brwn fox", config)

    assert grade == "good"
