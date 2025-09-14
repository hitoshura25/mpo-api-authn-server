# MLX Installation Guide for AI Security Fine-Tuning

## Overview

This guide provides comprehensive instructions for installing and configuring MLX (Machine Learning for Apple Silicon) to enable Phase 5 fine-tuning in the AI Security Dataset Research Initiative.

📖 **Quick Links:**
- [← Back to Main README](../../security-ai-analysis/README.md) - System overview and basic setup  
- [📚 Fine-Tuning Usage Guide](ai-security-fine-tuning-usage.md) - How to use MLX fine-tuning after installation

---

**Target Audience**: Developers setting up the AI security analysis pipeline with fine-tuning capabilities  
**Requirements**: Apple Silicon Mac (M1, M2, M3, or newer)  
**Estimated Setup Time**: 15-30 minutes

## Prerequisites

### ✅ Hardware Requirements
- **Apple Silicon Mac**: M1, M2, M3, or newer chip required
- **Memory**: Minimum 16GB RAM recommended (32GB+ for larger models)
- **Storage**: At least 10GB free space for models and fine-tuning workspace

### ✅ Software Requirements
- **macOS**: 12.0 (Monterey) or newer
- **Python**: 3.9+ (Python 3.11+ recommended)
- **Xcode Command Line Tools**: Required for compilation

### ✅ Verify Apple Silicon
```bash
# Verify you're running on Apple Silicon
uname -m
# Should output: arm64

# Check macOS version
sw_vers
# ProductVersion should be 12.0 or higher
```

## Installation Steps

### Step 1: Install Xcode Command Line Tools
```bash
# Install Xcode Command Line Tools (required for MLX compilation)
xcode-select --install

# Verify installation
xcode-select -p
# Should output: /Applications/Xcode.app/Contents/Developer or /Library/Developer/CommandLineTools
```

### Step 2: Set Up Python Environment
```bash
# Navigate to the security analysis directory
cd /path/to/mpo-api-authn-server/security-ai-analysis

# Activate the existing virtual environment
source venv/bin/activate

# Verify Python version
python3 --version
# Should be 3.9 or higher
```

### Step 3: Install MLX Framework
```bash
# Install MLX core framework
pip install mlx

# Install MLX Language Models package
pip install mlx-lm

# Verify MLX installation
python3 -c "import mlx.core as mx; print(f'MLX version: {mx.__version__}')"
```

### Step 4: Install Additional Dependencies
```bash
# Install fine-tuning specific dependencies
pip install transformers>=4.30.0
pip install datasets>=2.14.0
pip install accelerate>=0.21.0
pip install safetensors>=0.3.0
pip install sentencepiece>=0.1.99

# Install HuggingFace Hub for model upload
pip install huggingface_hub>=0.16.0

# Save updated requirements
pip freeze > requirements.txt
```

### Step 5: Verify MLX Installation
```bash
# Test MLX functionality
python3 -c "
import mlx.core as mx
import mlx.nn as nn
print('✅ MLX Core imported successfully')
print(f'MLX version: {mx.__version__}')

# Test basic MLX operations
x = mx.array([1.0, 2.0, 3.0])
y = mx.sum(x)
print(f'✅ MLX operations working: sum([1,2,3]) = {y}')

# Test MLX-LM
try:
    import mlx_lm
    print('✅ MLX-LM imported successfully')
except ImportError as e:
    print(f'❌ MLX-LM import failed: {e}')
"
```

## Configuration Setup

### Step 1: Validate Fine-Tuning Configuration
```bash
# Navigate to security analysis directory
cd security-ai-analysis

# Test fine-tuning configuration
python3 -c "
from fine_tuning_config import FineTuningConfig
config = FineTuningConfig.load_from_config()
print(f'✅ Fine-tuning config loaded successfully')
print(f'Base model: {config.base_model_name}')
print(f'Workspace: {config.workspace_dir}')
"
```

### Step 2: Test MLX Fine-Tuning Integration
```bash
# Test the MLX fine-tuning engine
python3 -c "
from scripts.mlx_finetuning import MLXFineTuner
from fine_tuning_config import FineTuningConfig

try:
    config = FineTuningConfig.load_from_config()
    fine_tuner = MLXFineTuner(config)
    print('✅ MLXFineTuner initialized successfully')
except Exception as e:
    print(f'❌ MLXFineTuner initialization failed: {e}')
"
```

### Step 3: Validate Pipeline Integration
```bash
# Test pipeline integration
python3 -c "
from pipeline_integration import is_fine_tuning_available, get_fine_tuning_status

available = is_fine_tuning_available()
status = get_fine_tuning_status()

print(f'Fine-tuning available: {available}')
print(f'Status: {status}')

if available:
    print('✅ MLX fine-tuning is ready for use')
else:
    print(f'❌ Issue detected: {status.get(\"error\", \"Unknown\")}')
"
```

## Model Setup

### Step 1: Verify Base Model Availability
```bash
# Check if OLMo-2-1B-Instruct model is available
ls -la ~/shared-olmo-models/base/OLMo-2-1B-*

# If models are missing, they will be downloaded automatically on first use
# Or manually download with:
# python3 -c "from model_manager import OLMoModelManager; OLMoModelManager().ensure_model_available('OLMo-2-1B-Instruct')"
```

