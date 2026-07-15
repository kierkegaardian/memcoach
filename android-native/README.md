# MemCoach Native Android (Offline-First)

This module is the native Android app for MemCoach. It is fully local-first and does not depend on the FastAPI backend.

## Current scope

Implemented core flow:
- Create kids and decks
- Add cards to a deck
- Run typed review sessions with deterministic local grading
- Apply SM-2 scheduling updates into local progress data
- Lock parent setup behind an optional local PIN for kid-device deployment

Deferred for later milestones:
- STT/microphone recitation
- import/export bridge
- extended stats and tags

## Modules

- `app`: Compose UI, Room database, repositories, review session flow
- `core-scheduling`: SM-2 scheduling logic
- `core-grading`: deterministic local grading

## Quickstart

Use `./gradlew17` for every Gradle command in this module. It is the canonical entrypoint for:
- bootstrapping a local Temurin JDK 17
- resolving the Android SDK location
- failing fast when required SDK packages are missing

`./gradlew17` is **preflight-only**. It does not install Android SDK packages for you.

### 1) Install Android Studio components

Make sure the Android SDK includes:
- `platforms;android-36`
- `build-tools;35.0.0`
- `platform-tools` for `adb` and device installs
- Android SDK Command-line Tools so `sdkmanager` is available

### 2) Point the wrapper at your SDK

The wrapper resolves the SDK in this order:
1. `ANDROID_SDK_ROOT`
2. `ANDROID_HOME`
3. `sdk.dir=` in `android-native/local.properties`
4. `$HOME/Android/Sdk`

Typical Linux setup:

```bash
export ANDROID_SDK_ROOT="$HOME/Android/Sdk"
export ANDROID_HOME="$ANDROID_SDK_ROOT"
```

Or use `local.properties`:

```properties
sdk.dir=/home/your-user/Android/Sdk
```

### 3) Accept licenses and install required packages

If Android SDK Command-line Tools are installed:

```bash
yes | "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --licenses
"$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" \
  "platforms;android-36" \
  "build-tools;35.0.0" \
  "platform-tools"
```

If your `sdkmanager` lives elsewhere, use that path instead. The wrapper prints the same commands when preflight fails.

### 4) Build and test

```bash
cd android-native
./gradlew17 :core-scheduling:test :core-grading:test
./gradlew17 :app:testDebugUnitTest
./gradlew17 :app:assembleDebug
```

Debug APK output:
- `android-native/app/build/outputs/apk/debug/app-debug.apk`

## Release bundle

For a release AAB with an upload key, set these environment variables:
- `MEMCOACH_UPLOAD_STORE_FILE`
- `MEMCOACH_UPLOAD_STORE_PASSWORD`
- `MEMCOACH_UPLOAD_KEY_ALIAS`
- `MEMCOACH_UPLOAD_KEY_PASSWORD`

Then build:

```bash
cd android-native
./gradlew17 :app:bundleRelease
```

If signing variables are not set, Gradle may build an unsigned release artifact, but it will not substitute the debug key. If any signing variable is set, all four are required.

## Boox Palma deployment notes

For a child-owned Palma or other e-ink Android device:
- Select the kid and deck in the home screen first.
- Open `Settings`, set a local parent PIN, and enable child mode.
- Verify the home screen returns to the locked child-review layout before sideloading or shipping a release build.
- Keep review text short and high-contrast; the current native UI avoids network calls and animation-heavy flows.
- For direct phone installs over USB, use [`USB_SIDELOAD.md`](USB_SIDELOAD.md).

## Dependency policy

Runtime dependencies remain open-source and local-only.
No cloud SDK is required for the core review path.

Key runtime dependencies:
- Jetpack Compose
- Navigation Compose
- Room (SQLite)
- Kotlin coroutines

## Manual QA

See `QA_CHECKLIST.md` for the current smoke matrix and wrapper preflight checks.
