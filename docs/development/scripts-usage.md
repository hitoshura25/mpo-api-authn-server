# Scripts Directory - Organized Project Scripts

This directory contains organized, reusable scripts categorized by functionality for improved maintainability and clarity.

## Directory Structure

```
scripts/
├── core/                      # Essential utilities used across workflows
│   ├── validate-markdown.sh   # Markdown syntax validation
│   ├── version-manager.sh     # Synchronized version generation  
│   └── run-android-tests.sh   # Cross-platform Android testing
├── docker/                    # Docker-related operations
│   ├── detect-changes.sh      # Docker image change detection
│   ├── scan-security.sh       # Comprehensive Docker security scanning
│   ├── publish-dockerhub.sh   # DockerHub publishing with conditional logic
│   └── cleanup-ghcr.sh        # GitHub Container Registry cleanup
├── security/                  # Security analysis and testing
│   ├── analyze-changes.sh     # Change-based security analysis
│   ├── analyze-pr.sh          # AI-powered PR security analysis
│   ├── generate-tests.sh      # Security test generation
│   ├── create-security-comment.cjs # PR security comment generation
│   └── add-security-labels.cjs # Automated security labeling
├── ci/                       # CI/CD specific scripts
│   ├── create-e2e-results-comment.cjs # E2E test result comments
│   └── add-vulnerability-pr-labels.cjs # Vulnerability PR labeling
├── monitoring/               # Monitoring and vulnerability scanning
│   ├── enhanced-monitor.sh   # Enhanced vulnerability monitoring
│   ├── vulnerability-monitor.js # Core vulnerability monitoring
│   └── ai-enhanced-vulnerability-monitor.js # AI-enhanced monitoring
└── setup/                    # One-time setup scripts
    ├── setup-vulnerability-monitoring.sh # Vulnerability monitoring setup
    └── setup-github-packages.sh # GitHub packages configuration
```

## Core Scripts (`scripts/core/`)

### validate-markdown.sh
**Purpose**: Validates markdown files for syntax errors and formatting issues.

**Usage**:
```bash
./scripts/core/validate-markdown.sh
```

### version-manager.sh
**Purpose**: Generates synchronized versions for both Android and npm clients.

**Usage**:
```bash
./scripts/core/version-manager.sh generate
./scripts/core/version-manager.sh validate "1.0.42"
```

### run-android-tests.sh
**Purpose**: Executes Android instrumentation tests with proper environment setup.

**Usage**:
```bash
./scripts/core/run-android-tests.sh
```

## Docker Scripts (`scripts/docker/`)

### detect-changes.sh
**Purpose**: Compares Docker image digests between GHCR and DockerHub to determine if publishing is needed.

**Usage**:
```bash
./scripts/docker/detect-changes.sh <image_type>
# where image_type is either "webauthn-server" or "test-credentials"
```

### scan-security.sh
**Purpose**: Performs comprehensive security scanning of Docker images with vulnerability assessment.

**Usage**:
```bash
./scripts/docker/scan-security.sh <webauthn_changed> <test_credentials_changed>
```

### publish-dockerhub.sh
**Purpose**: Publishes Docker images to DockerHub with conditional logic based on detected changes.

**Usage**:
```bash
./scripts/docker/publish-dockerhub.sh <webauthn_changed> <test_credentials_changed>
```

### cleanup-ghcr.sh
**Purpose**: Cleans up old Docker images from GitHub Container Registry to prevent storage bloat.

**Usage**:
```bash
./scripts/docker/cleanup-ghcr.sh [repository_owner]
```

## Security Scripts (`scripts/security/`)

### analyze-changes.sh
**Purpose**: Analyzes code changes for potential security implications.

**Usage**:
```bash
./scripts/security/analyze-changes.sh
```

### analyze-pr.sh
**Purpose**: **3-Tier AI Security Analysis** with intelligent mode detection and WebAuthn specialization:
- **Tier 1**: Official Anthropic Security Action (primary)
- **Tier 2**: Gemini WebAuthn-focused analysis (specialized fallback)
- **Tier 3**: Template-based analysis (always-available fallback)

**Usage**:
```bash
# Standard mode (tries all tiers)
./scripts/security/analyze-pr.sh <changed_files_json> <pr_title> <pr_body> <risk_level>

# Gemini-only mode (skip Tier 1, focus on WebAuthn)
GEMINI_ONLY_MODE=true ./scripts/security/analyze-pr.sh <args>

# Template-only mode (skip AI, zero-cost analysis)
TEMPLATE_ONLY_MODE=true ./scripts/security/analyze-pr.sh <args>
```

