# Process Artifacts Refactoring - Detailed Implementation Plan

## Overview

**Goal**: Create a new `process_artifacts_new.py` file alongside the existing monolithic version, implementing a clean 6-phase architecture with proper `--stop-after` support and correct file naming.

**Problem Statement**: The current `process_all_scans_enhanced()` function is a 460-line monolith containing 6 distinct phases mixed together, making it:
- Impossible to test phases individually
- No support for `--stop-after` functionality
- Wrong file naming causing integration test failures
- Difficult to maintain and extend

## Current State Analysis

### Monolithic Function Structure (process_all_scans_enhanced)
```
Lines 138-197:  Phase 1 - Vulnerability Parsing
Lines 200-255:  Phase 2 - AI Analysis
Lines 257-301:  Phase 3 - RAG Enhancement
Lines 323-361:  Phase 4 - Narrativization
Lines 363-499:  Phase 5 - Dataset Creation
Lines 500-578:  Phase 6 - Upload & Training
```

### Key Issues
1. **File Naming**: Creates `olmo_analysis_results_*.json` but tests expect `analyzed_vulnerabilities_*.json`
2. **No Phase Control**: No `--stop-after` argument support
3. **Tight Coupling**: Each phase directly uses variables from previous phase
4. **Testing Impossible**: Cannot test individual phases in isolation

## Detailed Implementation Plan

### Step 1: Create New File Structure

**File**: `security-ai-analysis/process_artifacts_new.py`

#### 1.1 Copy Base Structure
```python
#!/usr/bin/env python3
"""
Process downloaded GitHub Actions security artifacts with OLMo - Refactored Phase Architecture
"""
# Copy all imports from original file
# Copy utility functions: extract_artifacts(), find_security_files(), download_latest_artifacts()
```

#### 1.2 Add Phase Control Argument
```python
def main():
    parser.add_argument("--stop-after",
                       choices=["parsing", "analysis", "narrativization", "datasets", "training", "upload"],
                       help="Stop processing after the specified phase")
```

### Step 2: Implement Phase Functions

#### 2.1 Phase 1: `parse_vulnerabilities_phase()`

**Source**: Extract from original lines 138-197
**Function Signature**:
```python
def parse_vulnerabilities_phase(scan_files: dict, output_dir: str) -> Tuple[List, Path, Path]:
    """
    Phase 1: Parse security scan files and extract vulnerabilities

    Input:
        - scan_files: dict with scan tool files
        - output_dir: Output directory for results

    Output Files:
        - parsed_vulnerabilities_{timestamp}.json: Array of vulnerability objects
        - parsing_summary_{timestamp}.json: Summary statistics

    Returns:
        (all_vulnerabilities: List, vulnerabilities_file: Path, summary_file: Path)
    """
```

**Implementation Details**:
- Initialize empty `all_vulnerabilities = []`
- Loop through scan_files by type (trivy, checkov, semgrep, osv, sarif, zap)
- Parse each file using appropriate parser
- Accumulate vulnerabilities in list
- Generate summary with counts by tool
- Save files with timestamped names
- Return vulnerabilities list and file paths

#### 2.2 Phase 2: `analysis_phase()`

**Source**: Extract from original lines 200-255
**Function Signature**:
```python
def analysis_phase(vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path, Path]:
    """
    Phase 2: AI analysis of parsed vulnerabilities

    Input:
        - vulnerabilities_file: Path to parsed_vulnerabilities_*.json from Phase 1
        - output_dir: Output directory for analysis results
        - args: Command line arguments (model_name, branch, commit, etc.)

    Output Files:
        - analyzed_vulnerabilities_{timestamp}.json: AI-analyzed vulnerability objects
        - analysis_summary_{timestamp}.json: Analysis statistics and metadata

    Returns:
        (analyzed_vulnerabilities: List, analysis_file: Path, summary_file: Path)
    """
```

