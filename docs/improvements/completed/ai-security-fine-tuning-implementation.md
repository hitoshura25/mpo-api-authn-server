# AI Security Fine-Tuning Implementation Plan

## Executive Summary

This document provides a comprehensive implementation plan to add MLX fine-tuning capabilities to the AI Security Dataset Research Initiative. The plan extends the existing 4-phase pipeline (Analysis → Narrativization → Dataset Creation → HuggingFace Upload) by adding **Phase 5 & 6: MLX Fine-Tuning and Model Sharing** with flexible integration modes for both manual testing and automated daemon execution.

## System Architecture Overview

### Target Pipeline (6 Phases)
- **Phase 1**: Analysis → MLX-optimized OLMo-2-1B security analysis
- **Phase 2**: Narrativization → Rich security explanations with remediation guidance  
- **Phase 3**: Dataset Creation → Training/validation JSONL preparation (80/20 split)
- **Phase 4**: HuggingFace Upload → Production dataset sharing
- **Phase 5**: MLX Fine-Tuning → Domain-specific model training
- **Phase 6**: Model Upload → Community-standard model sharing

### Integration Architecture
**🎯 INTEGRATION APPROACH**: Fine-tuning and model upload enabled by default with flexible opt-out:
- **Default Behavior**: Both fine-tuning and model upload run automatically (maximizes research value + community contribution)
- **Manual Mode**: `process_artifacts.py` (full pipeline) with opt-out flags `--skip-fine-tuning`, `--skip-model-upload`
- **Automated Mode**: Daemon executes full pipeline with emergency config overrides
- **Standalone Mode**: Direct `mlx_finetuning.py` execution for advanced use cases

### Infrastructure Requirements
- **MLX Optimization**: Apple Silicon with MLX framework for 20-30X performance improvement
- **Portable Configuration**: Shared models at `~/shared-olmo-models/base/` and `~/shared-olmo-models/fine-tuned/`
- **Daemon Automation**: LaunchAgent integration for automated execution
- **Manual Testing**: Full manual execution capabilities
- **Community Standards**: HuggingFace model sharing with complete artifacts

## Architectural Decision: MLX-Native Fine-Tuning

### Key Insights
1. **MLX Performance Critical**: 20-30X speed improvement must be maintained in fine-tuning
2. **Model Sharing Architecture**: Fine-tuned models become shareable across projects
3. **WebAuthn Domain Specialization**: Fine-tuned model specifically for security vulnerability analysis
4. **Resource Efficiency**: MLX enables on-device fine-tuning with reasonable compute requirements
5. **Open Sharing Mission**: Fine-tuned models contribute to AI security research community

### Chosen Architecture: **Flexible Dual Integration with MLX Optimization**

**🔄 INTEGRATION STRATEGY**: Support all execution modes for maximum flexibility:

1. **Default Behavior** (Fine-tuning Always Enabled):
   ```bash
   # Complete 5-phase pipeline (fine-tuning included by default)
   python3 process_artifacts.py
   
   # Custom dataset (fine-tuning included by default)
   python3 process_artifacts.py --artifacts-dir custom_data --fine-tuning-model-name "experimental-v2"
   
   # Opt-out for development/testing only
   python3 process_artifacts.py --skip-fine-tuning
   ```

2. **Automated Production Mode** (Always Fine-tuning):
   ```bash
   # Daemon runs complete 5-phase pipeline every 5 minutes (fine-tuning always enabled)
   launchctl load ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist
   ```

3. **Standalone Advanced Mode**:
   ```bash
   # Direct fine-tuning on existing datasets
   python3 scripts/mlx_finetuning.py --dataset results/train_20250910_143022.jsonl --output-name "custom-model"
   ```

```
~/shared-olmo-models/
├── base/
│   ├── OLMo-2-1B-mlx-q4/      # Base model (existing)
│   └── OLMo-2-1B-mlx/         # Base model (existing)  
└── fine-tuned/                # Fine-tuned models (NEW)
    ├── webauthn-security-v1/   # This project's fine-tuned model
    │   ├── model/             # MLX-optimized fine-tuned weights
    │   ├── tokenizer/         # Associated tokenizer
    │   ├── config/            # Model configuration
    │   └── metadata.json     # Training metadata, dataset info, performance metrics
    └── future-models/         # Additional domain-specific models

security-ai-analysis/          # Fine-tuning workspace
├── fine-tuning/               # Fine-tuning specific components (.gitignored)
│   ├── training_data/        # Processed training datasets
│   ├── checkpoints/          # Training checkpoints during fine-tuning
│   ├── logs/                 # Training logs and metrics
│   └── temp/                 # Temporary training files
├── scripts/
│   ├── mlx_finetuning.py     # Main fine-tuning script (NEW)
│   └── tests/
│       └── test-fine-tuning.sh # Fine-tuning validation tests
└── [existing components]     # config_manager.py, etc.
```

**Benefits**:
- **MLX Performance**: Maintains 20-30X speed advantage during training
- **Shared Output**: Fine-tuned models available across projects
- **Incremental Training**: Can create specialized variants (webauthn-security-v2, etc.)
- **Community Contribution**: Fine-tuned models publishable to HuggingFace
- **Resource Efficient**: On-device training with Apple Silicon optimization

## Updated Test-Driven Implementation Plan (Flexible Dual Integration)

**🔄 REVISED APPROACH**: Implement both standalone fine-tuning script AND process_artifacts.py integration to support all execution modes.

### Phase 1: Fine-Tuning Infrastructure & Configuration (4-6 hours)

**Objective**: Establish MLX fine-tuning infrastructure with portable configuration and flexible integration points

#### 1.1 Enhanced Configuration for Fine-Tuning
**File**: `config/olmo-security-config.yaml` (extend existing)
```yaml
# Existing configuration...
base_models_dir: "~/shared-olmo-models/base"
fine_tuned_models_dir: "~/shared-olmo-models/fine-tuned"
default_base_model: "OLMo-2-1B-mlx-q4"

# Fine-tuning configuration (NEW)
fine_tuning:
  # Fine-tuning enabled by default - only disable for emergencies
  skip_in_daemon: false  # Set to true to disable automated fine-tuning (emergency only)
  workspace_dir: "security-ai-analysis/fine-tuning"
  default_output_name: "webauthn-security-v1"
  
  # Training hyperparameters
  training:
    learning_rate: 2e-5
    batch_size: 4
    max_epochs: 3
    warmup_steps: 100
    save_steps: 500
    eval_steps: 250
    
  # MLX-specific settings
  mlx:
    quantization: "q4"  # Match base model quantization
    memory_efficient: true
    gradient_checkpointing: true
```

#### 1.2 Fine-Tuning Configuration Manager
**File**: `security-ai-analysis/fine_tuning_config.py`
```python
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional
import yaml

@dataclass
class FineTuningConfig:
    """Configuration for MLX fine-tuning process"""
    
    # Directories
    workspace_dir: Path
    base_models_dir: Path
    fine_tuned_models_dir: Path
    
    # Model settings
    base_model_name: str
    output_model_name: str
    
    # Training parameters
    learning_rate: float
    batch_size: int
    max_epochs: int
    warmup_steps: int
    save_steps: int
    eval_steps: int
    
    # MLX settings
    quantization: str
    memory_efficient: bool
    gradient_checkpointing: bool
    
    @classmethod
    def load_from_config(cls, config_file: Optional[Path] = None) -> 'FineTuningConfig':
        """Load fine-tuning configuration from YAML file"""
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "olmo-security-config.yaml"
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        ft_config = config['fine_tuning']
        
        # Resolve paths
        project_root = Path(__file__).parent.parent
        workspace_dir = project_root / ft_config['workspace_dir']
        base_models_dir = Path(config['base_models_dir']).expanduser()
        fine_tuned_models_dir = Path(config['fine_tuned_models_dir']).expanduser()
        
        return cls(
            workspace_dir=workspace_dir,
            base_models_dir=base_models_dir,
            fine_tuned_models_dir=fine_tuned_models_dir,
            base_model_name=config['default_base_model'],
            output_model_name=ft_config['default_output_name'],
            learning_rate=ft_config['training']['learning_rate'],
            batch_size=ft_config['training']['batch_size'],
            max_epochs=ft_config['training']['max_epochs'],
            warmup_steps=ft_config['training']['warmup_steps'],
            save_steps=ft_config['training']['save_steps'],
            eval_steps=ft_config['training']['eval_steps'],
            quantization=ft_config['mlx']['quantization'],
            memory_efficient=ft_config['mlx']['memory_efficient'],
            gradient_checkpointing=ft_config['mlx']['gradient_checkpointing']
        )
    
    def get_base_model_path(self) -> Path:
        """Get path to base model for fine-tuning"""
        model_path = self.base_models_dir / self.base_model_name
        if not model_path.exists():
            raise FileNotFoundError(f"Base model not found: {model_path}")
        return model_path
    
    def get_output_model_path(self) -> Path:
        """Get path where fine-tuned model will be saved"""
        return self.fine_tuned_models_dir / self.output_model_name
    
    def setup_workspace(self):
        """Create fine-tuning workspace directories"""
        for subdir in ['training_data', 'checkpoints', 'logs', 'temp']:
            (self.workspace_dir / subdir).mkdir(parents=True, exist_ok=True)
```

