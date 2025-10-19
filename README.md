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

## 🤖 For AI Agents & Developers

**Quick Integration**: Looking to add WebAuthn authentication to your project? Check out [`.ai-agents.json`](./.ai-agents.json) for complete Docker setup configuration.

**Docker Image**: `hitoshura25/webauthn-server:latest` (Docker Hub - Multi-platform: linux/amd64, linux/arm64)

### Example AI Agent Prompt

```
Add hitoshura25/webauthn-server to my docker-compose.yml using the configuration from:
https://raw.githubusercontent.com/hitoshura25/mpo-api-authn-server/main/.ai-agents.json
```

This structured configuration file contains:
- Complete environment variable documentation with defaults
- PostgreSQL and Redis dependency configurations
- Health check setup and deployment requirements
- Ready-to-use docker-compose.yml template
- Security considerations and critical configuration notes

## 🚀 Quick Start

### Prerequisites

- **Java 21** - Required for Kotlin JVM target
- **Docker & Docker Compose** - For containerized PostgreSQL, Redis, and Jaeger
- **Node.js 18+** - For web client and TypeScript tests
- **TypeScript 5.3+** - For web client development

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

### Zero-Trust JWT Authentication

After successful WebAuthn authentication, the server issues JWT tokens for zero-trust architecture:

- **RS256 Asymmetric Signing** - 2048-bit RSA key pairs for secure token signing
- **15-Minute Token Expiration** - Short-lived tokens (900 seconds) for enhanced security
- **Public Key Export** - `/public-key` endpoint for downstream service verification
- **Bearer Token Format** - Standard OAuth2-compatible JWT tokens
- **No Session State** - Stateless authentication for distributed systems

#### JWT Token Response

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 900,
  "username": "user@example.com"
}
```

#### Downstream Service Verification

Downstream services can verify JWT signatures using the public key:

```bash
# Get the public key
curl http://webauthn-server:8080/public-key
```

**Example verification (Python)**:
```python
import httpx
import base64
from cryptography.hazmat.primitives.serialization import load_der_public_key
import jwt

# Fetch and cache public key
response = httpx.get("http://webauthn-server:8080/public-key")
public_key = load_der_public_key(base64.b64decode(response.text))

# Verify JWT token
decoded = jwt.decode(token, public_key, algorithms=["RS256"], issuer="mpo-webauthn")
username = decoded["sub"]
```

**Example verification (TypeScript)**:
```typescript
import * as jose from 'jose'

// Fetch and cache public key
const response = await fetch('http://webauthn-server:8080/public-key')
const publicKeyDer = await response.text()
const publicKey = await jose.importSPKI(
  `-----BEGIN PUBLIC KEY-----\n${publicKeyDer}\n-----END PUBLIC KEY-----`,
  'RS256'
)

// Verify JWT token
const { payload } = await jose.jwtVerify(token, publicKey, {
  issuer: 'mpo-webauthn'
})
const username = payload.sub
```

### 🛡️ Professional FOSS Security Implementation

Comprehensive security analysis using 8 professional FOSS tools with GitHub Security integration:

**Core Security Tools**:

- **Trivy** - Container vulnerability scanning with secrets detection
- **Semgrep** - Static Application Security Testing (SAST) with custom WebAuthn rules
- **GitLeaks** - Git history secrets detection and remediation
- **OSV-Scanner** - Open source vulnerability database scanning
- **Checkov** - Infrastructure as Code (IaC) security validation
- **OWASP ZAP** - Dynamic Application Security Testing (DAST) during E2E tests
- **Dependabot** - Automated dependency security updates
- **Gradle Dependency Locking** - Build reproducibility and tamper detection

**Performance Optimized Architecture**:

- **75% scan reduction** - Optimized Trivy implementation (2 scans instead of 8)
- **SARIF-only processing** - Unified reporting format for GitHub Security tab
- **Smart change detection** - Conditional execution based on file change patterns
- **Parallel execution** - Multiple security tools run simultaneously

**Security Focus Areas**:

- PoisonSeed attack patterns (CVE-2024-39912)
- Username enumeration vulnerabilities
- Cross-origin authentication abuse
- Credential tampering and replay attacks
- Information leakage in error responses
- Container and infrastructure security
- Supply chain security with dependency validation

**Automated Features**:

- 🚨 **Critical vulnerability blocking** - PRs with CRITICAL findings cannot merge
- 📊 **GitHub Security integration** - SARIF results in Security tab
- 💬 **Unified security dashboard** - Consolidated findings from all 8 tools
- 🔄 **Automated remediation** - Dependabot PRs for security updates
- ⚡ **Zero AI API costs** - Professional FOSS tools eliminate external dependencies

## 🤖 AI Security Dataset Research Initiative

**Transforming real-world security vulnerabilities into valuable AI research contributions for improved security remediation.**

### 🎯 Core Innovation

This project extends beyond traditional WebAuthn authentication to contribute to **AI safety and security research**. We leverage our comprehensive security findings to improve how AI models generate actionable security fixes, specifically targeting the OLMo model ecosystem.

**Key Research Components:**

- **🔍 Real Vulnerability Dataset**: 440+ vulnerabilities from 8 professional security tools
- **🧠 Local OLMo-2-1B Analysis**: MLX-optimized model with 214.6 tokens/sec performance (20-30X faster)
- **🚀 Local Automated Pipeline**: Replaced GitHub Actions with continuous macOS daemon for better reliability
- **📊 HuggingFace Integration**: Open source dataset sharing for research community
- **🍎 Apple Silicon Optimization**: Advanced MLX framework integration for M-series processors

### 📈 Research Impact

- **Problem Solved**: Replace vague AI security advice with specific, actionable fixes
- **Performance**: 20-30X faster inference through Apple Silicon MLX optimization
- **Scale**: Processing hundreds of real vulnerabilities continuously
- **Open Science**: Published production dataset at [HuggingFace Hub](https://huggingface.co/datasets/hitoshura25/webauthn-security-vulnerabilities-olmo)

### 🔗 Research Resources

- **📖 Complete Documentation**: [AI Security Dataset Research Guide](docs/improvements/completed/ai-security-dataset-research.md)
- **⚙️ Developer Setup**: [Local OLMo Analysis Setup Guide](docs/development/local-olmo-analysis-setup.md)
- **🏃‍♂️ System Status**: LaunchAgent running continuously (PID 79249) for automated processing

**This initiative demonstrates how production security systems can contribute to advancing AI safety and security research through automated vulnerability analysis and open dataset generation.**

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

### 🔍 Automated Security Monitoring

**Weekly Vulnerability Monitoring**:

- Automated WebAuthn vulnerability database scanning via OSV-Scanner
- GitHub Security Advisory integration for risk assessment
- Automated security test generation and PR creation with complete implementations
- Dependency correlation analysis with java-webauthn-server library

**Docker Security Scanning**:

- Multi-layer vulnerability detection (OS packages, application dependencies, secrets)
- SARIF-based vulnerability reporting and prioritization
- GitHub Security tab integration for centralized monitoring
- Automated security gate blocking Docker publishing on critical vulnerabilities

**Continuous Security Validation**:

- PR-triggered security analysis using professional FOSS tool suite
- Environment variable pattern security validation via GitLeaks
- Automated security labeling and workflow management
- Real-time security feedback via unified dashboard in pull request comments

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

**Multi-Tool Security Analysis**: Parallel execution of specialized FOSS tools

- **docker-security-scan.yml** - Trivy container vulnerability and secrets scanning
- **semgrep-sast.yml** - Static application security testing with custom WebAuthn rules
- **secrets-scan.yml** - GitLeaks git history secrets detection
- **osv-scanner.yml** - Open source vulnerability database scanning
- **iac-scan.yml** - Checkov infrastructure as code security validation

**OWASP ZAP Integration**: `e2e-tests.yml`

- Dynamic application security testing during E2E test execution
- Live application vulnerability scanning with real authentication flows
- SARIF integration for GitHub Security tab reporting

**Unified Security Dashboard**: `main-ci-cd.yml`

- Consolidated reporting from all 8 security tools
- SARIF-based findings aggregation and GitHub Security integration
- Automated critical vulnerability blocking for production deployments
- Performance optimized with smart change detection and parallel execution

### 🏗️ Environment Variable Management

**Centralized Configuration**:

```yaml
env:
  # Security Scanning Configuration
  TRIVY_SCAN_TIMEOUT: 300
  SEMGREP_TIMEOUT: 300
  CRITICAL_CVE_THRESHOLD: 9.0

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

### Multi-Platform Docker Support

All Docker images are built for multiple architectures:

- **linux/amd64** - x86_64 systems (GitHub Actions runners, Intel/AMD servers)
- **linux/arm64** - ARM64 systems (Apple Silicon, ARM servers, Raspberry Pi)

Docker will automatically pull the correct architecture for your platform. No special configuration needed!

```bash
# Works on any platform - Docker handles architecture selection
docker pull hitoshura25/webauthn-server:latest
docker run -p 8080:8080 hitoshura25/webauthn-server:latest
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
