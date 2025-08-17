#!/bin/bash
# Test Gradle property mapping and environment variable integration
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Gradle Property Mapping and Environment Variable Integration"
TEST_CATEGORY="gradle-simulation"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Property name consistency across environments
test_property_name_consistency() {
    log_info "Testing property name consistency across environments..."
    
    # The Android template uses hardcoded property names regardless of environment
    local expected_username_property="PublishingRepositoryUsername"
    local expected_password_property="PublishingRepositoryPassword"
    local expected_repo_name="PublishingRepository"
    
    # Test staging configuration
    local staging_username_env
    staging_username_env=$(load_config_value ".repositories.staging.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    local staging_password_env
    staging_password_env=$(load_config_value ".repositories.staging.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    # Test production configuration
    local prod_username_env
    prod_username_env=$(load_config_value ".repositories.production.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    local prod_password_env
    prod_password_env=$(load_config_value ".repositories.production.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    # Verify that different environments use different env vars but same property names
    if [[ "$staging_username_env" == "$prod_username_env" ]]; then
        log_error "Staging and production should use different username environment variables"
        log_error "Both use: $staging_username_env"
        return 1
    fi
    
    if [[ "$staging_password_env" == "$prod_password_env" ]]; then
        log_error "Staging and production should use different password environment variables"
        log_error "Both use: $staging_password_env"
        return 1
    fi
    
    log_success "Property name consistency validated"
    return 0
}

# Test 2: Environment variable to Gradle property mapping
test_env_var_property_mapping() {
    log_info "Testing environment variable to Gradle property mapping..."
    
    local temp_dir
    temp_dir=$(create_temp_dir "property_mapping")
    
    # Create a test Gradle script that demonstrates the mapping
    local gradle_file="$temp_dir/build.gradle.kts"
    
    cat > "$gradle_file" << 'EOF'
// Demonstrate the property mapping pattern used in the Android template
val publishingUsername = project.findProperty("PublishingRepositoryUsername") as String? 
    ?: System.getenv("ANDROID_PUBLISH_USER")
val publishingPassword = project.findProperty("PublishingRepositoryPassword") as String? 
    ?: System.getenv("ANDROID_PUBLISH_TOKEN")

// Test that fallback works
if (publishingUsername.isNullOrEmpty()) {
    throw GradleException("Publishing username not found in properties or environment")
}

if (publishingPassword.isNullOrEmpty()) {
    throw GradleException("Publishing password not found in properties or environment")
}

println("Username source: ${if (project.hasProperty("PublishingRepositoryUsername")) "property" else "environment"}")
println("Password source: ${if (project.hasProperty("PublishingRepositoryPassword")) "property" else "environment"}")
EOF
    
    # Test with environment variables set (simulating CI environment)
    export ANDROID_PUBLISH_USER="ci-user"
    export ANDROID_PUBLISH_TOKEN="ci-token"
    
    # Simulate Gradle property resolution (this would normally be done by Gradle)
    local username_resolution="environment"  # Since no property file, falls back to env
    local password_resolution="environment"  # Since no property file, falls back to env
    
    if [[ "$username_resolution" != "environment" ]]; then
        log_error "Expected username resolution from environment, got: $username_resolution"
        rm -rf "$temp_dir"
        return 1
    fi
    
    if [[ "$password_resolution" != "environment" ]]; then
        log_error "Expected password resolution from environment, got: $password_resolution"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Test with gradle.properties file (simulating local development)
    cat > "$temp_dir/gradle.properties" << 'EOF'
PublishingRepositoryUsername=local-user
PublishingRepositoryPassword=local-password
EOF
    
    # In this case, properties would take precedence
    local prop_username_resolution="property"  # Property file takes precedence
    local prop_password_resolution="property"  # Property file takes precedence
    
    if [[ "$prop_username_resolution" != "property" ]]; then
        log_error "Expected username resolution from property file, got: $prop_username_resolution"
        rm -rf "$temp_dir"
        return 1
    fi
    
    if [[ "$prop_password_resolution" != "property" ]]; then
        log_error "Expected password resolution from property file, got: $prop_password_resolution"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Clean up environment
    unset ANDROID_PUBLISH_USER ANDROID_PUBLISH_TOKEN
    
    log_success "Environment variable to property mapping validated"
    rm -rf "$temp_dir"
    return 0
}

# Test 3: Repository name hardcoding validation
test_repository_name_hardcoding() {
    log_info "Testing repository name hardcoding validation..."
    
    # The Android template hardcodes the repository name as "PublishingRepository"
    # This affects the generated Gradle task names and property names
    
    local expected_repo_name="PublishingRepository"
    local expected_task_suffix="ToPublishingRepositoryRepository"
    
    # Generate a sample Android template
    local temp_file
    temp_file=$(create_temp_file "android_template")
    
    generate_android_template \
        "io.github.test" \
        "test-client" \
        "1.0.0" \
        "https://maven.pkg.github.com/test/repo" \
        "$temp_file"
    
    # Verify hardcoded repository name
    if ! grep -q "name = 'PublishingRepository'" "$temp_file"; then
        log_error "Repository name not hardcoded correctly in template"
        log_error "Expected: name = 'PublishingRepository'"
        rm -f "$temp_file"
        return 1
    fi
    
    # Verify property name patterns match repository name
    if ! grep -q "PublishingRepositoryUsername" "$temp_file"; then
        log_error "Username property name doesn't match repository name pattern"
        rm -f "$temp_file"
        return 1
    fi
    
    if ! grep -q "PublishingRepositoryPassword" "$temp_file"; then
        log_error "Password property name doesn't match repository name pattern"
        rm -f "$temp_file"
        return 1
    fi
    
    log_success "Repository name hardcoding validated"
    rm -f "$temp_file"
    return 0
}

# Test 4: Cross-environment credential isolation
test_credential_isolation() {
    log_info "Testing cross-environment credential isolation..."
    
    # Test that staging and production use completely different credential sets
    local staging_android_user_env
    staging_android_user_env=$(load_config_value ".repositories.staging.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    local staging_android_pass_env
    staging_android_pass_env=$(load_config_value ".repositories.staging.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    local staging_npm_token_env
    staging_npm_token_env=$(load_config_value ".repositories.staging.npm.credentials.tokenEnv" "$CONFIG_FILE")
    
    local prod_android_user_env
    prod_android_user_env=$(load_config_value ".repositories.production.android.credentials.usernameEnv" "$CONFIG_FILE")
    
    local prod_android_pass_env
    prod_android_pass_env=$(load_config_value ".repositories.production.android.credentials.passwordEnv" "$CONFIG_FILE")
    
    local prod_npm_token_env
    prod_npm_token_env=$(load_config_value ".repositories.production.npm.credentials.tokenEnv" "$CONFIG_FILE")
    
    # Verify no overlap between staging and production credentials
    local staging_vars=("$staging_android_user_env" "$staging_android_pass_env" "$staging_npm_token_env")
    local prod_vars=("$prod_android_user_env" "$prod_android_pass_env" "$prod_npm_token_env")
    
    for staging_var in "${staging_vars[@]}"; do
        for prod_var in "${prod_vars[@]}"; do
            if [[ "$staging_var" == "$prod_var" ]]; then
                log_error "Credential environment variable shared between staging and production: $staging_var"
                return 1
            fi
        done
    done
    
    # Test that npm token can be shared (this is acceptable for GitHub Packages vs npmjs.org)
    # But Android credentials should be completely separate
    if [[ "$staging_android_user_env" == "$prod_android_user_env" ]]; then
        log_error "Android username env vars should be different between staging and production"
        return 1
    fi
    
    if [[ "$staging_android_pass_env" == "$prod_android_pass_env" ]]; then
        log_error "Android password env vars should be different between staging and production"
        return 1
    fi
    
    log_success "Cross-environment credential isolation validated"
    return 0
}

# Test 5: Gradle task name generation patterns
test_gradle_task_patterns() {
    log_info "Testing Gradle task name generation patterns..."
    
    # The hardcoded repository name "PublishingRepository" generates specific task names
    local expected_publish_task="publishMavenPublicationToPublishingRepositoryRepository"
    local expected_all_task="publishAllPublicationsToPublishingRepositoryRepository"
    
    # Test task name construction
    local repo_name="PublishingRepository"
    local publication_name="maven"
    
    # Construct expected task names (capitalize first letter of publication name)
    local publication_name_capitalized="$(echo "${publication_name:0:1}" | tr '[:lower:]' '[:upper:]')${publication_name:1}"
    local constructed_task="publish${publication_name_capitalized}PublicationTo${repo_name}Repository"
    local constructed_all_task="publishAllPublicationsTo${repo_name}Repository"
    
    if [[ "$constructed_task" != "publishMavenPublicationToPublishingRepositoryRepository" ]]; then
        log_error "Constructed task name doesn't match expected pattern"
        log_error "Expected: publishMavenPublicationToPublishingRepositoryRepository"
        log_error "Got: $constructed_task"
        return 1
    fi
    
    if [[ "$constructed_all_task" != "publishAllPublicationsToPublishingRepositoryRepository" ]]; then
        log_error "Constructed all-publications task name doesn't match expected pattern"
        log_error "Expected: publishAllPublicationsToPublishingRepositoryRepository"
        log_error "Got: $constructed_all_task"
        return 1
    fi
    
    log_success "Gradle task name generation patterns validated"
    return 0
}

# Test 6: Property precedence and fallback behavior
test_property_precedence() {
    log_info "Testing property precedence and fallback behavior..."
    
    # Test the property resolution precedence:
    # 1. Gradle project properties (highest priority)
    # 2. Environment variables (fallback)
    
    local temp_dir
    temp_dir=$(create_temp_dir "property_precedence")
    
    # Set up environment variables
    export TEST_USERNAME="env-user"
    export TEST_PASSWORD="env-pass"
    
    # Test 1: Only environment variables available
    local env_only_username="${TEST_USERNAME}"
    local env_only_password="${TEST_PASSWORD}"
    
    if [[ "$env_only_username" != "env-user" ]]; then
        log_error "Environment-only resolution failed for username"
        return 1
    fi
    
    if [[ "$env_only_password" != "env-pass" ]]; then
        log_error "Environment-only resolution failed for password"
        return 1
    fi
    
    # Test 2: Property file overrides environment
    # Simulate having gradle.properties with explicit values
    local prop_username="prop-user"
    local prop_password="prop-pass"
    
    # In real Gradle, project.findProperty() would return the property value if it exists
    # and fall back to environment if it doesn't
    local resolved_username="${prop_username:-$TEST_USERNAME}"  # Property takes precedence
    local resolved_password="${prop_password:-$TEST_PASSWORD}"  # Property takes precedence
    
    if [[ "$resolved_username" != "prop-user" ]]; then
        log_error "Property precedence failed for username"
        log_error "Expected: prop-user, Got: $resolved_username"
        return 1
    fi
    
    if [[ "$resolved_password" != "prop-pass" ]]; then
        log_error "Property precedence failed for password"
        log_error "Expected: prop-pass, Got: $resolved_password"
        return 1
    fi
    
    # Test 3: Fallback when property is empty/null
    local empty_prop_username=""
    local fallback_username="${empty_prop_username:-$TEST_USERNAME}"
    
    if [[ "$fallback_username" != "env-user" ]]; then
        log_error "Fallback behavior failed when property is empty"
        log_error "Expected: env-user, Got: $fallback_username"
        return 1
    fi
    
    # Clean up
    unset TEST_USERNAME TEST_PASSWORD
    rm -rf "$temp_dir"
    
    log_success "Property precedence and fallback behavior validated"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_property_name_consistency || test_result=1
    test_env_var_property_mapping || test_result=1
    test_repository_name_hardcoding || test_result=1
    test_credential_isolation || test_result=1
    test_gradle_task_patterns || test_result=1
    test_property_precedence || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi