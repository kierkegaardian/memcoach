.venv created for isolated environment
# MemCoach - Web Edition (Local-First, Server-Ready)

Build a **local-first web application** called **MemCoach** that helps kids memorize text (Bible verses, poems, quotes, etc.) using spaced repetition and AI-assisted grading — fully runnable offline, but designed from the ground up to be hosted on a server later.

## Core Requirements

- **Language**: Python 3.11+
- **Framework**: FastAPI + Jinja2 templates + HTMX (for smooth, snappy UI without heavy JS)
- **Frontend**: Simple, clean HTML/CSS with Tailwind CSS (via CDN) + minimal vanilla JS + HTMX for interactivity
- **Database**: SQLite (`~/.memcoach/memcoach.db`) — works perfectly locally and on servers
- **Run locally**: `http://127.0.0.1:8000` via `uvicorn`
- **Future-proof**: Can be deployed to any VPS, Fly.io, Render, Railway, etc. with zero code changes
- **AI Grading**: Use **Ollama** running locally (e.g. `llama3.2`, `phi3`, `gemma2`) for smart recall judgment

## Project Structure
```
memcoach/
├── main.py                  # FastAPI app entrypoint
├── config.py                # Load ~/.memcoach/config.toml
├── db/
│   ├── __init__.py
│   ├── database.py          # SQLite connection + init
│   └── schema.py            # Table creation
├── models/
│   ├── __init__.py
│   ├── kid.py
│   ├── deck.py
│   ├── card.py
│   └── review.py
├── routes/
│   ├── __init__.py
│   ├── kids.py
│   ├── decks.py
│   ├── cards.py
│   ├── review.py             # Core review session (HTMX-powered)
│   └── stats.py
├── templates/               # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── kids/
│   ├── decks/
│   ├── review.html          # Interactive review session
│   └── stats.html
├── static/
│   └── style.css            # Optional custom styles (Tailwind base + extras)
├── utils/
│   ├── __init__.py
│   ├── sm2.py               # SM-2 spaced repetition algorithm
│   ├── grading.py           # Levenshtein + Ollama grading logic
│   └── ollama.py            # Safe subprocess calls to Ollama
├── config.toml              # Example config (copied to ~/.memcoach on first run)
└── README.md
```

## Database Schema (SQLite)

```sql
-- Kids
CREATE TABLE kids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Decks
CREATE TABLE decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Cards (with SM-2 fields)
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    full_text TEXT NOT NULL,
    interval_days INTEGER NOT NULL DEFAULT 1,
    due_date TEXT NOT NULL DEFAULT (date('now')),
    ease_factor REAL NOT NULL DEFAULT 2.5,
    streak INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (deck_id) REFERENCES decks (id)
);

-- Review log
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    kid_id INTEGER NOT NULL,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    grade TEXT NOT NULL CHECK(grade IN ('perfect', 'good', 'fail')),
    user_text TEXT,
    FOREIGN KEY (card_id) REFERENCES cards (id),
    FOREIGN KEY (kid_id) REFERENCES kids (id)
);
```

## Config File (~/.memcoach/config.toml)

```toml
ollama_model = "llama3.2"
ollama_timeout = 15

# Grading thresholds
levenshtein_perfect_threshold = 0.98
levenshtein_good_threshold = 0.85

# Require LLM confirmation for borderline cases
use_llm_on_borderline = true
```

## Core Web Routes

| Route | Purpose | Method |
|-------|---------|--------|
| / | Home - list kids | GET |
| /kids/new | Add new kid | GET/POST |
| /kids/{kid_id}/decks | List decks for a kid | GET |
| /decks/new | Create new deck | GET/POST |
| /decks/{deck_id}/add | Add card(s) manually or via file upload | GET/POST |
| /review/{kid_id}/{deck_id} | Start interactive review session (HTMX-powered) | GET + HTMX |
| /review/next | HTMX: Get next due card | GET |
| /review/submit | HTMX: Submit recall attempt → grade → schedule | POST |
| /stats/{kid_id} | Stats dashboard per kid | GET |

## Card Import Behavior

- Support uploading a .txt file
- Split on blank lines → each block becomes a card
- Use fixed --prompt base (e.g. "Recite John 3:") + auto-number if multiple
- Example: prompt="Recite Psalm 23:" + verse 1,2,3... from file

## Review Session Flow (Beautiful & Kid-Friendly)

- Show prompt in large text
- Big textarea for child to type
- "I'm Done" button
- Instantly grade using:
  - Levenshtein ratio
  - Ollama call: "Does this correctly reproduce the text? Answer with exactly: perfect, good, or fail."
- Show result with color (green/orange/red) + correct text
- Auto-load next card via HTMX (no page refresh)

## Local Speech-to-Text Fallback

If browser voice input fails, use the **Record & transcribe** button. This sends audio to `/stt` and runs Whisper locally.

Requirements:
- `ffmpeg` installed on the host
- `faster-whisper` Python package (included in `requirements.txt`)

Optional config:
```toml
[stt]
provider = "auto"
model = "base"
language = "en"
device = "cpu"
compute_type = "int8"
normalize_audio = true
vad_filter = true
no_speech_threshold = 0.6
log_prob_threshold = -1.0
fallback_no_speech_threshold = 0.9
fallback_log_prob_threshold = -5.0
```

## SM-2 Implementation (in utils/sm2.py)

- Grade mapping: perfect→4, good→3, fail→0
- Standard SM-2 interval/ease updates
- due_date = today + interval_days

## First-Run Experience

- On first visit:
  - Auto-create ~/.memcoach/ directory
  - Copy default config.toml if missing
  - Run DB migrations (create tables)

## Installation & Running

```bash
# Clone and install
git clone https://github.com/you/memcoach-web.git
cd memcoach-web
pip install fastapi uvicorn jinja2 python-multipart levenshtein python-dotenv

# First run (sets up config and DB)
python main.py --init

# Run locally
uvicorn main:app --reload --port 8000
```
Then open: http://localhost:8000

## Bonus Points (Nice to Have)

- Dark mode toggle
- Progress bars per deck
- Export/import decks as .txt

## Local Bible Dataset (KJV)

This repo ships with a small local KJV dataset in `data/kjv.json` to support offline verse lookups.

**Format**
```json
{
  "translation": "KJV",
  "verses": [
    {
      "translation": "KJV",
      "book": "John",
      "chapter": 3,
      "verse": 16,
      "text": "For God so loved the world..."
    }
  ]
}
```

**Lookup helper**
- `utils/bible.py` provides `get_passage(translation, book, chapter, start_verse, end_verse, include_verses=False)`
- Returns a dict with `text`, `reference`, and optionally `verses` (per-verse breakdown).
- Mobile-friendly responsive design
- Confetti on 10-day streak ✨

## Why This Design Wins

- 100% local, private, no cloud dependency
- Ollama runs on your machine → zero cost, full privacy
- Works offline after first load
- Deployable anywhere with one command
- Beautiful, fast, and fun for kids

## Virtual Environment Setup

The project uses a virtual environment (.venv) for dependencies.

```bash
cd memcoach
source .venv/bin/activate  # On Linux/Mac
# or .venv\Scripts\activate on Windows

pip install -r requirements.txt
```

Deactivate with `deactivate`.
EOF
# memcoach
