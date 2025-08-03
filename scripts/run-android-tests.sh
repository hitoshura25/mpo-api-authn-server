#!/bin/bash
set -e

echo "⏱️ Starting Android tests..."

# Check KVM availability
if [ -e /dev/kvm ]; then
  echo "✅ KVM device available"
else
  echo "⚠️ KVM not available - emulator will be slower"
fi

# Run instrumentation tests (GitHub Action handles timeout)
echo "🧪 Running WebAuthnFlowTest instrumentation tests..."
cd android-test-client
./gradlew connectedAndroidTest --build-cache --parallel --configuration-cache --no-daemon
TEST_EXIT_CODE=$?

echo "android-test-exit-code=$TEST_EXIT_CODE" >> $GITHUB_OUTPUT

if [ $TEST_EXIT_CODE -ne 0 ]; then
  echo "❌ Android instrumentation tests failed with exit code $TEST_EXIT_CODE"
  exit $TEST_EXIT_CODE
else
  echo "✅ Android tests passed successfully"
fi
