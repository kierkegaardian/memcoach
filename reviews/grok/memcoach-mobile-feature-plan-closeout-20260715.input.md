# MemCoach Mobile Feature Build and Phone Deployment Plan

Status: reviewed and corrected  
Prepared: 2026-07-15  
Baseline: clean `main` at `de3d3ca`, equal to `origin/main`  
Independent review: Grok 4.5, `GO WITH CHANGES`

## New-chat kickoff

Use this prompt in a fresh Codex chat:

> Work in `/home/user/projects/memcoach`. Read `AGENTS.md` and
> `docs/MOBILE_FEATURE_BUILD_AND_PHONE_DEPLOY_PLAN.md`. Implement only Milestone 0
> and the core-only Milestone 1, with every gate in this plan. Do not implement
> adaptive cues yet. Preserve the installed `com.memcoach.offline` data: do not
> uninstall, clear data, change signing identity, or push without my approval.
> Before sideloading, re-check certificates, make and verify the documented
> secret-bearing `run-as` snapshot, and rehearse its restore against a disposable
> database. Stop on any migration, count, signing, storage, or device failure.

## Outcome and delivery order

Build a trustworthy offline Android app that receives existing web data, then
coaches a child from supported practice to unaided passage recall.

1. Milestone 0: preservation, real migration systems, and shared contracts.
2. Milestone 1: core portable library package and debug-phone checkpoint.
3. Milestone 2: adaptive cue ladder and second debug-phone checkpoint.
4. Milestone 3: passage stitching and parent action center.
5. Milestone 4: optional offline oral review after a target-device spike.

## Verified baseline

- Web: FastAPI/Jinja/HTMX, SQLite schema 9, raw backup/restore, per-kid progress,
  long-text chunks, hints, planning, and weekly reports.
- Android: Kotlin/Compose/Room v1, typed review, local grading, SM-2, basic stats,
  parent PIN, and child mode; Room schemas are not currently exported.
- Android is a strict subset of the web model; v1 portability must not pretend to
  support tags, texts, plans, mastery rules, assignments, or extended grading data.
- Device: Galaxy A17 `R5GL50EEHML`, Android 16; installed debuggable package
  `com.memcoach.offline` is `0.3.0`/3 and permits `run-as`.
- Installed/current debug certificate SHA-256:
  `7b40dac4a2f64743227610420186ed0a61f0e584d982fdfb4f9a75231ad67ea3`.
- Ignored release environment file exists at mode `0600`; never print or commit it.

## Non-negotiable constraints

- Core create/import/review/stats works in airplane mode.
- Imports and migrations never silently discard, overwrite, or reinterpret data.
- Portable exports omit PIN material, config, session/signing data, Bible corpora,
  and other machine-specific state.
- No destructive migration fallback; every version change has a tested migration.
- Python/Kotlin contracts are typed and share byte-level golden fixtures.
- New/heavily modified source files stay at or below 300 lines where practical.
- A new runtime dependency requires approval before coding against it.
- No uninstall, release-key transition, remote change, or push in Milestones 0-1.

## Milestone 0 - preservation, migrations, and contracts

### Repository baseline

- [ ] Create `codex/memcoach-mobile-coach-v1` from `de3d3ca`.
- [ ] Record `make check PYTHON=.venv/bin/python`, `make android-debug`, and
  `git diff --check` before changing behavior.
- [ ] Keep portability in new focused Python/Kotlin packages; do not grow the
  oversized card/review routes or extract unrelated STT JavaScript in this slice.
- [ ] Type-check new portability code and touched scheduling/progress boundaries.

### Web migration system

- [ ] Replace stamp-on-mismatch behavior with monotonic functions such as
  `migrate_9_to_10(conn)`; run step `n→n+1` only from `user_version == n`.
- [ ] Set `PRAGMA user_version` only after that step succeeds in its transaction.
- [ ] Reject databases newer than the application instead of rewriting the stamp.
- [ ] Require a migration function and fixture test for every future schema bump.
- [ ] Capture a sanitized real schema-9 fixture and verify pre/post row counts,
  indexes, foreign keys, and application queries—not merely successful startup.

