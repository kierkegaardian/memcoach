# SQL schema for MemCoach database

SCHEMA_VERSION = 2

SCHEMA_SQL = """
-- Kids
CREATE TABLE IF NOT EXISTS kids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    deleted_at TEXT
);

-- Decks
CREATE TABLE IF NOT EXISTS decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    deleted_at TEXT
);

-- Deck planning milestones
CREATE TABLE IF NOT EXISTS deck_plans (
    deck_id INTEGER PRIMARY KEY,
    weekly_goal INTEGER,
    target_date TEXT,
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
);

-- Long texts (parent for chunked cards)
CREATE TABLE IF NOT EXISTS texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    full_text TEXT NOT NULL,
    chunk_strategy TEXT NOT NULL DEFAULT 'lines',
    delimiter TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
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
    mastery_status TEXT NOT NULL DEFAULT 'new' CHECK(mastery_status IN ('new', 'learning', 'mastered')),
    position INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE,
    FOREIGN KEY (text_id) REFERENCES texts (id) ON DELETE SET NULL
);

-- Review log
CREATE TABLE IF NOT EXISTS reviews (
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
"""

# Indexes for performance
INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_cards_due ON cards (due_date);
CREATE INDEX IF NOT EXISTS idx_cards_deck ON cards (deck_id);
CREATE INDEX IF NOT EXISTS idx_cards_text ON cards (text_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_cards_deleted ON cards (deleted_at);
CREATE INDEX IF NOT EXISTS idx_cards_deck_position ON cards (deck_id, position);
CREATE INDEX IF NOT EXISTS idx_deck_plans_deck ON deck_plans (deck_id);
CREATE INDEX IF NOT EXISTS idx_texts_deck ON texts (deck_id);
CREATE INDEX IF NOT EXISTS idx_texts_deleted ON texts (deleted_at);
CREATE INDEX IF NOT EXISTS idx_kids_deleted ON kids (deleted_at);
CREATE INDEX IF NOT EXISTS idx_decks_deleted ON decks (deleted_at);
CREATE INDEX IF NOT EXISTS idx_reviews_card_kid ON reviews (card_id, kid_id);
CREATE INDEX IF NOT EXISTS idx_reviews_ts ON reviews (ts);
"""
