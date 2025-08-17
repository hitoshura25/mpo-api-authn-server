# Client Publishing Testing Suite

Comprehensive end-to-end testing framework for the configuration-driven client library publishing system.

## Overview

This testing suite validates the configuration-driven publishing architecture without actually executing GitHub workflows or publishing to registries. It provides multi-layered validation across configuration, workflows, templates, and integration scenarios.

## Directory Structure

```
scripts/testing/client-publishing/
├── README.md                          # This documentation
├── run-all-tests.sh                  # Master test runner
├── config-validation/                # Configuration file validation tests
│   ├── test-config-syntax.sh        # YAML syntax validation
│   ├── test-config-structure.sh     # Schema and structure validation
│   ├── test-config-completeness.sh  # Required fields validation
│   └── test-config-environments.sh  # Environment-specific validation
├── workflow-syntax/                  # GitHub Actions workflow validation
│   ├── test-workflow-syntax.sh      # Workflow syntax validation
│   ├── test-input-output-mapping.sh # Input/output validation
│   └── test-job-dependencies.sh     # Job dependency validation
├── gradle-simulation/               # Android template and Gradle tests
│   ├── test-android-template.sh     # Android template generation
│   ├── test-gradle-dry-run.sh       # Gradle execution simulation
│   └── test-property-mapping.sh     # Property name validation
├── environment-selection/           # Environment selection testing
│   ├── test-config-loading.sh       # Configuration loading validation
│   ├── test-environment-isolation.sh # Environment isolation validation
│   └── test-dynamic-queries.sh      # Dynamic yq query validation
├── integration/                     # End-to-end integration simulation
│   ├── test-full-workflow.sh        # Complete workflow simulation
│   ├── test-cross-platform.sh       # Cross-platform consistency
│   └── test-error-scenarios.sh      # Error handling validation
└── utils/                          # Common utility functions
    ├── common-functions.sh          # Shared utility functions
    ├── test-data.sh                 # Test data and scenarios
    └── mock-environments.sh         # Mock environment simulation
```

## Prerequisites

Before running the tests, ensure you have the following tools installed:

