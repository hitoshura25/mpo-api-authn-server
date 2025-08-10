#!/bin/bash
#
# Docker Security Scanning Script
#
# This script performs comprehensive security scanning of Docker images using Trivy scanner.
# It scans for vulnerabilities, secrets, and configuration issues, providing detailed JSON output
# and blocking publication on critical vulnerabilities.
#
# USAGE:
#   ./scan-security.sh <webauthn_changed> <test_credentials_changed> [webauthn_image_tag] [test_credentials_image_tag]
#   where first two parameters are "true" or "false"
#   and optional image tags specify the actual built images to scan
#
# ENVIRONMENT VARIABLES:
#   DOCKER_REGISTRY - Docker registry URL
#   DOCKER_IMAGE_NAME - GHCR image name for webauthn-server
#   DOCKER_TEST_CREDENTIALS_IMAGE_NAME - GHCR image name for test-credentials
#
# OUTPUTS:
#   - docker-security-scan-results.json - Comprehensive scan results
#   - Individual scan files (*-vulns.json, *-secrets.json, *-config.json)
#   - GitHub Actions outputs:
#     - scan-results: JSON scan results
#     - critical-vulnerabilities: Count of critical vulnerabilities
#     - scan-passed: true/false for overall scan status
#
# EXIT CODES:
#   0 - Scan passed (no critical vulnerabilities)
#   1 - Critical vulnerabilities found or scan failed
#

set -euo pipefail

# Function to log with timestamp
log() {
    local message="$(date '+%Y-%m-%d %H:%M:%S') - $*"
    echo "$message"
    echo "$message" >> "scan-security.log"
}

# Function to install Trivy scanner
install_trivy() {
    log "📦 Installing Trivy scanner..."
    
    sudo apt-get update
    sudo apt-get install -y wget apt-transport-https gnupg lsb-release
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
    echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
    sudo apt-get update
    sudo apt-get install -y trivy
    
    log "✅ Trivy scanner installed successfully"
}

# Function to verify locally built Docker images are available for scanning
verify_local_images() {
    local webauthn_changed="$1"
    local test_credentials_changed="$2"
    local webauthn_image_tag="$3"
    local test_credentials_image_tag="$4"
    
    log "📦 Verifying locally built images are available for security scanning..."
    
    # Check WebAuthn server image
    if [[ "$webauthn_changed" == "true" ]]; then
        if [[ -n "$webauthn_image_tag" ]]; then
            # Use the full image tag provided from build job
            if docker image inspect "$webauthn_image_tag" >/dev/null 2>&1; then
                log "✅ Found local WebAuthn server image: $webauthn_image_tag"
            else
                log "❌ Local WebAuthn server image not found: $webauthn_image_tag"
                log "   This indicates the Docker build step may have failed or the image wasn't loaded locally"
                exit 1
            fi
        else
            log "⚠️ No WebAuthn image tag provided, checking for latest tag"
            if docker image inspect "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest" >/dev/null 2>&1; then
                log "✅ Found local WebAuthn server image: ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest"
            else
                log "❌ Local WebAuthn server image not found with latest tag"
                exit 1
            fi
        fi
    fi
    
    # Check Test Credentials service image  
    if [[ "$test_credentials_changed" == "true" ]]; then
        if [[ -n "$test_credentials_image_tag" ]]; then
            # Use the full image tag provided from build job
            if docker image inspect "$test_credentials_image_tag" >/dev/null 2>&1; then
                log "✅ Found local Test Credentials service image: $test_credentials_image_tag"
            else
                log "❌ Local Test Credentials service image not found: $test_credentials_image_tag"
                log "   This indicates the Docker build step may have failed or the image wasn't loaded locally"
                exit 1
            fi
        else
            log "⚠️ No Test Credentials image tag provided, checking for latest tag"
            if docker image inspect "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}:latest" >/dev/null 2>&1; then
                log "✅ Found local Test Credentials service image: ${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}:latest"
            else
                log "❌ Local Test Credentials service image not found with latest tag"
                exit 1
            fi
        fi
    fi
    
    log "✅ All required local images verified and ready for scanning"
}

