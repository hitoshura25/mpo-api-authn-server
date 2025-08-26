# WebAuthn KTor Server - Claude Memory (Optimized)

## Current Work (In Progress)

### Active Tasks
- **Workflow Change Detection Optimization**: Minor optimization opportunity to prevent unnecessary Docker builds when workflow changes don't affect Docker processes (documented in client-publishing-architecture-cleanup.md). Expected: 40% faster CI for workflow-only changes

### Completed Major Refactors
- **Client Library Publishing Architecture Cleanup (PHASES 1-10 COMPLETED)**: ✅ **COMPLETED** - Successfully implemented complete CI/CD optimization with independent component processing achieving 40-95% performance improvements. **Phase 10** delivered correct architecture with parallel client publishing, eliminated duplicate change detection, and smart E2E dependency management. Key results: client libraries publish immediately when OpenAPI changes (not after full build pipeline), true parallel execution of builds + publishing, and comprehensive E2E cache optimization.
- **OpenAPI Client Library Architecture**: ✅ **COMPLETED** - Docker-inspired staging→production workflow using GitHub Packages with dedicated client library submodules.

### Planned Major Refactors
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

### 🚨 CRITICAL: NEVER Make Assumptions - Always Validate Documentation

**THE FUNDAMENTAL RULE**: NEVER create code, workflows, or configurations based on assumptions or invented parameters. ALWAYS validate against official documentation first.

#### **🚨 MANDATORY Documentation Validation Process:**

**BEFORE writing ANY code that integrates with external tools/APIs/actions:**
1. **Find Official Documentation**: Locate the current, official documentation for the tool/service
2. **Verify Current Version**: Ensure the documentation matches the version you're using
3. **Check Deprecation Status**: Verify the tool/action is not deprecated
4. **Validate Parameters**: Confirm ALL parameters exist and have correct syntax
5. **Look for Examples**: Use official examples as the foundation, not invented syntax

#### **🚨 RED FLAGS - STOP and Research:**
- **"I think the parameter should be..."** → STOP: Find documentation
- **"Based on similar tools..."** → STOP: Each tool has unique syntax  
- **"This parameter seems logical..."** → STOP: Logic ≠ actual API
- **"The old version had..."** → STOP: APIs change, verify current version

#### **Recent Critical Example: Semgrep Integration Failure**
**What Went Wrong:**
- Used deprecated `returntocorp/semgrep-action@v1` without checking status
- Invented parameters: `generateSarif`, `scanChangedFilesOnly`, `output` (none exist)
- Created invalid Semgrep rule syntax without validating schema
- Result: Complete workflow failure and wasted implementation time

**What Should Have Been Done:**
1. **Research First**: Check if `returntocorp/semgrep-action` is current
2. **Find Current Approach**: Discover official `semgrep/semgrep` Docker method
3. **Validate Rule Syntax**: Check Semgrep rule schema documentation
4. **Test Locally**: Validate YAML and rule syntax before committing

#### **Approved Information Sources (In Priority Order):**
1. **Official Documentation**: Tool's official docs site (e.g., semgrep.dev, docs.github.com)
2. **Official GitHub Repositories**: README files and examples in official repos
3. **Current Release Notes**: Check for breaking changes and deprecations
4. **Web Search**: Only for finding official documentation sources

#### **NEVER Acceptable Sources:**
- ❌ **Assumptions**: "This should work like X"
- ❌ **Invented Syntax**: Making up parameters or configurations
- ❌ **Outdated Examples**: Using old tutorials without version verification
- ❌ **Similar Tools Logic**: "Tool A works this way, so Tool B should too"

#### **When Documentation is Missing or Unclear:**
- **State the Problem**: "Official documentation for X is unclear/missing"
- **Request Research**: "This needs independent research before implementation"
- **Propose Alternatives**: Suggest different tools with better documentation
- **Don't Guess**: NEVER attempt to generate code without confirmed syntax

#### **Implementation Safety Pattern:**
```yaml
# ✅ CORRECT: Based on verified official documentation
uses: official/action@v2
with:
  validated-param: "documented-value"

# ❌ WRONG: Invented parameters
uses: deprecated/action@v1  
with:
  made-up-param: "seems-logical"
```

**This rule prevents:**
- Workflow failures from invalid syntax
- Security vulnerabilities from incorrect configurations
- Time waste from debugging non-existent features
- Loss of user confidence from repeated failures

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

#### **🚨 CRITICAL: Job Dependencies Rule (FUNDAMENTAL!)**
**ANY job that references `needs.JOBNAME.outputs.X` or `needs.JOBNAME.result` MUST include `JOBNAME` in its `needs` array.**

**WHY THIS IS CRITICAL**: Missing dependencies cause outputs to be empty/undefined with NO error - workflows appear to succeed but use wrong values.

```yaml
# ❌ WRONG: References generate-version but not in needs array
deploy-job:
  needs: [build-job]  # Missing generate-version!
  steps:
    - run: echo "Version: ${{ needs.generate-version.outputs.version }}"  # Will be EMPTY!

# ✅ CORRECT: All referenced jobs in needs array  
deploy-job:
  needs: [build-job, generate-version]  # Both dependencies declared
  steps:
    - run: echo "Version: ${{ needs.generate-version.outputs.version }}"  # Works correctly
```

**VALIDATION PATTERN**: For every `needs.JOBNAME.anything`, verify `JOBNAME` in `needs: [...]` array.
**CONDITIONAL JOBS**: Use `always() && needs.maybe-skipped.result == 'success'` for potentially skipped dependencies.
**DOCUMENTATION**: Complete guide at `docs/development/workflows/github-actions-dependency-rules.md`

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

#### **🚨 CRITICAL: Workflow Output Definition vs Implementation (August 2025)**
**When adding new workflow outputs, ALWAYS verify the complete implementation chain:**

```yaml
# Step 1: Define the workflow output (Declaration)
outputs:
  service-built:
    description: 'Whether service was built'
    value: ${{ jobs.docker-job.outputs.service-image != '' && 'true' || 'false' }}

# Step 2: Verify job outputs exist in callable workflow (Implementation)
# In docker-build.yml:
jobs:
  docker-job:
    outputs:
      service-image: ${{ steps.docker-meta.outputs.tags }}  # ✅ Must exist!
```

**CRITICAL VALIDATION STEPS:**
1. **Declaration**: Output defined in `outputs:` section ✓
2. **Reference**: Output references correct job via `jobs.JOBNAME.outputs.X` ✓  
3. **Implementation**: Referenced job output actually exists in callable workflow ✓
4. **Data Flow**: Job output gets value from step output ✓

**FAILURE PATTERN**: Defining workflow outputs that reference non-existent job outputs results in empty/undefined values with NO error messages.

**RECENT EXAMPLE**: Added `webauthn-server-built` and `test-credentials-service-built` outputs in build-and-test.yml but forgot to verify that docker-build.yml actually provides the referenced `webauthn-server-image` and `test-credentials-image` outputs.

**VALIDATION COMMANDS**:
```bash
# Verify job outputs exist in callable workflow
grep -A 10 "outputs:" .github/workflows/docker-build.yml
# Verify job sets the outputs  
grep "webauthn-server-image\|test-credentials-image" .github/workflows/docker-build.yml
```

#### **🚨 CRITICAL: Complete Job Dependency Chain Validation (August 2025)**
**When adding new change detection categories, ALWAYS verify the complete workflow dependency chain:**

**FAILURE PATTERN**: Change detection succeeds but downstream jobs are still skipped.
```yaml
# ❌ BROKEN: detect-changes outputs correct flag, but security-scanning job misses it
detect-changes.yml: docker-security-workflows-changed: true  ✅
main-ci-cd.yml security-scanning: checks workflows-changed only  ❌ (skipped)

# ✅ CORRECT: All downstream jobs check specific category flags  
security-scanning:
  if: |
    needs.detect-component-changes.outputs.docker-security-workflows-changed == 'true' ||
    needs.detect-component-changes.outputs.workflows-changed == 'true'  # fallback
```

**MANDATORY CHECKLIST** for new change detection categories:
- [ ] Category added to `detect-changes.yml` filters
- [ ] Category included in build decision logic  
- [ ] Category output defined at workflow and job levels
- [ ] **ALL dependent jobs include specific category check** (most critical step)
- [ ] End-to-end test: file change → detect-changes → all downstream jobs execute

**WHY CRITICAL**: Security-critical workflow changes can be deployed without validation, creating false security confidence.

#### **Common Workflow Issues to Avoid:**
- **❌ NEVER use `env.VARIABLE` in `if:` conditionals** - Use job outputs instead
- **❌ NEVER use `github.event.number`** - Use `github.event.pull_request.number`
- **❌ NEVER use `actions/github-script` with external file requires** - Use direct Node.js execution
- **❌ NEVER define outputs without verifying implementation chain** - Always validate job→step→value mapping
- **❌ NEVER add change detection without validating ALL downstream job conditions** - Change detection ≠ job execution
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
4. **🚨 CRITICAL: GitHub Actions Job Dependencies**: E2E test workflow dispatch failed due to missing `generate-staging-version` job in dependencies

**Why This Matters**: These patterns prevent common publishing failures and ensure consistent configuration across all client library workflows.

### 🚨 CRITICAL: GitHub Actions Job Dependencies Rule

**THE FUNDAMENTAL RULE**: Any job that references `needs.JOBNAME.outputs.X` or `needs.JOBNAME.result` MUST include `JOBNAME` in its `needs` array.

#### **Critical Pattern (Silent Failure)**:
```yaml
# ❌ WRONG - Will cause silent failure (empty/undefined values)
some-job:
  needs: [ other-job ]  # Missing required-job!
  with:
    param: ${{ needs.required-job.outputs.value }}  # Empty/undefined!

# ✅ CORRECT - Properly declares dependency
some-job:
  needs: [ other-job, required-job ]  # Include ALL referenced jobs
  with:
    param: ${{ needs.required-job.outputs.value }}  # Works correctly
```

#### **Why This is Critical**:
- **Silent Failures**: Missing dependencies don't cause workflow errors - they just return empty values
- **Hard to Debug**: Workflows succeed but use wrong/empty data (e.g., client-version: "")
- **Production Impact**: E2E tests might use fake packages instead of real published packages

#### **Validation Pattern**:
```bash
# Check all needs.* references have proper dependencies
grep -n "needs\." .github/workflows/*.yml | grep -v "needs: \[.*JOBNAME.*\]"
```

#### **Common Scenarios**:
1. **Multi-step pipelines**: Jobs referencing outputs from version generation, client publishing, etc.
2. **Conditional workflows**: Using `always() && needs.maybe-skipped.result == 'success'`
3. **Callable workflows**: Passing job outputs as inputs to other workflows

**Recent Fix**: E2E test workflow dispatch was failing because it referenced `needs.generate-staging-version.outputs.version` without including `generate-staging-version` in the needs array, causing empty client-version inputs.

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
- **`GITHUB_TOKEN`**: Automatically available in all workflows, NEVER define in callable workflow secrets AND NEVER pass explicitly in secrets block of calling workflows
- **GitHub Context Variables**: `github.*` properties are automatically available
- **System Environment Variables**: Many system env vars are reserved and should not be overridden

#### **Recently Fixed Critical Issues (August 2025):**
1. **Missing Input Definitions**: `force-publish` added to `client-publish.yml` but missing from `publish-typescript.yml` and `publish-android.yml`
2. **GITHUB_TOKEN Double Error**: Cannot define `GITHUB_TOKEN` in callable workflow secrets AND cannot pass it explicitly in calling workflow secrets block
3. **Input Type Mismatches**: Boolean inputs passed as strings causing validation failures
4. **E2E Cache Isolation**: Main branch E2E tests were using PR cache results - fixed by adding branch/event context to cache keys

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

### 🧪 CRITICAL: E2E Test Caching Strategy

**MANDATORY patterns for E2E test caching to prevent cache pollution between different execution contexts.**

#### **🚨 CRITICAL: Branch/Event Context Isolation**
**ALWAYS include branch and event context in E2E test cache keys to prevent cross-contamination:**

**Problem Pattern:**
- PR runs E2E tests and caches results with key: `web-e2e-results-{images}-{files}`
- Main branch uses identical images/files → generates same cache key → skips E2E tests
- Result: Main branch production deployment lacks fresh validation

**Solution Pattern:**
```bash
# Generate context-aware cache keys
if [[ "${{ github.event_name }}" == "pull_request" ]]; then
  CONTEXT_SUFFIX="pr-${{ github.event.pull_request.number }}"
elif [[ "${{ github.ref_name }}" == "main" ]]; then
  CONTEXT_SUFFIX="main"
else
  CONTEXT_SUFFIX="branch-${{ github.ref_name }}"
fi

# Cache key with context isolation
CACHE_KEY="web-e2e-results-${IMAGES_HASH}-${FILES_HASH}-${CONTEXT_SUFFIX}"
```

#### **Cache Key Components for E2E Tests:**
1. **Docker Images**: Hash of Docker image tags being tested
2. **Test Files**: Hash of E2E test files and configuration
3. **Branch Context**: PR number, main branch, or feature branch name
4. **Event Context**: pull_request vs push vs workflow_dispatch

#### **Benefits of Context Isolation:**
- **Production Validation**: Main branch always gets fresh E2E validation
- **PR Independence**: Each PR gets isolated cache without pollution
- **Branch Isolation**: Feature branches don't interfere with main/PR caches
- **Debugging**: Clear cache key patterns for troubleshooting

#### **Cache Key Examples:**
- **PR Run**: `web-e2e-results-{images}-{files}-pr-123`
- **Main Branch**: `web-e2e-results-{images}-{files}-main`
- **Feature Branch**: `web-e2e-results-{images}-{files}-branch-feat-new-feature`

**Why This Matters**: E2E test cache pollution can cause main branch production deployments to skip validation, leading to undetected integration issues in production.

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

## Server Development Best Practices

### Dependency Variant Selection for Server Projects

**CRITICAL: Always prefer JRE variants over Android variants for server-based projects**

When resolving dependency conflicts in server applications like webauthn-server, ensure you're using server-appropriate dependency variants:

- ✅ **JRE variant** (`com.google.guava:guava:31.1-jre`) - Optimized for standard JVM server environments
- ❌ **Android variant** (`com.google.guava:guava:31.1-android`) - Optimized for Android runtime, suboptimal for servers

#### **Common Issue Pattern:**
Gradle's conflict resolution may select Android variants when multiple dependencies request different versions, even in server projects:

```kotlin
// PROBLEM: Multiple variant conflict
dependencies {
    implementation("com.yubico:webauthn-server-core:2.6.0")  // Requests guava:[24.1.1,33)
    implementation("io.swagger.codegen.v3:swagger-codegen:3.0.41")  // Requests guava:31.0.1-jre
    implementation("io.swagger:swagger-core:1.6.10")  // Requests guava:31.1-android
}
// Result: Gradle selects 31.1-android (highest version wins, wrong variant)
```

#### **Solution Pattern:**
Use dependency constraints to explicitly select server-appropriate variants:

```kotlin
dependencies {
    constraints {
        implementation("com.google.guava:guava:31.1-jre") {
            because(
                "Pin Guava JRE version for server environment, avoiding version ranges and Android variants"
            )
        }
    }
    // ... other dependencies
}
```

#### **Benefits:**
- **Performance**: JRE variants optimized for server JVM environments
- **Compatibility**: Better compatibility with server-side frameworks and libraries
- **Predictability**: Explicit control prevents unexpected variant selection
- **Configuration Cache**: Pinning versions prevents cache invalidation from version ranges

#### **Detection Commands:**
```bash
# Check current variant selection
./gradlew :webauthn-server:dependencyInsight --dependency=com.google.guava:guava --configuration=runtimeClasspath

# Look for Android variants in server projects (should be empty)
./gradlew :webauthn-server:dependencies --configuration=runtimeClasspath | grep android
```

**Rule**: For server projects (webauthn-server, webauthn-test-credentials-service), always use `-jre` variants when available, never `-android` variants.

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