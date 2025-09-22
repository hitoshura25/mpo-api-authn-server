# Security AI Analysis - Comprehensive Testing Implementation Plan

## Context & Background

This plan creates a comprehensive testing system for `security-ai-analysis/process_artifacts.py` - a complex pipeline that processes security vulnerabilities through multiple phases. The current testing is insufficient and needs to be rebuilt from scratch.

## Pipeline Overview (What We're Testing)

The `process_artifacts.py` script performs these phases:
1. **Security Parsing**: Parse vulnerability files from multiple security tools
2. **AI Analysis**: Process vulnerabilities through OLMo model in batches
3. **Dataset Creation**: Generate training datasets and narrativized content
4. **Sequential Fine-tuning**: Two-stage model training (Analysis → Code Fixes)
5. **Model Upload**: Convert and upload models to HuggingFace
6. **Model Validation**: Test model capabilities and specialization

## Key Files and Locations

- **Main script**: `security-ai-analysis/process_artifacts.py`
- **Parser modules**: `security-ai-analysis/parsers/` (semgrep_parser.py, trivy_parser.py, etc.)
- **Test directory**: `security-ai-analysis/tests/`
- **Test runner**: `security-ai-analysis/run_tests.sh`
- **Real security data**: `security-ai-analysis/data/security_artifacts/` (contains actual SARIF/JSON files)

## Implementation Plan

### 1. Create Controlled Test Data

**Location**: `security-ai-analysis/tests/fixtures/controlled_test_data/`

Create minimal security artifacts with **exactly known vulnerability counts**:

**Files to create:**
- `semgrep.sarif`: Exactly 3 vulnerabilities with known rule IDs, file paths, line numbers
- `trivy-results.sarif`: Exactly 2 vulnerabilities with known CVEs and severities
- `checkov-results.sarif`: Exactly 1 vulnerability with known check ID
- `osv-results.json`: Exactly 1 vulnerability with known package/version
- `zap-report.json`: Exactly 1 vulnerability with known URL/risk level

**Total: 8 known vulnerabilities** for precise regression testing.

**Requirements for test data:**
- Use realistic but minimal SARIF/JSON structure
- Include all required fields that parsers expect
- Use predictable, testable values (e.g., file paths like "test.js", "test.py")
- Ensure each tool's parser will find exactly the expected count

### 2. Comprehensive Unit Tests

**Location**: `security-ai-analysis/tests/unit/test_security_parsers.py`

**Purpose**: Test all parser functions directly with controlled data

**Tests to implement:**
```python
class TestSecurityParsers:
    def test_semgrep_parser_exact_count(self):
        # Test parse_semgrep_sarif() with controlled SARIF
        # Assert: len(results) == 3
        # Assert: specific fields present and correct

    def test_trivy_parser_exact_count(self):
        # Test parse_trivy_json() with controlled SARIF
        # Assert: len(results) == 2

    def test_checkov_parser_exact_count(self):
        # Test parse_checkov_json() with controlled SARIF
        # Assert: len(results) == 1

    def test_osv_parser_exact_count(self):
        # Test parse_osv_json() with controlled JSON
        # Assert: len(results) == 1

    def test_zap_parser_exact_count(self):
        # Test parse_zap_json() with controlled JSON
        # Assert: len(results) == 1

    def test_parser_regression_detection(self):
        # Temporarily modify parser to return empty list
        # Verify test catches the regression
        # Restore parser and verify test passes
```

**Key requirements:**
- Test ALL parsers, not just semgrep
- Use controlled test data with known exact counts
- Verify data structure and required fields
- Include regression detection validation

### 3. Comprehensive Integration Tests

**Location**: `security-ai-analysis/tests/integration/test_process_artifacts_script.py`

**Purpose**: Test the complete `process_artifacts.py` pipeline with controlled inputs

**Structure:**
```python
class TestProcessArtifactsScript:
    # Phase 1: Security Parsing
    def test_exact_vulnerability_parsing(self):
        # Run script with controlled test data
        # Assert: total vulnerabilities == 8
        # Assert: by_tool counts match exactly (semgrep=3, trivy=2, etc.)

    def test_tool_specific_parsing_accuracy(self):
        # Verify each tool finds its expected vulnerabilities
        # Assert: semgrep finds exactly 3 with correct rule IDs
        # Assert: trivy finds exactly 2 with correct CVEs
        # etc.

    # Phase 2: AI Analysis (with --skip-fine-tuning for speed)
    def test_ai_analysis_batch_processing(self):
        # Verify 8 vulnerabilities processed in batches
        # Check batch size and total batch count

    def test_analysis_results_structure(self):
        # Validate olmo_analysis_results.json structure
        # Check required fields and data types

    # Phase 3: Dataset Creation
    def test_output_files_created_and_valid(self):
        # Verify all 6 expected output files exist:
        # - olmo_analysis_summary.json
        # - olmo_analysis_results.json
        # - narrativized_dataset.json
        # - train.jsonl
        # - validation.jsonl
        # - dataset_info.json
        # Assert: all files exist AND are non-empty

    def test_dataset_content_accuracy(self):
        # narrativized_dataset.json: exactly 8 entries
        # train.jsonl: ~6 entries (75% of 8)
        # validation.jsonl: ~2 entries (25% of 8)

    def test_summary_file_accuracy(self):
        # olmo_analysis_summary.json matches exact vulnerability counts
        # total_analyzed: 8
        # by_tool: {semgrep: 3, trivy: 2, checkov: 1, osv: 1, zap: 1}

    # Phase 4: Fine-tuning (Optional - slow tests)
    def test_fine_tuning_artifacts_creation(self):
        # When fine-tuning enabled, verify model directories created
        # Check for Stage 1 and Stage 2 model outputs
        # Only run when specifically testing fine-tuning

    def test_model_upload_artifacts(self):
        # When upload enabled, verify PEFT conversion files
        # Check adapter_model.safetensors, adapter_config.json, README.md
        # Only run when specifically testing upload
```

### 4. Test Configuration and Speed Optimization

**Test speed tiers:**
- **Unit tests**: ~2 seconds (direct parser testing)
- **Integration tests with --skip-fine-tuning**: ~30 seconds (full pipeline minus AI training)
- **Full end-to-end tests**: Minutes (complete pipeline when needed)

**Test arguments for speed:**
```python
# Standard test args for integration tests
process_artifacts_args = [
    "--artifacts-dir", str(controlled_test_data_dir),
    "--output-dir", str(temp_output_dir),
    "--skip-fine-tuning",  # Skip time-consuming fine-tuning
    "--disable-rag",       # Avoid RAG complexity
    "--disable-sequential-fine-tuning"  # Skip sequential training
]
```

### 5. Test Data Management

**Controlled test data requirements:**
- **Predictable**: Same input always produces same output
- **Minimal**: Small files that parse quickly
- **Realistic**: Valid SARIF/JSON structure that parsers expect
- **Comprehensive**: Covers all security tools
- **Documented**: Clear documentation of expected results

**Example test data structure:**
```
tests/fixtures/controlled_test_data/
├── semgrep.sarif          # 3 vulnerabilities
├── trivy-results.sarif    # 2 vulnerabilities
├── checkov-results.sarif  # 1 vulnerability
├── osv-results.json       # 1 vulnerability
├── zap-report.json        # 1 vulnerability
└── README.md              # Documents expected counts and test data purpose
```

### 6. Assertion Strategy

**Exact assertions where possible:**
- `assert summary["total_analyzed"] == 8` (not `> 0`)
- `assert summary["by_tool"]["semgrep"] == 3` (not `> 0`)
- `assert len(train_data) == 6` (not `> 0`)

**Smart assertions for flexibility:**
- File existence + non-empty size checks
- JSON schema validation for critical files
- Range checks where exact counts vary (e.g., model generation times)

**Brittleness prevention:**
- Test behavior, not implementation details
- Allow for reasonable variance in non-critical outputs
- Focus on regression detection for critical parsing

### 7. Test Organization and Structure

**Directory structure:**
```
tests/
├── unit/
│   └── test_security_parsers.py       # Direct parser function tests
├── integration/
│   └── test_process_artifacts_script.py # Complete pipeline tests
├── fixtures/
│   └── controlled_test_data/           # Known test artifacts
├── conftest.py                         # Shared fixtures and configuration
└── requirements.txt                    # Test dependencies
```

**Test execution options:**
- `./run_tests.sh quick`: Unit tests only (~2 seconds)
- `./run_tests.sh integration`: Full pipeline with --skip-fine-tuning (~30 seconds)
- `./run_tests.sh all`: Everything including optional slow tests

### 8. Success Criteria

The implemented testing system should:
1. **Catch regressions immediately**: Any parser returning wrong count = test failure
2. **Provide fast feedback**: Unit tests complete in seconds
3. **Cover all pipeline phases**: From parsing to dataset creation
4. **Use controlled inputs**: Known test data with predictable outputs
5. **Be maintainable**: Clear structure and documented expectations
6. **Prevent brittleness**: Test behavior, not implementation details

### 9. Implementation Notes

**Key imports needed:**
```python
from process_artifacts import find_security_files
from parsers.semgrep_parser import parse_semgrep_sarif
from parsers.trivy_parser import parse_trivy_json
# etc. for all parsers
```

**Common patterns:**
- Use `subprocess.run()` for integration tests
- Use `tempfile.mkdtemp()` for test output directories
- Use `json.load()` for validating output file contents
- Use controlled test data fixtures for predictable results

**Key insight**: Since you control the test data, you should know exactly what the results should be. No more vague assertions - everything should be precise and predictable.

## Implementation Status

- [ ] Create controlled test data with known vulnerability counts
- [ ] Implement comprehensive unit tests for all security parsers
- [ ] Implement comprehensive integration tests for the full pipeline
- [ ] Update test configuration and runner scripts
- [ ] Document test data and expected results
- [ ] Validate all tests pass and provide appropriate feedback speeds

## Notes

This plan replaces the previous over-engineered baseline management approach with a simpler, more effective strategy based on controlled test data and exact assertions. The focus is on precision, speed, and comprehensive coverage of all pipeline phases.