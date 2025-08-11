# Security Scripts Documentation - 3-Tier AI Analysis

This directory contains security-focused automation scripts implementing a comprehensive **3-Tier AI Security Analysis** system for WebAuthn authentication systems. The scripts are designed for GitHub Actions workflows and provide intelligent fallback mechanisms for reliable security analysis of pull requests.

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

**Purpose**: Performs comprehensive AI-powered security analysis using the **3-Tier AI Security Analysis** system with intelligent mode detection and specialized WebAuthn focus.

**Usage**:
```bash
./analyze-pr.sh <changed_files_json> <pr_title> <pr_body> <risk_level>
```

**Environment Variables**:
- `ANTHROPIC_API_KEY` - API key for Anthropic AI analysis (Tier 1, optional)
- `GEMINI_API_KEY` - API key for Google Gemini AI analysis (Tier 2, optional)
- `GEMINI_ONLY_MODE` - Set to "true" to skip Tier 1 and use Tier 2 WebAuthn-focused analysis
- `TEMPLATE_ONLY_MODE` - Set to "true" to skip AI and use Tier 3 template analysis
- `PR_NUMBER` - Pull request number
- `WEBAUTHN_SECURITY_AGENT_PATH` - Path to WebAuthn security agent file
- `VULNERABILITY_DB_PATH` - Path to vulnerability database JSON

**Outputs**:
- `security-analysis-results.json` - Complete analysis results
- GitHub Actions outputs for security score, vulnerabilities, and recommendations

**Features**:
- **3-Tier Analysis Architecture**: Official Anthropic → Gemini WebAuthn-Focused → Template Analysis
- **Intelligent Mode Detection**: Supports Standard, Gemini-Only, and Template-Only modes
- **WebAuthn-Specialized Tier 2**: Gemini analysis specifically focused on FIDO2/WebAuthn vulnerabilities
- **Official Anthropic Integration**: Uses official `anthropics/claude-code-security-review@v1` action when available
- **Automatic Fallback Logic**: Seamless tier progression based on availability and cost optimization
- **Enhanced Token Optimization**: Smart prompt sizing and provider selection for cost efficiency

### 3. generate-tests.sh

**Purpose**: Generates security test implementations for detected vulnerabilities using the **3-Tier Test Generation** system with mode-aware prompt optimization.

**Usage**:
```bash
./generate-tests.sh
```

**Requirements**:
- `security-analysis-results.json` from previous analysis
- Node.js environment with optional AI dependencies

**Environment Variables**:
- `ANTHROPIC_API_KEY` - API key for Anthropic AI test generation (Tier 1, optional)
- `GEMINI_API_KEY` - API key for Google Gemini AI test generation (Tier 2, optional)
- `GEMINI_ONLY_MODE` - Set to "true" to use Gemini-only WebAuthn-focused test generation
- `TEMPLATE_ONLY_MODE` - Set to "true" to skip AI and use template-based test generation

**Outputs**:
- `security-test-implementations.json` - Generated test code and metadata

**Features**:
- **3-Tier Test Generation**: Anthropic → Gemini WebAuthn-Focused → Template Generation
- **Mode-Aware Prompts**: Different prompt strategies for Standard vs WebAuthn-focused generation
- **WebAuthn-Specific Templates**: Specialized test templates for FIDO2 vulnerabilities
- **Provider Redundancy**: Seamless fallback with detailed tier reporting
- **Enhanced Metadata**: Complete tier tracking and generation source attribution

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

## 3-Tier AI Security Analysis Architecture

The security scripts implement a comprehensive **3-Tier AI Security Analysis** system designed for production reliability and cost optimization:

### Tier Selection Logic

#### **Tier 1: Official Anthropic Security Action** (Primary)
- **Tool**: Official `anthropics/claude-code-security-review@v1` GitHub Action
- **Purpose**: Comprehensive security analysis maintained by Anthropic experts
- **Triggers**: All PRs with security-relevant changes (unless Gemini-only mode)
- **Coverage**: Full spectrum security analysis (OWASP, injection attacks, etc.)
- **Cost**: Medium, but comprehensive and officially maintained

#### **Tier 2: Gemini WebAuthn-Focused Analysis** (Specialized Fallback)
- **Tool**: Custom Google Gemini 1.5 Pro analysis with WebAuthn specialization
- **Purpose**: WebAuthn-specific security patterns when Tier 1 unavailable
- **Triggers**: When Tier 1 fails OR when `GEMINI_ONLY_MODE=true`
- **Coverage**: **Specialized WebAuthn vulnerabilities**:
  - PoisonSeed attack patterns
  - Username enumeration (CVE-2024-39912)
  - Challenge reuse and replay attacks
  - Origin/RPID validation bypass
  - WebAuthn ceremony tampering
- **Cost**: Lower than Tier 1, optimized for WebAuthn focus
- **Assumption**: General security (SQL injection, XSS) handled by Tier 1 or existing tests

#### **Tier 3: Template Analysis** (Final Fallback)
- **Tool**: Zero-cost template-based security analysis
- **Purpose**: Ensure analysis always runs regardless of AI availability
- **Triggers**: When both AI providers fail OR when `TEMPLATE_ONLY_MODE=true`
- **Coverage**: File pattern analysis, risk assessment, basic vulnerability detection
- **Cost**: None, but limited analysis depth

### Mode Operation

