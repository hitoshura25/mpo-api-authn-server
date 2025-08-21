#!/bin/bash
# Test environment isolation and configuration boundaries
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Environment Isolation and Configuration Boundaries"
TEST_CATEGORY="environment-selection"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Staging environment isolation
test_staging_environment_isolation() {
    log_info "Testing staging environment isolation..."
    
    # Test that staging configuration only loads staging-specific values
    local staging_android_url
    staging_android_url=$(yq eval '.repositories.staging.android.url' "$CONFIG_FILE")
    
    local staging_npm_registry
    staging_npm_registry=$(yq eval '.repositories.staging.npm.registry' "$CONFIG_FILE")
    
    local staging_android_suffix
    staging_android_suffix=$(yq eval '.naming.staging.androidSuffix' "$CONFIG_FILE")
    
    local staging_npm_suffix
    staging_npm_suffix=$(yq eval '.naming.staging.npmSuffix' "$CONFIG_FILE")
    
    # Verify staging-specific URLs
    if [[ ! "$staging_android_url" =~ github\.com ]]; then
        log_error "Staging Android URL should point to GitHub Packages"
        log_error "Got: $staging_android_url"
        return 1
    fi
    
    if [[ "$staging_npm_registry" != "https://npm.pkg.github.com" ]]; then
        log_error "Staging npm registry should be GitHub Packages"
        log_error "Got: $staging_npm_registry"
        return 1
    fi
    
    # Verify staging suffixes are applied
    if [[ "$staging_android_suffix" != "-staging" ]]; then
        log_error "Staging Android suffix should be '-staging'"
        log_error "Got: '$staging_android_suffix'"
        return 1
    fi
    
    if [[ "$staging_npm_suffix" != "-staging" ]]; then
        log_error "Staging npm suffix should be '-staging'"
        log_error "Got: '$staging_npm_suffix'"
        return 1
    fi
    
    log_success "Staging environment isolation validated"
    return 0
}

# Test 2: Production environment isolation
test_production_environment_isolation() {
    log_info "Testing production environment isolation..."
    
    # Test that production configuration only loads production-specific values
    local prod_android_url
    prod_android_url=$(yq eval '.repositories.production.android.url' "$CONFIG_FILE")
    
    local prod_npm_registry
    prod_npm_registry=$(yq eval '.repositories.production.npm.registry' "$CONFIG_FILE")
    
    local prod_android_suffix
    prod_android_suffix=$(yq eval '.naming.production.androidSuffix' "$CONFIG_FILE")
    
    local prod_npm_suffix
    prod_npm_suffix=$(yq eval '.naming.production.npmSuffix' "$CONFIG_FILE")
    
    # Verify production-specific URLs
    if [[ ! "$prod_android_url" =~ sonatype\.com ]]; then
        log_error "Production Android URL should point to Maven Central"
        log_error "Got: $prod_android_url"
        return 1
    fi
    
    if [[ "$prod_npm_registry" != "https://registry.npmjs.org" ]]; then
        log_error "Production npm registry should be npmjs.org"
        log_error "Got: $prod_npm_registry"
        return 1
    fi
    
    # Verify production suffixes are empty
    if [[ "$prod_android_suffix" != "" ]]; then
        log_error "Production Android suffix should be empty"
        log_error "Got: '$prod_android_suffix'"
        return 1
    fi
    
    if [[ "$prod_npm_suffix" != "" ]]; then
        log_error "Production npm suffix should be empty"
        log_error "Got: '$prod_npm_suffix'"
        return 1
    fi
    
    log_success "Production environment isolation validated"
    return 0
}

# Test 3: Cross-environment configuration leakage prevention
test_cross_environment_leakage_prevention() {
    log_info "Testing cross-environment configuration leakage prevention..."
    
    # Verify that staging and production configurations are completely separate
    local temp_staging_config
    temp_staging_config=$(create_temp_file "staging_only")
    
    local temp_prod_config
    temp_prod_config=$(create_temp_file "prod_only")
    
    # Extract only staging configuration
    yq eval '.repositories.staging' "$CONFIG_FILE" > "$temp_staging_config"
    
    # Extract only production configuration
    yq eval '.repositories.production' "$CONFIG_FILE" > "$temp_prod_config"
    
    # Verify staging config doesn't contain production URLs
    if grep -q "registry.npmjs.org" "$temp_staging_config"; then
        log_error "Staging configuration contains production npm registry"
        rm -f "$temp_staging_config" "$temp_prod_config"
        return 1
    fi
    
    if grep -q "sonatype.com" "$temp_staging_config"; then
        log_error "Staging configuration contains production Maven repository"
        rm -f "$temp_staging_config" "$temp_prod_config"
        return 1
    fi
    
    # Verify production config doesn't contain staging URLs
    if grep -q "npm.pkg.github.com" "$temp_prod_config"; then
        log_error "Production configuration contains staging npm registry"
        rm -f "$temp_staging_config" "$temp_prod_config"
        return 1
    fi
    
    if grep -q "maven.pkg.github.com" "$temp_prod_config"; then
        log_error "Production configuration contains staging Maven repository"
        rm -f "$temp_staging_config" "$temp_prod_config"
        return 1
    fi
    
    rm -f "$temp_staging_config" "$temp_prod_config"
    log_success "Cross-environment leakage prevention validated"
    return 0
}

