# MLX Command Consolidation and Architecture Refactor

**Status**: In Progress
**Priority**: High
**Impact**: Code Quality, Maintainability, Consistency
**Target Completion**: 2025-10-02

## Problem Analysis

### Current Architecture Issues

#### 1. **Duplicated MLX Command Logic**
Multiple files implement `mlx_lm.lora` commands with different parameter sets:

- **`scripts/mlx_finetuning.py:512`** - Basic command
  ```python
  mlx_command = [
      "mlx_lm.lora",
      "--model", training_args["model"],
      "--train",
      "--data", str(training_data_dir),
      "--adapter-path", str(adapter_path),
      "--batch-size", str(training_args["batch_size"]),
      "--iters", str(training_args.get("training_steps", 100)),
      "--fine-tune-type", "lora"
      # ❌ MISSING: --learning-rate, --optimizer
  ]
  ```

- **`sequential_fine_tuner.py:430`** - Stage 2 command (complete)
  ```python
  mlx_command = [
      "mlx_lm.lora",
      "--model", str(self.config.get_base_model_path()),
      "--train",
      "--data", str(training_data_dir),
      "--adapter-path", str(stage2_adapters_dir),
      "--batch-size", str(self.stage2_config['batch_size']),
      "--iters", str(self.stage2_config['iters']),
      "--learning-rate", str(self.stage2_config['learning_rate']),  # ✅ Present
      "--fine-tune-type", self.stage2_config['fine_tune_type'],
      "--optimizer", self.stage2_config['optimizer'],              # ✅ Present
      "--resume-adapter-file", str(Path(stage1_adapter_path) / "adapters.safetensors")
  ]
  ```

- **`sequential_fine_tuner.py:1397`** - Stage 1 command (complete)
  ```python
  mlx_command = [
      "mlx_lm.lora",
      "--model", str(self.config.get_base_model_path()),
      "--train",
      "--data", str(training_data_dir),
      "--adapter-path", str(stage1_adapter_path),
      "--batch-size", str(self.stage1_config['batch_size']),
      "--iters", str(self.stage1_config['iters']),
      "--learning-rate", str(self.stage1_config['learning_rate']),  # ✅ Present
      "--fine-tune-type", self.stage1_config['fine_tune_type'],
      "--optimizer", self.stage1_config['optimizer']               # ✅ Present
  ]
  ```

#### 2. **Inconsistent Parameter Usage**
- **MLXFineTuner**: Missing critical parameters (`--learning-rate`, `--optimizer`)
- **SequentialFineTuner**: Has complete, research-backed parameter sets
- **Result**: Different training quality depending on which code path is used

#### 3. **Unclear Architectural Boundaries**
- **MLXFineTuner**: Originally intended as MLX abstraction layer but has incomplete implementation
- **SequentialFineTuner**: Has evolved to bypass MLXFineTuner and call MLX directly
- **Dependencies**: SequentialFineTuner still imports MLXFineTuner but only for data preparation
- **Design Confusion**: Two classes doing similar work with different capabilities

#### 4. **Dead Code Discovery**
- **`_run_stage2_fine_tuning_from_stage1()`** method was unused dead code (already removed)
- **MLXFineTuner** may be partially obsolete for sequential training use cases

## Root Cause Analysis

### Original Design Intent
`MLXFineTuner` was designed as:
1. **Apple Silicon Abstraction Layer**: Handle MLX availability and compatibility
2. **MLX Command Wrapper**: Centralize MLX-specific operations
3. **Cross-Platform Testing**: Allow mocking for non-Apple environments

### Evolution Problems
1. **Sequential Training Requirements**: SequentialFineTuner needed features MLXFineTuner didn't have
2. **Parameter Incompleteness**: MLXFineTuner's basic implementation was insufficient
3. **Bypass Pattern**: SequentialFineTuner started calling MLX directly rather than enhancing MLXFineTuner
4. **Technical Debt**: Two parallel implementations instead of proper abstraction

## Proposed Solution

### Architecture Goal: Enhanced MLXFineTuner as Central MLX Abstraction

**Principle**: All MLX operations should go through MLXFineTuner, with SequentialFineTuner handling only high-level orchestration.

### Phase 1: Fix Parameter Inconsistencies (Immediate)

#### 1.1 **Standardize MLX Command Parameters**
Create canonical parameter set based on research-optimized SequentialFineTuner:

