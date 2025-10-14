# Sequential Fine-Tuning Integration Plan

**Status**: In Progress
**Date**: 2025-10-13
**Updated**: 2025-10-14
**Goal**: Transform single-stage training pipeline into mandatory 2-stage sequential fine-tuning using public datasets (Stage 1) and WebAuthn-specific data (Stage 2)

## Important Implementation Guidelines

1. **Keep Single-Stage Methods**: Retain existing single-stage training methods in `MLXTrainer` (e.g., `train()`) for stage-specific testing. These will be used by `train_stage1()` and `train_stage2()` internally.

2. **No Backwards Compatibility**: Do NOT try to maintain backwards compatibility with old manifest versions or directory structures. Refactor/remove existing code as needed. The old v1.0 manifest format can be completely replaced with v2.0 - no need to support both.

---

## Table of Contents
1. [Overview](#overview)
2. [Current Architecture](#current-architecture)
3. [Proposed Sequential Architecture](#proposed-sequential-architecture)
4. [Implementation Phases](#implementation-phases)
5. [Code Changes](#code-changes)
6. [Testing Strategy](#testing-strategy)
7. [Expected Results](#expected-results)

---

## Overview

### Objective
Replace the current single-stage fine-tuning pipeline with a **mandatory 2-stage sequential pipeline** that:
- **Stage 1**: Trains on public vulnerability datasets (CrossVul + CVEfixes) from HuggingFace to build general security knowledge
- **Stage 2**: Specializes on WebAuthn-specific security tool findings with catastrophic forgetting prevention

**Key Principle**: No optional flags or customization. Sequential training is the only behavior.

### Why Sequential Training?

**Problem**: Single-stage training on small WebAuthn-specific datasets (50-200 examples) produces models with limited security knowledge.

**Solution**: Sequential fine-tuning builds expertise progressively:
1. **Stage 1** learns broad security patterns from 22K+ real-world vulnerability fixes
2. **Stage 2** specializes this knowledge for WebAuthn/FIDO2 while preserving general security understanding

**Benefits**:
- Better generalization across 158+ CWE types
- Stronger understanding of real-world CVE patterns
- Domain specialization without catastrophic forgetting
- Production-ready models with comprehensive security knowledge

---

## Current Architecture

### Training Run Directory Structure

Currently, each training run creates this structure:

```
~/shared-olmo-models/fine-tuned/webauthn-security-YYYYMMDD_HHMMSS/
├── run-manifest.json          # Training metadata (version 1.0)
├── adapters/                  # MLX LoRA adapters
│   ├── adapters.safetensors   # Final trained adapter
│   ├── adapter_config.json    # LoRA configuration
│   ├── training_metadata.json # Hyperparameters, timestamps
│   └── 0000XXX_adapters.safetensors  # Checkpoints (every 100 iters)
├── training-data/             # MLX-formatted training data
│   ├── train.jsonl           # Training examples (ChatML format)
│   └── valid.jsonl           # Validation examples (ChatML format)
└── evaluation/                # Test results
    ├── evaluation_results.json    # Metrics (exact match, CodeBLEU)
    └── model_evaluation/          # Per-test-case debug outputs
```

### Current Manifest Schema (v1.0)

```json
{
  "version": "1.0",
  "run_id": "webauthn-security-20251009_150359",
  "timestamp": "2025-10-09T15:03:59.301730",
  "base_model": "OLMo-2-1B-Instruct-mlx-q4",
  "training_params": {
    "learning_rate": 5e-06,
    "batch_size": 1,
    "num_iters": 800,
    "quality_weight_multiplier": 2.5
  },
  "adapters_path": "./adapters",
  "training_data_path": "./training-data",
  "evaluation_results_path": "./evaluation"
}
```

### Key Components

1. **TrainingRunManager** (`training_run_manager.py`):
   - Creates structured training run directories
   - Manages manifest files (JSON metadata)
   - Provides property accessors for paths (`adapters_path`, `training_data_path`, etc.)
   - Handles evaluation integration

2. **MLXTrainer** (`mlx_trainer.py`):
   - Executes MLX LoRA fine-tuning via `python -m mlx_lm lora`
   - Applies quality-weighted sampling (2.5x duplication of high-quality examples)
   - Manages training data preparation (rename to train.jsonl/valid.jsonl for MLX)
   - Saves training metadata

3. **process_artifacts.py**:
   - Orchestrates full pipeline: parsing → datasets → training → upload
   - Parses security tool outputs (Trivy, Semgrep, OSV, ZAP, Checkov)
   - Generates training data with tool-specific prompts
   - Applies data augmentation (semantic variations, self-mixup)
   - Trains model and evaluates on test set
   - Uploads to HuggingFace

### Current Pipeline Flow

```
User runs: python3 process_artifacts.py --artifacts-dir <dir> --output-dir results

Step 1: Parse vulnerabilities from security tools
  ↓ (parsed_vulnerabilities.json)

Step 2: Construct datasets (generate fixes, augment, split 80/10/10)
  ↓ (train_dataset.jsonl, validation_dataset.jsonl, test_dataset.jsonl)

Step 3: Train model (MLX LoRA with quality-weighted sampling)
  ↓ (adapters/, training-data/)

Step 4: Evaluate model on test set
  ↓ (evaluation_results.json)

Step 5: Upload to HuggingFace (model + datasets)
  ↓ (model_url, dataset_url)
```

---

## Proposed Sequential Architecture

### New Training Run Directory Structure

```
~/shared-olmo-models/fine-tuned/webauthn-security-sequential-YYYYMMDD_HHMMSS/
├── run-manifest.json          # Updated manifest (version 2.0)
│
├── stage1/                    # Stage 1: General Security Education
│   ├── adapters/
│   │   ├── adapters.safetensors
│   │   ├── adapter_config.json
│   │   ├── training_metadata.json
│   │   └── 0000XXX_adapters.safetensors  # Checkpoints
│   ├── training-data/
│   │   ├── train.jsonl       # CrossVul + CVEfixes (~17,840 examples)
│   │   └── valid.jsonl       # (~2,230 examples)
│   └── evaluation/
│       ├── evaluation_results.json
│       └── model_evaluation/
│
├── stage2/                    # Stage 2: WebAuthn Specialization
│   ├── adapters/
│   │   ├── adapters.safetensors
│   │   ├── adapter_config.json
│   │   ├── training_metadata.json
│   │   └── 0000XXX_adapters.safetensors  # Checkpoints
│   ├── training-data/
│   │   ├── train.jsonl       # WebAuthn tools + 15% Stage 1 replay
│   │   └── valid.jsonl       # WebAuthn validation set
│   └── evaluation/
│       ├── evaluation_results.json
│       └── model_evaluation/
│
└── final-model/               # Optional: Merged Stage 2 model for inference
    └── [merged model files]
```

### New Manifest Schema (v2.0)

```json
{
  "version": "2.0",
  "run_id": "webauthn-security-sequential-20251013_143000",
  "timestamp": "2025-10-13T14:30:00.000000",
  "base_model": "OLMo-2-1B-Instruct-mlx-q4",
  "pipeline_type": "sequential",

  "stage1": {
    "adapters_path": "./stage1/adapters",
    "training_data_path": "./stage1/training-data",
    "evaluation_results_path": "./stage1/evaluation",
    "training_params": {
      "learning_rate": 2e-05,
      "batch_size": 1,
      "num_iters": 5000,
      "quality_weight_multiplier": 2.5
    },
    "dataset_stats": {
      "sources": ["crossvul", "cvefixes"],
      "total_examples": 22300,
      "train_examples": 17840,
      "validation_examples": 2230,
      "test_examples": 2230
    }
  },

  "stage2": {
    "adapters_path": "./stage2/adapters",
    "training_data_path": "./stage2/training-data",
    "evaluation_results_path": "./stage2/evaluation",
    "training_params": {
      "learning_rate": 4e-06,
      "batch_size": 1,
      "num_iters": 1600,
      "quality_weight_multiplier": 2.5,
      "resume_from_stage1": true,
      "stage1_replay_ratio": 0.15
    },
    "dataset_stats": {
      "sources": ["webauthn_security_tools", "stage1_replay"],
      "webauthn_examples": 150,
      "stage1_replay_examples": 22,
      "total_train_examples": 172
    }
  },

  "final_model_path": "./final-model"
}
```

### Sequential Pipeline Flow

```
User runs: python3 process_artifacts.py --artifacts-dir <dir> --output-dir results

══════════════════════════════════════════════════════════════════════════════
STAGE 1: GENERAL SECURITY EDUCATION
══════════════════════════════════════════════════════════════════════════════

Step 1.1: Load public datasets from HuggingFace
  - Load hitoshura25/crossvul (9,313 examples)
  - Load hitoshura25/cvefixes (12,987 examples)
  - Transform to ChatML format
  ↓ (22,300 training pairs)

Step 1.2: Split and save Stage 1 datasets (80/10/10)
  ↓ (stage1/training-data/train.jsonl, valid.jsonl)
  ↓ (stage1_test.jsonl - saved separately for retention testing)

Step 1.3: Train Stage 1 model
  - Train on CrossVul + CVEfixes
  - 5,000 iterations, learning_rate=2e-5
  ↓ (stage1/adapters/adapters.safetensors)

Step 1.4: Evaluate Stage 1 model
  - Test on CrossVul/CVEfixes holdout set
  - Baseline for knowledge retention
  ↓ (stage1/evaluation/evaluation_results.json)

══════════════════════════════════════════════════════════════════════════════
STAGE 2: WEBAUTHN DOMAIN SPECIALIZATION
══════════════════════════════════════════════════════════════════════════════

Step 2.1: Parse WebAuthn security artifacts
  - Parse Trivy, Semgrep, OSV, ZAP, Checkov findings
  ↓ (parsed_vulnerabilities.json)

Step 2.2: Generate WebAuthn-specific training data
  - Create tool-specific prompts and fixes
  - Apply data augmentation
  - Split 80/10/10
  ↓ (stage2_base_train.jsonl, stage2_validation.jsonl, stage2_test.jsonl)

Step 2.3: Mix with 15% Stage 1 replay (catastrophic forgetting prevention)
  - Randomly sample 15% of Stage 1 training data
  - Combine with Stage 2 data and shuffle
  ↓ (stage2/training-data/train.jsonl, valid.jsonl)

Step 2.4: Train Stage 2 model (resume from Stage 1)
  - Resume from stage1/adapters/adapters.safetensors
  - 1,600 iterations, learning_rate=4e-6 (0.2x Stage 1)
  ↓ (stage2/adapters/adapters.safetensors)

Step 2.5: Evaluate Stage 2 model on WebAuthn test set
  ↓ (stage2/evaluation/evaluation_results.json)

Step 2.6: Verify Stage 1 knowledge retention
  - Re-test Stage 2 model on Stage 1 test set
  - Calculate retention rate vs Stage 1 baseline
  ↓ (Retention metrics logged)

══════════════════════════════════════════════════════════════════════════════
UPLOAD TO HUGGINGFACE
══════════════════════════════════════════════════════════════════════════════

Step 3: Upload final model and datasets
  - Upload stage2/adapters/ as final model
  - Upload all datasets with metadata
  ↓ (HuggingFace URLs)
```

---

## Implementation Phases

### Phase 1: Create Public Dataset Loader

**New File**: `security-ai-analysis/public_dataset_loader.py`

**Purpose**: Load CrossVul and CVEfixes datasets from HuggingFace and transform to ChatML format.

**Key Features**:
- Automatic HuggingFace download (no local storage)
- Streaming support for large CVEfixes dataset (5GB)
- Transform raw vulnerability records to ChatML format
- Metadata preservation for quality tracking

**Implementation**:

```python
#!/usr/bin/env python3
"""
Public Vulnerability Dataset Loader

Loads CrossVul and CVEfixes datasets from HuggingFace Hub and transforms
them into MLX-compatible ChatML format for Stage 1 training.
"""

import logging
import random
from typing import List, Dict, Any, Optional
from datasets import load_dataset

logger = logging.getLogger(__name__)


class PublicDatasetLoader:
    """Loads public vulnerability datasets from HuggingFace"""

    def __init__(self):
        """Initialize dataset loader"""
        self.crossvul_dataset_id = "hitoshura25/crossvul"
        self.cvefixes_dataset_id = "hitoshura25/cvefixes"

    def load_crossvul(self, max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load CrossVul dataset from HuggingFace.

        CrossVul contains 9,313 vulnerability/fix pairs across 158 CWE types
        and 21 programming languages.

        Raw format (from HuggingFace):
        {
            "cwe_id": "CWE-79",
            "cwe_description": "Cross-site Scripting (XSS) - ...",
            "language": "javascript",
            "vulnerable_code": "... code with vulnerability ...",
            "fixed_code": "... patched code ...",
            "file_pair_id": "79_123",
            "source": "crossvul",
            "language_dir": "javascript"
        }

        Transforms to ChatML format:
        {
            "messages": [
                {"role": "system", "content": "You are a security expert..."},
                {"role": "user", "content": "Fix CWE-XX in {language}:\n{vulnerable_code}"},
                {"role": "assistant", "content": "{fixed_code}"}
            ],
            "metadata": {
                "quality": "high",
                "source": "crossvul",
                "cwe_id": "CWE-XX",
                "language": "...",
                "chat_template": "chatml"
            }
        }

        Args:
            max_examples: Optional limit on number of examples (for testing)

        Returns:
            List of training pairs in ChatML format
        """
        logger.info(f"📥 Loading CrossVul dataset from HuggingFace: {self.crossvul_dataset_id}")

        # Load dataset from HuggingFace Hub
        dataset = load_dataset(self.crossvul_dataset_id, split="train")

        logger.info(f"   Total examples in dataset: {len(dataset)}")

        training_pairs = []
        for idx, example in enumerate(dataset):
            if max_examples and idx >= max_examples:
                logger.info(f"   Limiting to {max_examples} examples for testing")
                break

            # Transform to ChatML format
            training_pair = self._crossvul_to_chatml(example)
            training_pairs.append(training_pair)

        logger.info(f"   ✅ Loaded {len(training_pairs)} CrossVul examples")
        return training_pairs

    def load_cvefixes(self, max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load CVEfixes dataset from HuggingFace (5GB, uses streaming).

        CVEfixes contains 12,987 CVE fixes with metadata from 4,205 repositories.

        Uses streaming mode to avoid loading entire 5GB dataset into memory.

        Args:
            max_examples: Optional limit on number of examples (for testing)

        Returns:
            List of training pairs in ChatML format
        """
        logger.info(f"📥 Loading CVEfixes dataset from HuggingFace (streaming): {self.cvefixes_dataset_id}")

        # Use streaming=True for large dataset
        dataset = load_dataset(self.cvefixes_dataset_id, split="train", streaming=True)

        training_pairs = []
        for idx, example in enumerate(dataset):
            if max_examples and idx >= max_examples:
                logger.info(f"   Limiting to {max_examples} examples for testing")
                break

            # Transform to ChatML format (skip if no usable code diff)
            training_pair = self._cvefixes_to_chatml(example)
            if training_pair:
                training_pairs.append(training_pair)

            # Log progress every 1000 examples (streaming can be slow)
            if (idx + 1) % 1000 == 0:
                logger.info(f"   Processed {idx + 1} examples...")

        logger.info(f"   ✅ Loaded {len(training_pairs)} CVEfixes examples")
        return training_pairs

    def load_all_public_datasets(self,
                                 max_crossvul: Optional[int] = None,
                                 max_cvefixes: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load both CrossVul and CVEfixes datasets.

        Args:
            max_crossvul: Optional limit for CrossVul examples
            max_cvefixes: Optional limit for CVEfixes examples

        Returns:
            Combined and shuffled list of training pairs
        """
        logger.info("📚 Loading all public datasets for Stage 1 training...")

        # Load CrossVul
        crossvul_data = self.load_crossvul(max_examples=max_crossvul)

        # Load CVEfixes
        cvefixes_data = self.load_cvefixes(max_examples=max_cvefixes)

        # Combine datasets
        combined = crossvul_data + cvefixes_data

        # Shuffle to mix both datasets
        random.shuffle(combined)

        logger.info(f"✅ Total public dataset examples: {len(combined)}")
        logger.info(f"   - CrossVul: {len(crossvul_data)}")
        logger.info(f"   - CVEfixes: {len(cvefixes_data)}")

        return combined

    def _crossvul_to_chatml(self, example: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform CrossVul record to ChatML format.

        Args:
            example: Raw CrossVul record

        Returns:
            ChatML-formatted training pair
        """
        # Create language-specific system prompt
        system_prompt = self._create_security_system_prompt(example['language'])

        # Create user prompt with vulnerability context
        user_prompt = f"""Fix {example['cwe_id']} in {example['language']}:

CWE: {example['cwe_description']}

Vulnerable Code:
```{example['language']}
{example['vulnerable_code']}
```

Provide the fixed code."""

        # Create assistant response with fixed code
        assistant_response = f"""Fixed Code:
```{example['language']}
{example['fixed_code']}
```

**Explanation**: This fix addresses {example['cwe_id']} by implementing proper security controls."""

        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response}
            ],
            "metadata": {
                "quality": "high",
                "source": "crossvul",
                "cwe_id": example['cwe_id'],
                "language": example['language'],
                "file_pair_id": example.get('file_pair_id', 'unknown'),
                "chat_template": "chatml",
                "security_framework": "general-security-education"
            }
        }

    def _cvefixes_to_chatml(self, example: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform CVEfixes record to ChatML format.

        Note: CVEfixes records vary in structure. This method extracts
        code diffs and CVE metadata when available.

        Args:
            example: Raw CVEfixes record

        Returns:
            ChatML-formatted training pair, or None if no usable code diff
        """
        # TODO: Implement CVEfixes transformation
        # CVEfixes records contain:
        # - CVE ID and description
        # - CVSS scores
        # - CWE classification
        # - Git commit diffs
        # - Repository metadata

        # Extract relevant fields and transform to ChatML
        # Return None if no usable code diff is present

        # Placeholder implementation
        return None

    def _create_security_system_prompt(self, language: str) -> str:
        """
        Create language-specific system prompt for security fixes.

        Args:
            language: Programming language

        Returns:
            System prompt
        """
        return f"""You are a security expert specializing in {language} code analysis and vulnerability remediation.

Your task is to identify security vulnerabilities and provide corrected code that eliminates the vulnerability while preserving functionality.

Guidelines:
- Provide minimal, focused fixes
- Use appropriate security libraries and patterns
- Include brief explanations of the fix
- Preserve code functionality
- Follow {language} best practices"""
```

**Testing**:
```bash
# Test CrossVul loading
python3 -c "
from public_dataset_loader import PublicDatasetLoader
loader = PublicDatasetLoader()
data = loader.load_crossvul(max_examples=10)
print(f'Loaded {len(data)} examples')
print('Sample:', data[0]['messages'][0]['role'])
"

# Test CVEfixes loading (with limit for speed)
python3 -c "
from public_dataset_loader import PublicDatasetLoader
loader = PublicDatasetLoader()
data = loader.load_cvefixes(max_examples=10)
print(f'Loaded {len(data)} examples')
"
```

---

### Phase 2: Update Training Run Manager

**File**: `security-ai-analysis/training_run_manager.py`

**Changes**:
1. Update `RunManifest` dataclass to version 2.0 with stage1/stage2 structure
2. Add `SequentialStageManifest` dataclass for per-stage metadata
3. Add `create_sequential_run()` method
4. Add property accessors for stage1/stage2 paths

**Implementation**:

```python
# Add new dataclass for stage-specific manifest
@dataclass
class SequentialStageManifest:
    """Metadata for a single training stage (Stage 1 or Stage 2)"""
    adapters_path: str
    training_data_path: str
    evaluation_results_path: str
    training_params: Dict[str, Any] = None
    dataset_stats: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize empty dicts if not provided"""
        if self.training_params is None:
            self.training_params = {}
        if self.dataset_stats is None:
            self.dataset_stats = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "adapters_path": self.adapters_path,
            "training_data_path": self.training_data_path,
            "evaluation_results_path": self.evaluation_results_path,
            "training_params": self.training_params,
            "dataset_stats": self.dataset_stats
        }


# Update RunManifest to support sequential training
@dataclass
class RunManifest:
    """Training run manifest schema - Version 2.0 for sequential training"""
    version: str = "2.0"
    run_id: str = ""
    timestamp: str = ""
    base_model: str = ""
    pipeline_type: str = "sequential"  # Always "sequential" (no other options)

    # Stage 1: General Security Education (CrossVul + CVEfixes)
    stage1: Optional[SequentialStageManifest] = None

    # Stage 2: WebAuthn Domain Specialization
    stage2: Optional[SequentialStageManifest] = None

    # Final merged model path (optional)
    final_model_path: str = "./final-model"

    # Legacy fields (kept for compatibility with loading old manifests if needed)
    training_params: Dict[str, Any] = None
    adapters_path: Optional[str] = None
    training_data_path: Optional[str] = None
    evaluation_results_path: Optional[str] = None

    def __post_init__(self):
        """Initialize stage manifests if not provided"""
        if self.stage1 is None:
            self.stage1 = SequentialStageManifest(
                adapters_path="./stage1/adapters",
                training_data_path="./stage1/training-data",
                evaluation_results_path="./stage1/evaluation"
            )
        if self.stage2 is None:
            self.stage2 = SequentialStageManifest(
                adapters_path="./stage2/adapters",
                training_data_path="./stage2/training-data",
                evaluation_results_path="./stage2/evaluation"
            )
        if self.training_params is None:
            self.training_params = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "base_model": self.base_model,
            "pipeline_type": self.pipeline_type,
            "stage1": self.stage1.to_dict() if self.stage1 else None,
            "stage2": self.stage2.to_dict() if self.stage2 else None,
            "final_model_path": self.final_model_path,
        }
```

**Add property accessors to TrainingRun class**:

```python
class TrainingRun:
    # Existing properties remain unchanged...

    # Add Stage 1 property accessors
    @property
    def stage1_adapters_path(self) -> Path:
        """Get path to Stage 1 adapter artifacts"""
        if self.manifest.stage1 is None:
            raise ValueError("Stage 1 manifest not configured")
        return self.run_dir / self.manifest.stage1.adapters_path

    @property
    def stage1_training_data_path(self) -> Path:
        """Get path to Stage 1 training data directory"""
        if self.manifest.stage1 is None:
            raise ValueError("Stage 1 manifest not configured")
        return self.run_dir / self.manifest.stage1.training_data_path

    @property
    def stage1_evaluation_path(self) -> Path:
        """Get path to Stage 1 evaluation results directory"""
        if self.manifest.stage1 is None:
            raise ValueError("Stage 1 manifest not configured")
        return self.run_dir / self.manifest.stage1.evaluation_results_path

    # Add Stage 2 property accessors
    @property
    def stage2_adapters_path(self) -> Path:
        """Get path to Stage 2 adapter artifacts"""
        if self.manifest.stage2 is None:
            raise ValueError("Stage 2 manifest not configured")
        return self.run_dir / self.manifest.stage2.adapters_path

    @property
    def stage2_training_data_path(self) -> Path:
        """Get path to Stage 2 training data directory"""
        if self.manifest.stage2 is None:
            raise ValueError("Stage 2 manifest not configured")
        return self.run_dir / self.manifest.stage2.training_data_path

    @property
    def stage2_evaluation_path(self) -> Path:
        """Get path to Stage 2 evaluation results directory"""
        if self.manifest.stage2 is None:
            raise ValueError("Stage 2 manifest not configured")
        return self.run_dir / self.manifest.stage2.evaluation_results_path

    @property
    def final_model_path(self) -> Path:
        """Get path to final merged model"""
        return self.run_dir / self.manifest.final_model_path
```

**Add create_sequential_run() method to TrainingRunManager**:

```python
class TrainingRunManager:
    def create_sequential_run(self, run_id: Optional[str] = None) -> TrainingRun:
        """
        Create new sequential training run with stage1/stage2 structure.

        Args:
            run_id: Optional run ID (defaults to timestamp)

        Returns:
            TrainingRun instance with sequential manifest
        """
        # Generate run ID if not provided
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Note the "sequential" prefix in run directory name
        run_dir = self.fine_tuned_models_dir / f"webauthn-security-sequential-{run_id}"

        if run_dir.exists():
            logger.warning(f"Training run directory already exists: {run_dir}")

        # Create training run instance
        training_run = TrainingRun(run_dir)

        # Create manifest with stage1/stage2 structure
        manifest = RunManifest(
            version="2.0",
            run_id=f"webauthn-security-sequential-{run_id}",
            timestamp=datetime.now().isoformat(),
            base_model=self.config.default_base_model,
            pipeline_type="sequential",
            stage1=SequentialStageManifest(
                adapters_path="./stage1/adapters",
                training_data_path="./stage1/training-data",
                evaluation_results_path="./stage1/evaluation",
                training_params={},
                dataset_stats={}
            ),
            stage2=SequentialStageManifest(
                adapters_path="./stage2/adapters",
                training_data_path="./stage2/training-data",
                evaluation_results_path="./stage2/evaluation",
                training_params={},
                dataset_stats={}
            ),
            final_model_path="./final-model"
        )

        training_run._manifest = manifest
        training_run.save_manifest()

        logger.info(f"🚀 Created sequential training run: {run_id}")
        logger.info(f"   Directory: {run_dir}")
        logger.info(f"   Stage 1 adapters: {training_run.stage1_adapters_path}")
        logger.info(f"   Stage 2 adapters: {training_run.stage2_adapters_path}")

        return training_run
```

**Update _load_manifest() to handle v2.0**:

```python
def _load_manifest(self) -> RunManifest:
    """Load manifest from JSON file (v2.0 only)"""
    if not self.manifest_path.exists():
        raise FileNotFoundError(f"Run manifest not found: {self.manifest_path}")

    try:
        with open(self.manifest_path, 'r') as f:
            manifest_data = json.load(f)

        logger.info(f"📋 Loaded manifest for run: {manifest_data.get('run_id', 'unknown')}")

        # Load sequential manifest (v2.0)
        stage1_data = manifest_data.get("stage1", {})
        stage2_data = manifest_data.get("stage2", {})

        manifest = RunManifest(
            version="2.0",
            run_id=manifest_data.get("run_id", ""),
            timestamp=manifest_data.get("timestamp", ""),
            base_model=manifest_data.get("base_model", ""),
            pipeline_type=manifest_data.get("pipeline_type", "sequential"),
            stage1=SequentialStageManifest(
                adapters_path=stage1_data.get("adapters_path", "./stage1/adapters"),
                training_data_path=stage1_data.get("training_data_path", "./stage1/training-data"),
                evaluation_results_path=stage1_data.get("evaluation_results_path", "./stage1/evaluation"),
                training_params=stage1_data.get("training_params", {}),
                dataset_stats=stage1_data.get("dataset_stats", {})
            ),
            stage2=SequentialStageManifest(
                adapters_path=stage2_data.get("adapters_path", "./stage2/adapters"),
                training_data_path=stage2_data.get("training_data_path", "./stage2/training-data"),
                evaluation_results_path=stage2_data.get("evaluation_results_path", "./stage2/evaluation"),
                training_params=stage2_data.get("training_params", {}),
                dataset_stats=stage2_data.get("dataset_stats", {})
            ),
            final_model_path=manifest_data.get("final_model_path", "./final-model")
        )

        return manifest

    except (json.JSONDecodeError, TypeError, KeyError) as e:
        raise ValueError(f"Invalid manifest format in {self.manifest_path}: {e}")
```

---

### Phase 3: Extend MLX Trainer for Sequential Training

**File**: `security-ai-analysis/mlx_trainer.py`

**Changes**:
1. Add `train_stage1()` method for Stage 1 training
2. Add `train_stage2()` method for Stage 2 training with resume
3. Add `run_mlx_training_with_resume()` for `--resume-adapter-file` support

**Implementation**:

```python
class MLXTrainer:
    # Existing __init__ and methods remain unchanged...

    def train_stage1(self,
                     training_run: TrainingRun,
                     stage1_train_dataset: Path,
                     stage1_validation_dataset: Path) -> Path:
        """
        Train Stage 1: General Security Education.

        Uses CrossVul + CVEfixes datasets for broad security knowledge.

        Args:
            training_run: TrainingRun instance with stage1 paths
            stage1_train_dataset: Path to Stage 1 training dataset (JSONL)
            stage1_validation_dataset: Path to Stage 1 validation dataset (JSONL)

        Returns:
            Path to trained Stage 1 adapter
        """
        logger.info("=" * 80)
        logger.info("🎓 STAGE 1 TRAINING: General Security Education")
        logger.info("=" * 80)

        # Prepare stage1 training data directory
        stage1_data_dir = training_run.stage1_training_data_path
        stage1_data_dir.mkdir(parents=True, exist_ok=True)

        # Copy datasets to stage1/training-data/
        logger.info(f"📂 Preparing Stage 1 training data: {stage1_data_dir}")
        shutil.copy2(stage1_train_dataset, stage1_data_dir / "train.jsonl")
        shutil.copy2(stage1_validation_dataset, stage1_data_dir / "valid.jsonl")

        logger.info(f"   train.jsonl: {(stage1_data_dir / 'train.jsonl').stat().st_size} bytes")
        logger.info(f"   valid.jsonl: {(stage1_data_dir / 'valid.jsonl').stat().st_size} bytes")

        # Update trainer configuration for Stage 1
        self.output_dir = training_run.stage1_adapters_path
        self.num_iters = self.config.fine_tuning.max_stage1_iters
        self.learning_rate = self.config.fine_tuning.learning_rate

        logger.info(f"🔧 Stage 1 Training Configuration:")
        logger.info(f"   Iterations: {self.num_iters}")
        logger.info(f"   Learning Rate: {self.learning_rate}")
        logger.info(f"   Batch Size: {self.batch_size}")
        logger.info(f"   Output: {self.output_dir}")

        # Apply quality-weighted sampling and train
        adapter_path = self.train(training_data_dir=stage1_data_dir)

        logger.info(f"✅ Stage 1 training complete: {adapter_path}")
        return adapter_path

    def train_stage2(self,
                     training_run: TrainingRun,
                     stage2_train_dataset: Path,
                     stage2_validation_dataset: Path,
                     stage1_adapter_path: Path) -> Path:
        """
        Train Stage 2: WebAuthn Domain Specialization.

        Uses WebAuthn security tool findings + 15% Stage 1 replay data.
        Resumes training from Stage 1 adapter.

        Args:
            training_run: TrainingRun instance with stage2 paths
            stage2_train_dataset: Path to Stage 2 training dataset (JSONL, already mixed with replay)
            stage2_validation_dataset: Path to Stage 2 validation dataset (JSONL)
            stage1_adapter_path: Path to Stage 1 adapter directory (for --resume-adapter-file)

        Returns:
            Path to trained Stage 2 adapter
        """
        logger.info("=" * 80)
        logger.info("🔧 STAGE 2 TRAINING: WebAuthn Domain Specialization")
        logger.info("=" * 80)

        # Verify Stage 1 adapter exists
        stage1_adapter_file = stage1_adapter_path / "adapters.safetensors"
        if not stage1_adapter_file.exists():
            raise FileNotFoundError(f"Stage 1 adapter not found: {stage1_adapter_file}")

        logger.info(f"📋 Resuming from Stage 1 adapter: {stage1_adapter_file}")

        # Prepare stage2 training data directory
        stage2_data_dir = training_run.stage2_training_data_path
        stage2_data_dir.mkdir(parents=True, exist_ok=True)

        # Copy datasets to stage2/training-data/
        logger.info(f"📂 Preparing Stage 2 training data: {stage2_data_dir}")
        shutil.copy2(stage2_train_dataset, stage2_data_dir / "train.jsonl")
        shutil.copy2(stage2_validation_dataset, stage2_data_dir / "valid.jsonl")

        logger.info(f"   train.jsonl: {(stage2_data_dir / 'train.jsonl').stat().st_size} bytes")
        logger.info(f"   valid.jsonl: {(stage2_data_dir / 'valid.jsonl').stat().st_size} bytes")

        # Update trainer configuration for Stage 2
        self.output_dir = training_run.stage2_adapters_path
        self.num_iters = self.config.fine_tuning.max_stage2_iters
        self.learning_rate = self.config.fine_tuning.learning_rate * 0.2  # Reduced LR for Stage 2

        logger.info(f"🔧 Stage 2 Training Configuration:")
        logger.info(f"   Iterations: {self.num_iters}")
        logger.info(f"   Learning Rate: {self.learning_rate} (0.2x Stage 1)")
        logger.info(f"   Batch Size: {self.batch_size}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info(f"   Resume from: {stage1_adapter_file}")

        # Train with resume-adapter-file from Stage 1
        adapter_path = self.run_mlx_training_with_resume(
            mlx_data_dir=stage2_data_dir,
            resume_adapter_path=stage1_adapter_path
        )

        logger.info(f"✅ Stage 2 training complete: {adapter_path}")
        return adapter_path

    def run_mlx_training_with_resume(self,
                                     mlx_data_dir: Path,
                                     resume_adapter_path: Path) -> Path:
        """
        Execute MLX LoRA fine-tuning with --resume-adapter-file.

        This allows Stage 2 training to build upon Stage 1's learned weights.

        Args:
            mlx_data_dir: Directory containing train.jsonl and valid.jsonl
            resume_adapter_path: Path to adapter directory to resume from

        Returns:
            Path to trained adapter directory
        """
        logger.info("🚀 Starting MLX LoRA fine-tuning with adapter resume...")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Verify resume adapter file exists
        resume_adapter_file = resume_adapter_path / "adapters.safetensors"
        if not resume_adapter_file.exists():
            raise FileNotFoundError(f"Resume adapter file not found: {resume_adapter_file}")

        # Build MLX LoRA command with --resume-adapter-file
        command = [
            "python", "-m", "mlx_lm", "lora",
            "--model", str(self.base_model_path),
            "--train",
            "--data", str(mlx_data_dir),
            "--adapter-path", str(self.output_dir),
            "--resume-adapter-file", str(resume_adapter_file),  # KEY: Resume from Stage 1
            "--batch-size", str(self.batch_size),
            "--iters", str(self.num_iters),
            "--learning-rate", str(self.learning_rate),
            "--fine-tune-type", "lora",
            "--optimizer", "adamw"
        ]

        logger.info(f"   Command: {' '.join(command)}")
        logger.info(f"   Base model: {self.base_model_path}")
        logger.info(f"   Training data: {mlx_data_dir}")
        logger.info(f"   Resume adapter: {resume_adapter_file}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info(f"   Iterations: {self.num_iters}")
        logger.info(f"   Batch size: {self.batch_size}")
        logger.info(f"   Learning rate: {self.learning_rate}")

        try:
            # Execute MLX training
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )

            # Log training output
            if result.stdout:
                logger.debug(f"Training output:\n{result.stdout}")

            return self.output_dir

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ MLX training failed with exit code {e.returncode}")
            logger.error(f"   stdout: {e.stdout}")
            logger.error(f"   stderr: {e.stderr}")
            raise RuntimeError(f"MLX training with resume failed: {e.stderr}")
```

---

### Phase 4: Refactor process_artifacts.py

**File**: `security-ai-analysis/process_artifacts.py`

**Major Changes**:
1. Replace `run_full_pipeline()` with `run_sequential_pipeline()`
2. Add `_mix_with_stage1_replay()` helper function
3. Remove all single-phase execution code paths
4. Integrate `PublicDatasetLoader` for Stage 1

**Key Functions to Add**:

```python
def run_sequential_pipeline(artifacts_dir: str, output_dir: Path, skip_upload: bool = False):
    """
    Execute mandatory 2-stage sequential fine-tuning pipeline.

    Stage 1: Train on public datasets (CrossVul + CVEfixes)
    Stage 2: Specialize on WebAuthn security tools (parsed artifacts)

    No optional behavior - this is the only execution path.
    """
    config = OLMoSecurityConfig()
    run_manager = TrainingRunManager(config)

    # Create sequential training run
    training_run = run_manager.create_sequential_run()

    logger.info("=" * 80)
    logger.info("🚀 SEQUENTIAL FINE-TUNING PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Run ID: {training_run.run_id}")
    logger.info(f"Run Directory: {training_run.run_dir}")
    logger.info("")
    logger.info("📋 Pipeline Stages:")
    logger.info("  Stage 1: General Security Education (CrossVul + CVEfixes)")
    logger.info("  Stage 2: WebAuthn Domain Specialization (Security Tools)")
    logger.info("=" * 80)

    # ========== STAGE 1: GENERAL SECURITY EDUCATION ==========
    logger.info("\n🎓 STAGE 1: General Security Education")
    logger.info("=" * 80)

    # Step 1.1: Load public datasets from HuggingFace
    from public_dataset_loader import PublicDatasetLoader

    logger.info("📥 Loading public datasets from HuggingFace...")
    public_loader = PublicDatasetLoader()
    stage1_training_pairs = public_loader.load_all_public_datasets()
    logger.info(f"   Loaded {len(stage1_training_pairs)} examples (CrossVul + CVEfixes)")

    # Step 1.2: Split Stage 1 datasets (80/10/10)
    logger.info("📊 Splitting Stage 1 datasets (80/10/10)...")
    stage1_train, stage1_val, stage1_test = _stratified_split_by_source(
        stage1_training_pairs, split_ratios=(0.8, 0.1, 0.1)
    )

    logger.info(f"   Train: {len(stage1_train)} examples")
    logger.info(f"   Validation: {len(stage1_val)} examples")
    logger.info(f"   Test: {len(stage1_test)} examples")

    # Save Stage 1 datasets
    stage1_output_dir = output_dir / "stage1_datasets"
    stage1_output_dir.mkdir(parents=True, exist_ok=True)
    stage1_train_file = stage1_output_dir / "train.jsonl"
    stage1_val_file = stage1_output_dir / "valid.jsonl"
    stage1_test_file = stage1_output_dir / "test.jsonl"

    _save_jsonl(stage1_train, stage1_train_file)
    _save_jsonl(stage1_val, stage1_val_file)
    _save_jsonl(stage1_test, stage1_test_file)

    logger.info(f"   Saved Stage 1 datasets to: {stage1_output_dir}")

    # Step 1.3: Train Stage 1 model
    logger.info("\n🚀 Training Stage 1 model...")
    trainer = MLXTrainer(config, output_dir=training_run.stage1_adapters_path)
    stage1_adapter_path = trainer.train_stage1(
        training_run=training_run,
        stage1_train_dataset=stage1_train_file,
        stage1_validation_dataset=stage1_val_file
    )

    # Update manifest with Stage 1 training params and dataset stats
    training_run.manifest.stage1.training_params = {
        "learning_rate": trainer.learning_rate,
        "batch_size": trainer.batch_size,
        "num_iters": trainer.num_iters,
        "quality_weight_multiplier": trainer.quality_weight_multiplier
    }
    training_run.manifest.stage1.dataset_stats = {
        "sources": ["crossvul", "cvefixes"],
        "total_examples": len(stage1_training_pairs),
        "train_examples": len(stage1_train),
        "validation_examples": len(stage1_val),
        "test_examples": len(stage1_test)
    }
    training_run.save_manifest()

    # Step 1.4: Evaluate Stage 1 model
    logger.info("\n🔬 Evaluating Stage 1 model...")
    stage1_eval_results = run_manager.evaluate(training_run, stage1_test_file)
    stage1_exact_match = stage1_eval_results['metrics']['exact_match_percentage']
    logger.info(f"   ✅ Stage 1 Exact Match: {stage1_exact_match:.2f}%")

    # ========== STAGE 2: WEBAUTHN SPECIALIZATION ==========
    logger.info("\n🔧 STAGE 2: WebAuthn Domain Specialization")
    logger.info("=" * 80)

    # Step 2.1: Parse WebAuthn security tool findings
    logger.info("🔍 Parsing WebAuthn security artifacts...")
    parsed_vulns_file = parse_vulnerabilities_phase(artifacts_dir, output_dir)

    # Step 2.2: Generate WebAuthn-specific training data
    logger.info("🔧 Generating WebAuthn-specific training data...")
    stage2_train_base, stage2_val, stage2_test = construct_datasets_phase(
        parsed_vulns_file, output_dir
    )

    logger.info(f"   WebAuthn train examples: {len(stage2_train_base)}")
    logger.info(f"   WebAuthn validation examples: {len(stage2_val)}")
    logger.info(f"   WebAuthn test examples: {len(stage2_test)}")

    # Step 2.3: Mix with 15% Stage 1 replay (catastrophic forgetting prevention)
    logger.info("\n🔀 Mixing Stage 2 data with 15% Stage 1 replay...")
    stage2_train_mixed = _mix_with_stage1_replay(
        stage2_train_base,
        stage1_train,
        replay_ratio=0.15
    )

    # Save Stage 2 datasets
    stage2_output_dir = output_dir / "stage2_datasets"
    stage2_output_dir.mkdir(parents=True, exist_ok=True)
    stage2_train_file = stage2_output_dir / "train.jsonl"
    stage2_val_file = stage2_output_dir / "valid.jsonl"
    stage2_test_file = stage2_output_dir / "test.jsonl"

    _save_jsonl(stage2_train_mixed, stage2_train_file)
    _save_jsonl(stage2_val, stage2_val_file)
    _save_jsonl(stage2_test, stage2_test_file)

    logger.info(f"   Saved Stage 2 datasets to: {stage2_output_dir}")

    # Step 2.4: Train Stage 2 model (resume from Stage 1)
    logger.info("\n🚀 Training Stage 2 model (resuming from Stage 1)...")
    stage2_adapter_path = trainer.train_stage2(
        training_run=training_run,
        stage2_train_dataset=stage2_train_file,
        stage2_validation_dataset=stage2_val_file,
        stage1_adapter_path=stage1_adapter_path
    )

    # Update manifest with Stage 2 training params and dataset stats
    training_run.manifest.stage2.training_params = {
        "learning_rate": trainer.learning_rate,
        "batch_size": trainer.batch_size,
        "num_iters": trainer.num_iters,
        "quality_weight_multiplier": trainer.quality_weight_multiplier,
        "resume_from_stage1": True,
        "stage1_replay_ratio": 0.15
    }
    training_run.manifest.stage2.dataset_stats = {
        "sources": ["webauthn_security_tools", "stage1_replay"],
        "webauthn_examples": len(stage2_train_base),
        "stage1_replay_examples": len(stage2_train_mixed) - len(stage2_train_base),
        "total_train_examples": len(stage2_train_mixed),
        "validation_examples": len(stage2_val),
        "test_examples": len(stage2_test)
    }
    training_run.save_manifest()

    # Step 2.5: Evaluate Stage 2 model on WebAuthn test set
    logger.info("\n🔬 Evaluating Stage 2 model on WebAuthn test set...")
    stage2_eval_results = run_manager.evaluate(training_run, stage2_test_file)
    stage2_exact_match = stage2_eval_results['metrics']['exact_match_percentage']
    logger.info(f"   ✅ Stage 2 Exact Match: {stage2_exact_match:.2f}%")

    # Step 2.6: Verify Stage 1 knowledge retention
    logger.info("\n🔍 Verifying Stage 1 knowledge retention...")
    logger.info("   Re-testing Stage 2 model on Stage 1 test set...")
    retention_results = run_manager.evaluate(training_run, stage1_test_file)
    retention_exact_match = retention_results['metrics']['exact_match_percentage']
    retention_rate = (retention_exact_match / stage1_exact_match) * 100 if stage1_exact_match > 0 else 0

    logger.info(f"   Stage 1 Baseline: {stage1_exact_match:.2f}%")
    logger.info(f"   Stage 2 on Stage 1 Test: {retention_exact_match:.2f}%")
    logger.info(f"   ✅ Knowledge Retention: {retention_rate:.1f}%")

    if retention_rate < 90:
        logger.warning(f"   ⚠️  Knowledge retention below 90% threshold!")
        logger.warning(f"   Consider increasing stage1_replay_ratio or reducing Stage 2 learning rate")

    # ========== UPLOAD ARTIFACTS ==========
    logger.info("\n📤 Uploading Artifacts to HuggingFace")
    logger.info("=" * 80)

    upload_results = upload_artifacts_phase(
        adapter_path=stage2_adapter_path,
        train_dataset=stage2_train_file,
        validation_dataset=stage2_val_file,
        test_dataset=stage2_test_file,
        skip_upload=skip_upload
    )

    # ========== PIPELINE COMPLETE ==========
    logger.info("\n" + "=" * 80)
    logger.info("✅ SEQUENTIAL PIPELINE COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Training Run: {training_run.run_dir}")
    logger.info("")
    logger.info("📊 Final Results:")
    logger.info("")
    logger.info("Stage 1 (General Security):")
    logger.info(f"  - Examples: {len(stage1_training_pairs)} (CrossVul + CVEfixes)")
    logger.info(f"  - Exact Match: {stage1_exact_match:.2f}%")
    logger.info(f"  - Adapters: {stage1_adapter_path}")
    logger.info("")
    logger.info("Stage 2 (WebAuthn Specialization):")
    logger.info(f"  - Examples: {len(stage2_train_mixed)} (WebAuthn + replay)")
    logger.info(f"  - Exact Match: {stage2_exact_match:.2f}%")
    logger.info(f"  - Knowledge Retention: {retention_rate:.1f}%")
    logger.info(f"  - Adapters: {stage2_adapter_path}")
    logger.info("")
    if upload_results.get("model_url"):
        logger.info(f"🔗 Model: {upload_results['model_url']}")
    if upload_results.get("dataset_url"):
        logger.info(f"🔗 Dataset: {upload_results['dataset_url']}")
    logger.info("=" * 80)


def _mix_with_stage1_replay(stage2_data: List[Dict],
                            stage1_data: List[Dict],
                            replay_ratio: float = 0.15) -> List[Dict]:
    """
    Mix Stage 2 data with Stage 1 replay for catastrophic forgetting prevention.

    This is a key technique for sequential fine-tuning: by replaying a portion
    of Stage 1 training data during Stage 2, we prevent the model from
    "forgetting" its general security knowledge while specializing on WebAuthn.

    Args:
        stage2_data: Stage 2 training examples (WebAuthn-specific)
        stage1_data: Stage 1 training examples (public datasets)
        replay_ratio: Fraction of Stage 1 data to replay (default: 0.15 = 15%)

    Returns:
        Mixed training dataset with Stage 2 + Stage 1 replay
    """
    logger.info(f"🔀 Mixing Stage 2 data with {replay_ratio * 100:.0f}% Stage 1 replay...")

    # Calculate how many Stage 1 examples to replay
    # Based on Stage 2 dataset size (not Stage 1 size)
    replay_count = int(len(stage2_data) * replay_ratio)

    # Randomly sample Stage 1 examples (without replacement)
    stage1_replay = random.sample(stage1_data, min(replay_count, len(stage1_data)))

    # Mark replay examples for tracking
    for example in stage1_replay:
        if 'metadata' not in example:
            example['metadata'] = {}
        example['metadata']['replay_from_stage1'] = True

    # Combine and shuffle
    mixed_data = stage2_data + stage1_replay
    random.shuffle(mixed_data)

    logger.info(f"   Stage 2 examples: {len(stage2_data)}")
    logger.info(f"   Stage 1 replay: {len(stage1_replay)} ({replay_ratio * 100:.1f}%)")
    logger.info(f"   Total mixed examples: {len(mixed_data)}")

    return mixed_data


def _stratified_split_by_source(training_pairs: List[Dict],
                                split_ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1)) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Split training pairs by source (crossvul vs cvefixes) with stratification.

    Ensures both CrossVul and CVEfixes are represented proportionally in
    train/validation/test sets.

    Args:
        training_pairs: List of training examples
        split_ratios: (train, val, test) ratios (default: 80/10/10)

    Returns:
        Tuple of (train_pairs, val_pairs, test_pairs)
    """
    # Group by source
    source_groups = {}
    for pair in training_pairs:
        source = pair.get('metadata', {}).get('source', 'unknown')
        if source not in source_groups:
            source_groups[source] = []
        source_groups[source].append(pair)

    train_pairs = []
    val_pairs = []
    test_pairs = []

    # Split each source proportionally
    for source, pairs in source_groups.items():
        random.shuffle(pairs)
        count = len(pairs)

        train_size = int(count * split_ratios[0])
        val_size = int(count * split_ratios[1])

        source_train = pairs[:train_size]
        source_val = pairs[train_size:train_size + val_size]
        source_test = pairs[train_size + val_size:]

        train_pairs.extend(source_train)
        val_pairs.extend(source_val)
        test_pairs.extend(source_test)

        logger.info(f"   {source}: {len(source_train)} train / {len(source_val)} val / {len(source_test)} test")

    # Shuffle combined sets
    random.shuffle(train_pairs)
    random.shuffle(val_pairs)
    random.shuffle(test_pairs)

    return train_pairs, val_pairs, test_pairs


def _save_jsonl(data: List[Dict], output_file: Path):
    """Save list of dictionaries to JSONL file"""
    with open(output_file, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')
```

**Update main() to use sequential pipeline**:

```python
def main():
    """
    Main orchestrator for the sequential fine-tuning pipeline.
    """
    parser = argparse.ArgumentParser(description="Sequential Fine-Tuning Pipeline for WebAuthn Security")
    parser.add_argument("--artifacts-dir", type=Path, required=True,
                       help="Directory containing security scan artifacts for Stage 2")
    parser.add_argument("--output-dir", type=Path, default=Path("results"),
                       help="Directory to save pipeline outputs")
    parser.add_argument("--skip-upload", action="store_true",
                       help="Skip HuggingFace upload (default: False)")

    args = parser.parse_args()

    # Ensure base model is ready
    config = OLMoSecurityConfig()
    if not ensure_base_model_ready(config):
        logger.error("❌ Cannot proceed: Base model setup failed")
        return 1

    # Run sequential pipeline (only execution path)
    run_sequential_pipeline(
        artifacts_dir=str(args.artifacts_dir),
        output_dir=args.output_dir,
        skip_upload=args.skip_upload
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

### Phase 5: Update Configuration

**File**: `config/olmo-security-config.yaml`

Add sequential training configuration:

```yaml
fine_tuning:
  workspace_dir: "security-ai-analysis/workspace"
  default_output_name: "webauthn-security-model"

  training:
    # Base training parameters
    learning_rate: 2.0e-5
    batch_size: 1
    max_epochs: 3
    warmup_steps: 100
    save_steps: 100      # Checkpoint frequency
    eval_steps: 250

    # Stage 1: Public datasets (general security education)
    max_stage1_iters: 5000
    stage1_learning_rate: 2.0e-5

    # Stage 2: WebAuthn specialization (domain-specific)
    max_stage2_iters: 1600
    stage2_learning_rate: 4.0e-6  # 0.2x Stage 1 (preserve knowledge)

    # Catastrophic forgetting prevention
    stage1_replay_ratio: 0.15  # 15% Stage 1 data replayed in Stage 2

  lora:
    rank: 8
    alpha: 16
    dropout: 0.05
    target_modules: ["q_proj", "v_proj"]

  mlx:
    quantization: "q4"
    memory_efficient: true
    gradient_checkpointing: true

  huggingface:
    upload_enabled: true
    default_repo_prefix: "hitoshura25"
    private_repos: false
    skip_in_daemon: false
    upload_staging_dir: "upload_staging"

  sequential:
    # Sequential training is ALWAYS enabled (no optional behavior)
    enabled: true
    stage1_sources: ['crossvul', 'cvefixes']
    stage2_sources: ['webauthn_security_tools']

    # Dataset limits (set to null for no limit)
    max_crossvul_examples: null
    max_cvefixes_examples: null
```

---

## Testing Strategy

### Unit Tests

1. **Test PublicDatasetLoader**:
```bash
python3 -c "
from public_dataset_loader import PublicDatasetLoader
loader = PublicDatasetLoader()

# Test CrossVul loading (small sample)
crossvul = loader.load_crossvul(max_examples=10)
assert len(crossvul) == 10
assert 'messages' in crossvul[0]
assert 'metadata' in crossvul[0]
print('✅ CrossVul loader test passed')

# Test CVEfixes loading (small sample)
cvefixes = loader.load_cvefixes(max_examples=10)
assert len(cvefixes) <= 10  # May be less if some records skipped
print('✅ CVEfixes loader test passed')
"
```

2. **Test Sequential Run Creation**:
```bash
python3 -c "
from config_manager import OLMoSecurityConfig
from training_run_manager import TrainingRunManager

config = OLMoSecurityConfig()
manager = TrainingRunManager(config)

# Create sequential run
run = manager.create_sequential_run()
assert run.manifest.version == '2.0'
assert run.manifest.pipeline_type == 'sequential'
assert run.manifest.stage1 is not None
assert run.manifest.stage2 is not None

# Verify paths
assert 'stage1' in str(run.stage1_adapters_path)
assert 'stage2' in str(run.stage2_adapters_path)
print('✅ Sequential run creation test passed')
"
```

3. **Test Stage 1 Replay Mixing**:
```bash
python3 -c "
from process_artifacts import _mix_with_stage1_replay

# Create test data
stage2_data = [{'id': i, 'stage': 2} for i in range(100)]
stage1_data = [{'id': i, 'stage': 1} for i in range(1000)]

# Mix with 15% replay
mixed = _mix_with_stage1_replay(stage2_data, stage1_data, replay_ratio=0.15)

# Verify counts
expected_replay = int(100 * 0.15)  # 15
assert len(mixed) == 100 + expected_replay
print(f'✅ Stage 1 replay mixing test passed ({len(mixed)} examples)')
"
```

### Integration Tests

1. **Small-Scale End-to-End Test**:
```bash
# Create small test datasets
mkdir -p test_artifacts
echo '{"test": "artifact"}' > test_artifacts/test.json

# Run pipeline with small dataset limits
python3 process_artifacts.py \
    --artifacts-dir test_artifacts \
    --output-dir test_results \
    --skip-upload

# Verify structure
ls -R ~/shared-olmo-models/fine-tuned/webauthn-security-sequential-*
```

2. **Manifest Validation**:
```bash
# Verify manifest structure
python3 -c "
import json
from pathlib import Path

# Find latest sequential run
runs_dir = Path.home() / 'shared-olmo-models' / 'fine-tuned'
latest_run = max(runs_dir.glob('webauthn-security-sequential-*'))

# Load manifest
manifest_path = latest_run / 'run-manifest.json'
with open(manifest_path) as f:
    manifest = json.load(f)

# Validate structure
assert manifest['version'] == '2.0'
assert manifest['pipeline_type'] == 'sequential'
assert 'stage1' in manifest
assert 'stage2' in manifest
assert manifest['stage1']['adapters_path'] == './stage1/adapters'
assert manifest['stage2']['adapters_path'] == './stage2/adapters'
print('✅ Manifest validation passed')
"
```

### Production Validation

1. **Full Pipeline Run**:
```bash
# Run full sequential pipeline
python3 process_artifacts.py \
    --artifacts-dir /path/to/security/artifacts \
    --output-dir results_full \
    --skip-upload  # Test without upload first

# Verify all stages completed
# Expected: ~20-25 hours total training time
```

2. **Evaluation Metrics Verification**:
```bash
# Check Stage 1 evaluation
cat ~/shared-olmo-models/fine-tuned/webauthn-security-sequential-*/stage1/evaluation/evaluation_results.json | jq '.metrics'

# Check Stage 2 evaluation
cat ~/shared-olmo-models/fine-tuned/webauthn-security-sequential-*/stage2/evaluation/evaluation_results.json | jq '.metrics'

# Verify retention >= 90%
```

---

## Expected Results

### Dataset Sizes

**Stage 1 (Public Datasets)**:
- CrossVul: 9,313 examples
- CVEfixes: ~12,987 examples (may vary with streaming/filtering)
- **Total: ~22,300 examples**
- Split: 17,840 train / 2,230 val / 2,230 test (80/10/10)

**Stage 2 (WebAuthn + Replay)**:
- WebAuthn tools: ~50-200 examples (varies by security findings)
- Stage 1 replay (15%): ~7-30 examples
- **Total: ~57-230 examples**

### Training Time Estimates

**Stage 1**:
- Iterations: 5,000
- Time per iteration: ~15 seconds (large dataset, batch_size=1)
- **Estimated total: ~20 hours**

**Stage 2**:
- Iterations: 1,600
- Time per iteration: ~8 seconds (smaller dataset, resume training)
- **Estimated total: ~3.5 hours**

**Total Pipeline Time: ~23-25 hours**

### Success Criteria

**Stage 1 Model**:
- ✅ Exact match >60% on CrossVul/CVEfixes test set
- ✅ Recognizes 158+ CWE types
- ✅ Generates fixes across 21 programming languages
- ✅ Understands real-world CVE patterns

**Stage 2 Model**:
- ✅ Exact match >70% on WebAuthn-specific test set
- ✅ Retains >90% of Stage 1 knowledge (anti-forgetting validation)
- ✅ Specializes in WebAuthn/FIDO2 security
- ✅ Generates framework-native fixes (KTor, Gradle, Android)

**Pipeline**:
- ✅ Sequential training run structure created correctly
- ✅ All manifests (v2.0) saved with complete metadata
- ✅ Both stages evaluated with metrics
- ✅ Final model uploaded to HuggingFace

---

## Migration Notes

### No Backwards Compatibility

Per requirements, this implementation does **not** maintain backwards compatibility with the old single-stage pipeline. Changes can be reverted if needed by checking out the previous commit.

### Files Safe to Delete After Migration

Once sequential pipeline is verified working:
- Old single-stage code paths in `process_artifacts.py`
- Any `--only-*` flag handling
- Legacy manifest v1.0 loading (can keep for reading old runs)

### Revert Strategy

If issues occur and revert is needed:
```bash
# Find commit before sequential changes
git log --oneline --grep="sequential"

# Revert to previous commit
git revert <commit-hash>

# Or reset to before changes
git reset --hard <commit-hash>
```

---

## Implementation Checklist

- [ ] **Phase 1**: Create `public_dataset_loader.py`
  - [ ] Implement CrossVul loader with ChatML transformation
  - [ ] Implement CVEfixes loader with streaming support
  - [ ] Test with small samples (10 examples each)
  - [ ] Verify ChatML format correctness

- [ ] **Phase 2**: Update `training_run_manager.py`
  - [ ] Add `SequentialStageManifest` dataclass
  - [ ] Update `RunManifest` to v2.0
  - [ ] Implement `create_sequential_run()`
  - [ ] Add stage1/stage2 property accessors
  - [ ] Update `_load_manifest()` to handle v2.0
  - [ ] Test manifest creation and serialization

- [ ] **Phase 3**: Extend `mlx_trainer.py`
  - [ ] Implement `train_stage1()`
  - [ ] Implement `train_stage2()`
  - [ ] Implement `run_mlx_training_with_resume()`
  - [ ] Test with small datasets (50 Stage 1, 20 Stage 2)

- [ ] **Phase 4**: Refactor `process_artifacts.py`
  - [ ] Implement `run_sequential_pipeline()`
  - [ ] Implement `_mix_with_stage1_replay()`
  - [ ] Implement `_stratified_split_by_source()`
  - [ ] Implement `_save_jsonl()`
  - [ ] Update `main()` to use sequential pipeline
  - [ ] Remove old single-stage code paths

- [ ] **Phase 5**: Update `config/olmo-security-config.yaml`
  - [ ] Add sequential training configuration
  - [ ] Set Stage 1/Stage 2 parameters
  - [ ] Set replay ratio (0.15)

- [ ] **Testing**
  - [ ] Unit tests for all new components
  - [ ] Integration test with small datasets
  - [ ] Full pipeline test with real data
  - [ ] Validate evaluation metrics
  - [ ] Verify knowledge retention

- [ ] **Production Run**
  - [ ] Run full sequential pipeline
  - [ ] Verify Stage 1 evaluation (>60% exact match)
  - [ ] Verify Stage 2 evaluation (>70% exact match)
  - [ ] Verify knowledge retention (>90%)
  - [ ] Upload to HuggingFace
  - [ ] Document final model performance

---

## Additional Context

### Why 15% Stage 1 Replay?

The 15% replay ratio is based on research on catastrophic forgetting prevention:
- Too low (<10%): Model forgets Stage 1 knowledge
- Too high (>25%): Stage 2 specialization is diluted
- Sweet spot (15-20%): Preserves general knowledge while specializing

Can be tuned in config if retention falls below 90%.

### Why Lower Learning Rate for Stage 2?

Stage 2 uses 0.2x Stage 1 learning rate (4e-6 vs 2e-5) to:
- Preserve Stage 1 learned weights
- Fine-tune gently on WebAuthn domain
- Reduce risk of catastrophic forgetting
- Allow smaller dataset to specialize effectively

### MLX Resume Adapter Behavior

The `--resume-adapter-file` flag in MLX LoRA:
- Loads Stage 1 adapter weights as starting point
- Continues training from those weights (not from scratch)
- Allows transfer learning from general → specific domain
- Critical for sequential fine-tuning success

---

## References

- **CrossVul Dataset**: https://huggingface.co/datasets/hitoshura25/crossvul
- **CVEfixes Dataset**: https://huggingface.co/datasets/hitoshura25/cvefixes
- **MLX Documentation**: https://ml-explore.github.io/mlx/
- **LoRA Paper**: https://arxiv.org/abs/2106.09685
- **Catastrophic Forgetting**: Research on continual learning and knowledge retention

---

**Document Version**: 1.0
**Last Updated**: 2025-10-13
**Author**: Sequential Fine-Tuning Integration Team
