# Configurable Phase Execution - Implementation Plan

## Overview

Replace the current `--stop-after` mechanism with configurable `--only-*` flags that allow individual phase execution with specified input files. This enables isolated phase testing and more flexible pipeline control.

## Current Phase Analysis

### Complete Phase List (8 Phases)
Based on `process_artifacts.py` analysis:

1. **parsing** - `parse_vulnerabilities_phase()`
2. **vulnerability-analysis** - `core_analysis_phase()` (initial AI analysis of vulnerabilities)
3. **rag-enhancement** - `rag_enhancement_phase()`
4. **analysis-summary** - `analysis_summary_phase()` (combines vulnerability analysis + RAG)
5. **narrativization** - `narrativization_phase()`
6. **datasets** - `datasets_phase()`
7. **training** - `training_phase()`
8. **upload** - `upload_phase()`

### Current Phase Dependencies
```
parsing → vulnerability-analysis → rag-enhancement → analysis-summary → narrativization → datasets → training → upload
```

**Input/Output Analysis:**
- **parsing**: scan_files → parsed_vulnerabilities.json
- **vulnerability-analysis**: parsed_vulnerabilities.json → core_analysis.json
- **rag-enhancement**: core_analysis.json → rag_enhanced.json
- **analysis-summary**: rag_enhanced.json → analyzed_vulnerabilities.json (summary)
- **narrativization**: analyzed_vulnerabilities.json → narrativized.json
- **datasets**: narrativized.json + parsed_vulnerabilities.json → train.jsonl + validation.jsonl
- **training**: train.jsonl + validation.jsonl + narrativized.json → model artifacts
- **upload**: model artifacts + dataset files → HuggingFace uploads

## Implementation Plan

### Step 1: Create Phase Constants

**File: `process_artifacts.py`** - Add at top of file:
```python
# Phase constants to avoid string repetition and typos
class Phases:
    PARSING = "parsing"
    VULNERABILITY_ANALYSIS = "vulnerability-analysis"
    RAG_ENHANCEMENT = "rag-enhancement"
    ANALYSIS_SUMMARY = "analysis-summary"
    NARRATIVIZATION = "narrativization"
    DATASETS = "datasets"
    TRAINING = "training"
    UPLOAD = "upload"

    # List for validation
    ALL_PHASES = [
        PARSING, VULNERABILITY_ANALYSIS, RAG_ENHANCEMENT, ANALYSIS_SUMMARY,
        NARRATIVIZATION, DATASETS, TRAINING, UPLOAD
    ]

    # Input requirements mapping
    PHASE_INPUTS = {
        PARSING: [],  # Uses --artifacts-dir
        VULNERABILITY_ANALYSIS: ['parsed_input'],
        RAG_ENHANCEMENT: ['vulnerability_analysis_input'],
        ANALYSIS_SUMMARY: ['rag_enhanced_input'],
        NARRATIVIZATION: ['analyzed_input'],
        DATASETS: ['narrativized_input', 'parsed_input'],  # Both needed
        TRAINING: ['train_input', 'validation_input', 'narrativized_input'],
        UPLOAD: ['model_dir', 'dataset_files']
    }
```

### Step 2: Replace CLI Arguments

**Remove:**
```python
parser.add_argument("--stop-after", choices=[...])
```

**Add:**
```python
# Single-phase execution flags
phase_group = parser.add_argument_group('Single Phase Execution')
phase_group.add_argument("--only-parsing", action="store_true",
                        help="Execute only parsing phase")
phase_group.add_argument("--only-vulnerability-analysis", action="store_true",
                        help="Execute only vulnerability analysis phase")
phase_group.add_argument("--only-rag-enhancement", action="store_true",
                        help="Execute only RAG enhancement phase")
phase_group.add_argument("--only-analysis-summary", action="store_true",
                        help="Execute only analysis summary phase")
phase_group.add_argument("--only-narrativization", action="store_true",
                        help="Execute only narrativization phase")
phase_group.add_argument("--only-datasets", action="store_true",
                        help="Execute only datasets phase")
phase_group.add_argument("--only-training", action="store_true",
                        help="Execute only training phase")
phase_group.add_argument("--only-upload", action="store_true",
                        help="Execute only upload phase")

# Input file arguments
input_group = parser.add_argument_group('Phase Input Files')
input_group.add_argument("--parsed-input", type=Path,
                        help="Parsed vulnerabilities file (for core-analysis+)")
input_group.add_argument("--vulnerability-analysis-input", type=Path,
                        help="Vulnerability analysis results file (for rag-enhancement+)")
input_group.add_argument("--rag-enhanced-input", type=Path,
                        help="RAG enhanced results file (for analysis+)")
input_group.add_argument("--analyzed-input", type=Path,
                        help="Analyzed vulnerabilities file (for narrativization+)")
input_group.add_argument("--narrativized-input", type=Path,
                        help="Narrativized vulnerabilities file (for datasets+)")
input_group.add_argument("--train-input", type=Path,
                        help="Training dataset file (for training)")
input_group.add_argument("--validation-input", type=Path,
                        help="Validation dataset file (for training)")
input_group.add_argument("--model-dir", type=Path,
                        help="Model directory (for upload)")
input_group.add_argument("--dataset-files", type=str,
                        help="Comma-separated dataset files (for upload)")
```

### Step 3: Validation Functions

```python
def get_active_only_phase(args) -> Optional[str]:
    """Get the single active --only-* phase flag, or None for multi-phase"""
    only_flags = {
        Phases.PARSING: args.only_parsing,
        Phases.VULNERABILITY_ANALYSIS: args.only_vulnerability_analysis,
        Phases.RAG_ENHANCEMENT: args.only_rag_enhancement,
        Phases.ANALYSIS_SUMMARY: args.only_analysis_summary,
        Phases.NARRATIVIZATION: args.only_narrativization,
        Phases.DATASETS: args.only_datasets,
        Phases.TRAINING: args.only_training,
        Phases.UPLOAD: args.only_upload
    }

    active_phases = [phase for phase, flag in only_flags.items() if flag]

    if len(active_phases) > 1:
        raise ValueError(f"Error: Cannot specify multiple --only-* flags: {', '.join(active_phases)}")

    return active_phases[0] if active_phases else None

def validate_phase_inputs(phase: str, args):
    """Validate that required input files exist for the specified phase"""
    required_inputs = Phases.PHASE_INPUTS[phase]
    missing_inputs = []

    for input_name in required_inputs:
        input_value = getattr(args, input_name, None)
        if not input_value:
            missing_inputs.append(f"--{input_name.replace('_', '-')}")
        elif hasattr(input_value, 'exists') and not input_value.exists():
            raise ValueError(f"Error: Input file does not exist: {input_value}")

    if missing_inputs:
        raise ValueError(f"Error: --only-{phase} requires: {', '.join(missing_inputs)}")

def load_phase_input(input_path: Path) -> Any:
    """Load JSON data from phase input file"""
    if not input_path.exists():
        raise ValueError(f"Input file not found: {input_path}")

    with open(input_path, 'r') as f:
        return json.load(f)
```

### Step 4: Single Phase Executor

```python
def execute_single_phase(phase: str, args) -> Dict[str, Any]:
    """Execute a single phase with provided inputs"""
    print(f"\n🎯 Executing single phase: {phase}")

    output_dir = str(args.output_dir)

    if phase == Phases.PARSING:
        # Extract scan files from artifacts directory
        scan_files = find_security_files(args.artifacts_dir)
        return parse_vulnerabilities_phase(scan_files, output_dir)

    elif phase == Phases.VULNERABILITY_ANALYSIS:
        vulnerabilities_file = args.parsed_input
        return core_analysis_phase(vulnerabilities_file, output_dir, args)

    elif phase == Phases.RAG_ENHANCEMENT:
        vulnerability_analysis_file = args.vulnerability_analysis_input
        return rag_enhancement_phase(vulnerability_analysis_file, output_dir, args)

    elif phase == Phases.ANALYSIS_SUMMARY:
        rag_enhanced_file = args.rag_enhanced_input
        return analysis_summary_phase(rag_enhanced_file, output_dir, args)

    elif phase == Phases.NARRATIVIZATION:
        analyzed_file = args.analyzed_input
        return narrativization_phase(analyzed_file, output_dir, args)

    elif phase == Phases.DATASETS:
        narrativized_file = args.narrativized_input
        parsed_file = args.parsed_input
        return datasets_phase(narrativized_file, parsed_file, output_dir, args)

    elif phase == Phases.TRAINING:
        train_file = args.train_input
        validation_file = args.validation_input
        narrativized_data = load_phase_input(args.narrativized_input)
        train_data = load_phase_input(train_file)

        # Create dummy summary for compatibility
        summary = {"phase": "training", "single_phase_execution": True}
        return training_phase(train_file, train_data, narrativized_data, summary, args)

    elif phase == Phases.UPLOAD:
        model_dir = args.model_dir
        dataset_files = args.dataset_files.split(',') if args.dataset_files else []

        # Create dummy summary for compatibility
        summary = {"phase": "upload", "single_phase_execution": True}
        return upload_phase(model_dir, summary, args)

    else:
        raise ValueError(f"Unknown phase: {phase}")
```

