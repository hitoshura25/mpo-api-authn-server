# Component Change Detection Testing Framework

## Overview

Comprehensive testing framework for Phase 10.1 Component Change Detection, providing validation of intelligent change detection for independent component processing optimization.

## Purpose

This testing framework validates the **component change detection system** that enables:
- **40-60% faster builds** for single-component changes
- **Intelligent OpenAPI client generation** based on actual specification changes
- **Parallel processing optimization** while maintaining reliability
- **Accurate change boundary detection** between webauthn-server and test-credentials-service

## Test Categories

### 1. Component Boundary Detection (4 tests)

**Purpose**: Validate that file changes correctly trigger component processing

- `test-webauthn-server-boundaries.sh` - WebAuthn server component detection
- `test-test-credentials-boundaries.sh` - Test credentials service component detection  
- `test-shared-dependency-handling.sh` - webauthn-test-lib affects both components
- `test-component-isolation.sh` - Changes in one component don't trigger others

### 2. OpenAPI Change Detection (3 tests)

**Purpose**: Ensure client library generation only occurs when needed

- `test-openapi-spec-changes.sh` - documentation.yaml changes trigger client generation
- `test-openapi-build-changes.sh` - OpenAPI generation script changes
- `test-client-directory-changes.sh` - Client library source directory changes

### 3. Infrastructure Change Detection (3 tests)

**Purpose**: Validate infrastructure change detection accuracy

- `test-workflow-changes.sh` - .github/workflows/ directory changes
- `test-config-changes.sh` - config/ directory changes
- `test-build-file-changes.sh` - Root build configuration changes

### 4. GitHub Actions Integration (3 tests)

**Purpose**: Validate GitHub Actions workflow integration

- `test-github-outputs.sh` - GITHUB_OUTPUT environment variable handling
- `test-pr-context-detection.sh` - Pull request context handling
- `test-main-branch-context.sh` - Main branch context handling

### 5. Edge Cases & Error Handling (2 tests)

**Purpose**: Test error scenarios and fallback behavior

- `test-fallback-behavior.sh` - Behavior when change detection fails
- `test-edge-case-scenarios.sh` - Complex change patterns and edge cases

## Quick Start

### Run All Tests

```bash
# Execute complete validation suite
cd scripts/testing/component-change-detection/
./run-all-tests.sh

# Expected output: 15/15 tests passing
```

### Run Specific Test Category

```bash
# Component boundary detection
./component-boundaries/run-boundary-tests.sh

# OpenAPI change detection  
./openapi-detection/run-openapi-tests.sh

# GitHub Actions integration
./github-integration/run-integration-tests.sh
```

### Individual Test Execution

```bash
# Test specific component change detection
./component-boundaries/test-webauthn-server-boundaries.sh

# Test OpenAPI specification changes
./openapi-detection/test-openapi-spec-changes.sh

# Test GitHub Actions outputs
./github-integration/test-github-outputs.sh
```

## Test Environment Setup

### Prerequisites

```bash
# Ensure git repository with test files
cd /path/to/mpo-api-authn-server
git status  # Should show clean working directory

# Change detection script should be executable
chmod +x scripts/core/detect-component-changes.sh

# Verify component patterns are correctly defined
./scripts/core/detect-component-changes.sh --help
```

### Mock Test Environment

The testing framework creates temporary test scenarios:

```bash
# Creates temporary test files in:
webauthn-server/test-change.txt
webauthn-test-credentials-service/test-change.txt  
webauthn-test-lib/shared-change.txt
webauthn-server/src/main/resources/openapi/documentation.yaml

# All test files are automatically cleaned up after testing
```

## Testing Validation Scenarios

### Component Change Patterns

1. **WebAuthn Server Only**:
   ```bash
   # Should detect: webauthn-server-changed=true, others=false
   echo "test" > webauthn-server/test.txt
   ./scripts/core/detect-component-changes.sh HEAD~1 HEAD
   ```

2. **Test Credentials Service Only**:
   ```bash
   # Should detect: test-credentials-service-changed=true, others=false
   echo "test" > webauthn-test-credentials-service/test.txt
   ./scripts/core/detect-component-changes.sh HEAD~1 HEAD  
   ```

3. **Shared Library Changes**:
   ```bash
   # Should detect: BOTH webauthn-server=true AND test-credentials-service=true
   echo "test" > webauthn-test-lib/shared.txt
   ./scripts/core/detect-component-changes.sh HEAD~1 HEAD
   ```

4. **OpenAPI Specification Changes**:
   ```bash
   # Should detect: openapi-changed=true, client-generation-required=true
   echo "# comment" >> webauthn-server/src/main/resources/openapi/documentation.yaml
   ./scripts/core/detect-component-changes.sh HEAD~1 HEAD
   ```

### Expected Output Format

All tests validate that the change detection script produces correct GitHub Actions outputs:

```bash
webauthn-server-changed=true|false
test-credentials-service-changed=true|false
openapi-changed=true|false
e2e-tests-changed=true|false
infrastructure-changed=true|false
client-generation-required=true|false
```

## Continuous Integration Integration

### GitHub Actions Usage

The component change detection integrates with the main workflow:

```yaml
# In .github/workflows/main-ci-cd.yml
detect-component-changes:
  outputs:
    webauthn-server-changed: ${{ steps.component-detection.outputs.webauthn-server-changed }}
    # ... other outputs

  steps:
    - name: Run component change detection  
      id: component-detection
      run: ./scripts/core/detect-component-changes.sh
```

### Pre-merge Validation

```bash
# Before merging Phase 10.1 changes, validate:
./scripts/testing/component-change-detection/run-all-tests.sh

# All 15 tests should pass:
# ✅ Component Boundary Detection: 4/4 passed
# ✅ OpenAPI Change Detection: 3/3 passed  
# ✅ Infrastructure Detection: 3/3 passed
# ✅ GitHub Actions Integration: 3/3 passed
# ✅ Edge Cases & Error Handling: 2/2 passed
```

## Performance Benefits Validation

### Build Time Measurement

The testing framework includes performance validation:

```bash
# Measure component change detection performance
time ./scripts/core/detect-component-changes.sh HEAD~1 HEAD

# Expected: <2 seconds for change detection
# This enables 40-60% faster builds for single-component changes
```

### Change Detection Accuracy

```bash
# Validate >95% accuracy requirement
./component-boundaries/validate-detection-accuracy.sh

# Tests 20+ scenarios, expects <5% false positives/negatives
```

## Troubleshooting & Debugging

### Common Issues

1. **Git Repository State**:
   ```bash
   # Ensure clean git state before testing
   git status --porcelain
   # Should show no uncommitted changes
   ```

2. **Script Permissions**:
   ```bash
   # Ensure detection script is executable
   ls -la scripts/core/detect-component-changes.sh
   # Should show -rwxr-xr-x permissions
   ```

3. **GitHub Actions Environment**:
   ```bash
   # Test in CI-like environment
   export GITHUB_EVENT_NAME="pull_request"
   export GITHUB_BASE_REF="main"
   ./scripts/core/detect-component-changes.sh
   ```

### Debug Mode

```bash
# Enable detailed debug logging
export DEBUG_CHANGE_DETECTION=true
./scripts/core/detect-component-changes.sh HEAD~1 HEAD

# Shows detailed file pattern matching and decision logic
```

## Integration with Phase 10.2

This testing framework prepares for Phase 10.2 implementation:

- **Component Boundaries**: Validated change detection enables parallel workflow execution
- **OpenAPI Detection**: Accurate client generation triggering reduces unnecessary builds
- **GitHub Integration**: Workflow outputs ready for conditional job execution
- **Performance Validation**: Baseline measurements for 40-60% improvement validation

## Future Extensions

### Additional Test Scenarios

- **Multi-component changes**: Complex scenarios with multiple component changes
- **E2E test coordination**: Validation of cross-component integration testing
- **Workflow dependency management**: Testing of parallel execution coordination

### Performance Optimizations

- **Change detection caching**: Optimization for repeated detection runs
- **Pattern matching optimization**: Improved file pattern matching algorithms
- **Integration test coordination**: Enhanced E2E testing with parallel builds

---

**Phase 10.1 Status**: ✅ Component Change Detection implementation with comprehensive testing validation
**Next Phase**: Phase 10.2 - Parallel Workflow Architecture using validated change detection