#!/bin/bash
#
# Enhanced Vulnerability Monitoring Script
#
# This script performs AI-enhanced vulnerability monitoring for WebAuthn security issues.
# It attempts AI-enhanced monitoring first, then falls back to standard monitoring if needed.
#
# USAGE:
#   ./enhanced-monitor.sh
#
# ENVIRONMENT VARIABLES:
#   ANTHROPIC_API_KEY - API key for AI enhancement (optional)
#   GH_TOKEN - GitHub token for API access
#
# OUTPUTS:
#   - monitor-output.txt - Monitoring results and logs
#   - Updated vulnerability tracking and test files
#   - GitHub Actions outputs:
#     - no_changes: true/false indicating if files were modified
#
# EXIT CODES:
#   0 - Monitoring completed successfully
#   1 - Monitoring failed
#

set -euo pipefail

# Function to log with timestamp
log() {
    local message="$(date '+%Y-%m-%d %H:%M:%S') - $*"
    echo "$message"
    echo "$message" >> monitor-output.txt
}

# Function to check if AI-enhanced monitoring is available
check_ai_availability() {
    local ai_available=false
    
    if [ -n "${ANTHROPIC_API_KEY:-}" ] && [ -f "scripts/ai-enhanced-vulnerability-monitor.js" ]; then
        log "✅ AI enhancement available"
        ai_available=true
    else
        log "⚠️ AI enhancement not available"
        if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
            log "  - ANTHROPIC_API_KEY not set"
        fi
        if [ ! -f "scripts/ai-enhanced-vulnerability-monitor.js" ]; then
            log "  - AI monitor script not found"
        fi
    fi
    
    echo "$ai_available"
}

# Function to run AI-enhanced monitoring
run_ai_enhanced_monitoring() {
    log "🤖 Running AI-enhanced vulnerability monitoring..."
    
    if node scripts/ai-enhanced-vulnerability-monitor.js 2>&1; then
        log "✅ AI-enhanced monitoring completed successfully"
        return 0
    else
        log "❌ AI-enhanced monitoring failed"
        return 1
    fi
}

# Function to run standard monitoring
run_standard_monitoring() {
    log "⚠️ Running standard vulnerability monitoring..."
    
    if node scripts/vulnerability-monitor.js 2>&1; then
        log "✅ Standard monitoring completed successfully"
        return 0
    else
        log "❌ Standard monitoring failed"
        return 1
    fi
}

# Function to check if files were modified
check_for_changes() {
    log "🔍 Checking for file modifications..."
    
    if git diff --quiet; then
        log "✅ No changes detected"
        if [ -n "${GITHUB_OUTPUT:-}" ]; then
            echo "no_changes=true" >> "$GITHUB_OUTPUT"
        fi
        return 0
    else
        log "🔄 Changes detected in the following files:"
        git diff --name-only | while read -r file; do
            log "  - $file"
        done
        if [ -n "${GITHUB_OUTPUT:-}" ]; then
            echo "no_changes=false" >> "$GITHUB_OUTPUT"
        fi
        return 1
    fi
}

# Function to run security tests if changes were made
run_security_tests() {
    log "🧪 Running security tests to verify changes..."
    
    if ./gradlew test --tests="*VulnerabilityProtectionTest*" 2>&1; then
        log "✅ Security tests passed"
        return 0
    else
        log "❌ Security tests failed"
        return 1
    fi
}

# Function to prepare monitoring environment
prepare_environment() {
    log "📦 Preparing monitoring environment..."
    
    # Initialize output file
    echo "WebAuthn Vulnerability Monitor - $(date)" > monitor-output.txt
    echo "=======================================" >> monitor-output.txt
    
    # Check if npm dependencies are available
    if [ ! -d "node_modules" ]; then
        log "📦 Installing npm dependencies..."
        if npm install 2>&1; then
            log "✅ Dependencies installed"
        else
            log "❌ Failed to install dependencies"
            return 1
        fi
    fi
    
    # Check if required scripts exist
    if [ ! -f "scripts/vulnerability-monitor.js" ]; then
        log "❌ Required script not found: scripts/vulnerability-monitor.js"
        return 1
    fi
    
    log "✅ Environment prepared"
    return 0
}

# Function to generate monitoring summary
generate_summary() {
    local monitoring_success="$1"
    local changes_detected="$2"
    local tests_passed="$3"
    
    log "📊 Vulnerability Monitoring Summary"
    log "=================================="
    log "Monitoring Status: $([ "$monitoring_success" = true ] && echo "✅ Success" || echo "❌ Failed")"
    log "Changes Detected: $([ "$changes_detected" = true ] && echo "🔄 Yes" || echo "✅ No")"
    
    if [ "$changes_detected" = true ]; then
        log "Security Tests: $([ "$tests_passed" = true ] && echo "✅ Passed" || echo "❌ Failed")"
        
        # List modified files
        log ""
        log "📝 Modified Files:"
        git diff --name-only | while read -r file; do
            log "  - $file"
        done
    fi
    
    log ""
    log "🕐 Monitoring completed at $(date)"
}

# Main execution
main() {
    log "🚀 Enhanced Vulnerability Monitoring Starting"
    log "============================================="
    
    # Prepare environment
    if ! prepare_environment; then
        log "❌ Failed to prepare monitoring environment"
        exit 1
    fi
    
    # Check AI availability
    local ai_available
    ai_available=$(check_ai_availability)
    
    # Run monitoring (AI-enhanced or standard)
    local monitoring_success=false
    if [ "$ai_available" = true ]; then
        if run_ai_enhanced_monitoring; then
            monitoring_success=true
        else
            log "⚠️ AI-enhanced monitoring failed, falling back to standard monitoring"
            if run_standard_monitoring; then
                monitoring_success=true
            fi
        fi
    else
        if run_standard_monitoring; then
            monitoring_success=true
        fi
    fi
    
    # Check for changes
    local changes_detected=false
    if ! check_for_changes; then
        changes_detected=true
    fi
    
    # Run security tests if changes were detected
    local tests_passed=false
    if [ "$changes_detected" = true ]; then
        if [ "$monitoring_success" = true ]; then
            if run_security_tests; then
                tests_passed=true
            fi
        else
            log "⚠️ Skipping security tests due to monitoring failure"
        fi
    fi
    
    # Generate summary
    generate_summary "$monitoring_success" "$changes_detected" "$tests_passed"
    
    # Determine exit code
    if [ "$monitoring_success" = true ]; then
        if [ "$changes_detected" = false ] || [ "$tests_passed" = true ]; then
            log "🎉 Vulnerability monitoring completed successfully"
            exit 0
        else
            log "❌ Vulnerability monitoring completed but security tests failed"
            exit 1
        fi
    else
        log "❌ Vulnerability monitoring failed"
        exit 1
    fi
}

# Trap errors for better debugging
trap 'log "❌ Script failed at line $LINENO"' ERR

# Create output directory if it doesn't exist
mkdir -p "$(dirname "monitor-output.txt")"

# Run main function
main "$@" 2>&1 | tee -a monitor-output.txt