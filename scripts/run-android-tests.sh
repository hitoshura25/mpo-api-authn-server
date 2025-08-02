#!/bin/bash
set -e

echo "⏱️ Starting Android tests with 8-minute timeout..."

# Check KVM availability
if [ -e /dev/kvm ]; then
  echo "✅ KVM device available"
else
  echo "⚠️ KVM not available - emulator will be slower"
fi

# Run instrumentation tests with shorter timeout
echo "🧪 Running WebAuthnFlowTest instrumentation tests..."
timeout 300 ./gradlew connectedAndroidTest --build-cache --parallel
TEST_EXIT_CODE=$?

echo "android-test-exit-code=$TEST_EXIT_CODE" >> $GITHUB_OUTPUT

if [ $TEST_EXIT_CODE -ne 0 ]; then
  echo "❌ Android instrumentation tests failed with exit code $TEST_EXIT_CODE"
  exit $TEST_EXIT_CODE
else
  echo "✅ Android tests passed successfully"
fi
