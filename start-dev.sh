#!/bin/bash

# Development setup - Start only dependencies (PostgreSQL & Redis)
echo "🚀 Starting development dependencies (PostgreSQL & Redis)..."
docker-compose -f docker-compose.deps.yml up -d

echo "⏳ Waiting for services to be healthy..."
while ! docker-compose -f docker-compose.deps.yml ps | grep -q "healthy"; do
    sleep 2
done

echo "✅ Dependencies are ready!"
echo ""
echo "📝 Connection details:"
echo "  PostgreSQL: localhost:5432"
echo "  Database: webauthn"
echo "  User: webauthn_user"
echo "  Password: webauthn_password"
echo ""
echo "  Redis: localhost:6379"
echo "  Password: webauthn_password"
echo ""
echo "🏃 You can now run your Kotlin application locally!"
echo "   ./gradlew run"