### Step 2: Set Up Fine-Tuning Workspace
```bash
# Create fine-tuning workspace directories
python3 -c "
from fine_tuning_config import FineTuningConfig
config = FineTuningConfig.load_from_config()
config.setup_workspace()
print('✅ Fine-tuning workspace created')
print(f'Workspace location: {config.workspace_dir}')
"
```

## Testing Installation

### Quick Test: Run Phase 3 Integration Tests
```bash
# Run the comprehensive integration tests
bash scripts/tests/test-fine-tuning-phase3.sh
```

**Expected Output**: All 7/7 tests should pass:
- ✅ Pipeline integration module working
- ✅ Process artifacts integration successful  
- ✅ Mock integration test passed
- ✅ Configuration consistency validated
- ✅ Daemon integration ready
- ✅ Error handling robust
- ✅ Fail-fast behavior validated

### Advanced Test: Mock Fine-Tuning Run
```bash
# Test with sample data (without actual fine-tuning)
python3 -c "
from pathlib import Path
from pipeline_integration import integrate_fine_tuning_if_available
import json

# Create test data
workspace = Path('fine-tuning')
workspace.mkdir(exist_ok=True)

test_file = workspace / 'test_data.jsonl'
test_data = [
    {'prompt': 'Test security vulnerability', 'completion': 'Test analysis'},
    {'prompt': 'Another test case', 'completion': 'Another analysis'}
]

with open(test_file, 'w') as f:
    for item in test_data:
        f.write(json.dumps(item) + '\n')

# Test integration (will skip fine-tuning if MLX issues detected)
summary = {}
result = integrate_fine_tuning_if_available(test_file, test_data, summary)

print(f'Integration test result: {result.get(\"fine_tuning\", {})}')
test_file.unlink()  # Clean up
"
```

## Troubleshooting

### Common Issues

#### Issue: "MLX not available" Error
```bash
# Verify Apple Silicon
uname -m  # Should be arm64

# Reinstall MLX
pip uninstall mlx mlx-lm
pip install mlx mlx-lm

# Check for conflicting installations
pip list | grep mlx
```

#### Issue: Import Errors
```bash
# Check Python path
python3 -c "import sys; print('\n'.join(sys.path))"

# Verify virtual environment
which python3
# Should point to venv/bin/python3

# Reinstall in clean environment
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Issue: Memory Errors During Fine-Tuning
```bash
# Check available memory
memory_pressure

# Reduce batch size in config/olmo-security-config.yaml:
# fine_tuning:
#   batch_size: 1  # Reduce from default
```

#### Issue: Model Download Failures
```bash
# Check internet connectivity
curl -I https://huggingface.co

# Clear HuggingFace cache
rm -rf ~/.cache/huggingface

# Test HuggingFace token (if using private models)
python3 -c "from huggingface_hub import whoami; print(whoami())"
```

### Getting Help

1. **Check Logs**: Fine-tuning logs are saved in `fine-tuning/logs/`
2. **Run Diagnostics**: Use `python3 -c "from pipeline_integration import get_fine_tuning_status; print(get_fine_tuning_status())"`
3. **MLX Documentation**: https://ml-explore.github.io/mlx/build/html/index.html
4. **Project Issues**: Create issue in project repository with error output

## Performance Expectations

### Typical Performance (Apple Silicon)
- **Model Loading**: 2-5 seconds for OLMo-2-1B-Instruct
- **Fine-Tuning Speed**: 20-30X faster than CPU
- **Memory Usage**: 2-4GB for OLMo-2-1B-Instruct fine-tuning
- **Fine-Tuning Duration**: 5-15 minutes for typical security datasets (100-500 examples)

### Optimization Tips
1. **Use larger batch sizes** if you have sufficient memory (16GB+)
2. **Enable gradient checkpointing** for memory efficiency
3. **Use mixed precision** (enabled by default in MLX)
4. **Close other applications** during fine-tuning for optimal performance

## Next Steps

After successful MLX installation:

1. **Run Full Pipeline**: `python3 process_artifacts.py` (includes fine-tuning by default)
2. **Test Daemon Mode**: Set up automated security scanning with fine-tuning
3. **Explore Standalone Mode**: `python3 scripts/mlx_finetuning.py --help`
4. **Monitor Results**: Check `fine-tuning/logs/` and `~/shared-olmo-models/fine-tuned/`

**Complete Usage Guide:**
For comprehensive fine-tuning usage patterns after installation, see the [Fine-Tuning Usage Guide](ai-security-fine-tuning-usage.md).

## Security Considerations

- **Model Storage**: Fine-tuned models contain patterns from security data - store securely
- **HuggingFace Upload**: Review model cards before public upload
- **Local Processing**: All fine-tuning runs locally - no data sent to external services
- **Access Controls**: Restrict access to `~/shared-olmo-models/` directory appropriately

---

**Last Updated**: 2025-09-14  
**Version**: 1.0  
**Tested On**: macOS 14.0+, Apple Silicon M1/M2/M3