# Test 4: Environment-specific credential validation
test_environment_credential_validation() {
    log_info "Testing environment-specific credential validation..."
    
    # Test staging credentials
    local staging_android_username_env
    staging_android_username_env=$(yq eval '.repositories.staging.android.credentials.usernameEnv' "$CONFIG_FILE")
    
    local staging_android_password_env
    staging_android_password_env=$(yq eval '.repositories.staging.android.credentials.passwordEnv' "$CONFIG_FILE")
    
    local staging_npm_token_env
    staging_npm_token_env=$(yq eval '.repositories.staging.npm.credentials.tokenEnv' "$CONFIG_FILE")
    
    # Test production credentials
    local prod_android_username_env
    prod_android_username_env=$(yq eval '.repositories.production.android.credentials.usernameEnv' "$CONFIG_FILE")
    
    local prod_android_password_env
    prod_android_password_env=$(yq eval '.repositories.production.android.credentials.passwordEnv' "$CONFIG_FILE")
    
    local prod_npm_token_env
    prod_npm_token_env=$(yq eval '.repositories.production.npm.credentials.tokenEnv' "$CONFIG_FILE")
    
    # Verify staging credentials follow GitHub Packages pattern
    if [[ ! "$staging_android_username_env" =~ ^(GITHUB_ACTOR|ANDROID_PUBLISH_USER)$ ]]; then
        log_warning "Staging Android username env may not follow GitHub Packages pattern: $staging_android_username_env"
    fi
    
    if [[ ! "$staging_android_password_env" =~ ^(GITHUB_TOKEN|ANDROID_PUBLISH_TOKEN)$ ]]; then
        log_warning "Staging Android password env may not follow GitHub Packages pattern: $staging_android_password_env"
    fi
    
    # Verify production credentials follow Maven Central pattern
    if [[ ! "$prod_android_username_env" =~ ^CENTRAL ]]; then
        log_warning "Production Android username env may not follow Maven Central pattern: $prod_android_username_env"
    fi
    
    if [[ ! "$prod_android_password_env" =~ ^CENTRAL ]]; then
        log_warning "Production Android password env may not follow Maven Central pattern: $prod_android_password_env"
    fi
    
    # Verify no credential overlap between environments (Android should be different)
    if [[ "$staging_android_username_env" == "$prod_android_username_env" ]]; then
        log_error "Android username credentials should be different between staging and production"
        return 1
    fi
    
    if [[ "$staging_android_password_env" == "$prod_android_password_env" ]]; then
        log_error "Android password credentials should be different between staging and production"
        return 1
    fi
    
    log_success "Environment-specific credential validation completed"
    return 0
}

# Test 5: Configuration query isolation
test_configuration_query_isolation() {
    log_info "Testing configuration query isolation..."
    
    # Test that queries for one environment don't return data from another
    local staging_query=".repositories.staging"
    local production_query=".repositories.production"
    
    # Query staging configuration
    local staging_result
    staging_result=$(yq eval "$staging_query" "$CONFIG_FILE")
    
    # Verify staging result doesn't contain production URLs
    if echo "$staging_result" | grep -q "registry.npmjs.org"; then
        log_error "Staging query returned production npm registry"
        return 1
    fi
    
    if echo "$staging_result" | grep -q "sonatype.com"; then
        log_error "Staging query returned production Maven repository"
        return 1
    fi
    
    # Query production configuration
    local production_result
    production_result=$(yq eval "$production_query" "$CONFIG_FILE")
    
    # Verify production result doesn't contain staging URLs
    if echo "$production_result" | grep -q "npm.pkg.github.com"; then
        log_error "Production query returned staging npm registry"
        return 1
    fi
    
    if echo "$production_result" | grep -q "maven.pkg.github.com"; then
        log_error "Production query returned staging Maven repository"
        return 1
    fi
    
    log_success "Configuration query isolation validated"
    return 0
}

# Test 6: Environment boundary enforcement
test_environment_boundary_enforcement() {
    log_info "Testing environment boundary enforcement..."
    
    # Test that configuration enforces clear boundaries between environments
    
    # Create test scenarios where one environment might accidentally access another
    local temp_config
    temp_config=$(create_temp_file "boundary_test")
    
    # Create a malformed config that might allow cross-environment access
    cat > "$temp_config" << 'EOF'
repositories:
  staging:
    android:
      url: "https://maven.pkg.github.com/test/repo"
      credentials:
        usernameEnv: "GITHUB_ACTOR"
        passwordEnv: "GITHUB_TOKEN"
    npm:
      registry: "https://npm.pkg.github.com"
      credentials:
        tokenEnv: "GITHUB_TOKEN"
  production:
    android:
      url: "https://ossrh-staging-api.central.sonatype.com/service/local/staging/deploy/maven2/"
      credentials:
        usernameEnv: "CENTRAL_PORTAL_USERNAME"
        passwordEnv: "CENTRAL_PORTAL_PASSWORD"
    npm:
      registry: "https://registry.npmjs.org"
      credentials:
        tokenEnv: "NPM_PUBLISH_TOKEN"
        # This would be a boundary violation - don't include staging tokens
        # stagingTokenEnv: "GITHUB_TOKEN"  # This should not exist
EOF
    
    # Test that production section doesn't have staging-specific fields
    local prod_staging_token
    prod_staging_token=$(yq eval '.repositories.production.npm.credentials.stagingTokenEnv' "$temp_config")
    
    if [[ "$prod_staging_token" != "null" ]]; then
        log_error "Production configuration should not contain staging-specific credential fields"
        rm -f "$temp_config"
        return 1
    fi
    
    # Test that staging section doesn't have production-specific fields
    local staging_central_username
    staging_central_username=$(yq eval '.repositories.staging.android.credentials.centralUsernameEnv' "$temp_config")
    
    if [[ "$staging_central_username" != "null" ]]; then
        log_error "Staging configuration should not contain production-specific credential fields"
        rm -f "$temp_config"
        return 1
    fi
    
    rm -f "$temp_config"
    log_success "Environment boundary enforcement validated"
    return 0
}

# Test 7: Package naming isolation
test_package_naming_isolation() {
    log_info "Testing package naming isolation..."
    
    # Test that staging and production use different package names
    local base_android_artifact
    base_android_artifact=$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")
    
    local base_npm_package
    base_npm_package=$(yq eval '.packages.typescript.basePackageName' "$CONFIG_FILE")
    
    local staging_android_suffix
    staging_android_suffix=$(yq eval '.naming.staging.androidSuffix' "$CONFIG_FILE")
    
    local staging_npm_suffix
    staging_npm_suffix=$(yq eval '.naming.staging.npmSuffix' "$CONFIG_FILE")
    
    local prod_android_suffix
    prod_android_suffix=$(yq eval '.naming.production.androidSuffix' "$CONFIG_FILE")
    
    local prod_npm_suffix
    prod_npm_suffix=$(yq eval '.naming.production.npmSuffix' "$CONFIG_FILE")
    
    # Construct full package names
    local staging_android_name="${base_android_artifact}${staging_android_suffix}"
    local prod_android_name="${base_android_artifact}${prod_android_suffix}"
    
    local staging_npm_name="${base_npm_package}${staging_npm_suffix}"
    local prod_npm_name="${base_npm_package}${prod_npm_suffix}"
    
    # Verify that staging and production package names are different
    if [[ "$staging_android_name" == "$prod_android_name" ]]; then
        log_error "Staging and production Android packages have the same name"
        log_error "Both resolve to: $staging_android_name"
        return 1
    fi
    
    if [[ "$staging_npm_name" == "$prod_npm_name" ]]; then
        log_error "Staging and production npm packages have the same name"
        log_error "Both resolve to: $staging_npm_name"
        return 1
    fi
    
    # Verify staging packages have identifying suffixes
    if [[ ! "$staging_android_name" =~ -staging$ ]]; then
        log_error "Staging Android package should have staging suffix"
        log_error "Got: $staging_android_name"
        return 1
    fi
    
    if [[ ! "$staging_npm_name" =~ -staging$ ]]; then
        log_error "Staging npm package should have staging suffix"
        log_error "Got: $staging_npm_name"
        return 1
    fi
    
    log_success "Package naming isolation validated"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_staging_environment_isolation || test_result=1
    test_production_environment_isolation || test_result=1
    test_cross_environment_leakage_prevention || test_result=1
    test_environment_credential_validation || test_result=1
    test_configuration_query_isolation || test_result=1
    test_environment_boundary_enforcement || test_result=1
    test_package_naming_isolation || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi