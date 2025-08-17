#!/bin/bash
# Mock environment management for client publishing tests
set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common-functions.sh"

# Mock environment types
MOCK_ENV_STAGING="staging"
MOCK_ENV_PRODUCTION="production"
MOCK_ENV_MISSING_CREDS="missing_credentials"
MOCK_ENV_INVALID="invalid"

# Current mock environment tracking
CURRENT_MOCK_ENV=""

# Mock environment setup functions

setup_mock_staging_environment() {
    log_debug "Setting up mock staging environment"
    
    # GitHub Packages credentials for staging
    export GITHUB_REPOSITORY="hitoshura25/mpo-api-authn-server"
    export GITHUB_ACTOR="staging-test-user"
    export GITHUB_TOKEN="ghp_mock_staging_token_1234567890abcdef"
    export GITHUB_RUN_NUMBER="123"
    
    # Android staging credentials
    export ANDROID_PUBLISH_USER="staging-android-user"
    export ANDROID_PUBLISH_TOKEN="staging_android_token_abcdef123456"
    
    # npm staging credentials (can reuse GitHub token for GitHub Packages)
    export NPM_TOKEN="npm_staging_token_fedcba098765"
    
    CURRENT_MOCK_ENV="$MOCK_ENV_STAGING"
    log_debug "Mock staging environment setup complete"
}

setup_mock_production_environment() {
    log_debug "Setting up mock production environment"
    
    # GitHub context (still needed for some operations)
    export GITHUB_REPOSITORY="hitoshura25/mpo-api-authn-server"
    export GITHUB_ACTOR="production-test-user"
    export GITHUB_TOKEN="ghp_mock_prod_github_token_abcdef1234567890"
    export GITHUB_RUN_NUMBER="456"
    
    # Maven Central credentials for production Android
    export CENTRAL_PORTAL_USERNAME="central-portal-user"
    export CENTRAL_PORTAL_PASSWORD="central_portal_password_secure123"
    
    # npm production credentials (npmjs.org)
    export NPM_TOKEN="npm_prod_token_secure_abcdef123456789"
    
    # Code signing credentials for production
    export SIGNING_KEY="mock_signing_key_base64_encoded_content"
    export SIGNING_PASSWORD="signing_key_password_secure456"
    export SIGNING_KEY_ID="mock-signing-key-id"
    
    CURRENT_MOCK_ENV="$MOCK_ENV_PRODUCTION"
    log_debug "Mock production environment setup complete"
}

setup_mock_missing_credentials_environment() {
    log_debug "Setting up mock environment with missing credentials"
    
    # Only basic GitHub context, missing publishing credentials
    export GITHUB_REPOSITORY="hitoshura25/mpo-api-authn-server"
    export GITHUB_ACTOR="test-user-no-creds"
    export GITHUB_TOKEN="ghp_mock_basic_token_no_publish_access"
    export GITHUB_RUN_NUMBER="789"
    
    # Intentionally missing:
    # - ANDROID_PUBLISH_USER
    # - ANDROID_PUBLISH_TOKEN  
    # - NPM_TOKEN (for staging)
    # - CENTRAL_PORTAL_USERNAME (for production)
    # - CENTRAL_PORTAL_PASSWORD (for production)
    # - SIGNING_KEY (for production)
    # - SIGNING_PASSWORD (for production)
    
    CURRENT_MOCK_ENV="$MOCK_ENV_MISSING_CREDS"
    log_debug "Mock missing credentials environment setup complete"
}

setup_mock_invalid_environment() {
    log_debug "Setting up mock invalid environment"
    
    # Set invalid/malformed values that would cause failures
    export GITHUB_REPOSITORY=""  # Empty repository
    export GITHUB_ACTOR="invalid user with spaces"  # Invalid characters
    export GITHUB_TOKEN="invalid-token-format"  # Wrong token format
    export GITHUB_RUN_NUMBER="not-a-number"  # Non-numeric run number
    
    # Invalid credential formats
    export ANDROID_PUBLISH_USER=""  # Empty username
    export ANDROID_PUBLISH_TOKEN="token with spaces"  # Invalid token format
    export NPM_TOKEN="npm_token_with_invalid_chars@#$"  # Invalid characters
    
    CURRENT_MOCK_ENV="$MOCK_ENV_INVALID"
    log_debug "Mock invalid environment setup complete"
}

# Environment validation functions

