# Scripts Directory - Refactored GitHub Actions Scripts

This directory contains organized, reusable scripts that have been extracted from GitHub Actions workflows to improve maintainability, testing, and reusability.

## Directory Structure

```
scripts/
├── docker/                 # Docker-related operations
│   ├── detect-changes.sh   # Docker image change detection
│   ├── scan-security.sh    # Comprehensive Docker security scanning
│   ├── publish-dockerhub.sh# DockerHub publishing with conditional logic
│   └── cleanup-ghcr.sh     # GitHub Container Registry cleanup
├── security/               # Security analysis and testing
│   ├── analyze-pr.sh       # AI-powered PR security analysis
│   └── generate-tests.sh   # Security test generation
├── monitoring/             # Vulnerability monitoring
│   └── enhanced-monitor.sh # AI-enhanced vulnerability monitoring
└── README.md              # This file
```

## Docker Scripts (`scripts/docker/`)

### detect-changes.sh
**Purpose**: Compares Docker image digests between GHCR and DockerHub to determine if publishing is needed.

**Usage**:
```bash
./scripts/docker/detect-changes.sh <image_type>
# where image_type is either "webauthn-server" or "test-credentials"
```

**Environment Variables**:
- `DOCKER_REGISTRY` - Docker registry URL (default: ghcr.io)
- `DOCKER_IMAGE_NAME` - GHCR image name for webauthn-server
- `DOCKER_TEST_CREDENTIALS_IMAGE_NAME` - GHCR image name for test-credentials
- `DOCKERHUB_SERVER_REPO` - DockerHub repository for webauthn-server
- `DOCKERHUB_TEST_CREDENTIALS_REPO` - DockerHub repository for test-credentials

**Outputs**: Sets GitHub Actions output `has-changes` (true/false)

### scan-security.sh
**Purpose**: Performs comprehensive security scanning using Trivy scanner for vulnerabilities, secrets, and configuration issues.

**Usage**:
```bash
./scripts/docker/scan-security.sh <webauthn_changed> <test_credentials_changed>
# where parameters are "true" or "false"
```

**Features**:
- Installs Trivy scanner automatically
- Scans for vulnerabilities, secrets, and configuration issues
- Blocks publishing on critical vulnerabilities
- Generates detailed JSON reports

### publish-dockerhub.sh
**Purpose**: Publishes Docker images from GHCR to DockerHub with conditional logic.

**Usage**:
```bash
./scripts/docker/publish-dockerhub.sh <webauthn_changed> <test_credentials_changed>
```

**Features**:
- Conditional publishing based on change detection
- Automatic re-tagging from GHCR to DockerHub
- Support for repository description updates

### cleanup-ghcr.sh
**Purpose**: Cleans up old versions of Docker packages in GHCR to prevent registry bloat.

**Usage**:
```bash
./scripts/docker/cleanup-ghcr.sh [repository_owner]
```

**Features**:
- Keeps latest 5 versions, deletes older ones
- Uses GitHub API for package management
- Graceful error handling

## Security Scripts (`scripts/security/`)

### analyze-pr.sh
**Purpose**: AI-powered security analysis of pull request changes using Anthropic Claude API.

**Usage**:
```bash
./scripts/security/analyze-pr.sh <changed_files_json> <pr_title> <pr_body> <risk_level>
```

**Environment Variables**:
- `ANTHROPIC_API_KEY` - API key for AI analysis (optional, falls back to standard analysis)
- `WEBAUTHN_SECURITY_AGENT_PATH` - Path to WebAuthn security agent file
- `VULNERABILITY_DB_PATH` - Path to vulnerability database JSON

**Features**:
- AI-powered vulnerability detection
- WebAuthn-specific security analysis
- Fallback to standard analysis if AI unavailable
- Generates comprehensive security reports

### generate-tests.sh
**Purpose**: Generates security test implementations for detected vulnerabilities using AI.

**Usage**:
```bash
./scripts/security/generate-tests.sh
# (Requires security-analysis-results.json from previous analysis)
```

**Features**:
- AI-generated Kotlin test methods
- Template-based fallback for non-AI environments
- Integration with existing VulnerabilityProtectionTest.kt patterns

## Monitoring Scripts (`scripts/monitoring/`)

### enhanced-monitor.sh
**Purpose**: Enhanced vulnerability monitoring with AI capabilities and fallback to standard monitoring.

**Usage**:
```bash
./scripts/monitoring/enhanced-monitor.sh
```

**Features**:
- AI-enhanced monitoring when available
- Automatic fallback to standard monitoring
- Security test execution after changes
- Comprehensive logging and reporting

## Benefits of This Refactoring

### 1. **Maintainability**
- ✅ Scripts are organized in logical directories
- ✅ Each script has a single, well-defined responsibility
- ✅ Comprehensive documentation and error handling
- ✅ Consistent logging and output formatting

### 2. **Testability**
- ✅ Scripts can be tested independently outside of CI/CD
- ✅ Proper error handling and exit codes
- ✅ Support for both CI and local development environments

### 3. **Reusability**
- ✅ Scripts can be shared across multiple workflows
- ✅ Parameterized for different use cases
- ✅ Environment variable configuration

### 4. **Version Control**
- ✅ Script changes are properly versioned
- ✅ Easy to track changes and improvements
- ✅ Better collaboration through code review

### 5. **Security**
- ✅ Proper input validation
- ✅ Secure handling of environment variables
- ✅ Comprehensive error trapping

## Updated Workflows

The following workflows have been updated to use these extracted scripts:

1. **main-branch-post-processing.yml**
   - Uses `scripts/docker/detect-changes.sh`
   - Uses `scripts/docker/scan-security.sh`
   - Uses `scripts/docker/publish-dockerhub.sh`
   - Uses `scripts/docker/cleanup-ghcr.sh`

2. **pr-security-analysis.yml**
   - Uses `scripts/security/analyze-pr.sh`
   - Uses `scripts/security/generate-tests.sh`

3. **vulnerability-monitor.yml**
   - Uses `scripts/monitoring/enhanced-monitor.sh`

## Running Scripts Locally

All scripts can be run locally for testing and development:

```bash
# Make scripts executable
find scripts/ -name "*.sh" -exec chmod +x {} \;

# Example: Test change detection locally
export DOCKER_REGISTRY="ghcr.io"
export DOCKER_IMAGE_NAME="hitoshura25/webauthn-server"
export DOCKERHUB_SERVER_REPO="hitoshura25/webauthn-server"
./scripts/docker/detect-changes.sh webauthn-server

# Example: Test security analysis locally
export ANTHROPIC_API_KEY="your-api-key"
./scripts/security/analyze-pr.sh '["file1.kt", "file2.kt"]' "PR Title" "PR Body" "MEDIUM"
```

## Best Practices

1. **Always make scripts executable**: `chmod +x script.sh`
2. **Test scripts locally** before using in workflows
3. **Use proper error handling** with `set -euo pipefail`
4. **Validate required environment variables** before execution
5. **Provide comprehensive logging** with timestamps
6. **Follow consistent naming conventions** for parameters and outputs
7. **Document all environment variables and usage** in script headers

This refactoring significantly improves the maintainability and testability of the GitHub Actions workflows while preserving all existing functionality.