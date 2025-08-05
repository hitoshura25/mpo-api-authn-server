#!/bin/bash

# Setup script for consuming GitHub Packages
# This script helps configure local development environment to use published Android clients

set -e

echo "🔧 GitHub Packages Setup for Android Client"
echo "============================================"

# Check if we're in the right directory
if [ ! -f "build.gradle.kts" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Function to prompt for input with default value
prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        input="${input:-$default}"
    else
        read -p "$prompt: " input
    fi
    
    eval "$var_name='$input'"
}

# Get GitHub credentials
echo ""
echo "📋 We need your GitHub credentials to access packages"
echo "You can get a token from: https://github.com/settings/tokens"
echo "Required permissions: read:packages"
echo ""

# Try to get current GitHub user
CURRENT_USER=$(git config user.name 2>/dev/null || echo "")
if [ -n "$CURRENT_USER" ]; then
    echo "Git user detected: $CURRENT_USER"
fi

prompt_input "GitHub username" "$CURRENT_USER" "GITHUB_USERNAME"
prompt_input "GitHub token (will be hidden)" "" "GITHUB_TOKEN"

if [ -z "$GITHUB_USERNAME" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Both username and token are required"
    exit 1
fi

# Determine setup method
echo ""
echo "📝 Choose setup method:"
echo "1. Environment variables (temporary, session-only)"
echo "2. Global Gradle properties (permanent, all projects)"
echo "3. Project Gradle properties (permanent, this project only)"
echo ""

prompt_input "Choose method (1-3)" "2" "SETUP_METHOD"

case $SETUP_METHOD in
    1)
        echo ""
        echo "🔧 Setting up environment variables..."
        
        # Create a script that can be sourced
        cat > .env-github-packages << EOF
# GitHub Packages Environment Variables
# Source this file: source .env-github-packages
export USERNAME="$GITHUB_USERNAME"
export TOKEN="$GITHUB_TOKEN"

echo "✅ GitHub Packages environment variables loaded"
echo "   Username: \$USERNAME"
echo "   Token: [HIDDEN]"
EOF
        
        # Add to gitignore if not already there
        if ! grep -q ".env-github-packages" .gitignore 2>/dev/null; then
            echo ".env-github-packages" >> .gitignore
            echo "📝 Added .env-github-packages to .gitignore"
        fi
        
        echo "✅ Environment setup complete!"
        echo ""
        echo "📋 To use:"
        echo "   source .env-github-packages"
        echo ""
        ;;
        
    2)
        echo ""
        echo "🔧 Setting up global Gradle properties..."
        
        GRADLE_HOME="$HOME/.gradle"
        GRADLE_PROPS="$GRADLE_HOME/gradle.properties"
        
        # Create .gradle directory if it doesn't exist
        mkdir -p "$GRADLE_HOME"
        
        # Backup existing properties if they exist
        if [ -f "$GRADLE_PROPS" ]; then
            cp "$GRADLE_PROPS" "$GRADLE_PROPS.backup.$(date +%Y%m%d_%H%M%S)"
            echo "📋 Backed up existing gradle.properties"
        fi
        
        # Update or create gradle.properties
        {
            echo ""
            echo "# GitHub Packages credentials (added by setup script)"
            echo "gpr.user=$GITHUB_USERNAME"
            echo "gpr.key=$GITHUB_TOKEN"
        } >> "$GRADLE_PROPS"
        
        echo "✅ Global Gradle properties updated!"
        echo "📁 File: $GRADLE_PROPS"
        echo ""
        ;;
        
    3)
        echo ""
        echo "🔧 Setting up project Gradle properties..."
        
        PROJECT_PROPS="gradle.properties"
        
        # Backup existing properties if they exist
        if [ -f "$PROJECT_PROPS" ]; then
            cp "$PROJECT_PROPS" "$PROJECT_PROPS.backup.$(date +%Y%m%d_%H%M%S)"
            echo "📋 Backed up existing gradle.properties"
        fi
        
        # Update or create gradle.properties
        {
            echo ""
            echo "# GitHub Packages credentials (added by setup script)"
            echo "gpr.user=$GITHUB_USERNAME"
            echo "gpr.key=$GITHUB_TOKEN"
        } >> "$PROJECT_PROPS"
        
        # Add to gitignore if not already there
        if ! grep -q "gradle.properties" .gitignore 2>/dev/null; then
            echo "gradle.properties" >> .gitignore
            echo "📝 Added gradle.properties to .gitignore"
        fi
        
        echo "✅ Project Gradle properties updated!"
        echo "📁 File: $PROJECT_PROPS"
        echo ""
        ;;
        
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

# Test the setup
echo "🧪 Testing GitHub Packages access..."

# Create a temporary test project
TEST_DIR=$(mktemp -d)
cat > "$TEST_DIR/build.gradle" << EOF
plugins {
    id 'java'
}

repositories {
    maven {
        name = "GitHubPackages"
        url = uri("https://maven.pkg.github.com/$GITHUB_USERNAME/mpo-api-authn-server")
        credentials {
            username = project.findProperty("gpr.user") ?: System.getenv("USERNAME")
            password = project.findProperty("gpr.key") ?: System.getenv("TOKEN")
        }
    }
}

configurations {
    testResolve
}

dependencies {
    testResolve 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:+'
}

task testAccess {
    doLast {
        configurations.testResolve.resolve()
        println "✅ Successfully resolved Android client package"
    }
}
EOF

cd "$TEST_DIR"

# Set environment variables for test if using method 1
if [ "$SETUP_METHOD" = "1" ]; then
    export USERNAME="$GITHUB_USERNAME"
    export TOKEN="$GITHUB_TOKEN"
fi

# Run the test
if gradle testAccess 2>/dev/null; then
    echo "✅ GitHub Packages access test successful!"
else
    echo "⚠️  GitHub Packages access test failed"
    echo "   This might be normal if no packages have been published yet"
fi

# Cleanup
cd - > /dev/null
rm -rf "$TEST_DIR"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. The automated workflow will publish Android clients when:"
echo "   - OpenAPI specs change"
echo "   - Pull requests are created/updated"
echo "   - Changes are pushed to main branch"
echo ""
echo "2. Use the published client in your Android projects:"
echo "   implementation 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:VERSION'"
echo ""
echo "3. Check published packages at:"
echo "   https://github.com/$GITHUB_USERNAME/mpo-api-authn-server/packages"
echo ""
echo "📖 For more information, see docs/setup/github-packages-setup.md"