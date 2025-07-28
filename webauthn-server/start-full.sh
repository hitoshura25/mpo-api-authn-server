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

echo "🚀 Building WebAuthn Server..."
cd .. && ./gradlew :webauthn-server:shadowJar --build-cache --parallel --configuration-cache && cd webauthn-server

echo "🚀 Starting full stack (PostgreSQL, Redis & WebAuthn Server)..."
docker compose up --build -d

echo "⏳ Waiting for all services to be healthy..."
for i in {1..60}; do
    healthy_count=$(docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep -c "healthy" || true)
    if [ "$healthy_count" -eq 4 ]; then
        echo "✅ All services are healthy!"
        break
    fi
    echo "Waiting for services to be healthy... ($i/60) - $healthy_count/4 healthy"
    sleep 2
done

# Final health check
healthy_count=$(docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep -c "healthy" || true)
if [ "$healthy_count" -eq 4 ]; then
    echo "✅ Full stack is ready!"
    echo ""
    echo "🌐 WebAuthn Server: http://localhost:8080"
    echo "🏥 Health Check: http://localhost:8080/health"
    echo "📋 API Docs: http://localhost:8080/swagger"
    echo ""
    echo "🔍 To view logs: docker compose logs -f"
    echo "🛑 To stop: docker compose down"
else
    echo "❌ Not all services are healthy. Check logs with: docker compose logs"
    docker compose ps
fi
