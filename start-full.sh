#!/bin/bash

# Full stack setup - Start everything including the application
echo "🚀 Starting full stack (PostgreSQL, Redis & WebAuthn Server)..."
docker-compose up -d

echo "⏳ Waiting for all services to be healthy..."
sleep 10

echo "✅ Full stack is ready!"
echo ""
echo "📝 Services running:"
echo "  WebAuthn Server: http://localhost:8080"
echo "  PostgreSQL: localhost:5432"
echo "  Redis: localhost:6379"
echo ""
echo "🔍 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"
