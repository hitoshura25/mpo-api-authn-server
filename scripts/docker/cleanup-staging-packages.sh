#!/bin/bash
#
# GitHub Packages Staging Cleanup Script
#
# This script cleans up staging artifacts from GitHub Packages after main CI/CD completion.
# It targets ONLY staging packages and provides different cleanup strategies based on workflow outcome.
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
#
# EXIT CODES:
#   0 - Success (cleanup completed or skipped)
#   1 - Error occurred during cleanup
#

set -euo pipefail

# Configuration
WORKFLOW_OUTCOME="${1:-success}"
REPOSITORY_OWNER="${2:-${GITHUB_REPOSITORY_OWNER:-}}"

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

# Function to clean up staging Docker images from GHCR
cleanup_staging_docker() {
    log "🐳 Cleaning up staging Docker images from GHCR..."
    
    local packages=("webauthn-server" "webauthn-test-credentials-service")
    local total_deleted=0
    
    for package in "${packages[@]}"; do
        log "🔍 Processing Docker package: $package"
        
        # Get staging versions based on workflow outcome
        local versions_query
        if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
            # Delete ALL staging images on success (pr- tags and staging suffixes)
            versions_query='
            .[] | 
            select(
                (.metadata.container.tags[]? | test("^pr-[0-9]+")) or
                (.metadata.container.tags[]? | test("-staging$"))
            ) | 
            .id'
            log "  Strategy: DELETE ALL staging images (workflow succeeded)"
        else
            # Keep last 5 staging versions on failure (for debugging)
            versions_query='
            [.[] | 
             select(
                (.metadata.container.tags[]? | test("^pr-[0-9]+")) or
                (.metadata.container.tags[]? | test("-staging$"))
             )] |
            sort_by(.created_at) | reverse | .[5:] | .[].id'
            log "  Strategy: Keep last 5 staging versions (workflow failed)"
        fi
        
        local versions
        versions=$(gh api \
            --method GET \
            "/orgs/${REPOSITORY_OWNER}/packages/container/${package}/versions" \
            --jq "$versions_query" \
            2>/dev/null || echo "")
            
        if [[ -z "$versions" ]]; then
            log "ℹ️ No staging versions to clean up for $package"
            continue
        fi
        
        local package_deleted=0
        while IFS= read -r version_id; do
            if [[ -n "$version_id" ]]; then
                if gh api \
                    --method DELETE \
                    "/orgs/${REPOSITORY_OWNER}/packages/container/${package}/versions/$version_id" \
                    2>/dev/null; then
                    ((package_deleted++))
                    ((total_deleted++))
                else
                    log "⚠️ Failed to delete Docker version $version_id"
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
    
    local scope="vmenon25"
    local base_package="mpo-webauthn-client-staging"
    local scoped_package="${scope}%2F${base_package}"  # URL-encoded @scope/package
    local total_deleted=0
    
    # Try multiple API endpoints (user/repo/org packages)
    local api_endpoints=(
        "/user/packages/npm/$scoped_package"
        "/repos/${GITHUB_REPOSITORY:-$REPOSITORY_OWNER/repo}/packages/npm/$base_package"
        "/orgs/$REPOSITORY_OWNER/packages/npm/$base_package"
    )
    
    for endpoint in "${api_endpoints[@]}"; do
        log "🔍 Checking npm endpoint: $endpoint"
        
        if ! gh api "${endpoint}/versions" >/dev/null 2>&1; then
            continue
        fi
        
        log "📍 Found staging npm package at: $endpoint"
        
        # Get versions based on workflow outcome
        local versions_query
        if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
            # Delete ALL staging versions on success
            versions_query='.[] | .id'
            log "  Strategy: DELETE ALL staging versions (workflow succeeded)"
        else
            # Keep last 5 staging versions on failure
            versions_query='sort_by(.created_at) | reverse | .[5:] | .[].id'
            log "  Strategy: Keep last 5 staging versions (workflow failed)"
        fi
        
        local versions
        versions=$(gh api \
            --paginate \
            "${endpoint}/versions" \
            --jq "$versions_query" \
            2>/dev/null || echo "")
            
        if [[ -z "$versions" ]]; then
            log "ℹ️ No staging npm versions to clean up"
            break
        fi
        
        while IFS= read -r version_id; do
            if [[ -n "$version_id" ]]; then
                if gh api \
                    --method DELETE \
                    "${endpoint}/versions/$version_id" \
                    2>/dev/null; then
                    ((total_deleted++))
                else
                    log "⚠️ Failed to delete npm version $version_id"
                fi
            fi
        done <<< "$versions"
        
        break  # Found and processed the package, no need to try other endpoints
    done
    
    if [[ $total_deleted -eq 0 ]]; then
        log "ℹ️ No staging npm packages found or processed"
    else
        log "📦 npm staging cleanup complete: $total_deleted versions deleted"
    fi
}

# Function to clean up staging Maven packages
cleanup_staging_maven() {
    log "🏗️ Cleaning up staging Maven packages..."
    
    local package_name="io.github.hitoshura25.mpo-webauthn-android-client-staging"
    local total_deleted=0
    
    # Try multiple API endpoints (user/repo/org packages)
    local api_endpoints=(
        "/user/packages/maven/$package_name"
        "/repos/${GITHUB_REPOSITORY:-$REPOSITORY_OWNER/repo}/packages/maven/$package_name"
        "/orgs/$REPOSITORY_OWNER/packages/maven/$package_name"
    )
    
    for endpoint in "${api_endpoints[@]}"; do
        log "🔍 Checking Maven endpoint: $endpoint"
        
        if ! gh api "${endpoint}/versions" >/dev/null 2>&1; then
            continue
        fi
        
        log "📍 Found staging Maven package at: $endpoint"
        
        # Get versions based on workflow outcome
        local versions_query
        if [[ "$WORKFLOW_OUTCOME" == "success" ]]; then
            # Delete ALL staging versions on success
            versions_query='.[] | .id'
            log "  Strategy: DELETE ALL staging versions (workflow succeeded)"
        else
            # Keep last 5 staging versions on failure
            versions_query='sort_by(.created_at) | reverse | .[5:] | .[].id'
            log "  Strategy: Keep last 5 staging versions (workflow failed)"
        fi
        
        local versions
        versions=$(gh api \
            --paginate \
            "${endpoint}/versions" \
            --jq "$versions_query" \
            2>/dev/null || echo "")
            
        if [[ -z "$versions" ]]; then
            log "ℹ️ No staging Maven versions to clean up"
            break
        fi
        
        while IFS= read -r version_id; do
            if [[ -n "$version_id" ]]; then
                if gh api \
                    --method DELETE \
                    "${endpoint}/versions/$version_id" \
                    2>/dev/null; then
                    ((total_deleted++))
                else
                    log "⚠️ Failed to delete Maven version $version_id"
                fi
            fi
        done <<< "$versions"
        
        break  # Found and processed the package
    done
    
    if [[ $total_deleted -eq 0 ]]; then
        log "ℹ️ No staging Maven packages found or processed"
    else
        log "🏗️ Maven staging cleanup complete: $total_deleted versions deleted"
    fi
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