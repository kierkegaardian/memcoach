from pathlib import Path

import config


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
