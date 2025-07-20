#!/bin/bash

# Development setup - Start only dependencies (PostgreSQL & Redis)
echo "🚀 Starting development dependencies (PostgreSQL & Redis)..."
docker compose -f docker-compose.deps.yml up -d

echo "⏳ Waiting for services to be healthy..."
while ! docker compose -f docker-compose.deps.yml ps | grep -q "healthy"; do
    sleep 2
done

echo "✅ Dependencies are ready!"
echo ""
echo "🏃 You can now run your Kotlin application locally!"
echo "   ./gradlew run"
echo ""
echo "🔍 To view dependency logs: docker-compose logs -f"
echo "🛑 To stop dependencies: docker-compose down"
