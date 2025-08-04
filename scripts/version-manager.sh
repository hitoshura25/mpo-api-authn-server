#!/bin/bash

# Version Manager Script
# Generates synchronized versions for both Android and npm clients

set -euo pipefail

# Configuration
BASE_VERSION="${BASE_VERSION:-1.0.0}"
BUILD_NUMBER="${GITHUB_RUN_NUMBER:-1}"
EVENT_NAME="${GITHUB_EVENT_NAME:-push}"
REF_NAME="${GITHUB_REF_NAME:-main}"
GITHUB_PR_NUMBER="${GITHUB_PR_NUMBER:-}"

# Generate version based on event type and branch
generate_version() {
    local version
    local is_prerelease
    
    case "$EVENT_NAME" in
        "push")
            if [[ "$REF_NAME" == "main" ]]; then
                # Main branch: semantic version with build number
                version="${BASE_VERSION}.${BUILD_NUMBER}"
                is_prerelease="false"
                echo "📦 Main branch release: $version" >&2
            else
                # Other branches (shouldn't happen with current config, but defensive)
                branch_name=$(echo "$REF_NAME" | sed 's/[^a-zA-Z0-9]/-/g' | tr '[:upper:]' '[:lower:]')
                version="${BASE_VERSION}-${branch_name}.${BUILD_NUMBER}"
                is_prerelease="true"
                echo "🌿 Branch release: $version" >&2
            fi
            ;;
        "pull_request")
            # PR: snapshot version with PR number
            pr_number="${GITHUB_PR_NUMBER:-${BUILD_NUMBER}}"
            version="${BASE_VERSION}-pr-${pr_number}.${BUILD_NUMBER}"
            is_prerelease="true"
            echo "🔄 PR snapshot release: $version" >&2
            ;;
        "workflow_dispatch")
            # Manual dispatch: use base version
            version="$BASE_VERSION"
            is_prerelease="false"
            echo "🚀 Manual release: $version" >&2
            ;;
        *)
            # Default case
            version="${BASE_VERSION}-unknown.${BUILD_NUMBER}"
            is_prerelease="true"
            echo "❓ Unknown event release: $version" >&2
            ;;
    esac
    
    echo "Generated version: $version (prerelease: $is_prerelease)" >&2
    
    # Output for GitHub Actions
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "version=$version" >> "$GITHUB_OUTPUT"
        echo "is-prerelease=$is_prerelease" >> "$GITHUB_OUTPUT"
    fi
    
    # Output for shell consumption
    echo "$version"
}

# Validate version format
validate_version() {
    local version="$1"
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?(-[a-zA-Z0-9.-]+)?$ ]]; then
        echo "❌ Invalid version format: $version" >&2
        return 1
    fi
    echo "✅ Valid version format: $version" >&2
}

# Main execution
main() {
    local command="${1:-generate}"
    
    case "$command" in
        "generate")
            local version
            version=$(generate_version)
            validate_version "$version"
            ;;
        "validate")
            local version="${2:-}"
            if [[ -z "$version" ]]; then
                echo "❌ Version required for validation" >&2
                exit 1
            fi
            validate_version "$version"
            ;;
        *)
            echo "Usage: $0 {generate|validate [version]}" >&2
            echo "Environment variables:" >&2
            echo "  BASE_VERSION: Base version (default: 1.0.0)" >&2
            echo "  GITHUB_RUN_NUMBER: Build number for versioning" >&2
            echo "  GITHUB_EVENT_NAME: GitHub event type" >&2
            echo "  GITHUB_REF_NAME: Branch name" >&2
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"