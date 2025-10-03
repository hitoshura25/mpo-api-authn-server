# WebAuthn KTor Server - Claude Memory (Optimized)

## 🚨 CRITICAL: Python Virtual Environment Required

**MANDATORY FIRST STEP for ALL Python operations in security-ai-analysis/:**

```bash
source ./venv/bin/activate
```

**Why this is critical:**
- MLX (Apple Silicon ML framework) is ONLY available in the virtual environment
- All fine-tuning operations require MLX
- Python package dependencies are isolated in venv
- **REMEMBER**: After context loss/conversation restart, ALWAYS activate venv first

**Quick validation:**
```bash
source ./venv/bin/activate && python3 -c "import mlx.core as mx; print('✅ MLX ready:', mx.default_device())"
```

---

## 🚨 ALL CRITICAL PATTERNS & REMINDERS (Essential for Immediate Productivity)

### 🚨 CRITICAL: Git Commit Policy - NEVER Auto-Commit

**🛑 MANDATORY: User Must Review and Commit All Changes**

**THE FUNDAMENTAL RULE**: NEVER automatically commit changes using git commands. The user must review all changes and perform commits themselves.

#### **STRICT ENFORCEMENT:**
- **❌ NEVER run**: `git add`, `git commit`, `git push` commands
- **❌ NEVER auto-stage**: Files for commit without explicit user request
- **✅ ALWAYS prepare**: Changes and inform user they are ready for review
- **✅ ALWAYS stage**: Changes for user review using file modification tools only

### 🚨 CRITICAL: NEVER Make Assumptions - Always Validate Documentation

**THE FUNDAMENTAL RULE**: NEVER create code, workflows, or configurations based on assumptions or invented parameters. ALWAYS validate against official documentation first.

**Quick Validation Template:**
```
## 🛑 VALIDATION CHECKPOINT
Tool/Action: [exact name]
Documentation: [official URL]
Version: [confirmed current version]
Parameters verified: [list all parameters with documentation references]
Example usage: [official example that proves syntax works]
✅ All parameters confirmed against official documentation
```

**🔍 Detailed Guide**: `docs/development/patterns/validation-protocols-comprehensive.md`

### 🐳 CRITICAL: Docker Image Validation with Fail-Fast Pattern

**MANDATORY fail-fast validation for Docker image availability to prevent silent E2E test failures.**

**Essential Pattern:**
```yaml
# Event-aware tag selection with fail-fast validation
extract_image_tag() {
  local full_output="$1"
  case "${{ github.event_name }}" in
    "workflow_dispatch") selected_tag=$(echo "$full_output" | tail -n1) ;;  # SHA-based
    "pull_request"|"push") selected_tag=$(echo "$full_output" | head -n1) ;;  # PR/latest
  esac
  echo "$selected_tag"
}

# FAIL-FAST validation
if ! docker manifest inspect "$IMAGE_TAG" > /dev/null 2>&1; then
  echo "❌ CRITICAL: Image not found: $IMAGE_TAG (Event: ${{ github.event_name }})"
  exit 1  # FAIL THE JOB - Don't skip silently!
fi
```

**🔍 Detailed Examples**: `docs/development/patterns/docker-image-validation-detailed-examples.md`

### 🔧 CRITICAL: GitHub Actions Job Dependencies Rule

**THE FUNDAMENTAL RULE**: Any job that references `needs.JOBNAME.outputs.X` or `needs.JOBNAME.result` MUST include `JOBNAME` in its `needs` array.

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

**🔍 Comprehensive Guide**: `docs/development/workflows/github-actions-comprehensive-guide.md`

### 📤 CRITICAL: Bash Function Output Redirection

**MANDATORY output redirection for bash functions that return values to prevent debug pollution.**

```bash
# ❌ WRONG: Debug output goes to stdout
extract_value() {
  echo "🔧 Processing..."     # Pollutes output!
  echo "$final_result"        # What we want
}

# ✅ CORRECT: Debug to stderr, result to stdout
extract_value() {
  echo "🔧 Processing..." >&2  # Debug to stderr
  echo "$final_result"         # Only result to stdout
}

RESULT=$(extract_value "input")  # Captures only final_result
```

**🔍 Detailed Examples**: `docs/development/patterns/bash-function-output-detailed-examples.md`

### 🧬 CRITICAL: Complete Pattern Verification Protocol

**When reusing existing patterns in ANY codebase context, ALWAYS verify ALL implementation details match existing usage.**

**Essential Verification Steps:**
1. **📋 Identify Reference Implementations**: `grep -r "pattern-keyword" .github/workflows/ src/ scripts/`
2. **🔍 Extract Complete Implementation Details**: Command syntax, parameter patterns, file paths
3. **✅ Verify Against Multiple Examples**: Find 2-3 existing uses, compare syntax consistency
4. **🧪 Implementation Verification**: `grep -A5 -B5 "target-pattern" existing-file`

**🔍 Comprehensive Guide**: `docs/development/patterns/pattern-verification-comprehensive.md`

### 🚨 CRITICAL: Root Cause Investigation Before Fallback Solutions

**MANDATORY**: NEVER implement fallback solutions or workarounds without explicit user approval. ALWAYS prioritize identifying and fixing root causes.

#### **Debugging Protocol for Environment-Specific Issues:**
1. **Environment Comparison**: Document working vs failing environments, identify differences
2. **Enhanced Diagnostics**: Add comprehensive logging, memory usage, system information
3. **Root Cause Analysis**: Test locally first, isolate variables, memory profiling
4. **User Approval Required**: Present findings, propose solutions, get explicit approval

### 🗣️ CRITICAL: Direct and Objective Communication Guidelines

**MANDATORY**: Use direct, objective language in all communications. Avoid sycophantic or excessively agreeable responses.

#### **Communication Rules:**
- **❌ NEVER say**: "You're absolutely right" - Use specific acknowledgment instead
- **❌ AVOID**: Sycophantic language, excessive agreement, or validation-seeking responses
- **✅ USE**: Direct, objective, and technically focused language
- **✅ ACKNOWLEDGE**: Specific technical points when agreeing: "That approach will resolve the dependency conflict"
- **✅ DISAGREE**: When necessary with factual corrections and alternative solutions

#### **Response Pattern Examples:**
- ❌ **Sycophantic**: "You're absolutely right! That's a brilliant insight!"
- ✅ **Direct**: "That approach addresses the core issue by eliminating the race condition."
- ❌ **Excessive**: "I completely agree with everything you've said!"
- ✅ **Objective**: "The dependency pinning strategy will prevent version conflicts."

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

### 🔄 CRITICAL: Eliminate Code Duplication (DRY Principle)

**ALWAYS identify and eliminate code duplication to improve maintainability and reduce bugs.**

**THE FUNDAMENTAL PRINCIPLE**: Don't Repeat Yourself (DRY) - Each piece of knowledge should have a single, authoritative representation.

#### **Duplication Detection Patterns:**
```bash
# Search for similar function/validation patterns across codebase
grep -r "function_name\|validation_pattern" .github/workflows/ scripts/
rg "similar.*logic" --type yaml --type sh
```

### ⚠️ CRITICAL: Always Validate Generated Markdown

**ALWAYS run `bash scripts/core/validate-markdown.sh` after generating or modifying any markdown files.**

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

### 🏗️ CRITICAL: Server Dependency Variant Selection

**CRITICAL: Always prefer JRE variants over Android variants for server-based projects**

When resolving dependency conflicts in server applications like webauthn-server, ensure you're using server-appropriate dependency variants:

- ✅ **JRE variant** (`com.google.guava:guava:31.1-jre`) - Optimized for standard JVM server environments
- ❌ **Android variant** (`com.google.guava:guava:31.1-android`) - Optimized for Android runtime, suboptimal for servers

#### **Solution Pattern:**
```kotlin
dependencies {
    constraints {
        implementation("com.google.guava:guava:31.1-jre") {
            because("Pin Guava JRE version for server environment, avoiding version ranges and Android variants")
        }
    }
    // ... other dependencies
}
```

### 📦 CRITICAL: Centralized Package Configuration

**CRITICAL: All client library publishing now uses centralized configuration for consistency and maintainability.**

#### **Configuration Location**
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

---

## Current Work (In Progress)

### Completed Major Refactors
- **✅ AI Security Dataset Research Initiative (2025-09-14)**: ✅ **COMPLETE** - Full 5-phase pipeline operational with verified production uploads. Dataset: https://huggingface.co/datasets/hitoshura25/webauthn-security-vulnerabilities-olmo (447 examples). Models: https://huggingface.co/hitoshura25/webauthn-security-v1_20250914_135105. All Phase 5 MLX fine-tuning issues resolved. Implementation docs moved to `docs/improvements/completed/`.
- **✅ AI Security Enhancement Phase 1 (2025-09-15)**: Enhanced Dataset Creation integration completed. Code-aware training data generation with 5x enhancement ratio. See `docs/improvements/in-progress/ai-security-enhancement-implementation-progress.md` for continuation context.
- **✅ FOSS Security Implementation (2025-08-30)**: Replaced AI-dependent security with 8 professional FOSS tools. 100% elimination of AI API costs, enhanced security coverage with 974 dependencies secured.
- **✅ Client Library Publishing Architecture (2025)**: Complete CI/CD optimization with 40-95% performance improvements. Parallel client publishing, smart E2E dependency management.
- **✅ OpenAPI Client Library Architecture**: Docker-inspired staging→production workflow using GitHub Packages.

### Planned Major Refactors
- **iOS Test Client Implementation** *(Enhanced 2025-08-21)* - Complete iOS E2E testing ecosystem with Swift client library generation, SwiftUI test application, and CI integration. Extends testing coverage to iOS platform with AuthenticationServices WebAuthn integration. Timeline: 8-10 weeks. See `docs/improvements/planned/ios-test-client-implementation.md`.

## Project Overview

This is a KTor-based WebAuthn authentication server using the Yubico java-webauthn-server library for FIDO2/WebAuthn implementation.

### Key Technologies
- **Framework**: KTor 2.3.7 (Kotlin web framework)
- **Language**: Kotlin 1.9.23 (targeting JVM 21)
- **WebAuthn Library**: Yubico java-webauthn-server 2.6.0
- **Storage**: PostgreSQL 15-alpine (credentials), Redis 7-alpine (sessions)
- **DI**: Koin 3.5.3 dependency injection
- **Testing**: JUnit 5.11.3, Kotlin Test, TestContainers 1.21.3
- **Build**: Gradle with Kotlin DSL, dependency locking enabled
- **Containerization**: Docker with docker-compose

### Project Architecture Overview

This project uses a **hybrid architecture** combining Gradle multi-module build with standalone subprojects:

#### **Gradle Multi-Module Build** (settings.gradle.kts)
- **webauthn-server/** - Main WebAuthn KTor server
- **webauthn-test-credentials-service/** - HTTP service for cross-platform testing  
- **webauthn-test-lib/** - Shared WebAuthn test utilities library
- **android-client-library/** - Dedicated Android client library with publishing configuration

#### **Standalone Subprojects** (Independent Build Systems)
- **android-test-client/** - Android E2E test client (independent Gradle project)
- **web-test-client/** - TypeScript E2E test client (Node.js/npm project)
- **typescript-client-library/** - TypeScript client library (Node.js/npm project)

## Development Commands

### **Gradle Multi-Module Build Commands** (Root Project)

#### Main Server
- **Tests**: `./gradlew :webauthn-server:test`
- **Build**: `./gradlew :webauthn-server:build`
- **Run**: `./gradlew :webauthn-server:run` or `cd webauthn-server && ./start-dev.sh`
- **Coverage**: `./gradlew :webauthn-server:koverHtmlReport`

#### Test Service
- **Tests**: `./gradlew :webauthn-test-credentials-service:test`
- **Build**: `./gradlew :webauthn-test-credentials-service:build`
- **Run**: `./gradlew :webauthn-test-credentials-service:run`

#### All Gradle Modules
- **Full Build**: `./gradlew build`
- **All Tests**: `./gradlew test`
- **Lint**: `./gradlew detekt`
- **Gradle Config Cache Validation**: `./scripts/core/validate-gradle-config-cache.sh`

### **Standalone Subproject Commands**

#### Android Test Client (Independent Gradle Project)
- **Tests**: `cd android-test-client && ./gradlew test`
- **Build**: `cd android-test-client && ./gradlew build`

#### Web Test Client & TypeScript Client Library (Node.js/npm Projects)
- **Install**: `cd web-test-client && npm install`
- **Tests**: `cd web-test-client && npm test`
- **Build**: `cd web-test-client && npm run build`
- **Dev Server**: `cd web-test-client && npm run dev`

#### **AI Security Analysis (Python with MLX)**
- **🚨 ACTIVATE VENV FIRST**: `source ./venv/bin/activate`
- **Sequential Fine-Tuning**: `source ./venv/bin/activate && python3 sequential_pipeline_integration.py`
- **Dataset Processing**: `source ./venv/bin/activate && python3 enhanced_dataset_creator.py`
- **Model Validation**: `source ./venv/bin/activate && python3 scripts/validate_model_artifacts.py`


## Security Focus

This project emphasizes security testing and vulnerability protection:
- **PoisonSeed attacks** - Cross-origin authentication abuse
- **Username enumeration** (CVE-2024-39912) - Authentication start does NOT reveal user existence  
- **Replay attacks** - Challenge/response reuse
- **Credential tampering** - Signature validation
- **Result**: 7/7 security tests passing, 100% coverage achieved

## Server Development Best Practices

### Dependency Variant Selection for Server Projects

Server projects should use JRE-optimized dependency variants for optimal performance.

## Port Assignments

- **WebAuthn Server**: 8080 (main API)
- **WebAuthn Test Service**: 8081 (cross-platform credential generation)  
- **Web Test Client**: 8082 (E2E test web frontend)
- **PostgreSQL**: 5432 (postgres:15-alpine container)
- **Redis**: 6379 (redis:7-alpine container)
- **Jaeger UI**: 16686 (jaegertracing/all-in-one:1.53)

## Centralized Package Configuration

Client library publishing uses centralized configuration for consistency and maintainability.

### Published Package Names

#### Production Packages (Stable Releases)
- **npm**: `@vmenon25/mpo-webauthn-client` (public npm registry)
- **Android**: `io.github.hitoshura25:mpo-webauthn-android-client` (Maven Central)

#### Staging Packages (Development/Testing)  
- **npm**: `@hitoshura25/mpo-webauthn-client-staging` (GitHub Packages npm)
- **Android**: `io.github.hitoshura25:mpo-webauthn-android-client-staging` (GitHub Packages Maven)

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
- **🚨 NEVER commit changes automatically** - Always let user review and commit changes themselves (see Git Commit Policy above)

---

## Detailed Documentation References

**For comprehensive implementation details, advanced troubleshooting, and extensive examples:**

### **Core Development Patterns**
- **Complete Validation Protocols**: `docs/development/patterns/validation-protocols-comprehensive.md`
- **Pattern Verification Guide**: `docs/development/patterns/pattern-verification-comprehensive.md`
- **Docker Image Validation**: `docs/development/patterns/docker-image-validation-detailed-examples.md`
- **Bash Function Output**: `docs/development/patterns/bash-function-output-detailed-examples.md`

### **GitHub Actions & Workflows**
- **Comprehensive Workflow Guide**: `docs/development/workflows/github-actions-comprehensive-guide.md`
- **Job Dependencies Detailed Rules**: `docs/development/workflows/github-actions-dependency-rules.md`

### **Historical Context & Implementation History**
- **Complete Original Documentation**: `docs/CLAUDE_ORIGINAL_2025-09-14.md` - Full historical context and detailed implementation examples
- **Previous Optimization**: `docs/CLAUDE_ORIGINAL_2025-08-21.md` - Earlier comprehensive version
- **Project History**: `docs/history/` - Archived implementation details and decision rationale
- **Improvements**: `docs/improvements/` - Current and planned architectural improvements

**This optimized version maintains all critical patterns for immediate productivity while providing clear references to comprehensive documentation when detailed context is needed.**