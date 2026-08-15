# Mobile Milestone 0 implementation receipt

Date: 2026-07-15  
Branch: `codex/memcoach-mobile-coach-v1`  
Baseline: `de3d3ca6774e09655177cdb131fb21bd5f94967f`

## Scope and safety

Implemented only Milestone 0 from
`MOBILE_FEATURE_BUILD_AND_PHONE_DEPLOY_PLAN.md`. Web production schema remains
version 9 and Room remains version 1. No physical Android device was connected,
and no install, uninstall, data clear, signing transition, remote change, commit,
or push was performed.

## Before-change baseline

- `make check PYTHON=.venv/bin/python`: passed, including 27 Python tests.
- `make android-debug`: passed, including core/app unit tests and debug APK.
- `git diff --check`: passed.

## Implemented

- Replaced web stamp-on-mismatch startup behavior with explicit transaction-per-
  step schema migrations from 1 through 9, atomic empty-database bootstrap, and
  fail-closed handling for newer or ambiguous unstamped databases.
- Added version-1 and sanitized real version-9 web fixtures covering counts,
  indexes, foreign keys, application queries, FTS, progress backfill, rollback,
  and orphaned-history failure behavior.
- Enabled Room schema export without bumping its version, committed schema v1,
  and added a populated production-shape `MigrationTestHelper` fixture/test.
- Added shared grading/SM-2 rules and fixtures consumed by Python and Kotlin,
  including normalized-indel behavior, locale-invariant case handling, half-even
  interval rounding, and invalid-input clamping parity.
- Added the core-only portable v1 JSON Schema, readable golden package, exact
  canonical payload/digest fixture, and required invalid-case mutations.
- Made Android instrumentation compilation part of `make android-debug` and
  required an explicit `ANDROID_SERIAL` for instrumentation and sideload targets.

## Final gates

- `make check PYTHON=.venv/bin/python`: passed, 40/40 tests plus Ruff, compile,
  and app-import smoke.
- `make android-debug`: passed, including both shared core suites, app unit tests,
  debug APK, and instrumentation-test APK.
- `make android-migration-test ANDROID_SERIAL=emulator-5580`: passed 1/1 on a
  freshly wiped dedicated Android 16/API-36 emulator; the emulator was stopped.
- Contract JSON parsing, canonical SHA-256 verification, secret-omission checks,
  and `git diff --check`: passed.
- AGY initial review found one P1 and three lower-severity gaps. The locale and
  parity/assertion gaps were fixed; orphaned legacy history was kept fail-closed
  rather than silently filtered. Follow-up verdict: `GO`, zero unresolved P0/P1.

Review artifacts:

- `reviews/agy/memcoach-milestone0-review-20260715.md`
- `reviews/agy/memcoach-milestone0-followup-20260715.md`

## Next slice

Core-only Milestone 1: web 9 to 10 and Room 1 to 2 portable identities and
timestamps, followed by typed package parsing/canonicalization, preview, and
transactional merge/copy. Phone preservation and sideload gates remain deferred
until Milestone 1 is complete and reviewed.
