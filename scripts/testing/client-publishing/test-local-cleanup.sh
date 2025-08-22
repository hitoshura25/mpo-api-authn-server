#!/bin/bash
#
# Local Testing Version of GitHub Packages Staging Cleanup Script
#
# This script provides enhanced testing capabilities for debugging staging package cleanup
# issues locally. It imports all the latest logic from the production cleanup script while
# adding testing-specific features for better troubleshooting.
#
# TESTING FEATURES:
# - Enhanced debugging output with color coding
# - Local authentication validation
# - Better error analysis for troubleshooting
# - Testing mode indicators
# - Verbose logging for debugging
#
# USAGE:
#   ./test-local-cleanup.sh [success|failure] [PR_number] [repository_owner]
#
# EXAMPLES:
#   ./test-local-cleanup.sh success 47 hitoshura25
#   ./test-local-cleanup.sh failure 42
#   ./test-local-cleanup.sh success    # Uses defaults
#
# ENVIRONMENT VARIABLES:
#   GH_TOKEN - GitHub token with packages:write permission (required)
#   CONFIG_FILE - Path to central configuration file (default: config/publishing-config.yml)
#   DEBUG_MODE - Set to 'true' for extra verbose output
#
# TESTING MODES:
#   default - Full cleanup test with enhanced debugging
#   debug - Extra verbose output with detailed API responses
#
# EXIT CODES:
#   0 - Success (cleanup completed or skipped)
#   1 - Error occurred during cleanup
#

set -euo pipefail

# Parse arguments with defaults for local testing
WORKFLOW_OUTCOME="${1:-success}"
LOCAL_PR_NUMBER="${2:-47}"
REPOSITORY_OWNER="${3:-hitoshura25}"

# Set up local testing environment variables
export GITHUB_EVENT_NAME="pull_request"
export GITHUB_PR_NUMBER="$LOCAL_PR_NUMBER"
export GITHUB_REF_NAME="${LOCAL_PR_NUMBER}/merge"
export GITHUB_REPOSITORY="hitoshura25/mpo-api-authn-server"
export GITHUB_REPOSITORY_OWNER="$REPOSITORY_OWNER"

# Central configuration file path
CONFIG_FILE="${CONFIG_FILE:-config/publishing-config.yml}"

# Debug mode for extra verbose output
DEBUG_MODE="${DEBUG_MODE:-false}"

# Colors for enhanced testing output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced logging functions for testing
log() {
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC} - $*"
}

debug() {
    if [[ "$DEBUG_MODE" == "true" ]]; then
        echo -e "${PURPLE}$(date '+%Y-%m-%d %H:%M:%S') [DEBUG]${NC} - $*"
    fi
}

success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ✅ $*"
}

warning() {
    echo -e "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ⚠️ $*"
}

error() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ❌ $*"
}

info() {
    echo -e "${CYAN}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ℹ️ $*"
}

# Load central configuration using yq (same as production)
load_central_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    if ! command -v yq &> /dev/null; then
        error "yq is not installed (required for configuration loading)"
        exit 1
    fi
    
    info "Loading central configuration from: $CONFIG_FILE"
    
    # Load configuration values with environment variable overrides
    ANDROID_GROUP_ID="${ANDROID_GROUP_ID:-$(yq eval '.packages.android.groupId' "$CONFIG_FILE")}"
    ANDROID_BASE_ARTIFACT_ID="${ANDROID_BASE_ARTIFACT_ID:-$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")}"
    
    TYPESCRIPT_SCOPE="${TYPESCRIPT_SCOPE:-$(yq eval '.packages.typescript.scope.staging' "$CONFIG_FILE")}"
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

# Function to validate configuration values (same as production)
validate_config() {
    local errors=0
    
    # Check for null or empty values from yq
    if [[ "$ANDROID_GROUP_ID" == "null" || -z "$ANDROID_GROUP_ID" ]]; then
        error "Android groupId not found in configuration"
        ((errors++))
    fi
    
    if [[ "$ANDROID_BASE_ARTIFACT_ID" == "null" || -z "$ANDROID_BASE_ARTIFACT_ID" ]]; then
        error "Android baseArtifactId not found in configuration"
        ((errors++))
    fi
    
    if [[ "$TYPESCRIPT_SCOPE" == "null" || -z "$TYPESCRIPT_SCOPE" ]]; then
        error "TypeScript scope not found in configuration"
        ((errors++))
    fi
    
    if [[ "$TYPESCRIPT_BASE_PACKAGE_NAME" == "null" || -z "$TYPESCRIPT_BASE_PACKAGE_NAME" ]]; then
        error "TypeScript basePackageName not found in configuration"
        ((errors++))
    fi
    
    if [[ "$AUTHOR_ID" == "null" || -z "$AUTHOR_ID" ]]; then
        error "Author ID not found in configuration"
        ((errors++))
    fi
    
    if [[ $errors -gt 0 ]]; then
        error "Configuration validation failed with $errors errors"
        exit 1
    fi
    
    success "Configuration validation complete:"
    log "  Repository Owner: $REPOSITORY_OWNER"
    log "  GitHub Repository: ${GITHUB_REPOSITORY:-NOT_SET}"
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
    log "  npm Scope (clean): $NPM_SCOPE_CLEAN"
}

# Function to determine cleanup scope based on context (same as production)
determine_cleanup_scope() {
    local event_name="${GITHUB_EVENT_NAME:-}"
    local pr_number="${GITHUB_PR_NUMBER:-}"
    local ref_name="${GITHUB_REF_NAME:-}"
    
    info "Determining cleanup scope from context:"
    log "  Event Name: ${event_name:-'NOT_SET'}"
    log "  PR Number: ${pr_number:-'NOT_SET'}"
    log "  Ref Name: ${ref_name:-'NOT_SET'}"
    
    # Determine cleanup context
    if [[ "$event_name" == "pull_request" && -n "$pr_number" ]]; then
        # PR context - clean only current PR packages
        CLEANUP_CONTEXT="pr"
        CLEANUP_PR_NUMBER="$pr_number"
        success "Context: PR #${pr_number} - will target only pr-${pr_number} packages"
    elif [[ "$event_name" == "push" && "$ref_name" == "main" ]]; then
        # Main branch context - determine which PR packages to clean
        CLEANUP_CONTEXT="main"
        CLEANUP_PR_NUMBER=""
        
        # For main branch, we could look at recent merge commits to find the PR number
        # For now, we'll use a more conservative approach and clean recent staging packages
        local recent_pr_from_merge
        recent_pr_from_merge=$(git log -1 --pretty=%s | grep -oE '#[0-9]+' | head -1 | tr -d '#' || echo "")
        
        if [[ -n "$recent_pr_from_merge" ]]; then
            CLEANUP_PR_NUMBER="$recent_pr_from_merge"
            success "Context: Main branch (recent merge from PR #${recent_pr_from_merge}) - will target pr-${recent_pr_from_merge} packages"
        else
            warning "Context: Main branch (no recent PR detected) - will use broad staging pattern for safety"
        fi
    else
        # Unknown context - use broad staging pattern but log the issue
        CLEANUP_CONTEXT="unknown"
        CLEANUP_PR_NUMBER=""
        warning "Context: Unknown (event: ${event_name}, ref: ${ref_name}) - will use broad staging pattern"
    fi
    
    # Set global variables for use in cleanup functions
    export CLEANUP_CONTEXT
    export CLEANUP_PR_NUMBER
    
    info "Final cleanup scope:"
    log "  Context: $CLEANUP_CONTEXT"
    log "  PR Number: ${CLEANUP_PR_NUMBER:-'NONE'}"
}

