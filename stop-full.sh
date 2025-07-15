#!/bin/bash

# Stop all services
echo "🛑 Stopping all services..."
docker-compose -f docker-compose.yml down

echo "✅ All services stopped!"
