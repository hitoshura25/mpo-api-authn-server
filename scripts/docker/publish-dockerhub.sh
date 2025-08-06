#!/bin/bash
#
# DockerHub Publishing Script
#
# This script publishes Docker images from GitHub Container Registry (GHCR) to DockerHub.
# It handles both webauthn-server and webauthn-test-credentials-service images with
# conditional publishing based on change detection.
#
# USAGE:
#   ./publish-dockerhub.sh <webauthn_changed> <test_credentials_changed>
#   where parameters are "true" or "false"
#
# ENVIRONMENT VARIABLES:
#   DOCKER_REGISTRY - Docker registry URL
#   DOCKER_IMAGE_NAME - GHCR image name for webauthn-server
#   DOCKER_TEST_CREDENTIALS_IMAGE_NAME - GHCR image name for test-credentials
#   DOCKERHUB_SERVER_REPO - DockerHub repository for webauthn-server
#   DOCKERHUB_TEST_CREDENTIALS_REPO - DockerHub repository for test-credentials
#
# AUTHENTICATION:
#   Assumes Docker login to both GHCR and DockerHub has already been performed.
#
# EXIT CODES:
#   0 - Success
#   1 - Error occurred during publishing
#

set -euo pipefail

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Function to publish WebAuthn Server to DockerHub
publish_webauthn_server() {
    log "🚀 Publishing WebAuthn Server to DockerHub..."
    
    # Pull from GHCR
    docker pull "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest"
    
    # Tag for DockerHub
    docker tag "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest" "${DOCKERHUB_SERVER_REPO}:latest"
    
    # Push to DockerHub
    docker push "${DOCKERHUB_SERVER_REPO}:latest"
    
    log "✅ WebAuthn Server successfully published to DockerHub"
}

# Function to publish Test Credentials Service to DockerHub
publish_test_credentials() {
    log "🚀 Publishing Test Credentials Service to DockerHub..."
    
    # Pull from GHCR
    docker pull "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}:latest"
    
    # Tag for DockerHub
    docker tag "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}:latest" "${DOCKERHUB_TEST_CREDENTIALS_REPO}:latest"
    
    # Push to DockerHub
    docker push "${DOCKERHUB_TEST_CREDENTIALS_REPO}:latest"
    
    log "✅ Test Credentials Service successfully published to DockerHub"
}

# Function to update DockerHub repository description
update_dockerhub_description() {
    local repo="$1"
    local description="$2"
    local readme_file="$3"
    
    log "📝 Updating DockerHub description for $repo..."
    
    # This would typically use peter-evans/dockerhub-description action in GitHub Actions
    # For standalone usage, this is a placeholder for manual description updates
    if [ -f "$readme_file" ]; then
        log "ℹ️ README file found: $readme_file"
        log "ℹ️ Description: $description"
        log "⚠️ DockerHub description update requires peter-evans/dockerhub-description action in CI/CD"
    else
        log "⚠️ README file not found: $readme_file"
    fi
}

# Main execution
main() {
    local webauthn_changed="${1:-false}"
    local test_credentials_changed="${2:-false}"
    
    # Validate required environment variables
    local required_vars=(
        "DOCKER_REGISTRY"
        "DOCKER_IMAGE_NAME"
        "DOCKER_TEST_CREDENTIALS_IMAGE_NAME"
        "DOCKERHUB_SERVER_REPO"
        "DOCKERHUB_TEST_CREDENTIALS_REPO"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log "❌ Error: Missing required environment variable: $var"
            exit 1
        fi
    done
    
    # Check if any images need publishing
    if [[ "$webauthn_changed" != "true" ]] && [[ "$test_credentials_changed" != "true" ]]; then
        log "ℹ️ No images changed - skipping DockerHub publishing"
        exit 0
    fi
    
    local published_images=()
    
    # Publish WebAuthn Server if changed
    if [[ "$webauthn_changed" == "true" ]]; then
        publish_webauthn_server
        published_images+=("${DOCKERHUB_SERVER_REPO}:latest")
        
        # Update DockerHub description
        update_dockerhub_description \
            "$DOCKERHUB_SERVER_REPO" \
            "WebAuthn authentication server built with Ktor and Yubico java-webauthn-server" \
            "./webauthn-server/README.md"
    fi
    
    # Publish Test Credentials Service if changed
    if [[ "$test_credentials_changed" == "true" ]]; then
        publish_test_credentials
        published_images+=("${DOCKERHUB_TEST_CREDENTIALS_REPO}:latest")
        
        # Update DockerHub description
        update_dockerhub_description \
            "$DOCKERHUB_TEST_CREDENTIALS_REPO" \
            "WebAuthn test credentials service for cross-platform testing with FIDO2/WebAuthn" \
            "./webauthn-test-credentials-service/README.md"
    fi
    
    # Summary
    log "🎉 DockerHub publishing completed successfully!"
    log "Published images:"
    for image in "${published_images[@]}"; do
        log "  - $image"
    done
}

# Trap errors for better debugging
trap 'log "❌ Script failed at line $LINENO"' ERR

# Run main function with all arguments
main "$@"