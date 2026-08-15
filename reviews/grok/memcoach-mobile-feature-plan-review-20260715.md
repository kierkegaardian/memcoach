I'll review the plan against the actual MemCoach codebase so findings are grounded in real schema, migrations, and Android packaging rather than the plan alone.# Plan review: MemCoach mobile + phone deploy

Baseline checked: `main` @ `de3d3ca`, web SQLite `SCHEMA_VERSION = 9`, Room DB v1 / `exportSchema = false`, no Room migrations registered, Android entity model is a strict subset of web.

---

## Findings

### P0 — must fix before implementing Milestones 0–1

**1. Portable package identity is incomplete for reviews and junctions**  
Plan: “stable portable UUIDs for primary entities” + “deduplicate reviews by portable UUID.”  
Reality: web/Android reviews use autoincrement `id`; `assignments`, `card_progress`, and tag links are composite PKs with no natural portable ID.

**Corrections:**
- Require `portable_id` (UUID string, unique index) on: kids, decks, cards, texts (web), tags (web), **reviews**, and optionally a single `portable_id` on `card_progress` rows.
- Junctions (`assignments`, `deck_tags`, `card_tags`, `deck_plans`, `deck_mastery_rules`): **no new UUIDs required** if package edges always reference parent portable UUIDs; document that as the contract.
- Backfill rule must be explicit: **store once, never recompute**. Random UUID on first migration is fine. Do **not** use display names. Do **not** use local row IDs alone across devices.
- Reject packages that omit review `portable_id`s when reviews are present.

**2. Merge can destroy scheduling / progress (silent data loss)**  
“Update matching portable UUIDs” with no field-level rules is unsafe for `card_progress` and cards’ scheduling fields.

**Corrections — add a merge matrix:**

| Entity | On portable_id match |
| --- | --- |
| Content (prompt, full_text, deck name, kid name) | Import wins only if `updated_at` (add this) is newer; else keep local and warn |
| `card_progress` | **Newer `last_review_ts` / `lastReviewEpochMillis` wins entire progress row**; never merge half-fields |
| Reviews | Insert-if-absent by review `portable_id` only; never update historical reviews |
| Soft-deleted web rows | Do not resurrect deleted local entities on merge unless package marks `deleted_at` and policy is explicit |

Also: both sides enforce **UNIQUE kid/deck names**. Merge-by-UUID still fails if two different UUIDs share a name. Define: rename import with suffix (`"Alice (import)"`) + warning, or hard-fail with counts—**never overwrite by name**.

**3. Web “schema version” is not a migration system today**  
`ensure_schema_version()` stamps `PRAGMA user_version = SCHEMA_VERSION` without stepwise upgrades (`db/database.py`). Incremental `ensure_*` column adds do not version-gate.

**Corrections:**
- Replace stamp-on-mismatch with a **monotonic migrator**: only run step *n* when `user_version == n-1`; then set `user_version = n`.
- Forbid bumping `SCHEMA_VERSION` without a corresponding `migrate_N_to_N+1` function and tests from a real v9 fixture.
- Gate: opening a captured pre-change DB file must prove columns/indexes/data counts, not just “app starts.”

**4. Web↔Android model asymmetry is underspecified → import data loss**  
M1 package lists tags, texts/chunks, plans, mastery rules, assignments, extended review fields. Room v1 only has kids/decks/cards/card_progress/reviews, and cards lack `text_id`, `chunk_index`, soft delete, mastery, tags, etc.

**Corrections:**
- Split package into **core** (required both runtimes) vs **extended** (web-only for v1).
- Core v1: kids, decks, cards (`prompt`/`full_text` + scheduling), card_progress, reviews (grade, user_text, timestamps, portable refs).
- Extended: tags, texts/chunks, plans, mastery, assignments, soft-delete, review grading metadata—web must export; Android must either (a) **preserve as opaque `extensions` and re-export without loss**, or (b) **fail import with a clear unsupported-section error**, never silent drop.
- Prefer (b) for first slice unless Android schema is expanded in the same PR as import.

