from pathlib import Path

import config
from routes.parent import sanitize_next_path
from starlette.requests import Request
from utils.auth import get_parent_pin_hash, is_parent_unlocked


def _write_config(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_set_parent_pin_hash_updates_existing_section(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    _write_config(config_path, "[parent]\npin_hash = \"\"\n")

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)

    config.set_parent_pin_hash("abc123")

    updated = config_path.read_text(encoding="utf-8")
    assert 'pin_hash = "abc123"' in updated


def test_set_parent_pin_hash_adds_section_when_missing(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    _write_config(config_path, "[grading]\nlevenshtein_good_threshold = 0.85\n")

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)

    config.set_parent_pin_hash("xyz789")

    updated = config_path.read_text(encoding="utf-8")
    assert "[parent]" in updated
    assert 'pin_hash = "xyz789"' in updated


def test_sanitize_next_path_blocks_external_and_protocol_relative():
    assert sanitize_next_path("https://evil.example/path") == "/"
    assert sanitize_next_path("//evil.example/path") == "/"
    assert sanitize_next_path("/kids") == "/kids"


def test_load_config_invalid_numeric_env_uses_defaults(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    _write_config(config_path, "[stt]\nno_speech_threshold = 0.6\n")

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    monkeypatch.setenv("STT_NO_SPEECH_THRESHOLD", "not-a-number")
    monkeypatch.setenv("STT_LOG_PROB_THRESHOLD", "bad-value")

    loaded = config.load_config()
    assert loaded["stt"]["no_speech_threshold"] == 0.6
    assert loaded["stt"]["log_prob_threshold"] == -1.0


def test_parent_routes_are_unlocked_until_pin_is_configured(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    _write_config(config_path, "[parent]\npin_hash = \"\"\n")

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)

    request = Request({"type": "http", "headers": []})

    assert get_parent_pin_hash() is None
    assert is_parent_unlocked(request)