### Step 5: Update Main Function

```python
def main():
    parser = argparse.ArgumentParser(description="Process security artifacts with OLMo")
    # ... existing argument setup ...

    args = parser.parse_args()

    # Check for single-phase execution
    single_phase = get_active_only_phase(args)

    if single_phase:
        # Validate inputs for single phase
        validate_phase_inputs(single_phase, args)

        # Execute single phase
        result = execute_single_phase(single_phase, args)

        print(f"\n✅ Single phase '{single_phase}' completed successfully")
        return result
    else:
        # Execute normal multi-phase pipeline (existing logic)
        # ... existing main() logic unchanged ...
```

### Step 6: Update Phase Function Calls

Replace all hardcoded phase strings with constants:

**Before:**
```python
if args.stop_after == "parsing":
    return results
```

**After:**
```python
if args.stop_after == Phases.PARSING:
    return results
```

## Usage Examples

### Single Phase Execution
```bash
# Test only vulnerability analysis phase
python process_artifacts.py \
    --only-vulnerability-analysis \
    --parsed-input ./test_data/parsed_vulnerabilities.json \
    --output-dir ./test_output

# Test only datasets phase with both required inputs
python process_artifacts.py \
    --only-datasets \
    --narrativized-input ./test_data/narrativized.json \
    --parsed-input ./test_data/parsed.json \
    --output-dir ./results

# Test RAG enhancement in isolation
python process_artifacts.py \
    --only-rag-enhancement \
    --vulnerability-analysis-input ./test_data/vulnerability_analysis.json
```

### Error Cases
```bash
# Multiple phases (should error)
python process_artifacts.py --only-parsing --only-vulnerability-analysis

# Missing required input (should error)
python process_artifacts.py --only-datasets --narrativized-input ./test.json
# Error: --only-datasets requires: --parsed-input
```

### Normal Multi-Phase (Unchanged)
```bash
# Existing behavior still works
python process_artifacts.py --artifacts-dir ./data
```

## Testing Integration

### New Test Methods
Add to `test_process_artifacts_script.py`:

```python
def test_single_phase_parsing(self):
    """Test isolated parsing phase execution"""
    result = self.run_process_artifacts(["--only-parsing"])
    assert result.returncode == 0
    # Verify only parsing outputs exist

def test_single_phase_datasets(self):
    """Test isolated datasets phase with provided inputs"""
    result = self.run_process_artifacts([
        "--only-datasets",
        "--narrativized-input", str(self.test_narratives_file),
        "--parsed-input", str(self.test_parsed_file)
    ])
    assert result.returncode == 0
    # Verify dataset files created

def test_multiple_only_flags_error(self):
    """Test that multiple --only-* flags raise error"""
    result = self.run_process_artifacts([
        "--only-parsing",
        "--only-analysis"
    ])
    assert result.returncode != 0
    assert "Cannot specify multiple --only-" in result.stderr

def test_missing_phase_inputs_error(self):
    """Test that missing required inputs raise error"""
    result = self.run_process_artifacts([
        "--only-datasets",
        "--narrativized-input", "./missing.json"
    ])
    assert result.returncode != 0
    assert "--parsed-input" in result.stderr
```

## Implementation Steps

1. **Step 1**: Add `Phases` class with constants
2. **Step 2**: Replace CLI arguments (remove `--stop-after`, add `--only-*` and input flags)
3. **Step 3**: Implement validation functions
4. **Step 4**: Create `execute_single_phase()` function
5. **Step 5**: Update `main()` function with single-phase logic
6. **Step 6**: Replace all hardcoded phase strings with constants
7. **Step 7**: Add comprehensive integration tests
8. **Step 8**: Update existing `--stop-after` usage throughout codebase

## Benefits

1. **Constants Eliminate Typos**: All phase names centralized in `Phases` class
2. **Isolated Testing**: Test any phase independently with controlled inputs
3. **Clear Validation**: Explicit error messages for missing/invalid inputs
4. **Maintainable**: Single source of truth for phase definitions
5. **Backward Compatible**: Existing multi-phase usage unchanged
6. **Flexible Development**: Skip expensive phases during development
7. **Better Debugging**: Focus on specific phase logic issues

## Migration Considerations

- **Backward Compatibility**: Remove `--stop-after` but maintain multi-phase default behavior
- **Error Messages**: Provide clear guidance when users have invalid input combinations
- **Documentation**: Update README with new usage patterns
- **Integration Tests**: Ensure all existing tests continue to pass
- **Phase Dependencies**: Maintain correct data flow between phases when run individually

This implementation transforms the pipeline from a rigid sequential system to a flexible, testable, configurable architecture while maintaining simplicity and clear validation rules.