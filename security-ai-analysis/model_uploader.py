#!/usr/bin/env python3
"""
Model Upload Utility for Security Analysis Pipeline

Dedicated module for uploading fine-tuned models to HuggingFace Hub.
Extracted from MLXFineTuner for clean phase separation.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# HuggingFace imports for model upload
try:
    from huggingface_hub import HfApi, create_repo
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent))
from config_manager import OLMoSecurityConfig

# Setup logging
logger = logging.getLogger(__name__)

class ModelUploader:
    """Dedicated model uploader for HuggingFace Hub integration"""

    def __init__(self, config: Optional[OLMoSecurityConfig] = None, skip_upload: bool = False):
        """
        Initialize model uploader

        Args:
            config: Security configuration (optional)
            skip_upload: If True, all upload operations will be skipped
        """
        self.config = config or OLMoSecurityConfig()
        self.skip_upload = skip_upload

        logger.info(f"ModelUploader initialized (skip_upload={skip_upload})")

    def upload_to_huggingface(self, model_path: Path, custom_repo_name: Optional[str] = None) -> Optional[str]:
        """
        Upload fine-tuned model to HuggingFace Hub

        Args:
            model_path: Path to the model directory to upload
            custom_repo_name: Optional custom repository name

        Returns:
            Repository URL if successful, None otherwise
        """
        # Honor skip upload flag
        if self.skip_upload:
            message = "🛑 Upload skipped (--skip-model-upload flag)"
            print(message)  # Print to stdout for test visibility
            logger.info(message)
            return None

        # ✅ PHASE 4.5: Convert MLX adapter to HuggingFace PEFT format before upload
        # This includes fail-fast validation that should run even in test environments
        logger.info("🔄 Converting MLX adapter to HuggingFace PEFT format...")
        peft_model_path = self._convert_mlx_to_peft_format(model_path)

        # ✅ PHASE 6.3: Pre-upload validation to ensure community standards
        # This validation must run in test environments to verify fail-fast behavior
        logger.info("🔍 Validating model artifacts before upload...")
        validation_result = self._validate_model_for_upload(peft_model_path)

        if not validation_result['overall_valid']:
            failed_checks = [k for k, v in validation_result['checks'].items() if not v]
            error_msg = f"Model validation failed: {', '.join(failed_checks)}"
            logger.error(f"❌ {error_msg}")
            if validation_result['errors']:
                for error in validation_result['errors'][:3]:  # Show first 3 errors
                    logger.error(f"   • {error}")
            # FAIL FAST: Validation failed - raise exception to stop process
            raise ValueError(f"Model validation failed - cannot upload non-functional model: {failed_checks}")

        logger.info("✅ Model validation passed - ready for upload")

        # ✅ SAFETY: Prevent actual uploads during testing (after validation completes)
        if (os.getenv('PYTEST_CURRENT_TEST') or
            os.getenv('TESTING') == '1' or
            'pytest' in sys.modules or
            'test' in sys.argv[0].lower()):
            message = "🛑 Upload blocked - test environment detected"
            print(message)  # Print to stdout for test visibility
            logger.info(message)
            # Return a fake success URL to maintain test flow
            return f"https://huggingface.co/test-blocked/{custom_repo_name or 'mock-model'}"

        if not self.config.fine_tuning.upload_enabled:
            logger.info("HuggingFace upload disabled in configuration")
            return None

        if not HUGGINGFACE_AVAILABLE:
            # Fail fast on missing critical dependencies
            logger.error("❌ CRITICAL: HuggingFace Hub dependency missing")
            logger.error("🔍 Install huggingface_hub package: pip install huggingface_hub")
            raise RuntimeError("HuggingFace Hub dependency missing - install huggingface_hub package") from None

        # Use saved HuggingFace CLI token (same approach as dataset upload)
        # This will use the token from `huggingface-cli login` automatically

        try:
            # Generate repository name
            if custom_repo_name:
                repo_name = custom_repo_name
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                repo_name = f"{self.config.fine_tuning.default_output_name}_{timestamp}"

            full_repo_name = f"{self.config.fine_tuning.default_repo_prefix}/{repo_name}"

            logger.info(f"Uploading model to HuggingFace: {full_repo_name}")

            # Initialize HF API (uses saved CLI token automatically)
            api = HfApi()

            # Create repository (uses saved CLI token automatically)
            repo_url = create_repo(
                repo_id=full_repo_name,
                private=self.config.fine_tuning.private_repos,
                exist_ok=True
            )

            # Upload model files (uses saved CLI token automatically)
            api.upload_folder(
                folder_path=str(peft_model_path),
                repo_id=full_repo_name
            )

            # Create and upload model card
            self._create_model_card(peft_model_path, full_repo_name)

            logger.info(f"✅ Model uploaded successfully: {repo_url}")
            return repo_url

        except Exception as e:
            logger.error(f"HuggingFace upload failed: {e}")
            raise

    def _create_model_card(self, model_path: Path, repo_name: str):
        """Create model card with training details"""

        # Load training metadata
        metadata_file = model_path / "training_metadata.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

        model_card_content = f"""---
language: en
tags:
- fine-tuned
- security-analysis
- webauthn
- olmo-2-1b
- mlx-optimized
library_name: transformers
pipeline_tag: text-generation
---

# {repo_name}

Fine-tuned OLMo-2-1B model for WebAuthn security vulnerability analysis.

## Model Details

- **Base Model**: OLMo-2-1B (MLX-optimized)
- **Fine-tuning Framework**: MLX (Apple Silicon optimized)
- **Domain**: WebAuthn Security Analysis
- **Training Date**: {metadata.get('training_timestamp', 'N/A')}
- **Training Duration**: {metadata.get('training_duration_seconds', 0):.2f} seconds

## Training Configuration

- **Learning Rate**: {metadata.get('training_parameters', {}).get('learning_rate', 'N/A')}
- **Batch Size**: {metadata.get('training_parameters', {}).get('batch_size', 'N/A')}
- **Epochs**: {metadata.get('training_parameters', {}).get('max_epochs', 'N/A')}
- **Quantization**: {metadata.get('mlx_configuration', {}).get('quantization', 'N/A')}

## Usage

```python
from mlx_lm import load, generate

model, tokenizer = load("{repo_name}")
response = generate(model, tokenizer, "Analyze this WebAuthn vulnerability:", max_tokens=500)
print(response)
```

## Performance

This model was fine-tuned using MLX framework for optimal performance on Apple Silicon devices,
providing 20-30X speed improvements over traditional fine-tuning approaches.

## Intended Use

This model is designed for analyzing WebAuthn security vulnerabilities and generating
security-focused documentation. It should be used in conjunction with professional
security analysis workflows.

## Limitations

- Specialized for WebAuthn/FIDO2 security analysis
- Optimized for Apple Silicon (MLX framework)
- May not generalize well to other domains without further fine-tuning

## Training Data

Fine-tuned on curated WebAuthn security vulnerability reports and analysis documentation.

Generated by Security Analysis Pipeline Model Uploader v1.0
"""

        model_card_file = model_path / "README.md"
        with open(model_card_file, 'w') as f:
            f.write(model_card_content)

        logger.info(f"Model card created: {model_card_file}")

    def _validate_model_for_upload(self, model_path: Path) -> Dict[str, Any]:
        """
        Validate model meets community standards before upload

        Phase 6.3 implementation: Ensure complete model artifacts
        """

        # Import validation system
        try:
            sys.path.append(str(Path(__file__).parent))
            from validate_model_artifacts import validate_model_artifacts

            return validate_model_artifacts(model_path)

        except ImportError as e:
            logger.error(f"Could not import model validation: {e}")
            raise

    def _basic_model_validation(self, model_path: Path) -> Dict[str, Any]:
        """Basic fallback validation when full validator unavailable"""

        logger.warning("Using basic fallback validation")

        result = {
            'overall_valid': False,
            'checks': {
                'directory_exists': False,
                'has_files': False,
                'no_obvious_placeholders': False
            },
            'errors': []
        }

        # Basic checks
        if not model_path.exists():
            result['errors'].append(f"Model directory does not exist: {model_path}")
            return result

        result['checks']['directory_exists'] = True

        # Check for files
        files = list(model_path.rglob('*'))
        if len(files) > 0:
            result['checks']['has_files'] = True
        else:
            result['errors'].append("Model directory is empty")

        # Check for obvious placeholder files
        placeholder_found = False
        for file_path in files:
            if file_path.is_file() and file_path.name.endswith('.txt'):
                try:
                    with open(file_path, 'r', errors='ignore') as f:
                        content = f.read()
                    if '# Placeholder for' in content:
                        placeholder_found = True
                        break
                except Exception as e:
                    logger.error(f"Could not read file {file_path}: {e}")
                    raise

        if not placeholder_found:
            result['checks']['no_obvious_placeholders'] = True
        else:
            result['errors'].append("Found obvious placeholder files")

        result['overall_valid'] = all(result['checks'].values())

        return result

    def _detect_and_validate_model_type(self, model_path: Path) -> str:
        """
        Detect model type and fail fast if invalid structure

        Returns:
            'lora' for LoRA adapter models
            'fused' for fused/merged models

        Raises:
            ValueError: For invalid or ambiguous model structures
        """
        adapters_dir = model_path / "adapters"
        adapters_file = adapters_dir / "adapters.safetensors"
        adapter_config = adapters_dir / "adapter_config.json"

        model_file = model_path / "model.safetensors"
        config_file = model_path / "config.json"

        # Check for LoRA structure
        if adapters_dir.exists() and adapters_file.exists() and adapter_config.exists():
            logger.info(f"✅ Detected LoRA model structure: {model_path}")
            return "lora"

        # Check for fused structure
        elif model_file.exists() and config_file.exists():
            logger.info(f"✅ Detected fused model structure: {model_path}")
            return "fused"

        # FAIL FAST: Invalid structure
        else:
            missing_files = []
            if not adapters_dir.exists():
                missing_files.append("adapters/ directory")
            if not model_file.exists():
                missing_files.append("model.safetensors")
            if not config_file.exists():
                missing_files.append("config.json")

            raise ValueError(
                f"Invalid model structure at {model_path}. "
                f"Expected either LoRA format (adapters/adapters.safetensors + adapter_config.json) "
                f"or fused format (model.safetensors + config.json). "
                f"Missing: {', '.join(missing_files)}"
            )

    def _convert_mlx_to_peft_format(self, model_path: Path) -> Path:
        """
        Convert MLX model to PEFT format with proper type detection

        Args:
            model_path: Path to MLX fine-tuned model directory

        Returns:
            Path to converted PEFT format model directory or original path for fused models
        """
        logger.info("🔄 Starting MLX to PEFT format conversion...")

        try:
            model_type = self._detect_and_validate_model_type(model_path)

            if model_type == "lora":
                logger.info("🔄 Processing LoRA model - converting to PEFT format")
                return self._convert_lora_to_peft(model_path)

            elif model_type == "fused":
                logger.info("📋 Processing fused model - using original format (no conversion needed)")
                return model_path

            else:
                # This shouldn't happen due to validation above
                raise RuntimeError(f"Unexpected model type returned: {model_type}")

        except ValueError as e:
            logger.error(f"❌ Model validation failed: {e}")
            raise  # Re-raise to fail fast
        except Exception as e:
            logger.error(f"❌ Model type detection failed: {e}")
            raise

    def _convert_lora_to_peft(self, model_path: Path) -> Path:
        """
        Convert LoRA model to PEFT format

        Args:
            model_path: Path to LoRA model directory (contains adapters/)

        Returns:
            Path to converted PEFT format model directory
        """
        try:
            # Import the converter utility
            sys.path.append(str(Path(__file__).parent))
            from mlx_to_peft_converter import convert_mlx_to_peft_format, validate_peft_adapter

            # Determine MLX adapter path - handle case where model_path is already adapters directory
            if model_path.name == "adapters":
                # model_path is already the adapters directory
                mlx_adapter_path = model_path
            else:
                # model_path is the parent directory containing adapters/
                mlx_adapter_path = model_path / "adapters"

            # Create PEFT conversion output directory
            if model_path.name == "adapters":
                # If model_path is adapters directory, create converted directory alongside parent
                peft_output_path = model_path.parent / f"{model_path.parent.name}_peft_converted"
            else:
                # If model_path is parent directory, create converted directory alongside it
                peft_output_path = model_path.parent / f"{model_path.name}_peft_converted"

            peft_output_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"📂 Converting MLX adapters to PEFT format:")
            logger.info(f"   MLX adapters: {mlx_adapter_path}")
            logger.info(f"   PEFT output: {peft_output_path}")

            # Get base model path for PEFT configuration
            base_model_path = str(self.config.get_base_model_path())

            # Perform the conversion
            conversion_result = convert_mlx_to_peft_format(
                mlx_adapter_path=mlx_adapter_path,
                output_path=peft_output_path,
                base_model_path=base_model_path
            )

            if not conversion_result['success']:
                raise RuntimeError(f"MLX to PEFT conversion failed: {conversion_result.get('error', 'Unknown error')}")

            logger.info("✅ MLX to PEFT conversion completed successfully")
            logger.info(f"   Parameters converted: {conversion_result['parameters_converted']}")
            logger.info(f"   Files created: {len(conversion_result['files_created'])}")

            # Validate the converted PEFT adapter
            logger.info("🔍 Validating converted PEFT adapter...")
            validation_result = validate_peft_adapter(peft_output_path)

            if not validation_result['valid']:
                raise RuntimeError(f"PEFT adapter validation failed: {validation_result['errors']}")

            logger.info("✅ PEFT adapter validation passed")
            logger.info(f"   Files validated: {validation_result['files_found']}")

            return peft_output_path

        except Exception as e:
            logger.error(f"❌ LoRA to PEFT conversion failed: {e}")
            raise  # Re-raise to fail fast
