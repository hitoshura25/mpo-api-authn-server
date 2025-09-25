# Integration Fixes - Test-Driven Implementation Plan

## Overview & Context

This document provides a comprehensive implementation plan to fix critical integration issues in the `security-ai-analysis` pipeline, specifically addressing code-aware dataset warnings and missing integrations. The approach follows the successful test-driven modular refactoring pattern used previously.

## Problem Statement

### Root Cause Analysis

**Primary Issue**: The `EnhancedDatasetCreator` in `process_artifacts.py` is receiving incorrect data format, causing massive "Failed to extract context" warnings.

**Current Flow (BROKEN)**:
```
parsing → analysis → narrativization → datasets(narrativized_data) ❌
```

**Expected Flow (CORRECT)**:
```
parsing → analysis → narrativization → datasets(raw_vulnerability_data) ✅
```

**Specific Problem**: Line 793-796 in `process_artifacts.py`:
```python
enhanced_result = creator.create_enhanced_dataset(
    narrativized_results,  # ❌ WRONG: {vulnerability_id, narrative, created_at}
    dataset_name=dataset_name
)
```

**Expected Input**: Raw vulnerability data with fields like `{tool, id, file_path, start, severity, ...}`

**Actual Input**: Narrativized data with fields like `{vulnerability_id, narrative, original_analysis, created_at}`

### Secondary Issues

1. **URL-to-Code Mapping Not Integrated**: `url_to_code_mapper.py` exists but isn't used to enhance ZAP/DAST vulnerabilities
2. **File-Based Data Flow Incomplete**: Datasets phase doesn't have access to original vulnerability data
3. **Integration Test Coverage Gap**: No tests validate data contracts between phases

## Current Architecture Context

### 6-Phase Modular Architecture
```
Phase 1: parse_vulnerabilities_phase()     → parsed_vulnerabilities_*.json
Phase 2: analysis_phase() (3 sub-phases)   → analyzed_vulnerabilities_*.json
Phase 3: narrativization_phase()           → narrativized_*.json
Phase 4: datasets_phase()                  → train_*.jsonl, validation_*.jsonl
Phase 5: training_phase()                  → model artifacts
Phase 6: upload_phase()                    → HuggingFace uploads
```

### File-Based Communication Pattern
Each phase:
- Reads input from previous phase output files
- Produces timestamped output files
- Uses file paths for clean separation of concerns

## Test-Driven Implementation Strategy

### Approach
1. **Create failing tests** that detect the integration issues
2. **Run tests to confirm failures**
3. **Implement fixes** to make tests pass
4. **Verify tests pass** and no regressions

### Optimization Strategy
Group test cases by `--stop-after` point to minimize pipeline executions:
- `--stop-after parsing`: 1 execution, multiple parsing tests
- `--stop-after analysis`: 1 execution, multiple analysis tests
- `--stop-after narrativization`: 1 execution, multiple narrativization tests
- `--stop-after datasets`: 1 execution, multiple datasets tests

**Total: 4 optimized test executions instead of 8+ individual tests**

## Detailed Test Specifications

### Test File Location
`/Users/vinayakmenon/mpo-api-authn-server/security-ai-analysis/tests/integration/test_process_artifacts_script.py`

### Test 1: Parsing Phase Outputs (`--stop-after parsing`)

```python
def test_parsing_phase_outputs(self):
    """Test all parsing phase outputs in single execution"""
    result = self.run_process_artifacts(["--stop-after", "parsing"])
    assert result.returncode == 0, f"Parsing phase failed: {result.stderr}"

    # Test 1: Parsed vulnerabilities file structure
    parsed_files = list(self.temp_output_dir.glob("parsed_vulnerabilities_*.json"))
    assert len(parsed_files) > 0, "Should have parsed vulnerabilities file"

    with open(parsed_files[0]) as f:
        parsed_data = json.load(f)

    assert len(parsed_data) > 0, "Parsed vulnerabilities should not be empty"

    # Test 2: Raw vulnerability data structure (needed by enhanced dataset creator)
    successful_results = [r for r in parsed_data if r.get('status') == 'success']
    assert len(successful_results) > 0, "Should have successful parsing results"

    sample_vuln = successful_results[0]['vulnerability']
    assert 'tool' in sample_vuln, f"Parsed vulnerability should have 'tool' field: {list(sample_vuln.keys())}"
    assert 'id' in sample_vuln, f"Parsed vulnerability should have 'id' field: {list(sample_vuln.keys())}"
    assert 'narrative' not in sample_vuln, f"Raw vulnerability should not have 'narrative': {list(sample_vuln.keys())}"

    # Test 3: URL-based vulnerabilities should be identifiable
    zap_vulns = [r['vulnerability'] for r in successful_results
                if r['vulnerability'].get('tool') == 'zap']
    if zap_vulns:
        # ZAP vulnerabilities should have URL info that can be mapped later
        for zap_vuln in zap_vulns:
            assert 'site_host' in zap_vuln or 'url' in zap_vuln or 'path' in zap_vuln, \
                f"ZAP vulnerability should have URL info for mapping: {list(zap_vuln.keys())}"
```

### Test 2: Analysis Phase Outputs (`--stop-after analysis`)

```python
def test_analysis_phase_outputs(self):
    """Test all analysis phase outputs in single execution"""
    result = self.run_process_artifacts(["--stop-after", "analysis"])
    assert result.returncode == 0, f"Analysis phase failed: {result.stderr}"

    # Test 1: Analysis output files exist
    analysis_files = list(self.temp_output_dir.glob("analyzed_vulnerabilities_*.json"))
    assert len(analysis_files) > 0, "Analysis output file should exist"

    with open(analysis_files[0]) as f:
        analysis_results = json.load(f)

    # Test 2: Vulnerability data preserved through analysis
    parsed_files = list(self.temp_output_dir.glob("parsed_vulnerabilities_*.json"))
    with open(parsed_files[0]) as f:
        parsed_results = json.load(f)

    original_vuln_ids = {r['vulnerability']['id'] for r in parsed_results
                        if r.get('status') == 'success' and r.get('vulnerability', {}).get('id')}
    analysis_vuln_ids = {r['vulnerability']['id'] for r in analysis_results
                        if r.get('status') == 'success' and r.get('vulnerability', {}).get('id')}

    assert original_vuln_ids == analysis_vuln_ids, \
        f"Vulnerability IDs should be preserved: original={len(original_vuln_ids)}, analysis={len(analysis_vuln_ids)}"

    # Test 3: URL-to-Code mapping should enhance ZAP vulnerabilities
    zap_results = [r for r in analysis_results
                   if r.get('status') == 'success' and
                   r.get('vulnerability', {}).get('tool') == 'zap']

    if zap_results:
        for zap_result in zap_results:
            vuln_data = zap_result['vulnerability']
            # SHOULD FAIL: ZAP vulnerabilities should have file_path after URL mapping
            assert 'file_path' in vuln_data or 'mapped_file_path' in vuln_data, \
                f"ZAP vulnerability should have file mapping: {list(vuln_data.keys())}"

            if 'file_path' in vuln_data or 'mapped_file_path' in vuln_data:
                assert 'line_number' in vuln_data or 'mapped_line' in vuln_data, \
                    f"Mapped ZAP vulnerability should have line info: {list(vuln_data.keys())}"
```

### Test 3: Narrativization Phase Outputs (`--stop-after narrativization`)

```python
def test_narrativization_phase_outputs(self):
    """Test all narrativization phase outputs in single execution"""
    result = self.run_process_artifacts(["--stop-after", "narrativization"])
    assert result.returncode == 0, f"Narrativization phase failed: {result.stderr}"

    # Test 1: Narrativized output exists
    narrativized_files = list(self.temp_output_dir.glob("narrativized_*.json"))
    assert len(narrativized_files) > 0, "Narrativized file should exist"

    with open(narrativized_files[0]) as f:
        narrativized_data = json.load(f)

    assert len(narrativized_data) > 0, "Narrativized data should not be empty"

    # Test 2: Narrativized data structure
    sample = narrativized_data[0]
    assert 'narrative' in sample, f"Narrativized data should have narrative: {list(sample.keys())}"
    assert 'vulnerability_id' in sample, f"Narrativized data should have vulnerability_id: {list(sample.keys())}"

    # Test 3: All required input files available for datasets phase
    required_files = [
        ("parsed_vulnerabilities_*.json", "original vulnerability data"),
        ("analyzed_vulnerabilities_*.json", "analyzed vulnerability data"),
        ("narrativized_*.json", "narrativized content")
    ]

    for file_pattern, description in required_files:
        matching_files = list(self.temp_output_dir.glob(file_pattern))
        assert len(matching_files) > 0, f"Should have {description}: {file_pattern}"

        with open(matching_files[0]) as f:
            data = json.load(f)
        assert len(data) > 0, f"{description} file should not be empty"
```

### Test 4: Datasets Phase Outputs (`--stop-after datasets`)

```python
def test_datasets_phase_outputs(self):
    """Test all datasets phase outputs in single execution"""
    result = self.run_process_artifacts(["--stop-after", "datasets"])
    assert result.returncode == 0, f"Datasets phase failed: {result.stderr}"

    # Test 1: Standard dataset files created
    train_files = list(self.temp_output_dir.glob("train_*.jsonl"))
    validation_files = list(self.temp_output_dir.glob("validation_*.jsonl"))

    assert len(train_files) > 0, "Training dataset file should be created"
    assert len(validation_files) > 0, "Validation dataset file should be created"

    # Test 2: Enhanced dataset creator should receive correct input
    # Check if enhanced dataset directory was created (indicates EnhancedDatasetCreator was called)
    enhanced_dirs = list(Path("enhanced_datasets/code-aware-training").glob("*"))

    if enhanced_dirs:
        # Test 3: Enhanced dataset files should exist
        enhanced_file = None
        for dir_path in enhanced_dirs:
            potential_file = dir_path / "enhanced_examples.jsonl"
            if potential_file.exists():
                enhanced_file = potential_file
                break

        # SHOULD FAIL: Enhanced examples file should exist if enhanced dataset creator ran successfully
        assert enhanced_file is not None, "Enhanced examples JSONL file should be created"

        # Test 4: Enhanced examples should have code context
        with open(enhanced_file) as f:
            enhanced_examples = [json.loads(line) for line in f]

        # SHOULD FAIL: Should have enhanced examples with code context
        assert len(enhanced_examples) > 0, "Should have enhanced examples"

        code_aware_examples = 0
        for example in enhanced_examples:
            metadata = example.get('metadata', {})
            if 'file_path' in metadata or 'code_context' in metadata:
                code_aware_examples += 1

        assert code_aware_examples > 0, \
            f"Should have code-aware examples: {code_aware_examples}/{len(enhanced_examples)}"

    # Test 5: Verify datasets phase used correct input data
    # Read parsed vulnerabilities to see what should have been passed to enhanced dataset creator
    parsed_files = list(self.temp_output_dir.glob("parsed_vulnerabilities_*.json"))
    with open(parsed_files[0]) as f:
        parsed_data = json.load(f)

    raw_vulns = [r['vulnerability'] for r in parsed_data if r.get('status') == 'success']

    # Check if any training examples reference the original vulnerability structure
    with open(train_files[0]) as f:
        train_examples = [json.loads(line) for line in f]

    # Enhanced examples should exist if raw vulnerabilities were properly passed
    enhanced_train_examples = [ex for ex in train_examples
                              if ex.get('metadata', {}).get('enhancement_type') == 'code_aware']

    if len(raw_vulns) > 0 and len(enhanced_dirs) > 0:
        # SHOULD FAIL: If we have raw vulnerabilities and enhanced dataset creator ran,
        # we should have some enhanced examples
        assert len(enhanced_train_examples) > 0 or len(enhanced_examples) > 0, \
            f"Should have enhanced examples when raw vulnerabilities available: {len(raw_vulns)} raw vulns"
```

## Implementation Steps

### Step 1: Add Test Methods

Add the 4 test methods above to `tests/integration/test_process_artifacts_script.py`.

### Step 2: Run Tests to Confirm Failures

```bash
cd /Users/vinayakmenon/mpo-api-authn-server/security-ai-analysis
source venv/bin/activate

# Run optimized test suite (should fail on specific assertions)
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_parsing_phase_outputs -xvs
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_analysis_phase_outputs -xvs
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_narrativization_phase_outputs -xvs
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_datasets_phase_outputs -xvs
```

**Expected Failures**:
- `test_analysis_phase_outputs`: ZAP URL mapping assertions should fail
- `test_datasets_phase_outputs`: Enhanced dataset creation assertions should fail

### Step 3: Implement Fixes

#### Fix 1: Enhanced Dataset Creator Data Format

**Problem**: `datasets_phase()` passes `narrativized_results` instead of raw vulnerability data.

**Current Code** (`process_artifacts.py` line ~793):
```python
enhanced_result = creator.create_enhanced_dataset(
    narrativized_results,  # ❌ Wrong data format
    dataset_name=dataset_name
)
```

**Fix**: Update `datasets_phase()` function signature and implementation:

```python
def datasets_phase(narrativized_file: Path, parsed_vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path, Path]:
    """
    Phase 4: Prepare training and validation datasets with enhanced code-aware examples

    Input:
        - narrativized_file: Path to narrativized vulnerabilities from Phase 3
        - parsed_vulnerabilities_file: Path to raw vulnerabilities from Phase 1 (for enhanced dataset creator)
        - output_dir: Output directory for dataset files
        - args: Command line arguments
    """
    # Load narrativized results for standard dataset creation
    with open(narrativized_file, 'r') as f:
        narrativized_results = json.load(f)

    # Load raw vulnerability data for enhanced dataset creation
    with open(parsed_vulnerabilities_file, 'r') as f:
        parsed_results = json.load(f)

    raw_vulnerabilities = [r['vulnerability'] for r in parsed_results if r.get('status') == 'success']

    # Enhanced dataset creation with correct input
    from enhanced_dataset_creator import EnhancedDatasetCreator
    creator = EnhancedDatasetCreator()
    enhanced_result = creator.create_enhanced_dataset(
        raw_vulnerabilities,  # ✅ Correct: raw vulnerability data
        dataset_name=dataset_name
    )

    # ... rest of implementation
```

**Update Orchestrator Call** (in main orchestration function):
```python
# Phase 4: Dataset Creation
train_file, validation_file, dataset_info = datasets_phase(
    narrativized_file,
    vulnerabilities_file,  # ✅ Pass parsed vulnerabilities file
    output_dir,
    args
)
```

#### Fix 2: URL-to-Code Mapping Integration

**Location**: Add to `analysis_phase()` or create new sub-phase.

**Implementation**: Integrate `URLToCodeMapper` to enhance ZAP/URL-based vulnerabilities:

```python
def analysis_phase(vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path, Path]:
    """Enhanced analysis phase with URL-to-code mapping"""

    # Load vulnerabilities
    with open(vulnerabilities_file, 'r') as f:
        parsed_results = json.load(f)

    all_vulnerabilities = [r['vulnerability'] for r in parsed_results if r.get('status') == 'success']

    # URL-to-Code Mapping Enhancement
    try:
        from url_to_code_mapper import URLToCodeMapper, enhance_vulnerability_with_url_mapping

        project_root = Path(__file__).parent.parent  # Adjust as needed
        url_mapper = URLToCodeMapper(project_root)

        print("🗺️ Enhancing URL-based vulnerabilities with code mapping...")
        enhanced_vulnerabilities = []

        for vuln in all_vulnerabilities:
            if vuln.get('tool') in ['zap', 'dast']:
                # Enhance URL-based vulnerabilities
                enhanced_vuln = enhance_vulnerability_with_url_mapping(vuln, url_mapper)
                enhanced_vulnerabilities.append(enhanced_vuln)

                if enhanced_vuln.get('file_path'):
                    print(f"  ✅ Mapped {vuln.get('id', 'unknown')} to {enhanced_vuln['file_path']}")
            else:
                enhanced_vulnerabilities.append(vuln)

        all_vulnerabilities = enhanced_vulnerabilities

    except ImportError:
        print("⚠️ URL-to-Code mapping not available, continuing without enhancement")
    except Exception as e:
        print(f"⚠️ URL-to-Code mapping failed: {e}, continuing with original vulnerabilities")

    # Continue with AI analysis using enhanced vulnerabilities...
```

