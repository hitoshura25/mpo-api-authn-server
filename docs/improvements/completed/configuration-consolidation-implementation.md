# Configuration Consolidation Implementation Plan

## Overview

This plan addresses the configuration management confusion identified in the security AI analysis system, where we currently have two overlapping configuration classes (`OLMoSecurityConfig` and `FineTuningConfig`) that duplicate functionality and create maintenance overhead.

**Goal**: Consolidate to a single, comprehensive `OLMoSecurityConfig` that handles all configuration needs while preserving the well-designed nested YAML structure.

## Current State Analysis

### Configuration Duplication Problems

#### **OLMoSecurityConfig** (`config_manager.py`)
- **Purpose**: Model paths, basic settings
- **Usage**: 14+ files across codebase
- **YAML Sections**: Root level (`base_models_dir`, `fine_tuned_models_dir`, `default_base_model`)
- **Environment Variables**: Limited (`OLMO_BASE_MODELS_DIR`, `OLMO_FINE_TUNED_MODELS_DIR`, `OLMO_DEFAULT_BASE_MODEL`)
- **Strengths**: Well-established, widely used, good path validation

#### **FineTuningConfig** (`fine_tuning_config.py`)
- **Purpose**: Training parameters, workspace management, HuggingFace settings
- **Usage**: 5 files (training-specific)
- **YAML Sections**: `fine_tuning.*` nested sections
- **Environment Variables**: Comprehensive (all training parameters with `OLMO_*` prefix)
- **Strengths**: Complete environment override support, good training parameter organization

### **Specific Duplication Issues**

1. **Duplicate Path Handling**: Both classes read and parse `base_models_dir` and `fine_tuned_models_dir`
2. **Inconsistent Environment Support**: OLMoSecurityConfig has limited env vars, FineTuningConfig has comprehensive support
3. **Split Validation Logic**: Model validation in OLMoSecurityConfig, training validation in FineTuningConfig
4. **Different Loading Patterns**: Different error handling and initialization approaches
5. **Maintenance Overhead**: Changes to model paths require updating both classes

## Target Architecture

### Enhanced OLMoSecurityConfig Design

```python
class OLMoSecurityConfig:
    """
    Unified configuration manager for AI Security Analysis system.

    Manages all configuration aspects:
    - Model paths and model configuration
    - Fine-tuning parameters and workspace management
    - Knowledge base configuration
    - Environment variable overrides for all settings
    """

    # Direct properties (global settings)
    base_models_dir: Path
    fine_tuned_models_dir: Path
    default_base_model: str

    # Nested configuration sections
    fine_tuning: FineTuningSection
    knowledge_base: KnowledgeBaseSection

    # Environment variable support for ALL settings
    # OLMO_* prefix for all overrideable values
```

### Nested Configuration Sections

```python
@dataclass
class FineTuningSection:
    """Fine-tuning specific configuration"""
    workspace_dir: Path
    default_output_name: str

    # Training parameters
    learning_rate: float
    batch_size: int
    max_epochs: int
    warmup_steps: int
    save_steps: int
    eval_steps: int
    max_stage1_iters: int
    max_stage2_iters: int

    # MLX settings
    quantization: str
    memory_efficient: bool
    gradient_checkpointing: bool

    # HuggingFace settings
    upload_enabled: bool
    repo_prefix: str
    private_repos: bool
    skip_in_daemon: bool

@dataclass
class KnowledgeBaseSection:
    """Knowledge base specific configuration"""
    base_dir: Path
    embeddings_model: str
    vector_store_type: str
```

## Enhanced YAML Structure

### Current Structure (Preserve and Extend)
```yaml
# Global model settings
base_models_dir: "~/shared-olmo-models/base"
fine_tuned_models_dir: "~/shared-olmo-models/fine-tuned"
default_base_model: "OLMo-2-1B-mlx-q4"

# Fine-tuning configuration
fine_tuning:
  workspace_dir: "security-ai-analysis/fine-tuning"
  default_output_name: "webauthn-security-v1"

  # Training parameters (add these)
  training:
    learning_rate: 2e-5
    batch_size: 1
    max_epochs: 3
    warmup_steps: 100
    save_steps: 500
    eval_steps: 250
    max_stage1_iters: 100
    max_stage2_iters: 150

  # MLX optimization settings (add these)
  mlx:
    quantization: "q4"
    memory_efficient: true
    gradient_checkpointing: true

  # HuggingFace upload settings (add these)
  huggingface:
    upload_enabled: true
    default_repo_prefix: "hitoshura25"
    private_repos: false
    skip_in_daemon: false

# Knowledge base configuration (add this)
knowledge_base:
  base_dir: "security-ai-analysis/knowledge_base"
  embeddings_model: "sentence-transformers/all-MiniLM-L6-v2"
  vector_store_type: "faiss"
```

## Environment Variable Consolidation

### Complete OLMO_* Variable Mapping

```bash
# Global model settings
OLMO_BASE_MODELS_DIR               # → base_models_dir
OLMO_FINE_TUNED_MODELS_DIR         # → fine_tuned_models_dir
OLMO_DEFAULT_BASE_MODEL            # → default_base_model

# Fine-tuning workspace
OLMO_WORKSPACE_DIR                 # → fine_tuning.workspace_dir

# Training parameters
OLMO_LEARNING_RATE                 # → fine_tuning.training.learning_rate
OLMO_BATCH_SIZE                    # → fine_tuning.training.batch_size
OLMO_MAX_EPOCHS                    # → fine_tuning.training.max_epochs
OLMO_WARMUP_STEPS                  # → fine_tuning.training.warmup_steps
OLMO_SAVE_STEPS                    # → fine_tuning.training.save_steps
OLMO_EVAL_STEPS                    # → fine_tuning.training.eval_steps
OLMO_MAX_STAGE1_ITERS             # → fine_tuning.training.max_stage1_iters
OLMO_MAX_STAGE2_ITERS             # → fine_tuning.training.max_stage2_iters

# Knowledge base
OLMO_KNOWLEDGE_BASE_DIR           # → knowledge_base.base_dir
```

## Implementation Strategy

### Phase 1: Extend OLMoSecurityConfig (Additive)

**Goal**: Add all FineTuningConfig functionality to OLMoSecurityConfig without breaking existing code

#### **Step 1.1: Update YAML Configuration**
**File**: `config/olmo-security-config.yaml`
- Add missing nested sections (training, mlx, huggingface, knowledge_base)
- Preserve existing structure completely
- Add default values for all new sections

#### **Step 1.2: Extend OLMoSecurityConfig Class**
**File**: `security-ai-analysis/config_manager.py`

**Changes**:
1. **Add dataclass sections**:
   ```python
   @dataclass
   class FineTuningSection:
       # All fine-tuning properties

   @dataclass
   class KnowledgeBaseSection:
       # Knowledge base properties
   ```

2. **Add properties to OLMoSecurityConfig**:
   ```python
   class OLMoSecurityConfig:
       def __init__(self, config_file: Optional[Path] = None):
           # Existing initialization...

           # Add fine-tuning section
           self.fine_tuning = self._load_fine_tuning_section(config)

           # Add knowledge base section
           self.knowledge_base = self._load_knowledge_base_section(config)
   ```

3. **Add comprehensive environment variable support**:
   ```python
   def _load_fine_tuning_section(self, config: Dict) -> FineTuningSection:
       ft_config = config.get('fine_tuning', {})
       train_config = ft_config.get('training', {})

       return FineTuningSection(
           learning_rate=float(os.getenv('OLMO_LEARNING_RATE',
                                       train_config.get('learning_rate', 2e-5))),
           batch_size=int(os.getenv('OLMO_BATCH_SIZE',
                                  train_config.get('batch_size', 1))),
           # ... all other parameters
       )
   ```

4. **Add validation methods**:
   ```python
   def validate_fine_tuning_configuration(self) -> bool:
       # Incorporate validation logic from FineTuningConfig
   ```

#### **Step 1.3: Testing Phase 1**
- Verify OLMoSecurityConfig can load all new sections
- Test environment variable overrides
- Ensure backward compatibility with existing code
- Run test suite to verify no regressions

### Phase 2: Migrate FineTuningConfig Usage

**Goal**: Replace all FineTuningConfig usage with enhanced OLMoSecurityConfig

#### **Files to Update** (5 files using FineTuningConfig):

1. **`process_artifacts.py`**
   ```python
   # OLD
   from fine_tuning_config import FineTuningConfig
   ft_config = FineTuningConfig.load_from_config()

   # NEW
   from config_manager import OLMoSecurityConfig
   config = OLMoSecurityConfig()
   # Access: config.fine_tuning.learning_rate
   ```

2. **`sequential_fine_tuner.py`**
   ```python
   # OLD
   self.ft_config = FineTuningConfig.load_from_config()
   learning_rate = self.ft_config.learning_rate

   # NEW
   self.config = OLMoSecurityConfig()
   learning_rate = self.config.fine_tuning.learning_rate
   ```

3. **`model_uploader.py`**
4. **`sequential_pipeline_integration.py`**
5. **`scripts/mlx_finetuning.py`**

#### **Step 2.1: Property Access Migration**

**Common migration patterns**:
```python
# Training parameters
ft_config.learning_rate      → config.fine_tuning.learning_rate
ft_config.batch_size         → config.fine_tuning.batch_size
ft_config.max_epochs         → config.fine_tuning.max_epochs

# Paths
ft_config.workspace_dir      → config.fine_tuning.workspace_dir
ft_config.base_models_dir    → config.base_models_dir
ft_config.get_base_model_path() → config.get_base_model_path()

# HuggingFace settings
ft_config.upload_enabled     → config.fine_tuning.upload_enabled
ft_config.repo_prefix        → config.fine_tuning.repo_prefix
```