```python
# In MLXFineTuner
def _build_mlx_lora_command(self, training_config: dict) -> List[str]:
    """Build standardized MLX LoRA command with complete parameter set."""
    base_command = [
        "mlx_lm.lora",
        "--model", str(training_config["model_path"]),
        "--train",
        "--data", str(training_config["data_path"]),
        "--adapter-path", str(training_config["adapter_path"]),
        "--batch-size", str(training_config["batch_size"]),
        "--iters", str(training_config["iters"]),
        "--learning-rate", str(training_config["learning_rate"]),     # ✅ Always include
        "--fine-tune-type", training_config.get("fine_tune_type", "lora"),
        "--optimizer", training_config.get("optimizer", "adamw")      # ✅ Always include
    ]

    # Optional parameters
    if "resume_adapter_file" in training_config:
        base_command.extend(["--resume-adapter-file", str(training_config["resume_adapter_file"])])

    return base_command
```

#### 1.2 **Add Missing Parameters to Existing MLXFineTuner**
Update `scripts/mlx_finetuning.py:512` to include missing parameters:
- Add `--learning-rate` from config
- Add `--optimizer` from config
- Maintain backward compatibility

### Phase 2: Create Specialized MLX Methods

#### 2.1 **Add Sequential Training Methods to MLXFineTuner**

```python
class MLXFineTuner:
    def run_stage1_training(self, training_data_dir: Path, adapter_output_dir: Path,
                           stage1_config: dict) -> Path:
        """Run Stage 1 training with MLX optimization."""

    def run_stage2_training(self, training_data_dir: Path, adapter_output_dir: Path,
                           stage2_config: dict, stage1_adapter_path: Path) -> Path:
        """Run Stage 2 training with resume-adapter-file support."""

    def run_basic_training(self, training_data_dir: Path, output_dir: Path,
                          training_config: dict) -> Path:
        """Run basic fine-tuning (existing functionality, enhanced)."""

    def fuse_adapter_with_model(self, base_model_path: Path, adapter_path: Path,
                               output_path: Path) -> Path:
        """Create fused model from base model and adapter."""
```

#### 2.2 **Support Structured Training Runs**
- Add TrainingRun awareness to MLXFineTuner
- Handle manifest-based path management
- Support lazy directory creation

### Phase 3: Refactor SequentialFineTuner

#### 3.1 **Remove Direct MLX Calls**
Replace these 3 direct MLX command implementations:
- `sequential_fine_tuner.py:430` → `self.base_fine_tuner.run_stage2_training()`
- `sequential_fine_tuner.py:1397` → `self.base_fine_tuner.run_stage1_training()`
- Remove subprocess.run() calls from SequentialFineTuner

#### 3.2 **Simplify SequentialFineTuner Responsibilities**
Focus on:
- High-level training orchestration
- Catastrophic forgetting prevention integration
- Training run management
- Progress tracking and logging
- Model validation coordination

#### 3.3 **Enhanced MLXFineTuner Interface**
```python
# New interface for SequentialFineTuner
class MLXFineTuner:
    def __init__(self, config: OLMoSecurityConfig, training_run: Optional[TrainingRun] = None):
        self.config = config
        self.training_run = training_run

    def set_training_run(self, training_run: TrainingRun):
        """Set structured training run for organized output."""

    def run_stage1_training(self, **kwargs) -> TrainingResult:
        """Enhanced stage 1 training with full error handling."""

    def run_stage2_training(self, **kwargs) -> TrainingResult:
        """Enhanced stage 2 training with sequential support."""
```

### Phase 4: Integration Points

#### 4.1 **Catastrophic Forgetting Prevention**
- MLXFineTuner should accept CF prevention hooks
- SequentialFineTuner handles CF logic, MLXFineTuner executes
- Clean separation of concerns

#### 4.2 **Configuration Integration**
- MLXFineTuner uses OLMoSecurityConfig for all parameters
- Consistent parameter sourcing across all training modes
- Environment variable override support

#### 4.3 **Error Handling Standardization**
- Centralize MLX-specific error handling in MLXFineTuner
- Consistent timeout and retry logic
- Better error messages with troubleshooting guidance

## Implementation Plan

### **Week 1: Parameter Standardization**
1. **Day 1-2**: Fix immediate parameter inconsistency in MLXFineTuner
2. **Day 3-4**: Create `_build_mlx_lora_command()` method with complete parameters
3. **Day 5**: Test parameter fixes with existing training pipeline

