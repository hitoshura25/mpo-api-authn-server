# Phase Input Fixtures Documentation

This directory contains fixture files that represent realistic input data for each phase of the security AI analysis pipeline. These fixtures enable isolated testing of individual phases using the `--only-*` flags without requiring the execution of previous phases.

## Fixture Overview

Each fixture file contains controlled test data representing **8 vulnerabilities across 5 security tools**:

- **3 vulnerabilities** from `semgrep` tool
- **2 vulnerabilities** from `sarif-trivy` tool
- **1 vulnerability** from `sarif-checkov` tool
- **1 vulnerability** from `zap` tool
- **1 vulnerability** from `osv-scanner` tool

## File Descriptions

### 1. parsed_vulnerabilities_fixture.json
**Purpose**: Input for `--only-vulnerability-analysis` phase
**Format**: Array of parsed vulnerability objects
**Content**: Raw vulnerability data from security tool outputs, normalized into consistent structure

```json
[
  {
    "vulnerability": {
      "tool": "semgrep",
      "id": "test.hardcoded-password",
      "severity": "HIGH",
      "message": "Hardcoded password detected...",
      "file_path": "test-config.js",
      // ... complete vulnerability details
    },
    "status": "success"
  }
  // ... 7 more vulnerabilities
]
```

### 2. core_analysis_fixture.json
**Purpose**: Input for `--only-rag-enhancement` phase
**Format**: Array of vulnerability objects with AI analysis added
**Content**: Same vulnerabilities as above, plus initial AI analysis results

### 3. rag_enhanced_fixture.json
**Purpose**: Input for `--only-analysis-summary` phase
**Format**: Enhanced analysis with RAG context
**Content**: Vulnerabilities with RAG improvements and WebAuthn-specific context

### 4. analyzed_vulnerabilities_fixture.json
**Purpose**: Input for `--only-narrativization` phase
**Format**: Final analysis summary format
**Content**: Complete analysis with risk scores and priority rankings

### 5. narrativized_fixture.json
**Purpose**: Input for `--only-datasets` phase
**Format**: Narrative training examples
**Content**: Structured narratives for each vulnerability with problem statements, technical details, and remediation steps

### 6. Training Dataset Fixtures

#### train_dataset_fixture.jsonl
**Purpose**: Input for `--only-training` phase (training data)
**Format**: JSONL with instruction/response pairs
**Content**: 5 training examples in instruction-tuning format

#### validation_dataset_fixture.jsonl
**Purpose**: Input for `--only-training` phase (validation data)
**Format**: JSONL with instruction/response pairs
**Content**: 2 validation examples for model evaluation

### 7. model_artifacts_fixture/
**Purpose**: Input for `--only-upload` phase
**Format**: Directory with model files
**Content**: Mock model artifacts representing fine-tuned model output

```
model_artifacts_fixture/
├── adapter_config.json      # LoRA adapter configuration
├── adapter_model.safetensors # Mock adapter weights (placeholder)
├── tokenizer_config.json    # Tokenizer configuration
└── training_args.json       # Training parameters used
```

## Usage in Tests

The fixtures are used by the `create_prerequisite_files_up_to()` method in `test_process_artifacts_script.py`:

```python
def create_prerequisite_files_up_to(self, target_phase):
    """Return paths to fixture files needed for testing target_phase"""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"

    if target_phase == "vulnerability-analysis":
        return {"parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json"}
    elif target_phase == "datasets":
        return {
            "narrativized_file": fixtures_dir / "narrativized_fixture.json",
            "parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json"
        }
    # ... other phases
```

## Benefits

- **Fast Testing**: No AI model loading or processing required
- **True Isolation**: Each phase tested independently
- **No File I/O Overhead**: Direct path references to permanent fixtures
- **Deterministic**: Same input always produces same output
- **Version Controlled**: Fixtures are visible and maintainable in source control

## Maintenance

When phase output formats change:
1. Run actual phases to generate new realistic data
2. Update corresponding fixture files
3. Ensure fixture data matches the controlled 8-vulnerability test dataset
4. Validate tests still pass with updated fixtures

## Controlled Test Data

All fixtures are based on these 8 specific vulnerabilities:

1. **CVE-2024-0001** (sarif-trivy) - Prototype pollution in lodash
2. **test.hardcoded-password** (semgrep) - Hardcoded credentials
3. **test.xss-vulnerability** (semgrep) - Cross-site scripting
4. **test.sql-injection** (semgrep) - SQL injection vulnerability
5. **CKV_AWS_20** (sarif-checkov) - S3 bucket misconfiguration
6. **10035** (zap) - Missing HSTS header
7. **GHSA-j8r2-6x86-q33q** (osv-scanner) - Requests library vulnerability
8. **test.weak-crypto** (semgrep) - Weak cryptographic algorithm

This controlled dataset ensures consistent testing across all phases and enables reliable fixture-based validation.