#!/bin/bash
set -e

echo "⏱️ Starting Android tests with 8-minute timeout..."

# Check KVM availability
if [ -e /dev/kvm ]; then
  echo "✅ KVM device available"
else
  echo "⚠️ KVM not available - emulator will be slower"
fi

# Wait for emulator with reasonable timeout
echo "📱 Waiting for emulator to be ready..."
timeout 180 adb wait-for-device shell 'while [[ -z $(getprop sys.boot_completed | tr -d '\r') ]]; do sleep 2; done'
EMULATOR_READY=$?

if [ $EMULATOR_READY -ne 0 ]; then
  echo "❌ Emulator failed to start within 3 minutes"
  echo "This usually indicates KVM issues or runner resource constraints"
  exit 1
fi

# Unlock device and verify it's responsive
adb shell input keyevent 82
sleep 1

# Quick responsiveness test
timeout 15 adb shell getprop ro.build.version.release
if [ $? -ne 0 ]; then
  echo "❌ Emulator not responsive within 15 seconds"
  exit 1
fi

echo "✅ Emulator ready and responsive"

# Run Android unit tests first (fast)
cd android-test-client
echo "🧪 Running Android unit tests..."
timeout 180 ./gradlew test --build-cache --parallel
UNIT_TEST_EXIT=$?

if [ $UNIT_TEST_EXIT -ne 0 ]; then
  echo "❌ Unit tests failed"
  exit $UNIT_TEST_EXIT
fi

# Run instrumentation tests with shorter timeout
echo "🧪 Running WebAuthnFlowTest instrumentation tests..."
timeout 300 ./gradlew connectedAndroidTest --build-cache --parallel --info
TEST_EXIT_CODE=$?

echo "android-test-exit-code=$TEST_EXIT_CODE" >> $GITHUB_OUTPUT

if [ $TEST_EXIT_CODE -ne 0 ]; then
  echo "❌ Android instrumentation tests failed with exit code $TEST_EXIT_CODE"
  exit $TEST_EXIT_CODE
else
  echo "✅ Android tests passed successfully"
fi