# WebAuthn KTor Server - Claude Memory (Optimized)

## Current Work (In Progress)

### Active Tasks
- **Phase 9: Consolidated CI/CD Publishing Workflow** *(Ready for Implementation - 2025-08-21)*
  - **Goal**: Merge `main-ci-cd.yml` and `main-branch-post-processing.yml` into unified workflow
  - **Benefits**: 23% faster main branch processing, 40% workflow complexity reduction
  - **Prerequisites**: Phase 8 Docker Image Lifecycle Coordination (✅ COMPLETED)
  - **Documentation**: `docs/improvements/in-progress/client-publishing-architecture-cleanup.md` (Phase 9 section)
  - **Implementation**: Stage-gate pattern with callable production workflows

### Completed Major Refactors
- **Client Library Publishing Architecture Cleanup (PHASES 1-8 COMPLETED)**: Centralized all client publishing configuration to `config/publishing-config.yml`. Eliminated ~35 lines of hardcoded repository logic, enhanced security by removing insecure yq downloads, achieved 100% Docker registry centralization. **Phase 8 CRITICAL FIX**: Resolved 0% DockerHub publishing success rate through Docker image lifecycle coordination.
- **OpenAPI Client Library Architecture**: Docker-inspired staging→production workflow using GitHub Packages with dedicated client library submodules.

### Planned Major Refactors
- **Client Publishing Architecture Phases 9-10** *(Remaining Plan 2025-08-21)* - Complete CI/CD optimization in two remaining phases: Phase 9 (Consolidated CI/CD Publishing), Phase 10 (Independent Component Processing). Expected outcomes: 23% faster main branch processing, 40-60% faster builds for single-component changes. Phase 8 (Docker Image Lifecycle) completed same-day. See `docs/improvements/in-progress/client-publishing-architecture-cleanup.md` (Phases 9-10).
- **iOS Test Client Implementation** *(Enhanced 2025-08-21)* - Complete iOS E2E testing ecosystem with Swift client library generation, SwiftUI test application, and CI integration. Extends testing coverage to iOS platform with AuthenticationServices WebAuthn integration. Timeline: 8-10 weeks. See `docs/improvements/planned/ios-test-client-implementation.md`.
- **FOSS Security Implementation**: Replace AI-dependent security solutions with established FOSS tools (Trivy Action, Semgrep, OWASP ZAP). See `docs/improvements/planned/foss-security-implementation.md` for complete plan.

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
- **android-test-client/** - Android E2E test client consuming published Android library
- **web-test-client/** - TypeScript E2E test client consuming published npm library
- **android-client-library/** - Dedicated Android client library submodule with publishing configuration
- **typescript-client-library/** - Dedicated TypeScript client library submodule with npm publishing

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
- **Gradle Config Cache Validation**: `./scripts/core/validate-gradle-config-cache.sh`

## Critical Development Reminders

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

#### **Available Specialized Subagents:**
- **general-purpose**: Complex refactoring, multi-file changes, systematic tasks
- **openapi-sync-agent**: API specification synchronization
- **client-generation-agent**: API client regeneration and updates
- **android-integration-agent**: Android-specific issues and testing
- **api-contract-validator-agent**: Contract compliance validation
- **cross-platform-testing-agent**: Multi-platform test coordination
- **security-vulnerability-analyst**: Threat modeling, vulnerability assessment

### 🧹 CRITICAL: Dead Code Cleanup After Refactoring

**ALWAYS perform comprehensive cleanup after removing or refactoring functionality to eliminate orphaned code.**

#### **Mandatory Cleanup Checklist After Refactoring:**
- [ ] **Scripts & Tools**: Search for and remove unused scripts, especially in `scripts/ci/`, `scripts/docker/`, `scripts/security/`
- [ ] **Workflow References**: Update all workflow files that may reference removed jobs or scripts
- [ ] **Documentation Updates**: Update README.md, CLAUDE.md, and docs/ files to reflect changes
- [ ] **Environment Variables**: Remove unused env vars from workflow files and docker-compose
- [ ] **Configuration Files**: Clean up orphaned config files and references
- [ ] **Dependencies**: Remove unused npm/gradle dependencies introduced for removed features

### ⚠️ CRITICAL: Always Validate Generated Markdown

**ALWAYS run `bash scripts/core/validate-markdown.sh` after generating or modifying any markdown files.**

### 🔧 CRITICAL: GitHub Actions Workflow Development

**ALWAYS follow GitHub Actions best practices to prevent workflow failures:**

#### **🚨 CRITICAL: Callable Workflow Env Var Pattern (NEVER FORGET!)**
When creating workflows with callable workflows:
```yaml
# MANDATORY: Add setup-config job to convert env vars to outputs
setup-config:
  outputs:
    package-name: ${{ steps.config.outputs.package-name }}
  steps:
    - id: config
      run: echo "package-name=${{ env.PACKAGE_NAME }}" >> $GITHUB_OUTPUT

# Then use job outputs in callable workflows
callable-job:
  uses: ./.github/workflows/some-workflow.yml
  needs: setup-config
  with:
    package-name: ${{ needs.setup-config.outputs.package-name }}  # ✅ CORRECT
    # package-name: ${{ env.PACKAGE_NAME }}  # ❌ WILL FAIL
```

#### **🚨 CRITICAL: Callable Workflow Secrets Pattern**
When secrets are explicitly defined in callable workflows, they MUST be explicitly passed:
```yaml
# In callable workflow
secrets:
  GRADLE_ENCRYPTION_KEY:
    required: true

# In calling workflow  
secrets:
  GRADLE_ENCRYPTION_KEY: ${{ secrets.GRADLE_ENCRYPTION_KEY }}
  # ❌ WILL FAIL: secrets: inherit (doesn't work with explicitly defined secrets)
```

#### **Common Workflow Issues to Avoid:**
- **❌ NEVER use `env.VARIABLE` in `if:` conditionals** - Use job outputs instead
- **❌ NEVER use `github.event.number`** - Use `github.event.pull_request.number`
- **❌ NEVER use `actions/github-script` with external file requires** - Use direct Node.js execution
- **✅ Use `always() &&` prefix when job should evaluate conditions even if dependencies are skipped**

### 🚀 CRITICAL: Proactive CLAUDE.md Optimization Strategy

**AUTOMATICALLY optimize CLAUDE.md when it exceeds performance thresholds to maintain session efficiency.**

#### **Auto-Optimization Triggers:**
- **File Size**: When CLAUDE.md exceeds 40KB or 800 lines
- **Performance Warning**: If user reports slow session loading
- **Session Start**: Proactively check size and optimize if needed

#### **Optimization Process:**
1. **Archive Current Version**: `mv CLAUDE.md docs/CLAUDE_ORIGINAL_[DATE].md`
2. **Create Optimized Version**: Keep current work, project overview, dev commands, critical reminders
3. **Preserve Essential Context**: All guidance needed for immediate productivity
4. **Historical Access**: Link to archive files for detailed context when needed

## Security Focus

This project emphasizes security testing and vulnerability protection:
- **PoisonSeed attacks** - Cross-origin authentication abuse
- **Username enumeration** (CVE-2024-39912) - Authentication start does NOT reveal user existence  
- **Replay attacks** - Challenge/response reuse
- **Credential tampering** - Signature validation
- **Result**: 7/7 security tests passing, 100% coverage achieved

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
Primary configuration in `config/publishing-config.yml`:
```yaml
packages:
  android:
    groupId: "io.github.hitoshura25"
    baseArtifactId: "mpo-webauthn-android-client"
  typescript:
    scope: "@vmenon25"
    basePackageName: "mpo-webauthn-client"
```

### Published Package Names
- **npm**: `@vmenon25/mpo-webauthn-client`
- **Android**: `com.vmenon.mpo.api.authn:mpo-webauthn-android-client`

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

---

## Historical Context

**For detailed implementation history, troubleshooting guides, and comprehensive lessons learned, see:**
- **Complete Original**: `docs/CLAUDE_ORIGINAL_2025-08-21.md` - Full historical context and detailed implementation examples
- **Project History**: `docs/history/` - Archived implementation details and decision rationale
- **Improvements**: `docs/improvements/` - Current and planned architectural improvements