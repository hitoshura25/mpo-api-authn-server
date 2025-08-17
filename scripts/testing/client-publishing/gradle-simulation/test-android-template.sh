#!/bin/bash
# Test Android template generation and validation
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Android Template Generation and Validation"
TEST_CATEGORY="gradle-simulation"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Test 1: Generate Android template with staging configuration
test_android_template_staging() {
    log_info "Testing Android template generation for staging..."
    
    local temp_template
    temp_template=$(create_temp_file "android_staging_template")
    
    # Get staging configuration values
    local group_id
    group_id=$(load_config_value ".packages.android.groupId" "$CONFIG_FILE")
    
    local base_artifact_id
    base_artifact_id=$(load_config_value ".packages.android.baseArtifactId" "$CONFIG_FILE")
    
    local staging_suffix
    staging_suffix=$(yq eval ".naming.staging.androidSuffix" "$CONFIG_FILE")
    
    local staging_repo_url
    staging_repo_url=$(load_config_value ".repositories.staging.android.url" "$CONFIG_FILE")
    
    # Generate full artifact ID with suffix
    local artifact_id="${base_artifact_id}${staging_suffix}"
    local version="1.0.0-test"
    
    # Generate template
    generate_android_template "$group_id" "$artifact_id" "$version" "$staging_repo_url" "$temp_template"
    
    # Validate template content
    assert_file_exists "$temp_template" "Android staging template file"
    
    # Check that template contains expected values
    local template_content
    template_content=$(cat "$temp_template")
    
    assert_contains "$template_content" "$group_id" "Template should contain group ID"
    assert_contains "$template_content" "$artifact_id" "Template should contain artifact ID with suffix"
    assert_contains "$template_content" "$version" "Template should contain version"
    assert_contains "$template_content" "$staging_repo_url" "Template should contain staging repository URL"
    assert_contains "$template_content" "PublishingRepository" "Template should use hardcoded repository name"
    assert_contains "$template_content" "PublishingRepositoryUsername" "Template should use hardcoded username property"
    assert_contains "$template_content" "PublishingRepositoryPassword" "Template should use hardcoded password property"
    
    log_success "Android staging template generation successful"
    rm -f "$temp_template"
    return 0
}

# Test 2: Generate Android template with production configuration
test_android_template_production() {
    log_info "Testing Android template generation for production..."
    
    local temp_template
    temp_template=$(create_temp_file "android_production_template")
    
    # Get production configuration values
    local group_id
    group_id=$(load_config_value ".packages.android.groupId" "$CONFIG_FILE")
    
    local base_artifact_id
    base_artifact_id=$(load_config_value ".packages.android.baseArtifactId" "$CONFIG_FILE")
    
    local production_suffix
    production_suffix=$(yq eval ".naming.production.androidSuffix" "$CONFIG_FILE")
    
    local production_repo_url
    production_repo_url=$(load_config_value ".repositories.production.android.url" "$CONFIG_FILE")
    
    # Generate full artifact ID with suffix (should be empty for production)
    local artifact_id="${base_artifact_id}${production_suffix}"
    local version="1.2.3"
    
    # Generate template
    generate_android_template "$group_id" "$artifact_id" "$version" "$production_repo_url" "$temp_template"
    
    # Validate template content
    assert_file_exists "$temp_template" "Android production template file"
    
    # Check that template contains expected values
    local template_content
    template_content=$(cat "$temp_template")
    
    assert_contains "$template_content" "$group_id" "Template should contain group ID"
    assert_contains "$template_content" "$artifact_id" "Template should contain artifact ID"
    assert_contains "$template_content" "$version" "Template should contain version"
    assert_contains "$template_content" "$production_repo_url" "Template should contain production repository URL"
    
    # For production, artifact ID should be the base ID (no suffix)
    assert_equals "$artifact_id" "$base_artifact_id" "Production artifact ID should not have suffix"
    
    log_success "Android production template generation successful"
    rm -f "$temp_template"
    return 0
}

# Test 3: Test template substitution with various inputs
test_template_substitution() {
    log_info "Testing template substitution with various inputs..."
    
    local temp_template
    temp_template=$(create_temp_file "android_substitution_template")
    
    # Test with custom values
    local test_group_id="com.example.test"
    local test_artifact_id="test-client-library"
    local test_version="2.0.0-alpha"
    local test_repo_url="https://example.com/maven"
    
    generate_android_template "$test_group_id" "$test_artifact_id" "$test_version" "$test_repo_url" "$temp_template"
    
    # Validate all substitutions were made
    local template_content
    template_content=$(cat "$temp_template")
    
    # Should not contain any placeholders
    if echo "$template_content" | grep -q "GROUP_ID_PLACEHOLDER\|ARTIFACT_ID_PLACEHOLDER\|VERSION_PLACEHOLDER\|REPOSITORY_URL_PLACEHOLDER"; then
        log_error "Template still contains placeholders after substitution"
        rm -f "$temp_template"
        return 1
    fi
    
    # Should contain the actual values
    assert_contains "$template_content" "$test_group_id" "Template should contain test group ID"
    assert_contains "$template_content" "$test_artifact_id" "Template should contain test artifact ID"
    assert_contains "$template_content" "$test_version" "Template should contain test version"
    assert_contains "$template_content" "$test_repo_url" "Template should contain test repository URL"
    
    log_success "Template substitution works correctly"
    rm -f "$temp_template"
    return 0
}

# Test 4: Validate template Gradle syntax
test_template_gradle_syntax() {
    log_info "Testing template Gradle syntax validity..."
    
    local temp_template
    temp_template=$(create_temp_file "android_syntax_template")
    
    # Generate template with realistic values
    local group_id="io.github.test"
    local artifact_id="test-android-client"
    local version="1.0.0"
    local repo_url="https://maven.pkg.github.com/test/repo"
    
    generate_android_template "$group_id" "$artifact_id" "$version" "$repo_url" "$temp_template"
    
    # Basic syntax validation - check for common Gradle patterns
    local template_content
    template_content=$(cat "$temp_template")
    
    # Check for required Gradle blocks
    assert_contains "$template_content" "plugins {" "Template should have plugins block"
    assert_contains "$template_content" "publishing {" "Template should have publishing block"
    assert_contains "$template_content" "repositories {" "Template should have repositories block"
    assert_contains "$template_content" "signing {" "Template should have signing block"
    
    # Check for proper Gradle DSL syntax
    assert_contains "$template_content" "maven(MavenPublication)" "Template should define Maven publication"
    assert_contains "$template_content" "from components.java" "Template should publish Java components"
    
    # Check that quotes are properly handled
    if echo "$template_content" | grep -q "group = $group_id"; then
        log_error "Group ID should be quoted in template"
        rm -f "$temp_template"
        return 1
    fi
    
    assert_contains "$template_content" "group = \"$group_id\"" "Group ID should be quoted"
    assert_contains "$template_content" "version = \"$version\"" "Version should be quoted"
    
    log_success "Template Gradle syntax is valid"
    rm -f "$temp_template"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_android_template_staging || test_result=1
    test_android_template_production || test_result=1
    test_template_substitution || test_result=1
    test_template_gradle_syntax || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi