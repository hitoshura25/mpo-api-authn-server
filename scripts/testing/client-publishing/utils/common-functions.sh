#!/bin/bash
# Common utility functions for client publishing testing suite
set -euo pipefail

# Color codes for output formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Test result tracking
TESTS_PASSED=${TESTS_PASSED:-0}
TESTS_FAILED=${TESTS_FAILED:-0}
TESTS_TOTAL=${TESTS_TOTAL:-0}

# Project root directory
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
readonly CONFIG_FILE="${PROJECT_ROOT}/config/publishing-config.yml"
readonly WORKFLOWS_DIR="${PROJECT_ROOT}/.github/workflows"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $*"
    fi
}

log_test_start() {
    local test_name="$1"
    echo -e "\n${CYAN}=== Testing: ${test_name} ===${NC}"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

log_test_end() {
    local test_name="$1"
    local result="$2"
    
    if [[ "$result" -eq 0 ]]; then
        log_success "✅ ${test_name} PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "❌ ${test_name} FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

log_test_summary() {
    echo -e "\n${WHITE}=== Test Summary ===${NC}"
    echo -e "Total tests: ${TESTS_TOTAL}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    
    if [[ "$TESTS_FAILED" -gt 0 ]]; then
        echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
        echo -e "\n${RED}❌ Some tests failed. See details above.${NC}"
        return 1
    else
        echo -e "${GREEN}Failed: ${TESTS_FAILED}${NC}"
        echo -e "\n${GREEN}✅ All tests passed successfully!${NC}"
        return 0
    fi
}

# File and directory utilities
check_file_exists() {
    local file_path="$1"
    local description="${2:-file}"
    
    if [[ ! -f "$file_path" ]]; then
        log_error "Required ${description} not found: ${file_path}"
        return 1
    fi
    
    log_debug "Found ${description}: ${file_path}"
    return 0
}

check_directory_exists() {
    local dir_path="$1"
    local description="${2:-directory}"
    
    if [[ ! -d "$dir_path" ]]; then
        log_error "Required ${description} not found: ${dir_path}"
        return 1
    fi
    
    log_debug "Found ${description}: ${dir_path}"
    return 0
}

create_temp_file() {
    local prefix="${1:-test}"
    local temp_file=$(mktemp "/tmp/${prefix}.XXXXXX")
    echo "$temp_file"
}

create_temp_dir() {
    local prefix="${1:-test}"
    local temp_dir=$(mktemp -d "/tmp/${prefix}.XXXXXX")
    echo "$temp_dir"
}

cleanup_temp_files() {
    local pattern="${1:-/tmp/test.*}"
    find /tmp -name "test.*" -type f -mtime +1 2>/dev/null | xargs rm -f || true
    find /tmp -name "test.*" -type d -mtime +1 2>/dev/null | xargs rm -rf || true
}

# Tool availability checks
check_tool_available() {
    local tool="$1"
    local description="${2:-$tool}"
    
    if ! command -v "$tool" &> /dev/null; then
        log_error "${description} is not available. Please install it first."
        case "$tool" in
            "yq")
                log_info "Install with: brew install yq"
                log_info "Or download from: https://github.com/mikefarah/yq"
                ;;
            "actionlint")
                log_info "Install with: brew install actionlint"
                log_info "Or download from: https://github.com/rhymond/actionlint"
                ;;
            "jq")
                log_info "Install with: brew install jq"
                ;;
            "gradle")
                log_info "Use project's Gradle wrapper: ./gradlew"
                ;;
        esac
        return 1
    fi
    
    log_debug "${description} is available"
    return 0
}

check_required_tools() {
    local tools=("$@")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! check_tool_available "$tool"; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    return 0
}

# Configuration utilities
load_config_value() {
    local yaml_path="$1"
    local config_file="${2:-$CONFIG_FILE}"
    
    if ! check_file_exists "$config_file" "configuration file"; then
        return 1
    fi
    
    local value
    value=$(yq eval "$yaml_path" "$config_file" 2>/dev/null || echo "null")
    
    if [[ "$value" == "null" ]]; then
        log_debug "Configuration path '${yaml_path}' not found or null"
        return 1
    fi
    
    echo "$value"
    return 0
}

validate_config_path() {
    local yaml_path="$1"
    local expected_type="${2:-string}"
    local config_file="${3:-$CONFIG_FILE}"
    
    local value
    value=$(load_config_value "$yaml_path" "$config_file")
    local result=$?
    
    if [[ $result -ne 0 ]]; then
        log_error "Configuration path '${yaml_path}' is missing or null"
        return 1
    fi
    
    case "$expected_type" in
        "string")
            if [[ -z "$value" ]]; then
                log_error "Configuration path '${yaml_path}' is empty"
                return 1
            fi
            ;;
        "string_or_empty")
            # Allow empty strings - just check that the value exists and is a string type
            local value_type
            value_type=$(yq eval "${yaml_path} | type" "$config_file")
            if [[ "$value_type" != "!!str" ]]; then
                log_error "Configuration path '${yaml_path}' is not a string type"
                return 1
            fi
            ;;
        "object")
            if ! yq eval "${yaml_path} | type" "$config_file" | grep -q "!!map"; then
                log_error "Configuration path '${yaml_path}' is not an object"
                return 1
            fi
            ;;
        "array")
            if ! yq eval "${yaml_path} | type" "$config_file" | grep -q "!!seq"; then
                log_error "Configuration path '${yaml_path}' is not an array"
                return 1
            fi
            ;;
    esac
    
    log_debug "Configuration path '${yaml_path}' is valid (${expected_type}): ${value}"
    return 0
}

