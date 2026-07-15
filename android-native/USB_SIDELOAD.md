# USB Sideload Runbook

Use this path when you want the next build on a phone directly over USB instead of Play testing.

## 1) Prepare the phone

On the Android phone:
1. Enable Developer Options.
2. Enable USB debugging.
3. Connect the phone by USB.
4. Accept the RSA debugging prompt on the phone if it appears.

## 2) Verify adb sees the phone

```bash
adb devices
```

Expected: one device in the `device` state.

If it shows `unauthorized`, unlock the phone and accept the prompt.

## 3) Build the debug APK

```bash
cd android-native
./gradlew17 :core-scheduling:test :core-grading:test :app:testDebugUnitTest :app:assembleDebug
```

APK output:

`app/build/outputs/apk/debug/app-debug.apk`

## 4) Install over USB

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.memcoach.offline/.MainActivity
```

`-r` replaces the existing app while keeping app data when Android allows it.

## 5) Immediate on-phone checks

1. Launch the app.
2. Create or select the kid and deck.
3. Add at least one card if the deck is empty.
4. Open `Settings`, set a parent PIN, and enable child mode.
5. Return to the home screen and verify it relocks into the child-review layout.
6. Start a review and submit one exact answer.

## 6) If install fails

- `INSTALL_FAILED_VERSION_DOWNGRADE`: uninstall the existing app or bump the version code.
- `INSTALL_FAILED_UPDATE_INCOMPATIBLE`: the installed app was signed with a different key; uninstall the existing app first.
- `device offline`: reconnect USB and rerun `adb devices`.
- `unauthorized`: unlock the phone and accept the USB debugging prompt.
