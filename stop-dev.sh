#!/bin/bash

# Stop development dependencies
echo "🛑 Stopping development dependencies..."
docker-compose -f docker-compose.deps.yml down

echo "✅ Development dependencies stopped!"