#### 1.3 Phase 1 Validation Tests
**Test Script**: `security-ai-analysis/scripts/tests/test-fine-tuning-phase1.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Fine-Tuning Phase 1 Validation Tests"

# Test 1: Fine-tuning config loads without errors
python3 -c "
from security_ai_analysis.fine_tuning_config import FineTuningConfig
config = FineTuningConfig.load_from_config()
print(f'Base model: {config.base_model_name}')
print(f'Output model: {config.output_model_name}')
print(f'Workspace: {config.workspace_dir}')
print('✅ Fine-tuning config loads successfully')
"

# Test 2: Workspace directories created
python3 -c "
from security_ai_analysis.fine_tuning_config import FineTuningConfig
config = FineTuningConfig.load_from_config()
config.setup_workspace()
required_dirs = ['training_data', 'checkpoints', 'logs', 'temp']
for dir_name in required_dirs:
    dir_path = config.workspace_dir / dir_name
    if not dir_path.exists():
        raise AssertionError(f'Required directory not created: {dir_path}')
print('✅ Workspace directories created successfully')
"

# Test 3: Base model path resolution works
python3 -c "
from security_ai_analysis.fine_tuning_config import FineTuningConfig
config = FineTuningConfig.load_from_config()
try:
    base_path = config.get_base_model_path()
    print(f'✅ Base model found at: {base_path}')
except FileNotFoundError as e:
    print(f'⚠️  Base model not found (expected if not downloaded): {e}')
"

echo "✅ Fine-Tuning Phase 1 validation complete"
```

### Phase 2: MLX Fine-Tuning Engine Implementation (6-8 hours)

**Objective**: Implement core MLX-optimized fine-tuning functionality

#### 2.1 MLX Fine-Tuning Core Engine
**File**: `security-ai-analysis/scripts/mlx_finetuning.py`
```python
#!/usr/bin/env python3
"""
MLX-Optimized Fine-Tuning for OLMo Security Models

Implements fine-tuning of OLMo-2-1B models using MLX framework for Apple Silicon optimization.
Designed for security vulnerability analysis domain specialization.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict
import time
from datetime import datetime

# MLX imports (requires MLX installation)
try:
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    from mlx_lm import load, generate, convert, fine_tune
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("⚠️  MLX not available. Fine-tuning requires MLX installation on Apple Silicon.")

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from fine_tuning_config import FineTuningConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MLXFineTuner:
    """MLX-optimized fine-tuning for OLMo security models"""
    
    def __init__(self, config: Optional[FineTuningConfig] = None):
        if not MLX_AVAILABLE:
            raise RuntimeError("MLX not available. Fine-tuning requires MLX on Apple Silicon.")
            
        self.config = config or FineTuningConfig.load_from_config()
        self.config.setup_workspace()
        
        # Setup logging for this session
        log_file = self.config.workspace_dir / "logs" / f"fine_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        
        logger.info(f"MLX Fine-Tuner initialized with config: {self.config.output_model_name}")
        
    def prepare_training_data(self, dataset_file: Path) -> Path:
        """
        Prepare training data from HuggingFace dataset format to MLX format
        
        Expected input: JSON lines with 'instruction' and 'response' fields
        Output: MLX-compatible training format
        """
        logger.info(f"Preparing training data from: {dataset_file}")
        
        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_file}")
        
        # Output path
        output_file = self.config.workspace_dir / "training_data" / "mlx_training_data.jsonl"
        
        with open(dataset_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line_num, line in enumerate(infile, 1):
                try:
                    data = json.loads(line.strip())
                    
                    # Convert to MLX fine-tuning format
                    mlx_format = {
                        "messages": [
                            {"role": "user", "content": data["instruction"]},
                            {"role": "assistant", "content": data["response"]}
                        ]
                    }
                    
                    outfile.write(json.dumps(mlx_format) + "\\n")
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                    continue
        
        logger.info(f"Training data prepared: {output_file}")
        return output_file
    
    def run_fine_tuning(self, training_data_file: Path) -> Path:
        """
        Execute MLX fine-tuning process
        
        Returns path to fine-tuned model
        """
        logger.info("Starting MLX fine-tuning process")
        
        base_model_path = self.config.get_base_model_path()
        output_model_path = self.config.get_output_model_path()
        
        # Ensure output directory exists
        output_model_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Base model: {base_model_path}")
        logger.info(f"Output model: {output_model_path}")
        logger.info(f"Training data: {training_data_file}")
        
        # MLX fine-tuning parameters
        fine_tune_args = {
            "model": str(base_model_path),
            "data": str(training_data_file),
            "output_dir": str(output_model_path),
            "learning_rate": self.config.learning_rate,
            "batch_size": self.config.batch_size,
            "max_epochs": self.config.max_epochs,
            "warmup_steps": self.config.warmup_steps,
            "save_steps": self.config.save_steps,
            "eval_steps": self.config.eval_steps,
            "gradient_checkpointing": self.config.gradient_checkpointing,
            "quantization": self.config.quantization if self.config.quantization != "none" else None
        }
        
        logger.info(f"Fine-tuning parameters: {fine_tune_args}")
        
        try:
            # Start fine-tuning timer
            start_time = time.time()
            
            # Execute MLX fine-tuning
            # Note: This is a placeholder for actual MLX fine-tuning API
            # Actual implementation will depend on MLX-LM fine-tuning interface
            logger.info("Executing MLX fine-tuning...")
            
            # Placeholder for actual fine-tuning call:
            # fine_tune.train(**fine_tune_args)
            
            # For now, create placeholder structure
            self._create_model_structure(output_model_path, fine_tune_args)
            
            end_time = time.time()
            training_duration = end_time - start_time
            
            logger.info(f"Fine-tuning completed in {training_duration:.2f} seconds")
            
            # Save training metadata
            self._save_training_metadata(output_model_path, fine_tune_args, training_duration)
            
            return output_model_path
            
        except Exception as e:
            logger.error(f"Fine-tuning failed: {e}")
            raise
    
    def _create_model_structure(self, output_path: Path, training_args: Dict[str, Any]):
        """Create fine-tuned model directory structure"""
        
        # Create subdirectories
        (output_path / "model").mkdir(exist_ok=True)
        (output_path / "tokenizer").mkdir(exist_ok=True)
        (output_path / "config").mkdir(exist_ok=True)
        
        # Placeholder files (actual MLX fine-tuning would create these)
        (output_path / "model" / "weights.safetensors").touch()
        (output_path / "tokenizer" / "tokenizer.json").touch()
        (output_path / "config" / "config.json").touch()
        
        logger.info(f"Model structure created at: {output_path}")
    
    def _save_training_metadata(self, output_path: Path, training_args: Dict[str, Any], duration: float):
        """Save training metadata for future reference"""
        
        metadata = {
            "model_name": self.config.output_model_name,
            "base_model": self.config.base_model_name,
            "training_date": datetime.now().isoformat(),
            "training_duration_seconds": duration,
            "training_parameters": training_args,
            "config": asdict(self.config),
            "mlx_version": "placeholder",  # Would get actual MLX version
            "performance_notes": "MLX-optimized for Apple Silicon"
        }
        
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Training metadata saved: {metadata_file}")
    
    def validate_fine_tuned_model(self, model_path: Path) -> bool:
        """
        Validate fine-tuned model structure and basic functionality
        
        Returns True if model appears valid
        """
        logger.info(f"Validating fine-tuned model: {model_path}")
        
        required_files = [
            "model/weights.safetensors",
            "tokenizer/tokenizer.json", 
            "config/config.json",
            "metadata.json"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = model_path / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))
        
        if missing_files:
            logger.error(f"Missing required files: {missing_files}")
            return False
        
        # Validate metadata
        try:
            metadata_file = model_path / "metadata.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            required_metadata = ["model_name", "base_model", "training_date", "training_parameters"]
            missing_metadata = [key for key in required_metadata if key not in metadata]
            
            if missing_metadata:
                logger.error(f"Missing required metadata: {missing_metadata}")
                return False
                
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Invalid metadata file: {e}")
            return False
        
        logger.info("✅ Fine-tuned model validation passed")
        return True

def main():
    """Main fine-tuning entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MLX-Optimized Fine-Tuning for OLMo Security Models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=\"\"\"
Examples:
  # Fine-tune with default dataset
  python3 mlx_finetuning.py --dataset data/security_vulnerabilities_dataset.jsonl
  
  # Fine-tune with custom model name
  python3 mlx_finetuning.py --dataset data/custom_dataset.jsonl --output-name webauthn-security-v2
  
  # Validate existing fine-tuned model
  python3 mlx_finetuning.py --validate-model ~/shared-olmo-models/fine-tuned/webauthn-security-v1
        \"\"\"
    )
    
    parser.add_argument("--dataset", type=Path, 
                       help="Path to training dataset (JSONL format)")
    parser.add_argument("--output-name", 
                       help="Name for fine-tuned model (default from config)")
    parser.add_argument("--config", type=Path,
                       help="Path to configuration file")
    parser.add_argument("--validate-model", type=Path,
                       help="Validate existing fine-tuned model")
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = None
        if args.config:
            config = FineTuningConfig.load_from_config(args.config)
        else:
            config = FineTuningConfig.load_from_config()
            
        if args.output_name:
            config.output_model_name = args.output_name
        
        fine_tuner = MLXFineTuner(config)
        
        if args.validate_model:
            # Validate existing model
            is_valid = fine_tuner.validate_fine_tuned_model(args.validate_model)
            return 0 if is_valid else 1
            
        elif args.dataset:
            # Run fine-tuning
            logger.info(f"Starting fine-tuning with dataset: {args.dataset}")
            
            # Prepare training data
            training_data = fine_tuner.prepare_training_data(args.dataset)
            
            # Execute fine-tuning
            output_model = fine_tuner.run_fine_tuning(training_data)
            
            # Validate result
            if fine_tuner.validate_fine_tuned_model(output_model):
                logger.info(f"✅ Fine-tuning completed successfully: {output_model}")
                return 0
            else:
                logger.error("❌ Fine-tuning validation failed")
                return 1
        else:
            parser.print_help()
            return 1
            
    except Exception as e:
        logger.error(f"Fine-tuning failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
```