**5. Canonical JSON + SHA-256 is not implementable as written**  
Integrity section + “cross-runtime proof” without a canonicalization algorithm will fail on key order, Unicode escapes, floats (`ease_factor`), and integer width.

**Corrections (specify in `contracts/`):**
- Digest input = UTF-8 bytes of **canonical form of the document with `integrity` removed** (or `integrity.sha256` set to empty string—pick one and fixture it).
- Algorithm: **RFC 8785 JCS** *or* a frozen local subset: UTF-8, sorted object keys, no insignificant whitespace, arrays preserve order, numbers as shortest integer or fixed decimal for floats (e.g. 6 fractional digits for ease), strings as JSON with `\u` escapes only where JCS requires.
- Ship **byte-identical golden files** produced by Python and verified by Kotlin (and reverse).
- Pause at dependency gate only if a new library is needed; hand-rolled JCS-lite is acceptable if fully fixture-covered.

**6. Room 1→2 on the live Galaxy A17 install is under-gated**  
`AppContainer` builds Room with **no** `.addMigrations(...)`. Phone has real data under debuggable `0.3.0`/3.

**Corrections:**
- M0: `exportSchema = true`, commit **schema v1 JSON**, `MigrationTestHelper` opens a **v1 fixture that mirrors production columns**, not only empty DB.
- M1: `Migration(1, 2)` adds `portable_id` (+ indexes), backfills non-null UUIDs, **no** `fallbackToDestructiveMigration`.
- Wire `.addMigrations(MIGRATION_1_2)` before any sideload.
- Pre/post install gate on `R5GL50EEHML`: row counts for kids/decks/cards/reviews/progress; abort if any count drops.
- Document restore from `app-state.tar` **before** relying on portable export (chicken-and-egg on first migration build).

**7. Phone `run-as` snapshot is secret-bearing; restore path missing**  
`shared_prefs` includes parent PIN hash material. Fine as **local disaster recovery**, not as portable export—but plan never says how to restore `app-state.tar` after a bad install.

**Corrections:**
- Label tar backups as **device-private, secret-bearing, not portable**.
- Add restore runbook: debug-only `run-as` extract → stop app → replace `databases/` + `shared_prefs/` → verify counts.
- After debug→release transition, `run-as` may stop working; **portable package becomes the only non-root recovery**—so M1 must be proven before uninstall.

---

### P1 — fix in plan / first slice bounds

**8. Kickoff vs “first phone release” conflict**  
Kickoff: implement **only M0–1**. Definition of done: includes **adaptive cues (M2)**.

**Correction:** First implementation slice / first sideload = M0–1 only. First *product* phone release may still require M2, but do not block M0–1 deploy gates on cues.

**9. `replace` and dual snapshot strategy under-specified on Android**  
“Automatic local snapshot” + “retain most recent two” needs: storage path (app-private), format (Room `.db` checkpoint copy with DB closed, or portable JSON), restore UI, and failure if disk full.

**Correction:** Before merge/replace: close DB → `PRAGMA wal_checkpoint(FULL)` / file copy → reopen. Keep 2 snapshots. Replace only after preview shows deletion counts and second confirmation.

**10. Deck-scope export is ambiguous**  
Does `scope: deck` include assigned kids, only cards of that deck, progress/reviews for those cards, or orphan risk?

**Correction:** Define deck package as: deck + its cards (+ texts if any) + optional `include_progress: bool`. Kids only if progress included; reviews only for those (kid, card) pairs. Reject packages with dangling portable refs.

**11. FTS / web post-import consistency**  
Web import does not mention `cards_fts` rebuild. Search can silently go stale.

**Correction:** After successful web import transaction, rebuild FTS (`INSERT INTO cards_fts(cards_fts) VALUES('rebuild')`) inside the same transaction if possible, or immediately after with failure = full rollback.

**12. Grading/SM-2 “shared fixtures” overclaim risk**  
Kotlin SM-2 already aims at Python parity (including `pythonRound`). Web grading can call LLM on borderline; Android is pure Levenshtein.  
**Correction:** Shared fixtures cover **deterministic** grade thresholds and SM-2 only; document LLM path as web-only and exclude from portable integrity of *grading engine* parity.

**13. Adaptive cue model (M2) not aligned with existing hints**  
Cue ladder: `study | guided | initials | recall`. Existing web hints: `none | first_letters | every_nth_word | line_by_line`. “Separate dates” lacks timezone.

**Corrections for M2 (not M0–1):**
- Map cue → display function in both runtimes; freeze fixtures for boundaries.
- “Separate dates” = calendar dates in **kid-local device timezone** (or store review `date` as `YYYY-MM-DD` at submit).
- Define ceilings: fail at `study` stays `study`; perfect at `recall` stays `recall`.
- Manual stronger cue ⇒ that attempt does not count toward the two-success progression (already stated—fixture it).
- Keep SM-2 inputs independent of cue transitions (already stated—add regression: fail cue-up does not change interval unless grade says so).

**14. ADB / deploy gates incomplete for A17**  
Missing concrete commands/guards:

| Gap | Correction |
| --- | --- |
| Multi-device installs | Require `adb -s R5GL50EEHML` everywhere; refuse if serial absent from `adb devices` |
| Cert re-check | Spell out: `apksigner verify --print-certs` (or `keytool`) on installed APK path vs candidate APK; compare SHA-256 to known debug digest |
| Post-install verify | `dumpsys package` versionCode/Name + signing cert after install |
| Storage | Check free space before install/snapshot |
| Makefile | `android-install-usb` has **no** `-s` serial—do not use it for the A17 path |
| Device migration proof | Pre-count → install `-r` → post-count + open due card |
| Emulator-only gate | Keep, but **do not treat emulator as substitute** for A17 migration proof |
| No `connectedAndroidTest` / instrumentation | At least one instrumentation or scripted adb smoke is needed before calling phone release “done” |
| Release transition | Export portable **and** keep last tar; uninstall debug only after disposable-DB restore proof; then install release; import; full checklist |

**15. SAF details**  
`CreateDocument` / `OpenDocument` need MIME (`application/json`), persistable URI optional (not required if one-shot), and **main-thread-off** copy of large files. Reject non-UTF-8 and oversize before parse (mirror web `backup_restore_max_bytes`).

**16. Kotlin JSON dependency gate**  
Hand-written JSON for a multi-entity package is a high bug surface.  
**Correction:** Either pre-approve a minimal JSON approach (`org.json` already on Android + Python `json` + shared fixtures) **without** kotlinx.serialization, or schedule an explicit dependency approval pause **before** coding M1 DTOs—not mid-implementation.

---

### P2 — polish / scope hygiene

**17. M0 “extract review-page JS” is oversized for portable work**  
`templates/review.html` is ~763 lines, mostly STT/browser speech. Portable M0–1 does not need that refactor.

**Correction:** Move STT JS extraction to M2+/M4. For M0, only split if a portable UI page needs it.

**18. M0 “type-check scheduling/progress boundary” + adaptive-cue fixtures**  
Adaptive-cue fixtures belong in M2. M0 should only add **placeholder** cue contract files if needed for directory layout—not full transition matrices.

**19. `installation_id`**  
Useful as export `source.installation_id` metadata only.  
**Correction:** Never use installation ID as entity identity or merge key.

**20. Bible verses / config / PIN**  
Plan correctly excludes PIN/config/signing from portable packages. Also exclude `bible_verses` bulk corpus unless explicitly scoped—otherwise huge exports.

**21. File-size rule**  
Plan already points at splitting oversized routes; good. Ensure new `portable/` and Android portable packages stay ≤300 LOC per file.

**22. Version naming**  
“Increment versionCode; prerelease versionName” is good—bind example: `0.4.0-portable.1` / versionCode `4` for first M1 sideload.

---

