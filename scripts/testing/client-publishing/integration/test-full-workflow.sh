#!/bin/bash
# Test complete end-to-end workflow simulation without actual publishing
set -euo pipefail

# Source common functions and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test metadata
TEST_NAME="Complete End-to-End Workflow Simulation"
TEST_CATEGORY="integration"

# Initialize test environment
if ! init_test_environment; then
    exit 1
fi

log_test_start "${TEST_NAME}"

# Define workflow files for testing
declare -a WORKFLOW_FILES=(
    "${WORKFLOWS_DIR}/client-publish.yml"
    "${WORKFLOWS_DIR}/publish-android.yml"
    "${WORKFLOWS_DIR}/publish-typescript.yml"
)

# Test 1: Complete staging workflow simulation
test_staging_workflow_simulation() {
    log_info "Testing complete staging workflow simulation..."
    
    # Simulate staging publish workflow with test inputs
    local test_inputs=(
        "publish-type=staging"
        "client-version=1.0.0-pr.123.456"
        "workflow-identifier=123"
        "npm-scope=@vmenon25"
    )
    
    # Setup staging environment
    setup_test_environment_vars "staging_complete"
    
    # Test 1a: Input validation simulation
    local publish_type="staging"
    local client_version="1.0.0-pr.123.456"
    local workflow_identifier="123"
    local npm_scope="@vmenon25"
    
    # Validate inputs match expected patterns
    if [[ ! "$publish_type" =~ ^(staging|production)$ ]]; then
        log_error "Invalid publish-type for staging workflow: $publish_type"
        cleanup_mock_env
        return 1
    fi
    
    if ! validate_version_format "$client_version"; then
        log_error "Invalid client version format for staging workflow: $client_version"
        cleanup_mock_env
        return 1
    fi
    
    if [[ -z "$workflow_identifier" ]]; then
        log_error "Workflow identifier required for staging publishes"
        cleanup_mock_env
        return 1
    fi
    
    # Test 1b: Configuration loading simulation
    local staging_android_url
    staging_android_url=$(yq eval '.repositories.staging.android.url' "$CONFIG_FILE")
    
    local staging_npm_registry
    staging_npm_registry=$(yq eval '.repositories.staging.npm.registry' "$CONFIG_FILE")
    
    if [[ ! "$staging_android_url" =~ github\.com ]]; then
        log_error "Staging workflow should use GitHub Packages for Android"
        cleanup_mock_env
        return 1
    fi
    
    if [[ "$staging_npm_registry" != "https://npm.pkg.github.com" ]]; then
        log_error "Staging workflow should use GitHub Packages for npm"
        cleanup_mock_env
        return 1
    fi
    
    # Test 1c: Package name construction simulation
    local base_android_artifact
    base_android_artifact=$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")
    
    local base_npm_package
    base_npm_package=$(yq eval '.packages.typescript.basePackageName' "$CONFIG_FILE")
    
    local staging_android_suffix
    staging_android_suffix=$(yq eval '.naming.staging.androidSuffix' "$CONFIG_FILE")
    
    local staging_npm_suffix
    staging_npm_suffix=$(yq eval '.naming.staging.npmSuffix' "$CONFIG_FILE")
    
    local full_android_artifact="${base_android_artifact}${staging_android_suffix}"
    local full_npm_package="${base_npm_package}${staging_npm_suffix}"
    
    if [[ ! "$full_android_artifact" =~ -staging$ ]]; then
        log_error "Staging Android package should have staging suffix"
        cleanup_mock_env
        return 1
    fi
    
    if [[ ! "$full_npm_package" =~ -staging$ ]]; then
        log_error "Staging npm package should have staging suffix"
        cleanup_mock_env
        return 1
    fi
    
    # Test 1d: Environment variable availability
    local required_staging_vars=("ANDROID_PUBLISH_USER" "ANDROID_PUBLISH_TOKEN" "NPM_PUBLISH_TOKEN")
    
    for var in "${required_staging_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required staging environment variable not available: $var"
            cleanup_mock_env
            return 1
        fi
    done
    
    # Test 1e: Template generation simulation
    local temp_dir
    temp_dir=$(create_temp_dir "staging_workflow")
    
    local android_group_id
    android_group_id=$(yq eval '.packages.android.groupId' "$CONFIG_FILE")
    
    local android_gradle_file="$temp_dir/build.gradle.kts"
    
    generate_android_template \
        "$android_group_id" \
        "$full_android_artifact" \
        "$client_version" \
        "$staging_android_url" \
        "$android_gradle_file"
    
    # Verify template contains staging-specific values
    if ! grep -q "$full_android_artifact" "$android_gradle_file"; then
        log_error "Android template doesn't contain staging artifact name"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    if ! grep -q "$staging_android_url" "$android_gradle_file"; then
        log_error "Android template doesn't contain staging repository URL"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    # TypeScript package.json simulation
    local npm_package_file="$temp_dir/package.json"
    
    generate_template_with_substitutions "typescript" "$npm_package_file" \
        "NPM_PACKAGE_NAME_PLACEHOLDER=${npm_scope}/${full_npm_package}" \
        "VERSION_PLACEHOLDER=${client_version}" \
        "REGISTRY_URL_PLACEHOLDER=${staging_npm_registry}"
    
    # Verify TypeScript template contains staging-specific values
    if ! grep -q "${npm_scope}/${full_npm_package}" "$npm_package_file"; then
        log_error "TypeScript template doesn't contain staging package name"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    if ! grep -q "$staging_npm_registry" "$npm_package_file"; then
        log_error "TypeScript template doesn't contain staging registry"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    rm -rf "$temp_dir"
    cleanup_mock_env
    log_success "Staging workflow simulation completed successfully"
    return 0
}

# Test 2: Complete production workflow simulation
test_production_workflow_simulation() {
    log_info "Testing complete production workflow simulation..."
    
    # Simulate production publish workflow with test inputs
    local test_inputs=(
        "publish-type=production"
        "client-version=1.2.3"
        "workflow-identifier="
        "npm-scope=@vmenon25"
    )
    
    # Setup production environment
    setup_test_environment_vars "production_complete"
    
    # Test 2a: Input validation simulation
    local publish_type="production"
    local client_version="1.2.3"
    local workflow_identifier=""
    local npm_scope="@vmenon25"
    
    # Validate inputs
    if [[ ! "$publish_type" =~ ^(staging|production)$ ]]; then
        log_error "Invalid publish-type for production workflow: $publish_type"
        cleanup_mock_env
        return 1
    fi
    
    if ! validate_version_format "$client_version"; then
        log_error "Invalid client version format for production workflow: $client_version"
        cleanup_mock_env
        return 1
    fi
    
    # Production workflows don't require workflow-identifier
    if [[ "$publish_type" == "production" && -n "$workflow_identifier" ]]; then
        log_warning "Production workflows typically don't use workflow-identifier"
    fi
    
    # Test 2b: Configuration loading simulation
    local prod_android_url
    prod_android_url=$(yq eval '.repositories.production.android.url' "$CONFIG_FILE")
    
    local prod_npm_registry
    prod_npm_registry=$(yq eval '.repositories.production.npm.registry' "$CONFIG_FILE")
    
    if [[ ! "$prod_android_url" =~ sonatype\.com ]]; then
        log_error "Production workflow should use Maven Central for Android"
        cleanup_mock_env
        return 1
    fi
    
    if [[ "$prod_npm_registry" != "https://registry.npmjs.org" ]]; then
        log_error "Production workflow should use npmjs.org for npm"
        cleanup_mock_env
        return 1
    fi
    
    # Test 2c: Package name construction simulation (no suffixes for production)
    local base_android_artifact
    base_android_artifact=$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")
    
    local base_npm_package
    base_npm_package=$(yq eval '.packages.typescript.basePackageName' "$CONFIG_FILE")
    
    local prod_android_suffix
    prod_android_suffix=$(yq eval '.naming.production.androidSuffix' "$CONFIG_FILE")
    
    local prod_npm_suffix
    prod_npm_suffix=$(yq eval '.naming.production.npmSuffix' "$CONFIG_FILE")
    
    local full_android_artifact="${base_android_artifact}${prod_android_suffix}"
    local full_npm_package="${base_npm_package}${prod_npm_suffix}"
    
    # Production should not have staging suffixes
    if [[ "$full_android_artifact" =~ -staging$ ]]; then
        log_error "Production Android package should not have staging suffix"
        cleanup_mock_env
        return 1
    fi
    
    if [[ "$full_npm_package" =~ -staging$ ]]; then
        log_error "Production npm package should not have staging suffix"
        cleanup_mock_env
        return 1
    fi
    
    # Test 2d: Environment variable availability
    local required_prod_vars=("CENTRAL_PORTAL_USERNAME" "CENTRAL_PORTAL_PASSWORD" "NPM_PUBLISH_TOKEN" "SIGNING_KEY" "SIGNING_PASSWORD")
    
    for var in "${required_prod_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required production environment variable not available: $var"
            cleanup_mock_env
            return 1
        fi
    done
    
    # Test 2e: Template generation simulation
    local temp_dir
    temp_dir=$(create_temp_dir "production_workflow")
    
    local android_group_id
    android_group_id=$(yq eval '.packages.android.groupId' "$CONFIG_FILE")
    
    local android_gradle_file="$temp_dir/build.gradle.kts"
    
    generate_android_template \
        "$android_group_id" \
        "$full_android_artifact" \
        "$client_version" \
        "$prod_android_url" \
        "$android_gradle_file"
    
    # Verify template contains production-specific values
    if ! grep -q "$full_android_artifact" "$android_gradle_file"; then
        log_error "Android template doesn't contain production artifact name"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    if ! grep -q "$prod_android_url" "$android_gradle_file"; then
        log_error "Android template doesn't contain production repository URL"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    # TypeScript package.json simulation
    local npm_package_file="$temp_dir/package.json"
    
    generate_template_with_substitutions "typescript" "$npm_package_file" \
        "NPM_PACKAGE_NAME_PLACEHOLDER=${npm_scope}/${full_npm_package}" \
        "VERSION_PLACEHOLDER=${client_version}" \
        "REGISTRY_URL_PLACEHOLDER=${prod_npm_registry}"
    
    # Verify TypeScript template contains production-specific values
    if ! grep -q "${npm_scope}/${full_npm_package}" "$npm_package_file"; then
        log_error "TypeScript template doesn't contain production package name"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    if ! grep -q "$prod_npm_registry" "$npm_package_file"; then
        log_error "TypeScript template doesn't contain production registry"
        rm -rf "$temp_dir"
        cleanup_mock_env
        return 1
    fi
    
    rm -rf "$temp_dir"
    cleanup_mock_env
    log_success "Production workflow simulation completed successfully"
    return 0
}

