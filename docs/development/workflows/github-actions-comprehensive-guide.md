# GitHub Actions Comprehensive Development Guide

This document contains extensive GitHub Actions patterns and detailed examples extracted from CLAUDE.md for reference.

## Table of Contents
- [Callable Workflow Environment Variable Pattern](#callable-workflow-env-var-pattern)
- [Job Dependencies Rule (Detailed)](#job-dependencies-rule-detailed)
- [Workflow Output Implementation Chain](#workflow-output-implementation-chain)
- [Change Detection Category Validation](#change-detection-category-validation)
- [Bash Arithmetic Operations](#bash-arithmetic-operations)
- [Format Migration Validation](#format-migration-validation)
- [Secrets in Conditional Logic](#secrets-in-conditional-logic)
- [Android Publishing & Docker Registry](#android-publishing--docker-registry)
- [Callable Workflow Input/Output Validation](#callable-workflow-inputoutput-validation)
- [E2E Test Caching Strategy](#e2e-test-caching-strategy)

## Callable Workflow Env Var Pattern

**🚨 CRITICAL: NEVER FORGET!**
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
  uses: ./.github/workflows/docker-build.yml
  needs: setup-config
  with:
    package-name: ${{ needs.setup-config.outputs.package-name }}  # ✅ CORRECT
    # package-name: ${{ env.PACKAGE_NAME }}  # ❌ WILL FAIL
```

## Job Dependencies Rule (Detailed)

**THE FUNDAMENTAL RULE**: ANY job that references `needs.JOBNAME.outputs.X` or `needs.JOBNAME.result` MUST include `JOBNAME` in its `needs` array.

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

### Callable Workflow Secrets Pattern
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

## Workflow Output Implementation Chain

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

**VALIDATION COMMANDS**:
```bash
# Verify job outputs exist in callable workflow
grep -A 10 "outputs:" .github/workflows/docker-build.yml
# Verify job sets the outputs  
grep "webauthn-server-image\|test-credentials-image" .github/workflows/docker-build.yml
```

## Change Detection Category Validation

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

## Bash Arithmetic Operations

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

**VALIDATION PATTERN:**
```bash
# Test arithmetic operations locally before committing
set -e  # Enable strict error handling
COUNTER=0
COUNTER=$((COUNTER + 1))  # Safe - test this pattern
echo "Counter: $COUNTER"
```

## Format Migration Validation

**When changing output formats (JSON↔SARIF, CSV↔JSON, etc.), ALWAYS validate ALL references are updated:**

**THE PROBLEM**: Format migrations often leave stale references causing workflows to succeed but produce wrong results.

### Mandatory Format Migration Checklist:
- [ ] **Environment Variables**: Update all `*_FILE` environment variables to new format
- [ ] **Artifact Uploads**: Remove old format from upload paths
- [ ] **Processing Scripts**: Update all file loading/parsing logic
- [ ] **Function Implementations**: Ensure format-specific functions exist and work
- [ ] **Workflow Dependencies**: Verify downstream jobs expect the new format
- [ ] **Integration Testing**: Validate workflow output matches script input

### Common Format Migration Failures:
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

### Validation Pattern:
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

## Secrets in Conditional Logic

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

## Android Publishing & Docker Registry

**MANDATORY patterns for Android publishing and Docker registry references to prevent configuration failures.**

### vanniktech Maven Publish Plugin GitHub Packages Configuration
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

### Docker Registry Reference Pattern
**ALWAYS use job outputs for Docker registry references, NEVER environment variables:**
```yaml
# ✅ CORRECT: Use job output from setup-config
docker-registry: ${{ needs.setup-config.outputs.docker-registry }}

# ❌ WRONG: Environment variables not available in callable workflow context
docker-registry: ${{ env.DOCKER_REGISTRY }}
```

**Root Cause**: Environment variables are not accessible in callable workflow contexts. Setup-config jobs MUST convert env vars to outputs first.

## Callable Workflow Input/Output Validation

**MANDATORY validation process for callable workflow refactoring to prevent input/output mismatch errors.**

### Input/Output Contract Validation (Recurring Issue Pattern)
**ALWAYS validate that inputs passed to callable workflows match their definitions:**

**Common Failure Pattern:**
- Enhance orchestrator workflow (e.g., `client-publish.yml`) to pass new input (`force-publish`)
- Forget to add corresponding input definition to called workflows (`publish-typescript.yml`, `publish-android.yml`)
- Result: "Invalid input, X is not defined in the referenced workflow" errors

### Mandatory Validation Checklist for Callable Workflow Changes:

**Before Any Callable Workflow Refactoring:**
- [ ] **Map All Input Dependencies**: Document which workflows call which other workflows
- [ ] **Input Contract Verification**: Ensure ALL inputs passed by callers are defined in callable workflows
- [ ] **Output Contract Verification**: Ensure ALL outputs referenced by callers are defined in callable workflows  
- [ ] **Secret Contract Verification**: Ensure ALL secrets passed are properly defined (excluding system secrets like `GITHUB_TOKEN`)
- [ ] **Permission Alignment**: Verify calling workflows have necessary permissions for callable workflows

### Systematic Validation Process:

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
yq eval '.on.workflow_call.inputs' .github/workflows/publish-android.yml
```

### Input/Output Synchronization Patterns:

**When Adding New Inputs to Orchestrator:**
1. **Add to Orchestrator**: Define input in orchestrator workflow (e.g., `client-publish.yml`)
2. **Add to All Callees**: Add same input to ALL workflows called by orchestrator
3. **Validate Contract**: Ensure input names, types, and requirements match exactly
4. **Test Locally**: Push to feature branch and verify GitHub Actions validation passes

**When Adding New Outputs:**
1. **Define in Callable**: Add output to callable workflow
2. **Reference in Caller**: Update calling workflow to use new output
3. **Chain Dependencies**: Update job dependency chains if new outputs affect conditions

### System Reserved Names to Avoid:
- **`GITHUB_TOKEN`**: Automatically available in all workflows, NEVER define in callable workflow secrets AND NEVER pass explicitly in secrets block of calling workflows
- **GitHub Context Variables**: `github.*` properties are automatically available
- **System Environment Variables**: Many system env vars are reserved and should not be overridden

### Validation Tools and Commands:
```bash
# Validate workflow syntax
find .github/workflows -name "*.yml" -exec yq eval . {} \; > /dev/null

# Check for input/output mismatches
grep -r "force-publish" .github/workflows/ | grep -E "(inputs|with):"

# Find callable workflow relationships  
grep -r "uses: ./.github/workflows/" .github/workflows/
```

## E2E Test Caching Strategy

**MANDATORY patterns for E2E test caching to prevent cache pollution between different execution contexts.**

### Branch/Event Context Isolation
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

### Cache Key Components for E2E Tests:
1. **Docker Images**: Hash of Docker image tags being tested
2. **Test Files**: Hash of E2E test files and configuration
3. **Branch Context**: PR number, main branch, or feature branch name
4. **Event Context**: pull_request vs push vs workflow_dispatch

### Benefits of Context Isolation:
- **Production Validation**: Main branch always gets fresh E2E validation
- **PR Independence**: Each PR gets isolated cache without pollution
- **Branch Isolation**: Feature branches don't interfere with main/PR caches
- **Debugging**: Clear cache key patterns for troubleshooting

### Cache Key Examples:
- **PR Run**: `web-e2e-results-{images}-{files}-pr-123`
- **Main Branch**: `web-e2e-results-{images}-{files}-main`
- **Feature Branch**: `web-e2e-results-{images}-{files}-branch-feat-new-feature`

**Why This Matters**: E2E test cache pollution can cause main branch production deployments to skip validation, leading to undetected integration issues in production.

## Common Workflow Issues to Avoid

- **❌ NEVER use `env.VARIABLE` in `if:` conditionals** - Use job outputs instead
- **❌ NEVER use `github.event.number`** - Use `github.event.pull_request.number`
- **❌ NEVER use `actions/github-script` with external file requires** - Use direct Node.js execution
- **❌ NEVER define outputs without verifying implementation chain** - Always validate job→step→value mapping
- **❌ NEVER add change detection without validating ALL downstream job conditions** - Change detection ≠ job execution
- **❌ NEVER use compound arithmetic increment operations like `((VAR++))`** - Use safe assignment: `VAR=$((VAR + 1))`
- **✅ Use `always() &&` prefix when job should evaluate conditions even if dependencies are skipped**