#### **Step 2.2: Method Migration**

**Path methods** (already exist in OLMoSecurityConfig):
```python
# These already exist - no changes needed
config.get_base_model_path()
config.get_fine_tuned_model_path()
```

**New methods to add to OLMoSecurityConfig**:
```python
def get_workspace_path(self) -> Path:
    """Get fine-tuning workspace directory"""
    return self.fine_tuning.workspace_dir

def get_output_model_path(self, custom_name: Optional[str] = None) -> Path:
    """Get path where fine-tuned model will be saved"""
    model_name = custom_name or self.fine_tuning.default_output_name
    return self.fine_tuned_models_dir / model_name

def setup_workspace(self):
    """Create fine-tuning workspace directories"""
    # Move from FineTuningConfig
```

#### **Step 2.3: Testing Phase 2**
- Test each migrated file individually
- Verify property access works correctly
- Test environment variable overrides still work
- Run integration tests to ensure training pipeline works
- Verify knowledge base still uses correct directories

### Phase 3: Clean Up and Remove FineTuningConfig

**Goal**: Remove duplicate code and finalize consolidation

#### **Step 3.1: Remove FineTuningConfig**
**File**: `security-ai-analysis/fine_tuning_config.py`
- **Action**: Delete the entire file

#### **Step 3.2: Update Knowledge Base Integration**
**File**: `security-ai-analysis/local_security_knowledge_base.py`
```python
# OLD
from config_manager import OLMoSecurityConfig  # Already uses this
# Manual environment variable handling

# NEW - Use consolidated config
config = OLMoSecurityConfig()
self.knowledge_base_dir = config.knowledge_base.base_dir
```

#### **Step 3.3: Final Testing**
- Run complete test suite (`./run_tests.sh all`)
- Verify training tests work with consolidated config
- Test all environment variable overrides
- Verify knowledge base isolation in tests

## Migration Checklist

### Pre-Migration Validation
- [ ] Document all current FineTuningConfig usage
- [ ] Identify all environment variables in use
- [ ] Run baseline test suite to ensure current functionality

### Phase 1: Extension
- [ ] Update `olmo-security-config.yaml` with new sections
- [ ] Add dataclass sections to `config_manager.py`
- [ ] Extend OLMoSecurityConfig with fine-tuning properties
- [ ] Add comprehensive environment variable support
- [ ] Add validation methods from FineTuningConfig
- [ ] Test extended config loads correctly
- [ ] Verify backward compatibility

### Phase 2: Migration
- [ ] Update `process_artifacts.py` imports and usage
- [ ] Update `sequential_fine_tuner.py` imports and usage
- [ ] Update `model_uploader.py` imports and usage
- [ ] Update `sequential_pipeline_integration.py` imports and usage
- [ ] Update `scripts/mlx_finetuning.py` imports and usage
- [ ] Test each file individually after migration
- [ ] Run integration tests

### Phase 3: Cleanup
- [ ] Delete `fine_tuning_config.py`
- [ ] Update knowledge base to use consolidated config
- [ ] Remove any remaining FineTuningConfig imports
- [ ] Run complete test suite
- [ ] Update documentation

## Risk Mitigation

### Backward Compatibility
- **All environment variables preserved**: No changes to existing `OLMO_*` variables
- **Same YAML structure**: Additive changes only, no breaking changes
- **Incremental migration**: Each phase can be tested independently
- **Rollback capability**: Changes are additive until Phase 3

### Testing Strategy
- **Phase-by-phase testing**: Validate each phase before proceeding
- **Environment variable testing**: Verify all `OLMO_*` overrides work
- **Integration testing**: Ensure training pipeline works end-to-end
- **Regression testing**: Run existing test suite after each phase

### Performance Considerations
- **Single config load**: Eliminates duplicate YAML parsing
- **Memory efficiency**: Single config object instead of multiple
- **Faster initialization**: Consolidated loading logic

## Expected Benefits

### **✅ Eliminated Confusion**
- Single configuration class for all needs
- Consistent environment variable handling
- Unified validation and error handling

### **✅ Improved Maintainability**
- Changes in one place affect entire system
- No duplicate path handling logic
- Simplified testing with single config fixture

### **✅ Better Organization**
- Logical grouping of related settings
- Clear separation between global and section-specific config
- Preserved nested YAML structure for readability

### **✅ Enhanced Functionality**
- Comprehensive environment variable support for all settings
- Unified validation across all configuration aspects
- Single source of truth for all configuration needs

## Timeline Estimate

- **Phase 1** (Extension): 2-3 hours
- **Phase 2** (Migration): 3-4 hours
- **Phase 3** (Cleanup): 1-2 hours
- **Testing & Validation**: 2-3 hours throughout

**Total**: 8-12 hours for complete consolidation

---

**Status**: Implementation Plan Complete
**Next Step**: Begin Phase 1 implementation when ready to proceed