#!/bin/bash
#
# GitHub Container Registry (GHCR) Cleanup Script
#
# This script cleans up old versions of Docker packages in GHCR to prevent registry bloat.
# It keeps the latest 5 versions and deletes older ones using the GitHub API.
#
# USAGE:
#   ./cleanup-ghcr.sh [repository_owner]
#
# ENVIRONMENT VARIABLES:
#   GH_TOKEN - GitHub token with packages:write permission (required)
#   GITHUB_REPOSITORY_OWNER - Repository owner (if not provided as argument)
#
# AUTHENTICATION:
#   Requires GitHub CLI (gh) to be authenticated with appropriate permissions.
#
# EXIT CODES:
#   0 - Success (cleanup completed)
#   0 - No cleanup needed (no old versions found)
#   1 - Error occurred during cleanup
#

set -euo pipefail

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Function to clean up old versions of a package
cleanup_package() {
    local package_name="$1"
    local repository_owner="$2"
    local package_type="container"
    
    log "📦 Cleaning up package: $package_name"
    
    # Get package versions (keep latest 5, delete older ones)
    local versions
    versions=$(gh api \
        --method GET \
        "/orgs/${repository_owner}/packages/${package_type}/${package_name}/versions" \
        --jq 'sort_by(.created_at) | reverse | .[5:] | .[].id' \
        2>/dev/null || echo "")
        
    if [ -z "$versions" ]; then
        log "ℹ️ No old versions to clean up for $package_name"
        return 0
    fi
    
    local version_count
    version_count=$(echo "$versions" | wc -l)
    log "🗑️ Found $version_count old versions to delete for $package_name"
    
    # Delete old versions
    local deleted_count=0
    local failed_count=0
    
    while IFS= read -r version_id; do
        if [ -n "$version_id" ]; then
            log "Deleting version ID: $version_id"
            if gh api \
                --method DELETE \
                "/orgs/${repository_owner}/packages/${package_type}/${package_name}/versions/$version_id" \
                2>/dev/null; then
                ((deleted_count++))
            else
                log "⚠️ Failed to delete version $version_id"
                ((failed_count++))
            fi
        fi
    done <<< "$versions"
    
    log "📊 Cleanup summary for $package_name:"
    log "  - Deleted: $deleted_count versions"
    log "  - Failed: $failed_count versions"
    
    return 0
}

# Function to validate GitHub CLI and authentication
validate_github_cli() {
    log "🔍 Validating GitHub CLI setup..."
    
    # Check if gh is installed
    if ! command -v gh &> /dev/null; then
        log "❌ Error: GitHub CLI (gh) is not installed"
        log "Please install gh: https://cli.github.com/"
        return 1
    fi
    
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        log "❌ Error: GitHub CLI is not authenticated"
        log "Please run: gh auth login"
        return 1
    fi
    
    # Check if token has required permissions
    if [ -z "${GH_TOKEN:-}" ]; then
        log "⚠️ Warning: GH_TOKEN environment variable not set"
        log "Using default gh authentication"
    fi
    
    log "✅ GitHub CLI authentication validated"
    return 0
}

# Main cleanup function
perform_cleanup() {
    local repository_owner="$1"
    
    log "🧹 Starting GHCR cleanup for repository owner: $repository_owner"
    
    # List of packages to clean up
    local packages=(
        "webauthn-server"
        "webauthn-test-credentials-service"
    )
    
    local cleanup_success=true
    
    # Clean up each package
    for package in "${packages[@]}"; do
        if ! cleanup_package "$package" "$repository_owner"; then
            log "❌ Failed to clean up package: $package"
            cleanup_success=false
        fi
    done
    
    if [ "$cleanup_success" = true ]; then
        log "✅ GHCR cleanup completed successfully"
        return 0
    else
        log "⚠️ GHCR cleanup completed with some errors"
        return 0  # Don't fail the overall process for cleanup errors
    fi
}

# Main execution
main() {
    local repository_owner="${1:-${GITHUB_REPOSITORY_OWNER:-}}"
    
    if [ -z "$repository_owner" ]; then
        # Try to extract from GITHUB_REPOSITORY environment variable
        if [ -n "${GITHUB_REPOSITORY:-}" ]; then
            repository_owner="${GITHUB_REPOSITORY%%/*}"
        else
            log "❌ Error: Repository owner not specified"
            log "Usage: $0 [repository_owner]"
            log "Or set GITHUB_REPOSITORY_OWNER environment variable"
            exit 1
        fi
    fi
    
    log "🚀 GHCR Cleanup Script Starting"
    log "Repository owner: $repository_owner"
    
    # Validate GitHub CLI setup
    if ! validate_github_cli; then
        exit 1
    fi
    
    # Perform cleanup
    perform_cleanup "$repository_owner"
}

# Trap errors for better debugging (but allow cleanup to continue on errors)
trap 'log "⚠️ Warning: Error occurred at line $LINENO (continuing cleanup)"' ERR

# Run main function with all arguments
main "$@"