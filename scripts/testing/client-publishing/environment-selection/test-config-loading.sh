#!/bin/bash
# Test environment-specific configuration loading
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Environment-Specific Configuration Loading"
TEST_CATEGORY="environment-selection"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Load staging environment configuration
test_staging_config_loading() {
    log_info "Testing staging environment configuration loading..."
    
    # Test loading staging Android URL
    local staging_android_url
    staging_android_url=$(load_config_value ".repositories.staging.android.url" "$CONFIG_FILE")
    
    assert_not_empty "$staging_android_url" "Staging Android repository URL"
    assert_contains "$staging_android_url" "github.com" "Staging should typically use GitHub Packages"
    
    # Test loading staging npm registry
    local staging_npm_registry
    staging_npm_registry=$(load_config_value ".repositories.staging.npm.registry" "$CONFIG_FILE")
    
    assert_not_empty "$staging_npm_registry" "Staging npm registry URL"
    
    log_success "Staging configuration loading works correctly"
    return 0
}

# Test 2: Load production environment configuration
test_production_config_loading() {
    log_info "Testing production environment configuration loading..."
    
    # Test loading production Android URL
    local production_android_url
    production_android_url=$(load_config_value ".repositories.production.android.url" "$CONFIG_FILE")
    
    assert_not_empty "$production_android_url" "Production Android repository URL"
    
    # Test loading production npm registry
    local production_npm_registry
    production_npm_registry=$(load_config_value ".repositories.production.npm.registry" "$CONFIG_FILE")
    
    assert_not_empty "$production_npm_registry" "Production npm registry URL"
    
    log_success "Production configuration loading works correctly"
    return 0
}

# Test 3: Test dynamic environment selection
test_dynamic_environment_selection() {
    log_info "Testing dynamic environment selection..."
    
    local environments=("staging" "production")
    
    for env in "${environments[@]}"; do
        log_debug "Testing environment: $env"
        
        # Test dynamic Android URL loading
        local android_url
        android_url=$(yq eval ".repositories.${env}.android.url" "$CONFIG_FILE")
        
        assert_not_empty "$android_url" "Android URL for $env environment"
        
        # Test dynamic npm registry loading
        local npm_registry
        npm_registry=$(yq eval ".repositories.${env}.npm.registry" "$CONFIG_FILE")
        
        assert_not_empty "$npm_registry" "npm registry for $env environment"
        
        log_debug "Environment $env configuration loaded successfully"
    done
    
    log_success "Dynamic environment selection works correctly"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_staging_config_loading || test_result=1
    test_production_config_loading || test_result=1
    test_dynamic_environment_selection || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi