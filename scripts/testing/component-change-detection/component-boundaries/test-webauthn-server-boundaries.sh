#!/bin/bash
set -euo pipefail

# Component Change Detection Test: WebAuthn Server Boundary Detection
#
# Tests that changes in webauthn-server/ directory correctly trigger
# webauthn-server-changed=true while other components remain false.
#
# This test validates the core component boundary detection for:
# - webauthn-server/ directory changes
# - Proper isolation from other components
# - GitHub Actions output format compliance

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
DETECTION_SCRIPT="$PROJECT_ROOT/scripts/core/detect-component-changes.sh"
TEST_NAME="WebAuthn Server Boundary Detection"

# Logging functions
log_test() {
    echo -e "${BLUE}[TEST]${NC} $*"
}

log_success() {
    echo -e "${GREEN}✅${NC} $*"
}

log_error() {
    echo -e "${RED}❌${NC} $*"
}

log_info() {
    echo -e "${BLUE}📋${NC} $*"
}

# Test result tracking
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Helper function to run a single test case
run_test_case() {
    local test_description="$1"
    local test_function="$2"
    
    ((TOTAL_TESTS++))
    log_test "$test_description"
    
    if $test_function; then
        ((TESTS_PASSED++))
        log_success "$test_description"
    else
        ((TESTS_FAILED++))
        log_error "$test_description"
    fi
    
    echo ""
}