#### **Standard Mode** (Default)
- **Flow**: Tier 1 → Tier 2 (if Tier 1 fails) → Tier 3 (if both fail)
- **Use Case**: Production workflows with full AI coverage
- **Optimization**: Automatic tier progression based on availability and budget

#### **Gemini-Only Mode** (`GEMINI_ONLY_MODE=true`)
- **Flow**: Skip Tier 1 → Tier 2 WebAuthn-focused → Tier 3 (if Tier 2 fails)
- **Use Case**: Cost optimization or when focusing on WebAuthn-specific issues
- **Benefits**: Reduced costs, WebAuthn specialization, assumes general security handled elsewhere

#### **Template-Only Mode** (`TEMPLATE_ONLY_MODE=true`)
- **Flow**: Skip all AI → Tier 3 only
- **Use Case**: Budget constraints, offline development, or basic pattern analysis
- **Benefits**: Zero cost, always available, fast execution

### Intelligent Fallback Triggers
Tier progression occurs when:
- **Rate Limits**: HTTP 429 responses
- **Budget Issues**: HTTP 402 (payment required) responses  
- **Authentication Failures**: Invalid API keys
- **Quota Exceeded**: API usage limits reached
- **Service Unavailability**: Provider downtime or errors

### Strategic Benefits

#### **Reliability**
- **Always-On Analysis**: Guaranteed security analysis regardless of AI provider status
- **Multi-Provider Redundancy**: No single point of failure
- **Graceful Degradation**: Quality degrades predictably across tiers

#### **Cost Optimization**
- **Intelligent Tier Selection**: Automatic optimization based on budget and availability
- **Specialized Analysis**: Tier 2 provides focused WebAuthn analysis at lower cost
- **Zero-Cost Fallback**: Tier 3 ensures analysis continues when budgets exhausted

#### **Production Quality**
- **Official Tooling**: Tier 1 uses Anthropic's official security action
- **WebAuthn Expertise**: Tier 2 specialized for FIDO2/WebAuthn attack patterns
- **Comprehensive Coverage**: Each tier optimized for specific security domains

#### **Operational Excellence**
- **Transparent Reporting**: Clear indication of which tier provided results
- **Cost Tracking**: Token estimation and provider cost attribution
- **Debug Capability**: Detailed logging for troubleshooting tier selection

### Enhanced Logging and Transparency
- **Tier Identification**: Clear logging of which tier is executing and why
- **Fallback Reasoning**: Detailed explanation of tier progression triggers
- **Cost Tracking**: Token estimation and provider cost attribution
- **Performance Metrics**: Analysis timing and efficiency reporting
- **Provider Attribution**: Complete metadata about analysis source
- **GitHub Actions Labels**: Automatic PR labeling with tier information (`security:tier-1-anthropic`, `security:tier-2-gemini`, `security:tier-3-template`)

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

These scripts integrate with the **3-Tier AI Security Analysis** GitHub Actions workflow (`.github/workflows/security-analysis.yml`):

### Workflow Architecture
```yaml
# 3-Tier Analysis Jobs
jobs:
  # Tier 1: Official Anthropic Security Review
  tier1-anthropic-security-review:
    uses: anthropics/claude-code-security-review@v1
    if: env.ANTHROPIC_TIER_ENABLED == 'true'
    
  # Tier 2: Gemini WebAuthn Analysis  
  tier2-gemini-webauthn-analysis:
    needs: tier1-anthropic-security-review
    if: needs.tier1-anthropic-security-review.outputs.analysis-completed != 'true'
    env:
      GEMINI_ONLY_MODE: "true"
    run: scripts/security/analyze-pr.sh
    
  # Tier 3: Template Analysis
  tier3-template-analysis:
    needs: [tier1-anthropic-security-review, tier2-gemini-webauthn-analysis]
    if: |
      needs.tier1-anthropic-security-review.outputs.analysis-completed != 'true' &&
      needs.tier2-gemini-webauthn-analysis.outputs.analysis-completed != 'true'
    env:
      TEMPLATE_ONLY_MODE: "true"
    run: scripts/security/analyze-pr.sh
```

### Configuration Variables
```yaml
env:
  # Tier Control
  ANTHROPIC_TIER_ENABLED: true
  GEMINI_TIER_ENABLED: true  
  TEMPLATE_TIER_ENABLED: true
  
  # Analysis Configuration
  HIGH_RISK_SCORE_THRESHOLD: 7.0
  MEDIUM_RISK_SCORE_THRESHOLD: 4.0
  BLOCK_MERGE_ON_CRITICAL: true
```

## Dependencies

### Required
- **Bash 4.0+** - For shell scripts
- **Node.js 16+** - For JavaScript scripts
- **jq** - For JSON processing
- **GitHub Actions environment** - For workflow integration

### Optional (AI Dependencies)
- **Official Anthropic Action** - For Tier 1 analysis (`anthropics/claude-code-security-review@v1`)
- **@anthropic-ai/sdk** - For custom Anthropic AI analysis (Tier 1 fallback)
- **@google/generative-ai** - For Gemini AI analysis (Tier 2)
- **TypeScript** - For enhanced JavaScript analysis and type safety

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
4. **AI analysis failing**: Check tier configuration and API keys:
   - Verify `ANTHROPIC_API_KEY` for Tier 1 analysis
   - Verify `GEMINI_API_KEY` for Tier 2 analysis
   - Scripts automatically progress through available tiers
   - Template analysis (Tier 3) always available as final fallback
   - Check GitHub Actions logs for tier progression details

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