### generate-tests.sh
**Purpose**: **3-Tier Test Generation** with mode-aware prompts and WebAuthn specialization:
- **Tier 1**: Anthropic test generation (primary)
- **Tier 2**: Gemini WebAuthn-focused test generation (specialized)  
- **Tier 3**: Template-based test generation (always-available)

**Usage**:
```bash
# Standard mode (tries all tiers)
./scripts/security/generate-tests.sh

# Gemini-only mode (WebAuthn-focused test generation)
GEMINI_ONLY_MODE=true ./scripts/security/generate-tests.sh

# Template-only mode (zero-cost template tests)
TEMPLATE_ONLY_MODE=true ./scripts/security/generate-tests.sh
```

## CI Scripts (`scripts/ci/`)

### create-e2e-results-comment.cjs
**Purpose**: Creates GitHub PR comments with E2E test results and summaries.

### add-vulnerability-pr-labels.cjs
**Purpose**: Automatically adds appropriate labels to PRs based on vulnerability scans.

## Monitoring Scripts (`scripts/monitoring/`)

### enhanced-monitor.sh
**Purpose**: Enhanced vulnerability monitoring with comprehensive checks.

**Usage**:
```bash
./scripts/monitoring/enhanced-monitor.sh
```

### vulnerability-monitor.js
**Purpose**: Core vulnerability monitoring system for WebAuthn/FIDO2 security.

### ai-enhanced-vulnerability-monitor.js
**Purpose**: AI-enhanced vulnerability monitoring with advanced analysis capabilities.

## Setup Scripts (`scripts/setup/`)

### setup-vulnerability-monitoring.sh
**Purpose**: One-time setup for vulnerability monitoring system.

**Usage**:
```bash
./scripts/setup/setup-vulnerability-monitoring.sh
```

### setup-github-packages.sh
**Purpose**: Configures local environment for GitHub Packages consumption.

**Usage**:
```bash
./scripts/setup/setup-github-packages.sh
```

## Workflow Integration

### Used in GitHub Actions
- **build-and-test.yml**: 
   - Uses `scripts/core/version-manager.sh`
- **e2e-tests.yml**:
   - Uses `scripts/core/run-android-tests.sh`
   - Uses `scripts/ci/create-e2e-results-comment.cjs`
- **main-branch-post-processing.yml**:
   - Uses `scripts/docker/detect-changes.sh`
   - Uses `scripts/docker/scan-security.sh`
   - Uses `scripts/docker/publish-dockerhub.sh`
   - Uses `scripts/docker/cleanup-ghcr.sh`
- **security-analysis.yml**:
   - Uses `scripts/security/analyze-changes.sh`
   - Uses `scripts/security/analyze-pr.sh`
   - Uses `scripts/security/generate-tests.sh`
   - Uses `scripts/security/create-security-comment.cjs`
   - Uses `scripts/security/add-security-labels.cjs`
- **vulnerability-monitor.yml**:
   - Uses `scripts/monitoring/enhanced-monitor.sh`
   - Uses `scripts/ci/add-vulnerability-pr-labels.cjs`

### Local Development
- Security test execution after changes
- Docker image management
- Vulnerability monitoring setup

## Common Operations

### Make scripts executable
```bash
find scripts/ -name "*.sh" -exec chmod +x {} \;
find scripts/ -name "*.js" -exec chmod +x {} \;  
find scripts/ -name "*.cjs" -exec chmod +x {} \;
```

### Test individual scripts
```bash
./scripts/docker/detect-changes.sh webauthn-server
./scripts/security/analyze-pr.sh '["file1.kt", "file2.kt"]' "PR Title" "PR Body" "MEDIUM"
```

## Best Practices

1. **Always make scripts executable**: `chmod +x script.sh`
2. **Test scripts locally** before committing changes
3. **Use proper error handling** with `set -e` in bash scripts
4. **Validate required environment variables** before execution
5. **Use descriptive output** for CI/CD pipeline visibility

## Script Categories by Function

- **Essential Utilities** (`core/`): Scripts required for basic development workflow
- **Docker Operations** (`docker/`): Container management and registry operations  
- **Security** (`security/`): Security analysis and vulnerability management
- **CI/CD** (`ci/`): Scripts specific to continuous integration pipelines
- **Monitoring** (`monitoring/`): Vulnerability and security monitoring systems
- **Setup** (`setup/`): One-time configuration and setup scripts