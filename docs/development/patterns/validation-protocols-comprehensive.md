# Validation Protocols - Comprehensive Guide

This document contains detailed validation examples and extensive protocols extracted from CLAUDE.md for reference.

## MANDATORY CHECKPOINT: VALIDATE BEFORE ANY EXTERNAL INTEGRATION

**⚠️ STOP - READ THIS EVERY TIME BEFORE WRITING CODE ⚠️**

### 🔒 ENFORCEMENT RULE: NO CODE WITHOUT VALIDATION

**BEFORE writing a SINGLE LINE of code that uses external tools/APIs/actions:**

#### STEP 1: MANDATORY DOCUMENTATION RESEARCH
- [ ] **Find Official Docs**: GitHub Marketplace page or official documentation site
- [ ] **Verify Action/Tool Exists**: Confirm the exact action/tool name and repository  
- [ ] **Check Version**: Verify the version (@v1, @v2, etc.) is current and not deprecated
- [ ] **Read ALL Parameters**: Document every single input parameter that exists

#### STEP 2: MANDATORY PARAMETER VALIDATION
- [ ] **List Required Parameters**: What parameters are mandatory?
- [ ] **List Optional Parameters**: What parameters are available but optional?
- [ ] **Validate Syntax**: Confirm exact spelling, case sensitivity, data types
- [ ] **Check Examples**: Find official examples that show actual usage

#### STEP 3: MANDATORY IMPLEMENTATION CHECK
- [ ] **State Documentation Source**: "Based on [official docs URL]..."
- [ ] **Confirm All Parameters**: "Verified parameters X, Y, Z exist in official docs"
- [ ] **No Assumptions Made**: "All syntax confirmed against official examples"

### 🚨 CRITICAL: SUBAGENT VALIDATION PROTOCOL
**BEFORE using Task tool with subagents, ALWAYS include explicit validation instructions:**

```
MANDATORY VALIDATION REQUIREMENT:
- Do NOT generate any code without validating syntax against official documentation
- ALWAYS use WebFetch to verify API calls, parameters, and integration patterns  
- Mark any unvalidated components with ❌ warnings
- Only include code that has been confirmed against official sources
- If documentation is unclear, mark as "REQUIRES VALIDATION" instead of assuming
```

### 🔍 VALIDATION EVIDENCE REQUIREMENT
**Every code block MUST include validation evidence:**
```python
# ✅ VALIDATED: Based on GitHub CLI official docs
# https://cli.github.com/manual/gh_run_download
gh run download <run-id> --pattern "*security*"

# ❌ UNVALIDATED: Requires research against OLMo documentation
# model = OLMoModel.from_pretrained("allenai/OLMo-1B")
```

## 🚨 VIOLATION CONSEQUENCES
**If you proceed without completing ALL validation steps:**
- **Workflow will likely fail** with parameter errors
- **Time will be wasted** on non-functional implementations  
- **User confidence will be damaged** by repeated failures
- **Session will be terminated** to prevent further invalid implementations

## 🔍 VALIDATION TEMPLATE - USE THIS EVERY TIME

Before implementing any external tool, ALWAYS state:

```
## 🛑 VALIDATION CHECKPOINT
Tool/Action: [exact name]
Documentation: [official URL] 
Version: [confirmed current version]
Parameters verified: [list all parameters with documentation references]
Example usage: [official example that proves syntax works]
✅ All parameters confirmed against official documentation
```

## 🚨 RED FLAGS - STOP and Research

- **"I think the parameter should be..."** → STOP: Find documentation
- **"Based on similar tools..."** → STOP: Each tool has unique syntax  
- **"This parameter seems logical..."** → STOP: Logic ≠ actual API
- **"The old version had..."** → STOP: APIs change, verify current version

## Critical Example: Semgrep Integration Failure

**What Went Wrong:**
- Used deprecated `returntocorp/semgrep-action@v1` without checking status
- Invented parameters: `generateSarif`, `scanChangedFilesOnly`, `output` (none exist)
- Created invalid Semgrep rule syntax without validating schema
- Result: Complete workflow failure and wasted implementation time

**What Should Have Been Done:**
1. **Research First**: Check if `returntocorp/semgrep-action` is current
2. **Find Current Approach**: Discover official `semgrep/semgrep` Docker method
3. **Validate Rule Syntax**: Check Semgrep rule schema documentation
4. **Test Locally**: Validate YAML and rule syntax before committing

## Critical Example: FOSS Security Tools Validation Failure (2025-08-27)

**What Went Wrong:**
- **GitLeaks**: Assumed `gitleaks/gitleaks-action@v2` generates SARIF files (it doesn't)
- **Checkov**: Used manual pip installation instead of official `bridgecrewio/checkov-action@master`
- **OWASP ZAP**: Completely invented custom Docker automation framework syntax
- **Result**: 3 workflows with non-functional implementations, violated CLAUDE.md validation rules

**What Should Have Been Done:**
1. **GitLeaks**: Research revealed action only creates GitHub issues, no SARIF output
2. **Checkov**: Official action `bridgecrewio/checkov-action@master` with proper parameters
3. **OWASP ZAP**: Use official actions `zaproxy/action-full-scan` and `zaproxy/action-baseline`

**Validation Research Results:**
```
✅ GitLeaks: gitleaks/gitleaks-action@v2 (env: GITHUB_TOKEN only)
✅ Checkov: bridgecrewio/checkov-action@master (with: directory, output_format, etc.)
✅ OWASP ZAP: zaproxy/action-full-scan@v0.10.0 (with: target, rules_file_name)
```

**Why This Happened Again:**
- Skipped mandatory validation checkpoint despite CLAUDE.md warnings
- Assumed parameter syntax without checking official documentation
- Invented complex configurations instead of using simple official actions

## Approved Information Sources (In Priority Order)

1. **Official Documentation**: Tool's official docs site (e.g., semgrep.dev, docs.github.com)
2. **Official GitHub Repositories**: README files and examples in official repos
3. **Current Release Notes**: Check for breaking changes and deprecations
4. **Web Search**: Only for finding official documentation sources

## NEVER Acceptable Sources

- ❌ **Assumptions**: "This should work like X"
- ❌ **Invented Syntax**: Making up parameters or configurations
- ❌ **Outdated Examples**: Using old tutorials without version verification
- ❌ **Similar Tools Logic**: "Tool A works this way, so Tool B should too"

## When Documentation is Missing or Unclear

- **State the Problem**: "Official documentation for X is unclear/missing"
- **Request Research**: "This needs independent research before implementation"
- **Propose Alternatives**: Suggest different tools with better documentation
- **Don't Guess**: NEVER attempt to generate code without confirmed syntax

## Implementation Safety Pattern

```yaml
# ✅ CORRECT: Based on verified official documentation
uses: official/action@v2
with:
  validated-param: "documented-value"

# ❌ WRONG: Invented parameters
uses: deprecated/action@v1  
with:
  made-up-param: "seems-logical"
```

## This rule prevents:

- Workflow failures from invalid syntax
- Security vulnerabilities from incorrect configurations
- Time waste from debugging non-existent features
- Loss of user confidence from repeated failures

## Advanced Validation Techniques

### Multi-Source Verification
```bash
# Verify tool availability across multiple sources
curl -s https://api.github.com/repos/owner/tool/releases/latest | jq '.tag_name'
docker pull tool:latest --dry-run
npm view tool version
```

### Parameter Schema Validation
```bash
# For tools with schema definitions
yq eval schema.yml  # Validate YAML schema
ajv validate --schema=schema.json --data=config.json  # Validate JSON schema
```

### Version Compatibility Matrix
```bash
# Check compatibility across versions
tool --version
tool --help | grep -A5 "parameters"
git log --oneline -- path/to/tool/config | head -10
```

### Integration Testing Validation
```bash
# Test tool integration before full implementation
tool --dry-run config.yml
tool --validate-only --config config.yml
tool --check-syntax input-file
```

This comprehensive validation approach prevents the recurring pattern of failed implementations due to unvalidated assumptions about external tool behavior.