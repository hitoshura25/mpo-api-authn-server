# Security Scripts Documentation

This directory contains security-focused automation scripts for WebAuthn authentication system analysis. These scripts are designed to be used in GitHub Actions workflows for comprehensive security analysis of pull requests.

## Overview

The security scripts follow WebAuthn-specific security best practices and provide automated vulnerability detection, risk assessment, and test generation for authentication systems.

### Architecture

```
scripts/security/
├── analyze-changes.sh        # Security change impact analysis
├── analyze-pr.sh            # Main AI-powered security analysis
├── generate-tests.sh        # Security test generation
├── create-security-comment.js  # PR comment generation
├── add-security-labels.js   # Automated PR labeling
└── README.md               # This documentation
```

## Scripts Documentation

### 1. analyze-changes.sh

**Purpose**: Analyzes the security impact of PR changes by categorizing files and determining risk levels.

**Usage**: 
```bash
./analyze-changes.sh
```

**Environment Variables**:
- `AUTH_FLOWS_FILES` - Space-separated authentication flow files
- `SECURITY_COMPONENTS_FILES` - Space-separated security component files
- `SECURITY_TESTS_FILES` - Space-separated security test files
- `DEPENDENCIES_FILES` - Space-separated dependency files  
- `INFRASTRUCTURE_FILES` - Space-separated infrastructure files
- `ALL_CHANGED_FILES` - Space-separated all changed files
- `GITHUB_OUTPUT` - GitHub Actions output file path

**Outputs**:
- `has-auth-changes`: Boolean indicating authentication changes
- `has-security-changes`: Boolean indicating security component changes
- `has-dependency-changes`: Boolean indicating dependency changes
- `has-infrastructure-changes`: Boolean indicating infrastructure changes
- `security-risk-level`: Risk assessment (HIGH/MEDIUM/LOW/MINIMAL)
- `changed-files-json`: JSON array of all changed files

**Risk Assessment Logic**:
- **HIGH**: >5 security changes OR any dependency changes
- **MEDIUM**: >2 security changes OR any infrastructure changes  
- **LOW**: Any security changes
- **MINIMAL**: No security-related changes

### 2. analyze-pr.sh

**Purpose**: Performs comprehensive AI-powered security analysis using Anthropic Claude.

**Usage**:
```bash
./analyze-pr.sh <changed_files_json> <pr_title> <pr_body> <risk_level>
```

**Environment Variables**:
- `ANTHROPIC_API_KEY` - API key for AI analysis (optional)
- `PR_NUMBER` - Pull request number
- `WEBAUTHN_SECURITY_AGENT_PATH` - Path to security agent file
- `VULNERABILITY_DB_PATH` - Path to vulnerability database

**Outputs**:
- `security-analysis-results.json` - Complete analysis results
- GitHub Actions outputs for security score, vulnerabilities, and recommendations

**Features**:
- AI-powered vulnerability detection
- WebAuthn-specific security pattern analysis
- Fallback analysis when AI is unavailable
- Integration with existing security test suites

### 3. generate-tests.sh

**Purpose**: Generates security test implementations for detected vulnerabilities.

**Usage**:
```bash
./generate-tests.sh
```

**Requirements**:
- `security-analysis-results.json` from previous analysis
- Node.js environment with optional AI dependencies

**Environment Variables**:
- `ANTHROPIC_API_KEY` - API key for AI test generation (optional)

**Outputs**:
- `security-test-implementations.json` - Generated test code and metadata

**Features**:
- AI-generated Kotlin test methods
- Template-based fallback tests
- Integration with existing VulnerabilityProtectionTest patterns

### 4. create-security-comment.js

**Purpose**: Creates comprehensive security review comments for pull requests.

**Usage**:
```bash
node create-security-comment.js
```

**Environment Variables**:
- `SECURITY_SCORE` - Numerical security score (0-10)
- `VULNERABILITIES_COUNT` - Number of vulnerabilities found
- `REQUIRES_REVIEW` - Boolean for security review requirement
- `RISK_LEVEL` - Risk level assessment
- `GITHUB_TOKEN` - GitHub API token

**Input Files**:
- `security-analysis-results.json`
- `security-test-implementations.json`

**Features**:
- Structured vulnerability reporting with CWE references
- Collapsible test implementation sections
- Security patterns analysis reporting
- Interactive checklist for reviewers

