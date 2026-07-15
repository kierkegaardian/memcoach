# TODO: Android Native Offline Plan (MemCoach)

## Product Decision

- [x] Android must be fully offline from initial release.
- [x] The current `android-wrapper/` WebView app is not the target architecture.
- [x] Native Android is the primary mobile path; PWA/TWA are optional secondary paths.

## Open-Source Dependency Policy

- [x] Runtime app dependencies should be open-source libraries/frameworks.
- [x] No required cloud SDK/service dependency in the core review path.
- [x] Keep a dependency inventory in `android-native/README.md` as modules are added.

## Parity Decisions (Current)

- [x] Keep SM-2 and grading logic aligned with current Python behavior during migration.
- [ ] Decide whether to adjust grading normalization and early-interval progression after
  migration parity fixtures are in place.

## Success Criteria (Release 1)

- [ ] App works end-to-end in airplane mode:
  - create/edit students
  - create/edit decks/cards
  - run review session with SM-2 scheduling
  - view baseline stats
- [x] No Termux, local web server, or network tunnel required.
- [x] Data persists locally through Room; device restart remains in the manual QA matrix.
- [ ] Backup/export and restore/import supported locally.
- [x] Core grading is deterministic and local-only (Levenshtein + rule-based thresholds).

## Architecture Baseline

- [x] Project scaffold:
  - `android-native/` Android Studio project
  - Kotlin + Jetpack Compose + Room + ViewModel + Coroutines
  - minSdk 26, target latest stable SDK
- [ ] Module boundaries:
  - `app`: UI, navigation, dependency wiring
  - `core-scheduling`: SM-2 logic
  - `core-grading`: local grading logic
  - `data-local`: Room entities, DAO, migrations
  - `feature-*`: deck management, review, stats, settings
- [ ] Test baseline:
  - unit tests for scheduling/grading/domain mapping
  - instrumentation tests for critical offline flows

Acceptance:
- `./gradlew test` and `./gradlew connectedAndroidTest` run for baseline modules.
- Fresh install opens to working local app state without network calls.

## Phase 0: Bootstrap and Contracts (1-2 days)

- [x] Create native Android scaffold in `android-native/`.
- [x] Add CI/build commands to README (or native module README).
- [ ] Define shared product contracts for parity with Python app:
  - grade enum values
  - SM-2 fields and update rules
  - card/deck/student/review model constraints
- [ ] Add fixture format for parity tests (`android-native/test-fixtures/*.json`).

Acceptance:
- Project builds and launches on emulator/device.
- Contract doc exists and is referenced from this TODO.

## Phase 1: Domain Engine Parity (2-3 days)

- [x] Port SM-2 from `utils/sm2.py` to Kotlin with strict unit tests.
- [x] Port local grading policy from `utils/grading.py`:
  - keep deterministic local behavior
  - no optimistic fallback on failure
- [ ] Create golden tests against Python-generated fixtures for parity.
- [x] Ensure all domain models are fully typed (no loosely typed maps for core logic).

Acceptance:
- SM-2 and grading unit tests pass with parity fixtures.
- No dependency on Ollama or backend API for grading/scheduling.

## Phase 2: Local Data Layer (2-3 days)

- [x] Implement Room schema for:
  - students
  - decks
  - cards (including scheduling fields)
  - reviews
  - optional tags/assignments (if needed for parity)
- [x] Build DAO queries for:
  - due cards by deck/student
  - review log writes
  - basic stats aggregation
- [ ] Add migration strategy and seed data path.
- [x] Add repository interfaces around DAOs for testable domain/use-case logic.

Acceptance:
- Create/edit/delete and review writes persist locally.
- Due-card fetch and schedule updates function without race/crash issues.

## Phase 3: Core Offline UX (4-6 days)

- [x] Compose navigation and screen set:
  - home (students/decks)
  - deck detail + card list
  - card editor (import deferred)
  - review session
  - basic stats
  - settings/backup
- [x] Implement review flow parity:
  - prompt display
  - answer input (typed first)
  - grade result
  - schedule update + next card
- [x] Parent guardrails:
  - local PIN gate for parent-only actions
  - lock/unlock flows

Acceptance:
- Full session works in airplane mode from launch through multiple card reviews.
- Parent-only actions are gated by PIN and tested.

## Phase 4: Import/Export and Migration Bridge (2-3 days)

- [ ] Define `memcoach-backup-v1.json` format for portable backups.
- [ ] Implement export/import in native app.
- [ ] Add bridge script in Python app for one-time migration to JSON backup format.
- [ ] Validate conflict behavior on import (replace/merge modes).

Acceptance:
- Existing MemCoach data can be exported from Python app and imported into Android app.
- Backup/restore works locally with clear user feedback on failures.

## Phase 5: Offline Audio/STT (Optional for R1, Required for R2) (3-5 days)

- [ ] Decide offline STT engine:
  - preferred: embedded offline model (for deterministic offline behavior)
  - fallback: typed-only if model size/perf blocks R1
- [ ] Integrate microphone capture with explicit runtime permission handling.
- [ ] Add feature flag so release can ship typed-only if STT quality is not ready.

Acceptance:
- If STT enabled: recitation works offline with no network dependency.
- If STT deferred: typed flow remains complete and stable for R1.

## Phase 6: Hardening, QA, and Release (2-3 days)

- [ ] Add offline test matrix:
  - airplane mode manual checklist
  - low-storage behavior
  - app kill/restart during review
  - backup restore failure handling
- [ ] Performance sanity checks:
  - review submission latency target
  - cold start target
- [ ] Release prep:
  - signing config
  - versioning policy
  - release checklist

Acceptance:
- Debug and release APKs install cleanly and pass offline checklist.
- No blocking P0/P1 findings in final review.

## Explicit Non-Goals (Release 1)

- [x] No required cloud sync.
- [x] No required remote hosting.
- [x] No dependence on Ollama for grading.
- [x] No requirement for iOS parity in R1.

## Execution Order (Concrete)

1. Scaffold `android-native/` and establish module/test baseline.
2. Port SM-2 and grading logic with parity fixtures.
3. Implement Room data layer and repository interfaces.
4. Build typed review flow end-to-end in Compose.
5. Add parent PIN gating and baseline stats.
6. Add import/export plus Python-to-Android migration bridge.
7. Decide STT gate: include offline STT if stable, otherwise ship typed-only R1.
8. Run offline QA matrix and prepare release build/signing.

## First Slice to Implement Next

- [x] Create `android-native/` project scaffold.
- [x] Implement `core-scheduling` SM-2 port + tests.
- [x] Implement `core-grading` deterministic local grading + tests.
- [x] Wire a temporary "review sandbox" screen with in-memory sample card data.

Acceptance:
- We can demonstrate a full review-cycle state transition locally on device/emulator
  without network and without backend.
