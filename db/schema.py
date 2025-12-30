# SQL schema for MemCoach database

SCHEMA_VERSION = 8

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
    review_mode TEXT NOT NULL DEFAULT 'free_recall' CHECK(review_mode IN ('free_recall', 'recitation', 'cloze', 'first_letters')),
    deleted_at TEXT
);

-- Kid/deck assignments
CREATE TABLE IF NOT EXISTS assignments (
    kid_id INTEGER NOT NULL,
    deck_id INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    days_of_week TEXT,
    new_cap INTEGER,
    review_cap INTEGER,
    paused_until TEXT,
    PRIMARY KEY (kid_id, deck_id),
    FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE,
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
);

-- Deck planning milestones
CREATE TABLE IF NOT EXISTS deck_plans (
    deck_id INTEGER PRIMARY KEY,
    weekly_goal INTEGER,
    target_date TEXT,
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
);

-- Deck mastery rules
CREATE TABLE IF NOT EXISTS deck_mastery_rules (
    deck_id INTEGER PRIMARY KEY,
    consecutive_grades INTEGER NOT NULL DEFAULT 3,
    min_ease_factor REAL NOT NULL DEFAULT 2.5,
    min_interval_days INTEGER NOT NULL DEFAULT 7,
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

-- Card search (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
    prompt,
    full_text,
    content='cards',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS cards_ai AFTER INSERT ON cards BEGIN
    INSERT INTO cards_fts(rowid, prompt, full_text)
    VALUES (new.id, new.prompt, new.full_text);
END;

CREATE TRIGGER IF NOT EXISTS cards_ad AFTER DELETE ON cards BEGIN
    INSERT INTO cards_fts(cards_fts, rowid, prompt, full_text)
    VALUES ('delete', old.id, old.prompt, old.full_text);
END;

CREATE TRIGGER IF NOT EXISTS cards_au AFTER UPDATE ON cards BEGIN
    INSERT INTO cards_fts(cards_fts, rowid, prompt, full_text)
    VALUES ('delete', old.id, old.prompt, old.full_text);
    INSERT INTO cards_fts(rowid, prompt, full_text)
    VALUES (new.id, new.prompt, new.full_text);
END;

-- Tags
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS deck_tags (
    deck_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (deck_id, tag_id),
    FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS card_tags (
    card_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (card_id, tag_id),
    FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

-- Review log
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    kid_id INTEGER NOT NULL,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    grade TEXT NOT NULL CHECK(grade IN ('perfect', 'good', 'fail')),
    auto_grade TEXT CHECK(auto_grade IN ('perfect', 'good', 'fail')),
    final_grade TEXT CHECK(final_grade IN ('perfect', 'good', 'fail')),
    graded_by TEXT NOT NULL DEFAULT 'auto' CHECK(graded_by IN ('auto', 'parent')),
    review_mode TEXT NOT NULL DEFAULT 'free_recall' CHECK(review_mode IN ('free_recall', 'recitation', 'cloze', 'first_letters')),
    hint_mode TEXT NOT NULL DEFAULT 'none',
    user_text TEXT,
    duration_seconds INTEGER,
    FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE,
    FOREIGN KEY (kid_id) REFERENCES kids (id) ON DELETE CASCADE
);

-- Bible verses (local KJV or other translations)
CREATE TABLE IF NOT EXISTS bible_verses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation TEXT NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL
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
CREATE INDEX IF NOT EXISTS idx_deck_mastery_rules_deck ON deck_mastery_rules (deck_id);
CREATE INDEX IF NOT EXISTS idx_texts_deck ON texts (deck_id);
CREATE INDEX IF NOT EXISTS idx_texts_deleted ON texts (deleted_at);
CREATE INDEX IF NOT EXISTS idx_kids_deleted ON kids (deleted_at);
CREATE INDEX IF NOT EXISTS idx_decks_deleted ON decks (deleted_at);
CREATE INDEX IF NOT EXISTS idx_reviews_card_kid ON reviews (card_id, kid_id);
CREATE INDEX IF NOT EXISTS idx_reviews_ts ON reviews (ts);
CREATE INDEX IF NOT EXISTS idx_assignments_kid ON assignments (kid_id);
CREATE INDEX IF NOT EXISTS idx_assignments_deck ON assignments (deck_id);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags (name);
CREATE INDEX IF NOT EXISTS idx_deck_tags_deck ON deck_tags (deck_id);
CREATE INDEX IF NOT EXISTS idx_deck_tags_tag ON deck_tags (tag_id);
CREATE INDEX IF NOT EXISTS idx_card_tags_card ON card_tags (card_id);
CREATE INDEX IF NOT EXISTS idx_card_tags_tag ON card_tags (tag_id);
CREATE INDEX IF NOT EXISTS idx_bible_verses_lookup ON bible_verses (translation, book, chapter, verse);
CREATE INDEX IF NOT EXISTS idx_bible_verses_book ON bible_verses (book, chapter, verse);
"""
