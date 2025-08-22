#!/bin/bash
# Test configuration file structure and schema validation
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Configuration File Structure and Schema Validation"
TEST_CATEGORY="config-validation"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Define required configuration paths
declare -a REQUIRED_PATHS=(
    ".packages"
    ".packages.android"
    ".packages.android.groupId"
    ".packages.android.baseArtifactId"
    ".packages.typescript"
    ".packages.typescript.scope"
    ".packages.typescript.scope.staging"
    ".packages.typescript.scope.production"
    ".packages.typescript.basePackageName"
    ".repositories"
    ".repositories.staging"
    ".repositories.staging.android"
    ".repositories.staging.android.url"
    ".repositories.staging.android.credentials"
    ".repositories.staging.android.credentials.usernameEnv"
    ".repositories.staging.android.credentials.passwordEnv"
    ".repositories.staging.npm"
    ".repositories.staging.npm.registry"
    ".repositories.staging.npm.credentials"
    ".repositories.staging.npm.credentials.tokenEnv"
    ".repositories.production"
    ".repositories.production.android"
    ".repositories.production.android.url"
    ".repositories.production.android.credentials"
    ".repositories.production.android.credentials.usernameEnv"
    ".repositories.production.android.credentials.passwordEnv"
    ".repositories.production.npm"
    ".repositories.production.npm.registry"
    ".repositories.production.npm.credentials"
    ".repositories.production.npm.credentials.tokenEnv"
    ".naming"
    ".naming.staging"
    ".naming.staging.androidSuffix"
    ".naming.staging.npmSuffix"
    ".naming.production"
    ".naming.production.androidSuffix"
    ".naming.production.npmSuffix"
    ".metadata"
    ".schema"
    ".schema.version"
)

# Test 1: Validate all required sections exist
test_required_sections() {
    log_info "Testing required configuration sections..."
    
    local missing_sections=()
    
    for path in "${REQUIRED_PATHS[@]}"; do
        # Special handling for suffix paths which can be empty strings
        if [[ "$path" == ".naming.production.androidSuffix" || "$path" == ".naming.production.npmSuffix" ]]; then
            if ! validate_config_path "$path" "string_or_empty" "$CONFIG_FILE" 2>/dev/null; then
                missing_sections+=("$path")
            fi
        elif ! validate_config_path "$path" "string" "$CONFIG_FILE" 2>/dev/null; then
            # Check if it's an object type
            if ! validate_config_path "$path" "object" "$CONFIG_FILE" 2>/dev/null; then
                missing_sections+=("$path")
            fi
        fi
    done
    
    if [[ ${#missing_sections[@]} -gt 0 ]]; then
        log_error "Missing required configuration sections:"
        for section in "${missing_sections[@]}"; do
            log_error "  - $section"
        done
        return 1
    fi
    
    log_success "All required configuration sections present"
    return 0
}

# Test 2: Validate configuration data types
test_configuration_types() {
    log_info "Testing configuration data types..."
    
    # Test object types
    local object_paths=(
        ".packages"
        ".packages.android"
        ".packages.typescript"
        ".packages.typescript.scope"
        ".repositories"
        ".repositories.staging"
        ".repositories.staging.android"
        ".repositories.staging.android.credentials"
        ".repositories.staging.npm"
        ".repositories.staging.npm.credentials"
        ".repositories.production"
        ".repositories.production.android"
        ".repositories.production.android.credentials"
        ".repositories.production.npm"
        ".repositories.production.npm.credentials"
        ".naming"
        ".naming.staging"
        ".naming.production"
        ".metadata"
        ".metadata.author"
        ".schema"
    )
    
    for path in "${object_paths[@]}"; do
        if ! validate_config_path "$path" "object" "$CONFIG_FILE"; then
            log_error "Configuration path '$path' should be an object"
            return 1
        fi
    done
    
    # Test string types (non-empty)
    local string_paths=(
        ".packages.android.groupId"
        ".packages.android.baseArtifactId"
        ".packages.typescript.scope.staging"
        ".packages.typescript.scope.production"
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
        ".metadata.projectUrl"
        ".metadata.description"
        ".metadata.license"
        ".metadata.author.name"
        ".metadata.author.email"
        ".metadata.author.id"
        ".schema.version"
        ".schema.lastUpdated"
    )
    
    for path in "${string_paths[@]}"; do
        if ! validate_config_path "$path" "string" "$CONFIG_FILE"; then
            log_error "Configuration path '$path' should be a non-empty string"
            return 1
        fi
    done
    
    log_success "Configuration data types are valid"
    return 0
}

# Test 3: Validate environment-specific structure consistency
test_environment_consistency() {
    log_info "Testing environment-specific structure consistency..."
    
    # Both staging and production should have the same structure
    local environments=("staging" "production")
    local platforms=("android" "npm")
    
    for env in "${environments[@]}"; do
        for platform in "${platforms[@]}"; do
            local base_path=".repositories.${env}.${platform}"
            
            # Check platform section exists
            if ! validate_config_path "$base_path" "object" "$CONFIG_FILE"; then
                log_error "Missing ${platform} configuration for ${env} environment"
                return 1
            fi
            
            # Check required platform-specific fields
            case "$platform" in
                "android")
                    if ! validate_config_path "${base_path}.url" "string" "$CONFIG_FILE"; then
                        log_error "Missing url for ${platform} in ${env} environment"
                        return 1
                    fi
                    if ! validate_config_path "${base_path}.credentials.usernameEnv" "string" "$CONFIG_FILE"; then
                        log_error "Missing usernameEnv for ${platform} in ${env} environment"
                        return 1
                    fi
                    if ! validate_config_path "${base_path}.credentials.passwordEnv" "string" "$CONFIG_FILE"; then
                        log_error "Missing passwordEnv for ${platform} in ${env} environment"
                        return 1
                    fi
                    ;;
                "npm")
                    if ! validate_config_path "${base_path}.registry" "string" "$CONFIG_FILE"; then
                        log_error "Missing registry for ${platform} in ${env} environment"
                        return 1
                    fi
                    if ! validate_config_path "${base_path}.credentials.tokenEnv" "string" "$CONFIG_FILE"; then
                        log_error "Missing tokenEnv for ${platform} in ${env} environment"
                        return 1
                    fi
                    ;;
            esac
            
            # Check naming configuration
            local naming_path=".naming.${env}.${platform}Suffix"
            if ! yq eval "$naming_path" "$CONFIG_FILE" >/dev/null 2>&1; then
                log_error "Missing naming suffix for ${platform} in ${env} environment"
                return 1
            fi
        done
    done
    
    log_success "Environment-specific structure is consistent"
    return 0
}

# Test 4: Validate URL formats
test_url_formats() {
    log_info "Testing URL format validation..."
    
    local url_paths=(
        ".repositories.staging.android.url"
        ".repositories.staging.npm.registry"
        ".repositories.production.android.url"
        ".repositories.production.npm.registry"
        ".metadata.projectUrl"
    )
    
    for path in "${url_paths[@]}"; do
        local url_value
        url_value=$(load_config_value "$path" "$CONFIG_FILE")
        
        if [[ ! "$url_value" =~ ^https?:// ]]; then
            log_error "Invalid URL format for '$path': $url_value"
            log_error "URLs should start with http:// or https://"
            return 1
        fi
    done
    
    log_success "URL formats are valid"
    return 0
}

# Test 5: Validate package naming conventions
test_package_naming_conventions() {
    log_info "Testing package naming conventions..."
    
    # Android group ID should follow Java package naming
    local android_group_id
    android_group_id=$(load_config_value ".packages.android.groupId" "$CONFIG_FILE")
    
    if [[ ! "$android_group_id" =~ ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$ ]]; then
        log_error "Invalid Android group ID format: $android_group_id"
        log_error "Should follow Java package naming convention (lowercase, dots, underscores)"
        return 1
    fi
    
    # Android artifact ID should be valid Maven artifact ID
    local android_artifact_id
    android_artifact_id=$(load_config_value ".packages.android.baseArtifactId" "$CONFIG_FILE")
    
    if [[ ! "$android_artifact_id" =~ ^[a-z][a-z0-9-]*$ ]]; then
        log_error "Invalid Android artifact ID format: $android_artifact_id"
        log_error "Should be lowercase with hyphens allowed"
        return 1
    fi
    
    # TypeScript scopes should start with @ for both environments
    local staging_scope production_scope
    staging_scope=$(load_config_value ".packages.typescript.scope.staging" "$CONFIG_FILE")
    production_scope=$(load_config_value ".packages.typescript.scope.production" "$CONFIG_FILE")
    
    for scope_name in "staging" "production"; do
        local scope_value
        if [[ "$scope_name" == "staging" ]]; then
            scope_value="$staging_scope"
        else
            scope_value="$production_scope"
        fi
        
        if [[ ! "$scope_value" =~ ^@[a-z0-9-]+$ ]]; then
            log_error "Invalid TypeScript $scope_name scope format: $scope_value"
            log_error "Should start with @ and contain lowercase letters, numbers, hyphens"
            return 1
        fi
    done
    
    # TypeScript package name should be valid npm package name
    local typescript_package
    typescript_package=$(load_config_value ".packages.typescript.basePackageName" "$CONFIG_FILE")
    
    if [[ ! "$typescript_package" =~ ^[a-z0-9-]+$ ]]; then
        log_error "Invalid TypeScript package name format: $typescript_package"
        log_error "Should be lowercase with hyphens allowed"
        return 1
    fi
    
    log_success "Package naming conventions are valid"
    return 0
}

# Test 6: Validate email format in metadata
test_email_format() {
    log_info "Testing email format in metadata..."
    
    local author_email
    author_email=$(load_config_value ".metadata.author.email" "$CONFIG_FILE")
    
    # Basic email validation
    if [[ ! "$author_email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        log_error "Invalid email format: $author_email"
        return 1
    fi
    
    log_success "Email format is valid"
    return 0
}

# Test 7: Test structure with missing sections
test_missing_sections_detection() {
    log_info "Testing detection of missing configuration sections..."
    
    local temp_config
    temp_config=$(create_temp_file "missing_sections")
    
    # Create config missing packages section
    create_test_config_file "missing_packages_section" "$temp_config"
    
    # This should fail validation
    if validate_config_path ".packages" "object" "$temp_config" 2>/dev/null; then
        log_error "Failed to detect missing packages section"
        rm -f "$temp_config"
        return 1
    fi
    
    # Create config missing android config
    create_test_config_file "missing_android_config" "$temp_config"
    
    if validate_config_path ".packages.android" "object" "$temp_config" 2>/dev/null; then
        log_error "Failed to detect missing android configuration"
        rm -f "$temp_config"
        return 1
    fi
    
    log_success "Missing sections detection works correctly"
    rm -f "$temp_config"
    return 0
}

# Test 8: Test null values detection
test_null_values_detection() {
    log_info "Testing detection of null values..."
    
    local temp_config
    temp_config=$(create_temp_file "null_values")
    
    create_test_config_file "null_values_config" "$temp_config"
    
    # These should fail validation due to null values
    if validate_config_path ".packages.android.groupId" "string" "$temp_config" 2>/dev/null; then
        log_error "Failed to detect null groupId value"
        rm -f "$temp_config"
        return 1
    fi
    
    if validate_config_path ".packages.typescript.basePackageName" "string" "$temp_config" 2>/dev/null; then
        log_error "Failed to detect null basePackageName value"
        rm -f "$temp_config"
        return 1
    fi
    
    log_success "Null values detection works correctly"
    rm -f "$temp_config"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_required_sections || test_result=1
    test_configuration_types || test_result=1
    test_environment_consistency || test_result=1
    test_url_formats || test_result=1
    test_package_naming_conventions || test_result=1
    test_email_format || test_result=1
    test_missing_sections_detection || test_result=1
    test_null_values_detection || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi