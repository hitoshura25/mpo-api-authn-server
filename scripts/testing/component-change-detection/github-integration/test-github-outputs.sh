#!/bin/bash
set -euo pipefail

# Component Change Detection Test: GitHub Actions Outputs
#
# Tests that the change detection script correctly integrates with GitHub Actions
# by properly writing outputs to GITHUB_OUTPUT environment file and handling
# the GitHub Actions workflow context correctly.
#
# This test validates:
# - GITHUB_OUTPUT environment variable handling
# - Proper output format for GitHub Actions consumption
# - Output file writing and format compliance
# - Integration with main-ci-cd.yml workflow requirements

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
TEST_NAME="GitHub Actions Outputs"

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

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $*"
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

# Test case: GITHUB_OUTPUT environment variable handling
test_github_output_file_writing() {
    local temp_output
    local temp_file="$PROJECT_ROOT/webauthn-server/test-github-output.txt"
    
    # Create test change
    echo "Test GitHub output handling" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for GitHub Actions output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        # Check if output file exists and has content
        if [[ ! -f "$temp_output" ]]; then
            log_error "GITHUB_OUTPUT file was not created: $temp_output"
            unset GITHUB_OUTPUT
            rm -f "$temp_file"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            return 1
        fi
        
        # Check if file has expected output lines
        local output_lines
        output_lines=$(wc -l < "$temp_output")
        
        if [[ $output_lines -lt 6 ]]; then
            log_error "Expected at least 6 output lines, got: $output_lines"
            log_error "Output content:"
            cat "$temp_output"
            unset GITHUB_OUTPUT
            rm -f "$temp_file" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            return 1
        fi
        
        # Validate specific output format
        local expected_outputs=(
            "webauthn-server-changed="
            "test-credentials-service-changed="
            "openapi-changed="
            "e2e-tests-changed="
            "infrastructure-changed="
            "client-generation-required="
        )
        
        local success=true
        for expected in "${expected_outputs[@]}"; do
            if ! grep -q "^$expected" "$temp_output"; then
                log_error "Missing expected output: $expected"
                success=false
            fi
        done
        
        if [[ "$success" == "true" ]]; then
            log_info "✅ GITHUB_OUTPUT file correctly written with all required outputs"
            log_info "   File: $temp_output"
            log_info "   Lines: $output_lines"
            
            # Show a sample of the output for verification
            log_info "   Sample outputs:"
            head -3 "$temp_output" | sed 's/^/     /'
            
            unset GITHUB_OUTPUT
            rm -f "$temp_file" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            return 0
        else
            log_error "❌ GITHUB_OUTPUT format validation failed"
            unset GITHUB_OUTPUT
            rm -f "$temp_file" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            return 1
        fi
    else
        log_error "Change detection script failed to execute"
        unset GITHUB_OUTPUT
        rm -f "$temp_file" "$temp_output"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        return 1
    fi
}

# Test case: Output format compliance for GitHub Actions
test_output_format_compliance() {
    local temp_output
    local temp_file="$PROJECT_ROOT/webauthn-test-credentials-service/test-format.txt"
    
    # Create test change
    echo "Test output format compliance" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for GitHub Actions output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        # Validate output format - should be key=value pairs
        local format_valid=true
        local line_num=0
        
        while IFS= read -r line; do
            ((line_num++))
            
            # Skip empty lines
            [[ -z "$line" ]] && continue
            
            # Check if line matches key=value format
            if [[ ! "$line" =~ ^[a-zA-Z0-9_-]+=(true|false)$ ]]; then
                log_error "Invalid output format on line $line_num: $line"
                log_error "Expected format: key=true|false"
                format_valid=false
            fi
        done < "$temp_output"
        
        if [[ "$format_valid" == "true" ]]; then
            log_info "✅ Output format complies with GitHub Actions requirements"
            log_info "   All lines follow key=value pattern with boolean values"
            
            # Validate specific values
            local webauthn_changed
            local test_credentials_changed
            
            webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2)
            test_credentials_changed=$(grep "test-credentials-service-changed=" "$temp_output" | cut -d'=' -f2)
            
            if [[ "$webauthn_changed" == "false" && "$test_credentials_changed" == "true" ]]; then
                log_info "✅ Component isolation correctly reflected in outputs"
                log_info "   webauthn-server-changed: $webauthn_changed (correct)"
                log_info "   test-credentials-service-changed: $test_credentials_changed (correct)"
            else
                log_error "Component detection logic issue:"
                log_error "   webauthn-server-changed: $webauthn_changed (expected: false)"
                log_error "   test-credentials-service-changed: $test_credentials_changed (expected: true)"
                format_valid=false
            fi
        fi
        
        unset GITHUB_OUTPUT
        rm -f "$temp_file" "$temp_output"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        
        return $([[ "$format_valid" == "true" ]] && echo 0 || echo 1)
    else
        log_error "Change detection script failed to execute"
        unset GITHUB_OUTPUT
        rm -f "$temp_file" "$temp_output"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        return 1
    fi
}

# Test case: No GITHUB_OUTPUT environment variable behavior
test_no_github_output_env() {
    local temp_file="$PROJECT_ROOT/webauthn-server/test-no-env.txt"
    
    # Create test change
    echo "Test no GITHUB_OUTPUT env behavior" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Ensure GITHUB_OUTPUT is not set
    unset GITHUB_OUTPUT 2>/dev/null || true
    
    # Run change detection - should still work without GITHUB_OUTPUT
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        log_info "✅ Script executes successfully without GITHUB_OUTPUT environment variable"
        log_info "   This is expected behavior for local testing and debugging"
        
        rm -f "$temp_file"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        return 0
    else
        log_error "Script failed when GITHUB_OUTPUT not set"
        log_error "Script should handle missing GITHUB_OUTPUT gracefully"
        
        rm -f "$temp_file"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        return 1
    fi
}

# Test case: Main workflow integration outputs
test_main_workflow_integration() {
    local temp_output
    local temp_file="$PROJECT_ROOT/webauthn-server/src/main/resources/openapi/test-integration.yaml"
    
    # Create test change in OpenAPI file to trigger multiple detections
    mkdir -p "$(dirname "$temp_file")"
    echo "# Test integration change" >> "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for GitHub Actions output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        # Validate that all outputs expected by main-ci-cd.yml are present
        local required_workflow_outputs=(
            "webauthn-server-changed"
            "test-credentials-service-changed"
            "openapi-changed"
            "e2e-tests-changed"
            "infrastructure-changed"
            "client-generation-required"
        )
        
        local integration_success=true
        
        for output_key in "${required_workflow_outputs[@]}"; do
            if ! grep -q "^$output_key=" "$temp_output"; then
                log_error "Missing required workflow output: $output_key"
                integration_success=false
            else
                local output_value
                output_value=$(grep "^$output_key=" "$temp_output" | cut -d'=' -f2)
                if [[ "$output_value" != "true" && "$output_value" != "false" ]]; then
                    log_error "Invalid boolean value for $output_key: $output_value"
                    integration_success=false
                fi
            fi
        done
        
        if [[ "$integration_success" == "true" ]]; then
            log_info "✅ All main-ci-cd.yml required outputs present and valid"
            
            # Validate OpenAPI change detection worked
            local openapi_changed
            local client_generation_required
            
            openapi_changed=$(grep "openapi-changed=" "$temp_output" | cut -d'=' -f2)
            client_generation_required=$(grep "client-generation-required=" "$temp_output" | cut -d'=' -f2)
            
            if [[ "$openapi_changed" == "true" && "$client_generation_required" == "true" ]]; then
                log_info "✅ OpenAPI change correctly triggered client generation"
                log_info "   openapi-changed: $openapi_changed"
                log_info "   client-generation-required: $client_generation_required"
            else
                log_error "OpenAPI change detection failed:"
                log_error "   openapi-changed: $openapi_changed (expected: true)"
                log_error "   client-generation-required: $client_generation_required (expected: true)"
                integration_success=false
            fi
        fi
        
        unset GITHUB_OUTPUT
        rm -f "$temp_file" "$temp_output"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        
        return $([[ "$integration_success" == "true" ]] && echo 0 || echo 1)
    else
        log_error "Change detection script failed to execute"
        unset GITHUB_OUTPUT
        rm -f "$temp_file" "$temp_output"
        git reset HEAD "$temp_file" >/dev/null 2>&1 || true
        return 1
    fi
}

# Main test execution
main() {
    echo ""
    log_test "🔧 $TEST_NAME"
    log_info "Testing GitHub Actions workflow integration and output handling"
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
    run_test_case "GITHUB_OUTPUT File Writing" "test_github_output_file_writing"
    run_test_case "Output Format Compliance" "test_output_format_compliance"
    run_test_case "No GITHUB_OUTPUT Environment Handling" "test_no_github_output_env"
    run_test_case "Main Workflow Integration Outputs" "test_main_workflow_integration"
    
    # Test summary
    echo "=================================="
    log_info "$TEST_NAME Results:"
    echo "  Total Tests: $TOTAL_TESTS"
    echo "  Passed: $TESTS_PASSED"
    echo "  Failed: $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo ""
        log_success "🎉 All GitHub Actions integration tests passed!"
        log_info "GitHub Actions workflow integration ready:"
        log_info "  ✅ GITHUB_OUTPUT file handling working correctly"
        log_info "  ✅ Output format complies with workflow requirements"
        log_info "  ✅ All required outputs present for main-ci-cd.yml"
        log_info "  ✅ Graceful handling when GITHUB_OUTPUT not set"
        echo ""
        log_info "Integration points validated:"
        log_info "  - Component change detection → workflow conditional logic"
        log_info "  - OpenAPI changes → client library generation triggers"
        log_info "  - Boolean output format → GitHub Actions if: conditions"
        exit 0
    else
        echo ""
        log_error "❌ $TESTS_FAILED test(s) failed"
        log_error "GitHub Actions integration needs fixes before Phase 10.2"
        echo ""
        log_error "Integration issues will cause:"
        log_error "  - Workflow conditional logic failures"
        log_error "  - Incorrect job execution decisions"
        log_error "  - Component change detection not working in CI"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi