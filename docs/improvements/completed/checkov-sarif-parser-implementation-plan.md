# Checkov SARIF Parser Implementation Plan

**Status**: Planning
**Priority**: Medium
**Estimated Effort**: 2-3 hours
**Created**: 2025-10-07

## Executive Summary

Implement a dedicated Checkov SARIF parser (`parsers/sarif_checkov_parser.py`) to extract security configuration findings with rule-based remediation guidance for AI training data generation.

## Problem Statement

### Current State
- **Generic SARIF Parser**: `parsers/sarif_parser.py` treats all SARIF files the same
- **No Tool-Specific Parsing**: Checkov's SARIF output has limited structured remediation data
- **Lost Context**: Rule IDs (e.g., `CKV2_GHA_1`) contain valuable security guidance not being extracted
- **Training Data Quality**: Generic message text doesn't provide actionable fixes for model training

### Why Separate Parser Needed
Checkov SARIF structure differs from other tools:
- **Trivy**: Structured dependency data (package name, versions, fixed version)
- **Checkov**: Configuration security rules with implicit remediation (rule description = guidance)
- **Semgrep**: Code pattern vulnerabilities with snippets
- **GitLeaks**: Secret detection without fixes

## Checkov SARIF Data Structure

### Available Fields

```json
{
  "ruleId": "CKV2_GHA_1",
  "ruleIndex": 0,
  "level": "error",
  "message": {
    "text": "Ensure top-level permissions are not set to write-all"
  },
  "locations": [
    {
      "physicalLocation": {
        "artifactLocation": {
          "uri": ".github/workflows/android-e2e-tests.yml"
        },
        "region": {
          "startLine": 166,
          "endLine": 167,
          "snippet": {
            "text": ""
          }
        }
      }
    }
  ]
}
```

### Rule Metadata (from `tool.driver.rules`)

```json
{
  "id": "CKV2_GHA_1",
  "name": "Ensure top-level permissions are not set to write-all",
  "shortDescription": {
    "text": "Ensure top-level permissions are not set to write-all"
  },
  "fullDescription": {
    "text": "Ensure top-level permissions are not set to write-all"
  },
  "help": {
    "text": "Ensure top-level permissions are not set to write-all\nResource: on(Android E2E Tests - Emulator)"
  },
  "defaultConfiguration": {
    "level": "error"
  }
}
```

### What's Missing
❌ No `fixedVersion` field
❌ No structured remediation steps
❌ No before/after code examples
❌ Empty `snippet.text` (no vulnerable code captured)

### What We Can Extract
✅ **Rule ID**: `CKV2_GHA_1` (maps to Checkov documentation)
✅ **Problem Description**: Rule name/message (implicit remediation guidance)
✅ **File Location**: Exact file path
✅ **Line Range**: `startLine` to `endLine`
✅ **Severity**: Mapped from `level` (error/warning/note)
✅ **Context**: GitHub Actions, Docker, Kubernetes, Terraform, etc.

## Implementation Design

### 1. File: `parsers/sarif_checkov_parser.py`

#### Purpose
Parse Checkov SARIF files and extract configuration security findings with rule-based remediation guidance.

#### Key Functions

##### `parse_checkov_sarif(filepath: str) -> List[Dict]`
Main entry point that:
1. Loads SARIF JSON from file
2. Validates it's Checkov output (checks `tool.driver.name == "Checkov"`)
3. Builds rule lookup from `tool.driver.rules`
4. Iterates through `results` and extracts structured data
5. Returns list of vulnerability dicts

##### `_build_rule_lookup(rules: List[Dict]) -> Dict[str, Dict]`
Creates a mapping of `ruleId` → rule metadata for fast lookup:
```python
{
  "CKV2_GHA_1": {
    "name": "Ensure top-level permissions are not set to write-all",
    "shortDescription": "...",
    "fullDescription": "...",
    "help": "..."
  }
}
```

##### `_extract_remediation_guidance(rule_id: str, message: str, rule_info: Dict) -> str`
Generates actionable remediation text from available data:
- Uses rule name as primary guidance
- Falls back to message text
- Optionally enhances with rule-specific knowledge (see Rule-Based Remediation Map)

##### `_map_severity(level: str) -> str`
Maps SARIF levels to standard severity:
```python
{
  'error': 'HIGH',
  'warning': 'MEDIUM',
  'note': 'LOW',
  'info': 'INFO'
}
```

##### `_extract_file_context(location: Dict) -> Dict`
Extracts file path, line numbers, and code snippet:
```python
{
  'file_path': '.github/workflows/android-e2e-tests.yml',
  'start_line': 166,
  'end_line': 167,
  'snippet': ''  # Usually empty in Checkov SARIF
}
```

### 2. Output Format

Each vulnerability dict should contain:

```python
{
    # Core identification
    'tool': 'checkov',
    'id': 'CKV2_GHA_1',
    'rule_name': 'Ensure top-level permissions are not set to write-all',

    # Severity and classification
    'severity': 'HIGH',  # Mapped from 'error'
    'level': 'error',    # Original SARIF level

    # Location
    'file_path': '.github/workflows/android-e2e-tests.yml',
    'path': '.github/workflows/android-e2e-tests.yml',  # Alias for compatibility
    'start': {'line': 166},
    'end': {'line': 167},

    # Descriptions
    'message': 'Ensure top-level permissions are not set to write-all',
    'short_description': 'Ensure top-level permissions are not set to write-all',
    'full_description': 'Ensure top-level permissions are not set to write-all',
    'help_text': 'Ensure top-level permissions are not set to write-all\nResource: on(Android E2E Tests - Emulator)',

    # Remediation (derived)
    'remediation': 'Remove write-all from top-level permissions. Instead, specify granular permissions like contents: read, pull-requests: write as needed per job.',

    # Metadata
    'tool_name': 'Checkov',
    'tool_version': '3.2.470',
    'security_category': 'configuration_security',
    'category_confidence': 0.9,

    # Context hints for training
    'config_type': 'github_actions',  # Derived from file path
    'fix_complexity': 'low',           # Most config fixes are straightforward
}
```

### 3. Rule-Based Remediation Map (Optional Enhancement)

Create a mapping of common Checkov rules to specific remediation guidance:

```python
CHECKOV_RULE_REMEDIATION = {
    'CKV2_GHA_1': {
        'problem': 'Top-level permissions set to write-all in GitHub Actions workflow',
        'fix': 'Remove write-all from top-level permissions. Specify granular permissions like contents: read, pull-requests: write at the job level.',
        'example': '''
# Before (Insecure)
permissions: write-all

# After (Secure)
permissions:
  contents: read
  pull-requests: write
'''
    },
    'CKV_DOCKER_2': {
        'problem': 'Dockerfile missing HEALTHCHECK instruction',
        'fix': 'Add HEALTHCHECK instruction to monitor container health.',
        'example': 'HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost/ || exit 1'
    },
    # Add more as we encounter them
}
```

**Implementation Note**: Start without this map, add rules as we discover them in actual training data.

## Integration Points

### 1. Update `process_artifacts.py`

**Current Code** (line ~80-120):
```python
# Parse SARIF files (generic parser)
sarif_files = list(Path(artifacts_dir).rglob('*.sarif'))
for sarif_file in sarif_files:
    findings.extend(sarif_parser.parse_sarif_json(str(sarif_file)))
```

**New Code** (tool-specific dispatch):
```python
# Parse SARIF files with tool-specific parsers
sarif_files = list(Path(artifacts_dir).rglob('*.sarif'))
for sarif_file in sarif_files:
    # Detect tool type from SARIF content
    with open(sarif_file) as f:
        data = json.load(f)
        tool_name = data['runs'][0]['tool']['driver']['name'].lower()

    # Dispatch to appropriate parser
    if tool_name == 'checkov':
        findings.extend(sarif_checkov_parser.parse_checkov_sarif(str(sarif_file)))
    elif tool_name == 'trivy':
        findings.extend(sarif_trivy_parser.parse_trivy_sarif(str(sarif_file)))
    elif tool_name == 'semgrep':
        findings.extend(sarif_semgrep_parser.parse_semgrep_sarif(str(sarif_file)))
    else:
        # Fallback to generic SARIF parser
        findings.extend(sarif_parser.parse_sarif_json(str(sarif_file)))
```

