# WebAuthn KTor Server - Claude Memory

## Project Overview

This is a KTor-based WebAuthn authentication server using the Yubico java-webauthn-server library for FIDO2/WebAuthn
implementation.

## Key Technologies

- **Framework**: KTor (Kotlin web framework)
- **WebAuthn Library**: Yubico java-webauthn-server
- **Storage**: PostgreSQL (credentials), Redis (sessions)
- **DI**: Koin dependency injection
- **Testing**: JUnit 5, Kotlin Test
- **Build**: Gradle with Kotlin DSL
- **Containerization**: Docker with docker-compose

## Development Commands

- **Tests**: `./gradlew test`
- **Build**: `./gradlew build`
- **Run**: `./gradlew run` or `./start-dev.sh`
- **Verification**: `./gradlew check` (runs all checks including tests)
- **Coverage Report**: `./gradlew koverHtmlReport` (generates HTML coverage report)

## Project Structure

- `src/main/kotlin/com/vmenon/mpo/api/authn/` - Main application code
    - `routes/` - HTTP endpoint handlers
    - `storage/` - Data persistence layer
    - `security/` - Security-related services
    - `yubico/` - WebAuthn implementation using Yubico library
- `src/test/kotlin/` - Test suites
    - `security/VulnerabilityProtectionTest.kt` - Comprehensive security validation

## Security Focus

This project emphasizes security testing and vulnerability protection:

- **PoisonSeed attacks** - Cross-origin authentication abuse
- **Username enumeration** (CVE-2024-39912)
- **Replay attacks** - Challenge/response reuse
- **Credential tampering** - Signature validation

## MCP Integration

- **Configuration**: `claude_config.json` with webauthn-dev-tools server
- **MCP Server**: `dev-tools-mcp-server.js` for development tools
- **Setup**: Run `./setup-dev-tools.sh` to install dependencies

## Important Notes

- Always run security tests before deployment
- The Yubico library handles most WebAuthn security automatically
- Use `testStorageModule` for integration tests (in-memory storage)
- Use `storageModule` for real container-based testing

## JSON Structure Gotcha

WebAuthn responses have nested structure requiring `.get("publicKey")` access:

```kotlin
// Correct
val challenge = response.get("publicKeyCredentialRequestOptions")
    ?.get("publicKey")?.get("challenge")?.asText()
```

## Testing Strategy

- **VulnerabilityProtectionTest**: Comprehensive security validation (7 tests)
- **Integration tests**: Use BaseIntegrationTest with real containers
- **Unit tests**: Mock dependencies with testStorageModule
- **WebAuthnTestHelpers**: Shared test utilities for registration/authentication flows

## Test Utilities

Use `WebAuthnTestHelpers` for common WebAuthn operations:

- `registerUser(client, username, displayName, keyPair)` - Complete registration
- `authenticateUser(client, username, keyPair)` - Complete authentication
- `startRegistration/completeRegistration` - Individual steps
- `startAuthentication/completeAuthentication` - Individual steps
- `generateTestUsername(prefix)` - Unique test usernames
- `generateTestKeypair()` - Test key pairs
- `extractChallenge/extractRequestId` - JSON parsing helpers
- `createTamperedCredentialWithOrigin` - Security testing helpers

## Vulnerability Monitoring

- **Monitor Script**: `node scripts/vulnerability-monitor.js` ✅ Working
- **GitHub Action**: Runs weekly, creates PRs for new vulnerabilities
- **Manual Check**: `npm run monitor` ✅ Working
- **Setup**: `./scripts/setup-vulnerability-monitoring.sh` ✅ Working
- **Pre-commit Hook**: Runs security tests before commits ✅ Active
- **Tracking File**: `vulnerability-tracking.json` (4 vulnerabilities, 100% coverage)
- **Test Coverage**: All known WebAuthn vulnerabilities have protection tests
