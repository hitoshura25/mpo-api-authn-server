#!/bin/bash
# Test cross-platform consistency between Android and TypeScript clients
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Cross-Platform Consistency Between Android and TypeScript"
TEST_CATEGORY="integration"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Package naming consistency
test_package_naming_consistency() {
    log_info "Testing package naming consistency across platforms..."
    
    local environments=("staging" "production")
    
    for env in "${environments[@]}"; do
        local android_suffix=$(yq eval ".naming.${env}.androidSuffix" "$CONFIG_FILE")
        local npm_suffix=$(yq eval ".naming.${env}.npmSuffix" "$CONFIG_FILE")
        
        # Both platforms should use the same suffix pattern for the same environment
        if [[ "$android_suffix" != "$npm_suffix" ]]; then
            log_error "Android and npm suffixes should match for ${env} environment"
            log_error "Android: '$android_suffix', npm: '$npm_suffix'"
            return 1
        fi
    done
    
    log_success "Package naming consistency validated"
    return 0
}

# Test 2: Repository URL patterns
test_repository_url_patterns() {
    log_info "Testing repository URL patterns across platforms..."
    
    # Staging should use GitHub Packages for both platforms
    local staging_android_url=$(yq eval '.repositories.staging.android.url' "$CONFIG_FILE")
    local staging_npm_registry=$(yq eval '.repositories.staging.npm.registry' "$CONFIG_FILE")
    
    if [[ ! "$staging_android_url" =~ github\.com ]]; then
        log_error "Staging Android should use GitHub Packages"
        return 1
    fi
    
    if [[ ! "$staging_npm_registry" =~ github\.com ]]; then
        log_error "Staging npm should use GitHub Packages"
        return 1
    fi
    
    # Production should use different registries but both public
    local prod_android_url=$(yq eval '.repositories.production.android.url' "$CONFIG_FILE")
    local prod_npm_registry=$(yq eval '.repositories.production.npm.registry' "$CONFIG_FILE")
    
    if [[ ! "$prod_android_url" =~ (sonatype\.com|oss\.sonatype\.org) ]]; then
        log_error "Production Android should use Maven Central"
        return 1
    fi
    
    if [[ "$prod_npm_registry" != "https://registry.npmjs.org" ]]; then
        log_error "Production npm should use npmjs.org"
        return 1
    fi
    
    log_success "Repository URL patterns validated"
    return 0
}

# Test 3: Version format compatibility
test_version_format_compatibility() {
    log_info "Testing version format compatibility across platforms..."
    
    local test_versions=("1.0.0" "1.0.0-pr.123.456" "1.0.0-staging" "2.1.3-beta.1")
    
    for version in "${test_versions[@]}"; do
        # Both platforms should accept the same version formats
        if ! validate_version_format "$version"; then
            log_error "Version format should be valid for both platforms: $version"
            return 1
        fi
    done
    
    log_success "Version format compatibility validated"
    return 0
}

# Test 4: Workflow input consistency
test_workflow_input_consistency() {
    log_info "Testing workflow input consistency across platforms..."
    
    local android_inputs=$(yq eval '.on.workflow_call.inputs | keys' "${WORKFLOWS_DIR}/publish-android.yml")
    local typescript_inputs=$(yq eval '.on.workflow_call.inputs | keys' "${WORKFLOWS_DIR}/publish-typescript.yml")
    
    # Core inputs should be the same
    local core_inputs=("client-version" "publish-type")
    
    for input in "${core_inputs[@]}"; do
        if ! echo "$android_inputs" | grep -q "$input"; then
            log_error "Android workflow missing core input: $input"
            return 1
        fi
        
        if ! echo "$typescript_inputs" | grep -q "$input"; then
            log_error "TypeScript workflow missing core input: $input"
            return 1
        fi
    done
    
    log_success "Workflow input consistency validated"
    return 0
}

# Test 5: Configuration structure alignment
test_configuration_structure_alignment() {
    log_info "Testing configuration structure alignment across platforms..."
    
    # Both platforms should have the same configuration structure
    local android_config=$(yq eval '.packages.android' "$CONFIG_FILE")
    local typescript_config=$(yq eval '.packages.typescript' "$CONFIG_FILE")
    
    if [[ "$android_config" == "null" ]]; then
        log_error "Android configuration missing"
        return 1
    fi
    
    if [[ "$typescript_config" == "null" ]]; then
        log_error "TypeScript configuration missing"
        return 1
    fi
    
    # Both should have similar credential structure
    local staging_android_creds=$(yq eval '.repositories.staging.android.credentials | keys' "$CONFIG_FILE")
    local staging_npm_creds=$(yq eval '.repositories.staging.npm.credentials | keys' "$CONFIG_FILE")
    
    # npm uses token, Android uses username/password - this is expected difference
    if ! echo "$staging_android_creds" | grep -q "usernameEnv"; then
        log_error "Android credentials should have usernameEnv"
        return 1
    fi
    
    if ! echo "$staging_npm_creds" | grep -q "tokenEnv"; then
        log_error "npm credentials should have tokenEnv"
        return 1
    fi
    
    log_success "Configuration structure alignment validated"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_package_naming_consistency || test_result=1
    test_repository_url_patterns || test_result=1
    test_version_format_compatibility || test_result=1
    test_workflow_input_consistency || test_result=1
    test_configuration_structure_alignment || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi