# WebAuthn KTor Server - Claude Memory (Optimized)

## Current Work (In Progress)

### Active Tasks
- No active tasks at this time - all major features completed

### Planned Major Refactors
- **FOSS Security Implementation**: Comprehensive plan to replace AI-dependent custom security solutions with established FOSS tools (Trivy Action, Semgrep, OWASP ZAP, Checkov, GitLeaks). Eliminates AI API costs and maintenance overhead. See `docs/security/FOSS_SECURITY_IMPLEMENTATION_PLAN.md` for complete implementation plan (5-7 week timeline)
- **OpenAPI Client Library Architecture**: Comprehensive plan to refactor from file-copying to Docker-inspired staging→production workflow using GitHub Packages. See `docs/OPENAPI_CLIENT_REFACTOR_PLAN.md` for complete implementation plan (8-11 week timeline)

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

### 🧹 CRITICAL: Dead Code Cleanup After Refactoring

**ALWAYS perform comprehensive cleanup after removing or refactoring functionality to eliminate orphaned code.**

#### **Mandatory Cleanup Checklist After Refactoring:**
- [ ] **Scripts & Tools**: Search for and remove unused scripts, especially in `scripts/ci/`, `scripts/docker/`, `scripts/security/`
- [ ] **Workflow References**: Update all workflow files that may reference removed jobs or scripts
- [ ] **Documentation Updates**: Update README.md, CLAUDE.md, and docs/ files to reflect changes
- [ ] **Environment Variables**: Remove unused env vars from workflow files and docker-compose
- [ ] **Configuration Files**: Clean up orphaned config files and references
- [ ] **Dependencies**: Remove unused npm/gradle dependencies introduced for removed features

#### **Search Strategy for Dead Code Detection:**
1. **Script Usage Search**: `grep -r "script-name" .` to find all references
2. **Workflow Job References**: Search workflows for removed job names and outputs
3. **Environment Variable Search**: Look for unused env vars in removed contexts
4. **Import/Dependency Analysis**: Check for unused imports or dependencies
5. **File Pattern Search**: Look for files matching removed feature patterns

#### **Examples of Common Dead Code:**
- **Removed Workflow Jobs**: AI security analysis scripts when jobs are consolidated
- **Renamed Workflows**: Old workflow name references in documentation
- **Refactored Features**: Scripts supporting removed functionality
- **Consolidated Tools**: Duplicate utilities after consolidation
- **Legacy Configurations**: Config files for removed services or features

#### **Documentation Requirements:**
- Update all relevant documentation to reflect architectural changes
- Remove references to deleted scripts or workflows
- Update workflow diagrams and process descriptions
- Add notes about why functionality was removed/consolidated

**Why This Matters**: Dead code creates maintenance burden, confusion, and potential security issues. Clean refactoring prevents technical debt accumulation.

**✅ Recent Success Example**: Security workflow consolidation (pr-security-analysis.yml → security-analysis.yml) included removal of unused ai-docker-security-analyzer.cjs and updating all references.

### 🏗️ CRITICAL: Callable Workflow Architecture

**The project now uses a modular callable workflow architecture for better maintainability and reusability:**

#### **Architecture Overview:**
- **Main Orchestrator**: `build-and-test.yml` (358 lines, down from 777 lines)
- **Unit Testing Module**: `unit-tests.yml` - Callable workflow for test execution and coverage
- **Docker Pipeline Module**: `docker-build.yml` - Callable workflow for build/scan/push operations

#### **Workflow Structure:**
1. **detect-changes**: Smart change detection and execution strategy (unchanged)
2. **run-unit-tests**: Calls `unit-tests.yml` with proper inputs/outputs
3. **docker-build-scan-push**: Calls `docker-build.yml` for complete Docker lifecycle
4. **report-build-results**: Results aggregation and status reporting (updated)

#### **Benefits Achieved:**
- **54% Size Reduction**: Main workflow reduced from 777 to 358 lines
- **Better Maintainability**: Logical separation of concerns
- **Improved Reusability**: Callable workflows can be used by other workflows
- **Preserved Functionality**: All conditional logic, job dependencies, and outputs maintained

#### **Key Implementation Details:**
- **Conditional Logic**: All `if:` conditions preserved exactly
- **Job Dependencies**: `needs:` relationships maintained with callable workflow outputs
- **Secret Passing**: Uses `secrets: inherit` for proper credential handling
- **Output Mapping**: Workflow outputs properly map to callable workflow results
- **Environment Variables**: Passed through to callable workflows correctly

#### **Usage Pattern for New Workflows:**
```yaml
unit-testing-job:
  uses: ./.github/workflows/unit-tests.yml
  with:
    changes-detected: true
    test-scope: 'all'
    java-version: '21'
  secrets: inherit

docker-operations-job:
  uses: ./.github/workflows/docker-build.yml  
  with:
    docker-changes-detected: true
    java-version: '21'
    push-enabled: true
  secrets: inherit
```

**Why This Matters**: Modular workflow architecture reduces complexity, improves maintainability, and enables better reuse across different CI/CD scenarios while preserving all existing functionality.

### ⚠️ CRITICAL: Always Validate Generated Markdown

**ALWAYS run `bash scripts/core/validate-markdown.sh` after generating or modifying any markdown files.**

- **Why**: Prevents syntax errors that break IDE display and documentation tools
- **When**: After any markdown generation, editing, or updates to documentation
- **Command**: `bash scripts/core/validate-markdown.sh`
- **Result**: Must show "🎉 All markdown files are valid!" before considering work complete

### 🔧 CRITICAL: GitHub Actions Workflow Development

**ALWAYS follow GitHub Actions best practices to prevent workflow failures:**

#### **Environment Variable Usage Rules:**
- **❌ NEVER use `env.VARIABLE` in `if:` conditionals** - GitHub Actions security restrictions prevent this
- **✅ ALWAYS use job outputs for conditionals** - Create setup jobs that convert env vars to outputs:
  ```yaml
  setup-job:
    outputs:
      tier-enabled: ${{ steps.config.outputs.tier-enabled }}
    steps:
      - id: config
        run: echo "tier-enabled=${TIER_ENABLED}" >> $GITHUB_OUTPUT
        env:
          TIER_ENABLED: ${{ env.TIER_ENABLED }}
  ```
- **✅ Reference job outputs in conditionals**: `needs.setup-job.outputs.tier-enabled == 'true'`

#### **Event Context Property Rules:**
- **❌ NEVER use `github.event.number` for PR numbers** - This property doesn't exist
- **✅ ALWAYS use `github.event.pull_request.number`** for pull request events
- **✅ Use conditional fallbacks** for workflows that handle multiple event types:
  ```yaml
  PR_NUMBER: ${{ github.event.pull_request.number || 'N/A' }}
  PR_TITLE: ${{ github.event.pull_request.title || github.event.head_commit.message }}
  PR_BODY: ${{ github.event.pull_request.body || 'Main branch push' }}
  ```
- **✅ Test multi-event workflows** with both pull request and push events

#### **Script Execution Patterns:**
- **❌ NEVER use `actions/github-script` with external file requires** - Sandboxed environment restrictions
- **✅ ALWAYS use direct Node.js execution**: `node scripts/security/script.cjs`
- **✅ Scripts must use environment variables**: Not GitHub Actions context objects
- **✅ Include cross-platform fetch helpers** for Node.js compatibility

#### **Common Shell Script Pitfalls:**
- **❌ Function ordering issues**: Functions must be defined before first call (move `log()` to script top)
- **❌ Case sensitivity errors**: Use `elif` not `Elif`, `then` not `Then`, etc.
- **❌ Action version assumptions**: Verify tagged versions exist, use `@main` if no `@v1` available
- **✅ Test scripts locally** before committing to catch syntax errors
- **✅ Use `set -euo pipefail`** for proper error handling

#### **Recently Fixed Issues (Manual Fixes Applied):**
1. **analyze-pr.sh Function Ordering**: `log` function called before definition - moved function to top of script
2. **generate-tests.sh Syntax Error**: `Elif` used instead of `elif` on line 39 - case sensitivity issue
3. **claude-code-security-review Action**: Used `@v1` but only `@main` exists - verify action versions before use

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
5. **Dead Code Cleanup**: ALWAYS remove unused scripts, files, and references after refactoring (see detailed guidance above)
6. **Git History**: Always use `git mv` instead of `mv` for file moves to preserve history
7. **Docker Image Validation**: ALWAYS verify Docker images exist before updating Dockerfiles
   - Use `docker manifest inspect <image>` to validate image existence
   - Check available tags with registry APIs or Docker Hub before specifying versions
   - Example: `eclipse-temurin:21.0.8_9-jre-jammy` (verified) vs `21.0.6_3-jre-jammy` (non-existent)