## Milestone sequencing (bounded?)

| Milestone | Verdict |
| --- | --- |
| **M0** | Implementable if adaptive-cue fixtures and full review JS extract are trimmed; Room v1 schema export + migration test harness is the critical path. |
| **M1** | Implementable only after P0 contract fixes (core vs extended, merge matrix, canonical digest, real SQLite migrator, Room 1→2). Still large but bounded if Android does **core-only** package. |
| **M2** | Sound pedagogy outline; needs cue↔hint mapping + timezone. Correctly after M1. |
| **M3–M4** | Correctly deferred; keep out of first slice. Passage stitching depends on `text_id`/`chunk_index` Android support—another reason not to fake extended parity in M1. |

Sequencing M0 → M1 → phone debug sideload → (later) M2 → release-sign transition is right. Do **not** couple release-key uninstall to M0–1.

---

## Verdict: **GO WITH CHANGES**

Direction is sound: portable IDs, non-destructive migrations, preview/merge/copy/replace, SAF, airplane-mode bar, debug-before-release, and deferred speech/scheduler. It is **not** safe to implement as written until identity/merge, web migrator, core-vs-extended package, canonical hashing, and live Room 1→2 phone gates are tightened.

---

## Smallest corrected first implementation slice

**Branch:** `codex/memcoach-mobile-coach-v1` from `de3d3ca`  
**Scope:** Milestone 0 + **core-only** Milestone 1. No adaptive cues, no STT, no passage stitching, no review.html STT extract, no tags/plans/mastery on Android, no debug→release uninstall.

### A. Contracts & preservation (M0)
1. Record baseline: `make check`, `make android-debug`, `git diff --check`.
2. `contracts/`: grade enums, SM-2 golden fixtures (Python↔Kotlin), `memcoach-backup-v1` JSON Schema for **core entities only**, canonicalization + digest algorithm + golden bytes.
3. Room `exportSchema = true`; commit v1 schema; `MigrationTestHelper` opens v1 fixture.
4. Web: introduce real versioned migrator scaffold **without** bumping production schema yet (or only no-op current=9).
5. New web code under `portable/` only; do not grow `routes/cards.py` / `routes/review.py`.

### B. Portable package core (M1)
1. SQLite **9→10**: `portable_id` + unique indexes on kids/decks/cards/reviews; `portable_id` on `card_progress`; `installation_id` metadata table/row; backfill UUIDs; tests from v9 fixture.
2. Room **1→2**: same portable fields; `addMigrations`; no destructive fallback; migration tests.
3. Export/import: `preview` / `merge` (with progress LWW + name-collision policy) / `copy` (rewrite UUID graph, no history); **optional** `replace` only if snapshot+confirm fully implemented—otherwise defer replace to a fast follow.
4. Reject: bad version, bad digest, dangling refs, duplicate UUIDs, oversize, secrets.
5. Web parent routes + keep raw SQLite zip as DR.
6. Android SAF Create/OpenDocument; parent-gated; local DB snapshots (2) before merge/replace.
7. Cross-runtime: Python golden → Kotlin import; Kotlin golden → Python import; merge idempotent; secrets absent.

### C. Phone gate (debug only, `R5GL50EEHML`)
1. Serial-locked adb; cert SHA-256 match; force-stop; `run-as` tar + SHA256SUMS; **document tar restore**.
2. Pre-count entities → `adb -s … install -r` debug APK (bumped versionCode) → post-count + open app + due review.
3. Export package; validate digest on host; preview; import into disposable DB/emulator; airplane-mode smoke.
4. Stop on any count drop, migration failure, or cert mismatch. **No uninstall, no release key, no push.**

### Explicitly out of this slice
M2 cue state, M3 stitching/parent center, M4 speech, full extended web graph on Android, review STT JS split, Play/release signing transition, scheduler replacement.

---

**Bottom line:** Approve the plan once the P0 contract/migration/merge/digest/phone-restore corrections are written into the plan text; then implement only the core M0–M1 slice above.
