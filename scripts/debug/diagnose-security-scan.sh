#!/bin/bash

# Security Scan Diagnosis Script
# Helps identify specific critical vulnerabilities in Docker images

set -euo pipefail

echo "🔍 Docker Security Scan Diagnosis Tool"
echo "========================================"
echo ""

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Check if Trivy is installed
if ! command -v trivy &> /dev/null; then
    log "📦 Installing Trivy scanner..."
    # Install trivy (Ubuntu/Debian)
    sudo apt-get update
    sudo apt-get install wget apt-transport-https gnupg lsb-release
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
    echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
    sudo apt-get update
    sudo apt-get install trivy
    
    # Alternative: Download binary directly (if above fails)
    if ! command -v trivy &> /dev/null; then
        log "📥 Downloading Trivy binary directly..."
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    fi
fi

log "✅ Trivy scanner ready"

# Function to scan local Docker image if available
scan_local_image() {
    local image_name="$1"
    log "🔍 Scanning local image: $image_name"
    
    if docker image inspect "$image_name" >/dev/null 2>&1; then
        log "📋 Found local image, scanning for vulnerabilities..."
        
        # Scan for CRITICAL vulnerabilities only
        echo ""
        echo "=== CRITICAL VULNERABILITIES ==="
        trivy image --severity CRITICAL --format table "$image_name" || true
        
        echo ""
        echo "=== HIGH VULNERABILITIES ==="
        trivy image --severity HIGH --format table --head 10 "$image_name" || true
        
        # Generate JSON report for detailed analysis
        trivy image --format json --output "${image_name//[\/:]/_}-security-report.json" "$image_name" 2>/dev/null || true
        
        if [[ -f "${image_name//[\/:]/_}-security-report.json" ]]; then
            local critical_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "${image_name//[\/:]/_}-security-report.json" 2>/dev/null || echo 0)
            local high_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "${image_name//[\/:]/_}-security-report.json" 2>/dev/null || echo 0)
            
            log "📊 Summary for $image_name:"
            log "  - CRITICAL: $critical_count"
            log "  - HIGH: $high_count"
            
            if [[ $critical_count -gt 0 ]]; then
                log "🚨 CRITICAL vulnerabilities found!"
                echo ""
                echo "=== TOP CRITICAL VULNERABILITY DETAILS ==="
                jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | "CVE: \(.VulnerabilityID)\nPackage: \(.PkgName) (\(.InstalledVersion))\nDescription: \(.Description)\nFixed Version: \(.FixedVersion // "Not Available")\n---"' "${image_name//[\/:]/_}-security-report.json" 2>/dev/null | head -50
            fi
        fi
        
        echo ""
        echo "=== CONFIGURATION SCAN ==="
        trivy config --format table . || true
        
    else
        log "❌ Local image $image_name not found"
    fi
}

# Function to scan base images directly
scan_base_images() {
    log "🐳 Scanning base images for known vulnerabilities..."
    
    # List of base images used in our Dockerfiles
    local base_images=(
        "eclipse-temurin:21-jre-jammy"
        "gcr.io/distroless/java21-debian12"
    )
    
    for image in "${base_images[@]}"; do
        echo ""
        log "🔍 Pulling and scanning base image: $image"
        
        # Pull the latest version
        docker pull "$image" || {
            log "❌ Failed to pull $image"
            continue
        }
        
        scan_local_image "$image"
    done
}

# Function to analyze Dockerfiles
analyze_dockerfiles() {
    log "📄 Analyzing Dockerfiles for security best practices..."
    
    local dockerfiles=(
        "webauthn-server/Dockerfile"
        "webauthn-test-credentials-service/Dockerfile"
    )
    
    for dockerfile in "${dockerfiles[@]}"; do
        if [[ -f "$dockerfile" ]]; then
            echo ""
            log "📋 Analyzing $dockerfile"
            trivy config --format table "$dockerfile" || true
        fi
    done
}

# Function to check for recent CVEs affecting Java 21
check_java_cves() {
    log "🔍 Checking for recent Java 21 CVEs (January 2025)..."
    
    echo ""
    echo "=== KNOWN JAVA 21 VULNERABILITIES (January 2025 CPU) ==="
    cat << 'EOF'
Recent Oracle Critical Patch Update (January 2025) affects:
- CVE-2025-0509: Java SE Install component vulnerability 
- CVE-2025-21502: Java SE, GraalVM vulnerability

Affected Java versions:
- Java 21.0.5 and earlier (upgrade to 21.0.6+)
- Java 17.0.14 and earlier
- Java 11.0.26 and earlier
- Java 8u431 and earlier

Recommendation: Update to latest Eclipse Temurin images that include
the January 2025 security patches.
EOF
}

# Main execution
main() {
    log "🚀 Starting security diagnosis..."
    
    # Check Java CVEs first
    check_java_cves
    
    # Analyze our Dockerfiles
    analyze_dockerfiles
    
    # Scan base images
    scan_base_images
    
    # Try to scan our built images if they exist
    local our_images=(
        "ghcr.io/hitoshura25/webauthn-server:latest"
        "ghcr.io/hitoshura25/webauthn-test-credentials-service:latest"
    )
    
    for image in "${our_images[@]}"; do
        scan_local_image "$image"
    done
    
    log "✅ Diagnosis complete!"
    
    echo ""
    echo "=== NEXT STEPS ==="
    echo "1. Review critical vulnerabilities above"
    echo "2. Update base images to latest versions with security patches"
    echo "3. Check JSON reports generated: *-security-report.json"
    echo "4. Consider using newer base images or alternative distroless variants"
    
    echo ""
    echo "=== GENERATED FILES ==="
    ls -la *-security-report.json 2>/dev/null || echo "No JSON reports generated"
}

# Run main function
main "$@"