# Environment simulation utilities
setup_mock_env() {
    local env_type="${1:-staging}"
    local workflow_id="${2:-123}"
    
    # Export mock environment variables that workflows would have
    export GITHUB_REPOSITORY="hitoshura25/mpo-api-authn-server"
    export GITHUB_ACTOR="test-user"
    export GITHUB_TOKEN="mock-token"
    export GITHUB_RUN_NUMBER="$workflow_id"
    
    case "$env_type" in
        "staging")
            export ANDROID_PUBLISH_USER="test-user"
            export ANDROID_PUBLISH_TOKEN="mock-token"
            export NPM_TOKEN="mock-npm-token"
            ;;
        "production")
            export CENTRAL_PORTAL_USERNAME="central-user"
            export CENTRAL_PORTAL_PASSWORD="central-pass"
            export NPM_TOKEN="prod-npm-token"
            export SIGNING_KEY="mock-signing-key"
            export SIGNING_PASSWORD="mock-signing-pass"
            ;;
    esac
    
    log_debug "Mock environment setup for ${env_type} with workflow ID ${workflow_id}"
}

cleanup_mock_env() {
    unset GITHUB_REPOSITORY GITHUB_ACTOR GITHUB_TOKEN GITHUB_RUN_NUMBER
    unset ANDROID_PUBLISH_USER ANDROID_PUBLISH_TOKEN NPM_TOKEN
    unset CENTRAL_PORTAL_USERNAME CENTRAL_PORTAL_PASSWORD
    unset SIGNING_KEY SIGNING_PASSWORD
    
    log_debug "Mock environment cleaned up"
}

# Version utilities
validate_version_format() {
    local version="$1"
    local version_regex='^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*)?$'
    
    if [[ "$version" =~ $version_regex ]]; then
        log_debug "Version format is valid: ${version}"
        return 0
    else
        log_error "Invalid version format: ${version}"
        log_error "Expected format: X.Y.Z or X.Y.Z-prerelease"
        return 1
    fi
}

generate_test_version() {
    local prefix="${1:-1.0}"
    local suffix="${2:-}"
    local build_number="${3:-123}"
    
    local version="${prefix}.${build_number}"
    if [[ -n "$suffix" ]]; then
        version="${version}-${suffix}"
    fi
    
    echo "$version"
}

# Workflow utilities
validate_workflow_syntax() {
    local workflow_file="$1"
    
    if ! check_file_exists "$workflow_file" "workflow file"; then
        return 1
    fi
    
    if ! check_tool_available "actionlint"; then
        log_warning "actionlint not available, skipping syntax validation"
        return 0
    fi
    
    local temp_output
    temp_output=$(create_temp_file "actionlint")
    
    if actionlint "$workflow_file" > "$temp_output" 2>&1; then
        log_debug "Workflow syntax is valid: $(basename "$workflow_file")"
        rm -f "$temp_output"
        return 0
    else
        log_error "Workflow syntax errors in $(basename "$workflow_file"):"
        cat "$temp_output" | while IFS= read -r line; do
            log_error "  $line"
        done
        rm -f "$temp_output"
        return 1
    fi
}

extract_workflow_inputs() {
    local workflow_file="$1"
    local temp_output
    temp_output=$(create_temp_file "workflow_inputs")
    
    yq eval '.on.workflow_call.inputs | keys' "$workflow_file" > "$temp_output" 2>/dev/null || echo "[]" > "$temp_output"
    cat "$temp_output"
    rm -f "$temp_output"
}

extract_workflow_outputs() {
    local workflow_file="$1"
    local temp_output
    temp_output=$(create_temp_file "workflow_outputs")
    
    yq eval '.on.workflow_call.outputs | keys' "$workflow_file" > "$temp_output" 2>/dev/null || echo "[]" > "$temp_output"
    cat "$temp_output"
    rm -f "$temp_output"
}

# Gradle utilities
simulate_gradle_command() {
    local gradle_command="$1"
    local project_dir="${2:-$PROJECT_ROOT}"
    local dry_run="${3:-true}"
    
    log_debug "Simulating Gradle command: ${gradle_command}"
    log_debug "Project directory: ${project_dir}"
    
    if [[ "$dry_run" == "true" ]]; then
        # Simulate the command without executing
        log_info "Would execute: ./gradlew ${gradle_command}"
        return 0
    else
        # Actually execute the command (use with caution)
        cd "$project_dir"
        ./gradlew $gradle_command --dry-run
    fi
}

generate_android_template() {
    local group_id="$1"
    local artifact_id="$2"
    local version="$3"
    local repo_url="$4"
    local output_file="$5"
    
    cat > "$output_file" << EOF
plugins {
    id 'java-library'
    id 'maven-publish'
    id 'signing'
}

group = '${group_id}'
version = '${version}'

publishing {
    publications {
        maven(MavenPublication) {
            groupId = '${group_id}'
            artifactId = '${artifact_id}'
            version = '${version}'
            
            from components.java
        }
    }
    
    repositories {
        maven {
            name = 'PublishingRepository'
            url = '${repo_url}'
            credentials {
                username = project.findProperty('PublishingRepositoryUsername') ?: System.getenv('ANDROID_PUBLISH_USER')
                password = project.findProperty('PublishingRepositoryPassword') ?: System.getenv('ANDROID_PUBLISH_TOKEN')
            }
        }
    }
}

signing {
    required { gradle.taskGraph.hasTask("publish") }
    sign publishing.publications.maven
}
EOF

    log_debug "Generated Android template: ${output_file}"
}

# Test assertion utilities
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-Assertion failed}"
    
    if [[ "$expected" == "$actual" ]]; then
        log_debug "Assertion passed: ${message}"
        return 0
    else
        log_error "${message}"
        log_error "  Expected: '${expected}'"
        log_error "  Actual:   '${actual}'"
        return 1
    fi
}

assert_not_empty() {
    local value="$1"
    local message="${2:-Value should not be empty}"
    
    if [[ -n "$value" ]]; then
        log_debug "Assertion passed: ${message}"
        return 0
    else
        log_error "${message}"
        log_error "  Value is empty or null"
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-String should contain substring}"
    
    if [[ "$haystack" == *"$needle"* ]]; then
        log_debug "Assertion passed: ${message}"
        return 0
    else
        log_error "${message}"
        log_error "  String: '${haystack}'"
        log_error "  Should contain: '${needle}'"
        return 1
    fi
}

assert_file_exists() {
    local file_path="$1"
    local message="${2:-File should exist}"
    
    if [[ -f "$file_path" ]]; then
        log_debug "Assertion passed: ${message}"
        return 0
    else
        log_error "${message}"
        log_error "  File not found: ${file_path}"
        return 1
    fi
}

# JSON/YAML utilities
validate_json() {
    local json_string="$1"
    local temp_file
    temp_file=$(create_temp_file "json_validation")
    
    echo "$json_string" > "$temp_file"
    
    if jq empty "$temp_file" 2>/dev/null; then
        log_debug "JSON is valid"
        rm -f "$temp_file"
        return 0
    else
        log_error "Invalid JSON format"
        rm -f "$temp_file"
        return 1
    fi
}

validate_yaml() {
    local yaml_file="$1"
    
    if yq eval '.' "$yaml_file" > /dev/null 2>&1; then
        log_debug "YAML is valid: $(basename "$yaml_file")"
        return 0
    else
        log_error "Invalid YAML format: $(basename "$yaml_file")"
        return 1
    fi
}

# Error handling utilities
handle_error() {
    local exit_code=$?
    local line_number="${1:-unknown}"
    local function_name="${2:-unknown}"
    
    if [[ $exit_code -ne 0 ]]; then
        log_error "Error occurred in function '${function_name}' at line ${line_number}"
        log_error "Exit code: ${exit_code}"
    fi
    
    return $exit_code
}

# Setup error handling
set_error_trap() {
    set -eE
    # Use simpler error trap that doesn't rely on FUNCNAME
    trap 'handle_error ${LINENO} ${0##*/}' ERR
}

# Initialization function
init_test_environment() {
    local required_tools=("yq" "jq")
    
    # Check if we're in the right directory
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found. Are you running from the project root?"
        log_error "Expected: ${CONFIG_FILE}"
        return 1
    fi
    
    # Check required tools
    if ! check_required_tools "${required_tools[@]}"; then
        return 1
    fi
    
    # Setup error handling (disabled for compatibility)
    # set_error_trap
    
    # Clean up old temp files
    cleanup_temp_files
    
    log_debug "Test environment initialized successfully"
    return 0
}

# Export functions for use in other scripts
export -f log_info log_success log_warning log_error log_debug
export -f log_test_start log_test_end log_test_summary
export -f check_file_exists check_directory_exists create_temp_file create_temp_dir cleanup_temp_files
export -f check_tool_available check_required_tools
export -f load_config_value validate_config_path
export -f setup_mock_env cleanup_mock_env
export -f validate_version_format generate_test_version
export -f validate_workflow_syntax extract_workflow_inputs extract_workflow_outputs
export -f simulate_gradle_command generate_android_template
export -f assert_equals assert_not_empty assert_contains assert_file_exists
export -f validate_json validate_yaml
export -f handle_error set_error_trap init_test_environment