# Test case: WebAuthn server source code changes
test_webauthn_server_source_changes() {
    local temp_file="$PROJECT_ROOT/webauthn-server/test-boundary-change.txt"
    local temp_output
    
    # Create test change in webauthn-server directory
    echo "Test change for boundary detection" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        # Check outputs
        local webauthn_changed
        local test_credentials_changed
        local openapi_changed
        local e2e_changed
        local infrastructure_changed
        
        webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        test_credentials_changed=$(grep "test-credentials-service-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        openapi_changed=$(grep "openapi-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        e2e_changed=$(grep "e2e-tests-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        infrastructure_changed=$(grep "infrastructure-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        
        # Validate expected outputs
        local success=true
        
        if [[ "$webauthn_changed" != "true" ]]; then
            log_error "Expected webauthn-server-changed=true, got: $webauthn_changed"
            success=false
        fi
        
        if [[ "$test_credentials_changed" != "false" ]]; then
            log_error "Expected test-credentials-service-changed=false, got: $test_credentials_changed"
            success=false
        fi
        
        if [[ "$openapi_changed" != "false" ]]; then
            log_error "Expected openapi-changed=false, got: $openapi_changed"
            success=false
        fi
        
        if [[ "$e2e_changed" != "false" ]]; then
            log_error "Expected e2e-tests-changed=false, got: $e2e_changed"
            success=false
        fi
        
        if [[ "$infrastructure_changed" != "false" ]]; then
            log_error "Expected infrastructure-changed=false, got: $infrastructure_changed"
            success=false
        fi
        
        if [[ "$success" == "true" ]]; then
            log_info "✅ WebAuthn server change correctly detected in isolation"
            return 0
        else
            log_error "❌ Component isolation validation failed"
            return 1
        fi
    else
        log_error "Change detection script failed to execute"
        return 1
    fi
    
    # Cleanup
    rm -f "$temp_file" "$temp_output"
    git reset HEAD "$temp_file" >/dev/null 2>&1 || true
    unset GITHUB_OUTPUT
}

# Test case: WebAuthn server Gradle build file changes
test_webauthn_server_build_changes() {
    local temp_file="$PROJECT_ROOT/webauthn-server/build.gradle.kts.test"
    local temp_output
    
    # Create test change in webauthn-server build file
    echo "// Test build change" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        local webauthn_changed
        webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        
        if [[ "$webauthn_changed" == "true" ]]; then
            log_info "✅ WebAuthn server build file change correctly detected"
            rm -f "$temp_file" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 0
        else
            log_error "Expected webauthn-server-changed=true for build file, got: $webauthn_changed"
            rm -f "$temp_file" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 1
        fi
    else
        log_error "Change detection script failed to execute"
        rm -f "$temp_file" "$temp_output" 
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        unset GITHUB_OUTPUT
        return 1
    fi
}

# Test case: WebAuthn server subdirectory changes
test_webauthn_server_subdirectory_changes() {
    local temp_dir="$PROJECT_ROOT/webauthn-server/src/test/kotlin/test"
    local temp_file="$temp_dir/BoundaryTest.kt"
    local temp_output
    
    # Create test subdirectory and file
    mkdir -p "$temp_dir"
    echo "class BoundaryTest" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        local webauthn_changed
        webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        
        if [[ "$webauthn_changed" == "true" ]]; then
            log_info "✅ WebAuthn server subdirectory change correctly detected"
            rm -rf "$temp_dir" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 0
        else
            log_error "Expected webauthn-server-changed=true for subdirectory, got: $webauthn_changed"
            rm -rf "$temp_dir" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 1
        fi
    else
        log_error "Change detection script failed to execute"
        rm -rf "$temp_dir" "$temp_output"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        unset GITHUB_OUTPUT
        return 1
    fi
}

# Test case: No changes should result in no component detection
test_no_changes_scenario() {
    local temp_output
    
    # Create temporary file for output with clean working directory
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Ensure clean working directory
    local has_changes
    has_changes=$(git status --porcelain | wc -l)
    
    if [[ $has_changes -gt 0 ]]; then
        log_info "Skipping no-changes test - working directory has uncommitted changes"
        unset GITHUB_OUTPUT
        rm -f "$temp_output"
        return 0
    fi
    
    # Run change detection on identical commits (should detect no changes)
    if "$DETECTION_SCRIPT" HEAD HEAD >/dev/null 2>&1; then
        local webauthn_changed
        webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        
        if [[ "$webauthn_changed" == "false" ]]; then
            log_info "✅ No changes correctly result in no component detection"
            unset GITHUB_OUTPUT
            rm -f "$temp_output"
            return 0
        else
            log_error "Expected webauthn-server-changed=false for no changes, got: $webauthn_changed"
            unset GITHUB_OUTPUT
            rm -f "$temp_output"
            return 1
        fi
    else
        log_error "Change detection script failed to execute for no-changes scenario"
        unset GITHUB_OUTPUT
        rm -f "$temp_output"
        return 1
    fi
}

# Main test execution
main() {
    echo ""
    log_test "🔍 $TEST_NAME"
    log_info "Testing webauthn-server/ directory boundary detection accuracy"
    echo ""
    
    # Validate prerequisites
    if [[ ! -f "$DETECTION_SCRIPT" ]]; then
        log_error "Change detection script not found: $DETECTION_SCRIPT"
        exit 1
    fi
    
    if [[ ! -x "$DETECTION_SCRIPT" ]]; then
        log_error "Change detection script is not executable: $DETECTION_SCRIPT"
        exit 1
    fi
    
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
    
    # Run test cases
    run_test_case "WebAuthn Server Source Code Changes" "test_webauthn_server_source_changes"
    run_test_case "WebAuthn Server Build File Changes" "test_webauthn_server_build_changes"
    run_test_case "WebAuthn Server Subdirectory Changes" "test_webauthn_server_subdirectory_changes"
    run_test_case "No Changes Scenario" "test_no_changes_scenario"
    
    # Test summary
    echo "=================================="
    log_info "$TEST_NAME Results:"
    echo "  Total Tests: $TOTAL_TESTS"
    echo "  Passed: $TESTS_PASSED"
    echo "  Failed: $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo ""
        log_success "🎉 All WebAuthn server boundary detection tests passed!"
        log_info "Component isolation working correctly for webauthn-server/ changes"
        exit 0
    else
        echo ""
        log_error "❌ $TESTS_FAILED test(s) failed"
        log_error "WebAuthn server boundary detection needs fixes"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi