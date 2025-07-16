# mpo-api-authn-server

[![codecov](https://codecov.io/gh/hitoshura25/mpo-api-authn-server/graph/badge.svg?token=DMqg4cl5Vq)](https://codecov.io/gh/hitoshura25/mpo-api-authn-server)

Server implementation for webauthn based on Yubico's java-webauthn-server

**Disclaimer**: Used GitHub Copilot agent mode along with various AI Models (Claude Sonnet, Gpt 4.1)

# Environment Variables

Setup the below in order to properly configure the app and dependencies:

### Database Configuration

```
MPO_AUTHN_DB_NAME
MPO_AUTHN_DB_USERNAME
MPO_AUTHN_DB_PASSWORD
MPO_AUTHN_DB_PORT
```

### Redis Configuration

```
MPO_AUTHN_REDIS_PASSWORD
MPO_AUTHN_REDIS_HOST
MPO_AUTHN_REDIS_PORT
```

### Application Configuration

```
MPO_AUTHN_APP_RELYING_PARTY_ID
MPO_AUTHN_APP_RELYING_PARTY_NAME

MPO_AUTHN_APP_PORT # Only used when running the full docker compose stack
```

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
./start-dev.sh # (or docker-compose -f docker-compose.deps.yml up -d)

# Run your application locally
./gradlew run

# Stop dependencies when done
docker-compose down
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
./start-full.sh # (or docker-compose -f docker-compose.yml up -d)

# Stop everything
docker-compose down
```
