# mpo-api-authn-server

[![codecov](https://codecov.io/gh/hitoshura25/mpo-api-authn-server/graph/badge.svg?token=DMqg4cl5Vq)](https://codecov.io/gh/hitoshura25/mpo-api-authn-server)

Server implementation for webauthn based on Yubico's java-webauthn-server

**Disclaimer**: Used GitHub Copilot agent mode along with various AI Models (Claude Sonnet, Gpt 4.1)

# Environment Variables

Setup the below in order to properly configure the app and dependencies:

### Database Configuration

```
MPO_AUTHN_DB_HOST
MPO_AUTHN_DB_PORT
MPO_AUTHN_DB_NAME
MPO_AUTHN_DB_USERNAME
MPO_AUTHN_DB_PASSWORD
```

### Redis Configuration

```
MPO_AUTHN_REDIS_HOST
MPO_AUTHN_REDIS_PORT
MPO_AUTHN_REDIS_PASSWORD
```

### Application Configuration

```
MPO_AUTHN_APP_RELYING_PARTY_ID
MPO_AUTHN_APP_RELYING_PARTY_NAME

 # Only used when running the full docker compose stack
MPO_AUTHN_APP_PORT
MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT # If not setup, OpenTelemetry.noop() will be used
MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME
```

See [Docker Setup Guide for an example](#example-env)

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

## Example .env

Below is an example .env file that can be used with the docker-compose setup:

```
# Database Configuration
MPO_AUTHN_DB_NAME=webauthn
MPO_AUTHN_DB_USERNAME=webauthn_user
MPO_AUTHN_DB_PASSWORD=<password>
MPO_AUTHN_DB_PORT=5432
MPO_AUTHN_DB_HOST=postgres

# Redis Configuration
MPO_AUTHN_REDIS_PASSWORD=<password>
MPO_AUTHN_REDIS_HOST=redis
MPO_AUTHN_REDIS_PORT=6379

# Application Configuration
MPO_AUTHN_APP_PORT=8080
MPO_AUTHN_APP_RELYING_PARTY_ID=webauthn.mpo.io
MPO_AUTHN_APP_RELYING_PARTY_NAME=MPO Api Authn

MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME=mpo-authn-server
MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT=http://jaeger:4317
```
