# MPO WebAuthn Authentication Server

A production-ready WebAuthn (FIDO2/Passkeys) authentication server built with KTor and comprehensive security testing.

## 🏗️ Multi-Module Project Structure

This project follows a multi-module architecture for clear separation of concerns:

- **webauthn-server/** - Main WebAuthn KTor server with production features
- **webauthn-test-credentials-service/** - HTTP service for cross-platform testing credentials
- **webauthn-test-lib/** - Shared WebAuthn test utilities library
- **android-test-client/** - Android client with generated API library
- **web-test-client/** - TypeScript web client with automated OpenAPI client generation and webpack bundling

## 🚀 Quick Start

### Prerequisites

- Java 21+
- Docker & Docker Compose
- Node.js 18+ (for web client and tests)
- TypeScript 5.3+ (for web client development)

### Running the Server

```bash
# Start with Docker (recommended)
cd webauthn-server
./start-dev.sh

# Or run directly (requires local Redis/PostgreSQL)
./gradlew :webauthn-server:run
```

### Running Tests

```bash
# Server tests
./gradlew :webauthn-server:test

# Android client tests  
cd android-test-client && ./gradlew test

# Web TypeScript client tests (requires server running)
cd web-test-client
npm install
npm run build  # Build TypeScript client
npm test       # Run Playwright E2E tests
```

## 🌐 Port Assignments

- **WebAuthn Server**: 8080 (main API)
- **WebAuthn Test Service**: 8081 (cross-platform credential generation)
- **Web Test Client**: 8082 (TypeScript client with E2E tests)
- **PostgreSQL**: 5432
- **Redis**: 6379
- **Jaeger UI**: 16686

## 🔐 Security Features

- **WebAuthn 2.0/FIDO2** compliance using Yubico library
- **Username enumeration protection** - Authentication start doesn't reveal user existence
- **Replay attack prevention** - Challenge/response validation
- **Cross-origin protection** - Proper RP ID validation
- **Comprehensive vulnerability testing** - 7 security test categories

## 📱 Client Generation

Generate client libraries for multiple platforms:

```bash
# Generate Android client
./gradlew :webauthn-server:copyGeneratedClientToLibrary

# Generate TypeScript web client (automatically integrated)
cd web-test-client
# OpenAPI client auto-generated during build process

# Generate all clients (when implemented)
./gradlew :webauthn-server:generateAllClients
```

## 🧪 Testing Architecture

The project uses a **layered testing approach** with different access patterns:

### Testing Layers

1. **webauthn-test-lib** - Shared credential generation library
2. **webauthn-test-credentials-service** - HTTP API wrapper (port 8081)
3. **Integration tests** - Use shared library directly for performance

### Cross-Platform Testing

Start the test service for external clients:

```bash
# Start test service
./gradlew :webauthn-test-credentials-service:run

# Test endpoints available at http://localhost:8081
# - POST /test/generate-registration-credential
# - POST /test/generate-authentication-credential
# - POST /test/clear
# - GET /test/sessions
```

**Architecture Decisions**:

- **webauthn-server integration tests**: Use shared library directly for performance and reliability
- **Android client tests**: Use HTTP API calls to webauthn-test-credentials-service for realistic cross-platform testing
- **TypeScript web client**: Uses generated OpenAPI client with automated build process and UMD bundling for browser compatibility

## 📊 Monitoring & Observability

- **OpenTelemetry** tracing with OTLP export
- **Micrometer** metrics with Prometheus export
- **Automated vulnerability monitoring** - Weekly scans with PR generation
- **Code coverage** reports with Kover

## 🏛️ Architecture

### Storage

- **PostgreSQL** - Credential storage with quantum-safe encryption
- **Redis** - Session and challenge storage
- **HikariCP** - Connection pooling
- **Flyway** - Database migrations

### Security

- **Post-quantum cryptography** preparation with BouncyCastle
- **Koin** dependency injection for testability
- **CBOR** encoding for WebAuthn data structures

### API

- **OpenAPI 3.0** specification with Swagger UI
- **Jackson** JSON processing with Kotlin support
- **CORS** configuration for web clients
- **Generated TypeScript clients** with automated OpenAPI synchronization

## 📚 Documentation

- [Security Analysis](WEBAUTHN_SECURITY_ANALYSIS.md) - Vulnerability testing details
- [Client Generation](CLIENT_GENERATION.md) - Multi-platform client setup
- [MCP Development](MCP_DEVELOPMENT_GUIDE.md) - Claude Code integration
- [GitHub Packages](GITHUB_PACKAGES_SETUP.md) - Publishing setup

## 🛠️ Development

### Module Commands

```bash
# Main server
./gradlew :webauthn-server:test
./gradlew :webauthn-server:run
./gradlew :webauthn-server:koverHtmlReport

# Test service  
./gradlew :webauthn-test-credentials-service:build
./gradlew :webauthn-test-credentials-service:run

# Shared test library
./gradlew :webauthn-test-lib:build

# Android client
cd android-test-client && ./gradlew test
cd android-test-client && ./gradlew client-library:publish

# TypeScript web client
cd web-test-client && npm run build
cd web-test-client && npm test
```

### Docker Development

```bash
# Start all dependencies
cd webauthn-server  
./start-dev.sh

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🤝 Contributing

1. Follow security-first development practices
2. All WebAuthn changes require security test coverage
3. Use `git mv` for file moves to preserve history
4. Generate clients after API changes
5. Update documentation for structural changes

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

```
Copyright 2024 Vinayak Menon

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