- **yq** (YAML processor) - `brew install yq` or download from [mikefarah/yq](https://github.com/mikefarah/yq)
- **actionlint** (GitHub Actions linter) - `brew install actionlint` or download from [rhymond/actionlint](https://github.com/rhymond/actionlint)
- **gradle** (for dry-run simulations) - Use project's Gradle wrapper
- **jq** (JSON processor) - Usually pre-installed or `brew install jq`
- **bash 4+** - macOS users may need `brew install bash`

## Quick Start

### Run All Tests
```bash
# Run the complete test suite
./scripts/testing/client-publishing/run-all-tests.sh

# Run with verbose output
./scripts/testing/client-publishing/run-all-tests.sh --verbose

# Run specific test categories
./scripts/testing/client-publishing/run-all-tests.sh --category config-validation
./scripts/testing/client-publishing/run-all-tests.sh --category workflow-syntax
```

### Run Individual Test Categories

#### Configuration Validation
```bash
# Test configuration file syntax and structure
./scripts/testing/client-publishing/config-validation/test-config-syntax.sh
./scripts/testing/client-publishing/config-validation/test-config-structure.sh
./scripts/testing/client-publishing/config-validation/test-config-completeness.sh
./scripts/testing/client-publishing/config-validation/test-config-environments.sh
```

#### Workflow Syntax Validation
```bash
# Test GitHub Actions workflow files
./scripts/testing/client-publishing/workflow-syntax/test-workflow-syntax.sh
./scripts/testing/client-publishing/workflow-syntax/test-input-output-mapping.sh
./scripts/testing/client-publishing/workflow-syntax/test-job-dependencies.sh
```

#### Gradle Simulation
```bash
# Test Android template and Gradle configuration
./scripts/testing/client-publishing/gradle-simulation/test-android-template.sh
./scripts/testing/client-publishing/gradle-simulation/test-gradle-dry-run.sh
./scripts/testing/client-publishing/gradle-simulation/test-property-mapping.sh
```

#### Environment Selection
```bash
# Test environment-specific configuration loading
./scripts/testing/client-publishing/environment-selection/test-config-loading.sh
./scripts/testing/client-publishing/environment-selection/test-environment-isolation.sh
./scripts/testing/client-publishing/environment-selection/test-dynamic-queries.sh
```

#### Integration Testing
```bash
# Test end-to-end workflow simulation
./scripts/testing/client-publishing/integration/test-full-workflow.sh
./scripts/testing/client-publishing/integration/test-cross-platform.sh
./scripts/testing/client-publishing/integration/test-error-scenarios.sh
```

## Test Scenarios Covered

### Configuration Testing
- **YAML Syntax**: Validates proper YAML formatting and structure
- **Schema Validation**: Ensures all required sections and fields are present
- **Environment Completeness**: Validates both staging and production configurations
- **Cross-Reference Validation**: Ensures naming consistency across sections
- **Value Type Validation**: Validates data types and formats

### Workflow Testing
- **Syntax Validation**: GitHub Actions workflow YAML syntax
- **Input/Output Mapping**: Validates data flow between orchestrator and platform workflows
- **Job Dependencies**: Validates job dependency chains and conditional logic
- **Secret Management**: Validates secret passing and usage patterns
- **Environment Variable Handling**: Tests env var to job output conversion

### Template & Gradle Testing
- **Android Template Generation**: Tests template substitution with various inputs
- **Property Name Validation**: Validates hardcoded property names in templates
- **Gradle Dry-Run**: Simulates Gradle publishing commands without execution
- **Repository Configuration**: Tests repository URL and credential mapping
- **Version Handling**: Tests version format validation and application

### Environment Selection Testing
- **Configuration Loading**: Tests yq queries for environment-specific configuration
- **Environment Isolation**: Ensures only selected environment data is loaded
- **Dynamic Query Generation**: Tests programmatic yq query construction
- **Fallback Handling**: Tests default value handling and error scenarios

### Integration Testing
- **Full Workflow Simulation**: End-to-end workflow execution simulation
- **Cross-Platform Consistency**: Validates Android and TypeScript consistency
- **Error Handling**: Tests various failure scenarios and error recovery
- **Package Naming**: Tests complete package name generation for all scenarios

## Test Data and Mock Environments

The testing suite includes comprehensive test data covering:

- **Valid Configuration Scenarios**: Multiple valid configuration variations
- **Invalid Configuration Scenarios**: Various error conditions and malformed configs
- **Environment Variations**: Different staging and production configurations
- **Version Formats**: Various semantic version formats and edge cases
- **Input Combinations**: Different workflow input combinations and edge cases

Mock environments simulate:
- **GitHub Actions Context**: Environment variables and workflow context
- **Registry Responses**: Mock registry API responses for version checking
- **Gradle Environment**: Mock Gradle project structure and properties
- **File System State**: Various project directory structures

## Error Detection and Reporting

The testing suite provides detailed error reporting including:

- **Configuration Errors**: Missing fields, invalid values, structural issues
- **Workflow Errors**: Syntax errors, invalid references, dependency issues
- **Template Errors**: Substitution failures, property mapping issues
- **Integration Errors**: End-to-end workflow simulation failures

Each test script provides:
- Clear pass/fail status with color-coded output
- Detailed error messages with line numbers and context
- Suggestions for fixing detected issues
- Summary reports for batch test execution

## Extending the Testing Suite

### Adding New Test Cases

1. **Configuration Tests**: Add new scenarios to `utils/test-data.sh`
2. **Workflow Tests**: Add new workflow validation rules to relevant test scripts
3. **Integration Tests**: Add new end-to-end scenarios to `integration/` directory
4. **Mock Data**: Add new mock responses to `utils/mock-environments.sh`

### Adding New Test Categories

1. Create new directory under `scripts/testing/client-publishing/`
2. Add test scripts following the naming pattern `test-*.sh`
3. Update `run-all-tests.sh` to include the new category
4. Update this README with documentation for the new tests

### Test Script Template

```bash
#!/bin/bash
set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../utils/common-functions.sh"
source "${SCRIPT_DIR}/../utils/test-data.sh"

# Test script metadata
TEST_NAME="Description of what this tests"
TEST_CATEGORY="category-name"

log_test_start "${TEST_NAME}"

# Test implementation
test_function() {
    log_info "Testing specific functionality..."
    
    # Test logic here
    if [[ condition ]]; then
        log_success "Test passed"
        return 0
    else
        log_error "Test failed: detailed error message"
        return 1
    fi
}

# Main execution
main() {
    test_function
    log_test_end "${TEST_NAME}" $?
}

main "$@"
```

## Troubleshooting

### Common Issues

1. **yq Not Found**: Install yq using `brew install yq` or download from GitHub
2. **actionlint Not Found**: Install using `brew install actionlint`
3. **Permission Errors**: Ensure all test scripts are executable (`chmod +x`)
4. **Configuration Path Errors**: Verify the configuration file exists at expected path

### Test Failures

1. **Configuration Test Failures**: Check YAML syntax and required fields
2. **Workflow Test Failures**: Validate GitHub Actions syntax with actionlint
3. **Template Test Failures**: Verify template files exist and are properly formatted
4. **Integration Test Failures**: Check that all dependencies are properly mocked

### Debug Mode

Run any test script with the `--debug` flag for verbose output:
```bash
./scripts/testing/client-publishing/config-validation/test-config-syntax.sh --debug
```

## Performance Considerations

- **Test Execution Time**: Full test suite runs in under 2 minutes
- **Parallel Execution**: Tests can be run in parallel by category
- **Resource Usage**: Tests use minimal system resources (no actual publishing)
- **Caching**: Test data and mock responses are cached for faster subsequent runs

## Future Enhancements

- **CI Integration**: GitHub Actions workflow for running tests on PR
- **Test Coverage Reporting**: Detailed coverage metrics for test scenarios
- **Performance Benchmarking**: Automated performance regression testing
- **Visual Test Reports**: HTML reports with detailed test results
- **Test Data Generation**: Automated generation of test scenarios