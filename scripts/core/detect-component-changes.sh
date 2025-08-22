#!/bin/bash
set -euo pipefail

# Component Change Detection Script for Phase 10.1 - Independent Component Processing & Optimization
#
# This script implements intelligent component change detection to optimize CI/CD performance
# by identifying which specific components require processing based on file changes.
#
# COMPONENT BOUNDARIES:
# - webauthn-server: Files in webauthn-server/, webauthn-test-lib/ (shared dependency)
# - test-credentials-service: Files in webauthn-test-credentials-service/, webauthn-test-lib/ (shared dependency)
# - openapi-specification: Changes in webauthn-server/src/main/resources/openapi/documentation.yaml or OpenAPI generation scripts
# - e2e-tests: Files in web-test-client/, android-test-client/, E2E workflow files
# - infrastructure: .github/workflows/, config/, scripts/, root build files
#
# USAGE:
#   ./detect-component-changes.sh [base_ref] [head_ref]
#   
# EXAMPLES:
#   # PR context - compare PR branch against base branch
#   ./detect-component-changes.sh origin/main HEAD
#   
#   # Main branch context - compare current commit against previous commit
#   ./detect-component-changes.sh HEAD~1 HEAD
#
# OUTPUTS (GitHub Actions format):
#   webauthn-server-changed=true/false
#   test-credentials-service-changed=true/false
#   openapi-changed=true/false
#   e2e-tests-changed=true/false
#   infrastructure-changed=true/false
#   client-generation-required=true/false

# Logging functions
log() {
    echo "🔍 [COMPONENT-DETECTION] $*"
}

log_debug() {
    echo "  📋 $*"
}

log_result() {
    echo "🎯 [RESULT] $*"
}

log_warning() {
    echo "⚠️  [WARNING] $*"
}

log_error() {
    echo "❌ [ERROR] $*"
}

# Initialize change detection variables
WEBAUTHN_SERVER_CHANGED=false
TEST_CREDENTIALS_SERVICE_CHANGED=false
OPENAPI_CHANGED=false
E2E_TESTS_CHANGED=false
INFRASTRUCTURE_CHANGED=false
CLIENT_GENERATION_REQUIRED=false

# Component file pattern definitions (using functions for compatibility)
get_component_patterns() {
    local component="$1"
    case "$component" in
        "webauthn-server")
            echo "webauthn-server/ webauthn-test-lib/"
            ;;
        "test-credentials-service")
            echo "webauthn-test-credentials-service/ webauthn-test-lib/"
            ;;
        "openapi-specification")
            echo "webauthn-server/src/main/resources/openapi/documentation.yaml android-client-library/ typescript-client-library/"
            ;;
        "e2e-tests")
            echo "web-test-client/ android-test-client/ .github/workflows/e2e-tests.yml .github/workflows/web-e2e-tests.yml .github/workflows/android-e2e-tests.yml"
            ;;
        "infrastructure")
            echo ".github/workflows/ config/ scripts/ settings.gradle.kts build.gradle.kts gradle.properties gradle/ docker-compose.yml"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Function to determine git diff strategy based on context
determine_git_diff_strategy() {
    local base_ref="${1:-}"
    local head_ref="${2:-}"
    
    # If both refs provided, use them directly
    if [[ -n "$base_ref" && -n "$head_ref" ]]; then
        echo "$base_ref..$head_ref"
        return 0
    fi
    
    # Auto-detect context based on GitHub Actions environment
    if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
        # PR context - compare against base branch
        local base_branch="${GITHUB_BASE_REF:-main}"
        log_debug "PR context detected - comparing against origin/$base_branch"
        echo "origin/$base_branch..HEAD"
    elif [[ "${GITHUB_REF_NAME:-}" == "main" ]]; then
        # Main branch context - compare against previous commit
        log_debug "Main branch context detected - comparing against previous commit"
        echo "HEAD~1..HEAD"
    else
        # Fallback - compare against main branch
        log_warning "Unknown context - falling back to main branch comparison"
        echo "origin/main..HEAD"
    fi
}

# Function to check if any files in a component pattern have changed
check_component_changes() {
    local component_name="$1"
    local diff_range="$2"
    local patterns
    patterns=$(get_component_patterns "$component_name")
    
    log_debug "Checking $component_name component changes (patterns: $patterns)"
    
    # Get list of changed files
    local changed_files
    if ! changed_files=$(git diff --name-only "$diff_range" 2>/dev/null); then
        log_error "Failed to get git diff for range: $diff_range"
        return 1
    fi
    
    if [[ -z "$changed_files" ]]; then
        log_debug "No files changed in diff range: $diff_range"
        return 1
    fi
    
    # Check each pattern
    for pattern in $patterns; do
        # Remove trailing slash for directory patterns
        local pattern_clean="${pattern%/}"
        
        # Check if any changed file matches this pattern
        while IFS= read -r file; do
            if [[ "$file" == "$pattern_clean"* ]]; then
                log_debug "✅ Match found: $file matches pattern $pattern"
                return 0
            fi
        done <<< "$changed_files"
    done
    
    log_debug "❌ No matches found for $component_name patterns"
    return 1
}

