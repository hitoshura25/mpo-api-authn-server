#!/bin/bash

# Full stack setup - Start everything including the application
set -euo pipefail

echo "🔍 Checking for existing services..."

# Check if services are already running
if docker compose ps --services --filter "status=running" | grep -q .; then
    echo "⚠️  Some services are already running. Stopping them first..."
    docker compose down
    echo "🛑 Stopped existing services"
fi

echo "🚀 Building WebAuthn Test Credentials Server..."
cd .. && ./gradlew :webauthn-test-credentials-service:shadowJar --build-cache --parallel --configuration-cache && cd webauthn-server

echo "🚀 Building WebAuthn Server..."
cd .. && ./gradlew :webauthn-server:shadowJar --build-cache --parallel --configuration-cache && cd webauthn-server

echo "🚀 Starting full stack (PostgreSQL, Redis & WebAuthn Server)..."
docker compose up --build -d

echo "⏳ Waiting for dependencies to be healthy..."
for i in {1..60}; do
    healthy_count=$(docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep -c "healthy" || true)
    if [ "$healthy_count" -eq 3 ]; then
        echo "✅ All dependencies are healthy!"
        break
    fi
    echo "Waiting for dependencies to be healthy... ($i/60) - $healthy_count/3 healthy"
    sleep 2
done

# Check dependencies health
dependency_health=$(docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep -c "healthy" || true)
if [ "$dependency_health" -eq 3 ]; then
    echo "✅ Dependencies ready, checking WebAuthn server..."

    # External health check for distroless webauthn-server
    for j in {1..30}; do
        if curl -s --fail http://localhost:8080/health > /dev/null 2>&1; then
            echo "✅ WebAuthn server is responding!"
            SERVER_HEALTHY=true
            break
        fi
        echo "Waiting for WebAuthn server... ($j/30)"
        sleep 2
    done

    if [ "${SERVER_HEALTHY:-false}" = "true" ]; then
        echo "✅ Full stack is ready!"
        echo ""
        echo "🌐 WebAuthn Server: http://localhost:8080"
        echo "🏥 Health Check: http://localhost:8080/health"
        echo "📋 API Docs: http://localhost:8080/swagger"
        echo ""
        echo "🔍 To view logs: docker compose logs -f"
        echo "🛑 To stop: docker compose down"
    else
        echo "❌ WebAuthn server failed to start. Check logs with: docker compose logs webauthn-server"
        docker compose ps
    fi
else
    echo "❌ Dependencies failed to start. Check logs with: docker compose logs"
    docker compose ps
fi
