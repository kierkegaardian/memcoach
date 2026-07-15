PYTHON ?= python3

.PHONY: lint test build smoke check android-debug android-wrapper-debug android-install-usb

lint:
	$(PYTHON) -m ruff check config.py main.py db models routes tests utils

test:
	$(PYTHON) -m pytest

build:
	$(PYTHON) -m compileall -q config.py main.py db models routes utils

smoke:
	$(PYTHON) -c "from main import app; print(app.title)"

check: lint test build smoke

android-debug:
	cd android-native && ./gradlew17 :core-scheduling:test :core-grading:test :app:testDebugUnitTest :app:assembleDebug --no-daemon

android-wrapper-debug:
	cd android-native && ./gradlew17 -p ../android-wrapper :app:testDebugUnitTest :app:assembleDebug --no-daemon

android-install-usb:
	adb install -r android-native/app/build/outputs/apk/debug/app-debug.apk
	adb shell am start -n com.memcoach.offline/.MainActivity
