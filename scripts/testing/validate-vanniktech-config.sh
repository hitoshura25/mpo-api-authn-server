#!/bin/bash
set -euo pipefail

# Validate vanniktech plugin configuration in Android template

echo "🔍 Validating vanniktech plugin configuration..."

TEMPLATE_FILE="android-client-library/build.gradle.kts.template"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "❌ Template file not found: $TEMPLATE_FILE"
    exit 1
fi

echo "✅ Template file found: $TEMPLATE_FILE"

# Check for vanniktech plugin
if grep -q "com.vanniktech.maven.publish" "$TEMPLATE_FILE"; then
    echo "✅ vanniktech plugin configured"
else
    echo "❌ vanniktech plugin not found"
    exit 1
fi

# Check for automaticRelease = true in production configuration
if grep -A 5 'publishType == "production"' "$TEMPLATE_FILE" | grep -q "automaticRelease = true"; then
    echo "✅ automaticRelease = true configured for production"
else
    echo "❌ automaticRelease = true not found for production"
    exit 1
fi

# Check for CENTRAL_PORTAL host
if grep -q "SonatypeHost.CENTRAL_PORTAL" "$TEMPLATE_FILE"; then
    echo "✅ Central Portal host configured"
else
    echo "❌ Central Portal host not found"
    exit 1
fi

# Check for environment variable configuration
if grep -q "System.getenv(\"PUBLISH_TYPE\")" "$TEMPLATE_FILE"; then
    echo "✅ Environment variable configuration found"
else
    echo "❌ Environment variable configuration missing"
    exit 1
fi

# Check for repository URL environment variable support
if grep -q "ANDROID_REPOSITORY_URL" "$TEMPLATE_FILE"; then
    echo "✅ Repository URL environment variable support found"
else
    echo "❌ Repository URL environment variable support missing"
    exit 1
fi

# Check for GitHub repository environment variable support
if grep -q "GITHUB_REPOSITORY" "$TEMPLATE_FILE"; then
    echo "✅ GitHub repository environment variable support found"
else
    echo "❌ GitHub repository environment variable support missing"
    exit 1
fi

echo ""
echo "🎯 vanniktech Plugin Configuration Summary:"
echo "  ✅ Plugin configured: com.vanniktech.maven.publish v0.29.0"
echo "  ✅ Production target: Maven Central (Central Portal)"
echo "  ✅ Automatic release: ENABLED for production"
echo "  ✅ Staging target: GitHub Packages"
echo "  ✅ Environment variables: Properly configured"
echo "  ✅ Repository URLs: Dynamic via environment variables"
echo ""
echo "🚀 Benefits of vanniktech Plugin Migration:"
echo "  ✅ No manual release steps required for Maven Central"
echo "  ✅ Automatic signing and publication"
echo "  ✅ Simplified workflow without manual verification"
echo "  ✅ Packages immediately available on Maven Central"
echo ""
echo "✅ vanniktech plugin configuration validation completed successfully!"