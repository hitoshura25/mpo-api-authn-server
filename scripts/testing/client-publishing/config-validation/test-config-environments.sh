#!/bin/bash
# Test environment-specific configuration validation
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Environment-Specific Configuration Validation"
TEST_CATEGORY="config-validation"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Validate staging environment configuration
test_staging_environment_config() {
    log_info "Testing staging environment configuration..."
    
    # Test staging Android configuration
    local staging_android_url
    staging_android_url=$(load_config_value ".repositories.staging.android.url" "$CONFIG_FILE")
    
    assert_not_empty "$staging_android_url" "Staging Android repository URL"
    
    local staging_android_username_env
    staging_android_username_env=$(load_config_value ".repositories.staging.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    assert_not_empty "$staging_android_username_env" "Staging Android username environment variable"
    
    local staging_android_password_env
    staging_android_password_env=$(load_config_value ".repositories.staging.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    assert_not_empty "$staging_android_password_env" "Staging Android password environment variable"
    
    # Test staging npm configuration
    local staging_npm_registry
    staging_npm_registry=$(load_config_value ".repositories.staging.npm.registry" "$CONFIG_FILE")
    
    assert_not_empty "$staging_npm_registry" "Staging npm registry URL"
    
    local staging_npm_token_env
    staging_npm_token_env=$(load_config_value ".repositories.staging.npm.credentials.tokenEnv" "$CONFIG_FILE")
    
    assert_not_empty "$staging_npm_token_env" "Staging npm token environment variable"
    
    # Test staging naming configuration
    local staging_android_suffix
    staging_android_suffix=$(yq eval ".naming.staging.androidSuffix" "$CONFIG_FILE")
    
    # Suffix can be empty, but should not be null
    if [[ "$staging_android_suffix" == "null" ]]; then
        log_error "Staging Android suffix should not be null (use empty string if no suffix)"
        return 1
    fi
    
    local staging_npm_suffix
    staging_npm_suffix=$(yq eval ".naming.staging.npmSuffix" "$CONFIG_FILE")
    
    if [[ "$staging_npm_suffix" == "null" ]]; then
        log_error "Staging npm suffix should not be null (use empty string if no suffix)"
        return 1
    fi
    
    log_success "Staging environment configuration is valid"
    return 0
}

# Test 2: Validate production environment configuration
test_production_environment_config() {
    log_info "Testing production environment configuration..."
    
    # Test production Android configuration
    local production_android_url
    production_android_url=$(load_config_value ".repositories.production.android.url" "$CONFIG_FILE")
    
    assert_not_empty "$production_android_url" "Production Android repository URL"
    
    local production_android_username_env
    production_android_username_env=$(load_config_value ".repositories.production.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    assert_not_empty "$production_android_username_env" "Production Android username environment variable"
    
    local production_android_password_env
    production_android_password_env=$(load_config_value ".repositories.production.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    assert_not_empty "$production_android_password_env" "Production Android password environment variable"
    
    # Test production npm configuration
    local production_npm_registry
    production_npm_registry=$(load_config_value ".repositories.production.npm.registry" "$CONFIG_FILE")
    
    assert_not_empty "$production_npm_registry" "Production npm registry URL"
    
    local production_npm_token_env
    production_npm_token_env=$(load_config_value ".repositories.production.npm.credentials.tokenEnv" "$CONFIG_FILE")
    
    assert_not_empty "$production_npm_token_env" "Production npm token environment variable"
    
    # Test production naming configuration
    local production_android_suffix
    production_android_suffix=$(yq eval ".naming.production.androidSuffix" "$CONFIG_FILE")
    
    if [[ "$production_android_suffix" == "null" ]]; then
        log_error "Production Android suffix should not be null (use empty string if no suffix)"
        return 1
    fi
    
    local production_npm_suffix
    production_npm_suffix=$(yq eval ".naming.production.npmSuffix" "$CONFIG_FILE")
    
    if [[ "$production_npm_suffix" == "null" ]]; then
        log_error "Production npm suffix should not be null (use empty string if no suffix)"
        return 1
    fi
    
    log_success "Production environment configuration is valid"
    return 0
}

# Test 3: Test environment-specific credential naming patterns
test_credential_naming_patterns() {
    log_info "Testing credential naming patterns for different environments..."
    
    # Staging credentials should typically be different from production
    local staging_android_user_env
    staging_android_user_env=$(load_config_value ".repositories.staging.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    local staging_android_pass_env
    staging_android_pass_env=$(load_config_value ".repositories.staging.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    local production_android_user_env
    production_android_user_env=$(load_config_value ".repositories.production.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    local production_android_pass_env
    production_android_pass_env=$(load_config_value ".repositories.production.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    # Check that staging and production use different credential environment variables
    if [[ "$staging_android_user_env" == "$production_android_user_env" ]]; then
        log_warning "Staging and production use the same Android username environment variable: $staging_android_user_env"
        log_warning "This may lead to credential conflicts"
    fi
    
    if [[ "$staging_android_pass_env" == "$production_android_pass_env" ]]; then
        log_warning "Staging and production use the same Android password environment variable: $staging_android_pass_env"
        log_warning "This may lead to credential conflicts"
    fi
    
    # npm tokens can be the same for GitHub Packages vs public npm
    local staging_npm_token_env
    staging_npm_token_env=$(load_config_value ".repositories.staging.npm.credentials.tokenEnv" "$CONFIG_FILE")
    
    local production_npm_token_env
    production_npm_token_env=$(load_config_value ".repositories.production.npm.credentials.tokenEnv" "$CONFIG_FILE")
    
    if [[ "$staging_npm_token_env" == "$production_npm_token_env" ]]; then
        log_info "Staging and production use the same npm token environment variable: $staging_npm_token_env"
        log_info "This is acceptable if the token has access to both registries"
    fi
    
    log_success "Credential naming patterns validated"
    return 0
}

# Test 4: Test environment-specific URL patterns
test_environment_url_patterns() {
    log_info "Testing environment-specific URL patterns..."
    
    # Staging URLs should typically point to GitHub Packages or staging registries
    local staging_android_url
    staging_android_url=$(load_config_value ".repositories.staging.android.url" "$CONFIG_FILE")
    
    if [[ "$staging_android_url" =~ maven\.pkg\.github\.com ]]; then
        log_debug "Staging Android uses GitHub Packages (recommended for staging)"
    elif [[ "$staging_android_url" =~ ossrh.*staging ]]; then
        log_debug "Staging Android uses Maven Central staging (acceptable)"
    else
        log_warning "Staging Android URL pattern is unusual: $staging_android_url"
    fi
    
    local staging_npm_registry
    staging_npm_registry=$(load_config_value ".repositories.staging.npm.registry" "$CONFIG_FILE")
    
    if [[ "$staging_npm_registry" =~ npm\.pkg\.github\.com ]]; then
        log_debug "Staging npm uses GitHub Packages (recommended for staging)"
    else
        log_warning "Staging npm registry pattern is unusual: $staging_npm_registry"
    fi
    
    # Production URLs should typically point to public registries
    local production_android_url
    production_android_url=$(load_config_value ".repositories.production.android.url" "$CONFIG_FILE")
    
    if [[ "$production_android_url" =~ ossrh.*central|oss\.sonatype\.org ]]; then
        log_debug "Production Android uses Maven Central (recommended for production)"
    elif [[ "$production_android_url" =~ maven\.pkg\.github\.com ]]; then
        log_warning "Production Android uses GitHub Packages (unusual for production)"
    else
        log_info "Production Android uses custom repository: $production_android_url"
    fi
    
    local production_npm_registry
    production_npm_registry=$(load_config_value ".repositories.production.npm.registry" "$CONFIG_FILE")
    
    if [[ "$production_npm_registry" =~ registry\.npmjs\.org ]]; then
        log_debug "Production npm uses public npm registry (recommended for production)"
    else
        log_info "Production npm uses custom registry: $production_npm_registry"
    fi
    
    log_success "Environment-specific URL patterns validated"
    return 0
}

# Test 5: Test suffix application logic
test_suffix_application_logic() {
    log_info "Testing suffix application logic..."
    
    # Get base package names
    local android_base_artifact
    android_base_artifact=$(load_config_value ".packages.android.baseArtifactId" "$CONFIG_FILE")
    
    local npm_base_package
    npm_base_package=$(load_config_value ".packages.typescript.basePackageName" "$CONFIG_FILE")
    
    # Get suffixes
    local staging_android_suffix
    staging_android_suffix=$(yq eval ".naming.staging.androidSuffix" "$CONFIG_FILE")
    
    local staging_npm_suffix
    staging_npm_suffix=$(yq eval ".naming.staging.npmSuffix" "$CONFIG_FILE")
    
    local production_android_suffix
    production_android_suffix=$(yq eval ".naming.production.androidSuffix" "$CONFIG_FILE")
    
    local production_npm_suffix
    production_npm_suffix=$(yq eval ".naming.production.npmSuffix" "$CONFIG_FILE")
    
    # Test staging package names
    local expected_staging_android="${android_base_artifact}${staging_android_suffix}"
    local expected_staging_npm="${npm_base_package}${staging_npm_suffix}"
    
    log_debug "Expected staging Android artifact: $expected_staging_android"
    log_debug "Expected staging npm package: $expected_staging_npm"
    
    # Test production package names
    local expected_production_android="${android_base_artifact}${production_android_suffix}"
    local expected_production_npm="${npm_base_package}${production_npm_suffix}"
    
    log_debug "Expected production Android artifact: $expected_production_android"
    log_debug "Expected production npm package: $expected_production_npm"
    
    # Validate that staging and production names are different (unless production has no suffix)
    if [[ "$expected_staging_android" == "$expected_production_android" && -n "$staging_android_suffix" ]]; then
        log_warning "Staging and production Android artifacts have the same name: $expected_staging_android"
        log_warning "This may cause conflicts if both are published to the same registry"
    fi
    
    if [[ "$expected_staging_npm" == "$expected_production_npm" && -n "$staging_npm_suffix" ]]; then
        log_warning "Staging and production npm packages have the same name: $expected_staging_npm"
        log_warning "This may cause conflicts if both are published to the same registry"
    fi
    
    log_success "Suffix application logic validated"
    return 0
}

# Test 6: Test environment isolation
test_environment_isolation() {
    log_info "Testing environment isolation..."
    
    # Test that staging and production configurations don't overlap in ways that could cause conflicts
    local staging_android_url
    staging_android_url=$(load_config_value ".repositories.staging.android.url" "$CONFIG_FILE")
    
    local production_android_url
    production_android_url=$(load_config_value ".repositories.production.android.url" "$CONFIG_FILE")
    
    # If both use the same repository URL, they should have different artifact names
    if [[ "$staging_android_url" == "$production_android_url" ]]; then
        local android_base_artifact
        android_base_artifact=$(load_config_value ".packages.android.baseArtifactId" "$CONFIG_FILE")
        
        local staging_android_suffix
        staging_android_suffix=$(yq eval ".naming.staging.androidSuffix" "$CONFIG_FILE")
        
        if [[ -z "$staging_android_suffix" ]]; then
            log_error "Same repository URL but no staging suffix - this will cause conflicts"
            log_error "Staging URL: $staging_android_url"
            log_error "Production URL: $production_android_url"
            return 1
        fi
    fi
    
    # Similar check for npm
    local staging_npm_registry
    staging_npm_registry=$(load_config_value ".repositories.staging.npm.registry" "$CONFIG_FILE")
    
    local production_npm_registry
    production_npm_registry=$(load_config_value ".repositories.production.npm.registry" "$CONFIG_FILE")
    
    if [[ "$staging_npm_registry" == "$production_npm_registry" ]]; then
        local staging_npm_suffix
        staging_npm_suffix=$(yq eval ".naming.staging.npmSuffix" "$CONFIG_FILE")
        
        if [[ -z "$staging_npm_suffix" ]]; then
            log_error "Same npm registry but no staging suffix - this will cause conflicts"
            log_error "Staging registry: $staging_npm_registry"
            log_error "Production registry: $production_npm_registry"
            return 1
        fi
    fi
    
    log_success "Environment isolation validated"
    return 0
}

# Test 7: Test environment-specific workflow compatibility
test_workflow_compatibility() {
    log_info "Testing workflow compatibility with environment configurations..."
    
    # Test that all required environment variables are properly named for workflow usage
    local all_env_vars=(
        $(load_config_value ".repositories.staging.android.credentials.usernameEnv" "$CONFIG_FILE")
        $(load_config_value ".repositories.staging.android.credentials.passwordEnv" "$CONFIG_FILE")
        $(load_config_value ".repositories.staging.npm.credentials.tokenEnv" "$CONFIG_FILE")
        $(load_config_value ".repositories.production.android.credentials.usernameEnv" "$CONFIG_FILE")
        $(load_config_value ".repositories.production.android.credentials.passwordEnv" "$CONFIG_FILE")
        $(load_config_value ".repositories.production.npm.credentials.tokenEnv" "$CONFIG_FILE")
    )
    
    # Check for duplicate environment variable names across different credential types
    local seen_vars=()
    local duplicate_vars=()
    
    for var in "${all_env_vars[@]}"; do
        if [[ ${#seen_vars[@]} -gt 0 && " ${seen_vars[*]} " =~ " ${var} " ]]; then
            duplicate_vars+=("$var")
        else
            seen_vars+=("$var")
        fi
    done
    
    if [[ ${#duplicate_vars[@]} -gt 0 ]]; then
        log_warning "Duplicate environment variable names detected:"
        for var in "${duplicate_vars[@]}"; do
            log_warning "  - $var"
        done
        log_warning "This may be intentional but could cause confusion"
    fi
    
    log_success "Workflow compatibility validated"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_staging_environment_config || test_result=1
    test_production_environment_config || test_result=1
    test_credential_naming_patterns || test_result=1
    test_environment_url_patterns || test_result=1
    test_suffix_application_logic || test_result=1
    test_environment_isolation || test_result=1
    test_workflow_compatibility || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi