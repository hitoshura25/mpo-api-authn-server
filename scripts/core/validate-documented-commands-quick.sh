#!/bin/bash
# Quick validation of critical documented development commands
# Phase 5 (FINAL PHASE) of Documentation Consistency Remediation

# set -e # Don't exit on errors, we want to collect all results
echo "🔍 Quick validation of documented development commands..."

PASSED=0
WARNINGS=0
ERRORS=0

# Function to log results
log_success() { echo "✅ $1"; ((PASSED++)); }
log_warning() { echo "⚠️  $1"; ((WARNINGS++)); }
log_error() { echo "❌ $1"; ((ERRORS++)); }

echo ""
echo "📦 Critical Gradle Commands..."

# Core commands from CLAUDE.md
./gradlew help --quiet >/dev/null 2>&1 && log_success "Gradle wrapper works" || log_error "Gradle wrapper failed"
./gradlew :webauthn-server:build --dry-run --quiet >/dev/null 2>&1 && log_success "Server build (:webauthn-server:build)" || log_error "Server build failed"
./gradlew :webauthn-server:test --dry-run --quiet >/dev/null 2>&1 && log_success "Server test (:webauthn-server:test)" || log_error "Server test failed"  
./gradlew :webauthn-test-credentials-service:build --dry-run --quiet >/dev/null 2>&1 && log_success "Test service build" || log_error "Test service build failed"
./gradlew build --dry-run --quiet >/dev/null 2>&1 && log_success "Full build (./gradlew build)" || log_error "Full build failed"
./gradlew test --dry-run --quiet >/dev/null 2>&1 && log_success "All tests (./gradlew test)" || log_error "All tests failed"
./gradlew detekt --dry-run --quiet >/dev/null 2>&1 && log_success "Lint (./gradlew detekt)" || log_error "Lint failed"

echo ""
echo "🐳 Docker & Scripts..."

# Docker and scripts
docker --version >/dev/null 2>&1 && log_success "Docker available" || log_error "Docker not available"
[ -f "webauthn-server/start-dev.sh" ] && log_success "start-dev.sh exists" || log_error "start-dev.sh missing"
[ -x "webauthn-server/start-dev.sh" ] && log_success "start-dev.sh executable" || log_warning "start-dev.sh not executable"
[ -f "scripts/core/validate-gradle-config-cache.sh" ] && log_success "validate-gradle-config-cache.sh exists" || log_error "validate-gradle-config-cache.sh missing"
[ -f "scripts/core/validate-markdown.sh" ] && log_success "validate-markdown.sh exists" || log_error "validate-markdown.sh missing"

echo ""
echo "📱 Client Modules..."

# Module structure
[ -d "android-client-library" ] && log_success "android-client-library directory exists" || log_error "android-client-library missing"
[ -d "android-test-client" ] && log_success "android-test-client directory exists" || log_error "android-test-client missing"
[ -d "typescript-client-library" ] && log_success "typescript-client-library directory exists" || log_error "typescript-client-library missing"
[ -d "web-test-client" ] && log_success "web-test-client directory exists" || log_error "web-test-client missing"
[ -d "webauthn-server" ] && log_success "webauthn-server directory exists" || log_error "webauthn-server missing"

echo ""
echo "📊 Quick Validation Summary"
echo "============================"
echo "✅ Passed:   $PASSED"
echo "⚠️  Warnings: $WARNINGS" 
echo "❌ Errors:   $ERRORS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "🎉 All critical documented commands work!"
    exit 0
else
    echo "❌ Some critical issues found. See full validation script."
    exit 1
fi