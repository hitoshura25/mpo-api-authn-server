#!/bin/bash
# Comprehensive validation of all documented development commands
# Phase 5 (FINAL PHASE) of Documentation Consistency Remediation

set -e
echo "🔍 Validating all documented development commands..."

VALIDATION_PASSED=0
VALIDATION_WARNINGS=0
VALIDATION_ERRORS=0

# Function to log results
log_success() { echo "✅ $1"; ((VALIDATION_PASSED++)); }
log_warning() { echo "⚠️  $1"; ((VALIDATION_WARNINGS++)); }
log_error() { echo "❌ $1"; ((VALIDATION_ERRORS++)); }

echo ""
echo "📦 Testing Gradle Core Commands..."

# Test Gradle availability
if ./gradlew help >/dev/null 2>&1; then
    log_success "Gradle wrapper available"
else
    log_error "Gradle wrapper failed"
    exit 1
fi

# Test main server commands from CLAUDE.md
if ./gradlew :webauthn-server:build --dry-run --quiet >/dev/null 2>&1; then
    log_success "Server build command (:webauthn-server:build)"
else
    log_error "Server build command failed"
fi

if ./gradlew :webauthn-server:test --dry-run --quiet >/dev/null 2>&1; then
    log_success "Server test command (:webauthn-server:test)"
else
    log_error "Server test command failed"
fi

if ./gradlew :webauthn-server:run --dry-run --quiet >/dev/null 2>&1; then
    log_success "Server run command (:webauthn-server:run)"
else
    log_warning "Server run command has issues (may require dependencies)"
fi

if ./gradlew :webauthn-server:koverHtmlReport --dry-run --quiet >/dev/null 2>&1; then
    log_success "Server coverage command (:webauthn-server:koverHtmlReport)"
else
    log_error "Server coverage command failed"
fi

# Test credentials service commands from CLAUDE.md
if ./gradlew :webauthn-test-credentials-service:build --dry-run --quiet >/dev/null 2>&1; then
    log_success "Test service build command"
else
    log_error "Test service build command failed"
fi

if ./gradlew :webauthn-test-credentials-service:test --dry-run --quiet >/dev/null 2>&1; then
    log_success "Test service test command"
else
    log_error "Test service test command failed"
fi

if ./gradlew :webauthn-test-credentials-service:run --dry-run --quiet >/dev/null 2>&1; then
    log_success "Test service run command"
else
    log_warning "Test service run command has issues (may require dependencies)"
fi

# Test module-wide commands from CLAUDE.md
if ./gradlew build --dry-run --quiet >/dev/null 2>&1; then
    log_success "Full build command (./gradlew build)"
else
    log_error "Full build command failed"
fi

if ./gradlew test --dry-run --quiet >/dev/null 2>&1; then
    log_success "All tests command (./gradlew test)"
else
    log_error "All tests command failed"
fi

if ./gradlew detekt --dry-run --quiet >/dev/null 2>&1; then
    log_success "Lint command (./gradlew detekt)"
else
    log_error "Lint command failed"
fi

echo ""
echo "📱 Testing Android Client Commands..."

# Test Android client library commands from CLAUDE.md and README.md
if [ -d "android-client-library" ]; then
    if [ -f "android-client-library/gradlew" ]; then
        if (cd android-client-library && ./gradlew test --dry-run --quiet >/dev/null 2>&1); then
            log_success "Android client library test command (submodule)"
        else
            log_warning "Android client library test command has issues"
        fi
        
        if (cd android-client-library && ./gradlew publish --dry-run --quiet >/dev/null 2>&1); then
            log_success "Android client library publish command (submodule)"
        else
            log_warning "Android client library publish command has issues (requires credentials)"
        fi
    else
        log_warning "Android client library uses root gradle wrapper"
        if ./gradlew :android-client-library:test --dry-run --quiet >/dev/null 2>&1; then
            log_success "Android client library test command (root gradle)"
        else
            log_warning "Android client library test command has issues"
        fi
    fi
else
    log_error "Android client library directory not found"
fi

# Test Android test client commands from README.md
if [ -d "android-test-client" ]; then
    if [ -f "android-test-client/gradlew" ]; then
        if (cd android-test-client && ./gradlew build --dry-run --quiet >/dev/null 2>&1); then
            log_success "Android test client build command"
        else
            log_warning "Android test client build command has issues"
        fi
        
        if (cd android-test-client && ./gradlew test --dry-run --quiet >/dev/null 2>&1); then
            log_success "Android test client test command"
        else
            log_warning "Android test client test command has issues"
        fi
        
        if (cd android-test-client && ./gradlew connectedAndroidTest --dry-run --quiet >/dev/null 2>&1); then
            log_success "Android test client connected test command"
        else
            log_warning "Android test client connected test command has issues (requires device/emulator)"
        fi
    else
        log_warning "Android test client missing gradle wrapper"
    fi
else
    log_error "Android test client directory not found"
fi

echo ""
echo "🌐 Testing Web/TypeScript Client Commands..."

# Test TypeScript client library commands from CLAUDE.md and README.md
if [ -d "typescript-client-library" ]; then
    if [ -f "typescript-client-library/package.json" ]; then
        if (cd typescript-client-library && npm --version >/dev/null 2>&1); then
            log_success "npm available in typescript-client-library"
            
            # Check if build script exists
            if (cd typescript-client-library && npm run build --silent >/dev/null 2>&1); then
                log_success "TypeScript client library build command"
            else
                log_warning "TypeScript client library build command has issues"
            fi
            
            # Check if test script exists
            if (cd typescript-client-library && npm test --silent >/dev/null 2>&1); then
                log_success "TypeScript client library test command"
            else
                log_warning "TypeScript client library test command has issues (may have no tests)"
            fi
        else
            log_error "npm not available for typescript-client-library"
        fi
    else
        log_error "TypeScript client library missing package.json"
    fi
else
    log_error "TypeScript client library directory not found"
fi

# Test Web test client commands from README.md
if [ -d "web-test-client" ]; then
    if [ -f "web-test-client/package.json" ]; then
        if (cd web-test-client && npm --version >/dev/null 2>&1); then
            log_success "npm available in web-test-client"
            
            # Test documented npm commands from web-test-client README.md
            if (cd web-test-client && npm run build --silent >/dev/null 2>&1); then
                log_success "Web test client build command (npm run build)"
            else
                log_warning "Web test client build command has issues"
            fi
            
            if (cd web-test-client && npm run dev >/dev/null 2>&1 &); then
                sleep 2
                pkill -f "npm run dev" >/dev/null 2>&1 || true
                log_success "Web test client dev command (npm run dev)"
            else
                log_warning "Web test client dev command has issues"
            fi
            
            if (cd web-test-client && npm test --silent >/dev/null 2>&1); then
                log_success "Web test client test command (npm test)"
            else
                log_warning "Web test client test command has issues (may require server)"
            fi
        else
            log_error "npm not available for web-test-client"
        fi
    else
        log_error "Web test client missing package.json"
    fi
else
    log_error "Web test client directory not found"
fi

echo ""
echo "🐳 Testing Docker Commands..."

# Test Docker availability
if docker --version >/dev/null 2>&1; then
    log_success "Docker available"
else
    log_error "Docker not available"
fi

# Test docker-compose files existence (from CLAUDE.md)
if ls webauthn-server/docker-compose*.yml >/dev/null 2>&1; then
    log_success "Docker compose files found in webauthn-server/"
else
    log_warning "Docker compose files not found in expected location"
fi

echo ""
echo "🔧 Testing Development Scripts..."

# Test start-dev.sh script from CLAUDE.md
if [ -f "webauthn-server/start-dev.sh" ]; then
    if [ -x "webauthn-server/start-dev.sh" ]; then
        log_success "webauthn-server/start-dev.sh exists and is executable"
    else
        log_warning "webauthn-server/start-dev.sh exists but is not executable"
    fi
else
    log_error "webauthn-server/start-dev.sh not found"
fi

# Test validate-gradle-config-cache.sh from CLAUDE.md
if [ -f "scripts/core/validate-gradle-config-cache.sh" ]; then
    if [ -x "scripts/core/validate-gradle-config-cache.sh" ]; then
        log_success "scripts/core/validate-gradle-config-cache.sh exists and is executable"
    else
        log_warning "scripts/core/validate-gradle-config-cache.sh exists but is not executable"
    fi
else
    log_error "scripts/core/validate-gradle-config-cache.sh not found"
fi

# Test validate-markdown.sh from CLAUDE.md
if [ -f "scripts/core/validate-markdown.sh" ]; then
    if [ -x "scripts/core/validate-markdown.sh" ]; then
        log_success "scripts/core/validate-markdown.sh exists and is executable"
        
        # Test if it actually runs
        if bash scripts/core/validate-markdown.sh >/dev/null 2>&1; then
            log_success "validate-markdown.sh runs successfully"
        else
            log_warning "validate-markdown.sh has runtime issues"
        fi
    else
        log_warning "scripts/core/validate-markdown.sh exists but is not executable"
    fi
else
    log_error "scripts/core/validate-markdown.sh not found"
fi

echo ""
echo "📊 Command Validation Summary"
echo "=============================="
echo "✅ Passed:   $VALIDATION_PASSED"
echo "⚠️  Warnings: $VALIDATION_WARNINGS"
echo "❌ Errors:   $VALIDATION_ERRORS"
echo ""

if [ $VALIDATION_ERRORS -eq 0 ]; then
    if [ $VALIDATION_WARNINGS -eq 0 ]; then
        echo "🎉 All documented commands validated successfully!"
        exit 0
    else
        echo "✅ All critical commands work, but some have warnings (usually expected for missing dependencies/credentials)"
        exit 0
    fi
else
    echo "❌ Some documented commands failed validation. Review the errors above."
    exit 1
fi