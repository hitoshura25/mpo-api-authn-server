#!/bin/bash
set -euo pipefail

# Component Change Detection Test: Shared Dependency Handling
#
# Tests that changes in webauthn-test-lib/ (shared library) correctly trigger
# BOTH webauthn-server-changed=true AND test-credentials-service-changed=true
# since both services depend on the shared library.
#
# This test validates the critical shared dependency detection for:
# - webauthn-test-lib/ directory changes affecting both components
# - Proper cross-component impact detection
# - Accurate boundary detection for shared code

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
TEST_NAME="Shared Dependency Handling"

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

# Test case: webauthn-test-lib source changes affect both services
test_shared_lib_source_changes() {
    local temp_file="$PROJECT_ROOT/webauthn-test-lib/test-shared-change.kt"
    local temp_output
    
    # Create test change in shared library
    echo "// Test shared library change" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        # Check outputs - both services should be affected
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
        
        # Validate expected outputs - BOTH services should be true
        local success=true
        
        if [[ "$webauthn_changed" != "true" ]]; then
            log_error "Expected webauthn-server-changed=true (shared lib affects server), got: $webauthn_changed"
            success=false
        fi
        
        if [[ "$test_credentials_changed" != "true" ]]; then
            log_error "Expected test-credentials-service-changed=true (shared lib affects service), got: $test_credentials_changed"
            success=false
        fi
        
        # These should remain false for shared library changes
        if [[ "$openapi_changed" != "false" ]]; then
            log_error "Expected openapi-changed=false (shared lib doesn't affect OpenAPI), got: $openapi_changed"
            success=false
        fi
        
        if [[ "$e2e_changed" != "false" ]]; then
            log_error "Expected e2e-tests-changed=false (shared lib change doesn't affect E2E test files), got: $e2e_changed"
            success=false
        fi
        
        if [[ "$infrastructure_changed" != "false" ]]; then
            log_error "Expected infrastructure-changed=false (shared lib doesn't affect infrastructure), got: $infrastructure_changed"
            success=false
        fi
        
        if [[ "$success" == "true" ]]; then
            log_info "✅ Shared library change correctly affects BOTH services"
            log_info "   webauthn-server-changed: $webauthn_changed"
            log_info "   test-credentials-service-changed: $test_credentials_changed"
            return 0
        else
            log_error "❌ Shared dependency detection validation failed"
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

# Test case: webauthn-test-lib build file changes
test_shared_lib_build_changes() {
    local temp_file="$PROJECT_ROOT/webauthn-test-lib/build.gradle.kts.test"
    local temp_output
    
    # Create test change in shared library build file
    echo "// Test shared build change" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        local webauthn_changed
        local test_credentials_changed
        
        webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        test_credentials_changed=$(grep "test-credentials-service-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        
        if [[ "$webauthn_changed" == "true" && "$test_credentials_changed" == "true" ]]; then
            log_info "✅ Shared library build change affects both services correctly"
            rm -f "$temp_file" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 0
        else
            log_error "Expected both services to be affected by shared build change"
            log_error "  webauthn-server-changed: $webauthn_changed"
            log_error "  test-credentials-service-changed: $test_credentials_changed"
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

# Test case: webauthn-test-lib subdirectory changes
test_shared_lib_subdirectory_changes() {
    local temp_dir="$PROJECT_ROOT/webauthn-test-lib/src/main/kotlin/test"
    local temp_file="$temp_dir/SharedTestUtil.kt"
    local temp_output
    
    # Create test subdirectory and file in shared library
    mkdir -p "$temp_dir"
    echo "class SharedTestUtil" > "$temp_file"
    git add "$temp_file" >/dev/null 2>&1 || true
    
    # Create temporary file for output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        local webauthn_changed
        local test_credentials_changed
        
        webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        test_credentials_changed=$(grep "test-credentials-service-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        
        if [[ "$webauthn_changed" == "true" && "$test_credentials_changed" == "true" ]]; then
            log_info "✅ Shared library subdirectory change affects both services correctly"
            rm -rf "$temp_dir" "$temp_output"
            git reset HEAD "$temp_file" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 0
        else
            log_error "Expected both services to be affected by shared subdirectory change"
            log_error "  webauthn-server-changed: $webauthn_changed"
            log_error "  test-credentials-service-changed: $test_credentials_changed"
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

# Test case: Validate shared dependency boundary accuracy
test_shared_dependency_boundaries() {
    local webauthn_temp="$PROJECT_ROOT/webauthn-server/test-server-only.txt"
    local shared_temp="$PROJECT_ROOT/webauthn-test-lib/test-shared.txt"
    local temp_output
    
    # Create changes in BOTH webauthn-server and shared library
    echo "Server only change" > "$webauthn_temp"
    echo "Shared library change" > "$shared_temp"
    git add "$webauthn_temp" "$shared_temp" >/dev/null 2>&1 || true
    
    # Create temporary file for output
    temp_output=$(mktemp)
    export GITHUB_OUTPUT="$temp_output"
    
    # Run change detection
    if "$DETECTION_SCRIPT" HEAD~1 HEAD >/dev/null 2>&1; then
        local webauthn_changed
        local test_credentials_changed
        
        webauthn_changed=$(grep "webauthn-server-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        test_credentials_changed=$(grep "test-credentials-service-changed=" "$temp_output" | cut -d'=' -f2 || echo "false")
        
        # With shared library changes, BOTH services should be true
        # With webauthn-server changes, webauthn should definitely be true
        # The shared lib change should make test-credentials true as well
        
        if [[ "$webauthn_changed" == "true" && "$test_credentials_changed" == "true" ]]; then
            log_info "✅ Mixed changes correctly detected:"
            log_info "   webauthn-server change + shared lib change = both services affected"
            rm -f "$webauthn_temp" "$shared_temp" "$temp_output"
            git reset HEAD "$webauthn_temp" "$shared_temp" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 0
        else
            log_error "Mixed change detection failed"
            log_error "  webauthn-server-changed: $webauthn_changed (expected: true)"
            log_error "  test-credentials-service-changed: $test_credentials_changed (expected: true)"
            log_error "  Shared library changes should affect BOTH services"
            rm -f "$webauthn_temp" "$shared_temp" "$temp_output"
            git reset HEAD "$webauthn_temp" "$shared_temp" >/dev/null 2>&1 || true
            unset GITHUB_OUTPUT
            return 1
        fi
    else
        log_error "Change detection script failed to execute"
        rm -f "$webauthn_temp" "$shared_temp" "$temp_output"
        git reset HEAD "$webauthn_temp" "$shared_temp" >/dev/null 2>&1 || true
        unset GITHUB_OUTPUT
        return 1
    fi
}

# Main test execution
main() {
    echo ""
    log_test "🔗 $TEST_NAME"
    log_info "Testing webauthn-test-lib/ shared dependency detection accuracy"
    log_warning "CRITICAL: webauthn-test-lib changes must affect BOTH services"
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
    
    # Validate shared library directory exists
    if [[ ! -d "$PROJECT_ROOT/webauthn-test-lib" ]]; then
        log_error "webauthn-test-lib directory not found: $PROJECT_ROOT/webauthn-test-lib"
        log_error "Shared dependency testing requires the shared library directory"
        exit 1
    fi
    
    # Run test cases
    run_test_case "Shared Library Source Changes" "test_shared_lib_source_changes"
    run_test_case "Shared Library Build Changes" "test_shared_lib_build_changes"
    run_test_case "Shared Library Subdirectory Changes" "test_shared_lib_subdirectory_changes"
    run_test_case "Mixed Changes Boundary Validation" "test_shared_dependency_boundaries"
    
    # Test summary
    echo "=================================="
    log_info "$TEST_NAME Results:"
    echo "  Total Tests: $TOTAL_TESTS"
    echo "  Passed: $TESTS_PASSED"
    echo "  Failed: $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo ""
        log_success "🎉 All shared dependency detection tests passed!"
        log_info "Critical shared dependency handling working correctly:"
        log_info "  ✅ webauthn-test-lib changes affect BOTH services"
        log_info "  ✅ Cross-component impact detection accurate"
        log_info "  ✅ Mixed change scenarios handled correctly"
        echo ""
        log_info "This enables proper component coordination for Phase 10.2:"
        log_info "  - Both services rebuild when shared lib changes"
        log_info "  - E2E tests coordinate properly with shared dependencies"
        log_info "  - No missed rebuilds due to shared code changes"
        exit 0
    else
        echo ""
        log_error "❌ $TESTS_FAILED test(s) failed"
        log_error "Shared dependency detection needs fixes - CRITICAL for Phase 10.2"
        echo ""
        log_error "Impact if not fixed:"
        log_error "  - Services may not rebuild when shared code changes"
        log_error "  - E2E tests could run with stale shared library builds"
        log_error "  - Parallel processing could miss critical dependencies"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi