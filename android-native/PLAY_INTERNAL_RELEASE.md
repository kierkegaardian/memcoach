# Play Internal Testing Runbook

Expected build artifacts:
- AAB: `app/build/outputs/bundle/release/app-release.aab`
- Release APK (local sideload): `app/build/outputs/apk/release/app-release.apk`
- Debug APK: `app/build/outputs/apk/debug/app-debug.apk`

Current package/version:
- Application ID: `com.memcoach.offline`
- Version code: `3`
- Version name: `0.3.0`

## 1) Build
```bash
cd android-native
source .secrets/upload-keystore.env
./gradlew17 :app:bundleRelease :app:assembleRelease :app:assembleDebug
```

Release tasks fail closed unless all four `MEMCOACH_UPLOAD_*` variables are present. Use an absolute path for `MEMCOACH_UPLOAD_STORE_FILE` when reusing the same signing environment for `android-wrapper`.

## 2) Phone push for immediate testing
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.memcoach.offline/.MainActivity
```

## 3) Google Play Console (manual, account login required)
1. Open Play Console -> your app (or create app if new).
2. Go to **Testing > Internal testing**.
3. Create release.
4. Upload `app-release.aab` from path above.
5. Add release name/notes.
6. Add tester emails/group.
7. Roll out to internal testing.

## 4) Validate internal test install
1. Open tester invite link on device.
2. Install from Play Store.
3. Run the smoke flow from `QA_CHECKLIST.md`.
4. Specifically verify child mode on-device:
   - set a parent PIN
   - enable child mode
   - confirm the home screen relocks after returning
   - verify the selected kid/deck still launches review
   - verify the wrong PIN does not unlock parent setup

## 5) If internal testing is blocked
Use **Internal app sharing** as fallback with the same AAB/APK while resolving account/setup blockers.