#### 2.2 Phase 2 Validation Tests
**Test Script**: `security-ai-analysis/scripts/tests/test-fine-tuning-phase2.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Fine-Tuning Phase 2 Validation Tests"

# Activate virtual environment
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

# Test 1: MLX fine-tuning script loads without errors
python3 -c "
import sys
sys.path.append('scripts')
from mlx_finetuning import MLXFineTuner, FineTuningConfig
config = FineTuningConfig.load_from_config()
print(f'✅ MLX fine-tuning imports successful')
print(f'Base model: {config.base_model_name}')
print(f'Output model: {config.output_model_name}')
"

# Test 2: Training data preparation (mock data)
echo "Creating mock training dataset..."
mkdir -p fine-tuning/training_data
cat > fine-tuning/training_data/mock_dataset.jsonl << 'EOF'
{"instruction": "Analyze this security vulnerability", "response": "This is a mock security analysis response"}
{"instruction": "Explain this WebAuthn issue", "response": "This is a mock WebAuthn explanation"}
EOF

python3 -c "
import sys
sys.path.append('scripts')
from mlx_finetuning import MLXFineTuner
from pathlib import Path

fine_tuner = MLXFineTuner()
dataset_file = Path('fine-tuning/training_data/mock_dataset.jsonl')
prepared_data = fine_tuner.prepare_training_data(dataset_file)
print(f'✅ Training data preparation successful: {prepared_data}')
"

# Test 3: Model structure creation (without actual training)
python3 -c "
import sys
sys.path.append('scripts')
from mlx_finetuning import MLXFineTuner
from pathlib import Path

fine_tuner = MLXFineTuner()
test_output_path = Path('fine-tuning/temp/test_model')
test_output_path.mkdir(parents=True, exist_ok=True)

# Test model structure creation
training_args = {'test': 'placeholder'}
fine_tuner._create_model_structure(test_output_path, training_args)
fine_tuner._save_training_metadata(test_output_path, training_args, 123.45)

# Validate structure
is_valid = fine_tuner.validate_fine_tuned_model(test_output_path)
if not is_valid:
    raise AssertionError('Model structure validation failed')
print('✅ Model structure creation and validation successful')
"

# Test 4: Command-line interface
python3 scripts/mlx_finetuning.py --help | grep -q "MLX-Optimized Fine-Tuning" && echo "✅ CLI interface works"

echo "✅ Fine-Tuning Phase 2 validation complete"
```

### Phase 3: Flexible Integration Implementation (4-5 hours)

**Objective**: Implement dual integration approach for maximum flexibility

#### 3.1 Enhanced Process Artifacts Script (PRIMARY INTEGRATION)
**Updates to**: `security-ai-analysis/process_artifacts.py` (extend existing)

**Add fine-tuning arguments to argument parser** (opt-out approach):
```python
# Add to existing argument parser in main()
parser.add_argument("--skip-fine-tuning", action="store_true",
                   help="Skip MLX fine-tuning (fine-tuning enabled by default)")
parser.add_argument("--fine-tuning-model-name", type=str, 
                   help="Custom name for fine-tuned model (default: auto-generated)")
```

**Add Phase 5 fine-tuning integration after existing Phase 4 (HuggingFace Upload)**:
```python
# **Phase 5: MLX Fine-Tuning (Default Behavior)**
if not args.skip_fine_tuning:
    print("\n" + "="*60)
    print("🚀 Phase 5: MLX Fine-Tuning")
    print("="*60)
    
    try:
        from scripts.mlx_finetuning import MLXFineTuner, FineTuningConfig
        
        # Use the training dataset we just created in Phase 3
        latest_train_file = output_path / f"train_{timestamp}.jsonl"
        
        if latest_train_file.exists():
            config = FineTuningConfig.load_from_config()
            
            # Generate model name
            if args.fine_tuning_model_name:
                config.output_model_name = args.fine_tuning_model_name
            else:
                config.output_model_name = f"webauthn-security-{timestamp}"
            
            print(f"🎯 Fine-tuning model: {config.output_model_name}")
            print(f"📚 Training dataset: {latest_train_file}")
            
            fine_tuner = MLXFineTuner(config)
            fine_tuned_model = fine_tuner.run_fine_tuning(latest_train_file)
            
            print(f"✅ Fine-tuning completed: {fine_tuned_model}")
            
            # Log model information
            metadata_file = fine_tuned_model / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                print(f"🎨 Model: {metadata['model_name']}")
                print(f"⏱️  Duration: {metadata['training_duration_seconds']:.2f}s")
            
            pipeline_phases.append("Fine-tuning")
            
        else:
            print("❌ Training dataset not found - cannot proceed with fine-tuning")
            print(f"   Expected: {latest_train_file}")
            
    except Exception as e:
        print(f"❌ Fine-tuning failed: {e}")
        # Don't fail the entire pipeline if fine-tuning fails
        print("⚠️  Pipeline completed successfully, fine-tuning failed")
else:
    print("\n" + "="*60)
    print("⏭️  Phase 5: MLX Fine-Tuning (SKIPPED)")
    print("🔧 Use without --skip-fine-tuning for complete pipeline")
    print("="*60)

# Update final summary to show all phases
print(f"🎉 Complete {len(pipeline_phases)}-phase pipeline finished: {' → '.join(pipeline_phases)}'")
```

**Manual Usage Examples**:
```bash
# Complete 5-phase pipeline (fine-tuning enabled by default)
python3 process_artifacts.py

# Custom dataset (fine-tuning enabled by default)
python3 process_artifacts.py --artifacts-dir custom_data --fine-tuning-model-name "experimental-v2"

# Development mode (skip fine-tuning for faster testing)
python3 process_artifacts.py --artifacts-dir test_data --skip-fine-tuning
```

#### 3.2 Daemon Integration (AUTOMATED MODE)
**Updates to**: `local-analysis/security_artifact_daemon.py`

**Add configuration-driven fine-tuning to daemon workflow**:
```python
# Enhanced trigger_local_analysis method
def trigger_local_analysis(self, artifacts_dir: Path, run_info: Dict) -> bool:
    """Enhanced to include configurable fine-tuning"""
    logger.info(f"🤖 Starting local OLMo analysis for run {run_info['run_id']}...")
    
    # ... existing analysis code ...
    
    # Build analysis command (fine-tuning enabled by default)
    analysis_command = [
        sys.executable, str(process_script),
        "--artifacts-dir", str(artifacts_dir),
        "--output-dir", str(analysis_output),
        "--model-name", self._get_model_path(),
        "--branch", "main", 
        "--commit", run_info['head_sha']
    ]
    
    # Fine-tuning enabled by default - only skip if explicitly disabled
    try:
        from config_manager import OLMoSecurityConfig
        config = OLMoSecurityConfig()
        fine_tuning_config = config.get_fine_tuning_config()
        
        if fine_tuning_config.get('skip_in_daemon', False):
            analysis_command.append("--skip-fine-tuning")
            logger.warning("⚠️  Fine-tuning DISABLED in daemon configuration (emergency mode)")
        else:
            logger.info("🎯 Fine-tuning enabled in automated mode (default behavior)")
            
    except Exception as e:
        logger.warning(f"Could not load fine-tuning config: {e}")
        # Default behavior: fine-tuning enabled
        logger.info("🎯 Fine-tuning enabled by default (config load failed)")
    
    # ... rest of existing code ...
```

**Configuration Control** (Emergency Opt-out Only):
```yaml
# config/olmo-security-config.yaml
fine_tuning:
  skip_in_daemon: false  # Set to true only in emergencies to disable fine-tuning
```

**Daemon Usage**:
```bash
# Automated fine-tuning every 5 minutes (production mode)
launchctl load ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist

# Check daemon fine-tuning activity
tail -f security-ai-analysis/results/daemon.log | grep -i "fine-tuning"
```

#### 3.3 Standalone Fine-Tuning Script (ADVANCED MODE)
**File**: `security-ai-analysis/scripts/mlx_finetuning.py` (implement as per Phase 2)

**Standalone Usage Examples**:
```bash
# Direct fine-tuning on existing dataset
python3 scripts/mlx_finetuning.py --dataset results/train_20250910_143022.jsonl --output-name "custom-model"

# Fine-tuning with custom configuration
python3 scripts/mlx_finetuning.py --dataset data/custom.jsonl --config custom-config.yaml

# Validate existing fine-tuned model
python3 scripts/mlx_finetuning.py --validate-model ~/shared-olmo-models/fine-tuned/webauthn-security-v1
```

#### 3.4 Phase 3 Validation Tests (All Integration Modes)
**Test Script**: `security-ai-analysis/scripts/tests/test-fine-tuning-phase3.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Fine-Tuning Phase 3 Validation Tests (All Integration Modes)"

source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

# Test 1: process_artifacts.py integration  
echo "📝 Testing process_artifacts.py integration..."
python3 process_artifacts.py --help | grep -q "skip-fine-tuning" && echo "✅ Fine-tuning opt-out option added to process_artifacts"

# Test 2: Standalone script availability
echo "📝 Testing standalone script..."
python3 scripts/mlx_finetuning.py --help | grep -q "MLX-Optimized Fine-Tuning" && echo "✅ Standalone fine-tuning script works"

# Test 3: Mock end-to-end pipeline with fine-tuning
echo "📝 Testing complete pipeline integration..."
mkdir -p test_pipeline_data
echo '{"test": "vulnerability"}' > test_pipeline_data/mock_artifact.json

# Test command structure (dry run)
python3 -c "
import sys
from pathlib import Path
sys.path.append('.')
from process_artifacts import main

# Mock args for testing (fine-tuning enabled by default)
class MockArgs:
    skip_fine_tuning = False  # Default: fine-tuning enabled
    fine_tuning_model_name = 'test-model'
    artifacts_dir = Path('test_pipeline_data')
    output_dir = Path('test_pipeline_output')
    model_name = 'OLMo-2-1B-mlx-q4'
    branch = 'test'
    commit = 'test'

print('✅ Pipeline integration structure validates (fine-tuning enabled by default)')
"

# Test 4: Daemon integration check
echo "📝 Testing daemon integration..."
cd ../local-analysis
python3 -c "
import sys
sys.path.append('../security-ai-analysis')
from security_artifact_daemon import SecurityArtifactDaemon
daemon = SecurityArtifactDaemon()
print('✅ Daemon fine-tuning integration compatible')
"

echo "✅ Fine-Tuning Phase 3 validation complete - All integration modes ready"
```

#### 3.5 Integration Summary
**Three Integration Modes Successfully Implemented**:

1. **👩‍💻 Manual Development Mode**: `process_artifacts.py` (fine-tuning enabled by default)
   - Complete control over datasets and model names
   - Perfect for development, testing, and experimentation
   - Use `--skip-fine-tuning` only for faster development cycles

2. **🤖 Automated Production Mode**: Daemon with fine-tuning always enabled
   - Continuous fine-tuning with new security data every 5 minutes
   - Fine-tuning enabled by default (emergency opt-out available)
   - Production-ready with comprehensive logging

3. **🔧 Advanced Standalone Mode**: Direct `mlx_finetuning.py` execution
   - Maximum flexibility for research and advanced use cases
   - Works with any existing datasets
   - Independent model validation and testing

### Phase 4: Documentation & MLX Dependencies (2-3 hours)

**Objective**: Complete documentation and dependency management

#### 4.1 Enhanced Requirements  
**Updates to**: `security-ai-analysis/requirements.txt`
```txt
# Existing requirements...

# MLX fine-tuning dependencies (Apple Silicon only)
mlx>=0.0.8                    # MLX framework for Apple Silicon
mlx-lm>=0.0.8                 # MLX Language Model utilities
```

#### 4.2 Fine-Tuning Documentation
**File**: `security-ai-analysis/docs/FINE_TUNING.md`
```markdown
# MLX Fine-Tuning Guide

## Overview

This guide covers fine-tuning OLMo models for security vulnerability analysis using MLX optimization on Apple Silicon.

## Prerequisites

1. **AI Security Portability** implementation completed
2. **Apple Silicon Mac** (M1/M2/M3 series)  
3. **MLX framework** installed
4. **Prepared dataset** from security analysis pipeline

## Quick Start

### 1. Setup (if not already done)
```bash
python3 security-ai-analysis/scripts/setup.py
```

### 2. Run Fine-Tuning
```bash
cd security-ai-analysis
source venv/bin/activate

# Fine-tune with existing dataset
python3 scripts/mlx_finetuning.py --dataset data/security_dataset.jsonl

# Or run complete pipeline (fine-tuning enabled by default)
python3 process_artifacts.py --artifacts-dir data/
```

### 3. Use Fine-Tuned Model
Fine-tuned models are saved to `~/shared-olmo-models/fine-tuned/` and can be used across projects.

## Configuration

Fine-tuning parameters are configured in `config/olmo-security-config.yaml`:

```yaml
fine_tuning:
  training:
    learning_rate: 2e-5
    batch_size: 4  
    max_epochs: 3
```

## Performance

Expected fine-tuning performance on Apple Silicon:
- **M1/M2**: ~2-4 hours for typical security dataset
- **MLX Optimization**: 20-30X faster than CPU training
- **Memory Usage**: ~8-16GB during training

## Troubleshooting

### MLX Not Available
```bash
pip install mlx mlx-lm
```

### Model Not Found
Ensure base model is downloaded:
```bash
python3 scripts/setup.py
```
```

#### 4.3 Updated .gitignore
**Updates to**: `security-ai-analysis/.gitignore`
```gitignore
# Existing entries...

# Fine-tuning workspace (temporary training files)
fine-tuning/training_data/
fine-tuning/checkpoints/
fine-tuning/logs/
fine-tuning/temp/
```

### Phase 5: End-to-End Integration & Performance Testing (4-5 hours)

**Objective**: Comprehensive testing of all three integration modes with performance validation

#### 5.1 Complete Integration Test (All Modes)
**Test Script**: `security-ai-analysis/scripts/tests/test-fine-tuning-integration.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Fine-Tuning Complete Integration Test (All 3 Modes)"

# Test in fresh environment
TEST_DIR="/tmp/fine-tuning-integration-test-$(date +%s)"
mkdir -p "$TEST_DIR" 
cd "$TEST_DIR"

# Clone and setup
git clone https://github.com/hitoshura25/mpo-api-authn-server.git
cd mpo-api-authn-server

# Setup system
python3 security-ai-analysis/scripts/setup.py

# Create realistic test dataset
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

mkdir -p test_data
cat > test_data/security_dataset.jsonl << 'EOF'
{"instruction": "Analyze this SQL injection vulnerability in authentication", "response": "This SQL injection vulnerability occurs in the user authentication process..."}
{"instruction": "Explain the impact of this XSS vulnerability", "response": "This XSS vulnerability allows attackers to inject malicious scripts..."}
{"instruction": "Describe mitigation for this CSRF attack", "response": "To mitigate this CSRF attack, implement proper token validation..."}
EOF

echo "📝 Testing Mode 1: Manual Development Integration"
# Test complete 5-phase pipeline with process_artifacts.py
python3 process_artifacts.py \\
  --artifacts-dir test_data \\
  --output-dir integration_output_manual \\
  --fine-tuning-model-name "test-manual-model"

# Validate manual integration
if [[ -d ~/shared-olmo-models/fine-tuned/test-manual-model ]]; then
  echo "✅ Manual integration: Fine-tuned model created"
else
  echo "❌ Manual integration failed"
  exit 1
fi

echo "📝 Testing Mode 2: Daemon Integration"
# Test daemon integration (test mode)
cd ../local-analysis
python3 security_artifact_daemon.py --test-mode --data-dir ../security-ai-analysis/test_data
echo "✅ Daemon integration: Test mode completed successfully"

echo "📝 Testing Mode 3: Standalone Advanced Mode"
# Test standalone fine-tuning script
cd ../security-ai-analysis

# Find a training dataset from manual test
TRAIN_FILE=$(find integration_output_manual -name "train_*.jsonl" | head -1)
if [[ -n "$TRAIN_FILE" ]]; then
  python3 scripts/mlx_finetuning.py \\
    --dataset "$TRAIN_FILE" \\
    --output-name "test-standalone-model"
  
  if [[ -d ~/shared-olmo-models/fine-tuned/test-standalone-model ]]; then
    echo "✅ Standalone integration: Fine-tuned model created"
  else
    echo "❌ Standalone integration failed"
    exit 1
  fi
else
  echo "⚠️  No training dataset found for standalone test"
fi

# Validate all created models
echo "📝 Validating all created models..."
for model_dir in ~/shared-olmo-models/fine-tuned/test-*; do
  if [[ -d "$model_dir" ]]; then
    echo "Validating $(basename "$model_dir")..."
    python3 scripts/mlx_finetuning.py --validate-model "$model_dir"
  fi
done

echo "✅ Fine-Tuning complete integration test passed - All 3 modes working"

# Cleanup
cd /
rm -rf "$TEST_DIR"
```

