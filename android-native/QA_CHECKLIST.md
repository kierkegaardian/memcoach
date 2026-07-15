# Native Android QA Checklist

## Wrapper preflight checks

1. Run `./gradlew17 :app:tasks` with no SDK configured and verify it fails before Gradle with SDK location guidance.
2. Point `ANDROID_SDK_ROOT` at an SDK missing `platforms;android-36` and verify preflight fails with the exact `sdkmanager` package command.
3. Point `ANDROID_SDK_ROOT` at an SDK missing `build-tools;35.0.0` and verify preflight fails with the exact `sdkmanager` package command.
4. Point `ANDROID_SDK_ROOT` at an SDK missing `platform-tools` and verify preflight prints a warning but still continues into Gradle.

## Core smoke flow (airplane mode)

1. Enable airplane mode.
2. Install debug APK.
3. Launch app and create a kid.
4. Create a deck.
5. Verify `Start Review` stays disabled for the new empty deck and the home screen tells you to add at least one card first.
6. Open deck card manager.
7. Add at least one card with prompt + full text.
8. Return home and verify `Start Review` becomes enabled for the selected kid/deck.
9. Start review for selected kid/deck.
10. Submit an exact answer.
11. Verify grade is `perfect` and session advances.
12. Verify no due card remains immediately after a perfect first review.

## Persistence checks

1. Force close app.
2. Reopen app.
3. Verify kid/deck/card data still exists.
4. Re-enter review and verify scheduling state persisted.

## Child-mode checks

1. Open `Settings` and set a parent PIN.
2. Enable child mode.
3. Return to the home screen and verify parent setup is hidden behind the PIN prompt.
4. Verify the selected kid/deck from the parent session remains available for `Start Review`.
5. Enter the correct PIN and verify parent setup becomes available again.
6. Enter an incorrect PIN and verify the app stays locked.

## Basic validation checks

1. Try adding blank kid name -> should show validation message.
2. Try adding blank deck name -> should show validation message.
3. Try adding card with blank prompt or full text -> should show validation message.

## Release artifact checks

1. Build `:app:bundleRelease`.
2. Verify AAB exists under `app/build/outputs/bundle/release/`.
3. Upload to Play Internal Testing.
4. Install from internal testing link and run core smoke flow plus child-mode checks.