### Room migration baseline

- [ ] Set `exportSchema = true`, configure the schema directory, and commit v1 JSON.
- [ ] Add `MigrationTestHelper` and a populated v1 fixture matching production.
- [ ] Prove the v1 fixture opens and preserves all entity/progress counts.
- [ ] Never add `fallbackToDestructiveMigration`.

### Shared contract area

- [ ] Add `contracts/` with deterministic grade enum/threshold rules, SM-2 fixtures,
  `memcoach-backup-v1.schema.json`, canonical byte fixtures, and invalid examples.
- [ ] Limit grading parity to deterministic thresholds/SM-2; Ollama remains a
  documented web-only borderline option.
- [ ] Use Android platform `org.json` plus typed DTO construction for this bounded
  core format unless the user approves a serialization dependency first.

### Milestone 0 gate

- [ ] Existing Python/Android checks remain green.
- [ ] Python and Kotlin pass identical deterministic grading/SM-2 fixtures.
- [ ] Real web-9 and Room-v1 fixtures open without loss.
- [ ] No production schema version has changed yet.

## Milestone 1 - core portable library package

### First-format scope

Ship whole-library scope only. The required core graph is:

- kids, decks, cards;
- per-kid card progress;
- reviews with grade, answer, duration, and timestamp;
- references among those entities using portable UUIDs.

Web-only extended sections are not accepted by Android v1. If an `extensions`
object is present, Android fails preview with an unsupported-section message; it
must never silently drop and re-export incomplete data. Deck-only packages,
assignments, tags, texts/chunks, plans, mastery rules, soft deletion, and extended
review metadata are fast-follow format work.

Core export selects only web kids/decks/cards with `deleted_at IS NULL`; it includes
progress/reviews only when both referenced kid and card are in that active set.
Tombstones remain out of v1; raw SQLite backup remains the complete web DR path.

### Identity and schema changes

- [ ] Web 9→10: add unique, non-null `portable_id` to kids/decks/cards/reviews and
  card-progress rows; add `updated_at` to mutable core content and installation
  metadata used only as export provenance.
- [ ] Room 1→2: add equivalent portable IDs/updated timestamps with unique indexes.
- [ ] Backfill random UUIDs once and store them; never recompute them from names,
  installation IDs, or local row IDs.
- [ ] Backfill non-null `updated_at` from existing `created_at`, else migration UTC;
  every content create/edit bumps it in the same transaction. Reviews never bump it.
- [ ] Junction edges need no UUID: they refer to parent portable IDs in packages.
- [ ] Wire `MIGRATION_1_2` through `.addMigrations(...)` before any sideload.

### Exact JSON and integrity contract

- [ ] File name: `memcoach-backup-v1.json`; UTF-8 only; MIME `application/json`.
- [ ] Top fields: `format: memcoach.portable`, `version: 1`, UTC export timestamp,
  source app/version/installation provenance, `scope: library`, core graph, integrity.
- [ ] Core allow-list: kid `(portable_id,name,updated_at)`; deck
  `(portable_id,name,updated_at)`; card `(portable_id,deck_portable_id,prompt,
  full_text,updated_at)`; progress `(portable_id,kid_portable_id,card_portable_id,
  interval_days,due_date,ease_factor,streak,last_review)`; review
  `(portable_id,card_portable_id,kid_portable_id,grade,user_text,duration_seconds,ts)`.
- [ ] Set core-object JSON Schema `additionalProperties: false`; card-level schedule
  fields are not merge authority—only progress rows carry portable scheduling state.
- [ ] Digest input is the document with the top-level `integrity` member removed.
- [ ] Canonical bytes use sorted object keys, compact separators, preserved array
  order, UTF-8/NFC strings, lowercase UUIDs, UTC RFC3339 timestamps, integer counts,
  and ease factors encoded as fixed six-decimal strings—not binary JSON floats.
- [ ] Sort every entity array by portable ID; timestamps use second precision and
  `Z`; integrity is `{ "alg": "sha256", "sha256": "<lowercase hex>" }`.
