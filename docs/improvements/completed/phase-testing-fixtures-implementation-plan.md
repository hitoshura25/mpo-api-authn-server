# Phase Testing Fixtures Implementation Plan

## Problem Analysis

The current `create_prerequisite_files_up_to()` method in the integration tests defeats the purpose of isolated phase testing by:

- **Running all previous phases sequentially**: Slow execution, cascading failures
- **Not truly testing individual `--only-*` phase execution**: Tests become interdependent
- **Making tests dependent on AI model loading and processing**: Causes timeouts and resource issues
- **Creating cascading failures**: If one phase fails, all subsequent phase tests fail

### Current Problematic Flow
```python
def create_prerequisite_files_up_to(self, target_phase):
    if target_phase == "vulnerability-analysis":
        # This RUNS the parsing phase!
        result = self.run_process_artifacts(["--only-parsing"])
        # Then uses its output...
    elif target_phase == "rag-enhancement":
        # This runs parsing AND vulnerability-analysis!
        parsed_result = self.create_prerequisite_files_up_to("vulnerability-analysis")
        vuln_result = self.run_process_artifacts([...])
```

This creates a chain where testing `--only-datasets` actually runs: parsing → vulnerability-analysis → rag-enhancement → analysis-summary → narrativization.

## Solution: Static Phase Input Fixtures

Replace the recursive phase execution with realistic fixture files that represent each phase's expected input format.

## Implementation Plan

### Phase 1: Create Fixture Directory Structure

Create the following directory structure:

```
tests/fixtures/phase_inputs/
├── parsed_vulnerabilities_fixture.json          # Input for vulnerability-analysis phase
├── core_analysis_fixture.json                   # Input for rag-enhancement phase
├── rag_enhanced_fixture.json                    # Input for analysis-summary phase
├── analyzed_vulnerabilities_fixture.json        # Input for narrativization phase
├── narrativized_fixture.json                    # Input for datasets phase
├── train_dataset_fixture.jsonl                  # Input for training phase
├── validation_dataset_fixture.jsonl             # Input for training phase
├── model_artifacts_fixture/                     # Input for upload phase
│   ├── adapter_config.json
│   ├── adapter_model.safetensors
│   └── tokenizer_config.json
└── README.md                                    # Documentation of fixture formats
```

### Phase 2: Generate Realistic Fixture Content

Each fixture file should contain realistic data that matches the expected phase output format, based on the controlled test data (8 vulnerabilities across 5 tools).

#### 2.1 parsed_vulnerabilities_fixture.json
**Purpose**: Input for `--only-vulnerability-analysis`
**Format**: Array of parsed vulnerability objects
```json
[
  {
    "vulnerability": {
      "tool": "semgrep",
      "id": "test.hardcoded-password",
      "severity": "HIGH",
      "level": "error",
      "message": "Hardcoded password 'admin123' detected in configuration",
      "file_path": "test-config.js",
      "rule_name": "Hardcoded Password Detection",
      "short_description": "Hardcoded password found",
      "full_description": "Application contains hardcoded password which poses security risk",
      "help_uri": "https://cwe.mitre.org/data/definitions/798.html",
      "tool_name": "Semgrep",
      "path": "test-config.js",
      "start": {"line": 15},
      "cwe": ["CWE-798"],
      "owasp": [],
      "technology": ["javascript"],
      "category": "security"
    },
    "status": "success"
  },
  // ... 7 more vulnerability objects matching controlled test data
]
```

#### 2.2 core_analysis_fixture.json
**Purpose**: Input for `--only-rag-enhancement`
**Format**: Array of vulnerability objects with AI analysis added
```json
[
  {
    "vulnerability": {
      // Same structure as above
    },
    "analysis": {
      "vulnerability_id": "test.hardcoded-password",
      "severity": "HIGH",
      "tool": "semgrep",
      "raw_analysis": "This vulnerability represents a critical security flaw...",
      "structured_analysis": {
        "impact": "High",
        "exploitability": "Easy",
        "remediation": "Remove hardcoded password and use environment variables"
      }
    },
    "status": "success"
  },
  // ... 7 more analyzed vulnerabilities
]
```

#### 2.3 rag_enhanced_fixture.json
**Purpose**: Input for `--only-analysis-summary`
**Format**: Enhanced analysis with RAG context
```json
[
  {
    "vulnerability": {
      // Same vulnerability structure
    },
    "analysis": {
      // Enhanced with RAG improvements
      "vulnerability_id": "test.hardcoded-password",
      "severity": "HIGH",
      "tool": "semgrep",
      "raw_analysis": "Enhanced analysis with additional context...",
      "structured_analysis": {
        "impact": "High",
        "exploitability": "Easy",
        "remediation": "Remove hardcoded password and use environment variables",
        "rag_enhancements": {
          "additional_context": "WebAuthn applications are particularly sensitive to credential exposure...",
          "best_practices": ["Use environment variables", "Implement secret rotation"]
        }
      }
    },
    "status": "success"
  },
  // ... 7 more RAG-enhanced vulnerabilities
]
```

