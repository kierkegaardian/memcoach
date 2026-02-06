from pathlib import Path
from datetime import date, timedelta

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
                "",
                "[ollama]",
                "model = \"llama3.2\"",
                "timeout = 15",
            ]
        ),
        encoding="utf-8",
    )


def test_review_submit_renders_result_partial(tmp_path, monkeypatch):
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
        conn.commit()

    client = TestClient(app)
    response = client.post(
        f"/review/submit?kid_id={kid_id}&deck_id={deck_id}&card_id={card_id}",
        data={"user_text": "2"},
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