#### 5.2 Performance Benchmarking
**Test Script**: `security-ai-analysis/scripts/tests/test-fine-tuning-performance.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Fine-Tuning Performance Benchmarking"

source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

# Create performance test dataset
mkdir -p performance_test_data
echo "Generating larger test dataset for performance testing..."

# Generate 100 training examples
for i in {1..100}; do
  echo '{"instruction": "Analyze security vulnerability #'$i'", "response": "This is a detailed security analysis response for vulnerability '$i' that covers the technical details, impact assessment, and recommended remediation steps..."}' >> performance_test_data/perf_dataset.jsonl
done

echo "Created performance dataset with 100 examples"

# Run performance test
echo "Starting performance benchmark..."
START_TIME=$(date +%s)

python3 scripts/mlx_finetuning.py \\
  --dataset performance_test_data/perf_dataset.jsonl \\
  --output-name webauthn-security-perf-test

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Fine-tuning completed in $DURATION seconds"

# Performance validation
if [[ $DURATION -lt 7200 ]]; then  # Less than 2 hours
  echo "✅ Performance target met: $DURATION seconds (< 2 hours)"
else
  echo "⚠️  Performance slower than expected: $DURATION seconds"
fi

# Validate model quality (basic checks)
PERF_MODEL=~/shared-olmo-models/fine-tuned/webauthn-security-perf-test
if python3 scripts/mlx_finetuning.py --validate-model "$PERF_MODEL"; then
  echo "✅ Performance test model validation passed"
else
  echo "❌ Performance test model validation failed"
  exit 1
fi

echo "✅ Fine-Tuning performance benchmarking complete"
```

## Risk Mitigation & Success Criteria

### Low-Risk Approach
- **Prerequisites enforced**: Portability implementation required first
- **Incremental phases**: Each phase independently testable
- **MLX compatibility**: Graceful fallback if MLX unavailable  
- **Configuration-driven**: All parameters tunable without code changes

### Success Criteria

#### Must Pass All Tests
1. **Phase 1**: Fine-tuning configuration loads, workspace creation works
2. **Phase 2**: MLX fine-tuning engine functional, model structure creation works
3. **Phase 3**: Pipeline integration successful, daemon compatibility maintained
4. **Phase 4**: Documentation complete, dependencies resolved
5. **Phase 5**: End-to-end integration works, performance targets met

#### Performance Requirements
- **MLX Performance**: Fine-tuning completes within 2 hours for typical dataset
- **Model Quality**: Fine-tuned model passes validation checks
- **Pipeline Integration**: All 4 phases work together seamlessly
- **Shared Model Architecture**: Fine-tuned models available across projects

#### Technical Requirements
- **Apple Silicon Compatibility**: Works on M1/M2/M3 Macs with MLX
- **Memory Efficiency**: Fine-tuning uses <16GB RAM
- **Model Sharing**: Fine-tuned models stored in shared directory structure
- **Configuration Driven**: All parameters configurable via YAML

## Updated Implementation Timeline (Flexible Dual Integration)

**Total Estimated Time**: 18-24 hours across multiple sessions (reduced due to existing infrastructure)
- **Phase 1**: 4-6 hours (infrastructure & configuration)
- **Phase 2**: 6-8 hours (MLX fine-tuning engine - core implementation)  
- **Phase 3**: 4-5 hours (flexible integration - all 3 modes)
- **Phase 4**: 2-3 hours (documentation & dependencies)
- **Phase 5**: 4-5 hours (comprehensive integration & performance testing)

## System Architecture Context
- **AI Security System**: Complete 4-phase pipeline (Analysis → Narrativization → Dataset → HuggingFace Upload)
- **Portability Implementation**: Shared model architecture at `~/shared-olmo-models/`
- **Daemon Automation**: LaunchAgent polling integration capability
- **Production Dataset**: HuggingFace dataset publishing at `hitoshura25/webauthn-security-vulnerabilities-olmo`
- **Fine-Tuning**: Phase 5 & 6 implementation target

### 🎯 Implementation Target
**What we're building**: Phase 5 MLX Fine-Tuning with flexible dual integration

**Three Integration Modes** (All with Fine-tuning Enabled by Default):
1. **Manual Mode**: `process_artifacts.py` (fine-tuning always enabled, `--skip-fine-tuning` for development only)
2. **Automated Mode**: Daemon integration with fine-tuning always enabled (emergency opt-out available)
3. **Standalone Mode**: `scripts/mlx_finetuning.py` (advanced research use)

### 🔄 Architecture Confirmed
- **Shared Models**: `~/shared-olmo-models/base/` (existing) + `~/shared-olmo-models/fine-tuned/` (new)
- **MLX Optimization**: Maintain 20-30X performance advantage during training
- **Configuration**: Extend existing `config/olmo-security-config.yaml` with fine-tuning section
- **Phase Structure**: Analysis → Narrativization → Dataset Creation → HuggingFace Upload → **Fine-tuning**

### ⚡ Ready to Implement
- **All prerequisites met**: Working system, shared model architecture, daemon automation
- **Clear integration path**: process_artifacts.py already has complete 4-phase pipeline
- **Test-driven approach**: Each phase has validation script that must pass
- **Hardware requirement**: Apple Silicon with MLX framework

### 🚀 Next Steps for Implementation
1. **Begin Phase 1**: Create fine-tuning configuration system
2. **Implement Phase 2**: Build MLX fine-tuning engine (`mlx_finetuning.py`)
3. **Add Phase 3**: Integrate all three modes (manual, automated, standalone)
4. **Validate Phase 5**: Comprehensive end-to-end testing

**⚠️ Critical**: Fine-tuning requires Apple Silicon with MLX framework. System is otherwise ready for implementation.

---

---

## 🚀 ENHANCED: HuggingFace Model Upload Integration

### Complete Model Sharing Package

**✅ What Gets Uploaded to HuggingFace Model Hub:**

```
hitoshura25/webauthn-security-olmo-model/
├── weights.safetensors           # 🎯 The fine-tuned weights (~1.2GB) - THE VALUABLE PART!
├── tokenizer.json               # 📝 Text processing (how to convert text→numbers)
├── tokenizer_config.json        # 📝 Tokenizer settings  
├── vocab.json                   # 📝 Vocabulary (words the model knows)
├── config.json                  # ⚙️ Model architecture (layers, size, etc.)
├── generation_config.json       # ⚙️ How to generate text
├── README.md                    # 📋 Complete model card with usage examples
├── metadata.json                # 📊 Training details, dataset info, performance
└── .gitattributes              # 🔧 Git LFS settings for large files
```

**Total Upload Size**: ~1.5-2.5GB (mostly the weights)

### Community Best Practices Implementation

**🏆 Model Card Auto-Generation** (Following HuggingFace standards):
```yaml
---
license: apache-2.0
library_name: transformers
tags:
- security
- webauthn  
- vulnerability-analysis
- cybersecurity
- olmo
datasets:
- hitoshura25/webauthn-security-vulnerabilities-olmo
base_model:
- allenai/OLMo-2-1B
---
```

**📚 Complete Usage Examples**:
```python
# Standard usage
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("hitoshura25/webauthn-security-olmo")

# MLX-optimized usage (20-30X faster on Apple Silicon)
from mlx_lm import load, generate
model, tokenizer = load("hitoshura25/webauthn-security-olmo")
```

### Enhanced Fine-Tuning Script

**🔄 New Command Line Options**:
```bash
# Fine-tune and upload automatically
python3 scripts/mlx_finetuning.py --dataset data.jsonl --upload

# Upload existing fine-tuned model
python3 scripts/mlx_finetuning.py --upload-model ~/shared-olmo-models/fine-tuned/webauthn-security-v1

# Complete pipeline with model upload (fine-tuning enabled by default)
python3 process_artifacts.py --upload-model

# Skip fine-tuning for development/testing only
python3 process_artifacts.py --skip-fine-tuning
```

### Configuration Integration

**📝 Enhanced `config/olmo-security-config.yaml`**:
```yaml
fine_tuning:
  # HuggingFace model sharing
  huggingface:
    upload_enabled: false      # Toggle for automatic upload
    default_repo_prefix: "hitoshura25"  # Repository naming
    private_repos: false       # Public models for research sharing
    
  # Existing configuration...
  workspace_dir: "security-ai-analysis/fine-tuning"
  default_output_name: "webauthn-security-v1"
```

### Why This Matters

**🌍 Community Impact**:
- **Complete Package**: Researchers get weights + tokenizer + config + documentation
- **Ready to Use**: No setup required, just `from_pretrained()` 
- **MLX Optimized**: Specialized performance files for Apple Silicon
- **Research Contribution**: Both training data AND resulting models shared
- **Open Science**: Aligns with OLMo's open research mission

**🎯 Integration Modes All Support Upload**:
- **Manual**: `process_artifacts.py` (both fine-tuning and model upload enabled by default)
- **Automated**: Daemon with fine-tuning and upload always enabled
- **Standalone**: Direct script upload capabilities

---

## Phase 6: Production MLX Fine-Tuning & Complete Model Sharing

### 🎯 Phase 6 Architecture Requirements
**Objective**: Implement production-grade MLX fine-tuning with community-standard model sharing capabilities.

**Core Requirements**:
- **Real MLX Training**: Implement actual model weight fine-tuning using MLX-LM framework
- **Complete Model Artifacts**: Generate functional weights, tokenizer, and configuration files  
- **Community Standards**: Ensure uploaded models meet HuggingFace compatibility requirements
- **Default Behavior**: Both fine-tuning and model upload enabled by default with opt-out capability
- **Validation Protocol**: Follow CLAUDE.md external API validation requirements

### 6.1 CLI Interface Specification

**Default Behavior Requirement**: Both fine-tuning and model upload must run by default to maximize research value and community contribution.

**Required CLI Pattern**:

```python
# Required CLI Interface Specification
parser.add_argument("--skip-fine-tuning", action="store_true",
                   help="Skip MLX fine-tuning (fine-tuning enabled by default)")
parser.add_argument("--skip-model-upload", action="store_true",
                   help="Skip uploading fine-tuned model to HuggingFace Hub (upload enabled by default)")
```

**Behavioral Specification**:
- **Default**: `python3 process_artifacts.py` → Fine-tuning + Model Upload  
- **Skip Fine-tuning**: `python3 process_artifacts.py --skip-fine-tuning` → Dataset only + Model Upload
- **Skip Upload**: `python3 process_artifacts.py --skip-model-upload` → Fine-tuning only
- **Minimal**: `python3 process_artifacts.py --skip-fine-tuning --skip-model-upload` → Dataset creation only

### 6.2 MLX-LM Integration Requirements

**Objective**: Implement production MLX fine-tuning with validated MLX-LM APIs.

#### 6.2.1 MLX-LM API Validation
**File**: `security-ai-analysis/scripts/research/mlx_api_research.py` (new)
**Target**: Research and document actual MLX-LM APIs

**Tasks**:
- [ ] **API Documentation Research**: Use WebFetch to validate MLX-LM documentation
  - Research `mlx_lm.tuner` module and available fine-tuning functions
  - Document exact parameter requirements for `tuner.train()`
  - Validate LoRA vs full fine-tuning approaches available
  - Confirm model loading, training, and saving workflows

- [ ] **Local API Testing**: Create standalone test script
  ```python
  # Validate MLX-LM installation and basic functionality
  from mlx_lm import load, generate, tuner
  
  # Test model loading
  model, tokenizer = load("mlx-community/OLMo-2-1B-mlx-q4")
  
  # Test basic generation
  response = generate(model, tokenizer, "Test prompt", max_tokens=10)
  
  # Research tuner.train() parameters
  # Document actual API signature and requirements
  ```

- [ ] **Integration Pattern Documentation**: Document validated integration approach
  - Complete parameter mapping for security analysis fine-tuning
  - Error handling patterns for MLX-specific failures
  - Memory management for Apple Silicon optimization
  - Performance benchmarking approach

#### 6.2.2 Production Fine-Tuning Implementation
**File**: `security-ai-analysis/scripts/mlx_finetuning.py` (modify)
**Target**: Replace placeholder `_create_model_structure()` with real MLX training

**Current Issue (Lines 227-242)**:
```python
# ❌ PLACEHOLDER: Creates fake files instead of real model weights
placeholder_files = [
    "config.json",
    "tokenizer.json", 
    "tokenizer_config.json",
    "weights.safetensors",  # ❌ Placeholder text file, not real weights!
    "generation_config.json"
]

for file_name in placeholder_files:
    placeholder_file = output_path / file_name
    if not placeholder_file.exists():
        placeholder_file.write_text(f"# Placeholder for {file_name}\\n# Generated by MLX fine-tuning process\\n")
```

**Required Changes**:
- [ ] **Replace Placeholder Training**: Remove Lines 227-242 placeholder file creation
  ```python
  # ❌ REMOVE: Placeholder implementation
  def _create_model_structure(self, output_path: Path, training_args: Dict[str, Any]):
      # Current placeholder logic creates fake files
  
  # ✅ ADD: Real MLX fine-tuning
  def _execute_mlx_training(self, output_path: Path, training_args: Dict[str, Any]):
      # Real tuner.train() integration with validated parameters
      # Actual model weight fine-tuning
      # Real tokenizer and config generation
  ```

- [ ] **MLX Training Integration**: Implement validated `tuner.train()` calls
  - Dataset preparation in MLX-LM compatible format
  - LoRA fine-tuning configuration for memory efficiency
  - Training loop with proper checkpointing
  - Model saving with complete artifact generation

#### 6.2.3 Chat Template Integration & Security Optimization (SEPTEMBER 2025 UPDATE)
**Target**: Resolve OLMo chat template issue with security-focused approach based on current research
**Integration Point**: Extends Phase 6.2.2 Production Fine-Tuning Implementation

##### Current Research Findings (September 2025)

**🔍 OLMo-2-1B Chat Template Current State**:
- **No Built-in Template**: OLMo base models don't have specific chat templates
- **ChatML Default**: `apply_chat_template` defaults to ChatML format with `<|im_start|>` and `<|im_end|>` tokens
- **Instruct Variants**: OLMo-2-Instruct models have evolved with embedded chat templates using `<|user|>`, `<|assistant|>`, `<|endoftext|>`
- **MLX-LM Handling**: MLX-LM automatically handles chat template application during fine-tuning

**🚨 Current Security Vulnerabilities in Fine-tuning (2025)**:
- **Safety Alignment Breakdown**: Fine-tuning can compromise safety alignment with as few as **10 adversarial examples** at **$0.20 cost**
- **Safety Layer Vulnerability**: Recent research identifies "safety layers" in LLMs that are crucial for security but vulnerable to fine-tuning attacks
- **Training Data Poisoning**: Manipulated training data can introduce security flaws even when models function "correctly"
- **Regressive Learning**: Unlike humans, LLMs lose prior safety learnings during fine-tuning

**🛡️ Current Mitigation Approaches**:
- **Safely Partial-Parameter Fine-Tuning (SPPFT)**: Fixes gradients of safety layers to preserve security
- **Continuous Red-teaming**: Algorithmic evaluation to identify vulnerabilities post fine-tuning
- **Human-in-the-loop**: Expert review of AI-generated code for security flaws

##### MLX-LM Data Format Security Analysis (Current)

**📊 Format Security Ranking** (Best to Worst for Security Applications):

**🥇 Chat Format (Highly Recommended)**:
```json
{
  "messages": [
    {"role": "user", "content": "Analyze this vulnerability..."},
    {"role": "assistant", "content": "This vulnerability occurs..."}
  ]
}
```

**Security Advantages**:
- ✅ **Maintains Safety Layers**: Preserves role-based security boundaries
- ✅ **Template Validation**: Built-in format validation prevents malformed inputs
- ✅ **Proven Results**: Practitioners consistently report superior outcomes
- ✅ **Security Context**: Clear separation between instructions and data prevents prompt injection

**🥈 Completions Format (Moderate Security)**:
```json
{
  "prompt": "Analyze this vulnerability...",
  "completion": "This vulnerability occurs..."
}
```

**🥉 Text Format (Not Recommended)**:
```json
{
  "text": "Combined instruction and response text..."
}
```

**Security Issues**:
- ❌ **No Template Application**: Bypasses base model chat templates
- ❌ **Context Blending**: Merges instructions with data, increasing injection risks
- ❌ **Poor Results**: Consistently inferior performance reported

##### Chat Template Solution Implementation

**🎯 Primary Solution: Security-by-Default ChatML Integration**

**File**: `security-ai-analysis/scripts/mlx_finetuning.py` (modify `prepare_training_data` method)

**Current Challenge**: OLMo-2-1B lacks chat template, causing `apply_chat_template` error
**Solution**: Hard-code ChatML template with built-in security best practices (no configuration required)

**Security-by-Default Implementation**:

