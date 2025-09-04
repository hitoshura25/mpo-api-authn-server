# WebAuthn KTor Server - Claude Memory (Optimized)

## Current Work (In Progress)

### Active Tasks
- **AI Security Dataset Research Initiative**: Comprehensive research project leveraging our WebAuthn security findings (8 FOSS tools, 103 Semgrep findings, 1 Dependabot alert, ZAP analysis) to contribute to AI2/OLMo and advance AI security capabilities. Multi-model evaluation framework for security explanation quality, remediation guidance, and safety assessment. See `docs/improvements/planned/ai-security-dataset-research.md` for complete research plan.

### Completed Major Refactors
- **FOSS Security Implementation (2025-08-30)**: ✅ **COMPLETED** - Successfully replaced AI-dependent security solutions with 8 professional FOSS tools (Trivy, OSV-Scanner, Semgrep, GitLeaks, Checkov, OWASP ZAP, Dependabot, Gradle Dependency Locking). Achieved 100% elimination of AI API costs, enhanced security coverage with 974 dependencies secured, and established foundation for AI security research. Complete architecture delivers SARIF integration, PR comments, and GitHub Security tab functionality.
- **Client Library Publishing Architecture Cleanup (PHASES 1-10 COMPLETED)**: ✅ **COMPLETED** - Successfully implemented complete CI/CD optimization with independent component processing achieving 40-95% performance improvements. **Phase 10** delivered correct architecture with parallel client publishing, eliminated duplicate change detection, and smart E2E dependency management. Key results: client libraries publish immediately when OpenAPI changes (not after full build pipeline), true parallel execution of builds + publishing, and comprehensive E2E cache optimization.
- **OpenAPI Client Library Architecture**: ✅ **COMPLETED** - Docker-inspired staging→production workflow using GitHub Packages with dedicated client library submodules.

### Planned Major Refactors
- **iOS Test Client Implementation** *(Enhanced 2025-08-21)* - Complete iOS E2E testing ecosystem with Swift client library generation, SwiftUI test application, and CI integration. Extends testing coverage to iOS platform with AuthenticationServices WebAuthn integration. Timeline: 8-10 weeks. See `docs/improvements/planned/ios-test-client-implementation.md`.

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

## 🛑 **MANDATORY CHECKPOINT: VALIDATE BEFORE ANY EXTERNAL INTEGRATION**

**⚠️ STOP - READ THIS EVERY TIME BEFORE WRITING CODE ⚠️**

### **🔒 ENFORCEMENT RULE: NO CODE WITHOUT VALIDATION**

**BEFORE writing a SINGLE LINE of code that uses external tools/APIs/actions:**

#### **STEP 1: MANDATORY DOCUMENTATION RESEARCH**
- [ ] **Find Official Docs**: GitHub Marketplace page or official documentation site
- [ ] **Verify Action/Tool Exists**: Confirm the exact action/tool name and repository  
- [ ] **Check Version**: Verify the version (@v1, @v2, etc.) is current and not deprecated
- [ ] **Read ALL Parameters**: Document every single input parameter that exists

#### **STEP 2: MANDATORY PARAMETER VALIDATION** 
- [ ] **List Required Parameters**: What parameters are mandatory?
- [ ] **List Optional Parameters**: What parameters are available but optional?
- [ ] **Validate Syntax**: Confirm exact spelling, case sensitivity, data types
- [ ] **Check Examples**: Find official examples that show actual usage

#### **STEP 3: MANDATORY IMPLEMENTATION CHECK**
- [ ] **State Documentation Source**: "Based on [official docs URL]..."
- [ ] **Confirm All Parameters**: "Verified parameters X, Y, Z exist in official docs"
- [ ] **No Assumptions Made**: "All syntax confirmed against official examples"

### **🚨 VIOLATION CONSEQUENCES**
**If you proceed without completing ALL validation steps:**
- **Workflow will likely fail** with parameter errors
- **Time will be wasted** on non-functional implementations  
- **User confidence will be damaged** by repeated failures
- **Session will be terminated** to prevent further invalid implementations

