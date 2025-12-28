# SQL schema for MemCoach database

SCHEMA_SQL = """
-- Kids
CREATE TABLE IF NOT EXISTS kids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Decks
CREATE TABLE IF NOT EXISTS decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Parent texts for long-form content
CREATE TABLE IF NOT EXISTS texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    full_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
);

-- Cards (with SM-2 fields)
CREATE TABLE IF NOT EXISTS cards (
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
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE,
    FOREIGN KEY (text_id) REFERENCES texts (id) ON DELETE CASCADE
);

-- Review log
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    kid_id INTEGER NOT NULL,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    grade TEXT NOT NULL CHECK(grade IN ('perfect', 'good', 'fail')),
    user_text TEXT,
    FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE,
    FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE
);
"""

# Indexes for performance
INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_cards_due ON cards (due_date);
CREATE INDEX IF NOT EXISTS idx_cards_deck ON cards (deck_id);
CREATE INDEX IF NOT EXISTS idx_cards_text ON cards (text_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_reviews_card_kid ON reviews (card_id, kid_id);
CREATE INDEX IF NOT EXISTS idx_reviews_ts ON reviews (ts);
"""