- [ ] SHA-256 covers those exact bytes. Python and Kotlin must reproduce byte-for-
  byte golden files before import/export UI work begins.
- [ ] Reject unknown versions, invalid UTF-8, bad digest/enums/UUIDs, duplicate IDs,
  dangling references, excessive nesting, and files over the configured limit.

### Merge and copy rules

| Data | Match key | Rule |
| --- | --- | --- |
| Kid/deck/card | Entity UUID | Newer `updated_at` wins; tie keeps local and warns. |
| Progress | Kid UUID + card UUID | Newer non-null `last_review` wins entire row and its progress UUID; both null keeps local/warns. |
| Reviews | Review UUID | Insert only if absent; never rewrite history. |
| Unique name | Different UUID | Hard-fail merge/copy preview with collision counts. |

- [ ] `preview` validates and reports creates/updates/skips/collisions without writes.
- [ ] `merge` applies the matrix in one transaction and is idempotent.
- [ ] `copy` rewrites the UUID graph and imports content only—no progress/reviews.
- [ ] Defer `replace` until app-private snapshot/restore UI and disk-full handling are
  fully tested; it is not required for the first phone checkpoint.

### Web work

- [ ] Add typed models, parsing, canonicalization, export, preview, and transactional
  import under `portable/`; keep raw SQLite backup as disaster recovery.
- [ ] Add parent-only export, import-preview, and confirmed merge/copy routes/UI.
- [ ] Preserve existing upload bounds and add structure/count limits before writes.
- [ ] Rebuild `cards_fts` within the import transaction; failure rolls back import.
- [ ] Test migration, round trip, idempotency, collisions, rollback, secret omission,
  invalid/large inputs, and web-only extension rejection.

### Android work

- [ ] Add typed DTO/mapping code separate from Room entities.
- [ ] Use Storage Access Framework `CreateDocument`/`OpenDocument`; perform all I/O,
  digesting, parsing, and database work off the main thread.
- [ ] Parent-gate Settings actions for export, preview, merge, and copy.
- [ ] Before merge, close Room, checkpoint WAL, copy DB/WAL state into app-private
  storage, reopen, and retain two snapshots; fail safely on insufficient space.
- [ ] On merge/copy failure after snapshot, automatically restore the newest good
  snapshot before returning the error.
- [ ] Test Room 1→2, parser, preview, merge/copy, snapshot rollback, process restart,
  unsupported extensions, and large/invalid files.

### Cross-runtime and review gate

- [ ] Python golden export imports in Kotlin; Kotlin golden export imports in Python.
- [ ] Canonical bytes/digests match; merge is idempotent; copy omits history; secrets
  are absent; failures leave the original DB unchanged.
- [ ] Fresh emulator imports a sanitized web package and reviews a due card.
- [ ] Add at least one instrumentation or scripted ADB migration smoke.
- [ ] No unresolved P0/P1 data-loss, migration, or import findings.

## Debug-phone checkpoint - Galaxy A17

### Preflight and secret-bearing snapshot

- [ ] Require serial `R5GL50EEHML` on every ADB command; do not use the Makefile's
  non-serial `android-install-usb` target.
- [ ] Verify device authorization, free space, installed version, and current/candidate
  signing certificates with `apksigner verify --print-certs`; stop on mismatch.
- [ ] Record pre-install counts for kids/decks/cards/progress/reviews.
- [ ] Force-stop the app and archive private state:

```bash
stamp=$(date +%Y%m%dT%H%M%S%z)
dir=/home/user/.local/state/memcoach/phone-backups/$stamp
mkdir -p "$dir" && chmod 700 "$dir"
adb -s R5GL50EEHML shell am force-stop com.memcoach.offline
adb -s R5GL50EEHML exec-out run-as com.memcoach.offline \
  tar -C . -cf - databases shared_prefs > "$dir/app-state.tar"
chmod 600 "$dir/app-state.tar"
tar -tf "$dir/app-state.tar"
sha256sum "$dir/app-state.tar" > "$dir/SHA256SUMS"
```