### 5. add-security-labels.js

**Purpose**: Automatically applies security-related labels to pull requests.

**Usage**:
```bash
node add-security-labels.js
```

**Environment Variables**:
- `SECURITY_SCORE` - Numerical security score
- `RISK_LEVEL` - Risk level assessment
- `REQUIRES_SECURITY_REVIEW` - Security review requirement
- `HAS_AUTH_CHANGES` - Authentication changes indicator
- `HAS_DEPENDENCY_CHANGES` - Dependency changes indicator

**Applied Labels**:
- `security-analysis` - Base security analysis label
- `security:high-risk`, `security:medium-risk`, `security:low-risk` - Risk-based labels
- `security-review-required` - Manual review requirement
- `authentication` - Authentication flow changes
- `dependencies` - Dependency changes

## WebAuthn Security Focus

All scripts are specifically designed for WebAuthn authentication systems and focus on:

### Vulnerability Categories
- **PoisonSeed attacks** - Cross-origin authentication abuse
- **Username enumeration** (CVE-2024-39912) - User existence disclosure
- **Replay attacks** - Challenge/response reuse
- **Credential tampering** - Signature validation bypass
- **Information leakage** - Sensitive data in error responses

### Security Patterns
- **Origin validation** - Proper relying party validation
- **Challenge generation** - Cryptographically secure randomness
- **Credential verification** - Signature validation integrity
- **Error handling** - No information leakage
- **Session management** - Secure token handling

## Integration with CI/CD

These scripts are designed to integrate with the `pr-security-analysis.yml` GitHub Actions workflow:

```yaml
# Example workflow integration
- name: Analyze security impact
  env:
    AUTH_FLOWS_FILES: ${{ steps.changed-files.outputs.auth_flows_all_changed_files }}
    # ... other environment variables
  run: |
    chmod +x scripts/security/analyze-changes.sh
    scripts/security/analyze-changes.sh
```

## Dependencies

### Required
- **Bash 4.0+** - For shell scripts
- **Node.js 16+** - For JavaScript scripts
- **jq** - For JSON processing
- **GitHub Actions environment** - For workflow integration

### Optional
- **@anthropic-ai/sdk** - For AI-powered analysis (fallback available)
- **TypeScript** - For enhanced JavaScript analysis

## Error Handling

All scripts implement robust error handling:

- **Graceful degradation** - Continue with reduced functionality when AI unavailable
- **Fallback analysis** - Provide basic security analysis when advanced features fail
- **Clear error messages** - Detailed logging with timestamps
- **Exit codes** - Proper exit codes for CI/CD integration

## Security Considerations

- **API key handling** - Secure environment variable usage
- **File validation** - Input validation for all processed files
- **Permissions** - Minimal required permissions for GitHub API
- **Error information** - No sensitive data in error messages

## Testing

### Manual Testing
```bash
# Test change analysis
export AUTH_FLOWS_FILES="test1.kt test2.kt"
export SECURITY_COMPONENTS_FILES="test3.kt"
export DEPENDENCIES_FILES=""
export INFRASTRUCTURE_FILES=""
export ALL_CHANGED_FILES="test1.kt test2.kt test3.kt"
export GITHUB_OUTPUT="/tmp/test_output"
./analyze-changes.sh
```

### GitHub Actions Testing
Scripts are designed to be tested within GitHub Actions environment with proper mocking for offline development.

## Troubleshooting

### Common Issues

1. **Script not executable**: Run `chmod +x scripts/security/*.sh *.js`
2. **Missing jq**: Install with `apt-get install jq` or `brew install jq`
3. **Node.js dependencies**: Run `npm install` in repository root
4. **AI analysis failing**: Verify `ANTHROPIC_API_KEY` is set; fallback analysis will be used

### Debug Logging
All scripts include timestamp-based logging. Use `set -x` in shell scripts for verbose debugging.

## Contributing

When modifying security scripts:

1. **Maintain WebAuthn focus** - Ensure security patterns remain WebAuthn-specific
2. **Test thoroughly** - Verify both AI and fallback modes
3. **Update documentation** - Keep this README current
4. **Follow security practices** - No hardcoded secrets or sensitive data
5. **Validate outputs** - Ensure GitHub Actions integration remains functional

## Security Contact

For security-related issues with these scripts, please follow the repository's security reporting guidelines.