### 2. Training Data Generation

The extracted fields will flow through:
1. **process_artifacts.py** → `construct_datasets_phase()`
2. **multi_approach_fix_generator.py** → `generate_fixes()` for config vulnerabilities
3. **Training pairs** → User prompt with rule violation, Assistant response with fix

Expected training example:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Fix the following security configuration issue:\n\nFile: .github/workflows/android-e2e-tests.yml\nLine: 166-167\nIssue: Ensure top-level permissions are not set to write-all\n\nThis violates GitHub Actions security best practices."
    },
    {
      "role": "assistant",
      "content": "Remove write-all from top-level permissions. Instead, specify granular permissions at the job level:\n\npermissions:\n  contents: read\n  pull-requests: write\n\nThis follows the principle of least privilege and reduces the attack surface."
    }
  ]
}
```

## File Structure

```
security-ai-analysis/
├── parsers/
│   ├── __init__.py                      # Update imports
│   ├── sarif_parser.py                  # Keep as generic fallback
│   ├── sarif_checkov_parser.py         # NEW: Checkov-specific parser
│   ├── sarif_trivy_parser.py           # TODO: Next implementation
│   ├── sarif_semgrep_parser.py         # TODO: Future
│   ├── checkov_parser.py               # Existing (for non-SARIF Checkov JSON)
│   └── trivy_parser.py                 # Existing (for non-SARIF Trivy JSON)
├── process_artifacts.py                 # Update to dispatch tool-specific parsers
└── multi_approach_fix_generator.py      # May need config-specific fix templates
```

## Implementation Steps

### Phase 1: Core Parser (1-2 hours)
1. Create `parsers/sarif_checkov_parser.py`
2. Implement `parse_checkov_sarif()` main function
3. Implement `_build_rule_lookup()` helper
4. Implement `_map_severity()` helper
5. Implement `_extract_file_context()` helper
6. Add validation: check `tool.driver.name == "Checkov"`
7. Handle graceful failures (file not found, corrupted JSON)

### Phase 2: Remediation Enhancement (30 min)
1. Implement `_extract_remediation_guidance()`
2. Use rule name + message as base guidance
3. Optionally add `CHECKOV_RULE_REMEDIATION` map for common rules

### Phase 3: Integration (30 min)
1. Update `parsers/__init__.py` to export new parser
2. Update `process_artifacts.py` to dispatch Checkov SARIF files
3. Test with actual Checkov SARIF file from `data/security_artifacts/`

### Phase 4: Validation (30 min)
1. Run `construct_datasets_phase()` with new parser
2. Inspect `results/train_dataset.jsonl` for Checkov entries
3. Verify training data has actionable remediation guidance
4. Compare before/after data quality

## Testing Strategy

### Unit Tests
```python
# tests/parsers/test_sarif_checkov_parser.py

def test_parse_checkov_sarif_basic():
    """Test parsing valid Checkov SARIF file"""
    findings = parse_checkov_sarif('data/security_artifacts/checkov-results.sarif')
    assert len(findings) == 10
    assert findings[0]['tool'] == 'checkov'
    assert findings[0]['id'] == 'CKV2_GHA_1'

def test_rule_lookup():
    """Test rule metadata extraction"""
    rules = [{'id': 'CKV2_GHA_1', 'name': 'Test Rule'}]
    lookup = _build_rule_lookup(rules)
    assert 'CKV2_GHA_1' in lookup
    assert lookup['CKV2_GHA_1']['name'] == 'Test Rule'

def test_severity_mapping():
    """Test SARIF level to severity mapping"""
    assert _map_severity('error') == 'HIGH'
    assert _map_severity('warning') == 'MEDIUM'
    assert _map_severity('note') == 'LOW'
```

### Integration Test
```python
def test_checkov_training_data_generation():
    """Test end-to-end: Checkov SARIF → Training Data"""
    # Run parsing phase
    findings = parse_checkov_sarif('data/security_artifacts/checkov-results.sarif')

    # Generate training pairs
    training_pairs = generate_training_pairs(findings)

    # Verify structure
    assert len(training_pairs) > 0
    assert 'messages' in training_pairs[0]
    assert training_pairs[0]['messages'][0]['role'] == 'user'
    assert training_pairs[0]['messages'][1]['role'] == 'assistant'

    # Verify content quality
    assistant_msg = training_pairs[0]['messages'][1]['content']
    assert len(assistant_msg) > 20  # Not generic placeholder
    assert 'permissions' in assistant_msg.lower()  # Has relevant content
