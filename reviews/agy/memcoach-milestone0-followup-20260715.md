## Milestone 0 Code Review Follow-Up Report

Here is the strict read-only follow-up review of the **MemCoach Milestone 0** implementation. All code bases (Python and Kotlin) were rechecked against the baseline and previous findings.

---

### Prior Findings Status & Verification Evidence

#### 1. [CLOSED] Locale-Dependent Lowercasing in Kotlin (Turkish 'I' Defect) (P1)
*   **Status**: **CLOSED** (Fully Resolved & Tested)
*   **Verification & Evidence**:
    *   In the recall grader, comparison inputs are normalized using `Locale.ROOT`:
        *   [RecallGrader.kt:L21-22](file:///home/user/projects/memcoach/android-native/core-grading/src/main/kotlin/com/memcoach/offline/grading/RecallGrader.kt#L21-L22):
            ```kotlin
            val userClean = userText.trim().lowercase(Locale.ROOT)
            val fullClean = fullText.trim().lowercase(Locale.ROOT)
            ```
    *   In the scheduling engine, grade string matching is mapped safely:
        *   [Sm2Engine.kt:L18](file:///home/user/projects/memcoach/android-native/core-scheduling/src/main/kotlin/com/memcoach/offline/scheduling/Sm2Engine.kt#L18):
            ```kotlin
            return when (grade.lowercase(Locale.ROOT)) {
            ```
    *   A dedicated Turkish default-locale regression test validates that case mapping behavior remains invariant, and the `"I"` / `"i"` case matches correctly as `perfect` even when `Locale.getDefault()` is set to Turkish (`tr-TR`):
        *   [SharedGradingContractTest.kt:L23-31](file:///home/user/projects/memcoach/android-native/core-grading/src/test/kotlin/com/memcoach/offline/grading/SharedGradingContractTest.kt#L23-L31):
            ```kotlin
            @Test
            fun turkishDefaultLocaleCannotChangeContract() {
                val original = Locale.getDefault()
                try {
                    Locale.setDefault(Locale.forLanguageTag("tr-TR"))
                    assertEquals("perfect", RecallGrader.gradeRecall("I", "i"))
                } finally {
                    Locale.setDefault(original)
                }
            }
            ```

#### 2. [CLOSED] Parameter Clamping Divergence for Invalid Input Values (P3)
*   **Status**: **CLOSED** (Fully Resolved)
*   **Verification & Evidence**:
    *   Python SM-2 implementation now mirrors Kotlin's parameter clamping by applying safe interval and ease factor bounds at the start of calculations:
        *   [sm2.py:L21-22](file:///home/user/projects/memcoach/utils/sm2.py#L21-L22):
            ```python
            safe_interval = max(1, card_interval)
            safe_ef = max(1.3, card_ef)
            ```
        *   Clamped parameters are consumed throughout the math (e.g., [sm2.py:L28-32](file:///home/user/projects/memcoach/utils/sm2.py#L28-L32)).

#### 3. [CLOSED] Incomplete Migration Assertions for Rebuilt `card_progress` (P3)
*   **Status**: **CLOSED** (Fully Resolved)
*   **Verification & Evidence**:
    *   The `test_schema_one_fixture_migrates_to_nine_without_loss` migration test now asserts every rebuilt progress field for correct default calculations:
        *   [test_migrations.py:L93-100](file:///home/user/projects/memcoach/tests/test_migrations.py#L93-L100):
            ```python
            assert tuple(progress) == (
                6,
                2.5,
                1,
                "learning",
                "2026-07-20",
                "2026-07-14 09:00:00",
            )
            ```

#### 4. [CLOSED] Missing Schema Validation in Python Tests (P3)
*   **Status**: **CLOSED** (Addressed via stdlib tests)
*   **Verification & Evidence**:
    *   Without introducing an external `jsonschema` library dependency (adhering to the project's dependency addition limits), the backup JSON schema features, allow-lists, key sorting, array counts, canonical formats, digests, and secret exclusions are verified using stdlib tests:
        *   [test_shared_contracts.py:L88-121](file:///home/user/projects/memcoach/tests/test_shared_contracts.py#L88-L121)

#### 5. [CLOSED] Dangling Foreign Keys in Legacy Reviews Fail Version 8→9 Migration (P2)
*   **Status**: **CLOSED** (Rejected / Resolved via fail-closed behavior)
*   **Verification & Evidence**:
    *   Skipping dangling keys via a filtering `JOIN` was rejected to uphold the approved "no-discard history" plan and ensure `PRAGMA foreign_key_check` failures do not silently pass. Instead, a new test constructs an orphaned schema-8 database and proves migration fail-closed rollback, stamp preservation, review preservation, and no card_progress table:
        *   [test_migrations.py:L188-219](file:///home/user/projects/memcoach/tests/test_migrations.py#L188-L219)

---

### Test Suite Execution Status

Both test suites pass fully:
1.  **Python migration, contract, and grading tests**: `pytest` successfully passes **40/40 tests**.
2.  **Kotlin native suites**: Gradle tests (`:core-scheduling:test` and `:core-grading:test`) successfully execute and build: **BUILD SUCCESSFUL**.

---

### Verdict

**GO**

*   **Unresolved P0/P1**: **None** (Turkish 'I' default-locale defect is verified closed).
