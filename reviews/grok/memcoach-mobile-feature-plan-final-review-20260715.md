I'll review the corrected plan against the codebase and prior review context, focusing only on P0/P1 defects in the areas you listed.Checking schema details and edge cases that prior findings may still leave open.Checking a few more contract edges that could still cause silent data reinterpretation.# Corrected-plan re-review (P0/P1 only)

Scope checked against live baseline `de3d3ca`: web schema 9 with soft-delete + `card_progress`, Room v1 (`memcoach-offline.db`, no migrations, `exportSchema = false`), unique kid/deck names on both sides. Prior P0s on migrator shape, core-vs-extended, digest/canonical basics, Room export, secret tar labeling, and phone serial/cert gates look incorporated.

---

## Findings

### P0 — fix in plan text before implementation

**1. Soft-deleted web rows can be reinterpreted as live on Android**  
Web kids/decks/cards use `deleted_at`; Android has no tombstones. The plan defers soft-delete portability but never defines export selection. A whole-library export that includes soft-deleted rows will surface them as active content on Android (silent reinterpretation), violating the non-negotiable “never … reinterpret data” rule.

**Minimal edit** — add under First-format scope / Exact JSON:

- Core export includes only rows with `deleted_at IS NULL` for kids, decks, and cards.
- Progress and reviews are included only when both referenced kid and card are in that active export set.
- Soft-delete/tombstone portability remains out of v1 (raw SQLite backup remains full DR).

**2. `updated_at` is specified for merge but not for migration backfill or write paths**  
Merge says “newer `updated_at` wins” for kid/deck/card content, but the plan never requires:

- non-null backfill on web 9→10 / Room 1→2, or  
- bumping `updated_at` on every successful content create/edit.

Without both, post-migration values are equal/stale and remote content updates never win—merge is effectively “always keep local.”

**Minimal edit** — add under Identity and schema changes:

- Migration backfill: `updated_at` = existing `created_at` when present, else UTC timestamp of migration (same rule both runtimes).
- All kid/deck/card content create/update paths set `updated_at` to now (UTC) in the same transaction as the content write.
- `updated_at` is not derived from review activity; reviews do not bump content `updated_at`.

---

### P1 — fix in plan / first-slice contract bounds

**3. Card-progress merge key is wrong if taken literally**  
Progress is naturally one row per `(kid, card)`. Matching only on progress `portable_id` breaks when two installs share kid/card UUIDs but minted different progress UUIDs (independent backfill), and collides with PK `(kid_id, card_id)`.

**Minimal edit** — replace the progress row in the merge matrix with:

| Data | Match key | Rule |
| --- | --- | --- |
| Card progress | `(kid.portable_id, card.portable_id)` | Newer `last_review` wins entire row; winner’s progress `portable_id` is kept; null/absent `last_review` loses to any non-null; both null → keep local and warn |

Progress `portable_id` remains required unique identity in the package; it is not the merge match key.

**4. Core field inventory is still implicit**  
Without an allow-list, implementers may emit web-only fields (`mastery_status`, `text_id`, `chunk_index`, `review_mode`, extended review grading columns). Android cannot store them; `org.json` ignore = silent drop unless schema rejects.

**Minimal edit** — add an explicit core field allow-list (names only, no new features), e.g.:

- kid: `portable_id`, `name`, `updated_at`
- deck: `portable_id`, `name`, `updated_at`
- card: `portable_id`, `deck_portable_id`, `prompt`, `full_text`, `updated_at`
- progress: `portable_id`, `kid_portable_id`, `card_portable_id`, `interval_days`, `due_date`, `ease_factor`, `streak`, `last_review`
- review: `portable_id`, `card_portable_id`, `kid_portable_id`, `grade`, `user_text`/`answer`, `duration_seconds`, `ts`

And: JSON Schema for core objects uses `additionalProperties: false`. Card-level SM-2 columns on Android/web card rows are not portable merge authority; scheduling enters only via progress (Android may seed card-level COALESCE fallbacks from imported progress or defaults).

**5. Canonical export is under-specified for golden byte stability**  
Key sort + NFC + ease-as-fixed-string are present; export array order and integrity shape are not. Two correct exporters can still disagree byte-for-byte.

**Minimal edit** — under Exact JSON:

- Export arrays sorted by `portable_id` ascending (kids, decks, cards, progress, reviews).
- Timestamps: UTC RFC3339 with second precision and `Z` suffix, no fractional seconds (e.g. `2026-07-15T12:34:56Z`).
- `integrity`: `{ "alg": "sha256", "sha256": "<lowercase hex>" }` over canonical bytes of the document with the top-level `integrity` member removed.

**6. ADB secret-tar restore is outlined, not operationally safe**  
Force-stop + `run-as` tar is good. Restore rehearsal still risks live A17 overwrite, and Room’s `memcoach-offline.db` may ship with `-wal`/`-shm`.

**Minimal edit** — replace the restore paragraph with:

- After archive: require `tar -tf` to list `databases/memcoach-offline.db` and any `-wal`/`-shm`; refuse if DB member missing.
- Host-side count check from extracted `databases/` (open SQLite with WAL side files present) before any device restore.
- Restore rehearsal only on emulator or a disposable debug install—not an in-place overwrite of `R5GL50EEHML` production data unless the user explicitly orders recovery.
- Restore sequence: force-stop → `adb -s … exec-out run-as …` is insufficient alone; restore via `run-as` extract of the full `databases/` and `shared_prefs/` trees (UID-preserving) → launch → verify pre-recorded counts.
- Never restore only the main `.db` file when `-wal` was present in the tar.

**7. Name-collision policy vs “receive web data” on a non-empty phone**  
Hard-fail on same unique name / different UUID is fine and covers UNIQUE constraints. Combined with deferred `replace` and copy that does not rename, live merge/copy of a family web library onto a phone that already has the same kid/deck names will not succeed.

**Minimal edit** — under Merge and copy rules / Debug-phone checkpoint:

- Name-collision hard-fail applies to preview for both `merge` and `copy`.
- M1 phone acceptance does **not** require live import of a colliding web package onto the production A17 library; required paths are empty/disposable import, plus export → host validate → disposable restore.
- Live same-name receive waits on deferred `replace` or a later rename policy (do not invent rename now).

**8. Android merge failure rollback is test-mentioned, not behavioral**  
Snapshots before merge are required; auto-restore on failure is only implied by tests.

**Minimal edit** — under Android work:

- On any merge/copy failure after snapshot, automatically restore the newest good snapshot before surfacing the error; leave DB unchanged from the pre-merge view.

---

## Areas that look solid (no remaining P0/P1)

| Area | Status |
| --- | --- |
| Web monotonic `n→n+1` migrator + reject newer DB | OK |
| Room `exportSchema`, no destructive fallback, wire `MIGRATION_1_2` before sideload | OK |
| Portable IDs on kids/decks/cards/reviews/progress; no recompute from names/ids | OK |
| Core-only package; Android fails on `extensions` (no silent drop) | OK |
| Reviews insert-if-absent; never rewrite history | OK |
| Digest = canonical bytes with `integrity` removed; ease as fixed decimal strings | OK |
| FTS rebuild inside web import transaction | OK |
| Serial-locked ADB; cert re-check; no Makefile `android-install-usb`; no uninstall/`pm clear` | OK |
| Secret tar labeled local DR, not portable | OK |
| First slice bounds: M0 + core M1 only; M2+/speech/release-sign out | OK |
| Defer `replace` until snapshot/disk-full UI proven | OK |

---

## Verdict: **GO WITH CHANGES**

Previous blocking gaps are largely closed. Remaining blockers are narrow contract holes that still allow silent reinterpretation (soft-delete export) or a non-functional merge clock (`updated_at`), plus a few merge/canonical/ADB precision fixes.

### Exact patch list (apply to `docs/MOBILE_FEATURE_BUILD_AND_PHONE_DEPLOY_PLAN.md`)

1. **Export selection (P0):** active-only kids/decks/cards; progress/reviews only for exported entities.  
2. **`updated_at` lifecycle (P0):** migration backfill + bump on every content create/update.  
3. **Progress merge key (P1):** match `(kid, card)` portable pair; LWW by `last_review` with null rules; keep winner progress `portable_id`.  
4. **Core allow-list + `additionalProperties: false` (P1):** fields above; no card-level schedule as merge authority.  
5. **Canonical freeze (P1):** array sort by `portable_id`; timestamp form; `integrity` object shape.  
6. **ADB restore (P1):** WAL membership checks; host counts; emulator/disposable-only rehearsal; full tree restore.  
7. **Collision scope (P1):** hard-fail for merge and copy; M1 phone gate does not require live colliding web import.  
8. **Merge failure (P1):** auto-restore newest snapshot before error return.

After those eight edits land in the plan text, implementation of M0 + core M1 can start without further plan review from this pass.