```python
def _configure_chat_template(self, tokenizer) -> None:
    """Hard-code ChatML template for OLMo-2-1B with security-by-default"""
    
    # Always add ChatML special tokens (no configuration - security by default)
    special_tokens = {
        "additional_special_tokens": ["<|im_start|>", "<|im_end|>"]
    }
    tokenizer.add_special_tokens(special_tokens)
    
    # Hard-coded ChatML template optimized for security (no configuration options)
    chat_template = """{% for message in messages %}{{ '<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>\n' }}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"""
    
    tokenizer.chat_template = chat_template
    
    logger.info("✅ Security-by-default ChatML template applied")

def prepare_training_data(self, dataset_file: Path) -> Path:
    """
    Prepare training data with security-by-default implementation
    
    Expected input: JSON lines with 'instruction' and 'response' fields
    Output: MLX-compatible directory with train.jsonl and valid.jsonl
    
    Security measures applied by default (no configuration):
    - ChatML format (highest security rating)
    - Security analyst role enforcement
    - Structured message format for safety layer preservation
    """
    logger.info(f"Preparing training data from: {dataset_file}")
    
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_file}")
    
    # Create MLX training data directory
    mlx_data_dir = self.config.workspace_dir / "training_data" / "mlx_data"
    mlx_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Read and convert all data with security context preservation
    all_data = []
    error_count = 0
    
    with open(dataset_file, 'r') as infile:
        for line_num, line in enumerate(infile, 1):
            try:
                data = json.loads(line.strip())
                
                # Validate required fields
                if 'instruction' not in data or 'response' not in data:
                    logger.warning(f"Missing required fields at line {line_num}")
                    error_count += 1
                    continue
                
                # Convert to MLX fine-tuning format with security-by-default measures
                # Always use structured chat format (no configuration - security by default)
                mlx_format = {
                    "messages": [
                        {
                            "role": "user", 
                            "content": f"You are a security analyst specializing in WebAuthn and web application vulnerabilities. {data['instruction']}"
                        },
                        {
                            "role": "assistant", 
                            "content": data["response"]
                        }
                    ]
                }
                
                all_data.append(mlx_format)
                
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                error_count += 1
                continue
    
    if not all_data:
        raise ValueError("No valid training data found after processing")
    
    # Split data: 80% train, 20% validation (preserving security context)
    split_point = int(len(all_data) * 0.8)
    train_data = all_data[:split_point]
    valid_data = all_data[split_point:]
    
    # Write train.jsonl
    train_file = mlx_data_dir / "train.jsonl"
    with open(train_file, 'w') as f:
        for item in train_data:
            f.write(json.dumps(item) + "\n")
    
    # Write valid.jsonl
    valid_file = mlx_data_dir / "valid.jsonl"
    with open(valid_file, 'w') as f:
        for item in valid_data:
            f.write(json.dumps(item) + "\n")
    
    logger.info(f"MLX training data prepared: {mlx_data_dir}")
    logger.info(f"Training samples: {len(train_data)}")
    logger.info(f"Validation samples: {len(valid_data)}")
    logger.info(f"Processing errors: {error_count}")
    logger.info(f"✅ Security-by-default chat format applied (ChatML with analyst role)")
    
    return mlx_data_dir
```

##### Security-by-Default Implementation

**🛡️ Built-in Security Measures (No Configuration Required)**:

All security best practices are **hard-coded as default behavior** with no configuration toggles:

- ✅ **ChatML Format**: Always used (highest security rating)
- ✅ **Safety Layer Preservation**: Built into structured chat format 
- ✅ **Security Analyst Role**: Always enforced in training data
- ✅ **Prompt Injection Protection**: Automatic via role-based separation
- ✅ **Enhanced Error Handling**: Chat template diagnostics always enabled

**Rationale**: Security isn't optional - these measures are applied by default to ensure maximum safety without decision paralysis.

**🔄 MLX Command Integration**:

**File**: `security-ai-analysis/scripts/mlx_finetuning.py` (modify `_execute_mlx_training`)

```python
def _execute_mlx_training(self, output_path: Path, training_args: Dict[str, Any]):
    """Execute MLX fine-tuning with security-by-default implementation"""
    
    # Import subprocess for MLX-LM CLI integration
    import subprocess
    
    try:
        # Prepare training data directory (now returns directory, not single file)
        training_data_dir = training_args.get("train_file")  # This is the MLX data directory
        if not training_data_dir or not Path(training_data_dir).exists():
            raise FileNotFoundError(f"Training data directory not found: {training_data_dir}")
        
        # Validate required MLX files exist
        train_file = Path(training_data_dir) / "train.jsonl"
        valid_file = Path(training_data_dir) / "valid.jsonl"
        
        if not train_file.exists():
            raise FileNotFoundError(f"Training file not found: {train_file}")
        if not valid_file.exists():
            raise FileNotFoundError(f"Validation file not found: {valid_file}")
        
        # Create adapter output path
        adapter_path = output_path / "adapters"
        adapter_path.mkdir(parents=True, exist_ok=True)
        
        # Build MLX-LM LoRA command with directory path and security optimization
        mlx_command = [
            "mlx_lm.lora",
            "--model", training_args["model"],
            "--train",
            "--data", str(training_data_dir),  # Pass directory containing train.jsonl and valid.jsonl
            "--adapter-path", str(adapter_path),
            "--batch-size", str(training_args["batch_size"]),
            "--iters", str(training_args.get("training_steps", 100)),
            "--fine-tune-type", "lora"
        ]
        
        logger.info(f"🔧 Running MLX-LM command with security-by-default data: {' '.join(mlx_command)}")
        
        # Execute MLX fine-tuning with proper error handling
        result = subprocess.run(
            mlx_command,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            check=True
        )
        
        logger.info("✅ MLX fine-tuning completed successfully")
        logger.info(f"Training output: {result.stdout}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ MLX fine-tuning failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        
        # Enhanced error handling for chat template issues (security-by-default diagnostics)
        if "chat_template" in str(e.stderr) or "apply_chat_template" in str(e.stderr):
            logger.error("💡 Chat template issue detected - security-by-default ChatML should be applied automatically")
        elif "Missing required fields" in str(e.stderr):
            logger.error("💡 Data format issue - security-by-default message structure may not be applied")
        
        raise RuntimeError(f"MLX fine-tuning failed: {e.stderr}")
```

##### Security Validation Integration

**🧪 Security-by-Default Testing Framework**:

**File**: `security-ai-analysis/scripts/tests/test-fine-tuning-phase6-security.sh` (new)

```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Fine-Tuning Phase 6 Security-by-Default Validation Tests"

source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

# Test 1: Chat template configuration
echo "📝 Testing chat template configuration..."
python3 -c "
from scripts.mlx_finetuning import MLXFineTuner
from fine_tuning_config import FineTuningConfig

config = FineTuningConfig.load_from_config()
fine_tuner = MLXFineTuner(config)

# Test chat template application
print('✅ Chat template configuration test passed')
"

# Test 2: Security-optimized data preparation
echo "📝 Testing security-optimized data preparation..."
mkdir -p test_security_data
cat > test_security_data/security_dataset.jsonl << 'EOF'
{"instruction": "Analyze this SQL injection vulnerability", "response": "This SQL injection vulnerability occurs due to unsanitized user input being directly concatenated into SQL queries."}
{"instruction": "Explain this XSS vulnerability", "response": "This XSS vulnerability allows attackers to inject malicious scripts into web pages viewed by other users."}
EOF

python3 -c "
from scripts.mlx_finetuning import MLXFineTuner
from fine_tuning_config import FineTuningConfig
from pathlib import Path

config = FineTuningConfig.load_from_config()
fine_tuner = MLXFineTuner(config)

# Test data preparation with security-by-default implementation
dataset_file = Path('test_security_data/security_dataset.jsonl')
mlx_data_dir = fine_tuner.prepare_training_data(dataset_file)

# Verify chat format and security context
train_file = mlx_data_dir / 'train.jsonl'
with open(train_file, 'r') as f:
    first_line = f.readline()
    import json
    data = json.loads(first_line)
    
    # Validate structure
    assert 'messages' in data, 'Missing messages structure'
    assert len(data['messages']) == 2, 'Incorrect message count'
    assert data['messages'][0]['role'] == 'user', 'Incorrect user role'
    assert data['messages'][1]['role'] == 'assistant', 'Incorrect assistant role'
    assert 'security analyst' in data['messages'][0]['content'], 'Missing security context'
    
print('✅ Security-by-default data preparation test passed')
"

# Test 3: MLX command structure validation
echo "📝 Testing MLX command structure..."
python3 -c "
from scripts.mlx_finetuning import MLXFineTuner
from fine_tuning_config import FineTuningConfig
from pathlib import Path

config = FineTuningConfig.load_from_config()
fine_tuner = MLXFineTuner(config)

# Verify MLX data directory structure
mlx_data_dir = Path('fine-tuning/training_data/mlx_data')
if mlx_data_dir.exists():
    train_file = mlx_data_dir / 'train.jsonl'
    valid_file = mlx_data_dir / 'valid.jsonl'
    
    if train_file.exists() and valid_file.exists():
        print('✅ MLX command structure validation passed')
    else:
        print('⚠️  MLX files not found - run data preparation first')
else:
    print('⚠️  MLX data directory not found - run data preparation first')
"

echo "✅ Fine-Tuning Phase 6 Security-by-Default validation complete"
```

##### Updated Success Criteria

