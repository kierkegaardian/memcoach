### 1. Actionable P0/P1 Analysis

Based on the review of the complete function-context diff, **no new P0/P1 defects** were introduced in the wrapper signing configuration, CI test-path changes, or the helper scripts.

---

### 2. Verification of Earlier Android P1 Blockers

All four earlier P1 blockers have been successfully resolved by the changes in the diff:

#### A. Ambiguous WebView URL and Backslash Parsing
* **Status**: **Resolved**
* **Resolution Details**:
  * Replaced the loose Android `android.net.Uri` parsing with strict Java `java.net.URI` validation in `ServerUrlPolicy.kt:parseStrictWebUri()`.
  * Added an explicit check (`'\\' in raw`) to reject any URLs containing backslashes, preventing parser-differential exploits where Android's Uri parser and Java's URI parser disagree on host/path boundaries.
  * Added validation (`parsed.rawUserInfo != null`) to explicitly reject URLs containing user-info credentials (e.g., `https://attacker.example@memcoach.example`), preventing authority spoofing.
  * Migrated all verification paths in `MainActivity.kt` (including `shouldOverrideUrlLoading`, `onPageFinished`, and permission requests) to pass the raw string to `ServerUrlPolicy.isAllowedWebHost`, ensuring unified strict parsing.

#### B. Untrusted-Origin Microphone Permission Grants & Delayed Callbacks
* **Status**: **Resolved**
* **Resolution Details**:
  * Introduced `isTrustedAudioPermissionRequest()` inside `MainActivity.kt:208` which validates both that the request is for `RESOURCE_AUDIO_CAPTURE` and that `ServerUrlPolicy.isAllowedWebHost(request.origin.toString(), currentBaseUrl)` evaluates to true.
  * The check is executed both synchronously in `onPermissionRequest` and asynchronously within the `micPermissionLauncher` callback. This prevents privilege escalation if a delayed Android permission dialog completes after the WebView has navigated to an untrusted origin.

#### C. HomeViewModel Selection Reversion Before Preferences Persist
* **Status**: **Resolved**
* **Resolution Details**:
  * Reordered the fallback priority in `HomeViewModel.kt:preferredKidId()` and `preferredDeckId()`. The view model now prioritizes `current.selectedKidId` and `current.selectedDeckId` over `preferences.selectedKidId` and `preferences.selectedDeckId`.
  * This preserves the UI-selected ID during the database write window, preventing state updates from reverting the active selection back to the stale database preference before the async preference write finishes.

#### D. Unsigned Release Fail-Open Behavior
* **Status**: **Resolved**
* **Resolution Details**:
  * Added configuration-time task graph checks in both `android-native/app/build.gradle.kts:15-22` and `android-wrapper/app/build.gradle.kts:17-24`.
  * If a release build task is run (checked via `task.name.contains("release", ignoreCase = true)`) and upload signing keys are missing (`!hasUploadSigning`), the build immediately aborts with a `GradleException`. This prevents the compilation of silent, unsigned, or default-signed release artifacts.

---

### Conclusion

**All earlier Android P1 blockers are resolved.**
