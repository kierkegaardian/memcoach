I will start by listing the contents of the `/home/user/projects/memcoach` directory to see all the files and folders, especially the untracked ones mentioned in the stdin diff and files list.
I will list the files in the `db/` directory to see what implementation files are present.
I will list the files in the `tests/` directory to see all test files.
I will list the files in the `tests/fixtures/` directory to see what fixture files exist.
I will list the files in the `contracts/` directory to see the shared contracts.
I will list the files in the `docs/` directory to see the documentation.
I will list the schemas directory in the Android native app module.
I will list files inside the database schema folder.
I will list files inside the android-native/app/src/androidTest directory.
I will list the directories and files under android-native/app/src/androidTest/java to locate the instrumentation tests.
I will list the files under `android-native/app/src/androidTest/java/com/memcoach/offline/data/local/` to find Room migration test classes.
I will view the `db/migrations.py` file to inspect the migration system implementation.
I will view the relevant parts of `db/database.py` to understand the connection management and how transaction boundaries are handled.
I will view `tests/test_migrations.py` to understand how the migrations are tested.
I will view the `tests/test_shared_contracts.py` file to inspect how the parity contracts (normalized-indel, SM-2, JSON schemas) are verified.
I will view `contracts/deterministic-rules-v1.json` to verify the deterministic grading rules.
I will view `contracts/memcoach-backup-v1.schema.json` to verify the schema properties and constraints.
I will view `RoomV1MigrationTest.kt` to inspect the instrumentation tests that verify Room database startup and migration fixture counts.
I will list the files in the Android androidTest assets directory to verify the presence of the room v1 fixture.
I will list the files under `android-native/app/src/androidTest/assets/fixtures/` to verify the exact name.
I will view `SharedGradingContractTest.kt` to inspect the grading logic parity tests on the Kotlin side.
I will view `RecallGrader.kt` to inspect the grading logic and check if it has `levenshteinRatio` or a different method.
I will view the `SharedSm2ContractTest.kt` file to inspect how the SM-2 algorithm implementation is verified.
I will search for the definition of `Sm2Engine` to inspect its implementation.
I will view `Sm2Engine.kt` to inspect the scheduling logic details.
I will view `utils/sm2.py` to compare its implementation of SM-2 with `Sm2Engine.kt`.
I will view the `db/schema.py` file to inspect the database schema definitions and current version.
I will view the SQL statements in the schema version 1 fixture to ensure they align with the starting point for version 1 database migrations.
I will view `utils/progress.py` to inspect the helper functions used during the version 8 to 9 migration.
I will view `utils/mastery.py` to check the mastery rules retrieval function used during the migration.
I will run the command `make check` to verify that all existing Python and Android tests currently pass on the workspace.
I will search for occurrences of `position` in Python files to see if cards are initialized with a non-zero position or if position is updated elsewhere.
I will view the `Makefile` to inspect for safety issues, especially concerning the `ANDROID_SERIAL` environment variable.
I will view the Room v1 populated fixture SQL file to check its content.
I will view `MemCoachDatabase.kt` to check the entities and verify the version.
I will view the exported Room schema version 1 file to inspect the database structure defined by Room.
I will view `contracts/invalid/invalid-cases-v1.json` to inspect the defined validation failure cases.
I will view `requirements.txt` to see what dependencies are installed.
I will view `contracts/valid/memcoach-backup-v1.json` to verify the golden JSON structure against the schema definitions.
I will view `contracts/README.md` to verify the specifications of the shared contract interface.
I will list the files in the `reviews/grok/` directory to see if there are any existing review files.
I will view `contracts/fixtures/sm2-v1.tsv` to see the scheduling test cases that are shared between Python and Kotlin.
I will view the grading test cases in `contracts/fixtures/deterministic-grading-v1.tsv` to check for adequacy.
I will search for occurrences of `.lowercase` in the Kotlin files to check for potential locale-specific bugs.
## Milestone 0 Code Review Report

Below is the strict read-only review of MemCoach Milestone 0 implementation.

---

### Findings by Severity (P0 - P3)

#### P1 Findings (High / Major Logic Parity or Migration Risks)
*   **Locale-Dependent Lowercasing in Kotlin (Turkish 'I' Defect)**
    *   **File References:**
        *   [RecallGrader.kt:L20-21](file:///home/user/projects/memcoach/android-native/core-grading/src/main/kotlin/com/memcoach/offline/grading/RecallGrader.kt#L20-L21)
        *   [Sm2Engine.kt:L17](file:///home/user/projects/memcoach/android-native/core-scheduling/src/main/kotlin/com/memcoach/offline/scheduling/Sm2Engine.kt#L17)
        *   [SharedGradingContractTest.kt:L13-14](file:///home/user/projects/memcoach/android-native/core-grading/src/test/kotlin/com/memcoach/offline/grading/SharedGradingContractTest.kt#L13-L14)
    *   **Details:** On the Kotlin side, `.lowercase()` is called on user/expected text and grade strings without specifying a locale (such as `Locale.ROOT`). On JVM/Android runtimes, this defaults to the device's default locale. On devices with locales like Turkish (`tr-TR`), this converts the uppercase letter `I` to the dotless `ı` instead of `i`. This breaks grading and scheduling behavior parity with Python (which uses standard Unicode/ASCII lowercasing) for any inputs containing capital `I`.
    *   **Remediation:** Replace `.lowercase()` with `.lowercase(java.util.Locale.ROOT)` in these instances to guarantee locale-invariant behavior.

#### P2 Findings (Medium / Migration & Schema Edge Cases)
*   **Dangling Foreign Keys in Legacy Reviews Fail Version 8→9 Migration**
    *   **File Reference:** [migrations.py:L178](file:///home/user/projects/memcoach/db/migrations.py#L178)
    *   **Details:** The `migrate_8_to_9(conn)` migration selects all distinct `(kid_id, card_id)` pairs from the `reviews` table and attempts to populate `card_progress` for them. If a legacy database contains orphaned reviews with a dangling `kid_id` or `card_id` (which can happen if foreign keys were turned off or bypassed during manual database operations), inserting these rows into the new `card_progress` table will succeed initially. However, the subsequent database validation step `violations = conn.execute("PRAGMA foreign_key_check").fetchall()` will catch the foreign-key constraint violation on `card_progress`, causing the entire migration step to raise a `SchemaMigrationError` and roll back.
    *   **Remediation:** Join with `kids` and `cards` in the query to ensure only valid non-orphaned pairs are migrated:
        ```python
        pairs = conn.execute(
            "SELECT DISTINCT r.kid_id, r.card_id FROM reviews r "
            "JOIN kids k ON k.id = r.kid_id "
            "JOIN cards c ON c.id = r.card_id"
        ).fetchall()
        ```

#### P3 Findings (Low / Enhancements, Parity Polish, & Test Completeness)
*   **Parameter Clamping Divergence for Invalid Input Values**
    *   **File References:**
        *   [Sm2Engine.kt:L32-33](file:///home/user/projects/memcoach/android-native/core-scheduling/src/main/kotlin/com/memcoach/offline/scheduling/Sm2Engine.kt#L32-L33)
        *   [sm2.py:L13-33](file:///home/user/projects/memcoach/utils/sm2.py#L13-L33)
    *   **Details:** In `Sm2Engine.kt`, the input parameters `cardIntervalDays` and `cardEaseFactor` are immediately clamped using `max(1, cardIntervalDays)` and `max(1.3, cardEaseFactor)` before multiplying them. In Python `utils/sm2.py`, they are not clamped before the multiplication, only the final `new_ef` is clamped. For a database where `interval_days` is somehow 0, Python will calculate `new_interval = max(1, round(0 * card_ef)) = 1`, whereas Kotlin will clamp `safeInterval = 1`, and for `quality >= 4`, it will set `nextInterval = 6`. Although the schema in M1 enforces `interval_days >= 1`, aligning the math prevents theoretical drift.
*   **Missing Schema Validation in Python Tests**
    *   **File Reference:** [test_shared_contracts.py:L88](file:///home/user/projects/memcoach/tests/test_shared_contracts.py#L88)
    *   **Details:** The contract test `test_portable_golden_core_graph_and_allow_lists` checks individual keys manually, but does not execute a schema validation library against `memcoach-backup-v1.schema.json` because `jsonschema` is not listed in `requirements.txt`.
*   **Incomplete Migration Assertions for Rebuilt `card_progress`**
    *   **File Reference:** [test_migrations.py:L69](file:///home/user/projects/memcoach/tests/test_migrations.py#L69)
    *   **Details:** `test_schema_one_fixture_migrates_to_nine_without_loss` verifies that the `card_progress` table is created and has a row count of `1`, but it does not assert that the computed progress values (`interval_days = 6`, `ease_factor = 2.5`, `streak = 1`, `mastery_status = 'learning'`) match expectations for the single review in the version 1 fixture.

---

### Review Verdict and Milestone 0 Gate Status

#### **NO-GO**

#### Unresolved P0/P1 Blockers:
1.  **Locale-Dependent Lowercasing in Kotlin (Turkish 'I' Defect):** Locale-independent string mapping is required to ensure behavioral parity on Android devices configured to locales with non-standard letter casing (such as Turkish). This is located in [RecallGrader.kt:L20-21](file:///home/user/projects/memcoach/android-native/core-grading/src/main/kotlin/com/memcoach/offline/grading/RecallGrader.kt#L20-L21), [Sm2Engine.kt:L17](file:///home/user/projects/memcoach/android-native/core-scheduling/src/main/kotlin/com/memcoach/offline/scheduling/Sm2Engine.kt#L17), and [SharedGradingContractTest.kt:L13-14](file:///home/user/projects/memcoach/android-native/core-grading/src/test/kotlin/com/memcoach/offline/grading/SharedGradingContractTest.kt#L13-L14).