### **Week 2: Method Enhancement**
1. **Day 1-2**: Add stage1/stage2 training methods to MLXFineTuner
2. **Day 3-4**: Add model fusion and structured training run support
3. **Day 5**: Integration testing with TrainingRun instances

### **Week 3: SequentialFineTuner Refactor**
1. **Day 1-2**: Replace direct MLX calls with MLXFineTuner method calls
2. **Day 3-4**: Remove subprocess logic from SequentialFineTuner
3. **Day 5**: End-to-end testing of refactored sequential training

### **Week 4: Validation and Cleanup**
1. **Day 1-2**: Comprehensive testing of all training modes
2. **Day 3**: Performance validation and regression testing
3. **Day 4**: Documentation updates and code cleanup
4. **Day 5**: Final integration testing and deployment preparation

## Success Criteria

### **Code Quality**
- ✅ Single source of truth for all MLX commands
- ✅ Consistent parameters across all training modes
- ✅ No duplicated MLX command logic

### **Architecture**
- ✅ Clear separation: MLXFineTuner (MLX operations) vs SequentialFineTuner (orchestration)
- ✅ Proper abstraction layer for Apple Silicon/MLX dependencies
- ✅ Enhanced testability through centralized MLX interface

### **Functionality**
- ✅ All existing training modes continue to work
- ✅ No regression in sequential training quality
- ✅ Improved parameter consistency leads to better training outcomes

### **Maintainability**
- ✅ Easy to add new MLX operations or parameters
- ✅ Centralized error handling and troubleshooting
- ✅ Clear code ownership and responsibility boundaries

## Risk Mitigation

### **Training Pipeline Disruption**
- **Risk**: Refactoring breaks existing training workflows
- **Mitigation**: Maintain backward compatibility during transition
- **Testing**: Comprehensive regression testing at each phase

### **Parameter Regression**
- **Risk**: Missing or incorrect parameters reduce training quality
- **Mitigation**: Use SequentialFineTuner's proven parameter set as baseline
- **Validation**: Compare training outcomes before/after refactor

### **Apple Silicon Dependencies**
- **Risk**: Changes break MLX compatibility or cross-platform testing
- **Mitigation**: Preserve existing MLX availability checking
- **Testing**: Test on both Apple Silicon and non-MLX environments

## Files to Modify

### **Primary Changes**
1. **`scripts/mlx_finetuning.py`** - Enhanced MLXFineTuner with complete parameter support
2. **`sequential_fine_tuner.py`** - Simplified to use MLXFineTuner methods
3. **`config_manager.py`** - Ensure all MLX parameters are available via config

### **Supporting Changes**
1. **`sequential_pipeline_integration.py`** - Update MLXFineTuner usage patterns
2. **`model_uploader.py`** - May need MLXFineTuner interface updates
3. **Test files** - Update mocking and testing patterns

### **Documentation Updates**
1. **`CLAUDE.md`** - Update development commands and patterns
2. **Architecture docs** - Document new MLX abstraction layer
3. **Training guides** - Update with consolidated approach

## Validation Testing

### **Regression Testing**
- [ ] Basic fine-tuning still works (MLXFineTuner standalone)
- [ ] Sequential training produces same quality results
- [ ] All parameter configurations work correctly
- [ ] Cross-platform compatibility maintained

### **Integration Testing**
- [ ] Catastrophic forgetting prevention integration
- [ ] Structured training run support
- [ ] Error handling and recovery
- [ ] Configuration override mechanisms

### **Performance Testing**
- [ ] No performance regression in training speed
- [ ] Memory usage remains optimal
- [ ] MLX device utilization unchanged

## Future Benefits

### **Extensibility**
- Easy to add new MLX operations (quantization, merging, etc.)
- Simple parameter additions for new research techniques
- Clear interface for other training approaches

### **Testing**
- Mock MLXFineTuner for cross-platform CI/CD
- Isolated testing of MLX vs orchestration logic
- Better unit test coverage

### **Maintenance**
- Single place to update MLX command syntax
- Centralized error handling and troubleshooting
- Consistent logging and progress reporting

---

**Next Actions**:
1. Review and approve this architectural plan
2. Begin Phase 1 implementation with parameter standardization
3. Set up regression testing framework for validation