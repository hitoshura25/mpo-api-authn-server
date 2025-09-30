# Structured Model Output Architecture Implementation Plan

**Status**: In Progress
**Priority**: High
**Created**: 2025-09-28
**Target**: Q4 2025

## Table of Contents
1. [Context & Historical Analysis](#context--historical-analysis)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Proposed Architecture](#proposed-architecture)
4. [Technical Specifications](#technical-specifications)
5. [Implementation Strategy](#implementation-strategy)
6. [Migration Plan](#migration-plan)
7. [Benefits & Risk Analysis](#benefits--risk-analysis)
8. [Testing Strategy](#testing-strategy)

---

## Context & Historical Analysis

### Current System Overview
The WebAuthn Security AI Analysis system performs sequential fine-tuning to create specialized models:
- **Stage 1**: Vulnerability Analysis Specialist (produces LoRA adapters)
- **Stage 2**: Code Fix Generation Specialist (produces complete fused models)

### Historical Problems Identified

#### 1. **Timestamp-Based Discovery Anti-Pattern**
```bash
# Current problematic code patterns:
stage1_files = list(search_path.glob("**/*stage1*analysis*.jsonl"))
latest_file = sorted(stage1_files, key=lambda f: f.stat().st_mtime)[-1]
model_dirs = list(isolated_models_dir.glob("webauthn-security-sequential_*"))
selected_model = sorted(model_dirs)[-1]  # Newest by name
```

**Issues**:
- Fragile assumptions about "newest = correct"
- Race conditions in concurrent execution
- Debugging nightmares when tracing model usage
- No explicit contracts about artifact locations

#### 2. **Ambiguous Directory Naming**
```bash
# Current naming scheme doesn't distinguish:
webauthn-security-sequential_20250927_204946_stage1_analysis/
webauthn-security-sequential_20250927_204946_stage2_codefix/
webauthn-security-sequential_20250927_204946_stage2_codefix_stage1_merged_stage1_merged/  # What?
```

**Problems**:
- Cannot distinguish LoRA adapters from full models
- Intermediate vs final artifacts unclear
- Complex nested naming conventions
- No clear artifact type identification

#### 3. **Validation Logic Confusion**
Recent fail-fast improvements exposed:
```python
# Error: Model missing required files: ['config.json', 'model.safetensors', 'tokenizer.json']
# Root cause: Trying to validate LoRA adapter directory as full model
```

**Evidence from Git Changes** (feat/security_ai_tests branch):
- Removed exception suppression that masked configuration issues
- Changed `return {'success': False, 'error': str(e)}` to `raise RuntimeError()`
- Now exposes real path discovery and validation problems

#### 4. **Storage Path Disconnects**
From process_artifacts_output.log:
```
2025-09-27 20:50:55,036 - WARNING - ⚠️ No Stage 1 training data found for mixing
2025-09-27 20:50:55,036 - WARNING - ⚠️ No Stage 1 data found - using Stage 2 data only
```

**Root Cause**: Stage 1 data discovery searches in `fine_tuned_models_dir` but training data stored elsewhere.

---

## Root Cause Analysis

### Primary Issues Exposed by Fail-Fast Improvements

#### Issue 1: Model Type Validation Mismatch
- **Problem**: `_load_model_for_validation()` expects full model files but Stage 1 produces LoRA adapters
- **Location**: `sequential_fine_tuner.py:813`
- **Impact**: Stage 1 model validation fails with `FileNotFoundError`

#### Issue 2: Stage 1 Data Discovery Failure
- **Problem**: `_get_stage1_training_data()` searches wrong directory structure
- **Location**: `sequential_fine_tuner.py:1230-1256`
- **Impact**: Stage 2 training can't prevent catastrophic forgetting

#### Issue 3: Artifact Type Ambiguity
- **Problem**: No clear distinction between adapter vs full model directories
- **Impact**: Validation logic applies wrong expectations to wrong artifact types

#### Issue 4: Configuration Disconnects
- **Problem**: CLI `--model-dir` doesn't align with internal path expectations
- **Impact**: Models saved to wrong locations, discovery fails

### Test Evidence
Integration test `test_training_phase_creates_complete_model_files` now correctly fails, exposing:
1. Models not saved to expected CLI-specified directory
2. Model validation trying to validate adapters as full models
3. Stage 1 data discovery searching in wrong paths

---

## Proposed Architecture

### Overview: Explicit Contract-Based Structure

Replace timestamp-based discovery with manifest-driven, explicitly structured output organization.

### New Directory Structure

```
~/shared-olmo-models/
├── base/                                    # Base models (unchanged)
│   └── OLMo-2-1B-mlx-q4/
├── training-runs/                           # All training runs
│   └── webauthn-security-{run-id}/         # Single training run
│       ├── run-manifest.json              # Explicit metadata
│       ├── stage1/                        # Stage 1 artifacts
│       │   ├── adapters/                  # LoRA adapters
│       │   │   ├── adapters.safetensors
│       │   │   └── adapter_config.json
│       │   ├── merged-model/              # Fused Stage 1 model
│       │   │   ├── config.json
│       │   │   ├── model.safetensors
│       │   │   └── tokenizer.json
│       │   └── training-data/
│       │       └── analysis-dataset.jsonl
│       ├── stage2/                        # Stage 2 artifacts
│       │   ├── adapters/                  # Stage 2 LoRA adapters
│       │   │   ├── adapters.safetensors
│       │   │   └── adapter_config.json
│       │   ├── final-model/               # Complete fused model
│       │   │   ├── config.json
│       │   │   ├── model.safetensors
│       │   │   └── tokenizer.json
│       │   └── training-data/
│       │       ├── codefix-dataset.jsonl
│       │       └── mixed-dataset.jsonl
│       ├── validation/                    # Validation artifacts
│       │   ├── stage1-validation.json
│       │   └── stage2-validation.json
│       └── metadata/                      # Run metadata
│           ├── training-summary.json
│           └── performance-metrics.json
```

### Key Design Principles

#### 1. **Explicit Artifact Typing**
- **`adapters/`**: Always contains LoRA adapter files only
- **`merged-model/`** or **`final-model/`**: Always contains complete model files
- **`training-data/`**: Always contains JSONL training datasets

#### 2. **Hierarchical Organization**
- **Run-level**: `webauthn-security-{run-id}/`
- **Stage-level**: `stage1/`, `stage2/`
- **Artifact-level**: `adapters/`, `final-model/`, `training-data/`

#### 3. **Manifest-Driven Discovery**
- No more timestamp sorting or glob pattern matching
- Explicit file paths in manifest
- Artifact type validation based on directory structure

---

## Technical Specifications

### Run Manifest Schema

```json
{
  "$schema": "https://example.com/schemas/training-run-manifest.json",
  "version": "1.0",
  "run_metadata": {
    "run_id": "webauthn-security-20250927_204946",
    "timestamp": "2025-09-27T20:49:46Z",
    "status": "completed|failed|in_progress",
    "total_duration_seconds": 1247.5,
    "base_model": "OLMo-2-1B-mlx-q4",
    "training_type": "sequential_fine_tuning"
  },
  "stage1": {
    "status": "completed",
    "duration_seconds": 634.2,
    "adapters_path": "./stage1/adapters/",
    "merged_model_path": "./stage1/merged-model/",
    "training_data_path": "./stage1/training-data/analysis-dataset.jsonl",
    "validation_path": "./validation/stage1-validation.json",
    "artifact_types": {
      "adapters": "lora",
      "merged_model": "full_model"
    }
  },
  "stage2": {
    "status": "completed",
    "duration_seconds": 613.3,
    "adapters_path": "./stage2/adapters/",
    "final_model_path": "./stage2/final-model/",
    "training_data_paths": {
      "codefix_dataset": "./stage2/training-data/codefix-dataset.jsonl",
      "mixed_dataset": "./stage2/training-data/mixed-dataset.jsonl"
    },
    "validation_path": "./validation/stage2-validation.json",
    "artifact_types": {
      "adapters": "lora",
      "final_model": "full_model"
    },
    "stage1_dependencies": {
      "adapter_path": "./stage1/adapters/",
      "merged_model_path": "./stage1/merged-model/"
    }
  },
  "validation": {
    "stage1_score": 0.94,
    "stage2_score": 0.91,
    "validation_timestamp": "2025-09-27T21:15:30Z"
  }
}
```

### Artifact Validation Rules

#### LoRA Adapter Directories (`*/adapters/`)
**Required Files**:
- `adapters.safetensors` (>1KB, valid safetensors format)
- `adapter_config.json` (valid JSON with MLX fields)

**Validation Logic**:
```python
def validate_lora_adapters(adapter_path: Path) -> bool:
    required_files = ['adapters.safetensors', 'adapter_config.json']
    for file in required_files:
        file_path = adapter_path / file
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False
    return True
```

#### Full Model Directories (`*/merged-model/`, `*/final-model/`)
**Required Files**:
- `config.json` (valid model config)
- `model.safetensors` (>1MB, valid safetensors format)
- `tokenizer.json` (valid tokenizer config)

**Validation Logic**:
```python
def validate_full_model(model_path: Path) -> bool:
    required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
    for file in required_files:
        file_path = model_path / file
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False
    return True
```

### Discovery API Interface

```python
class TrainingRunManager:
    def __init__(self, base_models_dir: Path):
        self.training_runs_dir = base_models_dir / "training-runs"

    def create_run(self, run_id: str) -> TrainingRun:
        """Create new training run with structured directories"""

    def get_latest_run(self) -> TrainingRun:
        """Get most recent completed run by manifest timestamp"""

    def get_run_by_id(self, run_id: str) -> TrainingRun:
        """Get specific run by ID"""

class TrainingRun:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.manifest = self._load_manifest()

    @property
    def stage1_adapters_path(self) -> Path:
        """Get validated Stage 1 LoRA adapters path"""

    @property
    def stage2_final_model_path(self) -> Path:
        """Get validated Stage 2 complete model path"""

    def get_stage1_training_data(self) -> Path:
        """Get Stage 1 training dataset for mixing"""
```

---

## Implementation Strategy

### Direct Migration Approach (Single Phase: Week 1-2)

**Rationale**: Based on CLAUDE.md fail-fast principles and avoiding dual-system complexity that leads to dead code, missed edge cases, and session continuity issues.

#### Day 1-3: Core Infrastructure Implementation
- **Implement `TrainingRunManager` and `TrainingRun` classes**
  - Complete manifest-driven discovery system
  - Directory structure creation and validation
  - Artifact type detection and validation rules

#### Day 4-6: Complete Discovery Logic Replacement
- **Replace ALL timestamp-based discovery in `sequential_fine_tuner.py`**
  - Remove `sorted(files)[-1]` patterns entirely
  - Replace `_get_stage1_training_data()` with manifest-based lookup
  - Update `_load_model_for_validation()` with artifact-type-aware validation
  - No fallback logic - fail fast if structure is wrong

#### Day 7-8: Process Artifacts Integration
- **Update `process_artifacts.py` to use new discovery API**
  - CLI `--model-dir` creates new structure directly
  - Training phase outputs to manifest-defined locations
  - Remove all legacy path assumptions

#### Day 9-10: Migration and Testing
- **One-time migration of existing runs**
  - Script to convert `~/shared-olmo-models/fine-tuned/` to new structure
  - Validation that migration preserved all artifacts correctly
  - Archive old structure after successful migration
- **Update all integration tests**
  - Expect new directory structure only
  - Test manifest-based discovery
  - Test artifact-type-specific validation

### Benefits of Direct Migration
1. **Clean Codebase**: No conditional logic for old vs new paths
2. **Fail-Fast Alignment**: Issues surface immediately, no masking
3. **Session Safety**: No partial migration state to track across sessions
4. **Single Source of Truth**: One discovery mechanism, easier to debug
5. **Immediate Benefits**: All reliability improvements available immediately

---

## Migration Plan

### One-Time Complete Migration

**No backward compatibility period** - clean cut to new structure aligned with fail-fast principles.

#### Migration Script Implementation
```python
def migrate_all_legacy_runs(legacy_base_dir: Path, new_base_dir: Path) -> bool:
    """Complete migration of all legacy training runs"""
    legacy_runs = list(legacy_base_dir.glob("webauthn-security-sequential_*"))

    for legacy_run_dir in legacy_runs:
        # Analyze directory structure
        artifacts = analyze_legacy_structure(legacy_run_dir)

        # Create new structured directory
        new_run_dir = create_new_run_structure(new_base_dir, artifacts.run_id)

        # Move artifacts to correct locations
        migrate_artifacts(artifacts, new_run_dir)

        # Generate manifest
        create_manifest(new_run_dir, artifacts)

        # Validate migration
        validate_migrated_run(new_run_dir)

    # Archive legacy directory after successful migration
    archive_legacy_runs(legacy_base_dir)
```

#### Migration Commands
```bash
# Complete migration (one-time operation)
python scripts/migrate_to_structured_output.py \
  --legacy-dir ~/shared-olmo-models/fine-tuned \
  --new-dir ~/shared-olmo-models/training-runs \
  --backup-legacy \
  --validate

# Validation only (after migration)
python scripts/validate_training_runs.py \
  --training-runs-dir ~/shared-olmo-models/training-runs \
  --strict
```

#### Migration Safety
- **Full backup** of legacy structure before migration
- **Validation** that all artifacts were correctly migrated
- **Rollback capability** if migration fails
- **Fail-fast** on any migration errors - no partial migrations

---

## Benefits & Risk Analysis

### Benefits

#### 1. **Debugging and Maintenance**
- **Explicit traceability**: Always know which exact artifacts were used
- **Clear artifact types**: No confusion between adapters and full models
- **Validation clarity**: Right validation for right artifact type
- **Concurrent safety**: No race conditions in discovery

#### 2. **System Reliability**
- **Fail-fast validation**: Immediate detection of configuration issues
- **Contract enforcement**: Explicit expectations about artifact structure
- **Error clarity**: Clear error messages about missing/wrong artifacts

#### 3. **Development Velocity**
- **Predictable structure**: Developers know exactly where to find artifacts
- **Easy testing**: Can mock specific manifest configurations
- **Simplified debugging**: Clear paper trail of training runs

### Risks and Mitigation

#### Risk 1: Migration Complexity
**Mitigation**:
- Implement backward compatibility during transition
- Provide automated migration scripts
- Extensive testing of migration logic

#### Risk 2: Storage Space Increase
**Impact**: More explicit directory structure may use more space
**Mitigation**:
- Implement cleanup policies for old runs
- Add compression for archived training data
- Monitor storage usage during rollout

#### Risk 3: Breaking Changes for External Tools
**Mitigation**:
- Maintain API compatibility through discovery interface
- Provide migration period with warnings
- Document new structure clearly

---

## Testing Strategy

### Unit Tests
```python
def test_training_run_manager_creation():
    """Test training run directory structure creation"""

def test_manifest_validation():
    """Test manifest schema validation"""

def test_artifact_type_detection():
    """Test LoRA vs full model detection"""

def test_discovery_api():
    """Test manifest-based discovery"""
```

### Integration Tests
```python
def test_end_to_end_training_with_new_structure():
    """Test complete training pipeline creates correct structure"""

def test_stage1_data_discovery_reliability():
    """Test Stage 1 data mixing works with new structure"""

def test_validation_logic_correctness():
    """Test validation applies correct rules to correct artifacts"""

def test_cli_model_dir_integration():
    """Test --model-dir creates outputs in specified location"""
```

### Migration Tests
```python
def test_legacy_run_migration():
    """Test migration of existing training runs"""

def test_backward_compatibility():
    """Test system works with mix of old and new structures"""
```

---

## Implementation Checklist

### Direct Migration Implementation
- [ ] **Day 1-3: Core Infrastructure**
  - [ ] Implement `TrainingRunManager` class with manifest support
  - [ ] Implement `TrainingRun` class with discovery API
  - [ ] Create manifest JSON schema validation
  - [ ] Add artifact-type-specific validation logic
  - [ ] Create directory structure utilities

- [ ] **Day 4-6: Complete Discovery Replacement**
  - [ ] Remove all timestamp-based sorting from `sequential_fine_tuner.py`
  - [ ] Replace `_get_stage1_training_data()` with manifest lookup
  - [ ] Update `_load_model_for_validation()` with type-aware validation
  - [ ] Remove legacy glob patterns and path assumptions
  - [ ] Ensure fail-fast on structure mismatches

- [ ] **Day 7-8: Process Integration**
  - [ ] Update `process_artifacts.py` to use new discovery API
  - [ ] Modify CLI `--model-dir` to create new structure
  - [ ] Update training phase output generation
  - [ ] Remove all legacy path handling

- [ ] **Day 9-10: Migration and Testing**
  - [ ] Create complete migration script for existing runs
  - [ ] Implement migration validation and rollback
  - [ ] Update all integration tests for new structure only
  - [ ] Add comprehensive validation tests
  - [ ] Document migration process and new structure

### Validation Checklist
- [ ] All existing training runs successfully migrated
- [ ] Integration tests pass with new structure
- [ ] No timestamp-based discovery code remains
- [ ] Manifest-based discovery works reliably
- [ ] Artifact type validation correctly distinguishes adapters vs models
- [ ] CLI `--model-dir` creates outputs in specified locations

---

## Conclusion

This structured approach addresses the fundamental issues exposed by the fail-fast improvements:

1. **Eliminates timestamp-based discovery** with explicit manifest contracts
2. **Separates artifact types** with clear directory structure
3. **Provides reliable validation** with type-specific validation logic
4. **Enables debugging** with complete traceability of training runs

The implementation plan provides a safe migration path while significantly improving system reliability and maintainability.

**Next Step**: Review and approve this plan, then begin direct implementation starting with core infrastructure (Day 1-3) to completely replace timestamp-based discovery with manifest-driven architecture.