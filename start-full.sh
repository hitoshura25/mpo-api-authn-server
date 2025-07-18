#!/bin/bash

# Full stack setup - Start everything including the application
echo "🚀 Starting full stack (PostgreSQL, Redis & WebAuthn Server)..."
docker-compose up --build -d

echo "⏳ Waiting for all services to be healthy..."
sleep 10

echo "✅ Full stack is ready!"
echo ""
echo "🔍 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"