```

## Expected Outcomes

### Training Data Quality Improvement
**Before** (generic SARIF parser):
```json
{
  "role": "assistant",
  "content": "Recommended secure configuration"
}
```

**After** (Checkov-specific parser):
```json
{
  "role": "assistant",
  "content": "Remove write-all from top-level permissions. Specify granular permissions like contents: read, pull-requests: write at the job level to follow the principle of least privilege."
}
```

### Metrics
- **Checkov Findings Parsed**: ~10 from current SARIF file
- **Training Examples Generated**: ~10 configuration security fixes
- **Data Quality Tier**: Tier 2 (deterministic config fixes, no version upgrades)
- **Remediation Specificity**: Medium (rule-based guidance, not code-level fixes)

## Future Enhancements

1. **Rule Remediation Database**: Build comprehensive `CHECKOV_RULE_REMEDIATION` map over time
2. **Code Snippet Extraction**: If Checkov starts populating `snippet.text`, extract vulnerable code
3. **Multi-File Fixes**: Some Checkov rules affect multiple files (e.g., Terraform modules)
4. **Fix Validation**: Run Checkov again after applying fix to verify remediation
5. **Documentation Links**: Add links to Checkov docs for each rule ID

## Dependencies

### Required Files
- `data/security_artifacts/checkov-results-workflow_dispatch-392/checkov-results.sarif`

### Python Imports
```python
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
```

### No New External Dependencies
Uses standard library only.

## Risk Assessment

### Low Risk
- ✅ Isolated new file, doesn't modify existing parsers
- ✅ Graceful fallback to generic SARIF parser if Checkov parser fails
- ✅ No changes to training pipeline logic, only data extraction

### Medium Risk
- ⚠️ Checkov SARIF structure may change between versions
- ⚠️ Rule IDs may be deprecated/renamed over time
- ⚠️ Remediation guidance is derived, not explicit from Checkov

### Mitigation
- Add version checking: log warning if Checkov version differs from tested version
- Maintain rule ID mapping as configuration (easy to update)
- Fallback to generic message if remediation extraction fails

## Success Criteria

1. ✅ Parser successfully extracts all 10 findings from test SARIF file
2. ✅ Severity mapping produces HIGH/MEDIUM/LOW values
3. ✅ File paths and line numbers extracted correctly
4. ✅ Remediation guidance is non-empty and contextual
5. ✅ Training dataset contains Checkov examples with actionable fixes
6. ✅ No regression in existing parser functionality
7. ✅ Code passes linting (Detekt/Pylance) with no new warnings

## Next Steps After Completion

1. **Trivy SARIF Parser**: Implement `sarif_trivy_parser.py` with dependency upgrade extraction
2. **Semgrep SARIF Parser**: Extract code vulnerability patterns with fix suggestions
3. **Parser Dispatcher**: Refactor `process_artifacts.py` to use factory pattern for SARIF parsers
4. **Documentation**: Update project README with parser architecture diagram

## Integration with Enhanced Parsing Architecture

**Reference**: [Enhanced Parsing Architecture](./enhanced-parsing-architecture.md)

### Unified Data Format Output

```json
{
  // Standard vulnerability metadata
  "tool": "sarif-checkov",
  "id": "CKV2_GHA_1",
  "severity": "HIGH",
  "message": "Ensure top-level permissions are not set to write-all",
  "security_category": "infrastructure_security",
  "category_confidence": 0.95,

  // Location
  "file_path": ".github/workflows/android-e2e-tests.yml",
  "start": {"line": 166},

  // Code context (YAML configuration)
  "code_context": {
    "file_path": ".github/workflows/android-e2e-tests.yml",
    "language": "yaml",
    "vulnerability_line": 166,
    "vulnerable_code": "permissions:\n  contents: write\n  packages: write",
    "extraction_type": "config_file",
    "extraction_success": true
  },

  // Fix data (rule-based from MultiApproachFixGenerator)
  "fix": {
    "confidence": 0.7,  // Checkov = config patterns
    "description": "Restrict GitHub Actions permissions to read-only by default",
    "fixed_code": "permissions:\n  contents: read\n  # Add specific write permissions only where needed",
    "explanation": "Top-level write-all permissions allow any workflow step to modify repository contents and packages, violating least privilege. Restrict to read-only and grant write only to specific jobs that require it.",

    // Alternatives (different permission configurations)
    "alternatives": [
      {
        "description": "Remove top-level permissions, set per-job",
        "fixed_code": "# Remove top-level permissions\njobs:\n  deploy:\n    permissions:\n      contents: write  # Only this job can write",
        "explanation": "Most secure: no default permissions, each job declares exactly what it needs."
      }
    ]
  }
}
```

### Context Script Integration

**Scripts Used**:
- ❌ **URL Mapper**: Not needed (config files, not URLs)
- ✅ **Code Extractor**: Optional (extracts YAML context)
- ✅ **Fix Generator**: **REQUIRED** (`MultiApproachFixGenerator._generate_checkov_fix()`)

**Integration Pattern**: Config Pattern

```python
def parse_checkov_sarif(file_path: str) -> List[Dict]:
    """Parse Checkov SARIF and enrich with fixes."""
    vulnerabilities = extract_checkov_vulnerabilities(file_path)

    # Initialize helpers
    fix_generator = MultiApproachFixGenerator()
    code_extractor = VulnerableCodeExtractor()
    categorizer = VulnerabilityCategorizor()

    for vuln in vulnerabilities:
        # Step 1: Categorization
        category, confidence = categorizer.categorize_vulnerability(vuln)
        vuln['security_category'] = category
        vuln['category_confidence'] = confidence

        # Step 2: Code context extraction (optional)
        extraction_result = code_extractor.extract_vulnerability_context(vuln)
        if extraction_result.success and extraction_result.code_context:
            vuln['code_context'] = dataclass_to_dict(extraction_result.code_context)

        # Step 3: Fix generation via MultiApproachFixGenerator
        fix_result = fix_generator.generate_fixes(vuln, extraction_result.code_context)

        if fix_result.success and fix_result.fixes:
            vuln['fix'] = convert_fix_result_to_format(fix_result)

    return vulnerabilities
```

### MultiApproachFixGenerator Integration

Checkov uses rule knowledge base:

```python
# In MultiApproachFixGenerator class

def _generate_checkov_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
    """
    Checkov-specific: Configuration/IaC security fixes.

    Uses rule knowledge base + YAML context.
    """
    rule_id = vuln.get('check_id', vuln.get('rule_name', ''))

    # Look up rule fix pattern
    fix_pattern = self._get_checkov_fix_pattern(rule_id)

    if not fix_pattern:
        return FixGenerationResult(success=False, error_message=f"No fix pattern for rule {rule_id}")

    fix = SecurityFix(
        approach=FixApproach.CONFIGURATION_CHANGE,
        title=fix_pattern['title'],
        description=fix_pattern['description'],
        vulnerable_code=code_context.vulnerable_code if code_context else '',
        fixed_code=fix_pattern['fixed_code'],
        explanation=fix_pattern['explanation'],
        benefits=fix_pattern.get('benefits', []),
        language=code_context.language if code_context else 'yaml',
        complexity_level='low',
        security_impact='medium'
    )

    return FixGenerationResult(
        success=True,
        fixes=[fix],
        generation_metadata={
            'tool': 'checkov',
            'confidence': 0.7,
            'rule_id': rule_id
        }
    )

def _get_checkov_fix_pattern(self, rule_id: str) -> Optional[Dict]:
    """Get fix pattern for Checkov rule."""
    CHECKOV_RULE_FIXES = {
        'CKV2_GHA_1': {
            'title': 'Restrict GitHub Actions permissions to least privilege',
            'description': 'Set permissions to read-only by default',
            'fixed_code': """permissions:
  contents: read
  # Add specific write permissions only where needed""",
            'explanation': 'Top-level write-all permissions violate least privilege. Restrict to read and grant write only to jobs that require it.',
            'benefits': [
                'Limits blast radius of compromised workflows',
                'Follows principle of least privilege',
                'Prevents unauthorized repository modifications'
            ]
        },
        # Add more rule fixes as needed
    }

    return CHECKOV_RULE_FIXES.get(rule_id)
