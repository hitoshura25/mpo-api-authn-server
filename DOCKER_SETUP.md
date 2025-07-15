# Docker Setup Guide

This project supports two different Docker setups to accommodate different development workflows.

## 🔧 Development Mode (Recommended for active development)

**Use this when:** You're actively coding and want fast iteration cycles.

**What it does:** Starts only the dependencies (PostgreSQL & Redis) in Docker containers while you run your Kotlin
application locally.

**Benefits:**

- Faster development cycle (no Docker rebuilds)
- Better debugging capabilities
- IDE integration works seamlessly
- Easier testing and hot reloading

### Usage:

```bash
# Start dependencies only
./start-dev.sh

# Run your application locally
./gradlew run

# Stop dependencies when done
./stop-dev.sh
```

### Manual commands:

```bash
# Start dependencies
docker-compose -f docker-compose.deps.yml up -d

# Stop dependencies
docker-compose -f docker-compose.deps.yml down
```

## 🌐 Full Stack Mode (For demos, integration testing, production)

**Use this when:** You want to showcase the complete system, run integration tests, or deploy everything together.

**What it does:** Starts PostgreSQL, Redis, AND your WebAuthn server application in Docker containers.

**Benefits:**

- Complete environment isolation
- Perfect for demos and presentations
- Great for integration testing
- Production-like setup

### Usage:

```bash
# Start everything
./start-full.sh

# Stop everything
docker-compose down
```

### Manual commands:

```bash
# Start full stack
docker-compose up -d

# View logs
docker-compose logs -f

# Stop full stack
docker-compose down
```

## 📋 Connection Details

### PostgreSQL

- **Host:** localhost
- **Port:** 5432
- **Database:** webauthn
- **Username:** webauthn_user
- **Password:** webauthn_password

### Redis

- **Host:** localhost
- **Port:** 6379
- **Password:** webauthn_password

### WebAuthn Server (Full Stack Mode)

- **URL:** http://localhost:8080

## 🧪 For Testing

- **Unit tests:** Use development mode with local app
- **Integration tests:** Use full stack mode with all services containerized
- **End-to-end tests:** Use full stack mode for realistic environment

## 📁 Files Overview

- `docker-compose.yml` - Full stack (includes your app)
- `docker-compose.deps.yml` - Dependencies only
- `Dockerfile` - Your application container definition
- `start-dev.sh` - Helper script for development mode
- `start-full.sh` - Helper script for full stack mode
- `stop-dev.sh` - Helper script to stop development dependencies
