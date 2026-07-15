from pathlib import Path

from fastapi.testclient import TestClient

import config
from db import database
from main import app


def _write_test_config(config_path: Path) -> None:
    config_path.write_text(
        "\n".join(
            [
                "[grading]",
                "levenshtein_perfect_threshold = 0.98",
                "levenshtein_good_threshold = 0.85",
                "use_llm_on_borderline = false",
            ]
        ),
        encoding="utf-8",
    )


def test_kid_mode_hides_recitation_decks(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    _write_test_config(config_path)

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(database, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(database, "DB_PATH", config_dir / "memcoach.db")

    database.init_db()
    with database.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO kids (name) VALUES (?)", ("Eli",))
        cursor.execute("INSERT INTO decks (name, review_mode) VALUES (?, ?)", ("Spelling", "free_recall"))
        cursor.execute("INSERT INTO decks (name, review_mode) VALUES (?, ?)", ("Recitation Only", "recitation"))
        kid_id = cursor.execute("SELECT id FROM kids WHERE name = ?", ("Eli",)).fetchone()[0]
        conn.commit()

    client = TestClient(app)
    response = client.get(f"/kid-mode/{kid_id}")
    assert response.status_code == 200
    body = response.text
    assert "Spelling" in body
    assert "Recitation Only" not in body
    assert "parent-led deck" in body


def test_home_redirects_to_kid_mode(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    _write_test_config(config_path)

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(database, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(database, "DB_PATH", config_dir / "memcoach.db")
    database.init_db()

    client = TestClient(app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/kid-mode"
