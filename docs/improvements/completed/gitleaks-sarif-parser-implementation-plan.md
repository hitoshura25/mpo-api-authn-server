# GitLeaks SARIF Parser Implementation Plan

## ⚠️ **IMPLEMENTATION STATUS: DEFER**

**This parser implementation is DEFERRED and should NOT be prioritized for the enhanced parsing architecture.**

**Reasons for Deferral**:
1. ❌ **Zero Training Data**: Current codebase has 0 secrets detected (which is good for security, but means no training examples)
2. ❌ **Non-Deterministic Remediation**: Secrets require manual service-specific rotation, not code fixes
3. ❌ **Low Training Value**: Training Tier ⭐ (Tier 3) - cannot teach code transformations
4. ❌ **High Complexity**: Would require 208 service-specific remediation guides
5. ❌ **Security Risk**: Handling actual secret values in training pipeline requires careful sanitization
6. ✅ **Higher Priorities**: Focus on Trivy (Tier 1), Checkov (Tier 2), Semgrep (Tier 1-2) first

**When to Revisit**: Only implement when:
- ✅ All Tier 1-2 parsers (Trivy, Checkov, Semgrep, ZAP) are complete
- ✅ We have actual secret detection findings to learn from
- ✅ Training pipeline can handle non-code remediation guidance

**Recommendation**: Keep this document as reference, but do NOT include in enhanced parsing architecture implementation roadmap.

---

**Status**: Planning (DEFERRED)
**Priority**: LOW (No secrets found in current codebase, limited training value)
**Estimated Effort**: 2 hours (parser only) + significant effort for remediation knowledge base
**Created**: 2025-10-07

## Executive Summary

Analyze GitLeaks SARIF parser requirements for secret detection findings. **Current finding**: No secrets detected in codebase (0 vulnerabilities). GitLeaks provides **limited training data value** compared to Trivy/Checkov because secrets cannot be "fixed" with version upgrades - they require manual rotation/removal.

**Recommendation**: **Defer implementation** until higher-priority parsers (Trivy, Checkov, Semgrep) are complete and we have actual secret detection findings to learn from.

## Problem Statement

### Current State
- **Generic SARIF Parser**: `parsers/sarif_parser.py` handles GitLeaks SARIF as generic findings
- **No Findings**: Current test dataset has 0 secrets detected (good security posture!)
- **No Training Data**: Without findings, cannot validate parser or generate training examples

### Why GitLeaks is Different
Unlike dependency/config vulnerability tools, GitLeaks detects **secrets in code**:
- ❌ **No "Fix Version"**: Secrets can't be "upgraded" like dependencies
- ❌ **No Deterministic Remediation**: Each secret requires unique manual action
- ⚠️ **High Sensitivity**: Training data would contain information about secret types/locations
- ⚠️ **Manual Process**: Remediation requires rotating credentials, updating git history

## GitLeaks SARIF Data Structure Analysis

### Tool Metadata

```json
{
  "tool": {
    "driver": {
      "name": "gitleaks",
      "version": "N/A",
      "rules": [
        {
          "id": "aws-access-token",
          "shortDescription": {
            "text": "Uncovered a possible AWS Access Token, risking unauthorized AWS service access and data exposure."
          }
        }
        // 208 total secret detection rules
      ]
    }
  }
}
```

**Detection Rules**: 208 patterns covering:
- Cloud Provider Keys: AWS, Azure, GCP, Alibaba
- API Tokens: GitHub, GitLab, Stripe, Slack, SendGrid
- Database Credentials: PostgreSQL, MongoDB, Redis
- Encryption Keys: Age, OpenSSH, PGP
- Generic Patterns: Private keys, JWT tokens, passwords

### Example Result Structure (When Secret Found)

```json
{
  "ruleId": "aws-access-token",
  "ruleIndex": 42,
  "level": "error",
  "message": {
    "text": "Uncovered a possible AWS Access Token, risking unauthorized AWS service access and data exposure."
  },
  "locations": [
    {
      "physicalLocation": {
        "artifactLocation": {
          "uri": ".github/workflows/deploy.yml",
          "uriBaseId": "ROOTPATH"
        },
        "region": {
          "startLine": 25,
          "startColumn": 15,
          "endLine": 25,
          "endColumn": 55,
          "snippet": {
            "text": "AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE"
          }
        }
      }
    }
  ],
  "partialFingerprints": {
    "commitSha": "a1b2c3d4e5f6",
    "email": "developer@example.com",
    "author": "John Doe",
    "date": "2024-01-15T10:30:00Z"
  }
}
```

### Available Fields

✅ **Secret Classification**:
- `ruleId`: Type of secret detected (e.g., `aws-access-token`, `github-pat`)
- `message.text`: Generic warning about risk
- `level`: Always `error` (secrets are always critical)

✅ **Location Context**:
- `artifactLocation.uri`: File containing the secret
- `region.startLine/endLine`: Exact line number(s)
- `region.startColumn/endColumn`: Character position
- `snippet.text`: The leaked secret (may be redacted)

✅ **Git History Context** (unique to GitLeaks):
- `partialFingerprints.commitSha`: Git commit where secret was introduced
- `partialFingerprints.author`: Who committed it
- `partialFingerprints.email`: Committer email
- `partialFingerprints.date`: When it was committed

### What's Missing (Critical for Training)

❌ **No Remediation Guidance**: No "fixed version" or upgrade path
❌ **No Secret Value Sanitization**: May expose actual secrets in SARIF
❌ **No Rotation Instructions**: No tool-specific rotation guidance
❌ **No Environment Variable Examples**: No code examples for proper secrets management

## Remediation Strategies (Manual, Non-Deterministic)

### General Process
1. **Immediate Actions**:
   - Rotate/revoke the exposed secret (service-specific process)
   - Audit access logs for unauthorized usage
   - Monitor for suspicious activity

2. **Code Remediation**:
   - Remove hardcoded secret from source code
   - Replace with environment variable reference
   - Update deployment configs to inject secret securely

3. **Git History Cleanup** (if secret was committed):
   - Use `git filter-branch` or `BFG Repo Cleaner`
   - Force push to rewrite history (destructive!)
   - Notify team members to re-clone

4. **Prevention**:
   - Add secret to `.gitignore` / `.gitleaksignore`
   - Use secrets management tools (Vault, AWS Secrets Manager)
   - Enable pre-commit hooks to prevent future leaks

### Service-Specific Rotation Examples

#### AWS Access Token
```bash
# 1. Rotate via AWS Console or CLI
aws iam create-access-key --user-name <username>
aws iam delete-access-key --user-name <username> --access-key-id <old-key-id>

# 2. Update environment variables
export AWS_ACCESS_KEY_ID=<new-key>
export AWS_SECRET_ACCESS_KEY=<new-secret>

# 3. Update CI/CD secrets (GitHub Actions, etc.)
```

#### GitHub Personal Access Token
```bash
# 1. Revoke old token via GitHub Settings → Developer Settings → Personal Access Tokens
# 2. Generate new token with same scopes
# 3. Update git remote URL (if using token for auth)
git remote set-url origin https://<new-token>@github.com/user/repo.git

# 4. Update CI/CD secrets
```

#### Database Password
```sql
-- 1. Connect as superuser
ALTER USER myapp WITH PASSWORD 'new-secure-password';

-- 2. Update application config
DATABASE_URL=postgresql://myapp:new-password@localhost/mydb

-- 3. Restart application
```

### Code Transformation Example

**Before (Insecure)**:
```yaml
# .github/workflows/deploy.yml
env:
  AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**After (Secure)**:
```yaml
# .github/workflows/deploy.yml
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

## Training Data Challenges

### Problem: Secrets are NOT Like Dependencies

| Aspect | Dependencies (Trivy) | Secrets (GitLeaks) |
|--------|---------------------|-------------------|
| **Fix Type** | Version upgrade | Manual rotation |
| **Deterministic?** | ✅ Yes (upgrade to X.Y.Z) | ❌ No (service-specific) |
| **Code Example** | ✅ `implementation("pkg:1.2.3")` | ⚠️ Generic placeholders |
| **Automation** | ✅ Dependency bots | ❌ Manual process |
| **Training Value** | ✅ High (objective fixes) | ⚠️ Low (subjective process) |

### Training Data Quality Issues

1. **Non-Deterministic Remediation**:
   - "Rotate AWS key" requires AWS Console/CLI (not code change)
   - "Regenerate GitHub token" requires GitHub UI (not code change)
   - Different services have different rotation procedures

2. **Sensitive Information Exposure**:
   - SARIF may contain actual secret values (security risk)
   - Training model on secret patterns could leak information
   - Need careful sanitization before training

3. **Limited Generalization**:
   - Each secret type requires unique remediation steps
   - Cannot generalize across services (AWS ≠ GitHub ≠ Stripe)
   - Model would need to memorize 208 different rotation procedures

4. **Prevention vs Remediation**:
   - Best "fix" is to prevent secrets in code (pre-commit hooks)
   - Remediation (rotating existing secrets) is damage control
   - Training on remediation doesn't teach prevention

## Implementation Design (IF Pursued)

### 1. File: `parsers/sarif_gitleaks_parser.py`

#### Key Functions

##### `parse_gitleaks_sarif(filepath: str) -> List[Dict]`
Main entry point:
1. Loads SARIF JSON
2. Validates tool name is "gitleaks"
3. Builds rule lookup for secret types
4. Extracts findings with git history context
5. **Sanitizes secret values** (redacts actual secrets)
6. Returns vulnerability dicts

##### `_sanitize_secret_snippet(snippet: str, rule_id: str) -> str`
**CRITICAL SECURITY FUNCTION**: Redacts actual secret values:
```python
def _sanitize_secret_snippet(snippet: str, rule_id: str) -> str:
    """
    Redact actual secret value, show only context.

    Input:  "AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE"
    Output: "AWS_ACCESS_KEY_ID: AKIA****************"
    """
    # Pattern-based redaction
    if 'aws' in rule_id.lower():
        return re.sub(r'AKIA[0-9A-Z]{16}', 'AKIA****************', snippet)
    elif 'github' in rule_id.lower():
        return re.sub(r'ghp_[a-zA-Z0-9]{36}', 'ghp_***********************************', snippet)
    # ... other patterns ...

    # Generic fallback: redact likely secret portion
    return re.sub(r':\s*[A-Za-z0-9+/=]{20,}', ': [REDACTED]', snippet)
```

##### `_generate_rotation_guidance(rule_id: str) -> str`
Generates service-specific rotation guidance:
```python
ROTATION_GUIDANCE = {
    'aws-access-token': """
1. Rotate credentials via AWS IAM Console or CLI:
   aws iam create-access-key --user-name <user>
   aws iam delete-access-key --user-name <user> --access-key-id <old-key>

2. Update environment variables or secrets manager
3. Audit CloudTrail logs for unauthorized access
4. Consider using AWS Secrets Manager for future credentials
""",

    'github-pat': """
1. Revoke token: GitHub Settings → Developer Settings → Personal Access Tokens
2. Generate new token with same scopes
3. Update CI/CD secrets (GitHub Actions, GitLab CI, etc.)
4. Consider using fine-grained tokens with limited scope
""",

    # ... 206 more entries needed ...
}

def _generate_rotation_guidance(rule_id: str) -> str:
    return ROTATION_GUIDANCE.get(rule_id, ROTATION_GUIDANCE['generic'])
```

##### `_generate_prevention_guidance(rule_id: str, file_path: str) -> str`
Generates code transformation examples:
```python
def _generate_prevention_guidance(rule_id: str, file_path: str) -> str:
    """
    Generate before/after code showing proper secrets management.
    """
    if file_path.endswith('.yml') or file_path.endswith('.yaml'):
        if '.github/workflows' in file_path:
            return """
# Before (Insecure)
env:
  API_KEY: <api key in plain text>

# After (Secure)
env:
  API_KEY: ${{ secrets.API_KEY }}
"""
        elif 'docker-compose' in file_path:
            return """
# Before (Insecure)
environment:
  - DATABASE_PASSWORD=hardcoded_password

# After (Secure)
environment:
  - DATABASE_PASSWORD=${DB_PASSWORD}
"""

    elif file_path.endswith('.py'):
        return """
# Before (Insecure)
API_KEY = "<api key in plain text>"

# After (Secure)
import os
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
"""

    # ... more patterns ...
```

### 2. Output Format

```python
{
    # Core identification
    'tool': 'gitleaks',
    'id': 'aws-access-token',  # Secret type
    'rule_name': 'AWS Access Token',

    # Severity (always HIGH/CRITICAL for secrets)
    'severity': 'CRITICAL',
    'level': 'error',

    # Location
    'file_path': '.github/workflows/deploy.yml',
    'path': '.github/workflows/deploy.yml',
    'start': {'line': 25, 'column': 15},
    'end': {'line': 25, 'column': 55},

    # Sanitized context
    'snippet': 'AWS_ACCESS_KEY_ID: AKIA****************',  # REDACTED
    'message': 'Uncovered a possible AWS Access Token, risking unauthorized AWS service access and data exposure.',

    # Git history (for forensics)
    'commit_sha': 'a1b2c3d4e5f6',
    'author': 'John Doe',
    'author_email': 'john@example.com',
    'commit_date': '2024-01-15T10:30:00Z',

    # Remediation (service-specific)
    'rotation_guidance': 'Rotate credentials via AWS IAM...',
    'prevention_guidance': 'Use environment variables: ${{ secrets.AWS_ACCESS_KEY_ID }}',
    'removal_urgency': 'IMMEDIATE',  # All secrets are urgent

    # Metadata
    'tool_name': 'gitleaks',
    'security_category': 'secret_exposure',
    'category_confidence': 0.95,  # GitLeaks has some false positives
    'requires_git_history_cleanup': True,  # If committed
}
```

### 3. Training Data Example (Hypothetical)

```json
{
  "messages": [
    {
      "role": "user",
      "content": "A secret was detected in the codebase:\n\nFile: .github/workflows/deploy.yml\nLine: 25\nSecret Type: AWS Access Token\nSnippet: AWS_ACCESS_KEY_ID: AKIA****************\n\nThis secret has been committed to git history (commit a1b2c3d4). What are the immediate remediation steps?"
    },
    {
      "role": "assistant",
      "content": "IMMEDIATE ACTIONS REQUIRED:\n\n1. **Rotate AWS Credentials** (URGENT):\n   aws iam create-access-key --user-name <user>\n   aws iam delete-access-key --user-name <user> --access-key-id <old-key>\n\n2. **Audit for Unauthorized Access**:\n   Check AWS CloudTrail for any suspicious activity using the exposed key.\n\n3. **Remove Secret from Code**:\n   Replace hardcoded key with GitHub Actions secret:\n   env:\n     AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}\n\n4. **Clean Git History** (if committed):\n   git filter-branch --force --index-filter \\\n     'git rm --cached --ignore-unmatch .github/workflows/deploy.yml' \\\n     --prune-empty --tag-name-filter cat -- --all\n   \n   Or use BFG Repo Cleaner for easier cleanup.\n\n5. **Prevent Future Leaks**:\n   - Add pre-commit hook: brew install gitleaks && gitleaks protect\n   - Never commit secrets - use secrets management tools"
    }
  ]
}
```

## Implementation Challenges

### Challenge 1: No Test Data
- **Problem**: Current codebase has 0 secrets detected
- **Impact**: Cannot validate parser implementation
- **Mitigation**: Use synthetic test data or wait for real findings

### Challenge 2: Secret Sanitization
- **Problem**: SARIF may contain actual secret values
- **Impact**: Training data security risk
- **Mitigation**: Comprehensive redaction logic (complex, error-prone)

### Challenge 3: Service-Specific Knowledge
- **Problem**: 208 different secret types, each with unique rotation process
- **Impact**: Requires maintaining large remediation knowledge base
- **Mitigation**: Start with top 10 most common secret types

### Challenge 4: Low Training Value
- **Problem**: Secrets remediation is manual, service-specific, non-code
- **Impact**: Model learns procedural steps, not code transformations
- **Mitigation**: Focus on prevention guidance (code examples) over rotation

## Recommendation: Defer Implementation

### Reasons to Defer

1. **No Current Findings**: 0 secrets in test dataset means no validation data
2. **Low Training Value**: Manual remediation doesn't teach code transformations
3. **High Complexity**: Requires 208 service-specific remediation guides
4. **Security Risk**: Handling actual secret values in training pipeline
5. **Higher Priorities**: Trivy (Tier 1), Checkov (Tier 2) provide better training data

### Priority Ranking

| Parser | Training Value | Implementation Effort | Priority |
|--------|----------------|---------------------|----------|
| **Trivy** | ⭐⭐⭐⭐⭐ (Tier 1) | 3-4 hours | **HIGH** |
| **Checkov** | ⭐⭐⭐ (Tier 2) | 2-3 hours | **MEDIUM** |
| **Semgrep** | ⭐⭐⭐⭐ (Tier 1-2) | 3-4 hours | **MEDIUM** |
| **GitLeaks** | ⭐ (Tier 3) | 2 hours + 208 guides | **LOW** |

### When to Revisit

Implement GitLeaks parser when:
1. ✅ Trivy and Checkov parsers are complete and validated
2. ✅ We have actual secret detection findings (not just test data)
3. ✅ We've built a comprehensive service rotation knowledge base
4. ✅ We have secure secret sanitization infrastructure
5. ✅ Training pipeline can handle non-code remediation guidance

## Alternative Approach: Prevention-Focused Training

Instead of training on secret *remediation*, focus on secret *prevention*:

### Training Data Format (Prevention)

```json
{
  "messages": [
    {
      "role": "user",
      "content": "How should I securely handle API keys in a GitHub Actions workflow?"
    },
    {
      "role": "assistant",
      "content": "Never hardcode API keys in workflow files. Use GitHub Actions secrets:\n\n# Secure approach\nenv:\n  API_KEY: ${{ secrets.API_KEY }}\n\nSteps:\n1. Go to Repository Settings → Secrets and variables → Actions\n2. Click 'New repository secret'\n3. Name: API_KEY, Value: <your-key>\n4. Reference in workflow as shown above\n\nBenefits:\n- Encrypted at rest\n- Redacted in logs\n- Can be rotated without code changes"
    }
  ]
}
```

**Advantages**:
- ✅ Teaches secure coding patterns
- ✅ Generalizes across services
- ✅ No sensitive data in training
- ✅ More valuable than rotation procedures

**Source Data**: Security best practices documentation, not GitLeaks findings.

## If Implementation is Pursued (Future)

### Minimal Viable Implementation

1. **Parser**: Extract secret type, location, sanitized context
2. **Top 10 Services**: Rotation guidance for AWS, GitHub, Stripe, Slack, etc.
3. **Prevention Focus**: Code transformation examples (hardcoded → env vars)
4. **Sanitization**: Comprehensive secret redaction (security critical)
5. **Testing**: Synthetic test data (don't wait for real secrets)

### Estimated Effort Breakdown

- **Core Parser**: 2 hours
- **Secret Sanitization**: 1 hour (security-critical)
- **Top 10 Rotation Guides**: 2 hours
- **Prevention Code Examples**: 1 hour
- **Testing**: 1 hour
- **Total**: ~7 hours

## References

- **GitLeaks Documentation**: https://github.com/gitleaks/gitleaks
- **GitLeaks Rules**: https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml
- **SARIF Specification**: https://sarifweb.azurewebsites.net/
- **Current Generic SARIF Parser**: `parsers/sarif_parser.py`

---

**Author**: AI Security Enhancement System
**Review Status**: Awaiting prioritization decision
**Implementation Branch**: `feat/security-ai-analysis-refactor` (when implemented)
**Recommendation**: **DEFER** - Implement Trivy and Checkov parsers first