### Step 4: Verify Tests Pass

```bash
# Re-run the same tests after implementing fixes
source venv/bin/activate
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_parsing_phase_outputs -xvs
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_analysis_phase_outputs -xvs
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_narrativization_phase_outputs -xvs
python -m pytest tests/integration/test_process_artifacts_script.py::TestProcessArtifactsScript::test_datasets_phase_outputs -xvs

# Run full integration test suite to ensure no regressions
./run_tests.sh integration
```

### Step 5: Validation

After fixes, verify:

1. **No More Context Warnings**: The "Failed to extract context" warnings should be eliminated
2. **Enhanced Dataset Creation**: Code-aware examples should be generated successfully
3. **URL Mapping**: ZAP vulnerabilities should have `file_path` and `line_number` fields
4. **All Tests Pass**: Both new tests and existing integration tests should pass
5. **No Regressions**: Existing functionality should remain intact

## Key Integration Points

### Files to Modify

1. **`tests/integration/test_process_artifacts_script.py`**: Add 4 new test methods
2. **`process_artifacts.py`**:
   - Update `datasets_phase()` function signature and implementation
   - Update orchestrator calls to pass required file paths
   - Add URL-to-code mapping to analysis phase

### Dependencies

- **`enhanced_dataset_creator.py`**: Already exists, needs correct input format
- **`url_to_code_mapper.py`**: Already exists, needs integration
- **`vulnerable_code_extractor.py`**: Already exists, used by enhanced dataset creator
- **`multi_approach_fix_generator.py`**: Already exists, used by enhanced dataset creator
- **`fix_quality_assessor.py`**: Already exists, used by enhanced dataset creator

### Data Flow Architecture (After Fixes)

```
Phase 1: Parsing → parsed_vulnerabilities_file
Phase 2: Analysis → analyzed_vulnerabilities_file (enhanced with URL mappings)
Phase 3: Narrativization → narrativized_file
Phase 4: Datasets → Uses BOTH narrativized_file AND parsed_vulnerabilities_file
         ├── Standard dataset from narrativized_file
         └── Enhanced dataset from parsed_vulnerabilities_file ✅
Phase 5: Training → model artifacts
Phase 6: Upload → HuggingFace uploads
```

## Success Criteria

### Primary Goals
- ✅ Eliminate "Failed to extract context" warnings
- ✅ Generate actual code-aware enhanced training examples
- ✅ Map URL-based vulnerabilities to source code locations
- ✅ All integration tests pass without regressions

### Secondary Goals
- ✅ Maintain clean file-based phase architecture
- ✅ Preserve existing functionality and performance
- ✅ Enable future enhancements through proper data flow
- ✅ Comprehensive test coverage for integration contracts

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all enhancement modules are in Python path
2. **File Path Issues**: Verify project root detection for URL mapping
3. **Data Format Mismatches**: Check that phases receive expected file structures
4. **Missing Dependencies**: Ensure virtual environment has all required packages

### Debugging Commands

```bash
# Check test data structure
cd security-ai-analysis
python -c "
import json
from pathlib import Path
files = list(Path('tests/fixtures/controlled_test_data').glob('*.json'))
for f in files:
    with open(f) as file:
        data = json.load(f)
        print(f'{f.name}: {type(data)} with {len(data)} items')
"

# Verify enhanced dataset creator expectations
python -c "
from enhanced_dataset_creator import EnhancedDatasetCreator
help(EnhancedDatasetCreator.create_enhanced_dataset)
"
```

This plan provides complete context and implementation details for fixing the integration issues while maintaining the successful modular architecture pattern.