# AI Security Fine-Tuning Usage Guide

## Overview

This guide documents all integration modes and usage patterns for the AI Security Fine-Tuning system (Phase 5 of the AI Security Dataset Research Initiative). The system provides flexible execution modes for different development and production scenarios.

📖 **Quick Links:**
- [← Back to Main README](../../security-ai-analysis/README.md) - System overview and basic setup
- [🛠️ MLX Installation Guide](mlx-installation-guide.md) - Prerequisites for fine-tuning setup

---

**Target Audience**: Developers and researchers using the AI security analysis pipeline  
**Prerequisites**: MLX installed and configured → **[MLX Installation Guide](mlx-installation-guide.md)**

## Architecture Summary

### 5-Phase Pipeline
1. **Phase 1**: Security Analysis → MLX-optimized OLMo-2-1B vulnerability analysis
2. **Phase 2**: Narrativization → Rich security explanations with remediation
3. **Phase 3**: Dataset Creation → Training/validation JSONL preparation (80/20 split)  
4. **Phase 4**: HuggingFace Upload → Production dataset at `hitoshura25/webauthn-security-vulnerabilities-olmo`
5. **Phase 5**: **MLX Fine-Tuning** → Domain-specialized model creation and sharing

### Default Behavior
- **Fine-tuning enabled by default** in all modes (maximizes research value)
- **Opt-out available** for development/testing scenarios
- **Fail-fast approach** for system errors, graceful handling for legitimate opt-outs

## Integration Modes

### 1. Manual Mode (Development & Testing)

#### 1.1 Standard Execution (Default)
Complete 5-phase pipeline including fine-tuning:

```bash
# Navigate to security analysis directory
cd security-ai-analysis

# Run complete pipeline with fine-tuning (default behavior)
python3 process_artifacts.py

# Complete pipeline with model upload to HuggingFace
python3 process_artifacts.py --upload-model

# With custom model and upload
python3 process_artifacts.py --model-name ~/shared-olmo-models/base/OLMo-2-1B-Instruct --upload-model

# With branch/commit tracking and upload
python3 process_artifacts.py --branch main --commit abc123def --upload-model
```

**Expected Output**:
```
🔒 WebAuthn Security Analysis with OLMo-2-1B-Instruct
=============================================================
Phase 1: OLMo Security Analysis ✅
Phase 2: Creating Rich Security Narratives ✅
Phase 3: Preparing Fine-Tuning Dataset ✅
Phase 4: Uploading to Production HuggingFace Dataset ✅
Phase 5: MLX Fine-Tuning (Default Behavior) ✅
  🎯 Starting MLX fine-tuning with dataset: train_20250912_143022.jsonl
  📊 Training examples: 156
  📁 Output model: webauthn-security-olmo-20250912-143022
  ⚡ Starting MLX fine-tuning process...
  ✅ Fine-tuning completed successfully!
  📁 Model saved to: ~/shared-olmo-models/fine-tuned/webauthn-security-olmo-20250912-143022
  📤 Uploading fine-tuned model to HuggingFace (--upload-model)...
  ✅ Model uploaded: https://huggingface.co/hitoshura25/webauthn-security-model-20250912-143022
```

#### 1.2 Development Mode (Opt-Out)
Skip fine-tuning for faster iteration during development:

```bash
# Skip fine-tuning (development/testing mode)
python3 process_artifacts.py --skip-fine-tuning

# Combine with other options  
python3 process_artifacts.py --skip-fine-tuning --branch develop

# Note: --upload-model has no effect when --skip-fine-tuning is used
```

**When to Use Opt-Out**:
- 🧪 **Development/Testing**: Faster iteration during pipeline development
- 🚨 **Emergency Mode**: If fine-tuning breaks, temporary disable
- 📊 **Dataset-Only Runs**: Rare cases where only training data needed

#### 1.3 Manual Artifact Processing
Process existing artifacts with fine-tuning:

```bash
# Process artifacts from specific directory
python3 process_artifacts.py --artifacts-dir data/custom_security_artifacts

# Process with custom output directory
python3 process_artifacts.py --output-dir results/security_analysis_$(date +%Y%m%d)
```

### 2. Automated Daemon Mode (Production)

#### 2.1 Daemon Configuration
Fine-tuning runs automatically every 5 minutes via LaunchAgent:

```bash
# Check daemon status
python3 setup_launchagent.py --status

# View daemon configuration
cat templates/daemon.plist.template
```

**Daemon Configuration** (`local-analysis/security_artifact_daemon.py`):
- **Polling**: Every 5 minutes via LaunchAgent
- **Auto-Download**: Latest artifacts from main branch GitHub Actions
- **Complete Pipeline**: All 5 phases including fine-tuning
- **Error Handling**: Continues operation on fine-tuning failures

#### 2.2 Emergency Override
Disable fine-tuning in daemon mode (emergency only):

```yaml
# config/olmo-security-config.yaml
fine_tuning:
  skip_in_daemon: true  # Emergency override - disable automated fine-tuning
  # Set back to false when issue resolved
```

**When to Use Emergency Override**:
- 🚨 **Fine-tuning broken**: Temporary disable while fixing issues
- 🔧 **System maintenance**: Prevent fine-tuning during maintenance
- 📊 **Resource constraints**: Temporary resource limitation

**Note**: This is an emergency measure - normal daemon operation includes fine-tuning.

### 3. Standalone Mode (Advanced)

#### 3.1 Direct MLX Fine-Tuning
Advanced users can run fine-tuning directly on existing datasets:

```bash
# Navigate to security analysis directory
cd security-ai-analysis

# Fine-tune with existing dataset
python3 scripts/mlx_finetuning.py --dataset data/train_20250912_143022.jsonl

# With custom output name and upload
python3 scripts/mlx_finetuning.py \
  --dataset data/custom_security_data.jsonl \
  --output-name webauthn-custom-model-$(date +%Y%m%d) \
  --upload

# With custom configuration
python3 scripts/mlx_finetuning.py \
  --dataset data/security_data.jsonl \
  --batch-size 4 \
  --learning-rate 1e-5 \
  --max-epochs 3
```

#### 3.2 Standalone Options
```bash
# Show all available options
python3 scripts/mlx_finetuning.py --help
```

**Key Parameters**:
- `--dataset`: Path to JSONL training dataset (required)
- `--output-name`: Custom fine-tuned model name
- `--upload`: Upload to HuggingFace after fine-tuning
- `--batch-size`: Training batch size (default: 2)
- `--learning-rate`: Learning rate (default: 1e-5)
- `--max-epochs`: Maximum training epochs (default: 3)
- `--base-model`: Base model to fine-tune (default: from config)

## Configuration Management

### Configuration Files

#### Primary Configuration
**File**: `config/olmo-security-config.yaml`

```yaml
fine_tuning:
  # Core settings
  skip_in_daemon: false          # Emergency override only
  base_model_name: "OLMo-2-1B-Instruct"
  workspace_dir: "fine-tuning"
  
  # Training parameters
  batch_size: 2
  learning_rate: 1e-5
  max_epochs: 3
  warmup_steps: 100
  save_steps: 500
  eval_steps: 250
  
  # MLX optimization
  gradient_checkpointing: true
  quantization: "none"          # or "4bit", "8bit"
  
  # Output settings
  output_model_prefix: "webauthn-security-olmo"
  
  # HuggingFace upload
  upload_enabled: true          # Upload fine-tuned models
  hf_repo_prefix: "hitoshura25/webauthn-security-model"
```

#### Environment Variable Overrides
```bash
# Override configuration via environment variables
export FINE_TUNING_BATCH_SIZE=4
export FINE_TUNING_LEARNING_RATE=2e-5
export FINE_TUNING_UPLOAD_ENABLED=true

# HuggingFace token for model upload (required for --upload-model)
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Run with overrides
python3 process_artifacts.py
```

#### HuggingFace Model Upload Setup
```bash
# 1. Get HuggingFace token from https://huggingface.co/settings/tokens
# 2. Set environment variable
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 3. Test token validity
python3 -c "from huggingface_hub import whoami; print(whoami())"

# 4. Run with model upload
python3 process_artifacts.py --upload-model
```

### Workspace Structure
```
fine-tuning/
├── training_data/           # Generated training datasets
│   ├── train_20250912_143022.jsonl
│   ├── validation_20250912_143022.jsonl
│   └── dataset_info_20250912_143022.json
├── checkpoints/            # Training checkpoints
├── logs/                  # Fine-tuning logs
│   └── fine_tuning_20250912_143022.log
└── temp/                 # Temporary files
```

## Monitoring & Validation

### Real-Time Monitoring

#### Check Fine-Tuning Status
```bash
# Get current fine-tuning system status
python3 -c "
from pipeline_integration import get_fine_tuning_status
import json
status = get_fine_tuning_status()
print(json.dumps(status, indent=2))
"
```

#### Monitor Active Fine-Tuning
```bash
# Watch fine-tuning logs in real-time
tail -f fine-tuning/logs/fine_tuning_$(date +%Y%m%d)*.log

# Check GPU/MLX utilization
python3 -c "
import mlx.core as mx
print(f'MLX memory usage: {mx.metal.get_peak_memory() / 1e9:.2f}GB')
"
```

### Validation & Testing

#### Test Integration Health
```bash
# Run comprehensive integration tests
bash scripts/tests/test-fine-tuning-phase3.sh

# Expected: 7/7 tests passing
```

#### Validate Fine-Tuned Models
```bash
# List available fine-tuned models
ls -la ~/shared-olmo-models/fine-tuned/

# Test model loading
python3 -c "
from model_manager import OLMoModelManager
manager = OLMoModelManager()
models = manager.list_fine_tuned_models()
print('Available fine-tuned models:')
for model in models:
    print(f'  - {model}')
"
```

## Output & Results

### Generated Artifacts

#### 1. Training Datasets
- **Location**: `fine-tuning/training_data/`
- **Format**: JSONL with prompt-completion pairs
- **Split**: 80% training, 20% validation
- **Metadata**: Dataset info with statistics

#### 2. Fine-Tuned Models
- **Location**: `~/shared-olmo-models/fine-tuned/`
- **Format**: MLX-optimized model files
- **Components**: weights.safetensors, tokenizer, config
- **Naming**: `webauthn-security-olmo-YYYYMMDD-HHMMSS`

#### 3. HuggingFace Uploads
- **Dataset**: `hitoshura25/webauthn-security-vulnerabilities-olmo` (training data, Phase 4)
- **Models**: `hitoshura25/webauthn-security-model-YYYYMMDD-HHMMSS` (fine-tuned models, Phase 5)
- **Upload Triggers**: 
  - `--upload-model` CLI flag (overrides config)
  - `upload_enabled: true` in configuration
  - Requires `HF_TOKEN` environment variable
- **Visibility**: Public (research contribution)

### Performance Metrics

#### Typical Performance (Apple Silicon M1/M2/M3)
- **Fine-Tuning Speed**: 20-30X faster than CPU
- **Memory Usage**: 2-4GB for OLMo-2-1B
- **Fine-Tuning Duration**: 5-15 minutes (100-500 examples)
- **Model Size**: ~1.2GB fine-tuned model

#### Quality Metrics
- **Training Loss**: Monitored during fine-tuning
- **Validation Accuracy**: Computed on validation set
- **Domain Adaptation**: Improved WebAuthn security analysis

## Error Handling & Troubleshooting

### Error Categories

#### 1. Legitimate Opt-Outs (Graceful Handling)
- ✅ **CLI Flag**: `--skip-fine-tuning` (development mode)
- ✅ **Config Override**: `skip_in_daemon: true` (emergency)
- ✅ **MLX Unavailable**: Platform limitation (handled gracefully)
- ✅ **Missing Data**: No training data available

#### 2. Critical Failures (Fail-Fast)
- ❌ **System Errors**: Disk space, permissions, memory issues
- ❌ **Configuration Corruption**: Invalid YAML, missing required settings  
- ❌ **Model Corruption**: Base model files damaged
- ❌ **Runtime Errors**: Unexpected MLX failures

### Common Issues & Solutions

#### Issue: "MLX not available" 
```bash
# Solution: Install MLX (see MLX Installation Guide)
pip install mlx mlx-lm
```

#### Issue: Fine-tuning fails with memory error
```bash
# Solution: Reduce batch size in config
# config/olmo-security-config.yaml:
fine_tuning:
  batch_size: 1  # Reduce from default 2
```

#### Issue: Model upload fails
```bash
# Solution: Check HuggingFace token
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# Or disable upload:
export FINE_TUNING_UPLOAD_ENABLED=false
```

#### Issue: Training dataset empty
```bash
# Solution: Check security analysis phase
# Ensure vulnerabilities were found and analyzed in Phase 1-2
python3 process_artifacts.py --artifacts-dir data/security_artifacts
```

### Debug Commands

#### Comprehensive System Check
```bash
# Run full system diagnostics
python3 -c "
from pipeline_integration import get_fine_tuning_status
from fine_tuning_config import FineTuningConfig
import json

print('=== Fine-Tuning System Diagnostics ===')
status = get_fine_tuning_status()
print(f'Status: {json.dumps(status, indent=2)}')

try:
    config = FineTuningConfig.load_from_config()
    print(f'Config loaded: ✅')
    print(f'Base model: {config.base_model_name}')
    print(f'Workspace: {config.workspace_dir}')
except Exception as e:
    print(f'Config error: ❌ {e}')
"
```

## Best Practices

### Development Workflow
1. **Use opt-out during development**: `--skip-fine-tuning` for faster iteration
2. **Test with small datasets**: Validate pipeline before large runs  
3. **Monitor resource usage**: Check memory/disk space during fine-tuning
4. **Validate models**: Test fine-tuned models before deployment

### Production Deployment
1. **Enable daemon mode**: Automated fine-tuning on production security data
2. **Monitor logs**: Regular log review for fine-tuning health
3. **Resource planning**: Ensure adequate disk space for models
4. **Backup models**: Fine-tuned models are valuable research assets

### Security Considerations
1. **Data Privacy**: Fine-tuned models may contain security data patterns
2. **Model Access**: Restrict access to fine-tuned model directory
3. **Upload Review**: Review model cards before public HuggingFace upload
4. **Local Processing**: All fine-tuning happens locally (no external API calls)

---

**Last Updated**: 2025-09-14  
**Version**: 1.0  
**Related Documents**: 
- `docs/development/mlx-installation-guide.md`
- `docs/improvements/planned/ai-security-fine-tuning-implementation.md`
- `docs/improvements/in-progress/ai-security-fine-tuning-implementation-progress.md`