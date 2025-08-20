#!/bin/bash
#
# Quick manual deletion test script
# Use this to test the exact deletion command that was failing
#
# USAGE:
#   ./test-delete-version.sh [version_id]
#   Example: ./test-delete-version.sh 490951546
#

set -euo pipefail

VERSION_ID="${1:-}"

if [[ -z "$VERSION_ID" ]]; then
    echo "❌ Error: Version ID required"
    echo "Usage: $0 [version_id]"
    echo "Example: $0 490951546"
    exit 1
fi

# Based on the job output, the exact endpoint that was working
ENDPOINT="/users/hitoshura25/packages/container/webauthn-server"

echo "🧪 Testing manual deletion of Docker package version"
echo "🔍 Version ID: $VERSION_ID"
echo "🔍 Endpoint: $ENDPOINT"
echo ""

# Check authentication
echo "🔍 Checking GitHub CLI authentication..."
if ! gh auth status; then
    echo "❌ GitHub CLI not authenticated"
    exit 1
fi

echo ""
echo "🔍 Testing API access..."
if ! gh api /user >/dev/null 2>&1; then
    echo "❌ GitHub API access failed"
    exit 1
fi

echo "✅ API access confirmed"
echo ""

# Get version details first
echo "🔍 Getting version details..."
if version_details=$(gh api "${ENDPOINT}/versions/${VERSION_ID}" 2>&1); then
    echo "📋 Version found:"
    echo "$version_details" | jq -r '.metadata.container.tags[]' 2>/dev/null | head -5 | sed 's/^/  - /'
    echo ""
else
    echo "❌ Version not found or inaccessible: $version_details"
    exit 1
fi

# Test the deletion
echo "🗑️ Attempting deletion..."
echo "🔍 Command: gh api --method DELETE \"${ENDPOINT}/versions/$VERSION_ID\""
echo ""

if delete_result=$(gh api --method DELETE "${ENDPOINT}/versions/$VERSION_ID" 2>&1); then
    echo "✅ DELETION SUCCESSFUL"
    echo "✅ Response: $delete_result"
    exit 0
else
    echo "❌ DELETION FAILED"
    echo "❌ Error response: $delete_result"
    
    # Analyze the error
    if [[ "$delete_result" =~ "404" ]]; then
        echo "💡 Analysis: Version not found (404)"
    elif [[ "$delete_result" =~ "403" ]]; then
        echo "💡 Analysis: Permission denied (403) - check if token has packages:write permission"
    elif [[ "$delete_result" =~ "401" ]]; then
        echo "💡 Analysis: Unauthorized (401) - authentication issue"
    elif [[ "$delete_result" =~ "422" ]]; then
        echo "💡 Analysis: Unprocessable entity (422) - invalid request"
    else
        echo "💡 Analysis: Unknown error - see response above"
    fi
    
    exit 1
fi