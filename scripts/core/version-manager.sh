#!/bin/bash

# Version Manager Script
# Generates synchronized versions for both Android and npm clients

set -euo pipefail

# Configuration
BASE_VERSION="${BASE_VERSION:-1.0}"
BUILD_NUMBER="${GITHUB_RUN_NUMBER:-1}"
EVENT_NAME="${GITHUB_EVENT_NAME:-push}"
REF_NAME="${GITHUB_REF_NAME:-main}"
GITHUB_PR_NUMBER="${GITHUB_PR_NUMBER:-}"


# Get version continuity from existing git tags
get_next_build_number() {
    echo "🔍 Checking existing client library tags for version continuity..." >&2
    
    # Get the highest existing version from git tags to ensure continuity
    local highest_npm_tag highest_android_tag highest_version
    
    highest_npm_tag=$(git tag -l "npm-client-v*" 2>/dev/null | sed 's/npm-client-v//' | sort -V | tail -1 || echo "")
    highest_android_tag=$(git tag -l "android-client-v*" 2>/dev/null | sed 's/android-client-v//' | sort -V | tail -1 || echo "")
    
    # Find the highest version between npm and android tags
    if [[ -n "$highest_npm_tag" && -n "$highest_android_tag" ]]; then
        highest_version=$(printf '%s\n%s' "$highest_npm_tag" "$highest_android_tag" | sort -V | tail -1)
    elif [[ -n "$highest_npm_tag" ]]; then
        highest_version="$highest_npm_tag"
    elif [[ -n "$highest_android_tag" ]]; then
        highest_version="$highest_android_tag"
    else
        highest_version=""
    fi
    
    if [[ -n "$highest_version" ]]; then
        # Extract build number and increment (e.g., 1.0.32 -> 33)
        local current_build next_build
        current_build=$(echo "$highest_version" | cut -d. -f3)
        next_build=$((current_build + 1))
        echo "📈 Highest existing client version: $highest_version, using next build: $next_build" >&2
        echo "$next_build"
    else
        # No existing client tags, use provided build number
        echo "🆕 No existing client tags found, starting with build: $BUILD_NUMBER" >&2
        echo "$BUILD_NUMBER"
    fi
}

# Generate version based on event type and branch
generate_version() {
    local version
    local is_prerelease
    local actual_build_number
    
    # Get the actual build number (may be adjusted for continuity)
    actual_build_number=$(get_next_build_number)
    
    case "$EVENT_NAME" in
        "push")
            if [[ "$REF_NAME" == "main" ]]; then
                # Main branch: patch version increment with build number
                # Convert 1.0 + build 26 → 1.0.26 (npm-safe 3-part version)
                version="${BASE_VERSION}.${actual_build_number}"
                is_prerelease="false"
                echo "📦 Main branch release: $version" >&2
            else
                # Other branches (shouldn't happen with current config, but defensive)
                branch_name=$(echo "$REF_NAME" | sed 's/[^a-zA-Z0-9]//g' | tr '[:upper:]' '[:lower:]')
                version="${BASE_VERSION}.0-${branch_name}.${actual_build_number}"
                is_prerelease="true"
                echo "🌿 Branch release: $version" >&2
            fi
            ;;
        "pull_request")
            # PR: prerelease version based on next build number + PR and run identifiers
            # Use next build number (e.g., if latest is 1.0.35, use 1.0.36-pr.42.123)
            pr_number="${GITHUB_PR_NUMBER:-unknown}"
            next_build="${BASE_VERSION}.${actual_build_number}"
            version="${next_build}-pr.${pr_number}.${BUILD_NUMBER}"
            is_prerelease="true"
            echo "🔄 PR snapshot release: $version (based on next release ${next_build}, PR #${pr_number}, run ${BUILD_NUMBER})" >&2
            ;;
        "workflow_dispatch")
            # Manual dispatch: branch-aware versioning
            if [[ "$REF_NAME" == "main" ]]; then
                # Main branch manual dispatch: production-style version
                version="${BASE_VERSION}.${actual_build_number}"
                is_prerelease="false"
                echo "🚀 Manual main branch release: $version" >&2
            else
                # Feature branch manual dispatch: prerelease with branch identifier
                branch_name=$(echo "$REF_NAME" | sed 's/[^a-zA-Z0-9]//g' | tr '[:upper:]' '[:lower:]')
                version="${BASE_VERSION}.0-${branch_name}.${BUILD_NUMBER}"
                is_prerelease="true"
                echo "🌿 Manual branch release: $version (branch: $REF_NAME)" >&2
            fi
            ;;
        "workflow_run")
            # Workflow run (e.g., main-branch-post-processing): treat as main branch release
            # This runs after successful main branch CI/CD completion
            version="${BASE_VERSION}.${actual_build_number}"
            is_prerelease="false"
            echo "📦 Post-processing release: $version" >&2
            ;;
        *)
            # Default case
            version="${BASE_VERSION}.0-unknown.${actual_build_number}"
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
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*)?$ ]]; then
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
            echo "  BASE_VERSION: Base version (default: 1.0)" >&2
            echo "  GITHUB_RUN_NUMBER: Build number for versioning" >&2
            echo "  GITHUB_EVENT_NAME: GitHub event type" >&2
            echo "  GITHUB_REF_NAME: Branch name" >&2
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"