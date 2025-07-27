#!/bin/bash

# Build Android Test Client with Generated API Client
# This script ensures the generated client is built and published before building the Android app

set -e

echo "🚀 Building Android Test Client with Generated API Client"
echo "========================================================"

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Android client: $SCRIPT_DIR"

# Navigate to main project root
cd "$PROJECT_ROOT"

# Step 1: Generate and build the Android client  
echo "📦 Step 1: Generating Android API client..."
./gradlew generateAndroidClient

echo "🔨 Step 2: Building and publishing Android client to local Maven..."
cd build/generated-clients/android

# Use the main project's Gradle instead of the generated client's older Gradle
echo "🔨 Building generated Android client using main project Gradle..."
"$PROJECT_ROOT/gradlew" build publishToMavenLocal

# Navigate back to main project root
cd "$PROJECT_ROOT"

echo "✅ Android client published to local Maven repository"

# Step 3: Build the Android test client
echo "📱 Step 3: Building Android test client..."
cd "$SCRIPT_DIR"

# Clean and build the Android app
echo "🧹 Cleaning Android test client..."
./gradlew clean

echo "🔨 Building Android test client..."
./gradlew assembleDebug

echo ""
echo "🎉 Build completed successfully!"
echo ""
echo "📋 Generated artifacts:"
ls -la "$PROJECT_ROOT/build/generated-clients/android/build/libs/" 2>/dev/null || echo "   (No JAR files found - this is normal for Android library projects)"

echo ""
echo "📋 Next steps:"
echo "   1. Open android-test-client in Android Studio"
echo "   2. Run the app on device/emulator"  
echo "   3. Make sure your WebAuthn server is running on localhost:8080"
echo ""
echo "🔧 Development workflow:"
echo "   - When API changes: ./build-with-client.sh"
echo "   - For app-only changes: ./gradlew build (from android-test-client/)"
echo ""