**Implementation Details**:
- Load vulnerabilities from Phase 1 output file
- Initialize OLMo analyzer
- Process vulnerabilities in batches (30 for OLMo-2, 20 for others)
- Generate analysis results using `analyzer.batch_analyze()`
- Generate summary report with enhanced metadata
- **CRITICAL**: Save to `analyzed_vulnerabilities_{timestamp}.json` (NOT `olmo_analysis_results`)
- Save summary to `analysis_summary_{timestamp}.json`
- Handle RAG enhancement if enabled
- Return analysis results and file paths

#### 2.3 Phase 3: `narrativization_phase()`

**Source**: Extract from original lines 323-361
**Function Signature**:
```python
def narrativization_phase(analysis_file: Path, output_dir: str) -> Tuple[List, Path]:
    """
    Phase 3: Create rich security narratives from AI analysis

    Input:
        - analysis_file: Path to analyzed_vulnerabilities_*.json from Phase 2
        - output_dir: Output directory for narrativized results

    Output Files:
        - narrativized_vulnerabilities_{timestamp}.json: Vulnerability stories

    Returns:
        (narrativized_results: List, narrativized_file: Path)
    """
```

**Implementation Details**:
- Load analysis results from Phase 2 output file
- Initialize `SecurityNarrativizer`
- Create narratives for each successful analysis result
- Build narrativized items with structure:
  ```json
  {
    "vulnerability_id": "...",
    "original_analysis": "...",
    "narrative": "...",
    "created_at": "timestamp"
  }
  ```
- Save to `narrativized_vulnerabilities_{timestamp}.json`
- Return narrativized results and file path

#### 2.4 Phase 4: `datasets_phase()`

**Source**: Extract from original lines 363-499
**Function Signature**:
```python
def datasets_phase(narrativized_file: Path, output_dir: str, all_vulnerabilities: List) -> Tuple[Path, Path, Dict]:
    """
    Phase 4: Create training and validation datasets

    Input:
        - narrativized_file: Path to narrativized_vulnerabilities_*.json from Phase 3
        - output_dir: Output directory for dataset files
        - all_vulnerabilities: Original vulnerability data for enhanced dataset creation

    Output Files:
        - train_{timestamp}.jsonl: Training dataset in JSONL format
        - validation_{timestamp}.jsonl: Validation dataset in JSONL format
        - dataset_info_{timestamp}.json: Dataset metadata and statistics

    Returns:
        (train_file: Path, validation_file: Path, dataset_info: Dict)
    """
```

**Implementation Details**:
- Load narrativized results from Phase 3 output file
- Create standard training pairs from narrativized data
- Create enhanced training pairs using `EnhancedDatasetCreator`
- Combine standard + enhanced training pairs
- Split into training/validation (80/20)
- Save training set to `train_{timestamp}.jsonl`
- Save validation set to `validation_{timestamp}.jsonl`
- Save dataset info to `dataset_info_{timestamp}.json`
- Return file paths and dataset info

#### 2.5 Phase 5: `training_phase()`

**Source**: Extract from original lines 560-578
**Function Signature**:
```python
def training_phase(train_file: Path, validation_file: Path, output_dir: str, args, narrativized_results: List) -> Tuple[Dict, List[Path]]:
    """
    Phase 5: Fine-tune models using training datasets

    Input:
        - train_file: Path to train_*.jsonl from Phase 4
        - validation_file: Path to validation_*.jsonl from Phase 4
        - output_dir: Output directory for model artifacts
        - args: Arguments (skip_fine_tuning, disable_sequential_fine_tuning, etc.)
        - narrativized_results: Full vulnerability data for sequential fine-tuning

    Output Files:
        - fine_tuned_model_{timestamp}/: Directory with fine-tuned model files
        - training_log_{timestamp}.json: Training metrics and progress
        - model_metadata_{timestamp}.json: Model configuration and performance

    Returns:
        (training_summary: Dict, model_paths: List[Path])
    """
```

**Implementation Details**:
- Check if sequential fine-tuning is available and enabled
- If sequential: Run `run_sequential_fine_tuning_phase()`
- If legacy: Run `integrate_fine_tuning_if_available()`
- Handle fine-tuning skipping based on args
- Return training summary and model paths

#### 2.6 Phase 6: `upload_phase()`

**Source**: Extract from original lines 500-559
**Function Signature**:
```python
def upload_phase(model_paths: List[Path], dataset_files: List[Path], output_dir: str, args, training_pairs: List) -> Dict:
    """
    Phase 6: Upload models and datasets to HuggingFace Hub

    Input:
        - model_paths: Paths to fine-tuned models from Phase 5
        - dataset_files: Dataset files to upload
        - output_dir: Output directory for upload logs
        - args: Arguments (skip_model_upload, etc.)
        - training_pairs: Training data for dataset upload

    Output Files:
        - upload_log_{timestamp}.json: Upload results and URLs

    Returns:
        (upload_summary: Dict)
    """
```

**Implementation Details**:
- Serialize training pairs for HuggingFace Dataset upload
- Upload dataset to `hitoshura25/webauthn-security-vulnerabilities-olmo`
- Handle enum serialization issues
- Return upload summary with URLs and status

### Step 3: Create Orchestrator Function

#### 3.1 Refactor `process_all_scans_enhanced()`

**New Implementation**:
```python
def process_all_scans_enhanced(scan_files: dict, output_dir: str, args) -> Tuple[List, Dict]:
    """
    Orchestrates security analysis phases with --stop-after support

    Phases:
        1. Parsing (always runs)
        2. Analysis (AI processing)
        3. Narrativization (story creation)
        4. Datasets (training data prep)
        5. Training (model fine-tuning)
        6. Upload (model/dataset publishing)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Phase 1: Always run parsing
    all_vulnerabilities, vulnerabilities_file, parsing_summary_file = parse_vulnerabilities_phase(scan_files, output_dir)

    if args.stop_after == "parsing":
        return load_results_from_files(vulnerabilities_file, parsing_summary_file)

    # Phase 2: AI Analysis
    analyzed_vulnerabilities, analysis_file, analysis_summary_file = analysis_phase(vulnerabilities_file, output_dir, args)

    if args.stop_after == "analysis":
        return load_results_from_files(analysis_file, analysis_summary_file)

    # Phase 3: Narrativization
    narrativized_results, narrativized_file = narrativization_phase(analysis_file, output_dir)

    if args.stop_after == "narrativization":
        return load_results_from_files(narrativized_file, analysis_summary_file)

    # Phase 4: Dataset Creation
    train_file, validation_file, dataset_info = datasets_phase(narrativized_file, output_dir, all_vulnerabilities)

    if args.stop_after == "datasets":
        return load_results_from_files(narrativized_file, dataset_info)

    # Phase 5: Training
    if not args.skip_fine_tuning:
        training_summary, model_paths = training_phase(train_file, validation_file, output_dir, args, narrativized_results)

        if args.stop_after == "training":
            return load_results_from_files(narrativized_file, training_summary)
    else:
        model_paths = []
        training_summary = {"status": "skipped"}

    # Phase 6: Upload
    if not args.skip_model_upload:
        upload_summary = upload_phase(model_paths, [train_file, validation_file], output_dir, args, training_pairs)

        # Final results
        return load_results_from_files(narrativized_file, {**training_summary, **upload_summary})

    # Return without upload
    return load_results_from_files(narrativized_file, training_summary)
```

#### 3.2 Helper Function
```python
def load_results_from_files(results_file: Path, summary_data) -> Tuple[List, Dict]:
    """Load results from file and return with summary"""
    if results_file.exists():
        with open(results_file, 'r') as f:
            results = json.load(f)
    else:
        results = []

    if isinstance(summary_data, Path) and summary_data.exists():
        with open(summary_data, 'r') as f:
            summary = json.load(f)
    elif isinstance(summary_data, dict):
        summary = summary_data
    else:
        summary = {}

    return results, summary
```

### Step 4: Implementation Order

#### 4.1 Phase 1: Create File and Basic Structure
1. Create `process_artifacts_new.py`
2. Copy imports and utility functions
3. Add `--stop-after` argument to main()
4. Copy `main()` function

#### 4.2 Phase 2: Implement Parsing Phase
1. Extract parsing logic into `parse_vulnerabilities_phase()`
2. Test parsing phase in isolation
3. Verify output files are created correctly

#### 4.3 Phase 3: Implement Analysis Phase
1. Extract analysis logic into `analysis_phase()`
2. Fix file naming to `analyzed_vulnerabilities_*.json`
3. Test analysis phase with `--stop-after analysis`
4. Verify integration test `test_ai_analysis_batch_processing` passes

#### 4.4 Phase 4: Implement Remaining Phases
1. Extract narrativization into `narrativization_phase()`
2. Extract datasets into `datasets_phase()`
3. Extract training into `training_phase()`
4. Extract upload into `upload_phase()`

#### 4.5 Phase 5: Create Orchestrator
1. Implement `process_all_scans_enhanced()` orchestrator
2. Add `load_results_from_files()` helper
3. Test all `--stop-after` options

### Step 5: Testing and Validation

#### 5.1 Unit Testing
- Test each phase function individually
- Verify correct input/output file formats
- Test error handling in each phase

#### 5.2 Integration Testing
- Run existing integration tests with new file
- Verify `test_ai_analysis_batch_processing` passes
- Test all `--stop-after` options work correctly

#### 5.3 Performance Testing
- Verify `--stop-after analysis` completes in ~30 seconds
- Verify `--stop-after parsing` completes in ~3 seconds
- Compare full pipeline performance with original

### Step 6: File Replacement

#### 6.1 Verification
- All tests pass with new file
- Performance is equivalent or better
- All functionality preserved

#### 6.2 Replacement
- Rename original: `process_artifacts.py` → `process_artifacts_old.py`
- Rename new: `process_artifacts_new.py` → `process_artifacts.py`
- Update any references in other files

## Success Criteria

### Architecture Goals
- ✅ **Modular Design**: 6 focused phase functions vs 1 monolithic function
- ✅ **Testable Phases**: Each phase independently testable with clear inputs/outputs
- ✅ **Fast Tests**: Phase stops work correctly (~3-30 seconds per phase)
- ✅ **Clear Dependencies**: File-based interfaces between phases
- ✅ **Maintainable Code**: <100 lines per phase function vs 460-line monolith

### Functional Goals
- ✅ **All Phase Stops Work**: `--stop-after` properly implemented for all 6 phases
- ✅ **File Names Match Tests**: Output files match integration test expectations
- ✅ **Backward Compatibility**: Existing consumers still work
- ✅ **Integration Tests Pass**: All existing and new tests pass
- ✅ **Performance**: No regression in pipeline execution time

### File Naming Corrections
- ❌ `olmo_analysis_results_{timestamp}.json` → ✅ `analyzed_vulnerabilities_{timestamp}.json`
- ✅ `analysis_summary_{timestamp}.json` (unchanged)
- ✅ `parsed_vulnerabilities_{timestamp}.json` (new)
- ✅ `parsing_summary_{timestamp}.json` (new)

## Risk Mitigation

### Risks
1. **Breaking Changes**: New implementation might break existing functionality
2. **File Format Changes**: Output file formats might change unintentionally
3. **Performance Regression**: New architecture might be slower
4. **Integration Issues**: Phase dependencies might not work correctly

### Mitigation Strategies
1. **Parallel Implementation**: Keep original file until new one is fully validated
2. **Comprehensive Testing**: Test each phase individually and as complete pipeline
3. **Format Validation**: Ensure output formats exactly match original
4. **Performance Monitoring**: Compare execution times at each phase

## Implementation Timeline

### Day 1: Foundation
- Create new file structure
- Implement parsing phase
- Add basic orchestrator

### Day 2: Core Phases
- Implement analysis phase
- Fix file naming issues
- Test integration with existing tests

### Day 3: Advanced Phases
- Implement narrativization phase
- Implement datasets phase

### Day 4: Training & Upload
- Implement training phase
- Implement upload phase
- Complete orchestrator

### Day 5: Testing & Validation
- Comprehensive testing
- Performance validation
- File replacement

This refactoring will transform the codebase from a monolithic, untestable architecture to a clean, modular, phase-based system that matches the intended design and enables proper integration testing.