#### 2.4 analyzed_vulnerabilities_fixture.json
**Purpose**: Input for `--only-narrativization`
**Format**: Final analysis summary format
```json
[
  {
    "vulnerability": {
      // Same vulnerability structure
    },
    "analysis": {
      // Complete analysis with summary
    },
    "summary": {
      "risk_score": 8.5,
      "priority": "HIGH",
      "category": "Credential Management"
    },
    "status": "success"
  },
  // ... 7 more summarized vulnerabilities
]
```

#### 2.5 narrativized_fixture.json
**Purpose**: Input for `--only-datasets`
**Format**: Narrative training examples
```json
[
  {
    "vulnerability_id": "test.hardcoded-password",
    "narrative": {
      "problem_statement": "The application contains a hardcoded password in test-config.js at line 15...",
      "technical_details": "Semgrep rule test.hardcoded-password detected...",
      "impact_assessment": "This vulnerability allows unauthorized access...",
      "remediation_steps": "1. Remove the hardcoded password\n2. Use environment variables..."
    },
    "metadata": {
      "tool": "semgrep",
      "severity": "HIGH",
      "cwe": ["CWE-798"]
    }
  },
  // ... 7 more narratives
]
```

#### 2.6 Training Dataset Fixtures
**train_dataset_fixture.jsonl**: JSONL format for training
```jsonl
{"instruction": "Analyze this security vulnerability:", "response": "This is a hardcoded password vulnerability...", "metadata": {"vulnerability_id": "test.hardcoded-password"}}
{"instruction": "Provide remediation for SQL injection:", "response": "Use parameterized queries to prevent SQL injection...", "metadata": {"vulnerability_id": "test.sql-injection"}}
```

**validation_dataset_fixture.jsonl**: Smaller validation set
```jsonl
{"instruction": "Assess XSS vulnerability impact:", "response": "Cross-site scripting allows attackers to execute malicious scripts...", "metadata": {"vulnerability_id": "test.xss-vulnerability"}}
```

