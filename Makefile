PYTHON ?= python3

.PHONY: lint test build smoke check android-debug android-migration-test android-wrapper-debug android-install-usb

lint:
	$(PYTHON) -m ruff check config.py main.py db models portable routes tests utils

test:
	$(PYTHON) -m pytest

build:
	$(PYTHON) -m compileall -q config.py main.py db models portable routes utils

smoke:
	$(PYTHON) -c "from main import app; print(app.title)"

check: lint test build smoke

android-debug:
	cd android-native && ./gradlew17 :core-scheduling:test :core-grading:test :app:testDebugUnitTest :app:assembleDebug :app:assembleAndroidTest --no-daemon

android-migration-test:
	test -n "$(ANDROID_SERIAL)" || (echo "Set ANDROID_SERIAL to a disposable emulator serial" >&2; exit 1)
	cd android-native && ANDROID_SERIAL="$(ANDROID_SERIAL)" ./gradlew17 :app:connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.memcoach.offline.data.local.RoomV1MigrationTest --no-daemon

android-wrapper-debug:
	cd android-native && ./gradlew17 -p ../android-wrapper :app:testDebugUnitTest :app:assembleDebug --no-daemon

android-install-usb:
	test -n "$(ANDROID_SERIAL)" || (echo "Set ANDROID_SERIAL explicitly" >&2; exit 1)
	adb -s "$(ANDROID_SERIAL)" install -r android-native/app/build/outputs/apk/debug/app-debug.apk
	adb -s "$(ANDROID_SERIAL)" shell am start -n com.memcoach.offline/.MainActivity