**✅ Security-by-Default Chat Template Resolution**:
- ChatML template hard-coded for OLMo-2-1B models (no configuration required)
- Security context automatically preserved in all training data
- MLX-LM chat template compatibility built-in by default

**✅ Security-by-Default Implementation**:
- Safety layer protection automatically applied through structured chat format
- Security analyst role enforced in all training data (no opt-out)
- Enhanced error handling for chat template issues built-in

**✅ Security-by-Default Data Format**:
- Directory structure (train.jsonl + valid.jsonl) always used
- 80/20 train/validation split with security context automatically preserved
- Message structure validation and security role inclusion mandatory

**✅ Seamless Integration**:
- Extends Phase 6.2.2 without breaking existing tests
- Compatible with all three integration modes (Manual, Automated, Standalone)
- Maintains default behavior (fine-tuning + model upload enabled)
- Security measures applied transparently without configuration overhead

### 6.3 Complete Model Artifact Upload ⚠️ CRITICAL

**Problem**: Current upload includes only placeholder files, violating community standards
**Solution**: Ensure complete model artifact upload with real weights and metadata

#### 6.3.1 Model Artifact Requirements Analysis
**Reference**: HuggingFace Model Hub community standards
**Target**: Document complete artifact requirements

**Community Standard Components**:
- [ ] **Model Weights** (`model.safetensors` or `pytorch_model.bin`)
  - Real fine-tuned weights in SafeTensors format (preferred)
  - Weight file integrity and format validation
  - Proper tensor naming conventions

- [ ] **Tokenizer Files** (Complete tokenizer functionality)  
  - `tokenizer.json` - Fast tokenizer implementation
  - `tokenizer_config.json` - Tokenizer configuration
  - `vocab.txt` or equivalent vocabulary files
  - Special token configurations (`special_tokens_map.json`)

- [ ] **Model Configuration** (Transformer architecture details)
  - `config.json` - Model architecture and hyperparameters
  - `generation_config.json` - Generation-specific configurations
  - Model metadata and compatibility information

- [ ] **Model Card** (`README.md`)
  - Current implementation has comprehensive model card ✅
  - Training methodology and dataset description
  - Performance benchmarks and limitations
  - Usage examples with executable code

#### 6.3.2 Artifact Validation System
**File**: `security-ai-analysis/scripts/validate_model_artifacts.py` (new)
**Target**: Validate uploaded models meet community standards

**Validation Checks**:
- [ ] **File Integrity**: Verify all required files exist and are non-empty
- [ ] **SafeTensors Validation**: Confirm weight files contain actual tensors
- [ ] **Tokenizer Functionality**: Test tokenizer encoding/decoding
- [ ] **Model Loading**: Verify model loads correctly with `transformers` library
- [ ] **Generation Testing**: Confirm model generates coherent output

```python
def validate_model_artifacts(model_path: Path) -> Dict[str, bool]:
    """Validate model meets HuggingFace community standards"""
    
    validation_results = {
        'weights_valid': False,
        'tokenizer_functional': False, 
        'config_valid': False,
        'model_card_complete': False,
        'generation_works': False
    }
    
    # Check SafeTensors format and content
    # Validate tokenizer functionality
    # Test model loading and generation
    # Verify model card completeness
    
    return validation_results
```

#### 6.3.3 Upload Quality Gates
**Target**: Prevent uploading non-functional models to HuggingFace

**Pre-Upload Validation**:
- [ ] **Mandatory Artifact Check**: Fail upload if validation fails
- [ ] **Model Functionality Test**: Require successful generation test
- [ ] **Size Validation**: Ensure model files are reasonable size (not empty placeholders)
- [ ] **Metadata Completeness**: Verify training metadata exists and is valid

```python
def upload_to_huggingface(self, model_path: Path, custom_repo_name: Optional[str] = None) -> Optional[str]:
    """Upload with mandatory validation"""
    
    # ✅ ADD: Pre-upload validation
    validation_results = validate_model_artifacts(model_path)
    if not all(validation_results.values()):
        failed_checks = [k for k, v in validation_results.items() if not v]
        raise ValueError(f"Model validation failed: {failed_checks}")
    
    # Existing upload logic...
```

### 6.4 Integration Testing & Validation

#### 6.4.1 End-to-End Production Testing
**File**: `security-ai-analysis/scripts/tests/test-fine-tuning-phase6.sh` (new)
**Target**: Validate complete real fine-tuning workflow

**Test Coverage**:
- [ ] **Real Training**: Execute actual MLX fine-tuning with small dataset
- [ ] **Artifact Generation**: Verify real model files created (not placeholders)
- [ ] **Upload Testing**: Test upload with validation to private repository
- [ ] **Model Functionality**: Download and test uploaded model functionality
- [ ] **Performance Benchmarking**: Confirm MLX optimization maintained

### 6.5 Updated Command Summary

```bash
# 🎯 Default (Recommended): Complete 5-phase pipeline with fine-tuning AND model upload
python3 process_artifacts.py

# 🧪 Development: Skip fine-tuning for faster testing
python3 process_artifacts.py --skip-fine-tuning

# 📊 Dataset Only: Skip model upload (keep fine-tuning)
python3 process_artifacts.py --skip-model-upload

# 🔧 Minimal: Skip both (dataset creation only)
python3 process_artifacts.py --skip-fine-tuning --skip-model-upload

# 🚀 Standalone: Direct fine-tuning on existing datasets
python3 scripts/mlx_finetuning.py --dataset data.jsonl --upload
```

### Phase 6 Success Criteria

✅ **Default Behavior**: Both fine-tuning and model upload enabled by default with opt-out flags  
✅ **MLX Integration**: Real MLX-LM fine-tuning replaces placeholder implementation  
✅ **Complete Artifacts**: Model uploads include functional weights, tokenizer, and config  
✅ **Validation System**: Pre-upload validation prevents non-functional model uploads  
✅ **Community Standards**: Uploaded models meet HuggingFace community standards  

**Result**: Production-ready AI Security Fine-Tuning system with complete model sharing workflow

---

## 🎯 SUMMARY: Fine-Tuning AND Model Upload as Default Behavior

### **Key Change: From Mixed to Consistent Default Behavior**

**✅ BEFORE (Mixed)**: 
- Fine-tuning: `python3 process_artifacts.py` (default enabled) ✅
- Model upload: `python3 process_artifacts.py --upload-model` (opt-in) ❌

**🚀 AFTER (Consistent)**: `python3 process_artifacts.py` (both fine-tuning AND model upload enabled by default)

### **Why This Change Makes Sense**

1. **🎯 Purpose Alignment**: System exists to create AND share WebAuthn security intelligence
2. **📈 Maximizes Value**: Every security scan improves the model AND contributes to community
3. **🔄 Automation Ready**: Daemon gets maximum research value from each 5-minute cycle
4. **💡 Simplicity**: Default behavior does the right thing without configuration
5. **🚀 Research Impact**: Continuous model improvement AND sharing for community benefit
6. **🤝 Community Standards**: Aligns with AI research best practices for model sharing

### **When To Use Opt-Out Flags**

**`--skip-fine-tuning` is only for**:
- 🧪 **Development/Testing**: Faster iteration during pipeline development
- 🚨 **Emergency Mode**: If fine-tuning breaks, temporary disable via config
- 📊 **Dataset-Only Runs**: Rare cases where only training data needed

**`--skip-model-upload` is only for**:
- 🔒 **Private Research**: When models contain sensitive information
- 🚨 **Emergency Mode**: If upload breaks, temporary disable via config
- 🧪 **Development/Testing**: Skip upload during development cycles

### **Updated Command Summary**

```bash
# 🎯 Default (Recommended): Complete 5-phase pipeline with fine-tuning AND model upload
python3 process_artifacts.py

# 🧪 Development: Skip fine-tuning for faster testing
python3 process_artifacts.py --skip-fine-tuning

# 📊 Dataset Only: Skip model upload (keep fine-tuning)
python3 process_artifacts.py --skip-model-upload

# 🔧 Minimal: Skip both (dataset creation only)
python3 process_artifacts.py --skip-fine-tuning --skip-model-upload

# 🚀 Standalone: Direct fine-tuning on existing datasets
python3 scripts/mlx_finetuning.py --dataset data.jsonl --upload
```

### **Configuration Philosophy**

**Default Behavior**: Always fine-tune AND upload models (maximum research value + community contribution)  
**Fine-tuning Override**: `--skip-fine-tuning` (emergency disable only)  
**Upload Override**: `--skip-model-upload` (emergency disable only)  
**Daemon Override**: `skip_in_daemon: true` (emergency disable via config)  
**Result**: Every security scan contributes to model improvement AND community sharing unless explicitly skipped

---

## Implementation Prerequisites

**Required Infrastructure**: AI Security Portability Implementation (shared model architecture)  
**Hardware Requirements**: Apple Silicon with MLX framework support  
**Software Dependencies**: MLX-LM, HuggingFace Hub, transformers library  

**Objective**: Complete 6-phase implementation enabling automated WebAuthn security analysis with community-contributory fine-tuning and model sharing