#### 2.7 Model Artifacts Fixture
**model_artifacts_fixture/**: Mock model directory
```
model_artifacts_fixture/
├── adapter_config.json
├── adapter_model.safetensors
├── tokenizer_config.json
└── training_args.json
```

### Phase 3: Refactor create_prerequisite_files_up_to() Method

Replace the current recursive method with simple direct path references to fixture files:

```python
def create_prerequisite_files_up_to(self, target_phase):
    """Return paths to fixture files needed for testing target_phase"""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "phase_inputs"

    if target_phase == "vulnerability-analysis":
        # Return direct path to parsed vulnerabilities fixture
        return {"parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json"}

    elif target_phase == "rag-enhancement":
        # Return paths to both parsed and core analysis fixtures
        return {
            "parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json",
            "core_analysis_file": fixtures_dir / "core_analysis_fixture.json"
        }

    elif target_phase == "analysis-summary":
        # Return paths to analysis prerequisites
        return {
            "parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json",
            "rag_enhanced_file": fixtures_dir / "rag_enhanced_fixture.json"
        }

    elif target_phase == "narrativization":
        # Return path to analyzed vulnerabilities fixture
        return {"analyzed_file": fixtures_dir / "analyzed_vulnerabilities_fixture.json"}

    elif target_phase == "datasets":
        # Return paths to both narrativized and parsed fixtures
        return {
            "narrativized_file": fixtures_dir / "narrativized_fixture.json",
            "parsed_file": fixtures_dir / "parsed_vulnerabilities_fixture.json"
        }

    elif target_phase == "training":
        # Return paths to training dataset fixtures
        return {
            "train_file": fixtures_dir / "train_dataset_fixture.jsonl",
            "validation_file": fixtures_dir / "validation_dataset_fixture.jsonl",
            "narrativized_file": fixtures_dir / "narrativized_fixture.json"
        }

    elif target_phase == "upload":
        # Return path to model artifacts fixture
        return {"model_dir": fixtures_dir / "model_artifacts_fixture"}

    else:
        raise ValueError(f"Unknown target phase: {target_phase}")
```

**Key Improvement**: This approach eliminates all file copying operations (`shutil.copy()`, `shutil.copytree()`) and temporary directory management. Instead, it simply returns direct paths to the permanent fixture files. The `process_artifacts.py` script receives the same file paths as arguments, achieving identical isolation benefits with significantly less complexity.

### Phase 4: Update Individual Phase Tests

Modify phase tests to validate they work correctly with fixture input data:

```python
def test_vulnerability_analysis_phase_outputs(self):
    """Test vulnerability analysis phase with fixture input"""
    # Use fixture instead of running parsing phase
    prerequisites = self.create_prerequisite_files_up_to("vulnerability-analysis")

    # Test the actual phase execution
    result = self.run_process_artifacts([
        "--only-vulnerability-analysis",
        "--parsed-input", str(prerequisites["parsed_file"])
    ])

    assert result.returncode == 0, f"Vulnerability analysis phase failed"

    # Validate outputs exist and have correct structure
    core_analysis_files = list(self.temp_output_dir.glob("core_analysis_*.json"))
    assert len(core_analysis_files) > 0, "Core analysis output file should exist"

    # Validate content structure
    with open(core_analysis_files[0]) as f:
        core_results = json.load(f)

    assert len(core_results) > 0, "Core analysis should process vulnerabilities"

    # Validate that fixture input was processed correctly
    sample_result = core_results[0]
    assert 'vulnerability' in sample_result, "Core analysis should preserve vulnerability data"
    assert 'analysis' in sample_result, "Core analysis should contain analysis results"
```

### Phase 5: Create Fixture Generation Utility

Create a utility script to generate fixtures from actual phase outputs (for maintenance):

```python
# scripts/generate_test_fixtures.py
"""
Utility to generate test fixtures from actual phase outputs
Run this when phase output formats change
"""

def generate_fixtures():
    # Run actual phases once to generate realistic fixture data
    # Save outputs as fixtures for future tests
    pass
```

## Benefits of This Approach

### ✅ **Performance Improvements**
- **Fast Tests**: No AI model loading or complex processing (tests run in ~seconds instead of minutes)
- **No File I/O Overhead**: No copying operations needed - direct path references to permanent fixtures
- **Parallel Execution**: Tests can run concurrently without resource conflicts
- **CI/CD Friendly**: No model dependencies for basic phase testing

### ✅ **Test Reliability**
- **True Isolation**: Each phase test is completely independent
- **No Cascading Failures**: One phase failure doesn't break subsequent tests
- **Deterministic**: Same input always produces same output
- **Focused Testing**: Tests exactly what `--only-*` flags should do

### ✅ **Maintainability**
- **Easy Edge Case Testing**: Create custom fixtures for specific scenarios
- **Clear Test Intent**: Each test clearly shows what it's validating
- **Simple Debugging**: No complex phase chains to debug
- **Fixture Versioning**: Easy to update fixtures when formats change
- **Version-Controlled Fixtures**: Permanent fixture files are visible and maintainable in source control

### ✅ **Development Workflow**
- **Quick Feedback**: Developers get instant feedback on phase logic changes
- **Resource Efficient**: No need for model downloads or GPU resources for basic tests
- **Isolated Development**: Work on one phase without affecting others

## Implementation Timeline

### Week 1: Foundation
- [ ] Create fixture directory structure
- [ ] Generate parsed_vulnerabilities_fixture.json
- [ ] Generate core_analysis_fixture.json
- [ ] Refactor first 2 phases of create_prerequisite_files_up_to()

### Week 2: Complete Fixtures
- [ ] Generate remaining fixture files (rag_enhanced, analyzed, narrativized)
- [ ] Generate training dataset fixtures
- [ ] Create model artifacts fixture directory
- [ ] Complete refactoring of create_prerequisite_files_up_to()

### Week 3: Test Updates & Validation
- [ ] Update all individual phase tests to use fixtures
- [ ] Validate that tests still properly exercise phase logic
- [ ] Create fixture generation utility script
- [ ] Update test documentation

### Week 4: Integration & Cleanup
- [ ] Run full test suite to ensure no regressions
- [ ] Keep existing end-to-end integration tests for complete pipeline validation
- [ ] Document new fixture-based testing approach
- [ ] Clean up old recursive test methods

## Migration Strategy

### Backwards Compatibility
- Keep existing full pipeline integration tests for end-to-end validation
- New fixture-based tests complement rather than replace comprehensive testing
- Maintain ability to test complete pipeline when needed

### Gradual Migration
1. **Phase 1**: Implement fixtures for parsing and vulnerability-analysis phases
2. **Phase 2**: Extend to analysis pipeline phases (rag-enhancement, analysis-summary)
3. **Phase 3**: Complete with training and upload phases
4. **Phase 4**: Optimize and clean up old methods

### Validation Approach
- Compare fixture-based test results with actual phase outputs during development
- Ensure fixture data matches real phase output formats
- Regular fixture updates when phase output formats evolve

## Files to Modify

### New Files to Create
```
tests/fixtures/phase_inputs/parsed_vulnerabilities_fixture.json
tests/fixtures/phase_inputs/core_analysis_fixture.json
tests/fixtures/phase_inputs/rag_enhanced_fixture.json
tests/fixtures/phase_inputs/analyzed_vulnerabilities_fixture.json
tests/fixtures/phase_inputs/narrativized_fixture.json
tests/fixtures/phase_inputs/train_dataset_fixture.jsonl
tests/fixtures/phase_inputs/validation_dataset_fixture.jsonl
tests/fixtures/phase_inputs/model_artifacts_fixture/
tests/fixtures/phase_inputs/README.md
scripts/generate_test_fixtures.py
```

### Files to Modify
```
tests/integration/test_process_artifacts_script.py
- Refactor create_prerequisite_files_up_to() method
- Update individual phase test methods
- Add fixture validation helpers

tests/integration/README.md (if exists)
- Document new fixture-based testing approach
```

This implementation will transform the integration tests from slow, interdependent tests to fast, isolated tests that truly validate the `--only-*` phase execution functionality while maintaining comprehensive end-to-end validation through separate integration tests.