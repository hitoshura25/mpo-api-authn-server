#!/bin/bash

# Generate Client Libraries Script
# This script automates the process of generating client libraries for the WebAuthn API

set -e

echo "🚀 Starting client library generation process..."

# Configuration
SERVER_URL="http://localhost:8080"
BUILD_DIR="build"
OPENAPI_DIR="$BUILD_DIR/openapi"
CLIENTS_DIR="$BUILD_DIR/generated-clients"

# Create directories
mkdir -p "$OPENAPI_DIR"
mkdir -p "$CLIENTS_DIR"

# Function to check if server is running
check_server() {
    echo "📡 Checking if server is running at $SERVER_URL..."
    if curl -s --fail "$SERVER_URL/health" > /dev/null; then
        echo "✅ Server is running"
        return 0
    else
        echo "❌ Server is not running. Please start the server first."
        return 1
    fi
}

# Function to start server in background if not running
start_server_if_needed() {
    if ! check_server; then
        echo "🔄 Starting server in background..."
        ./gradlew :webauthn-server:run &
        SERVER_PID=$!

        # Wait for server to start
        echo "⏳ Waiting for server to start..."
        for i in {1..30}; do
            if check_server; then
                echo "✅ Server started successfully"
                return 0
            fi
            sleep 2
        done

        echo "❌ Server failed to start within 60 seconds"
        return 1
    fi
}

# Function to generate OpenAPI spec
generate_openapi_spec() {
    echo "📄 Generating OpenAPI specification..."
    mkdir -p "$OPENAPI_DIR"
    curl -s -o "$OPENAPI_DIR/openapi.yaml" "$SERVER_URL/openapi"

    if [ -f "$OPENAPI_DIR/openapi.yaml" ]; then
        echo "✅ OpenAPI specification generated successfully"
    else
        echo "❌ Failed to generate OpenAPI specification"
        return 1
    fi
}

# Function to generate clients
generate_clients() {
    echo "🏗️  Generating client libraries..."

    echo "  📦 Generating TypeScript client..."
    ./gradlew :webauthn-server:generateTsClient

    echo "  ☕ Generating Java client..."
    ./gradlew :webauthn-server:generateJavaClient

    echo "  🐍 Generating Python client..."
    ./gradlew :webauthn-server:generatePythonClient

    echo "  🔷 Generating C# client..."
    ./gradlew :webauthn-server:generateCsharpClient

    echo "✅ All client libraries generated successfully"
}

# Function to package clients
package_clients() {
    echo "📦 Packaging client libraries..."

    # Create distribution directory
    DIST_DIR="$BUILD_DIR/client-distributions"
    mkdir -p "$DIST_DIR"

    # Package TypeScript client
    if [ -d "$CLIENTS_DIR/typescript" ]; then
        cd "$CLIENTS_DIR/typescript"
        if [ -f "package.json" ]; then
            npm pack
            mv *.tgz "../../client-distributions/"
        fi
        cd - > /dev/null
    fi

    # Package Java client
    if [ -d "$CLIENTS_DIR/java" ]; then
        cd "$CLIENTS_DIR/java"
        if [ -f "pom.xml" ]; then
            mvn package -DskipTests
            find target -name "*.jar" -exec cp {} ../../client-distributions/ \;
        fi
        cd - > /dev/null
    fi

    # Package Python client
    if [ -d "$CLIENTS_DIR/python" ]; then
        cd "$CLIENTS_DIR/python"
        if [ -f "setup.py" ]; then
            python setup.py sdist
            find dist -name "*.tar.gz" -exec cp {} ../../client-distributions/ \;
        fi
        cd - > /dev/null
    fi

    echo "✅ Client libraries packaged in $DIST_DIR"
}

# Function to cleanup
cleanup() {
    if [ ! -z "$SERVER_PID" ]; then
        echo "🧹 Stopping background server..."
        kill $SERVER_PID 2>/dev/null || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    echo "🎯 MPO WebAuthn Client Generator"
    echo "================================"

    # Check if we're in the right directory
    if [ ! -f "build.gradle.kts" ]; then
        echo "❌ Please run this script from the project root directory"
        exit 1
    fi

    # Start server if needed
    start_server_if_needed

    # Generate OpenAPI spec
    generate_openapi_spec

    # Generate clients
    generate_clients

    # Package clients (optional)
    if [ "$1" == "--package" ]; then
        package_clients
    fi

    echo ""
    echo "🎉 Client generation completed successfully!"
    echo ""
    echo "📂 Generated clients are available in:"
    echo "   TypeScript: $CLIENTS_DIR/typescript"
    echo "   Java:       $CLIENTS_DIR/java"
    echo "   Python:     $CLIENTS_DIR/python"
    echo "   C#:         $CLIENTS_DIR/csharp"
    echo ""
    echo "📖 API Documentation:"
    echo "   OpenAPI Spec: $SERVER_URL/openapi"
    echo "   Swagger UI:   $SERVER_URL/swagger"
    echo ""
    echo "💡 Usage examples:"
    echo "   ./generate-clients.sh           # Generate clients only"
    echo "   ./generate-clients.sh --package # Generate and package clients"
}

# Run main function
main "$@"
