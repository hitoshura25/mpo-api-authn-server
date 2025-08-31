# MPO WebAuthn Authentication Server

[![codecov](https://codecov.io/github/hitoshura25/mpo-api-authn-server/graph/badge.svg?token=G4WWCSG5KR)](https://codecov.io/github/hitoshura25/mpo-api-authn-server)

A WebAuthn (FIDO2/Passkeys) authentication server built with KTor, and comprehensive security testing.

## 🏗️ Multi-Module Project Structure

This project follows a multi-module architecture for clear separation of concerns:

- **webauthn-server/** - Main WebAuthn KTor server with production features
- **webauthn-test-credentials-service/** - HTTP service for cross-platform testing credentials
- **webauthn-test-lib/** - Shared WebAuthn test utilities library
- **android-test-client/** - Android E2E test client consuming published Android library
- **web-test-client/** - TypeScript E2E test client consuming published npm library
- **android-client-library/** - Dedicated Android client library submodule
- **typescript-client-library/** - Dedicated TypeScript client library submodule

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

# Android client tests (uses published library)
cd android-test-client && ./gradlew test

# Web TypeScript client tests (uses published library)
cd web-test-client
npm install
npm run build
npm test       # Run Playwright E2E tests

# Client library tests (submodules)
cd android-client-library && ./gradlew test
cd typescript-client-library && npm test
```

## 🌐 Port Assignments

- **WebAuthn Server**: 8080 (main API)
- **WebAuthn Test Service**: 8081 (cross-platform credential generation)
- **Web Test Client**: 8082 (TypeScript client with E2E tests)
- **PostgreSQL**: 5432
- **Redis**: 6379
- **Jaeger UI**: 16686

## 🔐 Security Features

### WebAuthn Security

- **WebAuthn 2.0/FIDO2** compliance using Yubico library
- **Username enumeration protection** - Authentication start doesn't reveal user existence
- **Replay attack prevention** - Challenge/response validation
- **Cross-origin protection** - Proper RP ID validation
- **Comprehensive vulnerability testing** - 7 security test categories

### 🤖 3-Tier AI Security Analysis System

Automatic security analysis on all pull requests with intelligent fallback strategy:

**Tier 1: Anthropic Official Security Action** (Primary)

- Uses official `anthropics/claude-code-security-review@v1` action
- Comprehensive security coverage maintained by Anthropic
- Broad attack pattern detection and analysis

**Tier 2: Gemini WebAuthn-Focused Analysis** (Fallback)

- Custom WebAuthn-specific security analysis using Gemini AI
- Focused on FIDO2/WebAuthn vulnerability patterns
- PoisonSeed attacks, username enumeration, credential tampering detection

**Tier 3: Template-Based Analysis** (Final Fallback)

- Zero-cost security pattern analysis
- Template-driven vulnerability detection
- Ensures security coverage even when AI providers unavailable

**Security Focus Areas**:

- PoisonSeed attack patterns (CVE-2024-39912)
- Username enumeration vulnerabilities
- Cross-origin authentication abuse
- Credential tampering and replay attacks
- Information leakage in error responses

**Automated Features**:

- 🚨 **Critical vulnerability blocking** - PRs with high security scores cannot merge
- 🏷️ **Automatic security labeling** - PRs tagged with analysis tier and risk level
- 💬 **Detailed security comments** - AI-generated analysis and recommendations
- 🧪 **Security test generation** - Automated test creation for discovered vulnerabilities

## 📱 Published Client Libraries

Use the WebAuthn API in your applications with automatically published client libraries featuring **Docker-inspired staging→production workflow**:

### Android Library

```gradle
repositories {
    maven {
        url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
        credentials {
            username = "YOUR_GITHUB_USERNAME"
            password = "YOUR_GITHUB_TOKEN"
        }
    }
}

dependencies {
    implementation 'io.github.hitoshura25:mpo-webauthn-android-client:1.0.26'
}
```

### TypeScript/npm Library

```bash
npm install @vmenon25/mpo-webauthn-client
```

### Client Library Architecture (Implemented)

**Staging→Production Workflow** (similar to Docker workflow):

1. **PR Testing**: Staging packages published to GitHub Packages (e.g., `pr-123.456`)
2. **E2E Validation**: Test clients consume staging packages for validation
3. **Production Publishing**: Successful main branch merges publish to npm + GitHub Packages
4. **GitHub Releases**: Automated release creation with usage examples

- **Production**: Published to npm and GitHub Packages on main branch merges
- **Staging**: Published to GitHub Packages for PR testing
- **Client Submodules**: Dedicated `android-client-library/` and `typescript-client-library/` submodules
- **Local Development**: Use published packages or generate with:
  ```bash
  # Generate and build clients in submodules
  ./gradlew generateAndroidClient copyAndroidClientToSubmodule
  ./gradlew generateTsClient copyTsClientToSubmodule
  ```

## 🧪 Testing Architecture

The project uses a **layered testing approach** with different access patterns:

### Testing Layers

1. **webauthn-test-lib** - Shared credential generation library
2. **webauthn-test-credentials-service** - HTTP API wrapper (port 8081)
3. **Integration tests** - Use shared library directly for performance

### Cross-Platform Testing Architecture

```bash
# Start test service for E2E testing
./gradlew :webauthn-test-credentials-service:run

# Test endpoints available at http://localhost:8081
# - POST /test/generate-registration-credential
# - POST /test/generate-authentication-credential
# - POST /test/clear
# - GET /test/sessions
```

**Testing Architecture Layers**:

- **Unit Tests**: Use shared `webauthn-test-lib` directly for performance
- **Integration Tests**: Server tests use in-memory test storage
- **E2E Tests**: Android and web clients consume published staging packages
- **Client Library Tests**: Independent testing of Android and TypeScript submodules
- **Production Validation**: Published packages undergo comprehensive E2E validation

## 📊 Monitoring & Observability

### Application Monitoring

- **OpenTelemetry** tracing with OTLP export
- **Micrometer** metrics with Prometheus export
- **Code coverage** reports with Kover

### 🔍 AI-Enhanced Security Monitoring

**Weekly Vulnerability Monitoring**:

- Automated WebAuthn vulnerability database scanning
- AI-enhanced risk assessment using Anthropic Claude
- Automatic security test generation and PR creation
- Complete test implementations (not just stubs)
- Library correlation analysis with java-webauthn-server

**Docker Security Scanning**:

- Multi-layer vulnerability detection (OS, dependencies, secrets)
- AI-powered vulnerability analysis and prioritization
- GitHub Security integration with SARIF reporting
- Automated security gate for DockerHub publishing

**Continuous Security Validation**:

- PR-triggered security analysis with 3-tier AI system
- Environment variable pattern security validation
- Automated security labeling and workflow management
- Real-time security feedback in pull request comments

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

- **[Library Usage Guide](docs/setup/library-usage.md)** - How to use published client libraries in your applications
- [Security Analysis](docs/security/webauthn-analysis.md) - Vulnerability testing details
- [Client Generation](docs/setup/client-generation.md) - Multi-platform client setup
- [GitHub Packages Setup](docs/setup/github-packages-setup.md) - Publishing configuration
- [MCP Development](docs/setup/mcp-development.md) - Claude Code integration

## 🚀 CI/CD Pipeline & Workflows

### 🔄 Intelligent Pipeline Architecture

The project uses a **smart CI/CD pipeline** with conditional execution and optimized resource usage:

**Main Orchestrator**: `main-ci-cd.yml`

- Orchestrates entire CI/CD pipeline using callable workflows
- Eliminates workflow dispatch complexity and 404 errors
- Conditional E2E test execution only when Docker images built

**Smart Change Detection**: `build-and-test.yml`

```
| Change Type        | Unit Tests | Docker Build | E2E Tests |
|--------------------|-----------|-------------|----------|
| Documentation only |  ❌ Skip  |   ❌ Skip   |  ❌ Skip  |
| Workflow changes   |  ❌ Skip  |   ❌ Skip   |  ❌ Skip  |
| Source code        |  ✅ Run   |   ✅ Build  |  ✅ Run   |
| Tests only         |  ✅ Run   |   ❌ Skip   |  ❌ Skip  |
| Dockerfile only    |  ❌ Skip  |   ✅ Build  |  ✅ Run   |
| Build config       |  ✅ Run   |   ✅ Build  |  ✅ Run   |
```

**Performance Benefits**:

- ⚡ **Fast path**: Documentation/workflow changes complete in ~30 seconds
- 🏃‍♂️ **Standard path**: Full CI pipeline ~8 minutes when needed
- 🎯 **Smart detection**: Only run tests/builds for relevant changes

**Cross-Platform E2E Testing**: `e2e-tests.yml`

- Docker Compose with real service dependencies
- Parallel Web (Playwright) and Android (connectedAndroidTest) testing
- Uses exact Docker images built for the PR
- Comprehensive integration validation

### 🔒 Security Automation Workflows

**3-Tier Security Analysis**: `security-analysis.yml`

- Triggered on security-sensitive file changes
- Intelligent tier selection with fallback strategy
- Automated security gates and PR labeling
- Complete security analysis consolidation

**Docker Security & Publishing**: `main-ci-cd.yml`

- AI-enhanced Docker vulnerability scanning
- Change detection to prevent unnecessary publishing
- Automated DockerHub publishing with security gates
- GHCR cleanup and git tagging on successful publish

**Vulnerability Monitoring**: `vulnerability-monitor.yml`

- Weekly WebAuthn vulnerability database scans
- AI-enhanced analysis and test generation
- Automated PR creation with complete test implementations
- Security label management and prioritization

### 🏗️ Environment Variable Management

**Centralized Configuration**:

```yaml
env:
  # Security Analysis Configuration
  HIGH_RISK_SCORE_THRESHOLD: 7.0
  ANTHROPIC_TIER_ENABLED: true
  GEMINI_TIER_ENABLED: true
  TEMPLATE_TIER_ENABLED: true

  # Docker Registry Configuration  
  DOCKER_REGISTRY: ghcr.io
  BASE_VERSION: "1.0"

  # Service Ports
  WEBAUTHN_SERVER_PORT: 8080
  TEST_CREDENTIALS_PORT: 8081
  WEB_CLIENT_PORT: 8082
```

**Security Best Practices**:

- Secure environment variable handling in all workflows
- Minimal required permissions per job
- Branch-specific caching strategies
- Encrypted secrets management

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

# Android client library (submodule)
cd android-client-library && ./gradlew test
cd android-client-library && ./gradlew publish

# TypeScript client library (submodule)
cd typescript-client-library && npm run build
cd typescript-client-library && npm test

# E2E test clients (consume published libraries)
cd android-test-client && ./gradlew connectedAndroidTest
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
Copyright 2025 Vinayak Menon

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
