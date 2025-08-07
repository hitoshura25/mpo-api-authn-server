#!/bin/bash
#
# Security Changes Analyzer
#
# This script analyzes the security impact of PR changes by categorizing
# changed files and determining the overall risk level for the PR.
# It's specifically designed for WebAuthn authentication systems.
#
# USAGE:
#   ./analyze-changes.sh
#   (Uses GitHub Actions environment variables and tj-actions/changed-files outputs)
#
# INPUTS (Environment Variables):
#   - AUTH_FLOWS_FILES - Space-separated list of authentication flow files
#   - SECURITY_COMPONENTS_FILES - Space-separated list of security component files 
#   - SECURITY_TESTS_FILES - Space-separated list of security test files
#   - DEPENDENCIES_FILES - Space-separated list of dependency files
#   - INFRASTRUCTURE_FILES - Space-separated list of infrastructure files
#   - ALL_CHANGED_FILES - Space-separated list of all changed files
#
# OUTPUTS (GitHub Actions):
#   - has-auth-changes: true/false
#   - has-security-changes: true/false  
#   - has-dependency-changes: true/false
#   - has-infrastructure-changes: true/false
#   - security-risk-level: HIGH/MEDIUM/LOW/MINIMAL
#   - changed-files-json: JSON array of all changed files
#
# RISK ASSESSMENT LOGIC:
#   - HIGH: >5 security changes OR any dependency changes
#   - MEDIUM: >2 security changes OR any infrastructure changes
#   - LOW: Any security changes
#   - MINIMAL: No security-related changes
#
# EXIT CODES:
#   0 - Analysis completed successfully
#   1 - Analysis failed due to missing inputs or errors
#

set -euo pipefail

# Function to log with timestamp and appropriate formatting
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Function to validate required environment variables
validate_inputs() {
    log "🔍 Validating input environment variables..."
    
    # Check for GitHub Actions environment
    if [ -z "${GITHUB_OUTPUT:-}" ]; then
        log "❌ Error: GITHUB_OUTPUT not set - running outside GitHub Actions?"
        return 1
    fi
    
    # The file list variables might be empty (no changes in that category)
    # but they should at least be defined
    local required_vars=(
        "AUTH_FLOWS_FILES"
        "SECURITY_COMPONENTS_FILES" 
        "SECURITY_TESTS_FILES"
        "DEPENDENCIES_FILES"
        "INFRASTRUCTURE_FILES"
        "ALL_CHANGED_FILES"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var+x}" ]; then
            log "❌ Error: Required environment variable $var is not set"
            return 1
        fi
    done
    
    log "✅ Input validation completed"
    
    # Debug logging for environment variables
    log "🔍 Debug - Environment variables:"
    log "  AUTH_FLOWS_FILES='${AUTH_FLOWS_FILES:-}'"
    log "  SECURITY_COMPONENTS_FILES='${SECURITY_COMPONENTS_FILES:-}'"
    log "  SECURITY_TESTS_FILES='${SECURITY_TESTS_FILES:-}'"
    log "  DEPENDENCIES_FILES='${DEPENDENCIES_FILES:-}'"
    log "  INFRASTRUCTURE_FILES='${INFRASTRUCTURE_FILES:-}'"
    log "  ALL_CHANGED_FILES='${ALL_CHANGED_FILES:-}'"
    
    return 0
}

# Function to count words in a space-separated string
count_changes() {
    local file_list="$1"
    echo "$file_list" | wc -w
}

# Function to analyze security impact based on change counts
analyze_security_impact() {
    log "📊 Analyzing security impact of changes..."
    
    # Count changes by category
    local auth_changes security_changes test_changes dependency_changes infra_changes
    auth_changes=$(count_changes "$AUTH_FLOWS_FILES")
    security_changes=$(count_changes "$SECURITY_COMPONENTS_FILES")
    test_changes=$(count_changes "$SECURITY_TESTS_FILES")
    dependency_changes=$(count_changes "$DEPENDENCIES_FILES")
    infra_changes=$(count_changes "$INFRASTRUCTURE_FILES")
    
    # Debug logging for troubleshooting
    log "🔍 Debug - Change counts:"
    log "  auth_changes='$auth_changes'"
    log "  security_changes='$security_changes'"
    log "  test_changes='$test_changes'"
    log "  dependency_changes='$dependency_changes'"
    log "  infra_changes='$infra_changes'"
    
    log "📈 Change Analysis Summary:"
    log "  Authentication flows: $auth_changes files"
    log "  Security components: $security_changes files" 
    log "  Security tests: $test_changes files"
    log "  Dependencies: $dependency_changes files"
    log "  Infrastructure: $infra_changes files"
    
    # Calculate total security-sensitive changes
    local total_security_changes
    total_security_changes=$((auth_changes + security_changes))
    
    # Determine risk level using WebAuthn-specific thresholds
    local risk_level
    if [ "$total_security_changes" -gt 5 ] || [ "$dependency_changes" -gt 0 ]; then
        risk_level="HIGH"
        log "🚨 HIGH RISK: Major security changes or dependency updates detected"
    elif [ "$total_security_changes" -gt 2 ] || [ "$infra_changes" -gt 0 ]; then
        risk_level="MEDIUM"
        log "⚠️ MEDIUM RISK: Moderate security changes or infrastructure updates"
    elif [ "$total_security_changes" -gt 0 ]; then
        risk_level="LOW"
        log "🔍 LOW RISK: Minor security changes detected"
    else
        risk_level="MINIMAL"
        log "✅ MINIMAL RISK: No security-sensitive changes"
    fi
    
    log "🎯 Final Security Risk Assessment: $risk_level"
    
    # Set GitHub Actions outputs
    set_github_outputs "$auth_changes" "$security_changes" "$dependency_changes" "$infra_changes" "$risk_level"
}

# Function to set GitHub Actions outputs
set_github_outputs() {
    local auth_changes="$1"
    local security_changes="$2" 
    local dependency_changes="$3"
    local infra_changes="$4"
    local risk_level="$5"
    
    log "📤 Setting GitHub Actions outputs..."
    
    # Validate GITHUB_OUTPUT is writable
    if [ ! -w "$GITHUB_OUTPUT" ]; then
        log "❌ Error: GITHUB_OUTPUT file is not writable: $GITHUB_OUTPUT"
        return 1
    fi
    
    # Set boolean outputs based on change counts (using explicit conditionals to avoid command substitution issues)
    local has_auth_changes="false"
    local has_security_changes="false"
    local has_dependency_changes="false"
    local has_infrastructure_changes="false"
    
    # Set boolean values explicitly
    if [ "${auth_changes:-0}" -gt 0 ]; then
        has_auth_changes="true"
    fi
    
    if [ "${security_changes:-0}" -gt 0 ]; then
        has_security_changes="true"
    fi
    
    if [ "${dependency_changes:-0}" -gt 0 ]; then
        has_dependency_changes="true"
    fi
    
    if [ "${infra_changes:-0}" -gt 0 ]; then
        has_infrastructure_changes="true"
    fi
    
    # Write outputs to GitHub Actions
    {
        echo "has-auth-changes=$has_auth_changes"
        echo "has-security-changes=$has_security_changes"
        echo "has-dependency-changes=$has_dependency_changes"
        echo "has-infrastructure-changes=$has_infrastructure_changes"
        echo "security-risk-level=${risk_level:-MINIMAL}"
    } >> "$GITHUB_OUTPUT"
    
    # Create JSON array of all changed files for AI analysis
    # This requires proper JSON escaping and formatting
    create_changed_files_json
    
    log "✅ GitHub Actions outputs set successfully"
}

# Function to create properly formatted JSON array of changed files
create_changed_files_json() {
    log "📝 Creating JSON array of changed files..."
    
    # Convert space-separated files to JSON array using jq
    # This ensures proper JSON escaping of file paths
    local changed_files_json=""
    if command -v jq &> /dev/null; then
        # Use jq for robust JSON formatting
        if [ -n "$ALL_CHANGED_FILES" ]; then
            changed_files_json=$(echo "$ALL_CHANGED_FILES" | tr ' ' '\n' | jq -R . | jq -s .)
        else
            changed_files_json="[]"
        fi
    else
        # Fallback to basic JSON formatting if jq is not available
        log "⚠️ jq not available, using basic JSON formatting"
        if [ -n "$ALL_CHANGED_FILES" ]; then
            local files_array="["
            local first=true
            for file in $ALL_CHANGED_FILES; do
                if [ "$first" = true ]; then
                    first=false
                else
                    files_array+=","
                fi
                # Basic escaping for JSON (not comprehensive but better than nothing)
                local escaped_file
                escaped_file=$(echo "$file" | sed 's/\\/\\\\/g; s/"/\\"/g')
                files_array+="\"$escaped_file\""
            done
            files_array+="]"
            changed_files_json="$files_array"
        else
            changed_files_json="[]"
        fi
    fi
    
    # Write JSON output with proper validation
    if [ -n "$changed_files_json" ]; then
        echo "changed-files-json=$changed_files_json" >> "$GITHUB_OUTPUT"
    else
        echo "changed-files-json=[]" >> "$GITHUB_OUTPUT"
    fi
    
    local file_count
    file_count=$(echo "$ALL_CHANGED_FILES" | wc -w)
    log "✅ Created JSON array for $file_count changed files"
}

# Function to log security context for debugging
log_security_context() {
    log "🔐 WebAuthn Security Analysis Context:"
    log "  This analysis focuses on WebAuthn-specific security patterns"
    log "  Key areas of concern:"
    log "    - Authentication flow modifications"
    log "    - Credential handling changes"
    log "    - Origin validation updates"
    log "    - Security test coverage"
    log "    - Dependency vulnerabilities"
    log "  Risk thresholds tuned for authentication system criticality"
}

# Main execution function
main() {
    log "🚀 Security Changes Analyzer Starting"
    log_security_context
    
    # Validate inputs
    if ! validate_inputs; then
        log "❌ Input validation failed"
        exit 1
    fi
    
    # Analyze security impact
    analyze_security_impact
    
    log "✅ Security changes analysis completed successfully"
}

# Error handling with context
trap 'log "❌ Script failed at line $LINENO with exit code $?"' ERR

# Execute main function
main "$@"