validate_mock_staging_environment() {
    log_debug "Validating mock staging environment"
    
    local required_vars=(
        "GITHUB_REPOSITORY"
        "GITHUB_ACTOR" 
        "GITHUB_TOKEN"
        "ANDROID_PUBLISH_USER"
        "ANDROID_PUBLISH_TOKEN"
        "NPM_TOKEN"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required staging environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    # Validate staging-specific patterns
    if [[ ! "$ANDROID_PUBLISH_USER" =~ ^staging- ]]; then
        log_warning "Staging Android user should have 'staging-' prefix"
    fi
    
    log_debug "Mock staging environment validation passed"
    return 0
}

validate_mock_production_environment() {
    log_debug "Validating mock production environment"
    
    local required_vars=(
        "GITHUB_REPOSITORY"
        "CENTRAL_PORTAL_USERNAME"
        "CENTRAL_PORTAL_PASSWORD"
        "NPM_TOKEN"
        "SIGNING_KEY"
        "SIGNING_PASSWORD"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required production environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    # Validate production-specific patterns
    if [[ ! "$CENTRAL_PORTAL_USERNAME" =~ ^central ]]; then
        log_warning "Production central portal user should have 'central' prefix"
    fi
    
    log_debug "Mock production environment validation passed"
    return 0
}

# Environment cleanup functions

cleanup_mock_environment() {
    log_debug "Cleaning up mock environment: $CURRENT_MOCK_ENV"
    
    # GitHub context variables
    unset GITHUB_REPOSITORY GITHUB_ACTOR GITHUB_TOKEN GITHUB_RUN_NUMBER
    
    # Staging credentials
    unset ANDROID_PUBLISH_USER ANDROID_PUBLISH_TOKEN
    
    # Production credentials
    unset CENTRAL_PORTAL_USERNAME CENTRAL_PORTAL_PASSWORD
    unset SIGNING_KEY SIGNING_PASSWORD SIGNING_KEY_ID
    
    # npm credentials (used by both environments)
    unset NPM_TOKEN
    
    CURRENT_MOCK_ENV=""
    log_debug "Mock environment cleanup complete"
}

# High-level environment management

setup_mock_environment() {
    local env_type="${1:-}"
    
    if [[ -z "$env_type" ]]; then
        log_error "Environment type required (staging|production|missing_credentials|invalid)"
        return 1
    fi
    
    # Clean up any existing environment first
    cleanup_mock_environment
    
    case "$env_type" in
        "$MOCK_ENV_STAGING")
            setup_mock_staging_environment
            ;;
        "$MOCK_ENV_PRODUCTION")
            setup_mock_production_environment
            ;;
        "$MOCK_ENV_MISSING_CREDS")
            setup_mock_missing_credentials_environment
            ;;
        "$MOCK_ENV_INVALID")
            setup_mock_invalid_environment
            ;;
        *)
            log_error "Unknown environment type: $env_type"
            log_error "Available types: staging, production, missing_credentials, invalid"
            return 1
            ;;
    esac
    
    log_info "Mock environment setup: $env_type"
    return 0
}

validate_mock_environment() {
    local env_type="${1:-$CURRENT_MOCK_ENV}"
    
    if [[ -z "$env_type" ]]; then
        log_error "No environment type specified and no current environment"
        return 1
    fi
    
    case "$env_type" in
        "$MOCK_ENV_STAGING")
            validate_mock_staging_environment
            ;;
        "$MOCK_ENV_PRODUCTION")
            validate_mock_production_environment
            ;;
        "$MOCK_ENV_MISSING_CREDS")
            # For missing credentials environment, we expect validation to fail
            log_debug "Missing credentials environment - validation expected to find missing vars"
            return 0
            ;;
        "$MOCK_ENV_INVALID")
            # For invalid environment, we expect validation to fail
            log_debug "Invalid environment - validation expected to find issues"
            return 0
            ;;
        *)
            log_error "Unknown environment type for validation: $env_type"
            return 1
            ;;
    esac
}

# Environment inspection functions

get_current_mock_environment() {
    echo "$CURRENT_MOCK_ENV"
}

list_mock_environment_variables() {
    local env_type="${1:-$CURRENT_MOCK_ENV}"
    
    log_info "Mock environment variables for: $env_type"
    
    local github_vars=("GITHUB_REPOSITORY" "GITHUB_ACTOR" "GITHUB_TOKEN" "GITHUB_RUN_NUMBER")
    local staging_vars=("ANDROID_PUBLISH_USER" "ANDROID_PUBLISH_TOKEN")
    local production_vars=("CENTRAL_PORTAL_USERNAME" "CENTRAL_PORTAL_PASSWORD" "SIGNING_KEY" "SIGNING_PASSWORD")
    local common_vars=("NPM_TOKEN")
    
    echo "GitHub Context:"
    for var in "${github_vars[@]}"; do
        local value="${!var:-<not set>}"
        if [[ "$var" =~ TOKEN|PASSWORD|KEY ]]; then
            # Mask sensitive values
            value="${value:0:8}..."
        fi
        echo "  $var=$value"
    done
    
    if [[ "$env_type" == "$MOCK_ENV_STAGING" ]]; then
        echo "Staging Credentials:"
        for var in "${staging_vars[@]}"; do
            local value="${!var:-<not set>}"
            if [[ "$var" =~ TOKEN|PASSWORD ]]; then
                value="${value:0:8}..."
            fi
            echo "  $var=$value"
        done
    fi
    
    if [[ "$env_type" == "$MOCK_ENV_PRODUCTION" ]]; then
        echo "Production Credentials:"
        for var in "${production_vars[@]}"; do
            local value="${!var:-<not set>}"
            if [[ "$var" =~ TOKEN|PASSWORD|KEY ]]; then
                value="${value:0:8}..."
            fi
            echo "  $var=$value"
        done
    fi
    
    echo "Common Variables:"
    for var in "${common_vars[@]}"; do
        local value="${!var:-<not set>}"
        if [[ "$var" =~ TOKEN ]]; then
            value="${value:0:8}..."
        fi
        echo "  $var=$value"
    done
}

# Testing utility functions

test_environment_isolation() {
    log_info "Testing environment isolation between staging and production"
    
    # Test staging environment
    setup_mock_environment "$MOCK_ENV_STAGING"
    local staging_android_user="$ANDROID_PUBLISH_USER"
    local staging_android_token="$ANDROID_PUBLISH_TOKEN"
    
    # Switch to production environment
    setup_mock_environment "$MOCK_ENV_PRODUCTION"
    local prod_central_user="$CENTRAL_PORTAL_USERNAME"
    local prod_central_password="$CENTRAL_PORTAL_PASSWORD"
    
    # Verify no credential leakage
    if [[ -n "${ANDROID_PUBLISH_USER:-}" ]]; then
        log_error "Staging Android credentials leaked into production environment"
        cleanup_mock_environment
        return 1
    fi
    
    if [[ -z "${CENTRAL_PORTAL_USERNAME:-}" ]]; then
        log_error "Production credentials not properly set"
        cleanup_mock_environment
        return 1
    fi
    
    cleanup_mock_environment
    log_success "Environment isolation test passed"
    return 0
}

# Export functions for use in test scripts
export -f setup_mock_environment validate_mock_environment cleanup_mock_environment
export -f get_current_mock_environment list_mock_environment_variables
export -f test_environment_isolation

# If script is run directly, provide interactive environment management
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-help}" in
        "setup")
            setup_mock_environment "${2:-staging}"
            ;;
        "validate")
            validate_mock_environment "${2:-}"
            ;;
        "cleanup")
            cleanup_mock_environment
            ;;
        "list")
            list_mock_environment_variables "${2:-}"
            ;;
        "test-isolation")
            test_environment_isolation
            ;;
        "help"|*)
            echo "Mock Environment Management for Client Publishing Tests"
            echo ""
            echo "Usage: $0 <command> [arguments]"
            echo ""
            echo "Commands:"
            echo "  setup <env-type>     Setup mock environment (staging|production|missing_credentials|invalid)"
            echo "  validate [env-type]  Validate current or specified environment"
            echo "  cleanup              Clean up all mock environment variables"
            echo "  list [env-type]      List environment variables for current or specified environment"
            echo "  test-isolation       Test environment isolation between staging and production"
            echo "  help                 Show this help message"
            echo ""
            echo "Environment Types:"
            echo "  staging              Complete staging environment with GitHub Packages credentials"
            echo "  production           Complete production environment with Maven Central + npmjs.org"
            echo "  missing_credentials  Environment missing required credentials (for error testing)"
            echo "  invalid              Environment with invalid/malformed values"
            ;;
    esac
fi