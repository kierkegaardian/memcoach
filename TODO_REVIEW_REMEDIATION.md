# Review Remediation Status

## Scope
Address security/safety, type robustness, maintainability, pedagogy correctness, and portability gaps identified in the original code review. Checked items reflect the validated baseline as of 2026-07-15; unchecked items remain future work.

For the product requirement "fully offline Android from initial release," use
`TODO_ANDROID_NATIVE_OFFLINE.md` as the primary mobile plan. The web wrapper/TWA
track below is now secondary.

## Prerequisite (Infra-0)

- [x] Repair local test runner + environment baseline.
  - Recreate/fix `.venv` so test shebangs are valid for this repo path.
  - Verify `pytest -q` runs locally.
  - Add a short `README` note for reproducible test setup.
  - Acceptance: contributors can run tests without path/shebang failures.

## Priority 0: Safety, Security, and Integrity

- [x] Fix cross-deck review submission integrity checks.
  - Files: `routes/review.py`, `routes/today.py`.
  - Change:
    - Enforce `(card_id, deck_id)` ownership before write operations.
    - Keep explicit mismatch rejection in today flow; mirror same rigor in review flow.
  - Tests:
    - Reject submit when `card_id` does not belong to provided `deck_id`.
  - Acceptance: no review can be recorded against a mismatched deck context.

- [x] Add CSRF protection for form/HTMX mutation routes.
  - Files: `main.py`, templates (starting with `templates/base.html`), mutation routes.
  - Change:
    - Add CSRF middleware/token strategy compatible with FastAPI + HTMX.
    - Ensure all POST endpoints validate token.
  - Tests:
    - POST without token rejected.
    - Valid token accepted.
  - Acceptance: state-changing endpoints are not CSRF-vulnerable.

- [x] Sanitize `next_path` redirects in parent routes.
  - Files: `routes/parent.py`.
  - Change: allow only internal relative paths (leading `/`, no scheme/host/protocol-relative).
  - Tests:
    - External/protocol-relative redirect values fallback to `/`.
  - Acceptance: no open redirect via parent unlock/lock/setup flows.

- [x] Add upload size limits + bounded reads for all upload endpoints.
  - Files: `routes/backups.py`, `routes/stt.py`, `routes/cards.py`, optionally shared helper in `utils/`.
  - Change:
    - Remove unbounded `await file.read()` on user payloads.
    - Enforce endpoint-specific max sizes (configurable in `config.toml` + `config.py`).
    - Read/upload in chunks and abort on limit breach with 413.
  - Tests:
    - Oversized upload rejected for backup restore/STT/card import.
    - Boundary-at-limit upload accepted.
  - Acceptance: uploads cannot exhaust process memory through single request payloads.

## Priority 1: Logic, Concurrency, and Resilience

- [x] Remove optimistic grading fallback on LLM failure.
  - Files: `utils/ollama.py`, `utils/grading.py`.
  - Change:
    - Replace silent `good` fallback with deterministic fail-safe local behavior.
    - Preserve pedagogical integrity: failures do not inflate performance.
  - Tests:
    - Borderline + LLM failure path does not auto-upgrade grade.
  - Acceptance: grading failures never produce optimistic outcomes.

- [x] Harden config numeric coercion.
  - Files: `config.py`.
  - Change: replace direct `float(...)` env parsing with guarded coercion helpers.
  - Tests:
    - Invalid env values do not crash config loading.
  - Acceptance: bad env input degrades to defaults, not crashes.

- [x] Ensure blocking operations do not stall async request handling.
  - Files: `utils/ollama.py`, `utils/stt.py`, call sites in routes.
  - Change:
    - Audit blocking subprocess/compute paths.
    - Use thread offloading where needed (`asyncio.to_thread`/equivalent).
  - Tests:
    - Add focused tests for route responsiveness around blocking calls where practical.
  - Acceptance: no synchronous heavy operations block event loop in async routes.

- [x] Improve SQLite concurrency defaults.
  - Files: `db/database.py`.
  - Change:
    - Evaluate and enable WAL mode + appropriate busy timeout.
    - Confirm compatibility with backup/restore flows.
  - Acceptance: fewer lock-contention failures under concurrent usage.

## Priority 2: Portability and Data-Safety

- [x] Make restore flow robust across Windows/macOS/Linux.
  - Files: `routes/backups.py`, `db/database.py`.
  - Change:
    - Harden replacement sequence for file-lock-sensitive platforms.
    - Ensure failures are atomic/non-destructive and clearly reported.
  - Tests:
    - Simulated restore failure preserves original DB/config.
  - Acceptance: restore does not leave partial or corrupted state on failure.

- [x] Improve browser/mobile recording compatibility.
  - Files: `templates/review.html`, possibly `routes/stt.py`.
  - Change:
    - Add broader MIME fallback handling (including Safari/iOS-compatible options where supported).
    - Improve unsupported-feature messaging.
  - Acceptance: recording flow degrades gracefully across Chrome/Firefox/Safari mobile+desktop.

## Priority 3: Type Safety and Maintainability

- [ ] Introduce static type checking baseline.
  - Files: type-check config (`pyproject.toml` or `mypy.ini`), selected modules.
  - Change:
    - Add mypy/pyright config with practical strictness.
    - Start with `config.py`, `utils/progress.py`, `routes/review.py`, `routes/today.py`.
    - Replace broad `Dict[str, Any]` with `TypedDict`/dataclass where practical.
  - Acceptance: type checker passes for scoped modules; expansion plan documented.

- [x] Remove stale/unused model imports and align model usage.
  - Files: `routes/cards.py`, `routes/decks.py`, `routes/kids.py`, `models/*.py`.
  - Acceptance: no unused model imports in routes; model layer reflects actual API usage.

- [ ] Split oversized files into focused units.
  - Files: `routes/cards.py`, `routes/review.py`, `routes/today.py`, `templates/review.html`.
  - Change:
    - Extract reusable review/session logic into helper modules.
    - Move large in-template JS to `static/` script files.
  - Acceptance: improved cohesion, smaller modules, and preserved behavior.

## Feature Roadmap: High-Impact

- [ ] Gamification & motivation system.
  - Files: new `utils/gamification.py`, `routes/stats.py`, templates.
  - Change:
    - XP/points system — award points per review weighted by grade and difficulty.
    - Achievement badges ("First Perfect Streak," "100 Cards Mastered," "7-Day Streak," etc.).
    - Visual streak calendar — GitHub-style heatmap of daily activity.
    - Level system with fun titles ("Memory Apprentice" → "Recall Champion").
    - Optional leaderboard for multiple students.
  - Acceptance: students see XP, badges, and streak calendar on their dashboard.

- [ ] Audio/oral recitation mode.
  - Files: `templates/review.html`, `routes/review.py`, `routes/stt.py`.
  - Change:
    - Wire STT (faster-whisper) into the review flow as a first-class "speak" option.
    - Add text-to-speech playback of reference text via browser `SpeechSynthesis` API.
    - Show STT transcript side-by-side with reference on result screen.
  - Acceptance: students can complete a review session entirely by speaking.

- [ ] Progressive difficulty / auto-scaffolding.
  - Files: `utils/hints.py`, `routes/review.py`, `routes/today.py`.
  - Change:
    - Auto-scaffolding — start new cards with heavy hints, reduce as student succeeds, re-introduce on failure.
    - Passage build-up — review chunks individually, then progressively combine into larger sections.
  - Acceptance: hint level adjusts automatically based on card progress without manual selection.

- [ ] Offline PWA support.
  - Files: new `static/manifest.json`, new `static/sw.js`, `templates/base.html`.
  - Change:
    - Add `manifest.json` with app icon, name, theme color, `display: standalone`.
    - Add Service Worker to cache HTML shell, Tailwind CSS, HTMX, and static assets.
    - Register SW in `base.html`.
    - Optional: offline review submission queue that replays when back online.
  - Acceptance: app installable via "Add to Home Screen" on Android/iOS; static assets load offline.

## Feature Roadmap: Analytics & Parent

- [ ] Enhanced reporting dashboard.
  - Files: `routes/stats.py`, `routes/reports.py`, templates, optionally add Chart.js to `static/vendor/`.
  - Change:
    - Time-series charts for reviews/day, success rate trend, cards mastered over time.
    - Surface session duration averages and trends (data already in `reviews.duration_seconds`).
    - Predicted mastery date per deck based on current pace + SM-2 intervals.
    - Difficult cards report — cards with most failures or lowest ease factors.
  - Acceptance: stats page shows charts and actionable insights, not just raw counts.

- [ ] Notifications & reminders.
  - Files: new `static/push.js`, `templates/base.html`, optionally new `routes/notifications.py`.
  - Change:
    - Browser push notifications for due reviews (requires Service Worker + Push API).
    - "Study buddy" splash — motivating message if student hasn't reviewed in 2+ days.
    - Optional: email digest for parents (requires email config).
  - Acceptance: students receive at least in-app reminders when reviews are due.

## Feature Roadmap: Workflow & Content

- [ ] Deck sharing & import/export.
  - Files: `routes/backups.py` or new `routes/sharing.py`, `routes/cards.py`.
  - Change:
    - Export decks as JSON/ZIP (cards, tags, metadata).
    - Import decks from JSON.
    - QR code generation linking to a deck download URL.
  - Acceptance: a deck can be exported from one MemCoach instance and imported into another.

- [ ] Additional practice modes.
  - Files: `routes/review.py`, `templates/review.html`, `utils/hints.py`.
  - Change:
    - Multiple choice — auto-generate wrong answers from other cards in the same deck.
    - Handwriting mode — canvas-based writing area (grade via STT/image-to-text or parent manual grade).
    - Enhanced cloze — richer fill-in-the-blank with configurable blank density.
  - Acceptance: at least multiple-choice mode available as a deck review option.

- [ ] Multi-language / i18n support.
  - Files: templates, new `utils/i18n.py` or Jinja2 i18n extension config.
  - Change:
    - UI string externalization with translation key system.
    - Ensure grading works correctly for non-Latin scripts (Hebrew, Greek, Arabic).
  - Acceptance: UI language switchable; Levenshtein grading passes tests with non-Latin input.

- [ ] Bulk operations.
  - Files: `routes/cards.py`, `routes/decks.py`, templates.
  - Change:
    - Multi-select cards for bulk tag/move/delete.
    - Deck merge and split-by-tag.
    - Drag-and-drop card reordering (currently button-based via `move_card`).
  - Acceptance: parent can select 10+ cards and apply a tag in one action.

## Cross-Platform Deployment

- [ ] **Primary mobile track: native offline Android**.
  - Plan and execution checklist: `TODO_ANDROID_NATIVE_OFFLINE.md`.
  - Requirement: fully offline usage with no Termux/server dependency.
  - Acceptance: app works in airplane mode for create/import/review/stats flow.

- [x] **Secondary track: hosted/PWA/wrapper paths**.
  - Keep as optional distribution channels after native Android baseline.
  - Includes: PWA installability, Docker hosting, wrapper/TWA polish, iOS evaluation.

## Cross-Cutting Verification

- [ ] Security audit pass for query construction and mutation routes.
  - Confirm SQL remains parameterized in dynamic query builders.
  - Re-check route authorization coverage for parent-only actions.

- [ ] Regression tests for all P0/P1 fixes.

- [ ] AGY re-review after implementation.
  - Save to a dated artifact under `reviews/agy/`.
  - Acceptance: no blocking P0/P1 findings remain.

## Execution Order

1. Infra-0: repair test runner baseline.
2. P0: integrity fix + CSRF + redirect sanitization + upload limits.
3. P1: grading fallback + config coercion + blocking I/O audit + SQLite concurrency.
4. P2: cross-platform restore hardening + mobile recording fallback.
5. P3: typing baseline + cleanup + file splits.
6. Native Android offline plan (`TODO_ANDROID_NATIVE_OFFLINE.md`) Phase 0-2.
7. Native Android offline plan (`TODO_ANDROID_NATIVE_OFFLINE.md`) Phase 3-6.
8. Feature roadmap (gamification → oral recitation → scaffolding → reporting → remaining).
9. Optional hosted/PWA/wrapper tracks.
10. Final verification and AGY re-review.

## Done Criteria

- All P0/P1 items implemented with tests.
- `pytest -q` runs locally in this repo.
- Type checker configured and passing for defined initial scope.
- Final AGY review reports no unresolved blocking P0/P1 issues.
- Native Android app is fully offline and installable without Termux/server setup.
- PWA/wrapper availability is optional and no longer required for initial release.
