# WebAuthn KTor Server

[![codecov](https://codecov.io/gh/hitoshura25/mpo-api-authn-server/graph/badge.svg?token=DMqg4cl5Vq)](https://codecov.io/gh/hitoshura25/mpo-api-authn-server)

A production-ready WebAuthn authentication server built with KTor and the Yubico java-webauthn-server library, featuring comprehensive security vulnerability protection and automated monitoring.

**Disclaimer**: Used GitHub Copilot agent mode along with various AI Models (Claude Sonnet, Gpt 4.1)

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd mpo-api-authn-server

# Start dependencies (PostgreSQL & Redis)
./start-dev.sh

# Run tests
./gradlew test

# Start the server
./gradlew run
```

## 🛡️ Security Features

This server provides **enterprise-grade security** with protection against:

- ✅ **PoisonSeed attacks** - Cross-origin authentication abuse
- ✅ **Username enumeration** (CVE-2024-39912) - Prevents user discovery
- ✅ **Replay attacks** - Challenge/response reuse prevention
- ✅ **Credential tampering** - Cryptographic signature validation
- ✅ **Automated vulnerability monitoring** - Weekly security checks with PR generation

**Security Status**: 🛡️ **Production Ready** (7/7 security tests passing, 100% coverage)

## 🏗️ Technology Stack

- **Framework**: KTor (Kotlin web framework)
- **WebAuthn Library**: Yubico java-webauthn-server (industry standard)
- **Storage**: PostgreSQL (credentials), Redis (sessions)
- **Testing**: JUnit 5, Kotlin Test, Testcontainers
- **Build**: Gradle with Kotlin DSL
- **Monitoring**: OpenTelemetry, Micrometer, Jaeger
- **Security**: Automated vulnerability monitoring & testing

## 📋 Development Commands

```bash
# Testing
./gradlew test                           # Run all tests
./gradlew test --tests="*Vulnerability*" # Run security tests only
./gradlew koverHtmlReport               # Generate coverage report

# Building & Running
./gradlew build                         # Build the project
./gradlew run                          # Run locally
./gradlew check                        # Run all verification checks

# Security Monitoring
npm run monitor                        # Check for new vulnerabilities
./scripts/setup-vulnerability-monitoring.sh  # Setup monitoring system
```

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

## 🧪 Testing

### Security Testing
The project includes comprehensive security testing with protection against known vulnerabilities:

```bash
# Run all security tests
./gradlew test --tests="*VulnerabilityProtectionTest*"

# View security analysis
cat WEBAUTHN_SECURITY_ANALYSIS.md
```

### End-to-End Testing
```bash
cd test-client
npm install -g playwright
npm install
npm run test:with-server:report
```

### Test Utilities
The project provides `WebAuthnTestHelpers` for easy test development:
- `registerUser()` / `authenticateUser()` - Complete flows
- `startRegistration()` / `completeRegistration()` - Individual steps
- `generateTestKeypair()` / `generateTestUsername()` - Test data
- Security testing helpers for tampered credentials

## 📁 Project Structure

```
src/main/kotlin/com/vmenon/mpo/api/authn/
├── routes/           # HTTP endpoint handlers
├── storage/          # Data persistence layer
├── security/         # Security services & quantum-safe crypto
├── yubico/          # WebAuthn implementation
└── monitoring/      # OpenTelemetry tracing

src/test/kotlin/
├── security/        # Security vulnerability tests
├── test_utils/      # Shared testing utilities
└── ...             # Integration & unit tests
```

## 🔐 Automated Security Monitoring

This project includes an automated vulnerability monitoring system that:

- **Monitors CVE databases** for new WebAuthn vulnerabilities
- **Tracks security advisories** from Yubico and FIDO Alliance  
- **Auto-generates test stubs** for newly discovered vulnerabilities
- **Creates pull requests** for security team review
- **Runs weekly via GitHub Actions** with zero maintenance

### Setup & Usage

```bash
# One-time setup
./scripts/setup-vulnerability-monitoring.sh

# Manual vulnerability check
npm run monitor

# View current security status
cat vulnerability-tracking.json
```

### Current Security Coverage
- **4 vulnerabilities tracked** with 100% test coverage
- **7 security tests** running on every commit via pre-commit hooks
- **Production-ready** security validation

## 📦 GitHub Packages Integration

Automated client library publishing with PR-aware versioning:

```bash
# Setup local access to published packages
./scripts/setup-github-packages.sh

# Published automatically on API changes:
# - Main branch: com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0
# - PR branches: com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0-pr-123.1
# - Feature branches: com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0-develop.15
```

**Features:**
- 🔄 **Automatic publishing** when OpenAPI specs change
- 🏷️ **PR-aware versioning** for safe testing of API changes  
- 💬 **GitHub bot comments** with usage instructions on PRs
- 🔐 **Secure GitHub Packages** integration
- 📱 **Android test client** auto-updates to use latest versions

See [GITHUB_PACKAGES_SETUP.md](GITHUB_PACKAGES_SETUP.md) for complete setup guide.

## 🤖 MCP Integration

Model Context Protocol integration for AI-assisted development:

```bash
# Setup MCP tools
./setup-dev-tools.sh

# Claude Code integration via claude_config.json
# Provides AI assistance for WebAuthn development
```

# Running in Intellij Guide

The environment variable values used for the dependency hosts (i.e. postgres, redis, jaeger, etc) may need to be updated
when the Application is run from within Intellij. One approach is starting up the dependency docker-compose env as
mentioned in the [Development Mode section](#-development-mode-recommended-for-active-development) and using
the [EnvFile plugin](https://plugins.jetbrains.com/plugin/7861-envfile).
Below is an example ide.env file that can be used:

```
MPO_AUTHN_DB_NAME=webauthn
MPO_AUTHN_DB_USERNAME=webauthn_user
MPO_AUTHN_DB_PASSWORD=<password>
MPO_AUTHN_DB_PORT=5432
MPO_AUTHN_DB_HOST=localhost


MPO_AUTHN_REDIS_PASSWORD=<pasword>
MPO_AUTHN_REDIS_HOST=localhost
MPO_AUTHN_REDIS_PORT=6379

# Application Configuration
MPO_AUTHN_APP_PORT=8080
MPO_AUTHN_APP_RELYING_PARTY_ID=webauthn.mpo.io
MPO_AUTHN_APP_RELYING_PARTY_NAME=MPO Api Authn

MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME=mpo-authn-server
MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT=http://localhost:4317
```