8. **GitHub Actions always() Conditional**: CRITICAL workflow dependency gotcha
   - Jobs are **automatically skipped** if ANY dependency in the **entire dependency chain** is skipped
   - This includes **indirect/transitive dependencies** - if A→B→C and A is skipped, C is also skipped
   - Use `always() &&` prefix when job should evaluate conditions even if dependencies are skipped
   - **Rule**: If ANY job in your dependency tree can be conditionally skipped, ALL downstream jobs need `always()`
   - **Common pattern**: `if: always() && needs.job.result == 'success' && other_conditions`
   - **Example failure**: Job with `needs: [job-that-depends-on-skipped-job]` will be skipped even if direct dependency ran
   - **Solution**: `if: always() && needs.dependency.outputs.value == 'true'` evaluates properly regardless of dependency chain
8. **GitHub Actions Permissions for PR Operations**: CRITICAL for automated PR interactions
   - **PR Commenting**: Requires both `pull-requests: write` AND `issues: write` permissions
   - **Security Scanning**: Requires `security-events: write` for uploading SARIF results
   - **Package Publishing**: Requires `packages: write` for Docker registry pushes
   - **Attestations**: Requires both `attestations: write` and `id-token: write` for build provenance
   - **Rule**: ALWAYS verify required permissions are set at both job level AND workflow level
   - **Common failure**: PR comment scripts fail with 403/422 errors when missing `issues: write` permission
9. **Docker Security Scan Architecture**: CRITICAL for proper image scanning workflow
   - **Scan Timing**: Security scan MUST run AFTER Docker build succeeds AND before registry push
   - **Image Source**: Rebuild images locally in security job (different runner from build job)
   - **Image Tags**: Use actual built image tags from build job outputs, NOT hardcoded `:latest`
   - **Job Dependencies**: Security scan job needs `needs.build-docker-images.result == 'success'` condition
   - **Runner Isolation**: Each job runs on separate runner - `load: true` images don't transfer between jobs
   - **Rebuild Strategy**: Rebuild with same tags as build job, leverages Docker layer cache for speed
   - **SARIF Format**: GitHub Security upload requires PURE SARIF (no custom fields like `summary`)
   - **SARIF Categories**: Each image must have unique SARIF category to avoid upload collision
   - **File Separation**: Use `.sarif` extension for GitHub Security, `.json` for PR comments with custom fields
   - **PR Comment Format**: PR script must handle consolidated scan results format, not direct Trivy format
   - **Common failures**: Assuming `load: true` images available across runners, SARIF category collisions, wrong data format for PR comments

### 🔍 CRITICAL: Script Integration & Testing Patterns

**ALWAYS validate script output formats and workflow data passing to prevent silent failures in complex integrations.**

#### **Data Structure Mismatch Prevention:**
- **Producer-Consumer Contract Validation**: Scripts that generate data MUST match consumer expectations exactly
- **Common Failure Pattern**: Security scan script outputs `{scans: [{image: "...", scans: {vulnerabilities: {...}}}]}` but PR comment consumer expects `{scans: [{image: "...", vulnerabilities: {...}}]}`
- **Result**: Vulnerability counts show as 0 when they should be >0 (silent data loss)
- **Solution**: Create contract validation tests that verify data structure compatibility

#### **Testing Strategy for Script Data Flow:**
```bash
# 1. Test script output format matches consumer expectations
node scripts/security/scan-docker-images.js | jq '.scans[0] | keys' # Should show expected keys
node -e "
const data = JSON.parse(require('fs').readFileSync('/tmp/scan-results.json'));
console.log('Expected format:', data.scans[0].vulnerabilities ? 'PASS' : 'FAIL - wrong structure');
"

# 2. Validate GitHub Actions workflow data passing
# Test that outputs from one job match inputs expected by next job
echo "Testing workflow data compatibility..."
```

#### **SARIF File Management:**
- **Category Collision Prevention**: Each Docker image scan MUST generate unique SARIF categories
- **File Separation Strategy**: 
  - `.sarif` files for GitHub Security (pure SARIF format only)
  - `.json` files for PR comments (can include custom summary fields)
- **Category Naming Pattern**: Use image name + timestamp or unique identifier
- **Common Failure**: Multiple images with identical categories cause GitHub Security upload failures

#### **Cross-Runner Integration Validation:**
- **Image Availability Rule**: Docker images built with `load: true` are NOT available on different runners
- **Solution**: Rebuild strategy with consistent tagging from job outputs
- **Testing Pattern**: Always verify rebuild produces identical image tags as original build
- **Cache Optimization**: Rebuilds leverage Docker layer cache for performance

