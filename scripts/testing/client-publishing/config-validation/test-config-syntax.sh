#!/bin/bash
# Test configuration file YAML syntax validation
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Configuration File YAML Syntax Validation"
TEST_CATEGORY="config-validation"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Valid configuration file syntax
test_valid_config_syntax() {
    log_info "Testing valid configuration file syntax..."
    
    if ! validate_yaml "$CONFIG_FILE"; then
        log_error "Main configuration file has invalid YAML syntax"
        return 1
    fi
    
    log_success "Main configuration file has valid YAML syntax"
    return 0
}

# Test 2: Test with various valid YAML configurations
test_valid_yaml_scenarios() {
    log_info "Testing various valid YAML scenarios..."
    
    local temp_config
    temp_config=$(create_temp_file "valid_config")
    
    # Test valid staging config
    create_test_config_file "valid_staging_config" "$temp_config"
    if ! validate_yaml "$temp_config"; then
        log_error "Valid staging config scenario failed YAML validation"
        rm -f "$temp_config"
        return 1
    fi
    
    log_success "Valid YAML scenarios passed"
    rm -f "$temp_config"
    return 0
}

# Test 3: Test with invalid YAML syntax
test_invalid_yaml_syntax() {
    log_info "Testing invalid YAML syntax detection..."
    
    local temp_config
    temp_config=$(create_temp_file "invalid_config")
    
    # Create invalid YAML
    create_test_config_file "invalid_yaml_syntax" "$temp_config"
    
    # This should fail
    if validate_yaml "$temp_config"; then
        log_error "Invalid YAML was incorrectly validated as valid"
        rm -f "$temp_config"
        return 1
    fi
    
    log_success "Invalid YAML syntax correctly detected"
    rm -f "$temp_config"
    return 0
}

# Test 4: Test YAML structure preservation
test_yaml_structure_preservation() {
    log_info "Testing YAML structure preservation..."
    
    local temp_config
    temp_config=$(create_temp_file "structure_test")
    
    create_test_config_file "valid_staging_config" "$temp_config"
    
    # Test that we can extract expected values
    local android_group_id
    android_group_id=$(yq eval '.packages.android.groupId' "$temp_config")
    
    if [[ "$android_group_id" != "io.github.hitoshura25" ]]; then
        log_error "YAML structure not preserved correctly"
        log_error "Expected: 'io.github.hitoshura25', Got: '$android_group_id'"
        rm -f "$temp_config"
        return 1
    fi
    
    # Test nested structure access
    local staging_android_url
    staging_android_url=$(yq eval '.repositories.staging.android.url' "$temp_config")
    
    if [[ "$staging_android_url" == "null" || -z "$staging_android_url" ]]; then
        log_error "Failed to access nested YAML structure"
        rm -f "$temp_config"
        return 1
    fi
    
    log_success "YAML structure preservation validated"
    rm -f "$temp_config"
    return 0
}

# Test 5: Test yq tool functionality
test_yq_tool_functionality() {
    log_info "Testing yq tool functionality with configuration..."
    
    # Test basic yq operations on main config
    local packages_section
    packages_section=$(yq eval '.packages | keys' "$CONFIG_FILE")
    
    if [[ "$packages_section" == "null" ]]; then
        log_error "yq failed to extract packages section"
        return 1
    fi
    
    # Test array access
    local has_android
    has_android=$(yq eval '.packages | has("android")' "$CONFIG_FILE")
    
    if [[ "$has_android" != "true" ]]; then
        log_error "yq failed to validate android package section exists"
        return 1
    fi
    
    # Test type checking
    local packages_type
    packages_type=$(yq eval '.packages | type' "$CONFIG_FILE")
    
    if [[ "$packages_type" != "!!map" ]]; then
        log_error "yq type checking failed - packages should be a map"
        return 1
    fi
    
    log_success "yq tool functionality validated"
    return 0
}

# Test 6: Test edge cases and special characters
test_yaml_edge_cases() {
    log_info "Testing YAML edge cases and special characters..."
    
    local temp_config
    temp_config=$(create_temp_file "edge_cases")
    
    # Create config with special characters and edge cases
    cat > "$temp_config" << 'EOF'
packages:
  android:
    groupId: "io.github.test-user"
    baseArtifactId: "test-artifact_with-special.chars"
  typescript:
    scope: "@test-org"
    basePackageName: "test-client"

repositories:
  staging:
    android:
      url: "https://maven.pkg.github.com/test-user/test-repo"
      credentials:
        usernameEnv: "USER_NAME"
        passwordEnv: "PASS_WORD"
    npm:
      registry: "https://npm.pkg.github.com"
      credentials:
        tokenEnv: "NPM_PUBLISH_TOKEN"

naming:
  staging:
    androidSuffix: "-staging"
    npmSuffix: "-staging"

metadata:
  description: "Test with quotes \"and\" special chars & symbols"
  projectUrl: "https://github.com/test-user/test-repo?tab=readme#section"
EOF

    if ! validate_yaml "$temp_config"; then
        log_error "YAML with special characters failed validation"
        rm -f "$temp_config"
        return 1
    fi
    
    # Test that special characters are preserved
    local description
    description=$(yq eval '.metadata.description' "$temp_config")
    
    if [[ "$description" != 'Test with quotes "and" special chars & symbols' ]]; then
        log_error "Special characters not preserved correctly"
        log_error "Expected: 'Test with quotes \"and\" special chars & symbols'"
        log_error "Got: '$description'"
        rm -f "$temp_config"
        return 1
    fi
    
    log_success "YAML edge cases handled correctly"
    rm -f "$temp_config"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_valid_config_syntax || test_result=1
    test_valid_yaml_scenarios || test_result=1
    test_invalid_yaml_syntax || test_result=1
    test_yaml_structure_preservation || test_result=1
    test_yq_tool_functionality || test_result=1
    test_yaml_edge_cases || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi