#!/bin/bash
#
# Docker Security Scanning Script
#
# This script performs comprehensive security scanning of Docker images using Trivy scanner.
# It scans for vulnerabilities, secrets, and configuration issues, providing detailed JSON output
# and blocking publication on critical vulnerabilities.
#
# USAGE:
#   ./scan-security.sh <webauthn_changed> <test_credentials_changed>
#   where parameters are "true" or "false"
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

# Function to pull Docker images for scanning (if they're not already local)
pull_images() {
    local webauthn_changed="$1"
    local test_credentials_changed="$2"
    local scan_local_images="${3:-false}"
    
    if [[ "$scan_local_images" == "true" ]]; then
        log "📦 Using locally built images for security scanning (build-and-test workflow)"
        # In build-and-test, images are already built locally with load: true
        # Check if images exist locally
        if [[ "$webauthn_changed" == "true" ]]; then
            if docker image inspect "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest" >/dev/null 2>&1; then
                log "✅ Found local webauthn-server image"
            else
                log "❌ Local webauthn-server image not found - may need to check build step"
                exit 1
            fi
        fi
        
        if [[ "$test_credentials_changed" == "true" ]]; then
            if docker image inspect "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}:latest" >/dev/null 2>&1; then
                log "✅ Found local test-credentials-service image"
            else
                log "❌ Local test-credentials-service image not found - may need to check build step"
                exit 1
            fi
        fi
    else
        log "📦 Pulling images from GHCR for security scanning (post-processing workflow)..."
        
        if [[ "$webauthn_changed" == "true" ]]; then
            docker pull "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest"
            log "✅ Pulled webauthn-server image"
        fi
        
        if [[ "$test_credentials_changed" == "true" ]]; then
            docker pull "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}:latest"
            log "✅ Pulled test-credentials-service image"
        fi
    fi
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
       trivy image --format sarif --output "${image_basename}-vulns.sarif" "$full_image" 2>/dev/null; then
        log "  ✅ Vulnerability scan completed (JSON + SARIF)"
        
        # Count critical and high vulnerabilities
        local critical_count high_count total_count
        critical_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "${image_basename}-vulns.json" 2>/dev/null || echo 0)
        high_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "${image_basename}-vulns.json" 2>/dev/null || echo 0)
        total_count=$(jq '[.Results[]?.Vulnerabilities[]?] | length' "${image_basename}-vulns.json" 2>/dev/null || echo 0)
        
        CRITICAL_VULN_COUNT=$((CRITICAL_VULN_COUNT + critical_count))
        TOTAL_VULN_COUNT=$((TOTAL_VULN_COUNT + total_count))
        
        log "    📊 Found $critical_count CRITICAL, $high_count HIGH, $total_count total vulnerabilities"
        
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
    local scan_local_images="${3:-false}"
    
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
        if ! scan_image "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}" "latest"; then
            SCAN_SUCCESS=false
        fi
    fi
    
    if [[ "$test_credentials_changed" == "true" ]]; then
        if ! scan_image "${DOCKER_REGISTRY}/${DOCKER_TEST_CREDENTIALS_IMAGE_NAME}" "latest"; then
            SCAN_SUCCESS=false
        fi
    fi
    
    # Consolidate SARIF files for GitHub Security upload
    log "📄 Consolidating SARIF results for GitHub Security..."
    local consolidated_sarif="docker-security-scan-results.json"
    
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
    
    # Pull images for scanning
    pull_images "$webauthn_changed" "$test_credentials_changed"
    
    # Perform security scanning
    perform_security_scan "$webauthn_changed" "$test_credentials_changed"
}

# Trap errors for better debugging
trap 'log "❌ Script failed at line $LINENO"' ERR

# Run main function with all arguments
main "$@"