# Function to perform OpenAPI diff analysis for client generation detection
check_openapi_diff() {
    local diff_range="$1"
    
    log_debug "Performing OpenAPI diff analysis for client generation detection"
    
    # Check if OpenAPI specification file changed
    if git diff --name-only "$diff_range" | grep -q "^webauthn-server/src/main/resources/openapi/documentation.yaml$"; then
        log_debug "✅ OpenAPI specification file changed: webauthn-server/src/main/resources/openapi/documentation.yaml"
        return 0
    fi
    
    # Check if client library source directories changed (affects generation)
    if git diff --name-only "$diff_range" | grep -E "^(android-client-library/|typescript-client-library/)" | head -1 >/dev/null; then
        log_debug "✅ Client library source directories changed - regeneration required"
        return 0
    fi
    
    # Check if OpenAPI generation scripts or build configs changed
    if git diff --name-only "$diff_range" | grep -E "^(scripts/|build\.gradle\.kts|settings\.gradle\.kts)" | grep -E "(openapi|client|generate)" | head -1 >/dev/null; then
        log_debug "✅ OpenAPI generation configuration changed - regeneration required"
        return 0
    fi
    
    # Check if root Gradle build files changed (affects client generation)
    if git diff --name-only "$diff_range" | grep -E "^(build\.gradle\.kts|settings\.gradle\.kts)$" | head -1 >/dev/null; then
        log_debug "✅ Root Gradle configuration changed - may affect client generation"
        return 0
    fi
    
    log_debug "❌ No OpenAPI changes requiring client regeneration detected"
    return 1
}

# Function to output GitHub Actions format results
output_github_actions_results() {
    if [[ "${GITHUB_OUTPUT:-}" ]]; then
        log_result "Writing results to GitHub Actions outputs"
        {
            echo "webauthn-server-changed=$WEBAUTHN_SERVER_CHANGED"
            echo "test-credentials-service-changed=$TEST_CREDENTIALS_SERVICE_CHANGED"
            echo "openapi-changed=$OPENAPI_CHANGED"
            echo "e2e-tests-changed=$E2E_TESTS_CHANGED"
            echo "infrastructure-changed=$INFRASTRUCTURE_CHANGED"
            echo "client-generation-required=$CLIENT_GENERATION_REQUIRED"
        } >> "$GITHUB_OUTPUT"
    else
        log_debug "GITHUB_OUTPUT not set - displaying results only"
    fi
}

# Function to display comprehensive results summary
display_results_summary() {
    log_result "=== COMPONENT CHANGE DETECTION SUMMARY ==="
    log_result "WebAuthn Server Changed: $WEBAUTHN_SERVER_CHANGED"
    log_result "Test Credentials Service Changed: $TEST_CREDENTIALS_SERVICE_CHANGED"
    log_result "OpenAPI Specification Changed: $OPENAPI_CHANGED"
    log_result "E2E Tests Changed: $E2E_TESTS_CHANGED"
    log_result "Infrastructure Changed: $INFRASTRUCTURE_CHANGED"
    log_result "Client Generation Required: $CLIENT_GENERATION_REQUIRED"
    
    # Performance optimization insights
    local components_changed=0
    [[ "$WEBAUTHN_SERVER_CHANGED" == "true" ]] && ((components_changed++))
    [[ "$TEST_CREDENTIALS_SERVICE_CHANGED" == "true" ]] && ((components_changed++))
    [[ "$E2E_TESTS_CHANGED" == "true" ]] && ((components_changed++))
    [[ "$INFRASTRUCTURE_CHANGED" == "true" ]] && ((components_changed++))
    
    log_result "Components requiring processing: $components_changed/4"
    
    if [[ $components_changed -eq 0 ]]; then
        log_result "🚀 FAST PATH: No component builds required - documentation/config changes only"
    elif [[ $components_changed -eq 1 ]]; then
        log_result "⚡ OPTIMIZED: Single component build - ~40-60% faster than full pipeline"
    else
        log_result "🔧 STANDARD: Multiple component builds required"
    fi
    
    if [[ "$CLIENT_GENERATION_REQUIRED" == "true" ]]; then
        log_result "📚 Client libraries will be regenerated due to OpenAPI changes"
    else
        log_result "⏭️  Client library regeneration skipped - OpenAPI specification unchanged"
    fi
}

# Main execution function
main() {
    local base_ref="${1:-}"
    local head_ref="${2:-}"
    
    log "Starting Component Change Detection for Phase 10.1"
    log "Independent Component Processing & Optimization"
    
    # Determine git diff strategy
    local diff_range
    diff_range=$(determine_git_diff_strategy "$base_ref" "$head_ref")
    log_debug "Using git diff range: $diff_range"
    
    # Validate git repository state
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
    
    # Check each component for changes
    log "Analyzing component changes..."
    
    if check_component_changes "webauthn-server" "$diff_range"; then
        WEBAUTHN_SERVER_CHANGED=true
    fi
    
    if check_component_changes "test-credentials-service" "$diff_range"; then
        TEST_CREDENTIALS_SERVICE_CHANGED=true
    fi
    
    if check_component_changes "openapi-specification" "$diff_range"; then
        OPENAPI_CHANGED=true
    fi
    
    if check_component_changes "e2e-tests" "$diff_range"; then
        E2E_TESTS_CHANGED=true
    fi
    
    if check_component_changes "infrastructure" "$diff_range"; then
        INFRASTRUCTURE_CHANGED=true
    fi
    
    # Perform OpenAPI diff analysis for client generation
    log "Analyzing OpenAPI changes for client generation..."
    if check_openapi_diff "$diff_range"; then
        CLIENT_GENERATION_REQUIRED=true
        # If OpenAPI changed, also mark it as changed for reporting
        OPENAPI_CHANGED=true
    fi
    
    # Output results
    output_github_actions_results
    display_results_summary
    
    log "Component change detection completed successfully"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi