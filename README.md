# MPO WebAuthn Authentication Server

A production-ready WebAuthn (FIDO2/Passkeys) authentication server built with KTor and comprehensive security testing.

## 🏗️ Multi-Module Project Structure

This project follows a multi-module architecture for clear separation of concerns:

- **webauthn-server/** - Main WebAuthn KTor server with production features
- **webauthn-test-service/** - HTTP service for cross-platform testing credentials  
- **android-test-client/** - Android client with generated API library
- **test-client/** - Web-based Playwright E2E tests

## 🚀 Quick Start

### Prerequisites
- Java 17+
- Docker & Docker Compose
- Node.js 18+ (for web tests)

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
./gradlew :android-test-client:app:test

# Web E2E tests (requires server running)
cd test-client
npm install
npm test
```

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

# Generate all clients (when implemented)
./gradlew :webauthn-server:generateAllClients
```

## 🧪 Cross-Platform Testing

The project includes a dedicated test service for generating WebAuthn credentials across platforms:

```bash
# Start test service
./gradlew :webauthn-test-service:run

# Test endpoints available at http://localhost:8081
# - POST /test/generate-registration-credential
# - POST /test/generate-authentication-credential
```

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
./gradlew :webauthn-test-service:build
./gradlew :webauthn-test-service:run

# Android client
./gradlew :android-test-client:app:test
./gradlew :android-test-client:client-library:publish
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

[Add your license here]