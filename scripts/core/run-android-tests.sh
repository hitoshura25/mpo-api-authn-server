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
./gradlew connectedAndroidTest \
  -PGitHubPackagesUsername="$GITHUB_PACKAGES_USERNAME" \
  -PGitHubPackagesPassword="$GITHUB_PACKAGES_PASSWORD" \
  --build-cache --parallel --configuration-cache --no-daemon

TEST_EXIT_CODE=$?

echo "android-test-exit-code=$TEST_EXIT_CODE" >> "$GITHUB_OUTPUT"

if [ $TEST_EXIT_CODE -ne 0 ]; then
  echo "tests-passed=false" >> "$GITHUB_OUTPUT"
  echo "❌ Android instrumentation tests failed with exit code $TEST_EXIT_CODE"
  exit $TEST_EXIT_CODE
else
  echo "tests-passed=true" >> "$GITHUB_OUTPUT"
  echo "✅ Android tests passed successfully"
  
  # Create test results for caching (go back to root directory)
  cd ..
  mkdir -p android-e2e-cache
  echo '{
    "status": "success",
    "tests_passed": true,
    "timestamp": "'$(date -Iseconds)'",
    "images": {
      "webauthn_server": "'${WEBAUTHN_SERVER_IMAGE:-unknown}'",
      "test_credentials": "'${TEST_CREDENTIALS_IMAGE:-unknown}'"
    },
    "client_package": "'${ANDROID_PACKAGE_NAME:-unknown}':'${CLIENT_VERSION:-unknown}'"
  }' > android-e2e-results.json
  
  echo "📝 Created test results file for caching"
fi

# Trying to address hanging Github job: https://github.com/ReactiveCircus/android-emulator-runner/issues/385#issuecomment-2492035091
killall -INT crashpad_handler || true
