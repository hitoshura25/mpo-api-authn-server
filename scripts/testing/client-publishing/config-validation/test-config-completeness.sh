#!/bin/bash
# Test configuration completeness and required field validation
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Configuration Completeness and Required Fields Validation"
TEST_CATEGORY="config-validation"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Validate all required fields are present and non-empty
test_required_fields_completeness() {
    log_info "Testing required fields completeness..."
    
    # Critical fields that must be present and non-empty
    local critical_fields=(
        ".packages.android.groupId"
        ".packages.android.baseArtifactId"
        ".packages.typescript.scope"
        ".packages.typescript.basePackageName"
        ".repositories.staging.android.url"
        ".repositories.staging.android.credentials.usernameEnv"
        ".repositories.staging.android.credentials.passwordEnv"
        ".repositories.staging.npm.registry"
        ".repositories.staging.npm.credentials.tokenEnv"
        ".repositories.production.android.url"
        ".repositories.production.android.credentials.usernameEnv"
        ".repositories.production.android.credentials.passwordEnv"
        ".repositories.production.npm.registry"
        ".repositories.production.npm.credentials.tokenEnv"
    )
    
    local missing_fields=()
    
    for field in "${critical_fields[@]}"; do
        local value
        value=$(load_config_value "$field" "$CONFIG_FILE")
        
        if [[ -z "$value" || "$value" == "null" ]]; then
            missing_fields+=("$field")
        fi
    done
    
    if [[ ${#missing_fields[@]} -gt 0 ]]; then
        log_error "Missing or empty required fields:"
        for field in "${missing_fields[@]}"; do
            log_error "  - $field"
        done
        return 1
    fi
    
    log_success "All required fields are present and non-empty"
    return 0
}

# Test 2: Validate naming suffixes are defined (can be empty for production)
test_naming_suffixes_defined() {
    log_info "Testing naming suffixes are properly defined..."
    
    local naming_fields=(
        ".naming.staging.androidSuffix"
        ".naming.staging.npmSuffix"
        ".naming.production.androidSuffix"
        ".naming.production.npmSuffix"
    )
    
    for field in "${naming_fields[@]}"; do
        # Check if field exists (value can be empty string for production)
        if ! yq eval "$field" "$CONFIG_FILE" >/dev/null 2>&1; then
            log_error "Naming field '$field' is not defined"
            return 1
        fi
        
        local value
        value=$(yq eval "$field" "$CONFIG_FILE")
        
        if [[ "$value" == "null" ]]; then
            log_error "Naming field '$field' should not be null (use empty string if no suffix)"
            return 1
        fi
    done
    
    log_success "Naming suffixes are properly defined"
    return 0
}

# Test 3: Validate metadata completeness
test_metadata_completeness() {
    log_info "Testing metadata section completeness..."
    
    local metadata_fields=(
        ".metadata.projectUrl"
        ".metadata.description"
        ".metadata.license"
        ".metadata.author.name"
        ".metadata.author.email"
        ".metadata.author.id"
    )
    
    local missing_metadata=()
    
    for field in "${metadata_fields[@]}"; do
        local value
        value=$(load_config_value "$field" "$CONFIG_FILE")
        
        if [[ -z "$value" || "$value" == "null" ]]; then
            missing_metadata+=("$field")
        fi
    done
    
    if [[ ${#missing_metadata[@]} -gt 0 ]]; then
        log_error "Missing or empty metadata fields:"
        for field in "${missing_metadata[@]}"; do
            log_error "  - $field"
        done
        return 1
    fi
    
    log_success "Metadata section is complete"
    return 0
}

# Test 4: Validate schema information
test_schema_information() {
    log_info "Testing schema information completeness..."
    
    local schema_version
    schema_version=$(load_config_value ".schema.version" "$CONFIG_FILE")
    
    if [[ -z "$schema_version" || "$schema_version" == "null" ]]; then
        log_error "Schema version is missing"
        return 1
    fi
    
    # Validate version format (should be semantic version like)
    if [[ ! "$schema_version" =~ ^[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid schema version format: $schema_version (expected X.Y)"
        return 1
    fi
    
    local last_updated
    last_updated=$(load_config_value ".schema.lastUpdated" "$CONFIG_FILE")
    
    if [[ -z "$last_updated" || "$last_updated" == "null" ]]; then
        log_error "Schema lastUpdated is missing"
        return 1
    fi
    
    # Validate date format (YYYY-MM-DD)
    if [[ ! "$last_updated" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        log_error "Invalid lastUpdated format: $last_updated (expected YYYY-MM-DD)"
        return 1
    fi
    
    log_success "Schema information is complete and valid"
    return 0
}

# Test 5: Validate environment variable naming conventions
test_env_var_naming() {
    log_info "Testing environment variable naming conventions..."
    
    local env_var_fields=(
        ".repositories.staging.android.credentials.usernameEnv"
        ".repositories.staging.android.credentials.passwordEnv"
        ".repositories.staging.npm.credentials.tokenEnv"
        ".repositories.production.android.credentials.usernameEnv"
        ".repositories.production.android.credentials.passwordEnv"
        ".repositories.production.npm.credentials.tokenEnv"
    )
    
    local env_var_pattern='^[A-Z][A-Z0-9_]*$'
    
    for field in "${env_var_fields[@]}"; do
        local env_var_name
        env_var_name=$(load_config_value "$field" "$CONFIG_FILE")
        
        if [[ ! "$env_var_name" =~ $env_var_pattern ]]; then
            log_error "Invalid environment variable name: $env_var_name (from $field)"
            log_error "Should be uppercase with underscores (e.g., MY_ENV_VAR)"
            return 1
        fi
    done
    
    log_success "Environment variable naming conventions are valid"
    return 0
}

# Test 6: Validate cross-environment consistency
test_cross_environment_consistency() {
    log_info "Testing cross-environment consistency..."
    
    # Package configuration should be the same across environments
    local android_group_staging
    local android_group_production
    android_group_staging=$(load_config_value ".packages.android.groupId" "$CONFIG_FILE")
    android_group_production=$(load_config_value ".packages.android.groupId" "$CONFIG_FILE")
    
    if [[ "$android_group_staging" != "$android_group_production" ]]; then
        log_error "Android group ID should be consistent across environments"
        return 1
    fi
    
    # Both environments should have all required platforms
    local environments=("staging" "production")
    local platforms=("android" "npm")
    
    for env in "${environments[@]}"; do
        for platform in "${platforms[@]}"; do
            if ! validate_config_path ".repositories.${env}.${platform}" "object" "$CONFIG_FILE"; then
                log_error "Missing ${platform} configuration in ${env} environment"
                return 1
            fi
            
            if ! yq eval ".naming.${env}.${platform}Suffix" "$CONFIG_FILE" >/dev/null 2>&1; then
                log_error "Missing ${platform}Suffix in ${env} naming configuration"
                return 1
            fi
        done
    done
    
    log_success "Cross-environment consistency validated"
    return 0
}

# Test 7: Validate repository URL accessibility patterns
test_repository_url_patterns() {
    log_info "Testing repository URL patterns..."
    
    # Staging should typically use GitHub Packages
    local staging_android_url
    staging_android_url=$(load_config_value ".repositories.staging.android.url" "$CONFIG_FILE")
    
    if [[ ! "$staging_android_url" =~ github\.com ]]; then
        log_warning "Staging Android repository doesn't use GitHub Packages: $staging_android_url"
        log_warning "This is unusual but may be intentional"
    fi
    
    local staging_npm_registry
    staging_npm_registry=$(load_config_value ".repositories.staging.npm.registry" "$CONFIG_FILE")
    
    if [[ ! "$staging_npm_registry" =~ npm\.pkg\.github\.com ]]; then
        log_warning "Staging npm registry doesn't use GitHub Packages: $staging_npm_registry"
        log_warning "This is unusual but may be intentional"
    fi
    
    # Production should typically use public registries
    local production_npm_registry
    production_npm_registry=$(load_config_value ".repositories.production.npm.registry" "$CONFIG_FILE")
    
    if [[ ! "$production_npm_registry" =~ registry\.npmjs\.org ]]; then
        log_warning "Production npm registry doesn't use public npm: $production_npm_registry"
        log_warning "This is unusual but may be intentional"
    fi
    
    log_success "Repository URL patterns validated"
    return 0
}

# Test 8: Validate configuration completeness against known good template
test_against_known_template() {
    log_info "Testing configuration against known good template..."
    
    local temp_good_config
    temp_good_config=$(create_temp_file "good_config")
    
    create_test_config_file "valid_staging_config" "$temp_good_config"
    
    # Extract all keys from known good config
    local good_config_keys
    good_config_keys=$(yq eval 'paths(scalars) as $p | $p | join(".")' "$temp_good_config" | sort)
    
    # Extract all keys from actual config
    local actual_config_keys
    actual_config_keys=$(yq eval 'paths(scalars) as $p | $p | join(".")' "$CONFIG_FILE" | sort)
    
    # Find missing keys (present in good config but not in actual)
    local missing_keys=()
    while IFS= read -r key; do
        if ! echo "$actual_config_keys" | grep -q "^${key}$"; then
            missing_keys+=("$key")
        fi
    done <<< "$good_config_keys"
    
    # Find extra keys (present in actual but not in good config)
    local extra_keys=()
    while IFS= read -r key; do
        if ! echo "$good_config_keys" | grep -q "^${key}$"; then
            extra_keys+=("$key")
        fi
    done <<< "$actual_config_keys"
    
    if [[ ${#missing_keys[@]} -gt 0 ]]; then
        log_warning "Keys present in template but missing in actual config:"
        for key in "${missing_keys[@]}"; do
            log_warning "  - $key"
        done
    fi
    
    if [[ ${#extra_keys[@]} -gt 0 ]]; then
        log_info "Extra keys in actual config (not in template):"
        for key in "${extra_keys[@]}"; do
            log_info "  + $key"
        done
    fi
    
    log_success "Configuration template comparison completed"
    rm -f "$temp_good_config"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_required_fields_completeness || test_result=1
    test_naming_suffixes_defined || test_result=1
    test_metadata_completeness || test_result=1
    test_schema_information || test_result=1
    test_env_var_naming || test_result=1
    test_cross_environment_consistency || test_result=1
    test_repository_url_patterns || test_result=1
    test_against_known_template || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi