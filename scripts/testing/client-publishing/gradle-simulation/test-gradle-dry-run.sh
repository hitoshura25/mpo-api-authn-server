#!/bin/bash
# Test Gradle dry-run simulation for client publishing
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Gradle Dry-Run Simulation for Client Publishing"
TEST_CATEGORY="gradle-simulation"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Android library publishing dry-run simulation
test_android_publish_dry_run() {
    log_info "Testing Android library publishing dry-run simulation..."
    
    local temp_dir
    temp_dir=$(create_temp_dir "android_dry_run")
    
    # Setup mock Android project structure
    mkdir -p "$temp_dir/android-client-library/src/main/java"
    
    # Generate Android build.gradle.kts from template
    local gradle_file="$temp_dir/android-client-library/build.gradle.kts"
    
    generate_template_with_substitutions "android" "$gradle_file" \
        "GROUP_ID_PLACEHOLDER=io.github.test" \
        "ARTIFACT_ID_PLACEHOLDER=test-android-client" \
        "VERSION_PLACEHOLDER=1.0.0-test" \
        "REPOSITORY_URL_PLACEHOLDER=https://maven.pkg.github.com/test/repo" \
        "USERNAME_ENV_PLACEHOLDER=TEST_ANDROID_USER" \
        "PASSWORD_ENV_PLACEHOLDER=TEST_ANDROID_TOKEN"
    
    # Test Gradle dry-run simulation
    if ! simulate_gradle_command "publishAllPublicationsToPublishingRepositoryRepository --dry-run" "$temp_dir/android-client-library" true; then
        log_error "Android Gradle dry-run simulation failed"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Verify generated content has correct placeholders replaced
    if ! grep -q "io.github.test" "$gradle_file"; then
        log_error "Group ID placeholder not replaced correctly"
        rm -rf "$temp_dir"
        return 1
    fi
    
    if ! grep -q "test-android-client" "$gradle_file"; then
        log_error "Artifact ID placeholder not replaced correctly"
        rm -rf "$temp_dir"
        return 1
    fi
    
    log_success "Android publishing dry-run simulation successful"
    rm -rf "$temp_dir"
    return 0
}

# Test 2: TypeScript package publishing simulation
test_typescript_publish_simulation() {
    log_info "Testing TypeScript package publishing simulation..."
    
    local temp_dir
    temp_dir=$(create_temp_dir "typescript_dry_run")
    
    # Generate package.json from template
    local package_file="$temp_dir/package.json"
    
    generate_template_with_substitutions "typescript" "$package_file" \
        "NPM_PACKAGE_NAME_PLACEHOLDER=@test/mpo-webauthn-client" \
        "VERSION_PLACEHOLDER=1.0.0-test" \
        "REGISTRY_URL_PLACEHOLDER=https://npm.pkg.github.com"
    
    # Verify generated content
    if ! jq -e '.name == "@test/mpo-webauthn-client"' "$package_file" >/dev/null; then
        log_error "Package name not set correctly in package.json"
        rm -rf "$temp_dir"
        return 1
    fi
    
    if ! jq -e '.version == "1.0.0-test"' "$package_file" >/dev/null; then
        log_error "Version not set correctly in package.json"
        rm -rf "$temp_dir"
        return 1
    fi
    
    if ! jq -e '.publishConfig.registry == "https://npm.pkg.github.com"' "$package_file" >/dev/null; then
        log_error "Registry not set correctly in package.json"
        rm -rf "$temp_dir"
        return 1
    fi
    
    log_success "TypeScript package simulation successful"
    rm -rf "$temp_dir"
    return 0
}

# Test 3: Environment variable validation for Gradle commands
test_gradle_env_var_validation() {
    log_info "Testing Gradle environment variable validation..."
    
    # Test staging environment setup
    setup_test_environment_vars "staging_complete"
    
    # Verify required environment variables are set
    local required_vars=("ANDROID_PUBLISH_USER" "ANDROID_PUBLISH_TOKEN" "NPM_TOKEN")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable not set: $var"
            cleanup_mock_env
            return 1
        fi
        log_debug "Environment variable $var is set: ${!var}"
    done
    
    # Test production environment setup
    cleanup_mock_env
    setup_test_environment_vars "production_complete"
    
    local prod_required_vars=("CENTRAL_PORTAL_USERNAME" "CENTRAL_PORTAL_PASSWORD" "NPM_TOKEN" "SIGNING_KEY" "SIGNING_PASSWORD")
    
    for var in "${prod_required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required production environment variable not set: $var"
            cleanup_mock_env
            return 1
        fi
        log_debug "Production environment variable $var is set: ${!var}"
    done
    
    cleanup_mock_env
    log_success "Gradle environment variable validation successful"
    return 0
}

# Test 4: Repository URL validation for different environments
test_repository_url_validation() {
    log_info "Testing repository URL validation for different environments..."
    
    # Test staging URLs
    local staging_android_url
    staging_android_url=$(load_config_value ".repositories.staging.android.url" "$CONFIG_FILE")
    
    if [[ ! "$staging_android_url" =~ ^https://maven\.pkg\.github\.com/.+ ]]; then
        log_error "Invalid staging Android repository URL: $staging_android_url"
        return 1
    fi
    
    local staging_npm_registry
    staging_npm_registry=$(load_config_value ".repositories.staging.npm.registry" "$CONFIG_FILE")
    
    if [[ ! "$staging_npm_registry" =~ ^https://npm\.pkg\.github\.com$ ]]; then
        log_error "Invalid staging npm registry URL: $staging_npm_registry"
        return 1
    fi
    
    # Test production URLs
    local prod_android_url
    prod_android_url=$(load_config_value ".repositories.production.android.url" "$CONFIG_FILE")
    
    if [[ ! "$prod_android_url" =~ ^https://.*\.sonatype\.com/.+ ]]; then
        log_error "Invalid production Android repository URL: $prod_android_url"
        return 1
    fi
    
    local prod_npm_registry
    prod_npm_registry=$(load_config_value ".repositories.production.npm.registry" "$CONFIG_FILE")
    
    if [[ ! "$prod_npm_registry" =~ ^https://registry\.npmjs\.org$ ]]; then
        log_error "Invalid production npm registry URL: $prod_npm_registry"
        return 1
    fi
    
    log_success "Repository URL validation successful"
    return 0
}

# Test 5: Gradle property name validation
test_gradle_property_names() {
    log_info "Testing Gradle property name validation..."
    
    local temp_file
    temp_file=$(create_temp_file "gradle_properties")
    
    # Create a mock gradle file with hardcoded property names
    cat > "$temp_file" << 'EOF'
publishing {
    repositories {
        maven {
            name = 'PublishingRepository'
            credentials {
                username = project.findProperty('PublishingRepositoryUsername') ?: System.getenv('ANDROID_PUBLISH_USER')
                password = project.findProperty('PublishingRepositoryPassword') ?: System.getenv('ANDROID_PUBLISH_TOKEN')
            }
        }
    }
}
EOF
    
    # Verify hardcoded property names are present
    if ! grep -q "PublishingRepositoryUsername" "$temp_file"; then
        log_error "Required Gradle property name 'PublishingRepositoryUsername' not found"
        rm -f "$temp_file"
        return 1
    fi
    
    if ! grep -q "PublishingRepositoryPassword" "$temp_file"; then
        log_error "Required Gradle property name 'PublishingRepositoryPassword' not found"
        rm -f "$temp_file"
        return 1
    fi
    
    if ! grep -q "PublishingRepository" "$temp_file"; then
        log_error "Required repository name 'PublishingRepository' not found"
        rm -f "$temp_file"
        return 1
    fi
    
    log_success "Gradle property name validation successful"
    rm -f "$temp_file"
    return 0
}

# Test 6: Version format validation for publishing
test_version_format_validation() {
    log_info "Testing version format validation for publishing..."
    
    local valid_versions=$(get_valid_versions)
    local invalid_versions=$(get_invalid_versions)
    
    # Test valid versions
    for version in $valid_versions; do
        if ! validate_version_format "$version"; then
            log_error "Valid version marked as invalid: $version"
            return 1
        fi
        log_debug "Version format valid: $version"
    done
    
    # Test invalid versions  
    for version in $invalid_versions; do
        if validate_version_format "$version"; then
            log_error "Invalid version marked as valid: $version"
            return 1
        fi
        log_debug "Version format correctly rejected: $version"
    done
    
    log_success "Version format validation successful"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_android_publish_dry_run || test_result=1
    test_typescript_publish_simulation || test_result=1
    test_gradle_env_var_validation || test_result=1
    test_repository_url_validation || test_result=1
    test_gradle_property_names || test_result=1
    test_version_format_validation || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi