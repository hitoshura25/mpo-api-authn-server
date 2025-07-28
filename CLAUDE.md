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
- **Username enumeration** (CVE-2024-39912) - Authentication start does NOT reveal user existence
- **Replay attacks** - Challenge/response reuse
- **Credential tampering** - Signature validation

### Security Design Decisions

**Authentication Start Behavior**: The `/authenticate/start` endpoint returns a valid challenge for both existing and non-existent users. This prevents username enumeration attacks by not revealing whether a username is registered. Authentication failure occurs later during credential verification, maintaining user privacy.

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

## Development Guidance & Lessons Learned

### User-Guided Implementation Approach
This project development followed a collaborative approach with continuous user guidance:

- **Iterative Refinement**: User provided specific corrections throughout implementation
- **Real-World Testing**: User insisted on actually testing scripts before claiming completion
- **Practical Focus**: User steered away from mock implementations toward real functionality
- **Security-First Mindset**: User emphasized comprehensive security testing and monitoring

### Key Implementation Lessons

#### 1. **Testing Philosophy**
- Always test scripts/functionality before claiming they work
- User preference: "Can we try actually running the scripts to make sure before we say it is complete?"
- ES module compatibility issues revealed through actual execution

#### 2. **Documentation vs Implementation**
- User correctly identified when documentation was outdated vs actual code state
- WEBAUTHN_SECURITY_ANALYSIS.md required updates when tests started passing
- README.md vs CLAUDE.md content organization improvements

#### 3. **Real vs Mock Implementation**
- User consistently pushed for actual implementations over mocks:
  - "We are currently mocking the checkCVEDatabase... Can you implement the actual logic"
  - "The checkFIDOAllianceNotices method is still mocked, can we implement the actual logic"
  - "The logic for createPullRequest is still mocked, is it feasible to implement the actual logic?"

#### 4. **Dependency-Focused Security Strategy**
- User insight: Since we use Yubico's own library, focus on dependency updates rather than generic advisories
- "Should we alter the check logic to see if the Yubico server library has already addressed it?"
- Correlation between vulnerabilities and library fixes became the key pattern

#### 5. **Test Simplification**
- User rejected complex nested test class generation: "let's just stick with a standard function for each test case"
- Preference for simple, readable test structures over over-engineered solutions

#### 6. **Practical Git Workflow**
- Pull request creation testing should happen in CI environment, not locally with uncommitted changes
- User understanding: "This is something that will be run as part of the github workflow... it may not be feasible to actually test for the pull request creation at this point"

#### 7. **Android Client Generation & Publishing**
- **Problem**: The initial publish workflow tried to embed complex Gradle syntax in YAML causing parsing errors
- **Solution**: Restructured to generate client directly into android-test-client library module
- **Key Insight**: "The whole point is using the client generated code, if we have to manually update it every time then that is an issue"
- **Approach**: Configure OpenAPI generation correctly rather than post-process generated code
- **Dependencies**: Android requires specific annotation libraries (JSR305 + javax.annotation-api) for generated code
- **Build Consistency**: User feedback: "Let's consistently use kts for the build scripts" - prefer Kotlin DSL throughout

#### 8. **OpenAPI Client Integration Challenges**
- **Annotation Compatibility**: Generated Java code uses javax.annotation which isn't available by default in Android
- **Testing Validation**: User insisted on actually running tests: "Please ensure that we can run the test with the generated client code"
- **Method Name Mismatches**: API methods may differ from expected names (e.g., `getHealth()` vs `healthCheck()`)
- **Enum Handling**: Generated enums require proper comparison (e.g., `status.toString() == "healthy"`)

### Code Quality Preferences
- **Self-Documenting Code**: "Going forward I prefer self-documentation of code versus explicit comments if possible"
- **Functional over Complex**: Simple functions preferred over nested class hierarchies
- **Real Integration**: Actual API calls and git operations over mocked behaviors
- **Build Consistency**: Kotlin DSL (.kts) preferred over Groovy for all build scripts ✅ Completed
- **Generated Code Integrity**: Never manually modify generated code; fix generation configuration instead

### Security Implementation Patterns
- **Comprehensive Coverage**: All 4 major WebAuthn vulnerabilities now have test coverage
- **Automated Monitoring**: Weekly vulnerability scanning with PR generation
- **Correlation Logic**: Link vulnerabilities to actionable dependency updates
- **Production Ready**: 7/7 security tests passing, 100% coverage achieved

### Android Client Publishing Architecture
- **Structure**: Main project generates → android-test-client/client-library → GitHub Packages
- **Workflow**: `./gradlew copyGeneratedClientToLibrary` → `./gradlew client-library:publish`
- **Testing**: Both unit and instrumentation tests validate generated client integration
- **Versioning**: PR-aware versioning (1.0.0-pr-123.1) for safe testing of API changes
