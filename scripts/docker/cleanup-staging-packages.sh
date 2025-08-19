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
    log "  Repository Owner: $REPOSITORY_OWNER"
    log "  GitHub Repository: ${GITHUB_REPOSITORY:-NOT_SET}"
    log "  Constructed Repo Path: ${GITHUB_REPOSITORY:-${REPOSITORY_OWNER}/repo}"
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
    log "  npm Scoped Package (URL-encoded): ${NPM_SCOPE_CLEAN}%2F${NPM_STAGING_PACKAGE_NAME}"
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

# Function to determine cleanup scope based on context
determine_cleanup_scope() {
    local event_name="${GITHUB_EVENT_NAME:-}"
    local pr_number="${GITHUB_PR_NUMBER:-}"
    local ref_name="${GITHUB_REF_NAME:-}"
    
    log "🔍 Determining cleanup scope from context:"
    log "  Event Name: ${event_name:-'NOT_SET'}"
    log "  PR Number: ${pr_number:-'NOT_SET'}"
    log "  Ref Name: ${ref_name:-'NOT_SET'}"
    
    # Determine cleanup context
    if [[ "$event_name" == "pull_request" && -n "$pr_number" ]]; then
        # PR context - clean only current PR packages
        CLEANUP_CONTEXT="pr"
        CLEANUP_PR_NUMBER="$pr_number"
        log "✅ Context: PR #${pr_number} - will target only pr-${pr_number} packages"
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
            log "✅ Context: Main branch (recent merge from PR #${recent_pr_from_merge}) - will target pr-${recent_pr_from_merge} packages"
        else
            log "⚠️ Context: Main branch (no recent PR detected) - will use broad staging pattern for safety"
        fi
    else
        # Unknown context - use broad staging pattern but log the issue
        CLEANUP_CONTEXT="unknown"
        CLEANUP_PR_NUMBER=""
        log "⚠️ Context: Unknown (event: ${event_name}, ref: ${ref_name}) - will use broad staging pattern"
        log "🔧 Consider updating workflow to provide proper context variables"
    fi
    
    # Set global variables for use in cleanup functions
    export CLEANUP_CONTEXT
    export CLEANUP_PR_NUMBER
    
    log "📋 Final cleanup scope:"
    log "  Context: $CLEANUP_CONTEXT"
    log "  PR Number: ${CLEANUP_PR_NUMBER:-'NONE'}"
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

# Function to URL-encode package names for API calls
url_encode_package_name() {
    local package_name="$1"
    # URL encode forward slashes and other special characters that may appear in package names
    echo "$package_name" | sed 's|/|%2F|g' | sed 's| |%20|g'
}

# Function to find the correct API endpoint for a package
find_package_endpoint() {
    local package_type="$1"
    local package_name="$2"
    
    # URL-encode the package name for API calls
    local encoded_package_name
    encoded_package_name=$(url_encode_package_name "$package_name")
    
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
        # Send logging to stderr to avoid contaminating command substitution
        log "🔍 Testing endpoint: $endpoint" >&2
        log "🔍 Original package name: $package_name" >&2
        log "🔍 URL-encoded package name: $encoded_package_name" >&2
        
        # Test endpoint with more robust error checking
        local api_test_result
        api_test_result=$(gh api "${endpoint}/versions" --silent 2>&1)
        local api_exit_code=$?
        
        if [[ $api_exit_code -eq 0 ]]; then
            log "✅ Found package at: $endpoint" >&2
            
            # Verify the endpoint actually returns version data
            local version_count
            version_count=$(echo "$api_test_result" | jq 'length' 2>/dev/null || echo "0")
            log "🔍 Endpoint verification: $version_count versions available" >&2
            
            # Only return the clean endpoint path to stdout
            echo "$endpoint"
            return 0
        else
            log "❌ Endpoint failed: $endpoint (exit code: $api_exit_code)" >&2
            if [[ "$api_test_result" =~ "404" ]]; then
                log "   Package not found at this endpoint" >&2
            elif [[ "$api_test_result" =~ "403" ]]; then
                log "   Permission denied - check token permissions" >&2
            else
                log "   Error details: $(echo "$api_test_result" | head -c 100)..." >&2
            fi
        fi
    done
    
    log "❌ Package not found at any endpoint: $package_name" >&2
    log "❌ Available endpoints tested:" >&2
    for endpoint in "${endpoints[@]}"; do
        log "   - $endpoint/versions" >&2
    done
    return 1
}

# Function to clean up staging Docker images from GHCR
cleanup_staging_docker() {
    log "🐳 Cleaning up staging Docker images from GHCR..."
    
    local packages=("$DOCKER_WEBAUTHN_IMAGE_NAME" "$DOCKER_TEST_CREDENTIALS_IMAGE_NAME")
    local total_deleted=0
    
    for package in "${packages[@]}"; do
        log "🔍 Processing Docker package: $package"
        
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
            log "🔍 Trying package variant: $package_variant"
            
            # Use the improved find_package_endpoint function
            if endpoint=$(find_package_endpoint "container" "$package_variant" 2>/dev/null); then
                found_package="$package_variant"
                log "✅ Found Docker package: $found_package at $endpoint"
                break
            else
                log "   Package variant not found: $package_variant"
            fi
        done
        
        if [[ -z "$endpoint" ]]; then
            log "⚠️ Skipping Docker package (not found with any name variant): $package"
            log "   Tried variants: ${package_variants[*]}"
            continue
        fi
        
        log "📍 Using Docker endpoint: $endpoint"
        
        # Get staging versions based on workflow outcome and cleanup context
        local versions_query
        local strategy_description
        
        # Build the filter based on cleanup context
        local filter_conditions=""
        if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
            # Target specific PR number
            filter_conditions='
                (.metadata.container.tags[]? | test("^pr-'"$CLEANUP_PR_NUMBER"'$")) or
                (.metadata.container.tags[]? | test("^sha256-.*pr-'"$CLEANUP_PR_NUMBER"'"))'
            strategy_description="TARGET PR #$CLEANUP_PR_NUMBER packages only"
            log "🎯 Targeting specific PR #$CLEANUP_PR_NUMBER packages"
        else
            # Fallback to broader pattern (legacy behavior for unknown contexts)
            filter_conditions='
                (.metadata.container.tags[]? | test("^pr-[0-9]+")) or
                (.metadata.container.tags[]? | test("-staging$")) or
                (.metadata.container.tags[]? | test("^pr-")) or
                (.metadata.container.tags[]? | test("^sha256-"))'
            strategy_description="TARGET ALL staging packages (broad pattern)"
            log "⚠️ Using broad staging pattern - no specific PR context"
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
        log "🔍 Getting versions for package: $found_package"
        
        local version_response
        local api_exit_code
        
        # Make the API call with proper error handling
        if version_response=$(gh api "${endpoint}/versions" 2>&1); then
            api_exit_code=0
            log "✅ API call successful"
        else
            api_exit_code=$?
            log "❌ API call failed for ${endpoint}/versions (exit code: $api_exit_code)"
            log "❌ Error response: $version_response"
            continue
        fi
        
        log "🔍 Raw API response received (length: ${#version_response} chars)"
        
        local version_count
        version_count=$(echo "$version_response" | jq 'length' 2>/dev/null || echo "0")
        log "🔍 Total versions found for $package: $version_count"
        
        if [[ "$version_count" -gt 0 ]]; then
            log "🔍 Sample version details:"
            echo "$version_response" | jq -r '.[:3] | .[] | "  - ID: \(.id), Tags: \(.metadata.container.tags // [] | join(", ")), Created: \(.created_at)"' 2>/dev/null || log "  (Failed to get details)"
            
            # Show current staging versions specifically for debugging using same filter
            local current_staging
            current_staging=$(echo "$version_response" | jq -r '.[] | select('"$filter_conditions"') | "  - Staging: ID=\(.id), Tags=[\(.metadata.container.tags | join(","))], Created=\(.created_at)"' 2>/dev/null || echo "")
            if [[ -n "$current_staging" ]]; then
                log "🔍 Current staging versions matching filter:"
                echo "$current_staging"
            else
                log "🔍 No staging versions found matching current filter"
            fi
        fi
        
        local versions
        log "🔍 Applying staging filter query..."
        versions=$(echo "$version_response" | jq -r "$versions_query" 2>&1)
        local jq_exit_code=$?
        
        if [[ $jq_exit_code -ne 0 ]]; then
            log "❌ JQ filter failed (exit code: $jq_exit_code)"
            log "❌ JQ error: $versions"
            log "❌ Query was: $versions_query"
            versions=""
        else
            log "✅ JQ filter applied successfully"
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
        
        log "🔍 Staging versions after filtering: $staging_count versions"
        if [[ "$staging_count" -gt 0 ]]; then
            log "🔍 Version IDs to delete: $(echo "$versions" | tr '\n' ' ')"
        fi
        
        if [[ "$staging_count" -eq 0 ]]; then
            log "ℹ️ No staging versions to clean up for $package"
            continue
        fi
        
        local package_deleted=0
        log "🗑️ Attempting to delete $staging_count staging versions..."
        
        while IFS= read -r version_id; do
            if [[ -n "$version_id" && "$version_id" != "null" ]]; then
                log "🔍 Deleting Docker version ID: $version_id"
                local delete_result
                if delete_result=$(gh api --method DELETE "${endpoint}/versions/$version_id" 2>&1); then
                    ((package_deleted++))
                    ((total_deleted++))
                    log "✅ Deleted Docker version: $version_id"
                else
                    log "⚠️ Failed to delete Docker version: $version_id"
                    log "   Delete error: $delete_result"
                fi
            fi
        done <<< "$versions"
        
        # Ensure the loop completed successfully
        local loop_exit_code=$?
        if [[ $loop_exit_code -ne 0 ]]; then
            log "⚠️ Version deletion loop had issues (exit code: $loop_exit_code)"
        fi
        
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
    # Based on testing, the working pattern is just the base package name without URL encoding the scope
    local package_patterns=(
        "$base_package"          # Base package name (verified working in testing)
        "$scoped_package"        # URL-encoded scoped package  
        "${scope}/${base_package}"  # Scoped package with slash
    )
    
    local endpoint
    for pattern in "${package_patterns[@]}"; do
        log "🔍 Trying npm package pattern: $pattern"
        if endpoint=$(find_package_endpoint "npm" "$pattern" 2>/dev/null); then
            log "📍 Found staging npm package: $pattern at $endpoint"
            break
        else
            log "   npm package pattern not found: $pattern"
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
    
    # Get versions based on workflow outcome and cleanup context - filter staging versions (contain -pr.)
    local versions_query
    local strategy_description
    
    # Build the filter based on cleanup context
    local name_filter
    if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
        # Target specific PR number: e.g. -pr.42.123
        name_filter='(.name | test("-pr\\.'$CLEANUP_PR_NUMBER'\\.\\d+$"))'
        strategy_description="TARGET PR #$CLEANUP_PR_NUMBER npm packages only"
        log "🎯 Targeting specific PR #$CLEANUP_PR_NUMBER npm packages"
    else
        # Fallback to broader pattern (legacy behavior)
        name_filter='(.name | test("-pr\\."))'
        strategy_description="TARGET ALL staging npm packages (broad pattern)"
        log "⚠️ Using broad npm staging pattern - no specific PR context"
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
    
    log "🔍 Staging npm versions after filtering: $staging_count versions"
    if [[ "$staging_count" -eq 0 ]]; then
        log "ℹ️ No staging npm versions to clean up"
        return 0
    fi
    
    while IFS= read -r version_id; do
        if [[ -n "$version_id" && "$version_id" != "null" ]]; then
            log "🔍 Deleting npm version ID: $version_id"
            local delete_result
            if delete_result=$(gh api --method DELETE "${endpoint}/versions/$version_id" 2>&1); then
                ((total_deleted++))
                log "✅ Deleted npm version: $version_id"
            else
                log "⚠️ Failed to delete npm version: $version_id"
                log "   Delete error: $delete_result"
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
    # Based on testing, the full package name format works
    local endpoint
    log "🔍 Searching for Maven package: $package_name"
    if ! endpoint=$(find_package_endpoint "maven" "$package_name" 2>/dev/null); then
        log "ℹ️ No staging Maven packages found with name: $package_name"
        return 0
    else
        log "📍 Found staging Maven package: $package_name at $endpoint"
    fi
        
    # Debug: First show basic info about Maven versions
    local version_count
    version_count=$(gh api "${endpoint}/versions" --jq 'length' 2>/dev/null || echo "0")
    log "🔍 Total Maven versions found: $version_count"
    
    if [[ "$version_count" -gt 0 ]]; then
        log "🔍 Sample Maven version details:"
        gh api "${endpoint}/versions" --jq '.[:3] | .[] | "  - ID: \(.id), Name: \(.name), Created: \(.created_at)"' 2>/dev/null || log "  (Failed to get details)"
    fi
    
    # Get versions based on workflow outcome and cleanup context - filter staging versions (contain -pr.)
    local versions_query
    local strategy_description
    
    # Build the filter based on cleanup context
    local name_filter
    if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
        # Target specific PR number: e.g. -pr.42.123
        name_filter='(.name | test("-pr\\.'$CLEANUP_PR_NUMBER'\\.\\d+$"))'
        strategy_description="TARGET PR #$CLEANUP_PR_NUMBER Maven packages only"
        log "🎯 Targeting specific PR #$CLEANUP_PR_NUMBER Maven packages"
    else
        # Fallback to broader pattern (legacy behavior)
        name_filter='(.name | test("-pr\\."))'
        strategy_description="TARGET ALL staging Maven packages (broad pattern)"
        log "⚠️ Using broad Maven staging pattern - no specific PR context"
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
    
    log "🔍 Staging Maven versions after filtering: $staging_count versions"
    if [[ "$staging_count" -eq 0 ]]; then
        log "ℹ️ No staging Maven versions to clean up"
        return 0
    fi
    
    while IFS= read -r version_id; do
        if [[ -n "$version_id" && "$version_id" != "null" ]]; then
            log "🔍 Deleting Maven version ID: $version_id"
            local delete_result
            if delete_result=$(gh api --method DELETE "${endpoint}/versions/$version_id" 2>&1); then
                ((total_deleted++))
                log "✅ Deleted Maven version: $version_id"
            else
                log "⚠️ Failed to delete Maven version: $version_id"
                log "   Delete error: $delete_result"
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
    log "🎯 Cleanup context: $CLEANUP_CONTEXT"
    if [[ -n "$CLEANUP_PR_NUMBER" ]]; then
        log "🔍 Targeting PR: #$CLEANUP_PR_NUMBER"
        log "📋 Package patterns:"
        log "  - Docker tags: pr-${CLEANUP_PR_NUMBER}, sha256-*pr-${CLEANUP_PR_NUMBER}"
        log "  - npm/Maven versions: *-pr.${CLEANUP_PR_NUMBER}.*"
    else
        log "⚠️ Using broad staging patterns (all PRs)"
        log "📋 Package patterns:"
        log "  - Docker tags: pr-*, sha256-*, *-staging"
        log "  - npm/Maven versions: *-pr.*"
    fi
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
    
    # Determine cleanup scope based on context
    determine_cleanup_scope
    
    # Perform staging cleanup
    perform_staging_cleanup
    
    log "✅ Staging cleanup script completed successfully"
}

# Trap errors for better debugging
trap 'log "❌ Error occurred at line $LINENO"' ERR

# Run main function
main