#### **Integration Testing Checklist:**
1. **Data Format Compatibility**:
   ```bash
   # Test producer output format
   ./scripts/producer.js > /tmp/output.json
   # Test consumer can process the output
   ./scripts/consumer.js /tmp/output.json && echo "PASS" || echo "FAIL"
   ```

2. **Workflow Output Passing**:
   ```yaml
   # In GitHub Actions, test with debug output
   - name: Validate Job Output Format
     run: |
       echo "Testing output format: ${{ needs.previous-job.outputs.data }}"
       echo '${{ needs.previous-job.outputs.data }}' | jq '.expectedField' || exit 1
   ```

3. **Cross-Job Resource Access**:
   ```yaml
   # Verify resources built in one job work in another
   - name: Test Resource Availability
     run: |
       docker images | grep expected-image-tag || {
         echo "ERROR: Expected image not available, implementing rebuild strategy"
         exit 1
       }
   ```

4. **SARIF Validation**:
   ```bash
   # Validate SARIF format before upload
   jq '.runs[0].tool.driver.name' scan-results.sarif || echo "Invalid SARIF format"
   # Check for category uniqueness
   find . -name "*.sarif" -exec jq -r '.runs[0].results[0].ruleId // "no-rule"' {} \; | sort | uniq -d
   ```

#### **Debugging Complex Integration Failures:**
1. **Silent Data Loss Detection**: Compare expected vs actual data at each workflow step
2. **Format Mismatch Identification**: Use `jq` queries to validate data structure at boundaries  
3. **Resource Availability Verification**: Test cross-job resource access before depending on it
4. **Category Collision Prevention**: Generate unique identifiers for all SARIF categories

#### **Prevention Guidelines:**
- **Never assume data structures** - always validate with sample data
- **Test cross-job dependencies** with manual verification steps
- **Use unique identifiers** for all resources that might collide
- **Implement contract tests** between script producers and consumers
- **Log intermediate data** to debug silent transformation failures

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

### Docker Security Standardization

**CRITICAL: Both services now use secure, standardized base images with 0 critical vulnerabilities**

#### **Base Image Strategy:**
- **Standard Image**: `eclipse-temurin:21.0.8_9-jre-noble` (Ubuntu 24.04 LTS)
- **Security Status**: 0 critical vulnerabilities (verified via security scanning)
- **Previous Issues**: webauthn-server used `gcr.io/distroless/java21-debian12` (1 CRITICAL vulnerability)
- **Resolution**: Migrated webauthn-server to match webauthn-test-credentials-service secure base

#### **Security Hardening (Both Services):**
- **Non-root execution**: Both run as `appuser` (uid 1001, gid 1001)  
- **Minimal attack surface**: Only essential packages installed (wget, curl for health checks)
- **Health monitoring**: Production-ready health checks on both services
- **JVM optimization**: Identical containerized JVM settings for performance and security
- **Layer optimization**: Clean apt cache, minimal layers, proper ownership

#### **Verification Commands:**
- **Security Scan**: `docker scout cves <image>` (should show 0 critical vulnerabilities)
- **Base Image Check**: Both Dockerfiles should reference `eclipse-temurin:21.0.8_9-jre-noble`
- **Build Validation**: `./gradlew build` and Docker build should succeed without security warnings

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
- **Client Library Publishing Architecture Refactoring**: Refactored complex temporary file generation approach to clean dedicated submodule architecture with `client-libraries/android-client/` and `client-libraries/typescript-client/` submodules, eliminating 80+ lines of complex build.gradle.kts scripting in favor of standard Gradle/npm publishing configurations
- **Enhanced Workflow Change Detection**: Implemented granular workflow change detection with component mapping, replacing unsafe "fast-path all workflow changes" with targeted validation levels (orchestration=full, unit-test=tests-only, docker=build-only, infrastructure=minimal)
- **Docker Build Workflow Consolidation**: Consolidated redundant docker-build.yml from 3 separate jobs (build→scan→push with 3x image rebuilds) into single efficient job, eliminating 60-70% build redundancy while maintaining security-first approach and all functionality
- **Callable Workflow Architecture Refactoring**: Refactored monolithic 777-line build-and-test.yml into modular callable workflows (54% size reduction) with unit-tests.yml and docker-build.yml modules, improving maintainability while preserving all conditional logic and job dependencies
- **Docker Security Standardization**: Migrated webauthn-server from distroless (1 CRITICAL vulnerability) to eclipse-temurin:21.0.8_9-jre-noble (0 critical vulnerabilities), achieving consistent secure base images across both services
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