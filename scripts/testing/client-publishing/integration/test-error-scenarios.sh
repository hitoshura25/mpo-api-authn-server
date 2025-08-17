#!/bin/bash
# Test error scenarios and edge cases in client publishing system
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Error Scenarios and Edge Cases"
TEST_CATEGORY="integration"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Invalid configuration scenarios
test_invalid_configuration_scenarios() {
    log_info "Testing invalid configuration scenarios..."
    
    local temp_config=$(create_temp_file "invalid_config")
    
    # Test missing packages section
    create_test_config_file "missing_packages_section" "$temp_config"
    
    if validate_config_path ".packages" "object" "$temp_config" 2>/dev/null; then
        log_error "Should detect missing packages section"
        rm -f "$temp_config"
        return 1
    fi
    
    # Test missing Android config
    create_test_config_file "missing_android_config" "$temp_config"
    
    if validate_config_path ".packages.android" "object" "$temp_config" 2>/dev/null; then
        log_error "Should detect missing Android configuration"
        rm -f "$temp_config"
        return 1
    fi
    
    # Test null values
    create_test_config_file "null_values_config" "$temp_config"
    
    if validate_config_path ".packages.android.groupId" "string" "$temp_config" 2>/dev/null; then
        log_error "Should detect null group ID"
        rm -f "$temp_config"
        return 1
    fi
    
    rm -f "$temp_config"
    log_success "Invalid configuration scenarios handled correctly"
    return 0
}

# Test 2: Invalid version formats
test_invalid_version_formats() {
    log_info "Testing invalid version formats..."
    
    local invalid_versions=$(get_invalid_versions)
    
    for version in $invalid_versions; do
        if validate_version_format "$version"; then
            log_error "Should reject invalid version: $version"
            return 1
        fi
    done
    
    log_success "Invalid version formats correctly rejected"
    return 0
}

# Test 3: Missing environment variables
test_missing_environment_variables() {
    log_info "Testing missing environment variables..."
    
    # Test staging environment with missing variables
    setup_test_environment_vars "missing_credentials"
    
    local required_staging_vars=("ANDROID_PUBLISH_USER" "ANDROID_PUBLISH_TOKEN" "NPM_TOKEN")
    local missing_vars=()
    
    for var in "${required_staging_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -eq 0 ]]; then
        log_error "Should have missing environment variables for test scenario"
        cleanup_mock_env
        return 1
    fi
    
    cleanup_mock_env
    log_success "Missing environment variables detected correctly"
    return 0
}

# Test 4: Workflow input validation errors
test_workflow_input_validation_errors() {
    log_info "Testing workflow input validation errors..."
    
    # Test invalid publish type
    local invalid_publish_type="invalid"
    
    if [[ "$invalid_publish_type" =~ ^(staging|production)$ ]]; then
        log_error "Should reject invalid publish type: $invalid_publish_type"
        return 1
    fi
    
    # Test empty version
    local empty_version=""
    
    if validate_version_format "$empty_version"; then
        log_error "Should reject empty version"
        return 1
    fi
    
    # Test invalid version format
    local invalid_version="1.0"
    
    if validate_version_format "$invalid_version"; then
        log_error "Should reject incomplete version: $invalid_version"
        return 1
    fi
    
    log_success "Workflow input validation errors detected correctly"
    return 0
}

# Test 5: Configuration file corruption scenarios
test_configuration_corruption_scenarios() {
    log_info "Testing configuration file corruption scenarios..."
    
    local temp_config=$(create_temp_file "corrupt_config")
    
    # Test invalid YAML syntax
    create_test_config_file "invalid_yaml_syntax" "$temp_config"
    
    if validate_yaml "$temp_config"; then
        log_error "Should detect invalid YAML syntax"
        rm -f "$temp_config"
        return 1
    fi
    
    # Test empty file
    echo "" > "$temp_config"
    
    if yq eval '.packages' "$temp_config" 2>/dev/null | grep -q -v "null"; then
        log_error "Should handle empty configuration file"
        rm -f "$temp_config"
        return 1
    fi
    
    rm -f "$temp_config"
    log_success "Configuration corruption scenarios handled correctly"
    return 0
}

# Test 6: Network and registry errors simulation
test_network_registry_errors() {
    log_info "Testing network and registry error simulation..."
    
    # Test invalid repository URLs
    local invalid_urls=("not-a-url" "ftp://invalid.com" "http://insecure.com")
    
    for url in "${invalid_urls[@]}"; do
        # URLs should be HTTPS for security
        if [[ "$url" =~ ^https:// ]]; then
            log_error "Invalid URL should not pass validation: $url"
            return 1
        fi
    done
    
    # Test unreachable registry patterns
    local test_unreachable_patterns=("https://nonexistent.registry.com" "https://invalid.pkg.github.com")
    
    for pattern in "${test_unreachable_patterns[@]}"; do
        # These would fail in real scenarios - we're just testing pattern recognition
        log_debug "Would test unreachable registry: $pattern"
    done
    
    log_success "Network and registry error simulation completed"
    return 0
}

# Test 7: Cross-environment contamination detection
test_cross_environment_contamination() {
    log_info "Testing cross-environment contamination detection..."
    
    # Test that staging config doesn't contain production values
    local staging_android_url=$(yq eval '.repositories.staging.android.url' "$CONFIG_FILE")
    
    if [[ "$staging_android_url" =~ sonatype\.com ]]; then
        log_error "Staging configuration contaminated with production URL"
        return 1
    fi
    
    # Test that production config doesn't contain staging values  
    local prod_npm_registry=$(yq eval '.repositories.production.npm.registry' "$CONFIG_FILE")
    
    if [[ "$prod_npm_registry" =~ github\.com ]]; then
        log_error "Production configuration contaminated with staging registry"
        return 1
    fi
    
    # Test that credential environment variables don't overlap inappropriately
    local staging_android_user=$(yq eval '.repositories.staging.android.credentials.usernameEnv' "$CONFIG_FILE")
    local prod_android_user=$(yq eval '.repositories.production.android.credentials.usernameEnv' "$CONFIG_FILE")
    
    if [[ "$staging_android_user" == "$prod_android_user" ]]; then
        log_error "Staging and production should use different Android credentials"
        return 1
    fi
    
    log_success "Cross-environment contamination detection working correctly"
    return 0
}

# Test 8: Template generation edge cases
test_template_generation_edge_cases() {
    log_info "Testing template generation edge cases..."
    
    local temp_dir=$(create_temp_dir "template_edge_cases")
    
    # Test with special characters in names
    local special_artifact="test-artifact_with-special.chars"
    local special_group="io.github.test-user"
    local special_version="1.0.0-alpha-beta.test"
    
    local gradle_file="$temp_dir/build.gradle.kts"
    
    generate_android_template \
        "$special_group" \
        "$special_artifact" \
        "$special_version" \
        "https://maven.pkg.github.com/test/repo" \
        "$gradle_file"
    
    # Verify special characters are preserved
    if ! grep -q "$special_artifact" "$gradle_file"; then
        log_error "Special characters in artifact name not preserved"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Test with empty suffixes (production scenario)
    local prod_suffix=""
    local base_artifact="base-artifact"
    local combined_artifact="${base_artifact}${prod_suffix}"
    
    if [[ "$combined_artifact" != "$base_artifact" ]]; then
        log_error "Empty suffix should result in base artifact name"
        rm -rf "$temp_dir"
        return 1
    fi
    
    rm -rf "$temp_dir"
    log_success "Template generation edge cases handled correctly"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_invalid_configuration_scenarios || test_result=1
    test_invalid_version_formats || test_result=1
    test_missing_environment_variables || test_result=1
    test_workflow_input_validation_errors || test_result=1
    test_configuration_corruption_scenarios || test_result=1
    test_network_registry_errors || test_result=1
    test_cross_environment_contamination || test_result=1
    test_template_generation_edge_cases || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi