#!/bin/bash
#
# GitHub Packages Staging Cleanup Diagnostic Tool
#
# This script tests GitHub Packages API endpoints to diagnose staging cleanup issues.
# Use this tool when staging cleanup is failing or to validate API endpoint accessibility.
#
# USAGE:
#   ./scripts/testing/client-publishing/debug-staging-cleanup.sh
#   REPOSITORY_OWNER=custom_owner ./scripts/testing/client-publishing/debug-staging-cleanup.sh
#
# REQUIREMENTS:
#   - GitHub CLI (gh) installed and authenticated
#   - yq for YAML configuration parsing
#   - GH_TOKEN with packages:read permissions
#

set -euo pipefail

# Configuration - override these via environment variables if needed
REPOSITORY_OWNER="${REPOSITORY_OWNER:-hitoshura25}"
CONFIG_FILE="${CONFIG_FILE:-config/publishing-config.yml}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC} - $*"
}

error() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ❌ $*"
}

success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ✅ $*"
}

warning() {
    echo -e "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ⚠️ $*"
}

# Function to load configuration
load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    if ! command -v yq &> /dev/null; then
        error "yq is not installed (required for configuration loading)"
        exit 1
    fi
    
    log "Loading configuration from: $CONFIG_FILE"
    
    # Load configuration values
    ANDROID_GROUP_ID="$(yq eval '.packages.android.groupId' "$CONFIG_FILE")"
    ANDROID_BASE_ARTIFACT_ID="$(yq eval '.packages.android.baseArtifactId' "$CONFIG_FILE")"
    TYPESCRIPT_SCOPE="$(yq eval '.packages.typescript.scope.staging' "$CONFIG_FILE")"
    TYPESCRIPT_BASE_PACKAGE_NAME="$(yq eval '.packages.typescript.basePackageName' "$CONFIG_FILE")"
    ANDROID_STAGING_SUFFIX="$(yq eval '.naming.staging.androidSuffix' "$CONFIG_FILE")"
    NPM_STAGING_SUFFIX="$(yq eval '.naming.staging.npmSuffix' "$CONFIG_FILE")"
    AUTHOR_ID="$(yq eval '.metadata.author.id' "$CONFIG_FILE")"
    
    # Construct package names
    ANDROID_STAGING_PACKAGE="${ANDROID_GROUP_ID}.${ANDROID_BASE_ARTIFACT_ID}${ANDROID_STAGING_SUFFIX}"
    NPM_STAGING_PACKAGE_NAME="${TYPESCRIPT_BASE_PACKAGE_NAME}${NPM_STAGING_SUFFIX}"
    NPM_SCOPE_CLEAN="${TYPESCRIPT_SCOPE#@}"  # Remove @ prefix
    
    log "Configuration loaded:"
    log "  Android staging package: $ANDROID_STAGING_PACKAGE"
    log "  npm staging package: $NPM_STAGING_PACKAGE_NAME"
    log "  npm scope: $NPM_SCOPE_CLEAN"
    log "  Author ID: $AUTHOR_ID"
    log "  Repository owner: $REPOSITORY_OWNER"
}

# Function to validate GitHub CLI
validate_github_cli() {
    log "Validating GitHub CLI setup..."
    
    if ! command -v gh &> /dev/null; then
        error "GitHub CLI (gh) is not installed"
        exit 1
    fi
    
    if ! gh auth status &> /dev/null; then
        error "GitHub CLI is not authenticated"
        exit 1
    fi
    
    success "GitHub CLI authentication validated"
}

# Function to test Docker container package endpoints
test_docker_endpoints() {
    log "🐳 Testing Docker container package endpoints..."
    
    # Use full GHCR repository paths (matching the fixed cleanup script)
    local packages=("${REPOSITORY_OWNER}/webauthn-server" "${REPOSITORY_OWNER}/webauthn-test-credentials-service")
    
    for package in "${packages[@]}"; do
        log "Testing Docker package: $package"
        
        # Test different endpoint variations
        local endpoints=(
            "/orgs/${REPOSITORY_OWNER}/packages/container/${package}/versions"
            "/users/${REPOSITORY_OWNER}/packages/container/${package}/versions"
            "/user/packages/container/${package}/versions"
        )
        
        for endpoint in "${endpoints[@]}"; do
            log "  Testing endpoint: $endpoint"
            
            local status_code
            status_code=$(gh api "$endpoint" --silent --include 2>&1 | head -1 | grep -o 'HTTP/[0-9.]* [0-9]*' | awk '{print $2}' || echo "ERROR")
            
            if [[ "$status_code" == "200" ]]; then
                success "    ✅ SUCCESS ($status_code): $endpoint"
                
                # Get package info
                local package_count
                package_count=$(gh api "$endpoint" --jq 'length' 2>/dev/null || echo "0")
                log "    📦 Found $package_count versions"
                
                # Show first few versions
                if [[ "$package_count" -gt 0 ]]; then
                    log "    🔍 Sample versions:"
                    gh api "$endpoint" --jq '.[:3] | .[] | "      - ID: \(.id), Tags: \(.metadata.container.tags // [] | join(", ") | if . == "" then "none" else . end), Created: \(.created_at)"' 2>/dev/null || log "      Failed to get version details"
                fi
                break
            elif [[ "$status_code" == "404" ]]; then
                warning "    ❌ NOT FOUND ($status_code): $endpoint"
            elif [[ "$status_code" == "403" ]]; then
                error "    ❌ FORBIDDEN ($status_code): $endpoint - Check permissions"
            else
                error "    ❌ ERROR ($status_code): $endpoint"
            fi
        done
        log ""
    done
}

# Function to test npm package endpoints
test_npm_endpoints() {
    log "📦 Testing npm package endpoints..."
    
    local base_package="$NPM_STAGING_PACKAGE_NAME"
    local scope="$NPM_SCOPE_CLEAN"
    local scoped_package="${scope}%2F${base_package}"  # URL-encoded @scope/package
    
    log "Testing npm package: $base_package (scope: $scope)"
    
    # Test different endpoint variations
    local endpoints=(
        "/orgs/${REPOSITORY_OWNER}/packages/npm/${base_package}/versions"
        "/users/${REPOSITORY_OWNER}/packages/npm/${base_package}/versions"
        "/user/packages/npm/${base_package}/versions"
        "/user/packages/npm/${scoped_package}/versions"
    )
    
    # Also try with the production package name
    local prod_package="${TYPESCRIPT_BASE_PACKAGE_NAME}"
    endpoints+=(
        "/orgs/${REPOSITORY_OWNER}/packages/npm/${prod_package}/versions"
        "/users/${REPOSITORY_OWNER}/packages/npm/${prod_package}/versions"
        "/user/packages/npm/${prod_package}/versions"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log "  Testing endpoint: $endpoint"
        
        local status_code
        status_code=$(gh api "$endpoint" --silent --include 2>&1 | head -1 | grep -o 'HTTP/[0-9.]* [0-9]*' | awk '{print $2}' || echo "ERROR")
        
        if [[ "$status_code" == "200" ]]; then
            success "    ✅ SUCCESS ($status_code): $endpoint"
            
            # Get package info
            local package_count
            package_count=$(gh api "$endpoint" --jq 'length' 2>/dev/null || echo "0")
            log "    📦 Found $package_count versions"
            
            # Show first few versions
            if [[ "$package_count" -gt 0 ]]; then
                log "    🔍 Sample versions:"
                gh api "$endpoint" --jq '.[:3] | .[] | "      - ID: \(.id), Name: \(.name), Created: \(.created_at)"' 2>/dev/null || log "      Failed to get version details"
            fi
        elif [[ "$status_code" == "404" ]]; then
            warning "    ❌ NOT FOUND ($status_code): $endpoint"
        elif [[ "$status_code" == "403" ]]; then
            error "    ❌ FORBIDDEN ($status_code): $endpoint - Check permissions"
        else
            error "    ❌ ERROR ($status_code): $endpoint"
        fi
    done
    log ""
}

# Function to test Maven package endpoints
test_maven_endpoints() {
    log "🏗️ Testing Maven package endpoints..."
    
    local package_name="$ANDROID_STAGING_PACKAGE"
    
    log "Testing Maven package: $package_name"
    
    # Test different endpoint variations
    local endpoints=(
        "/orgs/${REPOSITORY_OWNER}/packages/maven/${package_name}/versions"
        "/users/${REPOSITORY_OWNER}/packages/maven/${package_name}/versions"
        "/user/packages/maven/${package_name}/versions"
    )
    
    # Also try with the production package name
    local prod_package="${ANDROID_GROUP_ID}.${ANDROID_BASE_ARTIFACT_ID}"
    endpoints+=(
        "/orgs/${REPOSITORY_OWNER}/packages/maven/${prod_package}/versions"
        "/users/${REPOSITORY_OWNER}/packages/maven/${prod_package}/versions"
        "/user/packages/maven/${prod_package}/versions"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log "  Testing endpoint: $endpoint"
        
        local status_code
        status_code=$(gh api "$endpoint" --silent --include 2>&1 | head -1 | grep -o 'HTTP/[0-9.]* [0-9]*' | awk '{print $2}' || echo "ERROR")
        
        if [[ "$status_code" == "200" ]]; then
            success "    ✅ SUCCESS ($status_code): $endpoint"
            
            # Get package info
            local package_count
            package_count=$(gh api "$endpoint" --jq 'length' 2>/dev/null || echo "0")
            log "    📦 Found $package_count versions"
            
            # Show first few versions
            if [[ "$package_count" -gt 0 ]]; then
                log "    🔍 Sample versions:"
                gh api "$endpoint" --jq '.[:3] | .[] | "      - ID: \(.id), Name: \(.name), Created: \(.created_at)"' 2>/dev/null || log "      Failed to get version details"
            fi
        elif [[ "$status_code" == "404" ]]; then
            warning "    ❌ NOT FOUND ($status_code): $endpoint"
        elif [[ "$status_code" == "403" ]]; then
            error "    ❌ FORBIDDEN ($status_code): $endpoint - Check permissions"
        else
            error "    ❌ ERROR ($status_code): $endpoint"
        fi
    done
    log ""
}

# Function to list all packages for the repository owner
list_all_packages() {
    log "📋 Listing all packages for repository owner: $REPOSITORY_OWNER"
    
    # List organization packages
    log "  Checking organization packages..."
    local org_status
    org_status=$(gh api "/orgs/${REPOSITORY_OWNER}/packages" --silent --include 2>&1 | head -1 | grep -o 'HTTP/[0-9.]* [0-9]*' | awk '{print $2}' || echo "ERROR")
    
    if [[ "$org_status" == "200" ]]; then
        success "    ✅ Organization packages accessible"
        local org_count
        org_count=$(gh api "/orgs/${REPOSITORY_OWNER}/packages" --jq 'length' 2>/dev/null || echo "0")
        log "    📦 Found $org_count packages in organization"
        
        if [[ "$org_count" -gt 0 ]]; then
            log "    🔍 Organization packages:"
            gh api "/orgs/${REPOSITORY_OWNER}/packages" --jq '.[] | "      - \(.name) (\(.package_type)) - \(.visibility)"' 2>/dev/null || log "      Failed to get package details"
        fi
    else
        warning "    ❌ Organization packages not accessible ($org_status)"
    fi
    
    # List user packages
    log "  Checking user packages..."
    local user_status
    user_status=$(gh api "/users/${REPOSITORY_OWNER}/packages" --silent --include 2>&1 | head -1 | grep -o 'HTTP/[0-9.]* [0-9]*' | awk '{print $2}' || echo "ERROR")
    
    if [[ "$user_status" == "200" ]]; then
        success "    ✅ User packages accessible"
        local user_count
        user_count=$(gh api "/users/${REPOSITORY_OWNER}/packages" --jq 'length' 2>/dev/null || echo "0")
        log "    📦 Found $user_count packages for user"
        
        if [[ "$user_count" -gt 0 ]]; then
            log "    🔍 User packages:"
            gh api "/users/${REPOSITORY_OWNER}/packages" --jq '.[] | "      - \(.name) (\(.package_type)) - \(.visibility)"' 2>/dev/null || log "      Failed to get package details"
        fi
    else
        warning "    ❌ User packages not accessible ($user_status)"
    fi
    
    log ""
}

# Function to test the exact URLs from the current script
test_current_script_urls() {
    log "🔍 Testing exact URLs from current cleanup script..."
    
    # From the Docker cleanup function - line 237
    local docker_packages=("webauthn-server" "webauthn-test-credentials-service")
    
    for package in "${docker_packages[@]}"; do
        local endpoint="/orgs/${REPOSITORY_OWNER}/packages/container/${package}/versions"
        log "Testing Docker endpoint from script: $endpoint"
        
        local response
        if response=$(gh api "$endpoint" 2>&1); then
            success "    ✅ SUCCESS: $endpoint"
            local count
            count=$(echo "$response" | jq 'length' 2>/dev/null || echo "0")
            log "    📦 Found $count versions"
        else
            error "    ❌ FAILED: $endpoint"
            log "    📋 Error details: $response"
        fi
    done
    
    log ""
}

# Main execution
main() {
    log "🚀 GitHub Packages API Debug Script Starting"
    log "Repository: hitoshura25/mpo-api-authn-server"
    log "Repository owner: $REPOSITORY_OWNER"
    log ""
    
    # Load configuration and validate setup
    load_config
    validate_github_cli
    
    log "=" | head -c 80; echo ""
    
    # Test different package types
    list_all_packages
    test_current_script_urls
    test_docker_endpoints
    test_npm_endpoints
    test_maven_endpoints
    
    log "=" | head -c 80; echo ""
    success "Debug script completed"
    log ""
    log "🔧 NEXT STEPS:"
    log "  1. Review the successful endpoints above"
    log "  2. Update cleanup script to use working endpoints"
    log "  3. Check package naming patterns against actual packages"
    log "  4. Verify GitHub token has correct permissions (read:packages, write:packages)"
}

# Run main function
main "$@"