#!/bin/bash
#
# Docker Image Change Detection Script
#
# This script compares Docker image digests between GitHub Container Registry (GHCR)
# and DockerHub to determine if publishing is needed. It handles both webauthn-server
# and webauthn-test-credentials-service images.
#
# USAGE:
#   ./detect-changes.sh <image_type>
#   where image_type is either "webauthn-server" or "test-credentials"
#
# ENVIRONMENT VARIABLES:
#   DOCKER_REGISTRY - Docker registry URL (default: ghcr.io)
#   DOCKER_IMAGE_NAME - GHCR image name for webauthn-server
#   DOCKER_TEST_CREDENTIALS_IMAGE_NAME - GHCR image name for test-credentials
#   DOCKERHUB_SERVER_REPO - DockerHub repository for webauthn-server
#   DOCKERHUB_TEST_CREDENTIALS_REPO - DockerHub repository for test-credentials
#
# OUTPUTS:
#   Sets GitHub Actions outputs:
#   - has-changes: true/false indicating if image has changes
#
# EXIT CODES:
#   0 - Success
#   1 - Error occurred during detection
#

set -euo pipefail

# Default values
DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io}"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Function to check changes for webauthn-server
check_webauthn_server_changes() {
    log "🔍 Checking for changes in WebAuthn Server image..."
    
    # Get GHCR digest
    GHCR_DIGEST=$(docker buildx imagetools inspect "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest" --format '{{.Manifest.Digest}}' 2>/dev/null || echo "")
    
    if [ -z "$GHCR_DIGEST" ]; then
        log "❌ Failed to get GHCR digest for webauthn-server"
        echo "has-changes=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        return 0
    fi
    
    log "GHCR digest: $GHCR_DIGEST"
    
    # Get DockerHub digest (handle case where image doesn't exist yet)
    DOCKERHUB_DIGEST=$(docker buildx imagetools inspect "${DOCKERHUB_SERVER_REPO}:latest" --format '{{.Manifest.Digest}}' 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$DOCKERHUB_DIGEST" = "NOT_FOUND" ]; then
        log "📦 WebAuthn Server image not found on DockerHub - first publish needed"
        echo "has-changes=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    elif [ "$DOCKERHUB_DIGEST" != "$GHCR_DIGEST" ]; then
        log "🔄 WebAuthn Server image has changes"
        log "DockerHub digest: $DOCKERHUB_DIGEST"
        log "GHCR digest: $GHCR_DIGEST"
        echo "has-changes=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    else
        log "✅ WebAuthn Server image unchanged"
        echo "has-changes=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    fi
}

# Function to check changes for test-credentials service
check_test_credentials_changes() {
    log "🔍 Checking for changes in Test Credentials Service image..."
    
    # Get GHCR digest
    GHCR_DIGEST=$(docker buildx imagetools inspect "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}:latest" --format '{{.Manifest.Digest}}' 2>/dev/null || echo "")
    
    if [ -z "$GHCR_DIGEST" ]; then
        log "❌ Failed to get GHCR digest for test-credentials-service"
        echo "has-changes=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        return 0
    fi
    
    log "GHCR digest: $GHCR_DIGEST"
    
    # Get DockerHub digest (handle case where image doesn't exist yet)
    DOCKERHUB_DIGEST=$(docker buildx imagetools inspect "${DOCKERHUB_TEST_CREDENTIALS_REPO}:latest" --format '{{.Manifest.Digest}}' 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$DOCKERHUB_DIGEST" = "NOT_FOUND" ]; then
        log "📦 Test Credentials Service image not found on DockerHub - first publish needed"
        echo "has-changes=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    elif [ "$DOCKERHUB_DIGEST" != "$GHCR_DIGEST" ]; then
        log "🔄 Test Credentials Service image has changes"
        log "DockerHub digest: $DOCKERHUB_DIGEST"
        log "GHCR digest: $GHCR_DIGEST"
        echo "has-changes=true" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    else
        log "✅ Test Credentials Service image unchanged"
        echo "has-changes=false" >> "${GITHUB_OUTPUT:-/dev/stdout}"
    fi
}

# Main execution
main() {
    local image_type="${1:-}"
    
    if [ -z "$image_type" ]; then
        log "❌ Error: Image type not specified"
        log "Usage: $0 <image_type>"
        log "  image_type: 'webauthn-server' or 'test-credentials'"
        exit 1
    fi
    
    # Validate required environment variables
    case "$image_type" in
        "webauthn-server")
            if [ -z "${DOCKER_IMAGE_NAME:-}" ] || [ -z "${DOCKERHUB_SERVER_REPO:-}" ]; then
                log "❌ Error: Missing required environment variables for webauthn-server"
                log "Required: DOCKER_IMAGE_NAME, DOCKERHUB_SERVER_REPO"
                exit 1
            fi
            check_webauthn_server_changes
            ;;
        "test-credentials")
            if [ -z "${DOCKER_TEST_CREDENTIALS_IMAGE_NAME:-}" ] || [ -z "${DOCKERHUB_TEST_CREDENTIALS_REPO:-}" ]; then
                log "❌ Error: Missing required environment variables for test-credentials"
                log "Required: DOCKER_TEST_CREDENTIALS_IMAGE_NAME, DOCKERHUB_TEST_CREDENTIALS_REPO"
                exit 1
            fi
            check_test_credentials_changes
            ;;
        *)
            log "❌ Error: Invalid image type '$image_type'"
            log "Valid types: 'webauthn-server', 'test-credentials'"
            exit 1
            ;;
    esac
}

# Trap errors for better debugging
trap 'log "❌ Script failed at line $LINENO"' ERR

# Run main function with all arguments
main "$@"