#!/bin/bash
#
# GitHub Packages Staging Cleanup Script
#
# This script cleans up staging artifacts from GitHub Packages after main CI/CD completion.
# It targets ONLY staging packages and provides different cleanup strategies based on workflow outcome.
# Configuration is loaded from a central YAML file with environment variable override support.
#
# CLEANUP SCOPE - ONLY GitHub Packages:
# - GHCR (GitHub Container Registry): Staging Docker images
# - GitHub Packages npm: Staging packages (*-staging suffix)  
# - GitHub Packages Maven: Staging packages (*-staging suffix)
# - Does NOT touch external registries (Maven Central, DockerHub, npm registry)
#
# CLEANUP LOGIC:
# - On Successful Workflow: DELETE ALL staging packages (validation complete)
# - On Failed Workflow: Standard cleanup (keep last 5 versions for debugging)
# - Emergency Override: [preserve] keyword skips cleanup entirely
#
# USAGE:
#   ./cleanup-staging-packages.sh [success|failure] [repository_owner]
#
# ENVIRONMENT VARIABLES:
#   GH_TOKEN - GitHub token with packages:write permission (required)
#   GITHUB_REPOSITORY_OWNER - Repository owner (if not provided as argument)
#   PRESERVE_STAGING - Set to 'true' to skip all cleanup (emergency override)
#   CONFIG_FILE - Path to central configuration file (default: config/publishing-config.yml)
#
# CONFIGURATION OVERRIDES (optional - defaults loaded from central config):
#   ANDROID_GROUP_ID - Maven group ID for Android packages
#   ANDROID_BASE_ARTIFACT_ID - Base artifact ID for Android packages
#   TYPESCRIPT_SCOPE - npm scope for TypeScript packages
#   TYPESCRIPT_BASE_PACKAGE_NAME - Base package name for TypeScript packages
#   ANDROID_STAGING_SUFFIX - Suffix for Android staging packages
#   NPM_STAGING_SUFFIX - Suffix for npm staging packages
#   AUTHOR_ID - Author identifier for repository references
#   DOCKER_WEBAUTHN_IMAGE_NAME - WebAuthn server Docker image name
#   DOCKER_TEST_CREDENTIALS_IMAGE_NAME - Test credentials service Docker image name
#
# EXIT CODES:
#   0 - Success (cleanup completed or skipped)
#   1 - Error occurred during cleanup
#

set -euo pipefail

# Configuration
WORKFLOW_OUTCOME="${1:-success}"
REPOSITORY_OWNER="${2:-${GITHUB_REPOSITORY_OWNER:-}}"

# Central configuration file path
CONFIG_FILE="${CONFIG_FILE:-config/publishing-config.yml}"

# Load central configuration using yq
load_central_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log "❌ Error: Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    if ! command -v yq &> /dev/null; then
        log "❌ Error: yq is not installed (required for configuration loading)"
        exit 1
    fi
    
    log "📋 Loading central configuration from: $CONFIG_FILE"
    
    # Load configuration values with environment variable overrides
    ANDROID_GROUP_ID="${ANDROID_GROUP_ID:-$(yq eval '.packages.android.groupId' "$CONFIG_FILE")}"
    ANDROID_BASE_ARTIFACT_ID="${ANDROID_BASE_ARTIFACT_ID:-$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")}"
    
    TYPESCRIPT_SCOPE="${TYPESCRIPT_SCOPE:-$(yq eval '.packages.typescript.scope' "$CONFIG_FILE")}"
    TYPESCRIPT_BASE_PACKAGE_NAME="${TYPESCRIPT_BASE_PACKAGE_NAME:-$(yq eval '.packages.typescript.basePackageName' "$CONFIG_FILE")}"
    
    ANDROID_STAGING_SUFFIX="${ANDROID_STAGING_SUFFIX:-$(yq eval '.naming.staging.androidSuffix' "$CONFIG_FILE")}"
    NPM_STAGING_SUFFIX="${NPM_STAGING_SUFFIX:-$(yq eval '.naming.staging.npmSuffix' "$CONFIG_FILE")}"
    
    AUTHOR_ID="${AUTHOR_ID:-$(yq eval '.metadata.author.id' "$CONFIG_FILE")}"
    
    # Docker image names (just the image names, not full paths)
    DOCKER_WEBAUTHN_IMAGE_NAME="${DOCKER_WEBAUTHN_IMAGE_NAME:-webauthn-server}"
    DOCKER_TEST_CREDENTIALS_IMAGE_NAME="${DOCKER_TEST_CREDENTIALS_IMAGE_NAME:-webauthn-test-credentials-service}"
    
    # Construct full package names
    ANDROID_STAGING_PACKAGE="${ANDROID_GROUP_ID}.${ANDROID_BASE_ARTIFACT_ID}${ANDROID_STAGING_SUFFIX}"
    NPM_STAGING_PACKAGE_NAME="${TYPESCRIPT_BASE_PACKAGE_NAME}${NPM_STAGING_SUFFIX}"
    NPM_SCOPE_CLEAN="${TYPESCRIPT_SCOPE#@}"  # Remove @ prefix for scope
    
    # Validate required configuration
    validate_config
}

# Function to validate configuration values
validate_config() {
    local errors=0
    
    # Check for null or empty values from yq
    if [[ "$ANDROID_GROUP_ID" == "null" || -z "$ANDROID_GROUP_ID" ]]; then
        log "❌ Error: Android groupId not found in configuration"
        ((errors++))
    fi
    
    if [[ "$ANDROID_BASE_ARTIFACT_ID" == "null" || -z "$ANDROID_BASE_ARTIFACT_ID" ]]; then
        log "❌ Error: Android baseArtifactId not found in configuration"
        ((errors++))
    fi
    
    if [[ "$TYPESCRIPT_SCOPE" == "null" || -z "$TYPESCRIPT_SCOPE" ]]; then
        log "❌ Error: TypeScript scope not found in configuration"
        ((errors++))
    fi
    
    if [[ "$TYPESCRIPT_BASE_PACKAGE_NAME" == "null" || -z "$TYPESCRIPT_BASE_PACKAGE_NAME" ]]; then
        log "❌ Error: TypeScript basePackageName not found in configuration"
        ((errors++))
    fi
    
    if [[ "$AUTHOR_ID" == "null" || -z "$AUTHOR_ID" ]]; then
        log "❌ Error: Author ID not found in configuration"
        ((errors++))
    fi
    
    if [[ $errors -gt 0 ]]; then
        log "❌ Configuration validation failed with $errors errors"
        exit 1
    fi
    
    log "✅ Configuration validation complete:"
    log "  Android Group ID: $ANDROID_GROUP_ID"
    log "  Android Base Artifact ID: $ANDROID_BASE_ARTIFACT_ID"
    log "  Android Staging Suffix: $ANDROID_STAGING_SUFFIX"
    log "  TypeScript Scope: $TYPESCRIPT_SCOPE"
    log "  TypeScript Base Package: $TYPESCRIPT_BASE_PACKAGE_NAME"
    log "  npm Staging Suffix: $NPM_STAGING_SUFFIX"
    log "  Author ID: $AUTHOR_ID"
    log "  Docker WebAuthn Image: $DOCKER_WEBAUTHN_IMAGE_NAME"
    log "  Docker Test Credentials Image: $DOCKER_TEST_CREDENTIALS_IMAGE_NAME"
    log "  Constructed Android Staging Package: $ANDROID_STAGING_PACKAGE"
    log "  Constructed npm Staging Package: $NPM_STAGING_PACKAGE_NAME"
}

# Emergency override check
if [[ "${PRESERVE_STAGING:-false}" == "true" ]]; then
    echo "🚨 EMERGENCY OVERRIDE: PRESERVE_STAGING=true - Skipping all staging cleanup"
    echo "⚠️  All staging packages will be preserved for manual investigation"
    exit 0
fi

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Function to validate inputs
validate_inputs() {
    if [[ "$WORKFLOW_OUTCOME" != "success" && "$WORKFLOW_OUTCOME" != "failure" ]]; then
        log "❌ Error: Invalid workflow outcome: $WORKFLOW_OUTCOME"
        log "Usage: $0 [success|failure] [repository_owner]"
        exit 1
    fi
    
    if [[ -z "$REPOSITORY_OWNER" ]]; then
        if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
            REPOSITORY_OWNER="${GITHUB_REPOSITORY%%/*}"
        else
            log "❌ Error: Repository owner not specified"
            log "Usage: $0 [success|failure] [repository_owner]"
            log "Or set GITHUB_REPOSITORY_OWNER environment variable"
            exit 1
        fi
    fi
    
    log "✅ Validation complete:"
    log "  Workflow outcome: $WORKFLOW_OUTCOME"
    log "  Repository owner: $REPOSITORY_OWNER"
}

# Function to validate GitHub CLI and authentication
validate_github_cli() {
    log "🔍 Validating GitHub CLI setup..."
    
    if ! command -v gh &> /dev/null; then
        log "❌ Error: GitHub CLI (gh) is not installed"
        exit 1
    fi
    
    if ! gh auth status &> /dev/null; then
        log "❌ Error: GitHub CLI is not authenticated"
        exit 1
    fi
    
    if [[ -z "${GH_TOKEN:-}" ]]; then
        log "⚠️ Warning: GH_TOKEN environment variable not set"
        log "Using default gh authentication"
    fi
    
    log "✅ GitHub CLI authentication validated"
}

# Function to find the correct API endpoint for a package
find_package_endpoint() {
    local package_type="$1"
    local package_name="$2"
    
    local endpoints=(
        "/orgs/${REPOSITORY_OWNER}/packages/${package_type}/${package_name}"
        "/users/${REPOSITORY_OWNER}/packages/${package_type}/${package_name}"
        "/user/packages/${package_type}/${package_name}"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log "🔍 Testing endpoint: $endpoint"
        if gh api "${endpoint}/versions" >/dev/null 2>&1; then
            log "✅ Found package at: $endpoint"
            echo "$endpoint"
            return 0
        fi
    done
    
    log "❌ Package not found at any endpoint: $package_name"
    return 1
}

# Function to clean up staging Docker images from GHCR
cleanup_staging_docker() {
    log "🐳 Cleaning up staging Docker images from GHCR..."
    
    local packages=("$DOCKER_WEBAUTHN_IMAGE_NAME" "$DOCKER_TEST_CREDENTIALS_IMAGE_NAME")
    local total_deleted=0
    
    for package in "${packages[@]}"; do
        log "🔍 Processing Docker package: $package"
        
        # Find the correct API endpoint for this package
        local endpoint
        if ! endpoint=$(find_package_endpoint "container" "$package"); then
            log "⚠️ Skipping Docker package (not found): $package"
            continue
        fi
        
        # Get staging versions based on workflow outcome
        local versions_query
        if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
            # Delete ALL staging images on success (pr- tags and staging suffixes)
            versions_query='
            .[] | 
            select(
                (.metadata.container.tags[]? | test("^pr-[0-9]+")) or
                (.metadata.container.tags[]? | test("-staging$")) or
                (.metadata.container.tags[]? | test("^pr-"))
            ) | 
            .id'
            log "  Strategy: DELETE ALL staging images (workflow succeeded)"
        else
            # Keep last 5 staging versions on failure (for debugging)
            versions_query='
            [.[] | 
             select(
                (.metadata.container.tags[]? | test("^pr-[0-9]+")) or
                (.metadata.container.tags[]? | test("-staging$")) or
                (.metadata.container.tags[]? | test("^pr-"))
             )] |
            sort_by(.created_at) | reverse | .[5:] | .[].id'
            log "  Strategy: Keep last 5 staging versions (workflow failed)"
        fi
        
        # Debug: First show basic info about versions for this package
        local version_count
        version_count=$(gh api "${endpoint}/versions" --jq 'length' 2>/dev/null || echo "0")
        log "🔍 Total versions found for $package: $version_count"
        
        if [[ "$version_count" -gt 0 ]]; then
            log "🔍 Sample version details:"
            gh api "${endpoint}/versions" --jq '.[:3] | .[] | "  - ID: \(.id), Tags: \(.metadata.container.tags // [] | join(", ")), Created: \(.created_at)"' 2>/dev/null || log "  (Failed to get details)"
        fi
        
        local versions
        versions=$(gh api \
            --method GET \
            "${endpoint}/versions" \
            --jq "$versions_query" \
            2>/dev/null || echo "")
            
        # Count non-empty lines
        local staging_count=0
        if [[ -n "$versions" ]]; then
            staging_count=$(echo "$versions" | grep -c . || echo "0")
        fi
        
        log "🔍 Staging versions after filtering: $staging_count versions"
        if [[ "$staging_count" -eq 0 ]]; then
            log "ℹ️ No staging versions to clean up for $package"
            continue
        fi
        
        local package_deleted=0
        while IFS= read -r version_id; do
            if [[ -n "$version_id" ]]; then
                if gh api \
                    --method DELETE \
                    "${endpoint}/versions/$version_id" \
                    2>/dev/null; then
                    ((package_deleted++))
                    ((total_deleted++))
                    log "✅ Deleted Docker version: $version_id"
                else
                    log "⚠️ Failed to delete Docker version: $version_id"
                fi
            fi
        done <<< "$versions"
        
        log "📊 $package: deleted $package_deleted staging versions"
    done
    
    log "🐳 Docker staging cleanup complete: $total_deleted total versions deleted"
}

# Function to clean up staging npm packages
cleanup_staging_npm() {
    log "📦 Cleaning up staging npm packages..."
    
    local scope="$NPM_SCOPE_CLEAN"
    local base_package="$NPM_STAGING_PACKAGE_NAME"
    local scoped_package="${scope}%2F${base_package}"  # URL-encoded @scope/package
    local total_deleted=0
    
    # Try to find the npm package using different naming patterns
    local package_patterns=(
        "$scoped_package"        # URL-encoded scoped package
        "$base_package"          # Base package name
        "${scope}/${base_package}"  # Scoped package with slash
    )
    
    local endpoint
    for pattern in "${package_patterns[@]}"; do
        log "🔍 Trying npm package pattern: $pattern"
        if endpoint=$(find_package_endpoint "npm" "$pattern"); then
            log "📍 Found staging npm package: $pattern at $endpoint"
            break
        fi
    done
    
    if [[ -z "$endpoint" ]]; then
        log "ℹ️ No staging npm packages found"
        return 0
    fi
        
    # Debug: First show basic info about npm versions
    local version_count
    version_count=$(gh api "${endpoint}/versions" --jq 'length' 2>/dev/null || echo "0")
    log "🔍 Total npm versions found: $version_count"
    
    if [[ "$version_count" -gt 0 ]]; then
        log "🔍 Sample npm version details:"
        gh api "${endpoint}/versions" --jq '.[:3] | .[] | "  - ID: \(.id), Name: \(.name), Created: \(.created_at)"' 2>/dev/null || log "  (Failed to get details)"
    fi
    
    # Get versions based on workflow outcome - filter staging versions (contain -pr.)
    local versions_query
    if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
        # Delete ALL staging versions on success (versions containing -pr.)
        versions_query='.[] | select(.name | test("-pr\\.")) | .id'
        log "  Strategy: DELETE ALL staging versions (workflow succeeded)"
    else
        # Keep last 5 staging versions on failure
        versions_query='[.[] | select(.name | test("-pr\\."))] | sort_by(.created_at) | reverse | .[5:] | .[].id'
        log "  Strategy: Keep last 5 staging versions (workflow failed)"
    fi
    
    local versions
    versions=$(gh api \
        --paginate \
        "${endpoint}/versions" \
        --jq "$versions_query" \
        2>/dev/null || echo "")
        
    # Count non-empty lines
    local staging_count=0
    if [[ -n "$versions" ]]; then
        staging_count=$(echo "$versions" | grep -c . || echo "0")
    fi
    
    log "🔍 Staging npm versions after filtering: $staging_count versions"
    if [[ "$staging_count" -eq 0 ]]; then
        log "ℹ️ No staging npm versions to clean up"
        return 0
    fi
    
    while IFS= read -r version_id; do
        if [[ -n "$version_id" ]]; then
            if gh api \
                --method DELETE \
                "${endpoint}/versions/$version_id" \
                2>/dev/null; then
                ((total_deleted++))
                log "✅ Deleted npm version: $version_id"
            else
                log "⚠️ Failed to delete npm version: $version_id"
            fi
        fi
    done <<< "$versions"
    
    log "📦 npm staging cleanup complete: $total_deleted versions deleted"
}

# Function to clean up staging Maven packages
cleanup_staging_maven() {
    log "🏗️ Cleaning up staging Maven packages..."
    
    local package_name="$ANDROID_STAGING_PACKAGE"
    local total_deleted=0
    
    # Find the Maven package using dynamic endpoint detection
    local endpoint
    if ! endpoint=$(find_package_endpoint "maven" "$package_name"); then
        log "ℹ️ No staging Maven packages found"
        return 0
    fi
        
    # Debug: First show basic info about Maven versions
    local version_count
    version_count=$(gh api "${endpoint}/versions" --jq 'length' 2>/dev/null || echo "0")
    log "🔍 Total Maven versions found: $version_count"
    
    if [[ "$version_count" -gt 0 ]]; then
        log "🔍 Sample Maven version details:"
        gh api "${endpoint}/versions" --jq '.[:3] | .[] | "  - ID: \(.id), Name: \(.name), Created: \(.created_at)"' 2>/dev/null || log "  (Failed to get details)"
    fi
    
    # Get versions based on workflow outcome - filter staging versions (contain -pr.)
    local versions_query
    if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
        # Delete ALL staging versions on success (versions containing -pr.)
        versions_query='.[] | select(.name | test("-pr\\.")) | .id'
        log "  Strategy: DELETE ALL staging versions (workflow succeeded)"
    else
        # Keep last 5 staging versions on failure
        versions_query='[.[] | select(.name | test("-pr\\."))] | sort_by(.created_at) | reverse | .[5:] | .[].id'
        log "  Strategy: Keep last 5 staging versions (workflow failed)"
    fi
    
    local versions
    versions=$(gh api \
        --paginate \
        "${endpoint}/versions" \
        --jq "$versions_query" \
        2>/dev/null || echo "")
        
    # Count non-empty lines
    local staging_count=0
    if [[ -n "$versions" ]]; then
        staging_count=$(echo "$versions" | grep -c . || echo "0")
    fi
    
    log "🔍 Staging Maven versions after filtering: $staging_count versions"
    if [[ "$staging_count" -eq 0 ]]; then
        log "ℹ️ No staging Maven versions to clean up"
        return 0
    fi
    
    while IFS= read -r version_id; do
        if [[ -n "$version_id" ]]; then
            if gh api \
                --method DELETE \
                "${endpoint}/versions/$version_id" \
                2>/dev/null; then
                ((total_deleted++))
                log "✅ Deleted Maven version: $version_id"
            else
                log "⚠️ Failed to delete Maven version: $version_id"
            fi
        fi
    done <<< "$versions"
    
    log "🏗️ Maven staging cleanup complete: $total_deleted versions deleted"
}

# Main cleanup function
perform_staging_cleanup() {
    log "🧹 Starting GitHub Packages staging cleanup"
    log "📋 Cleanup scope: ONLY GitHub Packages staging artifacts"
    log "🎯 Workflow outcome: $WORKFLOW_OUTCOME"
    log "🏢 Repository owner: $REPOSITORY_OWNER"
    log ""
    
    case "$WORKFLOW_OUTCOME" in
        "success")
            log "✅ Workflow succeeded - performing COMPLETE staging cleanup"
            log "🗑️ Strategy: Delete ALL staging packages (validation complete)"
            ;;
        "failure")
            log "❌ Workflow failed - performing CONSERVATIVE staging cleanup"
            log "🔍 Strategy: Keep last 5 versions for debugging"
            ;;
    esac
    
    log ""
    
    # Perform cleanup for each package type
    cleanup_staging_docker
    log ""
    cleanup_staging_npm
    log ""
    cleanup_staging_maven
    
    log ""
    log "🎉 GitHub Packages staging cleanup completed"
}

# Check for emergency override in commit message
check_preserve_override() {
    # Check if latest commit message contains [preserve] keyword
    if git log -1 --pretty=%s 2>/dev/null | grep -i '\[preserve\]' >/dev/null; then
        log "🚨 EMERGENCY OVERRIDE: [preserve] keyword found in commit message"
        log "⚠️  Skipping all staging cleanup for manual investigation"
        exit 0
    fi
}

# Main execution
main() {
    log "🚀 GitHub Packages Staging Cleanup Script Starting"
    
    # Check for emergency override first
    check_preserve_override
    
    # Load central configuration
    load_central_config
    
    # Validate inputs and GitHub CLI
    validate_inputs
    validate_github_cli
    
    # Perform staging cleanup
    perform_staging_cleanup
    
    log "✅ Staging cleanup script completed successfully"
}

# Trap errors for better debugging
trap 'log "❌ Error occurred at line $LINENO"' ERR

# Run main function
main