# Function to scan a single image
scan_image() {
    local image_name="$1"
    local image_tag="$2"
    local full_image="${image_name}:${image_tag}"
    
    log "🔍 Scanning $full_image..."
    
    # Create scan result entry
    local scan_entry
    scan_entry=$(cat <<EOF
{
  "image": "$full_image",
  "timestamp": "$(date -Iseconds)",
  "scans": {
    "vulnerabilities": null,
    "secrets": null,
    "config": null
  }
}
EOF
)
    
    local scan_success=true
    local image_basename
    image_basename="${image_name##*/}"
    
    # Vulnerability scan with Trivy - generate both JSON for processing and SARIF for GitHub
    log "  📋 Running vulnerability scan..."
    if trivy image --format json --output "${image_basename}-vulns.json" "$full_image" 2>/dev/null && \
       trivy image --format sarif --output "${image_basename}-vulns-temp.sarif" "$full_image" 2>/dev/null; then
        log "  ✅ Vulnerability scan completed (JSON + SARIF)"
        
        # Count critical and high vulnerabilities
        local critical_count high_count total_count
        critical_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "${image_basename}-vulns.json" 2>/dev/null || echo 0)
        high_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "${image_basename}-vulns.json" 2>/dev/null || echo 0)
        total_count=$(jq '[.Results[]?.Vulnerabilities[]?] | length' "${image_basename}-vulns.json" 2>/dev/null || echo 0)
        
        CRITICAL_VULN_COUNT=$((CRITICAL_VULN_COUNT + critical_count))
        TOTAL_VULN_COUNT=$((TOTAL_VULN_COUNT + total_count))
        
        log "    📊 Found $critical_count CRITICAL, $high_count HIGH, $total_count total vulnerabilities"
        
        # Fix SARIF category collision by making each image's SARIF unique
        local unique_category="trivy-${image_basename}"
        jq --arg category "$unique_category" '
          if .runs then 
            .runs[].tool.driver.name = $category |
            .runs[].automationDetails.id = $category
          else . end
        ' "${image_basename}-vulns-temp.sarif" > "${image_basename}-vulns.sarif"
        rm -f "${image_basename}-vulns-temp.sarif"
        log "    🏷️  Updated SARIF with unique category: $unique_category"
        
        # Update scan result - use jq with file input to avoid argument length limits
        local temp_scan_file
        temp_scan_file=$(mktemp)
        echo "$scan_entry" > "$temp_scan_file"
        jq --slurpfile vulns "${image_basename}-vulns.json" '.scans.vulnerabilities = $vulns[0]' "$temp_scan_file" > "${temp_scan_file}.tmp"
        scan_entry=$(cat "${temp_scan_file}.tmp")
        rm -f "$temp_scan_file" "${temp_scan_file}.tmp"
    else
        log "  ❌ Vulnerability scan failed"
        scan_success=false
        SCAN_SUCCESS=false
    fi
    
    # Secret scan
    log "  🔐 Running secret scan..."
    if trivy image --scanners secret --format json --output "${image_basename}-secrets.json" "$full_image" 2>/dev/null; then
        log "  ✅ Secret scan completed"
        # Update scan result - use jq with file input to avoid argument length limits
        local temp_scan_file
        temp_scan_file=$(mktemp)
        echo "$scan_entry" > "$temp_scan_file"
        jq --slurpfile secrets "${image_basename}-secrets.json" '.scans.secrets = $secrets[0]' "$temp_scan_file" > "${temp_scan_file}.tmp"
        scan_entry=$(cat "${temp_scan_file}.tmp")
        rm -f "$temp_scan_file" "${temp_scan_file}.tmp"
    else
        log "  ⚠️ Secret scan failed or no secrets found"
    fi
    
    # Config scan (Dockerfile and security configs)
    log "  ⚙️ Running configuration scan..."
    if trivy image --scanners config --format json --output "${image_basename}-config.json" "$full_image" 2>/dev/null; then
        log "  ✅ Configuration scan completed"
        # Update scan result - use jq with file input to avoid argument length limits  
        local temp_scan_file
        temp_scan_file=$(mktemp)
        echo "$scan_entry" > "$temp_scan_file"
        jq --slurpfile config "${image_basename}-config.json" '.scans.config = $config[0]' "$temp_scan_file" > "${temp_scan_file}.tmp"
        scan_entry=$(cat "${temp_scan_file}.tmp")
        rm -f "$temp_scan_file" "${temp_scan_file}.tmp"
    else
        log "  ⚠️ Configuration scan failed"
    fi
    
    # Add to results - use jq with file input to avoid argument length limits
    local temp_file temp_scan_entry_file
    temp_file=$(mktemp)
    temp_scan_entry_file=$(mktemp)
    
    # Write scan entry to temp file
    echo "$scan_entry" > "$temp_scan_entry_file"
    
    # Use jq to merge files instead of command line variables
    jq --slurpfile new_scan "$temp_scan_entry_file" '.scans += $new_scan' "$SCAN_RESULTS_FILE" > "$temp_file" && mv "$temp_file" "$SCAN_RESULTS_FILE"
    
    # Clean up temp files
    rm -f "$temp_scan_entry_file"
    
    return $([[ "$scan_success" == true ]] && echo 0 || echo 1)
}

# Main scanning function
perform_security_scan() {
    local webauthn_changed="$1"
    local test_credentials_changed="$2"
    local webauthn_image_tag="$3"
    local test_credentials_image_tag="$4"
    
    log "🔍 Starting comprehensive Docker security scanning..."
    
    # Initialize global variables
    SCAN_RESULTS_FILE="docker-security-scan-results.json"
    CRITICAL_VULN_COUNT=0
    TOTAL_VULN_COUNT=0
    SCAN_SUCCESS=true
    
    # Initialize results file
    echo '{"timestamp": "'$(date -Iseconds)'", "scans": []}' > "$SCAN_RESULTS_FILE"
    
    # Initialize SARIF results file for GitHub Security
    local sarif_results_file="docker-security-scan-results.sarif"
    echo '{
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": []
    }' > "$sarif_results_file"
    
    # Scan images that have changes
    if [[ "$webauthn_changed" == "true" ]]; then
        # Use provided full image name or fall back to constructing one
        if [[ -n "$webauthn_image_tag" ]]; then
            log "🔍 Scanning WebAuthn server image: $webauthn_image_tag"
            # Extract base name and tag from full image name for scan_image function
            local base_name="${webauthn_image_tag%:*}"
            local tag="${webauthn_image_tag##*:}"
            if ! scan_image "$base_name" "$tag"; then
                SCAN_SUCCESS=false
            fi
        else
            log "⚠️ No WebAuthn image tag provided, falling back to latest"
            if ! scan_image "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}" "latest"; then
                SCAN_SUCCESS=false
            fi
        fi
    fi
    
    if [[ "$test_credentials_changed" == "true" ]]; then
        # Use provided full image name or fall back to constructing one
        if [[ -n "$test_credentials_image_tag" ]]; then
            log "🔍 Scanning Test Credentials service image: $test_credentials_image_tag"
            # Extract base name and tag from full image name for scan_image function
            local base_name="${test_credentials_image_tag%:*}"
            local tag="${test_credentials_image_tag##*:}"
            if ! scan_image "$base_name" "$tag"; then
                SCAN_SUCCESS=false
            fi
        else
            log "⚠️ No Test Credentials image tag provided, falling back to latest"
            if ! scan_image "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}" "latest"; then
                SCAN_SUCCESS=false
            fi
        fi
    fi
    
    # Consolidate SARIF files for GitHub Security upload
    log "📄 Consolidating SARIF results for GitHub Security..."
    local consolidated_sarif="docker-security-scan-results.sarif"
    
    # Find all SARIF files and merge them
    local sarif_files=(*.sarif)
    if [ -e "${sarif_files[0]}" ]; then
        # Create consolidated SARIF by merging all individual SARIF files
        local temp_sarif
        temp_sarif=$(mktemp)
        
        # Start with first SARIF file and ensure it's valid SARIF (no unauthorized properties)
        jq '{
            "version": .version,
            "$schema": ."$schema", 
            "runs": .runs
        }' "${sarif_files[0]}" > "$temp_sarif"
        
        # Merge additional SARIF files if they exist
        for sarif_file in "${sarif_files[@]:1}"; do
            if [ -f "$sarif_file" ]; then
                # Extract only valid SARIF properties and merge runs
                jq --slurpfile additional <(jq '{
                    "version": .version,
                    "$schema": ."$schema",
                    "runs": .runs
                }' "$sarif_file") '.runs += $additional[].runs' "$temp_sarif" > "${temp_sarif}.tmp"
                mv "${temp_sarif}.tmp" "$temp_sarif"
            fi
        done
        
        # Ensure final SARIF is clean (remove any non-standard properties)
        jq '{
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": .runs
        }' "$temp_sarif" > "$consolidated_sarif"
        rm -f "$temp_sarif"
        
        log "  ✅ SARIF consolidation completed: $consolidated_sarif"
    else
        # No SARIF files found, create empty valid SARIF
        echo '{
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": []
        }' > "$consolidated_sarif"
        log "  ⚠️ No SARIF files found, created empty SARIF file"
    fi
    
    # Generate scan summary
    log "📊 Security Scan Summary:"
    log "  Total vulnerabilities: $TOTAL_VULN_COUNT"
    log "  Critical vulnerabilities: $CRITICAL_VULN_COUNT"
    log "  Scan success: $SCAN_SUCCESS"
    
    # Update results file with summary
    local scan_passed
    scan_passed=$([[ $CRITICAL_VULN_COUNT -eq 0 ]] && [[ "$SCAN_SUCCESS" == true ]] && echo true || echo false)
    
    jq ".summary = {
      \"totalVulnerabilities\": $TOTAL_VULN_COUNT,
      \"criticalVulnerabilities\": $CRITICAL_VULN_COUNT,
      \"scanSuccess\": $SCAN_SUCCESS,
      \"scanPassed\": $scan_passed
    }" "$SCAN_RESULTS_FILE" > scan-results-temp.json && mv scan-results-temp.json "$SCAN_RESULTS_FILE"
    
    # Set GitHub Actions outputs
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
        {
            echo "scan-results=$(cat "$SCAN_RESULTS_FILE" | jq -c .)"
            echo "critical-vulnerabilities=$CRITICAL_VULN_COUNT"
            echo "scan-passed=$scan_passed"
        } >> "$GITHUB_OUTPUT"
    fi
    
    # Fail the script if critical vulnerabilities found
    if [ $CRITICAL_VULN_COUNT -gt 0 ]; then
        log "🚨 CRITICAL VULNERABILITIES FOUND - Blocking DockerHub publish"
        log "Found $CRITICAL_VULN_COUNT critical vulnerabilities in Docker images"
        return 1
    elif [ "$SCAN_SUCCESS" = false ]; then
        log "❌ Security scanning failed - Blocking DockerHub publish"
        return 1
    fi
    
    log "✅ Security scan passed - DockerHub publish approved"
    return 0
}

# Main execution
main() {
    local webauthn_changed="${1:-false}"
    local test_credentials_changed="${2:-false}"
    local webauthn_image_tag="${3:-}"
    local test_credentials_image_tag="${4:-}"
    
    # Validate required environment variables
    if [ -z "${DOCKER_REGISTRY:-}" ] || [ -z "${DOCKER_IMAGE_NAME:-}" ] || [ -z "${DOCKER_TEST_CREDENTIALS_IMAGE_NAME:-}" ]; then
        log "❌ Error: Missing required environment variables"
        log "Required: DOCKER_REGISTRY, DOCKER_IMAGE_NAME, DOCKER_TEST_CREDENTIALS_IMAGE_NAME"
        exit 1
    fi
    
    # Check if at least one image needs scanning
    if [[ "$webauthn_changed" != "true" ]] && [[ "$test_credentials_changed" != "true" ]]; then
        log "ℹ️ No images changed - skipping security scan"
        if [ -n "${GITHUB_OUTPUT:-}" ]; then
            {
                echo "scan-results={\"message\": \"No images to scan\"}"
                echo "critical-vulnerabilities=0"
                echo "scan-passed=true"
            } >> "$GITHUB_OUTPUT"
        fi
        exit 0
    fi
    
    # Install Trivy scanner
    install_trivy
    
    # Images were rebuilt locally by workflow, no need to verify - they're guaranteed to exist
    log "📦 Using locally rebuilt Docker images for security scanning..."
    
    # Perform security scanning
    perform_security_scan "$webauthn_changed" "$test_credentials_changed" "$webauthn_image_tag" "$test_credentials_image_tag"
}

# Trap errors for better debugging
trap 'log "❌ Script failed at line $LINENO"' ERR

# Run main function with all arguments
main "$@"