```

### Confidence Score

**Fixed at 0.7** - Checkov fixes are config patterns:

```python
TOOL_CONFIDENCE = {
    'checkov': 0.7,  # Medium: Config patterns with context
}
```

**Rationale**:
- Rule-based configuration fixes
- Some context-dependency (workflow structure)
- Clear remediation patterns
- YAML/IaC specific

### Training Data Generation

**ChatML Example** for Checkov configuration vulnerability:

```python
{
  "messages": [
    {
      "role": "system",
      "content": "You are a security expert specializing in vulnerability remediation for WebAuthn authentication servers. Provide specific, actionable fixes with code examples."
    },
    {
      "role": "user",
      "content": "Analyze this security vulnerability:\n\n**Tool**: Checkov\n**Rule**: CKV2_GHA_1\n**Severity**: HIGH\n**File**: .github/workflows/android-e2e-tests.yml\n**Line**: 166\n\n**Description**: Ensure top-level permissions are not set to write-all\n\n**Vulnerable Code**:\n```yaml\npermissions:\n  contents: write\n  packages: write\n```\n\n**Issue**: Top-level write permissions apply to all jobs in the workflow, violating least privilege principle.\n\nProvide a specific fix for this GitHub Actions workflow."
    },
    {
      "role": "assistant",
      "content": "To fix this GitHub Actions permissions issue:\n\n## 1. Restrict Top-Level Permissions\n\n**Fix**: Set default permissions to read-only\n\n```yaml\npermissions:\n  contents: read  # Default to read-only\n  # Remove write permissions from top level\n```\n\n## 2. Grant Write Permissions Per-Job\n\nFor jobs that need write access:\n\n```yaml\njobs:\n  build:\n    permissions:\n      contents: read  # Only needs read\n    steps:\n      - uses: actions/checkout@v4\n      - run: ./gradlew build\n\n  publish:\n    needs: build\n    permissions:\n      contents: write  # This job needs write\n      packages: write  # This job needs package write\n    steps:\n      - run: ./publish.sh\n```\n\n## 3. Why This Fix Works\n\nTop-level `write-all` permissions create security risks:\n- **Compromised dependencies**: Malicious npm/Maven packages can modify your repo\n- **Supply chain attacks**: Third-party actions gain unnecessary write access\n- **Blast radius**: One vulnerable step compromises entire workflow\n\nBy restricting to read-only and granting write per-job:\n- Limits scope of potential damage\n- Follows principle of least privilege\n- Explicit about which jobs modify repository\n\n## 4. Alternative: Remove Top-Level Permissions\n\nFor maximum security:\n\n```yaml\n# No top-level permissions - each job declares its needs\njobs:\n  test:\n    permissions:\n      contents: read\n    # ...\n\n  deploy:\n    permissions:\n      contents: write\n      packages: write\n    # ...\n```\n\n## 5. Verification\n\nAfter applying fix:\n```bash\ncheckov -f .github/workflows/android-e2e-tests.yml\n# Should pass CKV2_GHA_1\n```"
    }
  ]
}
```

### Expected Outcomes

**Volume**: 10 training examples for GitHub Actions security

**Quality Metrics**:
- **Confidence**: 0.7 (config patterns)
- **Fix Coverage**: 100% (all rules have patterns)
- **YAML Context**: Helpful for understanding
- **Small Dataset**: Only 10 findings (same rule)

## References

- **Enhanced Architecture**: [Enhanced Parsing Architecture](./enhanced-parsing-architecture.md)
- **Checkov Documentation**: https://www.checkov.io/
- **SARIF Specification**: https://sarifweb.azurewebsites.net/
- **Current SARIF Parser**: `parsers/sarif_parser.py`
- **Training Pipeline**: `process_artifacts.py` → `construct_datasets_phase()`

---

**Author**: AI Security Enhancement System
**Review Status**: Awaiting approval for implementation
**Implementation Branch**: `feat/security-ai-analysis-refactor`
