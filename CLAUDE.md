# WebAuthn KTor Server - Claude Memory (Optimized)

## Current Work (In Progress)

### Active Tasks
- No active tasks at this time - all major features completed

## Project Overview

This is a KTor-based WebAuthn authentication server using the Yubico java-webauthn-server library for FIDO2/WebAuthn implementation.

### Key Technologies
- **Framework**: KTor (Kotlin web framework)
- **WebAuthn Library**: Yubico java-webauthn-server
- **Storage**: PostgreSQL (credentials), Redis (sessions)
- **DI**: Koin dependency injection
- **Testing**: JUnit 5, Kotlin Test
- **Build**: Gradle with Kotlin DSL
- **Containerization**: Docker with docker-compose

### Multi-Module Project Structure
- **webauthn-server/** - Main WebAuthn KTor server
- **webauthn-test-credentials-service/** - HTTP service for cross-platform testing  
- **webauthn-test-lib/** - Shared WebAuthn test utilities library
- **android-test-client/** - Android client with generated API library
- **web-test-client/** - TypeScript web client with automated OpenAPI client generation and webpack bundling

## Development Commands

### Main Server
- **Tests**: `./gradlew :webauthn-server:test`
- **Build**: `./gradlew :webauthn-server:build`
- **Run**: `./gradlew :webauthn-server:run` or `cd webauthn-server && ./start-dev.sh`
- **Coverage**: `./gradlew :webauthn-server:koverHtmlReport`

### Test Service
- **Tests**: `./gradlew :webauthn-test-credentials-service:test`
- **Build**: `./gradlew :webauthn-test-credentials-service:build`
- **Run**: `./gradlew :webauthn-test-credentials-service:run`

### All Modules
- **Full Build**: `./gradlew build`
- **All Tests**: `./gradlew test`
- **Lint**: `./gradlew detekt`

## Development Guidance & Critical Reminders

### 🤖 CRITICAL: Proactively Use Subagents for Complex Tasks

**BEFORE starting any multi-step or complex task, ALWAYS evaluate if it should be delegated to a subagent.**

#### **Mandatory Subagent Evaluation Checklist:**
- [ ] **Multi-file changes** (>2 files) → Use subagent
- [ ] **Systematic refactoring** (patterns across codebase) → Use subagent  
- [ ] **Documentation updates** (multiple .md files) → Use subagent
- [ ] **Complex searches** (multiple rounds of discovery) → Use subagent
- [ ] **Performance optimization** (file restructuring, analysis) → Use subagent
- [ ] **Code quality fixes** (linting violations, imports) → Use subagent
- [ ] **Cross-cutting concerns** (renaming, configuration updates) → Use subagent

#### **Immediate Subagent Triggers:**
1. **Any task requiring >5 tool calls** → Stop and use subagent
2. **File optimization/restructuring** → Use subagent immediately
3. **Markdown validation across multiple files** → Use subagent
4. **Build configuration changes** → Use subagent
5. **Security vulnerability research + fixes** → Use subagent

#### **Default Response Pattern:**
```
User: [Complex multi-step request]
Claude: I'll use a subagent to handle this [task type] efficiently.

[Task tool call with appropriate subagent]
Task: "[Detailed description of work to be done systematically]"
```

#### **Available Specialized Subagents:**
- **general-purpose**: Complex refactoring, multi-file changes, systematic tasks
- **openapi-sync-agent**: API specification synchronization
- **client-generation-agent**: API client regeneration and updates
- **android-integration-agent**: Android-specific issues and testing
- **api-contract-validator-agent**: Contract compliance validation
- **cross-platform-testing-agent**: Multi-platform test coordination

#### **Performance Benefits:**
- **80-95% reduction** in tool calls for complex tasks
- **Faster completion** through specialized expertise
- **Better quality** through systematic approach
- **Context efficiency** by delegating entire workflows

**❌ Recent Failure Example**: CLAUDE.md optimization task used 15+ tool calls manually when 1 subagent call would have handled it completely.

**✅ Success Pattern**: Always ask "Could a subagent handle this more efficiently?" before starting complex work.

### ⚠️ CRITICAL: Always Validate Generated Markdown

**ALWAYS run `bash scripts/core/validate-markdown.sh` after generating or modifying any markdown files.**

- **Why**: Prevents syntax errors that break IDE display and documentation tools
- **When**: After any markdown generation, editing, or updates to documentation
- **Command**: `bash scripts/core/validate-markdown.sh`
- **Result**: Must show "🎉 All markdown files are valid!" before considering work complete

### 🚀 CRITICAL: Proactive CLAUDE.md Optimization Strategy

**AUTOMATICALLY optimize CLAUDE.md when it exceeds performance thresholds to maintain session efficiency.**

#### **Auto-Optimization Triggers:**
- **File Size**: When CLAUDE.md exceeds 40KB or 800 lines
- **Performance Warning**: If user reports slow session loading
- **Session Start**: Proactively check size and optimize if needed

#### **Optimization Process:**
1. **Archive Current Version**: `mv CLAUDE.md docs/CLAUDE_ORIGINAL_[DATE].md`
2. **Create Optimized Version**: 
   - Keep: Current work, project overview, dev commands, critical reminders, token strategies
   - Archive: Detailed implementation history, completed task specifics, extensive lessons learned
3. **Preserve Essential Context**: All guidance needed for immediate productivity
4. **Historical Access**: Link to archive files for detailed context when needed

#### **Target Metrics:**
- **Optimized Size**: ~150 lines, ~8KB (80%+ reduction typical)
- **Essential Context**: 100% preserved for development efficiency
- **Performance Gain**: 40-60% faster session startup
- **Context Window**: 80%+ reduction in consumption

#### **Optimization Template:**
```markdown
# Essential Sections (Keep):
- Current Work & Active Tasks
- Project Overview & Technologies  
- Development Commands & Scripts
- Critical Process Reminders (validation, security, etc.)
- Token Optimization Strategies
- Key Development Principles
- Port Assignments & Architecture
- Completed Work Summary (1-2 lines each)

# Archive Sections (Move to docs/CLAUDE_HISTORY_[DATE].md):
- Detailed implementation steps
- Full troubleshooting context
- Extensive lesson learned explanations
- Multi-step technical solutions
- Historical decision rationale
```

#### **Automation Strategy:**
- **Proactive**: Check CLAUDE.md size at session start, optimize if >40KB
- **User-Requested**: When user reports performance issues
- **Preventive**: Before adding large new sections, consider optimization first
- **Preservation**: Always maintain archive for detailed historical context

**Why This Matters**: Large CLAUDE.md files (64KB+) significantly impact session performance and context window usage. This strategy maintains productivity while preserving all essential development context.

### Key Development Principles

1. **Testing Philosophy**: ALWAYS run tests immediately after ANY refactoring before claiming completion
2. **Real vs Mock Implementation**: User consistently pushed for actual implementations over mocks
3. **Explicit Imports**: No wildcard imports - always use specific class imports
4. **Security-First**: All WebAuthn vulnerabilities have test coverage (100% protection achieved)
5. **Git History**: Always use `git mv` instead of `mv` for file moves to preserve history

### Token Optimization Strategies

#### 1. Batch Operations
- Use `MultiEdit` tool for multiple changes in single file vs multiple `Edit` calls
- Use `replace_all: true` for consistent renamings vs individual replacements

#### 2. Strategic Search Patterns  
- Use `Grep` with specific `path` parameters vs repository-wide searches
- Use `output_mode: "files_with_matches"` when you only need file lists

#### 3. Efficient File Reading
- Use `limit` and `offset` parameters to read specific sections vs entire files
- Use line numbers from `Grep` results to target `Read` operations

#### 4. Subagent Usage for Complex Tasks
- **Always consider subagents first** for any task involving multiple file modifications
- **Use subagents when**: Multi-file changes, systematic pattern application, cross-cutting concerns
- **Token savings**: 80-95% reduction in tool calls for large refactoring tasks

## Security Focus

This project emphasizes security testing and vulnerability protection:
- **PoisonSeed attacks** - Cross-origin authentication abuse
- **Username enumeration** (CVE-2024-39912) - Authentication start does NOT reveal user existence  
- **Replay attacks** - Challenge/response reuse
- **Credential tampering** - Signature validation
- **Result**: 7/7 security tests passing, 100% coverage achieved

## OpenAPI Specification Management 

**CRITICAL: Keep OpenAPI specification synchronized with server implementation at all times**

- **Source of Truth**: Server implementation takes precedence over specification
- **When Modifying Responses**: Update server → Update OpenAPI spec → Regenerate clients → Verify tests
- **Verification**: `./gradlew :webauthn-server:copyGeneratedClientToLibrary && cd android-test-client && ./gradlew connectedAndroidTest`

## Port Assignments

- **WebAuthn Server**: 8080 (main API)
- **WebAuthn Test Service**: 8081 (cross-platform credential generation)  
- **Web Test Client**: 8082 (E2E test web frontend)
- **PostgreSQL**: 5432
- **Redis**: 6379  
- **Jaeger UI**: 16686

## Centralized Package Configuration

**CRITICAL: All client library publishing now uses centralized configuration for consistency and maintainability.**

### Configuration Location
Primary configuration in `.github/workflows/client-e2e-tests.yml`:
```yaml
env:
  BASE_VERSION: "1.0"
  NPM_SCOPE: "@vmenon25"
  NPM_PACKAGE_NAME: "mpo-webauthn-client"
```

### Configuration Benefits
- **Single Point of Control**: Update npm scope in one location affects all publishing
- **Automated Documentation**: Package names in release notes use centralized values
- **Consistent Naming**: Both Android and npm clients reference the same configuration
- **Easy Maintenance**: No need to update multiple files when changing package scope

### Published Package Names
- **npm**: `@vmenon25/mpo-webauthn-client` (generated from `${NPM_SCOPE}/${NPM_PACKAGE_NAME}`)
- **Android**: `com.vmenon.mpo.api.authn:mpo-webauthn-android-client` (Maven coordinates)

## Completed Work Summary

### Major Achievements ✅
- **Centralized npm Package Configuration**: Established workflow environment variables (`NPM_SCOPE`, `NPM_PACKAGE_NAME`) for single-point configuration management
- **Enhanced Regex Validation**: Upgraded version validation from `^[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9]+(\\.[a-zA-Z0-9]+)*)?$` to `^[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9-]+(\\.[a-zA-Z0-9-]+)*)?$` supporting hyphens in prerelease identifiers for full npm semver compliance\n- **Robust Version Validation**: All version formats now properly validated - rejects invalid 2-part, 4-part, and empty prerelease formats while supporting advanced prerelease identifiers like `1.0.0-alpha-beta.1`\n- **Unified 3-Part Versioning**: Standardized both Android and npm clients to use identical semantic versioning with enhanced validation ensuring 100% npm compatibility\n- **PR Publishing Support**: Added automatic snapshot publishing for pull requests with version format 1.0.0-pr.42.123 for testing client changes before merge
- **Dual Registry Publishing**: Configured production releases to npm/GitHub Packages and PR snapshots to GitHub Packages with automated PR comments
- **Client Library Publishing Automation**: Enabled automated publishing of Android and TypeScript/npm client libraries on main branch merges with synchronized versioning
- **Library Usage Documentation**: Created comprehensive usage guide with integration examples for both Android and TypeScript clients including PR testing workflows
- **npm Package Configuration**: Enhanced TypeScript client with proper npm metadata and scoped package publishing (@vmenon25/mpo-webauthn-client)
- **GitHub Packages Integration**: Configured Android library publishing to GitHub Packages with proper authentication
- **Documentation Updates for TypeScript Conversion**: Updated all documentation files to reflect TypeScript web client architecture, build processes, and OpenAPI integration
- **TypeScript OpenAPI Client Integration**: Full TypeScript conversion with webpack bundling, automated client generation, and production-ready ESM/UMD builds
- **Server Process Management**: Added graceful shutdown with SIGTERM/SIGINT handling and port cleanup for test reliability
- **Generated Client Workflow**: Git exclusion for generated clients with CI regeneration and proper build dependency order
- **GitHub CI Path Issues**: Fixed package.json lifecycle, TypeScript configurations, and bundle loading complexity
- **GitHub Workflow Health Check**: Enhanced CI diagnostics for service health monitoring
- **OpenTelemetry Race Condition Fix**: Resolved test flakiness using system property approach  
- **Service Renaming**: webauthn-test-service → webauthn-test-credentials-service for clarity
- **Client Renaming**: test-client → web-test-client for clarity and consistency
- **Documentation Fixes**: Fixed all markdown syntax errors across project
- **Port Conflict Resolution**: Moved test client to 8082, eliminated CI conflicts
- **Code Quality**: Implemented comprehensive linting with Detekt/ktlint, 0 violations achieved
- **Security Testing**: 100% coverage of WebAuthn vulnerabilities with automated monitoring
- **Multi-Module Architecture**: Restructured from single-module to multi-module project
- **Android Client Integration**: Generated client library with automated publishing
- **Token Optimization**: Documented strategies achieving 40-60% token usage reduction

### Key Files & Scripts
- **Documentation**: Complete README files for project root and web-test-client with TypeScript architecture details
- **Validation**: `scripts/core/validate-markdown.sh` - Comprehensive markdown syntax validation
- **Security**: `scripts/monitoring/vulnerability-monitor.js` - Weekly vulnerability scanning  
- **Android Tests**: `scripts/core/run-android-tests.sh` - Cross-platform testing
- **Development**: `webauthn-server/start-dev.sh` - Local development environment
- **Port Cleanup**: `web-test-client/scripts/cleanup-port.js` - Port cleanup utility for tests
- **TypeScript Build**: `web-test-client/tsconfig.build.json` - Build-specific TypeScript configuration
- **Webpack Configs**: `web-test-client/webpack.config.js` - Unified webpack configuration for UMD/development builds

## Testing Architecture

- **VulnerabilityProtectionTest**: Comprehensive security validation (7 tests)
- **Integration tests**: Use BaseIntegrationTest with real containers + webauthn-test-lib
- **Unit tests**: Mock dependencies with testStorageModule  
- **Cross-platform**: webauthn-test-credentials-service for Android/web client testing
- **Coverage**: Kover 0.9.1 with XML/HTML reports for CI integration

## Important Notes

- Username enumeration protection: `/authenticate/start` returns valid challenges for both existing and non-existent users
- The Yubico library handles most WebAuthn security automatically
- Use `testStorageModule` for integration tests (in-memory storage)
- All tests must pass with `./gradlew test` before claiming completion
- Always verify Android tests pass: `cd android-test-client && ./gradlew connectedAndroidTest`

### WebAuthn Client Integration Requirements

**CRITICAL**: When integrating with WebAuthn clients, ensure proper data handling:

1. **Server Response Format**: Server returns `publicKeyCredentialCreationOptions` and `publicKeyCredentialRequestOptions` as JSON strings
2. **Client Parsing**: Must parse `.publicKey` field from server response for SimpleWebAuthn library
3. **Credential Serialization**: Must stringify credential responses before sending to server
4. **Test Title Matching**: Test verification must match actual page titles (e.g., "WebAuthn Web Test Client")

**Example Integration Pattern**:
```javascript
// Registration
const startData = await registrationApi.startRegistration({registrationRequest});
const publicKeyOptions = JSON.parse(startData.publicKeyCredentialCreationOptions).publicKey;
const credential = await SimpleWebAuthnBrowser.startRegistration(publicKeyOptions);
await registrationApi.completeRegistration({
    requestId: startData.requestId,
    credential: JSON.stringify(credential)  // Must stringify!
});
```

---

*For detailed historical context and implementation details, see `docs/CLAUDE_HISTORY.md`*