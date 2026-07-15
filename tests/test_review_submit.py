from pathlib import Path
from datetime import date, timedelta

from fastapi.testclient import TestClient

import config
from db import database
from main import app
from utils.auth import hash_pin


def _write_test_config(config_path: Path) -> None:
    config_path.write_text(
        "\n".join(
            [
                "[grading]",
                "levenshtein_perfect_threshold = 0.98",
                "levenshtein_good_threshold = 0.85",
                "use_llm_on_borderline = false",
                "",
                "[ollama]",
                "model = \"llama3.2\"",
                "timeout = 15",
            ]
        ),
        encoding="utf-8",
    )


def _bootstrap_test_db(tmp_path, monkeypatch):
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
        cursor.execute("INSERT INTO kids (name) VALUES (?)", ("Ada",))
        cursor.execute("INSERT INTO decks (name) VALUES (?)", ("Algebra",))
        kid_id = cursor.execute("SELECT id FROM kids WHERE name = ?", ("Ada",)).fetchone()[0]
        deck_id = cursor.execute("SELECT id FROM decks WHERE name = ?", ("Algebra",)).fetchone()[0]
        cursor.execute(
            """
            INSERT INTO cards (deck_id, prompt, full_text, interval_days, ease_factor, streak, due_date)
            VALUES (?, ?, ?, 1, 2.5, 0, date('now'))
            """,
            (deck_id, "1+1?", "2"),
        )
        card_id = cursor.execute(
            "SELECT id FROM cards WHERE deck_id = ?",
            (deck_id,),
        ).fetchone()[0]
        cursor.execute("INSERT INTO decks (name) VALUES (?)", ("Geometry",))
        wrong_deck_id = cursor.execute("SELECT id FROM decks WHERE name = ?", ("Geometry",)).fetchone()[0]
        conn.commit()
    return kid_id, deck_id, card_id, wrong_deck_id


def _csrf_headers(client: TestClient) -> dict[str, str]:
    client.get("/")
    token = client.cookies.get("memcoach_csrf_token")
    assert token
    return {"x-csrf-token": token}


def test_review_submit_renders_result_partial(tmp_path, monkeypatch):
    kid_id, deck_id, card_id, _wrong_deck_id = _bootstrap_test_db(tmp_path, monkeypatch)

    client = TestClient(app)
    headers = _csrf_headers(client)
    response = client.post(
        f"/review/submit?kid_id={kid_id}&deck_id={deck_id}&card_id={card_id}",
        data={"user_text": "2"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.text
    assert "Your Grade: PERFECT" in body
    assert "<strong>You typed:</strong> 2" in body
    assert "<strong>Correct:</strong> 2" in body
    assert "Next Card" in body
    assert "bg-green-100" in body

    with database.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT interval_days, streak, mastery_status, due_date
            FROM card_progress
            WHERE kid_id = ? AND card_id = ?
            """,
            (kid_id, card_id),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["interval_days"] == 6
        assert row["streak"] == 1
        assert row["mastery_status"] == "learning"
        assert row["due_date"] == (date.today() + timedelta(days=6)).isoformat()


def test_review_submit_requires_csrf_token(tmp_path, monkeypatch):
    kid_id, deck_id, card_id, _wrong_deck_id = _bootstrap_test_db(tmp_path, monkeypatch)
    client = TestClient(app)
    response = client.post(
        f"/review/submit?kid_id={kid_id}&deck_id={deck_id}&card_id={card_id}",
        data={"user_text": "2"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing"


def test_review_submit_rejects_deck_card_mismatch(tmp_path, monkeypatch):
    kid_id, _deck_id, card_id, wrong_deck_id = _bootstrap_test_db(tmp_path, monkeypatch)
    client = TestClient(app)
    headers = _csrf_headers(client)
    response = client.post(
        f"/review/submit?kid_id={kid_id}&deck_id={wrong_deck_id}&card_id={card_id}",
        data={"user_text": "2"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Deck does not match card"


def test_start_review_recitation_requires_parent_unlock(tmp_path, monkeypatch):
    config_dir = tmp_path / ".memcoach"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    _write_test_config(config_path)

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(database, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(database, "DB_PATH", config_dir / "memcoach.db")
    config.set_parent_pin_hash(hash_pin("1234"))

    database.init_db()
    with database.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO kids (name) VALUES (?)", ("Theo",))
        cursor.execute("INSERT INTO decks (name, review_mode) VALUES (?, ?)", ("Catechism", "recitation"))
        kid_id = cursor.execute("SELECT id FROM kids WHERE name = ?", ("Theo",)).fetchone()[0]
        deck_id = cursor.execute("SELECT id FROM decks WHERE name = ?", ("Catechism",)).fetchone()[0]
        conn.commit()

    client = TestClient(app)
    response = client.get(f"/review/{kid_id}/{deck_id}")
    assert response.status_code == 200
    assert "Parent Key Required" in response.text