# Function to validate inputs (enhanced for testing)
validate_inputs() {
    if [[ "$WORKFLOW_OUTCOME" != "success" && "$WORKFLOW_OUTCOME" != "failure" ]]; then
        error "Invalid workflow outcome: $WORKFLOW_OUTCOME"
        error "Usage: $0 [success|failure] [PR_number] [repository_owner]"
        exit 1
    fi
    
    if [[ -z "$REPOSITORY_OWNER" ]]; then
        if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
            REPOSITORY_OWNER="${GITHUB_REPOSITORY%%/*}"
        else
            error "Repository owner not specified"
            error "Usage: $0 [success|failure] [PR_number] [repository_owner]"
            exit 1
        fi
    fi
    
    success "Input validation complete:"
    log "  Workflow outcome: $WORKFLOW_OUTCOME"
    log "  Repository owner: $REPOSITORY_OWNER"
    log "  PR Number: $LOCAL_PR_NUMBER"
}

# Enhanced GitHub CLI validation for testing
validate_github_cli() {
    info "Validating GitHub CLI setup for local testing..."
    
    if ! command -v gh &> /dev/null; then
        error "GitHub CLI (gh) is not installed"
        exit 1
    fi
    
    # Get detailed auth status for debugging
    local auth_status
    auth_status=$(gh auth status 2>&1 || echo "Auth check failed")
    debug "GitHub CLI auth status: $auth_status"
    
    if ! gh auth status &> /dev/null; then
        error "GitHub CLI is not authenticated"
        error "Please run 'gh auth login' or set GH_TOKEN environment variable"
        exit 1
    fi
    
    if [[ -z "${GH_TOKEN:-}" ]]; then
        warning "GH_TOKEN environment variable not set"
        log "Using default gh authentication"
    else
        success "GH_TOKEN environment variable is set"
    fi
    
    # Test GitHub API access with packages scope
    info "Testing GitHub API access for packages..."
    local test_result
    if test_result=$(gh api /user 2>&1); then
        local username
        username=$(echo "$test_result" | jq -r '.login' 2>/dev/null || echo "unknown")
        success "GitHub API access confirmed for user: $username"
    else
        error "GitHub API test failed: $test_result"
        error "This may indicate insufficient token permissions"
        error "Required permissions: packages:write for GitHub Packages"
    fi
    
    success "GitHub CLI authentication validated"
}

# Function to URL-encode package names for API calls (same as production)
url_encode_package_name() {
    local package_name="$1"
    # URL encode forward slashes and other special characters that may appear in package names
    echo "$package_name" | sed 's|/|%2F|g' | sed 's| |%20|g'
}

# Enhanced package endpoint discovery with detailed testing output
find_package_endpoint() {
    local package_type="$1"
    local package_name="$2"
    
    debug "Starting endpoint discovery for $package_type package: $package_name"
    
    # URL-encode the package name for API calls
    local encoded_package_name
    encoded_package_name=$(url_encode_package_name "$package_name")
    debug "URL-encoded package name: $encoded_package_name"
    
    # Use the endpoint patterns that were verified to work in testing
    local endpoints=()
    case "$package_type" in
        "container")
            # Docker/container packages - use user-scoped endpoints (verified working)
            endpoints=(
                "/users/${REPOSITORY_OWNER}/packages/container/${encoded_package_name}"
                "/orgs/${REPOSITORY_OWNER}/packages/container/${encoded_package_name}"
                "/user/packages/container/${encoded_package_name}"
            )
            ;;
        "npm")
            # npm packages - use user packages endpoint (verified working)
            endpoints=(
                "/user/packages/npm/${encoded_package_name}"
                "/orgs/${REPOSITORY_OWNER}/packages/npm/${encoded_package_name}"
                "/users/${REPOSITORY_OWNER}/packages/npm/${encoded_package_name}"
            )
            ;;
        "maven")
            # Maven packages - use user packages endpoint (verified working)
            endpoints=(
                "/user/packages/maven/${encoded_package_name}"
                "/orgs/${REPOSITORY_OWNER}/packages/maven/${encoded_package_name}"
                "/users/${REPOSITORY_OWNER}/packages/maven/${encoded_package_name}"
            )
            ;;
        *)
            # Generic fallback for other package types
            endpoints=(
                "/user/packages/${package_type}/${encoded_package_name}"
                "/orgs/${REPOSITORY_OWNER}/packages/${package_type}/${encoded_package_name}"
                "/users/${REPOSITORY_OWNER}/packages/${package_type}/${encoded_package_name}"
            )
            ;;
    esac
    
    for endpoint in "${endpoints[@]}"; do
        debug "Testing endpoint: $endpoint"
        
        # Test endpoint with more robust error checking
        local api_test_result
        api_test_result=$(gh api "${endpoint}/versions" --silent 2>&1)
        local api_exit_code=$?
        
        if [[ $api_exit_code -eq 0 ]]; then
            success "Found package at: $endpoint" >&2
            
            # Verify the endpoint actually returns version data
            local version_count
            version_count=$(echo "$api_test_result" | jq 'length' 2>/dev/null || echo "0")
            debug "Endpoint verification: $version_count versions available"
            
            # Only return the clean endpoint path to stdout
            echo "$endpoint"
            return 0
        else
            debug "Endpoint failed: $endpoint (exit code: $api_exit_code)"
            if [[ "$api_test_result" =~ "404" ]]; then
                debug "   Package not found at this endpoint"
            elif [[ "$api_test_result" =~ "403" ]]; then
                debug "   Permission denied - check token permissions"
            else
                debug "   Error details: $(echo "$api_test_result" | head -c 100)..."
            fi
        fi
    done
    
    warning "Package not found at any endpoint: $package_name" >&2
    debug "Available endpoints tested:" >&2
    for endpoint in "${endpoints[@]}"; do
        debug "   - $endpoint/versions" >&2
    done
    return 1
}

# Enhanced Docker cleanup with detailed testing output
test_cleanup_staging_docker() {
    log "🐳 Testing staging Docker images cleanup from GHCR..."
    
    local packages=("$DOCKER_WEBAUTHN_IMAGE_NAME" "$DOCKER_TEST_CREDENTIALS_IMAGE_NAME")
    local total_deleted=0
    local total_found=0
    
    for package in "${packages[@]}"; do
        info "Processing Docker package: $package"
        
        # Container packages in GHCR may use different naming patterns
        # Try both simple name and repository-scoped name
        local package_variants=(
            "$package"                                                    # Simple name: webauthn-server
            "${REPOSITORY_OWNER}/${package}"                             # Owner-scoped: hitoshura25/webauthn-server  
            "mpo-api-authn-server/${package}"                           # Repo-scoped: mpo-api-authn-server/webauthn-server
            "${REPOSITORY_OWNER}/mpo-api-authn-server/${package}"       # Full path: hitoshura25/mpo-api-authn-server/webauthn-server
        )
        
        local endpoint=""
        local found_package=""
        
        # Try each package name variant using the improved endpoint discovery
        for package_variant in "${package_variants[@]}"; do
            debug "Trying package variant: $package_variant"
            
            # Use the improved find_package_endpoint function
            if endpoint=$(find_package_endpoint "container" "$package_variant" 2>/dev/null); then
                found_package="$package_variant"
                success "Found Docker package: $found_package at $endpoint"
                break
            else
                debug "Package variant not found: $package_variant"
            fi
        done
        
        if [[ -z "$endpoint" ]]; then
            warning "Skipping Docker package (not found with any name variant): $package"
            info "Tried variants: ${package_variants[*]}"
            continue
        fi
        
        log "📍 Using Docker endpoint: $endpoint"
        
        # Get staging versions based on workflow outcome and cleanup context
        local versions_query
        local strategy_description
        
        # Build the filter based on cleanup context (same as production)
        local filter_conditions=""
        if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
            # Target specific PR number with explicit SHA tags (no time-based guessing)
            filter_conditions='
                (.metadata.container.tags[]? | test("^pr-'"$CLEANUP_PR_NUMBER"'$")) or
                (.metadata.container.tags[]? | test("^sha256-[a-f0-9]+-pr-'"$CLEANUP_PR_NUMBER"'$"))'
            strategy_description="TARGET PR #$CLEANUP_PR_NUMBER packages with explicit SHA tags"
            info "Targeting specific PR #$CLEANUP_PR_NUMBER packages"
            debug "Using explicit SHA tags: sha256-*-pr-$CLEANUP_PR_NUMBER (no time-based guessing)"
        else
            # Fallback to broader staging pattern (legacy behavior for unknown contexts)
            filter_conditions='
                (.metadata.container.tags[]? | test("^pr-[0-9]+$")) or
                (.metadata.container.tags[]? | test("-staging$")) or
                (.metadata.container.tags[]? | test("^sha256-[a-f0-9]+-pr-[0-9]+$")) or
                (.metadata.container.tags[]? | test("^sha256-[a-f0-9]+-main-[0-9]+$")) or
                (.metadata.container.tags[]? | test("^sha256-[a-f0-9]+-manual-[0-9]+$")) or
                (.metadata.container.tags[]? | test("^sha256-[a-f0-9]+-branch-.+-[0-9]+$"))'
            strategy_description="TARGET ALL staging packages (explicit SHA pattern)"
            warning "Using broad staging pattern - no specific PR context"
            debug "Targeting explicit SHA tags: sha256-*-{pr|main|manual|branch}-* patterns only"
        fi
        
        if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
            # Delete ALL matching staging images on success
            versions_query='.[] | select('"$filter_conditions"') | .id'
            log "  Strategy: DELETE ALL $strategy_description (workflow succeeded)"
        else
            # Keep last 5 matching staging versions on failure (for debugging)
            versions_query='[.[] | select('"$filter_conditions"')] | sort_by(.created_at) | reverse | .[5:] | .[].id'
            log "  Strategy: Keep last 5 of $strategy_description (workflow failed)"
        fi
        
        # Make API call to get package versions
        debug "Getting versions for package: $found_package"
        
        local version_response
        local api_exit_code
        
        # Make the API call with proper error handling
        if version_response=$(gh api "${endpoint}/versions" 2>&1); then
            api_exit_code=0
            debug "API call successful"
        else
            api_exit_code=$?
            error "API call failed for ${endpoint}/versions (exit code: $api_exit_code)"
            error "Error response: $version_response"
            continue
        fi
        
        debug "Raw API response received (length: ${#version_response} chars)"
        
        local version_count
        version_count=$(echo "$version_response" | jq 'length' 2>/dev/null || echo "0")
        info "Total versions found for $package: $version_count"
        ((total_found += version_count))
        
        if [[ "$version_count" -gt 0 ]]; then
            debug "Sample version details:"
            echo "$version_response" | jq -r '.[:3] | .[] | "  - ID: \(.id), Tags: \(.metadata.container.tags // [] | join(", ")), Created: \(.created_at)"' 2>/dev/null || debug "  (Failed to get details)"
            
            # Show current staging versions specifically for debugging using same filter
            local current_staging
            current_staging=$(echo "$version_response" | jq -r '.[] | select('"$filter_conditions"') | "  - Staging: ID=\(.id), Tags=[\(.metadata.container.tags | join(","))], Created=\(.created_at)"' 2>/dev/null || echo "")
            if [[ -n "$current_staging" ]]; then
                info "Current staging versions matching filter:"
                echo "$current_staging"
            else
                info "No staging versions found matching current filter"
            fi
        fi
        
        local versions
        debug "Applying staging filter query..."
        versions=$(echo "$version_response" | jq -r "$versions_query" 2>&1)
        local jq_exit_code=$?
        
        if [[ $jq_exit_code -ne 0 ]]; then
            error "JQ filter failed (exit code: $jq_exit_code)"
            error "JQ error: $versions"
            debug "Query was: $versions_query"
            versions=""
        else
            debug "JQ filter applied successfully"
        fi
            
        # Count non-empty lines safely
        local staging_count=0
        if [[ -n "$versions" && "$versions" != "" ]]; then
            # Remove any trailing whitespace and count non-empty lines
            local cleaned_versions
            cleaned_versions=$(echo "$versions" | sed '/^[[:space:]]*$/d')
            if [[ -n "$cleaned_versions" ]]; then
                staging_count=$(echo "$cleaned_versions" | grep -c . 2>/dev/null || echo "0")
            fi
        fi
        
        info "Staging versions after filtering: $staging_count versions"
        if [[ "$staging_count" -gt 0 ]]; then
            debug "Version IDs to delete: $(echo "$versions" | tr '\n' ' ')"
        fi
        
        if [[ "$staging_count" -eq 0 ]]; then
            info "No staging versions to clean up for $package"
            continue
        fi
        
        local package_deleted=0
        warning "Would attempt to delete $staging_count staging versions in production..."
        
        # In test mode, show what would be deleted without actually deleting
        while IFS= read -r version_id; do
            if [[ -n "$version_id" && "$version_id" != "null" ]]; then
                debug "Would delete Docker version ID: $version_id"
                debug "DELETE endpoint: ${endpoint}/versions/$version_id"
                
                # Test auth check (same as production would do)
                local auth_check
                auth_check=$(gh auth status 2>&1 || echo "Auth failed")
                debug "Auth status: $(echo "$auth_check" | head -n 1)"
                
                # In production, this would actually delete
                success "✅ [TEST MODE] Would successfully delete Docker version: $version_id"
                ((package_deleted++))
                ((total_deleted++))
            else
                warning "Would skip invalid version ID: '$version_id'"
            fi
        done <<< "$versions"
        
        info "$package: would delete $package_deleted staging versions"
    done
    
    success "🐳 Docker staging cleanup test complete:"
    log "  Total versions found: $total_found"
    log "  Would delete: $total_deleted staging versions"
}

# Enhanced npm cleanup testing (same pattern as Docker)
test_cleanup_staging_npm() {
    log "📦 Testing staging npm packages cleanup..."
    
    local scope="$NPM_SCOPE_CLEAN"
    local base_package="$NPM_STAGING_PACKAGE_NAME"
    local scoped_package="${scope}%2F${base_package}"  # URL-encoded @scope/package
    local total_deleted=0
    
    # Try to find the npm package using different naming patterns
    local package_patterns=(
        "$base_package"          # Base package name (verified working in testing)
        "$scoped_package"        # URL-encoded scoped package  
        "${scope}/${base_package}"  # Scoped package with slash
    )
    
    local endpoint
    for pattern in "${package_patterns[@]}"; do
        debug "Trying npm package pattern: $pattern"
        if endpoint=$(find_package_endpoint "npm" "$pattern" 2>/dev/null); then
            success "Found staging npm package: $pattern at $endpoint"
            break
        else
            debug "npm package pattern not found: $pattern"
        fi
    done
    
    if [[ -z "$endpoint" ]]; then
        info "No staging npm packages found"
        return 0
    fi
        
    # Debug: First show basic info about npm versions
    local version_count
    version_count=$(gh api "${endpoint}/versions" --jq 'length' 2>/dev/null || echo "0")
    info "Total npm versions found: $version_count"
    
    if [[ "$version_count" -gt 0 ]]; then
        debug "Sample npm version details:"
        gh api "${endpoint}/versions" --jq '.[:3] | .[] | "  - ID: \(.id), Name: \(.name), Created: \(.created_at)"' 2>/dev/null || debug "  (Failed to get details)"
    fi
    
    # Get versions based on workflow outcome and cleanup context - filter staging versions
    local versions_query
    local strategy_description
    
    # Build the filter based on cleanup context (same as production)
    local name_filter
    if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
        # Target specific PR number: e.g. -pr.42.123
        name_filter='(.name | test("-pr\\.'$CLEANUP_PR_NUMBER'\\.\\d+$"))'
        strategy_description="TARGET PR #$CLEANUP_PR_NUMBER npm packages only"
        info "Targeting specific PR #$CLEANUP_PR_NUMBER npm packages"
    else
        # Fallback to broader pattern (legacy behavior)
        name_filter='(.name | test("-pr\\."))'
        strategy_description="TARGET ALL staging npm packages (broad pattern)"
        warning "Using broad npm staging pattern - no specific PR context"
    fi
    
    if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
        # Delete ALL matching staging versions on success
        versions_query='.[] | select('$name_filter') | .id'
        log "  Strategy: DELETE ALL $strategy_description (workflow succeeded)"
    else
        # Keep last 5 matching staging versions on failure
        versions_query='[.[] | select('$name_filter')] | sort_by(.created_at) | reverse | .[5:] | .[].id'
        log "  Strategy: Keep last 5 of $strategy_description (workflow failed)"
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
    
    info "Staging npm versions after filtering: $staging_count versions"
    if [[ "$staging_count" -eq 0 ]]; then
        info "No staging npm versions to clean up"
        return 0
    fi
    
    while IFS= read -r version_id; do
        if [[ -n "$version_id" && "$version_id" != "null" ]]; then
            debug "Would delete npm version ID: $version_id"
            debug "DELETE endpoint: ${endpoint}/versions/$version_id"
            
            success "✅ [TEST MODE] Would successfully delete npm version: $version_id"
            ((total_deleted++))
        else
            warning "Would skip invalid npm version ID: '$version_id'"
        fi
    done <<< "$versions"
    
    success "📦 npm staging cleanup test complete: would delete $total_deleted versions"
}

# Enhanced Maven cleanup testing (same pattern as npm)
test_cleanup_staging_maven() {
    log "🏗️ Testing staging Maven packages cleanup..."
    
    local package_name="$ANDROID_STAGING_PACKAGE"
    local total_deleted=0
    
    # Find the Maven package using dynamic endpoint detection
    local endpoint
    debug "Searching for Maven package: $package_name"
    if ! endpoint=$(find_package_endpoint "maven" "$package_name" 2>/dev/null); then
        info "No staging Maven packages found with name: $package_name"
        return 0
    else
        success "Found staging Maven package: $package_name at $endpoint"
    fi
        
    # Debug: First show basic info about Maven versions
    local version_count
    version_count=$(gh api "${endpoint}/versions" --jq 'length' 2>/dev/null || echo "0")
    info "Total Maven versions found: $version_count"
    
    if [[ "$version_count" -gt 0 ]]; then
        debug "Sample Maven version details:"
        gh api "${endpoint}/versions" --jq '.[:3] | .[] | "  - ID: \(.id), Name: \(.name), Created: \(.created_at)"' 2>/dev/null || debug "  (Failed to get details)"
    fi
    
    # Get versions based on workflow outcome and cleanup context - filter staging versions
    local versions_query
    local strategy_description
    
    # Build the filter based on cleanup context (same as production)
    local name_filter
    if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
        # Target specific PR number: e.g. -pr.42.123
        name_filter='(.name | test("-pr\\.'$CLEANUP_PR_NUMBER'\\.\\d+$"))'
        strategy_description="TARGET PR #$CLEANUP_PR_NUMBER Maven packages only"
        info "Targeting specific PR #$CLEANUP_PR_NUMBER Maven packages"
    else
        # Fallback to broader pattern (legacy behavior)
        name_filter='(.name | test("-pr\\."))'
        strategy_description="TARGET ALL staging Maven packages (broad pattern)"
        warning "Using broad Maven staging pattern - no specific PR context"
    fi
    
    if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
        # Delete ALL matching staging versions on success
        versions_query='.[] | select('$name_filter') | .id'
        log "  Strategy: DELETE ALL $strategy_description (workflow succeeded)"
    else
        # Keep last 5 matching staging versions on failure
        versions_query='[.[] | select('$name_filter')] | sort_by(.created_at) | reverse | .[5:] | .[].id'
        log "  Strategy: Keep last 5 of $strategy_description (workflow failed)"
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
    
    info "Staging Maven versions after filtering: $staging_count versions"
    if [[ "$staging_count" -eq 0 ]]; then
        info "No staging Maven versions to clean up"
        return 0
    fi
    
    while IFS= read -r version_id; do
        if [[ -n "$version_id" && "$version_id" != "null" ]]; then
            debug "Would delete Maven version ID: $version_id"
            debug "DELETE endpoint: ${endpoint}/versions/$version_id"
            
            success "✅ [TEST MODE] Would successfully delete Maven version: $version_id"
            ((total_deleted++))
        else
            warning "Would skip invalid Maven version ID: '$version_id'"
        fi
    done <<< "$versions"
    
    success "🏗️ Maven staging cleanup test complete: would delete $total_deleted versions"
}