# Test 3: Workflow job dependency validation
test_workflow_job_dependencies() {
    log_info "Testing workflow job dependency validation..."
    
    # Test that job dependencies are correctly defined across workflows
    
    # Test 3a: Main orchestrator workflow dependencies
    local orchestrator_file="${WORKFLOWS_DIR}/client-publish.yml"
    
    # Check that jobs have proper needs dependencies
    local validate_inputs_job
    validate_inputs_job=$(yq eval '.jobs.validate-inputs' "$orchestrator_file")
    
    if [[ "$validate_inputs_job" == "null" ]]; then
        log_error "validate-inputs job not found in orchestrator workflow"
        return 1
    fi
    
    # Check setup-config job dependencies
    local setup_config_needs
    setup_config_needs=$(yq eval '.jobs.setup-config.needs' "$orchestrator_file")
    
    if [[ "$setup_config_needs" == "null" ]]; then
        log_warning "setup-config job has no dependencies - this may be intentional"
    fi
    
    # Check publish jobs depend on proper prerequisites
    local publish_typescript_needs
    publish_typescript_needs=$(yq eval '.jobs.publish-typescript.needs' "$orchestrator_file")
    
    local publish_android_needs
    publish_android_needs=$(yq eval '.jobs.publish-android.needs' "$orchestrator_file")
    
    # Both publish jobs should have dependencies
    if [[ "$publish_typescript_needs" == "null" ]]; then
        log_error "publish-typescript job should have job dependencies"
        return 1
    fi
    
    if [[ "$publish_android_needs" == "null" ]]; then
        log_error "publish-android job should have job dependencies"
        return 1
    fi
    
    # Test 3b: Callable workflow structure
    local android_workflow="${WORKFLOWS_DIR}/publish-android.yml"
    local typescript_workflow="${WORKFLOWS_DIR}/publish-typescript.yml"
    
    # Verify callable workflows have proper on.workflow_call definitions
    local android_workflow_call
    android_workflow_call=$(yq eval '.on.workflow_call' "$android_workflow")
    
    local typescript_workflow_call
    typescript_workflow_call=$(yq eval '.on.workflow_call' "$typescript_workflow")
    
    if [[ "$android_workflow_call" == "null" ]]; then
        log_error "Android workflow should have workflow_call trigger"
        return 1
    fi
    
    if [[ "$typescript_workflow_call" == "null" ]]; then
        log_error "TypeScript workflow should have workflow_call trigger"
        return 1
    fi
    
    log_success "Workflow job dependency validation completed"
    return 0
}

# Test 4: Input/output contract validation
test_input_output_contracts() {
    log_info "Testing input/output contract validation..."
    
    # Test that workflow inputs and outputs are properly defined and used
    
    # Test 4a: Orchestrator workflow inputs
    local orchestrator_inputs
    orchestrator_inputs=$(yq eval '.on.workflow_call.inputs | keys' "${WORKFLOWS_DIR}/client-publish.yml")
    
    local expected_inputs=("publish-type" "client-version" "workflow-identifier" "npm-scope")
    
    for expected_input in "${expected_inputs[@]}"; do
        if ! echo "$orchestrator_inputs" | grep -q "$expected_input"; then
            log_error "Orchestrator workflow missing expected input: $expected_input"
            return 1
        fi
    done
    
    # Test 4b: Orchestrator workflow outputs
    local orchestrator_outputs
    orchestrator_outputs=$(yq eval '.on.workflow_call.outputs | keys' "${WORKFLOWS_DIR}/client-publish.yml")
    
    local expected_outputs=("typescript-package-name" "android-package-name" "staging-published" "production-published")
    
    for expected_output in "${expected_outputs[@]}"; do
        if ! echo "$orchestrator_outputs" | grep -q "$expected_output"; then
            log_error "Orchestrator workflow missing expected output: $expected_output"
            return 1
        fi
    done
    
    # Test 4c: Callable workflow inputs
    local android_inputs
    android_inputs=$(yq eval '.on.workflow_call.inputs | keys' "${WORKFLOWS_DIR}/publish-android.yml")
    
    local typescript_inputs
    typescript_inputs=$(yq eval '.on.workflow_call.inputs | keys' "${WORKFLOWS_DIR}/publish-typescript.yml")
    
    # Both should accept similar input sets
    local required_callable_inputs=("client-version" "publish-type")
    
    for required_input in "${required_callable_inputs[@]}"; do
        if ! echo "$android_inputs" | grep -q "$required_input"; then
            log_error "Android workflow missing required input: $required_input"
            return 1
        fi
        
        if ! echo "$typescript_inputs" | grep -q "$required_input"; then
            log_error "TypeScript workflow missing required input: $required_input"
            return 1
        fi
    done
    
    log_success "Input/output contract validation completed"
    return 0
}

# Test 5: End-to-end configuration consistency
test_end_to_end_configuration_consistency() {
    log_info "Testing end-to-end configuration consistency..."
    
    # Test that configuration is consistently applied across the entire workflow
    
    # Test 5a: Environment variable consistency
    local staging_android_username_env
    staging_android_username_env=$(yq eval '.repositories.staging.android.credentials.usernameEnv' "$CONFIG_FILE")
    
    local staging_android_password_env
    staging_android_password_env=$(yq eval '.repositories.staging.android.credentials.passwordEnv' "$CONFIG_FILE")
    
    # Verify these environment variables are referenced in the Android workflow
    local android_workflow="${WORKFLOWS_DIR}/publish-android.yml"
    
    if ! grep -q "$staging_android_username_env" "$android_workflow"; then
        log_warning "Android workflow may not reference staging username environment variable: $staging_android_username_env"
    fi
    
    # Test 5b: Package naming consistency
    local base_android_group
    base_android_group=$(yq eval '.packages.android.groupId' "$CONFIG_FILE")
    
    local base_android_artifact
    base_android_artifact=$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")
    
    # These should be consistently used across all workflows
    if [[ -z "$base_android_group" || "$base_android_group" == "null" ]]; then
        log_error "Android group ID not properly defined in configuration"
        return 1
    fi
    
    if [[ -z "$base_android_artifact" || "$base_android_artifact" == "null" ]]; then
        log_error "Android base artifact ID not properly defined in configuration"
        return 1
    fi
    
    # Test 5c: URL consistency
    local staging_android_url
    staging_android_url=$(yq eval '.repositories.staging.android.url' "$CONFIG_FILE")
    
    local prod_android_url
    prod_android_url=$(yq eval '.repositories.production.android.url' "$CONFIG_FILE")
    
    # URLs should be valid and environment-appropriate
    if [[ ! "$staging_android_url" =~ ^https:// ]]; then
        log_error "Staging Android URL should use HTTPS"
        return 1
    fi
    
    if [[ ! "$prod_android_url" =~ ^https:// ]]; then
        log_error "Production Android URL should use HTTPS"
        return 1
    fi
    
    if [[ "$staging_android_url" == "$prod_android_url" ]]; then
        log_error "Staging and production Android URLs should be different"
        return 1
    fi
    
    log_success "End-to-end configuration consistency validated"
    return 0
}

# Main test execution
main() {
    local test_result=0
    
    test_staging_workflow_simulation || test_result=1
    test_production_workflow_simulation || test_result=1
    test_workflow_job_dependencies || test_result=1
    test_input_output_contracts || test_result=1
    test_end_to_end_configuration_consistency || test_result=1
    
    log_test_end "${TEST_NAME}" $test_result
    return $test_result
}

# Run tests if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
    exit $?
fi