### **🔍 VALIDATION TEMPLATE - USE THIS EVERY TIME**

Before implementing any external tool, ALWAYS state:

```
## 🛑 VALIDATION CHECKPOINT
Tool/Action: [exact name]
Documentation: [official URL] 
Version: [confirmed current version]
Parameters verified: [list all parameters with documentation references]
Example usage: [official example that proves syntax works]
✅ All parameters confirmed against official documentation
```

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

#### **Recent Critical Example: FOSS Security Tools Validation Failure (2025-08-27)**
**What Went Wrong:**
- **GitLeaks**: Assumed `gitleaks/gitleaks-action@v2` generates SARIF files (it doesn't)
- **Checkov**: Used manual pip installation instead of official `bridgecrewio/checkov-action@master`
- **OWASP ZAP**: Completely invented custom Docker automation framework syntax
- **Result**: 3 workflows with non-functional implementations, violated CLAUDE.md validation rules

**What Should Have Been Done:**
1. **GitLeaks**: Research revealed action only creates GitHub issues, no SARIF output
2. **Checkov**: Official action `bridgecrewio/checkov-action@master` with proper parameters
3. **OWASP ZAP**: Use official actions `zaproxy/action-full-scan` and `zaproxy/action-baseline`

**Validation Research Results:**
```
✅ GitLeaks: gitleaks/gitleaks-action@v2 (env: GITHUB_TOKEN only)
✅ Checkov: bridgecrewio/checkov-action@master (with: directory, output_format, etc.)
✅ OWASP ZAP: zaproxy/action-full-scan@v0.10.0 (with: target, rules_file_name)
```

**Why This Happened Again:**
- Skipped mandatory validation checkpoint despite CLAUDE.md warnings
- Assumed parameter syntax without checking official documentation
- Invented complex configurations instead of using simple official actions

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

### 🚨 CRITICAL: Git Commit Policy - NEVER Auto-Commit

**🛑 MANDATORY: User Must Review and Commit All Changes**

**THE FUNDAMENTAL RULE**: NEVER automatically commit changes using git commands. The user must review all changes and perform commits themselves.

#### **STRICT ENFORCEMENT:**
- **❌ NEVER run**: `git add`, `git commit`, `git push` commands
- **❌ NEVER auto-stage**: Files for commit without explicit user request
- **✅ ALWAYS prepare**: Changes and inform user they are ready for review
- **✅ ALWAYS stage**: Changes for user review using file modification tools only

#### **Correct Workflow Pattern:**
1. **Make Changes**: Use Edit, Write, MultiEdit tools to modify files
2. **Inform User**: "Changes are ready for your review and commit"
3. **Let User Review**: User examines changes using git tools or IDE
4. **User Commits**: User decides when and how to commit changes

#### **Why This Is Critical:**
- **User Control**: User maintains full control over commit history and messages
- **Change Review**: User can review and potentially modify changes before commit
- **Commit Messages**: User can write appropriate commit messages for their workflow
- **Git History**: User maintains clean, intentional git history
- **Rollback Control**: User can selectively stage/unstage changes as needed

#### **Exception:**
- **Only when explicitly requested**: User says "commit these changes" or "create a commit"
- **Even then, confirm**: Ask for commit message and get explicit confirmation

**VIOLATION**: Automatically committing changes without user approval breaks user workflow and removes their control over the development process.

## Critical Development Reminders

### 🧬 CRITICAL: Complete Pattern Verification Protocol (FUNDAMENTAL!)
**When reusing existing patterns in ANY codebase context, ALWAYS verify ALL implementation details match existing usage, not just architectural concepts.**

**THE FUNDAMENTAL PROBLEM**: Assuming architectural understanding equals implementation accuracy across ALL code generation contexts.

#### **Universal Pattern Verification Checklist:**

**BEFORE implementing any code that reuses existing patterns (workflows, scripts, configs, application code, build files, etc.):**

1. **📋 Identify Reference Implementations**:
   ```bash
   # Find ALL existing implementations of the pattern across the codebase
   grep -r "pattern-keyword" .github/workflows/ src/ scripts/ *.gradle *.yml *.json
   find . -name "*.kt" -o -name "*.ts" -o -name "*.yml" | xargs grep "pattern"
   ```

2. **🔍 Extract Complete Implementation Details**:
   - **Command syntax**: Exact commands, spaces, hyphens, flags, ordering
   - **Parameter patterns**: Order, format, quoting style, escaping
   - **File paths**: Relative vs absolute, naming conventions, directory structure
   - **Environment variables**: Names, formats, scoping, default values
   - **Error handling**: Patterns for failures, cleanup, exit codes, conditions
   - **Code conventions**: Indentation, spacing, variable naming, function signatures
   - **Configuration syntax**: Key names, nesting, data types, comment styles

3. **✅ Verify Against Multiple Examples**:
   - **Find 2-3 existing uses** of the same pattern in different contexts
   - **Compare syntax consistency** across all examples
   - **Identify project-specific conventions** vs language/tool standards
   - **Note context-specific variations** (test vs production, different modules)

4. **🧪 Implementation Verification Pattern**:
   ```bash
   # Extract exact syntax from existing implementations
   grep -A5 -B5 "target-pattern" existing-file
   
   # Verify your new implementation matches EXACTLY
   diff <(grep "your-pattern" existing-file) <(grep "your-pattern" new-file)
   
   # For complex patterns, extract full context blocks
   sed -n '/start-pattern/,/end-pattern/p' reference-file
   ```

#### **Pattern Verification Examples by Context:**

**✅ CORRECT Process Examples:**

**GitHub Actions:**
```bash
grep -r "docker.*compose" .github/workflows/
# Found: docker compose (space, not hyphen) → Use exactly
```

**Kotlin/Gradle Code:**
```bash
grep -r "implementation.*webauthn" *.gradle.kts
# Found: implementation("com.yubico:webauthn-server-core:2.6.0") → Match format
```

**Script Patterns:**
```bash
grep -r "set -euo pipefail" scripts/
# Found: set -euo pipefail (specific flags) → Use same flags
```

**Configuration Files:**
```bash
grep -A3 "environment:" docker-compose*.yml
# Found: specific indentation and key patterns → Match exactly
```

**Application Code:**
```bash
grep -r "class.*Test" src/
# Found: class SomeTest : BaseIntegrationTest() → Follow naming pattern
```

#### **Common Pattern Verification Failures Across All Contexts:**

**Command/Script Syntax:**
- `docker-compose` vs `docker compose`, `npm run` vs `npx`, flag ordering
- `./gradlew` vs `gradle`, relative vs absolute script paths
- Shell options: `set -e` vs `set -euo pipefail`

**Code Conventions:**
- Function naming: `camelCase` vs `snake_case`, prefix patterns
- Import statements: relative vs absolute, ordering, grouping
- Error handling: `try-catch` vs `Result<T>`, exception types

**Configuration Syntax:**
- YAML indentation (2 vs 4 spaces), key naming (`snake_case` vs `kebab-case`)
- JSON formatting, comment styles, environment variable patterns
- Build file conventions: dependency declarations, plugin application

**File Organization:**
- Directory structure: `src/main/kotlin` vs `src/kotlin`
- Test file naming: `*Test.kt` vs `*Tests.kt` vs `Test*.kt`
- Resource file locations and naming patterns

#### **Context-Specific Verification Commands:**

```bash
# Workflow/CI Patterns
grep -r "docker.*compose\|npm.*run\|gradle.*build" .github/workflows/

# Application Code Patterns
grep -r "class.*\|fun.*\|val.*" src/main/kotlin/ src/test/kotlin/

# Script Patterns  
grep -r "set.*\|if.*then\|function.*" scripts/

# Configuration Patterns
grep -r "environment:\|ports:\|version:" *.yml *.yaml
grep -r "implementation\|testImplementation" *.gradle.kts

# Build/Dependency Patterns
grep -r "plugins.*\|dependencies.*\|repositories.*" build.gradle.kts */build.gradle.kts
```

#### **Critical Real-World Examples:**

**August 2025 - Docker Compose Commands**: Used `docker-compose` instead of `docker compose`
- **Root Cause**: Understood Docker Compose architecture but didn't verify command syntax
- **Pattern**: Good architectural grasp, missed implementation details

**Previous - Gradle Dependencies**: Wrong dependency syntax format
- **Root Cause**: Assumed standard Gradle syntax instead of checking project patterns
- **Pattern**: External knowledge applied without local verification

**Previous - Test File Naming**: Inconsistent test class naming conventions
- **Root Cause**: Used general conventions instead of project-specific patterns
- **Pattern**: Generic best practices overrode local consistency

#### **UNIVERSAL ENFORCEMENT RULE:**
**Every reused pattern must show `grep`/`find` evidence of existing usage before implementation, regardless of context (workflows, code, configs, scripts, documentation).**

#### **Integration with Existing Tools:**
- **IDE Search**: Use project-wide search before implementing patterns
- **Git History**: `git log --grep="pattern"` to understand pattern evolution  
- **Code Review**: Verify pattern consistency in review process
- **Linting**: Configure linters to enforce discovered patterns

**Why This Matters Universally:**
- **Consistency**: Maintains codebase coherence across all contexts
- **Maintainability**: Reduces cognitive load for developers
- **Reliability**: Prevents subtle bugs from syntax/convention mismatches
- **Quality**: Ensures new code follows established, proven patterns

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

### 🐳 CRITICAL: Docker Image Validation with Fail-Fast Pattern (RECURRING ISSUE!)

**MANDATORY fail-fast validation for Docker image availability to prevent silent E2E test failures.**

**THE RECURRING PROBLEM**: Multi-line Docker image tags from docker/metadata-action cause E2E validation to check wrong tags, leading to silent test skipping instead of clear failures.

#### **Critical Issue Pattern (Happened Multiple Times):**
```yaml
# Docker build outputs multi-line tags:
webauthn_server_image: |
  ghcr.io/repo/image:latest
  ghcr.io/repo/image:sha256-abc123-branch-main-123

# E2E validation naively uses first line:
docker manifest inspect "${{ env.WEBAUTHN_SERVER_IMAGE }}"  # Only checks 'latest'!

# Result: 'latest' doesn't exist → validation fails → E2E tests SKIP SILENTLY
```

#### **Mandatory Docker Validation Pattern:**
```yaml
# ✅ CORRECT: Event-aware tag selection with fail-fast validation
extract_image_tag() {
  local full_output="$1"
  local line_count=$(echo "$full_output" | wc -l)
  
  if [[ $line_count -gt 1 ]]; then
    case "${{ github.event_name }}" in
      "workflow_dispatch") 
        selected_tag=$(echo "$full_output" | tail -n1)  # SHA-based tag
        ;;
      "pull_request"|"push") 
        selected_tag=$(echo "$full_output" | head -n1)  # PR/latest tag
        ;;
    esac
  else
    selected_tag="$full_output"  # Single tag
  fi
  
  echo "$selected_tag"
}

# Validate with FAIL-FAST logic
if ! docker manifest inspect "$IMAGE_TAG" > /dev/null 2>&1; then
  echo "❌ CRITICAL ERROR: Image not found: $IMAGE_TAG"
  echo "Event: ${{ github.event_name }}, Branch: ${{ github.ref_name }}"
  echo "❌ FAILING FAST: E2E tests require valid Docker images"
  exit 1  # FAIL THE JOB - Don't skip silently!
fi
```

#### **Event-Specific Tag Selection Logic:**
- **`workflow_dispatch`**: Use SHA-based tag (last line) - `sha256-abc123-branch-main-123`
- **`pull_request`**: Use PR tag (first line) - `pr-123`  
- **`push` to main**: Use latest tag (first line) - `latest`
- **`push` to feature**: Use branch tag (first line) - `branch-feature-name`

#### **Why Fail-Fast is Critical:**
```yaml
# ❌ WRONG: Silent skipping masks infrastructure failures
if: needs.validate-images.outputs.webauthn-server-ready == 'true'  # Silently skips if false

# ✅ CORRECT: Fail-fast exposes the real problem immediately  
# validate-images job exits with error code 1 → entire workflow fails with clear error
```

#### **Validation Requirements:**
- [ ] **Multi-line tag detection**: Count lines in Docker image output
- [ ] **Event-aware selection**: Use correct tag based on `github.event_name`
- [ ] **Format validation**: Ensure extracted tag contains no newlines
- [ ] **Registry authentication**: Login before manifest inspection
- [ ] **Clear error reporting**: Include event type, branch, original input in error messages
- [ ] **Fail-fast behavior**: `exit 1` on any validation failure
- [ ] **Success confirmation**: Only set output variables after ALL images validated

#### **Testing All Event Types:**
```bash
# Validate pattern works for all event types:
# 1. Pull Request → Should use first tag (pr-XXX)
# 2. Push to main → Should use first tag (latest) 
# 3. Push to feature → Should use first tag (branch-name)
# 4. Workflow dispatch → Should use last tag (SHA-based)
```

**This pattern prevents:**
- Silent E2E test skipping due to wrong tag validation
- Infrastructure issues being masked as conditional skips
- Recurring debugging sessions for "why didn't E2E tests run?"
- Workflow completing successfully while missing critical testing

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
- **❌ NEVER use compound arithmetic increment operations like `((VAR++))`** - Use safe assignment: `VAR=$((VAR + 1))`
- **✅ Use `always() &&` prefix when job should evaluate conditions even if dependencies are skipped**

#### **🚨 CRITICAL: Bash Arithmetic Operations in GitHub Actions (August 2025)**
**GitHub Actions strict error handling can cause arithmetic operations to fail with exit code 1:**

```bash
# ❌ WRONG: Compound increment operations can fail in GitHub Actions
((EXECUTED_COUNT++))              # Can exit with code 1
[[ "$WEB_EXECUTED" == "true" ]] && ((EXECUTED_COUNT++))

# ✅ CORRECT: Safe arithmetic assignment operations
EXECUTED_COUNT=$((EXECUTED_COUNT + 1))     # Safe increment
if [[ "$WEB_EXECUTED" == "true" ]]; then
  EXECUTED_COUNT=$((EXECUTED_COUNT + 1))   # Safe conditional increment
fi
```

**WHY THIS HAPPENS:**
- **GitHub Actions Environment**: Runs with strict error handling (`set -e` equivalent behavior)
- **Arithmetic Expansion**: `((expr))` can return non-zero exit codes for certain operations
- **Pre-increment Evaluation**: `VAR++` evaluates current value before incrementing, causing issues when starting from 0

#### **🚨 CRITICAL: Format Migration Validation (August 2025)**
**When changing output formats (JSON↔SARIF, CSV↔JSON, etc.), ALWAYS validate ALL references are updated to prevent silent failures:**

**THE PROBLEM**: Format migrations often leave stale references causing workflows to succeed but produce wrong results.

#### **Mandatory Format Migration Checklist:**
- [ ] **Environment Variables**: Update all `*_FILE` environment variables to new format
- [ ] **Artifact Uploads**: Remove old format from upload paths
- [ ] **Processing Scripts**: Update all file loading/parsing logic
- [ ] **Function Implementations**: Ensure format-specific functions exist and work
- [ ] **Workflow Dependencies**: Verify downstream jobs expect the new format
- [ ] **Integration Testing**: Validate workflow output matches script input

#### **Common Format Migration Failures:**
```yaml
# ❌ WRONG: Environment variable still points to old format
env:
  SCAN_RESULTS_FILE: results.json  # But workflow generates results.sarif

# ✅ CORRECT: All references updated to new format  
env:
  SCAN_RESULTS_FILE: results.sarif

# ❌ WRONG: Artifact upload includes non-existent old format files
path: |
  results.json   # Doesn't exist anymore
  results.sarif  
  
# ✅ CORRECT: Only upload files that actually exist
path: |
  results.sarif
```

#### **Validation Pattern:**
```bash
# Verify ALL format references updated
grep -r "old-format-extension" .github/workflows/ scripts/
grep -r "OLD_FORMAT_FILE" .github/workflows/
```

**Recent Example**: Trivy SARIF-only optimization failed because:
- ✅ Workflow generated SARIF correctly (69 vulnerabilities found)
- ❌ Environment variable still referenced JSON (`results.json`)
- ❌ Script loaded wrong file, showing 0 vulnerabilities in PR comments
- ❌ Artifact upload still tried to include non-existent JSON files

**Prevention**: Always trace data flow from generation → processing → consumption when changing formats.

#### **🚨 CRITICAL: Secrets Cannot Be Referenced in if Conditions (Recurring Issue)**
**GitHub Actions security limitation: Secrets cannot be accessed directly in workflow if conditions.**

**FAILURE PATTERN:**
```yaml
# ❌ WRONG: This causes "Unrecognized named-value: 'secrets'" error
- name: Upload to service
  if: inputs.enable_upload == true && secrets.API_TOKEN != ''
```

**SOLUTION PATTERN:**
```yaml
# ✅ CORRECT: Use job/step outputs to handle secret availability
jobs:
  my-job:
    outputs:
      service_enabled: ${{ steps.check-token.outputs.enabled }}
    
    steps:
      - name: Check service token availability  
        id: check-token
        run: |
          if [[ "${{ secrets.API_TOKEN }}" != "" ]]; then
            echo "enabled=true" >> $GITHUB_OUTPUT
          else
            echo "enabled=false" >> $GITHUB_OUTPUT
          fi
      
      - name: Upload to service
        if: inputs.enable_upload == true && steps.check-token.outputs.enabled == 'true'
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
        run: |
          # Use the secret here in env, not in if condition
```

**WHY THIS RESTRICTION EXISTS:**
- **Security**: Prevents accidental secret exposure in workflow logs
- **GitHub Policy**: Secrets are only accessible in `env:` context and step `run:` blocks
- **Error Prevention**: Stops workflows from accidentally logging secret values

**RECENT EXAMPLE:** OLMo Security Analysis workflow failed with HF_TOKEN reference in if condition. Fixed by creating `huggingface_enabled` output.

**Prevention**: Always use step outputs to check secret availability before using secrets in conditional steps.

#### **🚨 CRITICAL: Bash Arithmetic Operations in GitHub Actions (August 2025)**
**GitHub Actions strict error handling can cause arithmetic operations to fail with exit code 1:**

**VALIDATION PATTERN:**
```bash
# Test arithmetic operations locally before committing
set -e  # Enable strict error handling
COUNTER=0
COUNTER=$((COUNTER + 1))  # Safe - test this pattern
echo "Counter: $COUNTER"
```

**Recent Example**: DAST scan integration failed with exit code 1 in cross-platform analysis due to `((EXECUTED_COUNT++))` operations. Fixed by using `EXECUTED_COUNT=$((EXECUTED_COUNT + 1))` pattern.


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
- **🚨 NEVER commit changes automatically** - Always let user review and commit changes themselves (see Git Commit Policy above)

---

## Historical Context

**For detailed implementation history, troubleshooting guides, and comprehensive lessons learned, see:**
- **Complete Original**: `docs/CLAUDE_ORIGINAL_2025-08-21.md` - Full historical context and detailed implementation examples
- **Project History**: `docs/history/` - Archived implementation details and decision rationale
- **Improvements**: `docs/improvements/` - Current and planned architectural improvements