This tar contains PIN-derived private state. It is local disaster recovery, not a
portable export. Require the archive to contain `databases/memcoach-offline.db` and
retain any `-wal`/`-shm`; refuse an incomplete archive. Extract on the host with WAL
sidecars and verify counts. Rehearse only on an emulator/disposable debug install:
force-stop, extract the full `databases/` and `shared_prefs/` trees through `run-as`
(app UID), launch, and compare counts. Never restore only the main DB when WAL exists,
or overwrite the A17 in a rehearsal without explicit recovery authorization.

### Build, sideload, and acceptance

- [ ] Bump to version code 4/name `0.4.0-portable.1`.
- [ ] Run `make check PYTHON=.venv/bin/python`, `make android-debug`, migration tests,
  instrumentation/scripted smoke, and `git diff --check` on the exact commit.
- [ ] Install only with
  `adb -s R5GL50EEHML install -r android-native/app/build/outputs/apk/debug/app-debug.apk`.
- [ ] Verify post-install version/certificate and that no entity count dropped.
- [ ] Launch, open a due card, export/host-validate a package, preview it, restore it
  into a disposable DB, and complete airplane-mode create/import/review/stats.
- [ ] Production-phone M1 does not require importing a same-name colliding web
  library; that waits for `replace` or a later explicit rename policy.
- [ ] Force-stop/relaunch; verify persistence and parent-gated import/export.
- [ ] Stop on count drop, migration exception, cert mismatch, or restore failure.
- [ ] Never use uninstall, `pm clear`, downgrade flags, release signing, or push here.

## Milestone 2 - adaptive passage coach

- [ ] Add per-kid/card states `study → guided → initials → recall` with pure,
  fixture-shared Python/Kotlin transitions.
- [ ] Map each state to explicit display functions in both runtimes; move relevant
  review JS only when this UI changes.
- [ ] Two perfect attempts on separate kid-local calendar dates reduce help; good
  holds; fail increases help; stronger manual hint prevents advancement.
- [ ] Clamp study/recall boundaries and keep cue transitions separate from SM-2.
- [ ] Add web 10→11 and Room 2→3 migrations plus parity/rollback tests.
- [ ] Explain the selected cue, preserve parent override, log actual cue, allow a
  parent cap/disable control, and repeat the debug-phone checkpoint.

## Milestones 3-4 - later product work

- [ ] Passage stitching: add Android text/chunk support, then virtual ordered
  `1`, `2`, `1+2`, `3`, `1+2+3`, full-passage attempts without hidden duplicate cards.
- [ ] Parent action center: per-kid slipping cards, missed tokens, cue level, overdue
  load, recommendation rationale, and one-click targeted sessions.
- [ ] Correct weekly reports to be per-kid and properly time-bounded.
- [ ] Oral spike: benchmark a Vosk-class open-source engine on Galaxy A17 and Boox
  for accuracy, latency, memory, size, and battery before requesting dependency use.
- [ ] If accepted, request microphone at use, retain no audio by default, show/grade
  transcript with parent override, and keep typed review complete offline.

## Release-signing transition - later gate

The installed app is debug-signed. A release APK cannot replace it in place.

1. Prove portable export, host validation, and disposable restore.
2. Keep the last verified secret-bearing tar while debug `run-as` remains available.
3. Build/verify signed APK/AAB after sourcing the ignored env file without output.
4. Only then approve debug uninstall, release/Play install, portable import, and the
   full airplane/child-mode checklist. After transition, portable export is the
   only normal non-root recovery path.

## Review and definition of done

- Grok 4.5 findings: `reviews/grok/memcoach-mobile-feature-plan-review-20260715.md`
  and `reviews/grok/memcoach-mobile-feature-plan-final-review-20260715.md`;
  closeout: `reviews/grok/memcoach-mobile-feature-plan-closeout-20260715.md`.
- Final verdict: `GO`; no P0/P1 remains. M2+, release signing, extended format,
  and speech remain outside the first slice.
- First debug checkpoint is done only when core round trip, rollback, live Room
  migration, pre/post counts, tar-restore rehearsal, airplane mode, child-mode gate,
  exact deployed commit/tests/hashes, and zero unresolved P0/P1 findings are recorded.