# Main testing function
perform_staging_cleanup_test() {
    log "🧹 Starting GitHub Packages staging cleanup test"
    info "📋 Test scope: ONLY GitHub Packages staging artifacts"
    log "🎯 Workflow outcome: $WORKFLOW_OUTCOME"
    log "🏢 Repository owner: $REPOSITORY_OWNER"
    log "🎯 Cleanup context: $CLEANUP_CONTEXT"
    if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
        info "🔍 Targeting PR: #$CLEANUP_PR_NUMBER"
        log "📋 Package patterns:"
        log "  - Docker tags: pr-${CLEANUP_PR_NUMBER}, sha256-*-pr-${CLEANUP_PR_NUMBER}"
        log "  - npm/Maven versions: *-pr.${CLEANUP_PR_NUMBER}.*"
    else
        warning "Using broad staging patterns (all PRs)"
        log "📋 Package patterns:"
        log "  - Docker tags: pr-*, sha256-*-{pr|main|manual|branch}-*, *-staging"
        log "  - npm/Maven versions: *-pr.*"
    fi
    log ""
    
    case "$WORKFLOW_OUTCOME" in
        "success")
            success "✅ Workflow succeeded - testing COMPLETE staging cleanup"
            log "🗑️ Strategy: Delete ALL staging packages (validation complete)"
            ;;
        "failure")
            warning "❌ Workflow failed - testing CONSERVATIVE staging cleanup"
            log "🔍 Strategy: Keep last 5 versions for debugging"
            ;;
    esac
    
    log ""
    
    # Perform cleanup testing for each package type
    test_cleanup_staging_docker
    log ""
    test_cleanup_staging_npm
    log ""
    test_cleanup_staging_maven
    
    log ""
    success "🎉 GitHub Packages staging cleanup test completed"
}

# Main execution function
main() {
    log "🚀 Local GitHub Packages Staging Cleanup Test Starting"
    
    success "🧪 LOCAL TESTING MODE"
    log "  Workflow outcome: $WORKFLOW_OUTCOME"
    log "  Repository owner: $REPOSITORY_OWNER"
    log "  PR Number: $LOCAL_PR_NUMBER"
    log "  Using local GitHub CLI authentication"
    if [[ "$DEBUG_MODE" == "true" ]]; then
        log "  Debug mode: ENABLED"
    fi
    log ""
    
    # Load central configuration
    load_central_config
    log ""
    
    # Validate inputs and GitHub CLI
    validate_inputs
    log ""
    validate_github_cli
    log ""
    
    # Determine cleanup scope based on context
    determine_cleanup_scope
    log ""
    
    # Perform staging cleanup test
    perform_staging_cleanup_test
    
    success "✅ Local staging cleanup test completed successfully"
}

# Enhanced error trapping for better debugging
trap 'error "Error occurred at line $LINENO in function ${FUNCNAME[1]:-main}"; error "Last command: $BASH_COMMAND"; error "Exit code: $?"' ERR

# Run main function with all arguments
main "$@"