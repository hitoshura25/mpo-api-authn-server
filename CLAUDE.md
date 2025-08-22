# WebAuthn KTor Server - Claude Memory (Optimized)

## Current Work (In Progress)

### Active Tasks
- No active tasks at this time - all major features completed

### Completed Major Refactors
- **Client Library Publishing Architecture Cleanup (PHASES 1-9 COMPLETED)**: Successfully implemented complete CI/CD consolidation achieving 23% faster main branch processing (13 min → 10 min) and 40% reduction in workflow complexity. Phase 9 consolidated `main-ci-cd.yml` and `main-branch-post-processing.yml` into unified workflow with parallel production publishing and comprehensive cleanup coordination. Centralized configuration via `config/publishing-config.yml` with enhanced security and 100% Docker registry optimization.
- **OpenAPI Client Library Architecture**: ✅ **COMPLETED** - Docker-inspired staging→production workflow using GitHub Packages with dedicated client library submodules.

### Planned Major Refactors
- **Client Publishing Architecture Phase 10** *(Future Optimization)* - Independent Component Processing for 40-60% faster builds when only single components change. Phase 9 (Consolidated CI/CD Publishing) completed successfully achieving 23% performance improvement.
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

### 🏗️ CRITICAL: Android Publishing & Docker Registry Patterns

**MANDATORY patterns for Android publishing and Docker registry references to prevent configuration failures.**

#### **🚨 CRITICAL: vanniktech Maven Publish Plugin GitHub Packages Configuration**
For Android client library publishing to GitHub Packages, ALWAYS use this exact pattern:
```gradle
publishing {
    repositories {
        maven {
            name = "GitHubPackages"
            url = uri(System.getenv("ANDROID_REPOSITORY_URL"))
            credentials(PasswordCredentials::class)  // ✅ MANDATORY for vanniktech plugin
        }
    }
}
```

**Critical Requirements:**
- **ALWAYS include `credentials(PasswordCredentials::class)`** - Required by vanniktech plugin for GitHub Packages
- **NEVER rely on automatic credential resolution** - Explicit credentials block is mandatory
- **Environment Variables**: Use `ORG_GRADLE_PROJECT_GitHubPackagesUsername` and `ORG_GRADLE_PROJECT_GitHubPackagesPassword`
- **Reference**: [vanniktech GitHub Packages Documentation](https://vanniktech.github.io/gradle-maven-publish-plugin/other/#github-packages-example)

#### **🚨 CRITICAL: Docker Registry Reference Pattern**
**ALWAYS use job outputs for Docker registry references, NEVER environment variables:**
```yaml
# ✅ CORRECT: Use job output from setup-config
docker-registry: ${{ needs.setup-config.outputs.docker-registry }}

# ❌ WRONG: Environment variables not available in callable workflow context
docker-registry: ${{ env.DOCKER_REGISTRY }}
```

**Root Cause**: Environment variables are not accessible in callable workflow contexts. Setup-config jobs MUST convert env vars to outputs first.

#### **Android Credential Configuration Best Practices:**
- **Repository Name Matching**: Credential env var names MUST match repository name (e.g., `GitHubPackages` → `GitHubPackagesUsername`)
- **Gradle Property Pattern**: Use `ORG_GRADLE_PROJECT_` prefix for automatic Gradle property injection
- **Staging vs Production**: GitHub Packages for staging, Maven Central for production (with `--no-configuration-cache`)

#### **Recently Fixed Critical Issues (August 2025):**
1. **Missing `credentials(PasswordCredentials::class)`**: Android publishing failed without explicit credentials block
2. **Wrong Docker Registry Reference**: web-e2e-tests.yml used `${{ env.DOCKER_REGISTRY }}` instead of job output
3. **Credential Name Mismatch**: Repository "GitHubPackages" required matching environment variable names

**Why This Matters**: These patterns prevent common publishing failures and ensure consistent configuration across all client library workflows.

### 🔄 CRITICAL: Callable Workflow Input/Output Validation

**MANDATORY validation process for callable workflow refactoring to prevent input/output mismatch errors.**

#### **🚨 CRITICAL: Input/Output Contract Validation (Recurring Issue Pattern)**
**ALWAYS validate that inputs passed to callable workflows match their definitions:**

**Common Failure Pattern:**
- Enhance orchestrator workflow (e.g., `client-publish.yml`) to pass new input (`force-publish`)
- Forget to add corresponding input definition to called workflows (`publish-typescript.yml`, `publish-android.yml`)
- Result: "Invalid input, X is not defined in the referenced workflow" errors

#### **Mandatory Validation Checklist for Callable Workflow Changes:**

**Before Any Callable Workflow Refactoring:**
- [ ] **Map All Input Dependencies**: Document which workflows call which other workflows
- [ ] **Input Contract Verification**: Ensure ALL inputs passed by callers are defined in callable workflows
- [ ] **Output Contract Verification**: Ensure ALL outputs referenced by callers are defined in callable workflows  
- [ ] **Secret Contract Verification**: Ensure ALL secrets passed are properly defined (excluding system secrets like `GITHUB_TOKEN`)
- [ ] **Permission Alignment**: Verify calling workflows have necessary permissions for callable workflows

#### **Systematic Validation Process:**

**Step 1: Workflow Dependency Mapping**
```bash
# Find all callable workflow references
grep -r "uses: .*\.yml" .github/workflows/
# Document the calling relationships
```

**Step 2: Input/Output Contract Validation**
```bash
# For each callable workflow, validate inputs match callers
# Example: If client-publish.yml passes force-publish to publish-typescript.yml
grep -A 10 "force-publish" .github/workflows/client-publish.yml    # Caller
grep -A 5 "force-publish" .github/workflows/publish-typescript.yml # Callable
```

**Step 3: Automated Syntax Validation**
```bash
# GitHub Actions will validate on push, but local validation prevents failed commits
yq eval '.on.workflow_call.inputs' .github/workflows/callable-workflow.yml
```

#### **Input/Output Synchronization Patterns:**

**When Adding New Inputs to Orchestrator:**
1. **Add to Orchestrator**: Define input in orchestrator workflow (e.g., `client-publish.yml`)
2. **Add to All Callees**: Add same input to ALL workflows called by orchestrator
3. **Validate Contract**: Ensure input names, types, and requirements match exactly
4. **Test Locally**: Push to feature branch and verify GitHub Actions validation passes

**When Adding New Outputs:**
1. **Define in Callable**: Add output to callable workflow
2. **Reference in Caller**: Update calling workflow to use new output
3. **Chain Dependencies**: Update job dependency chains if new outputs affect conditions

#### **System Reserved Names to Avoid:**
- **`GITHUB_TOKEN`**: Automatically available, cannot be explicitly defined in callable workflow secrets
- **GitHub Context Variables**: `github.*` properties are automatically available
- **System Environment Variables**: Many system env vars are reserved and should not be overridden

#### **Recently Fixed Critical Issues (August 2025):**
1. **Missing Input Definitions**: `force-publish` added to `client-publish.yml` but missing from `publish-typescript.yml` and `publish-android.yml`
2. **System Reserved Secret**: `GITHUB_TOKEN` cannot be explicitly defined in callable workflow secrets
3. **Input Type Mismatches**: Boolean inputs passed as strings causing validation failures

#### **Validation Tools and Commands:**
```bash
# Validate workflow syntax
find .github/workflows -name "*.yml" -exec yq eval . {} \; > /dev/null

# Check for input/output mismatches
grep -r "force-publish" .github/workflows/ | grep -E "(inputs|with):"

# Find callable workflow relationships  
grep -r "uses: ./.github/workflows/" .github/workflows/
```

**Why This Matters**: Callable workflow input/output mismatches are a recurring issue that cause GitHub Actions validation failures. Systematic validation prevents these errors and ensures smooth workflow refactoring.

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