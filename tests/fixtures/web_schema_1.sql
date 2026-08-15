PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

CREATE TABLE kids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE deck_plans (
    deck_id INTEGER PRIMARY KEY,
    weekly_goal INTEGER,
    target_date TEXT,
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
);
CREATE TABLE texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    full_text TEXT NOT NULL,
    chunk_strategy TEXT NOT NULL DEFAULT 'lines',
    delimiter TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
);
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    full_text TEXT NOT NULL,
    text_id INTEGER,
    chunk_index INTEGER,
    interval_days INTEGER NOT NULL DEFAULT 1,
    due_date TEXT NOT NULL DEFAULT (date('now')),
    ease_factor REAL NOT NULL DEFAULT 2.5,
    streak INTEGER NOT NULL DEFAULT 0,
    mastery_status TEXT NOT NULL DEFAULT 'new'
        CHECK(mastery_status IN ('new', 'learning', 'mastered')),
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE,
    FOREIGN KEY (text_id) REFERENCES texts (id) ON DELETE SET NULL
);
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    kid_id INTEGER NOT NULL,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    grade TEXT NOT NULL CHECK(grade IN ('perfect', 'good', 'fail')),
    hint_mode TEXT NOT NULL DEFAULT 'none',
    user_text TEXT,
    FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE,
    FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE
);

CREATE INDEX idx_cards_due ON cards (due_date);
CREATE INDEX idx_cards_deck ON cards (deck_id);
CREATE INDEX idx_cards_text ON cards (text_id, chunk_index);
CREATE INDEX idx_deck_plans_deck ON deck_plans (deck_id);
CREATE INDEX idx_texts_deck ON texts (deck_id);
CREATE INDEX idx_reviews_card_kid ON reviews (card_id, kid_id);
CREATE INDEX idx_reviews_ts ON reviews (ts);

INSERT INTO kids (id, name) VALUES (1, 'Version One Kid');
INSERT INTO decks (id, name) VALUES (1, 'Version One Deck');
INSERT INTO deck_plans (deck_id, weekly_goal, target_date)
VALUES (1, 3, '2026-08-01');
INSERT INTO texts (
    id, deck_id, title, full_text, chunk_strategy, delimiter, created_at
) VALUES (
    1, 1, 'Version One Text', 'First line. Second line.', 'lines', NULL,
    '2026-07-14 00:00:00'
);
INSERT INTO cards (
    id, deck_id, prompt, full_text, text_id, chunk_index, interval_days,
    due_date, ease_factor, streak, mastery_status
) VALUES (
    1, 1, 'Recite the fixture', 'First line.', 1, 0, 1,
    '2026-07-14', 2.5, 0, 'new'
);
INSERT INTO reviews (
    id, card_id, kid_id, ts, grade, hint_mode, user_text
) VALUES (
    1, 1, 1, '2026-07-14 09:00:00', 'perfect', 'none', 'First line.'
);

PRAGMA user_version = 1;
COMMIT;
