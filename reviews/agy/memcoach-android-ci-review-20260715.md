Here is the correctness and security review of the selected Android and CI changes in `memcoach` commit `b23e1b8`.

---

### P0 Findings
*No P0 findings identified.*

---

### P1 Findings (Blocking)

#### 1. WebView Host Validation Bypass via Path/Authority Normalization Differences
* **File & Line**: [ServerUrlPolicy.kt:30-46](file:///home/user/projects/memcoach/android-wrapper/app/src/main/java/com/memcoach/wrapper/ServerUrlPolicy.kt#L30-L46)
* **Details**: [ServerUrlPolicy.isAllowedWebHost](file:///home/user/projects/memcoach/android-wrapper/app/src/main/java/com/memcoach/wrapper/ServerUrlPolicy.kt#L30) relies on Android's `android.net.Uri.parse` to extract the hostname. Android's parser resolves hosts differently from Chromium (the WebView core) when dealing with backslashes in the authority component. For example, a target URL like `https://attacker.com\@[at]example.com` (assuming `example.com` is the trusted host) is parsed by Android's `Uri.parse` as having the host `example.com`. However, Chromium normalizes backslashes to forward slashes before parsing (converting the URL to `https://attacker.com/@[at]example.com`), interpreting the host as `attacker.com`. This discrepancy bypasses the `shouldOverrideUrlLoading` check, allowing the WebView to load pages from `attacker.com`.
* **Remediation**: Validate that the target URL contains no backslash characters `\` in the authority/host portion before checking correctness, or perform strict WHATWG-compliant URL parsing.

#### 2. WebView Untrusted Origin Permission Grant
* **File & Line**: [MainActivity.kt:123-137](file:///home/user/projects/memcoach/android-wrapper/app/src/main/java/com/memcoach/wrapper/MainActivity.kt#L123-L137)
* **Details**: In [MainActivity](file:///home/user/projects/memcoach/android-wrapper/app/src/main/java/com/memcoach/wrapper/MainActivity.kt), the `WebChromeClient.onPermissionRequest` callback grants `RESOURCE_AUDIO_CAPTURE` directly if the app has the system `RECORD_AUDIO` permission. It does not inspect `request.origin`. If the WebView navigates to an untrusted page (e.g., through an iframe load or a redirect), that external origin can trigger audio recording without the app validating that the origin is trusted.
* **Remediation**: Check `request.origin` using [ServerUrlPolicy.isAllowedWebHost](file:///home/user/projects/memcoach/android-wrapper/app/src/main/java/com/memcoach/wrapper/ServerUrlPolicy.kt#L30) before calling `request.grant`.

#### 3. UI State Reversion and Selection Flicker Race Condition
* **File & Line**: [HomeViewModel.kt:46-88](file:///home/user/projects/memcoach/android-native/app/src/main/java/com/memcoach/offline/feature/home/HomeViewModel.kt#L46-L88)
* **Details**: [HomeViewModel](file:///home/user/projects/memcoach/android-native/app/src/main/java/com/memcoach/offline/feature/home/HomeViewModel.kt) combines background repository flows with preference changes to construct UI state. When a user selects a kid or deck (e.g., via `selectKid(id)`), the UI state is updated synchronously and a coroutine is launched to write the change asynchronously to SharedPreferences via `appPreferencesRepository.setSelectedKidId(id)`. If another flow (e.g., `observeKids()`) emits before the SharedPreferences write completes, `flatMapLatest` evaluates using the old SharedPreferences value. This causes `preferredKidId` to select the old kid ID and overwrite the active user selection, resulting in a UI state reversion and subsequent flicker.
* **Remediation**: Decouple transient UI selections from database flows, or ensure the UI selection state acts as the single source of truth during ongoing transitions.

#### 4. Unsigned Release Build Fail-Open Behavior
* **File & Line**: [build.gradle.kts:43-50](file:///home/user/projects/memcoach/android-native/app/build.gradle.kts#L43-L50)
* **Details**: In the `android-native` configuration, if the release signing environment variables (`MEMCOACH_UPLOAD_*`) are missing or blank, `signingConfig` is set to `null`. This allows the release build task to succeed silently and output an unsigned release APK. This is a fail-open behavior that can result in a CI pipeline successfully completing but releasing/publishing an unsigned APK.
* **Remediation**: Throw a `GradleException` if a release build is requested but the required signing variables are not defined.

---

### P2 Findings

#### 1. Missing Signing Configuration for Wrapper Release Build
* **File & Line**: [build.gradle.kts:30-38](file:///home/user/projects/memcoach/android-wrapper/app/build.gradle.kts#L30-L38)
* **Details**: Unlike the native application, the `android-wrapper` build configuration has no `signingConfigs` block or `signingConfig` assignment in its `release` build type block. Release wrapper builds will always produce unsigned packages.
* **Remediation**: Add a signing configuration similar to the native app.

#### 2. Divergent CI and Local Build/Execution Pathways
* **File & Line**: [ci.yml:31-34](file:///home/user/projects/memcoach/.github/workflows/ci.yml#L31-L34) vs [Makefile:19-24](file:///home/user/projects/memcoach/Makefile#L19-L24)
* **Details**: The CI workflow executes `./gradlew` directly, bypassing the local development entrypoint script [gradlew17](file:///home/user/projects/memcoach/android-native/gradlew17). As a result, the SDK version verification, JDK setup, and local environment properties checked in `gradlew17` are bypassed in CI, risking configuration drifts.
* **Remediation**: Update [ci.yml](file:///home/user/projects/memcoach/.github/workflows/ci.yml) to execute `./gradlew17` to align with the local `Makefile` commands.

#### 3. Unpinned and Unverified JDK Downloads
* **File & Line**: [gradlew17:9](file:///home/user/projects/memcoach/android-native/gradlew17#L9) and [gradlew17:158-162](file:///home/user/projects/memcoach/android-native/gradlew17#L158-L162)
* **Details**: The `gradlew17` script queries a dynamic URL (`.../latest/17/...`) to fetch the latest JDK 17. Because the file is downloaded without verifying against a SHA-256 checksum, builds lack determinism and the environment is exposed to potential MITM or supply-chain payload injection.
* **Remediation**: Pin the download link to a specific minor/patch release and verify its SHA-256 integrity hash before extracting it.

---

### P3 / Residual Findings

#### 1. Plaintext PIN Memory Exposure
* **File & Line**: [AppPreferencesRepositoryImpl.kt:109-116](file:///home/user/projects/memcoach/android-native/app/src/main/java/com/memcoach/offline/data/repository/AppPreferencesRepositoryImpl.kt#L109-L116)
* **Details**: The `derivePin` method operates on `pin.trim().toCharArray()`. While `spec.clearPassword()` is executed, the temporary char array generated by `toCharArray()` and the immutable String generated by `pin.trim()` remain in JVM memory until garbage collection executes, exposing sensitive PINs to memory dump inspection.
* **Remediation**: Avoid string operations on secrets where possible. Use and pass char arrays directly, and explicitly zero them out (e.g., fill with `\u0000`) immediately after use.

#### 2. Minification Disabled in Release Configurations
* **File & Line**: [build.gradle.kts:44](file:///home/user/projects/memcoach/android-native/app/build.gradle.kts#L44) and [build.gradle.kts:32](file:///home/user/projects/memcoach/android-wrapper/app/build.gradle.kts#L32)
* **Details**: Both native and wrapper configurations set `isMinifyEnabled = false` for release builds. This leads to larger binary sizes and leaves bytecode fully de-obfuscated.
* **Remediation**: Set `isMinifyEnabled = true` and define appropriate rules in `proguard-rules.pro`.

#### 3. Use of Mutable Version Tags in CI Actions
* **File & Line**: [ci.yml:13-16](file:///home/user/projects/memcoach/.github/workflows/ci.yml#L13-L16) and [ci.yml:23-29](file:///home/user/projects/memcoach/.github/workflows/ci.yml#L23-L29)
* **Details**: The workflow references mutable version tags (such as `@v4`, `@v5`, and `@v3`) for external actions. This can allow upstream modifications to break pipeline builds.
* **Remediation**: Pin external actions to their immutable Git commit SHAs.
