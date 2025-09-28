#!/usr/bin/env python3
"""
Model Artifacts Validation Module

Provides comprehensive validation of model artifacts before upload to ensure
models meet quality and format requirements.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def validate_model_artifacts(model_path: Path) -> Dict[str, Any]:
    """
    Comprehensive validation of model artifacts before upload

    Args:
        model_path: Path to model directory containing artifacts

    Returns:
        Dictionary with validation results:
        {
            'overall_valid': bool,
            'checks': {
                'directory_exists': bool,
                'has_model_files': bool,
                'config_valid': bool,
                'reasonable_size': bool,
                'no_placeholder_files': bool
            },
            'errors': [list of error messages],
            'warnings': [list of warning messages]
        }
    """
    result = {
        'overall_valid': False,
        'checks': {
            'directory_exists': False,
            'has_model_files': False,
            'config_valid': False,
            'reasonable_size': False,
            'no_placeholder_files': False
        },
        'errors': [],
        'warnings': []
    }

    try:
        # Check 1: Directory exists
        if not model_path.exists():
            result['errors'].append(f"Model directory does not exist: {model_path}")
            return result

        if not model_path.is_dir():
            result['errors'].append(f"Model path is not a directory: {model_path}")
            return result

        result['checks']['directory_exists'] = True

        # Check 2: Has model files (LoRA, fused, or PEFT)
        has_lora = _check_lora_structure(model_path, result)
        has_fused = _check_fused_structure(model_path, result)
        has_peft = _check_peft_structure(model_path, result)

        if has_lora or has_fused or has_peft:
            result['checks']['has_model_files'] = True
        else:
            result['errors'].append("No valid model structure found (neither LoRA, fused, nor PEFT)")

        # Check 3: Config validation
        if _validate_config_files(model_path, result):
            result['checks']['config_valid'] = True

        # Check 4: Reasonable file sizes
        if _check_reasonable_sizes(model_path, result):
            result['checks']['reasonable_size'] = True

        # Check 5: No placeholder files
        if _check_no_placeholders(model_path, result):
            result['checks']['no_placeholder_files'] = True

        # Overall validation
        result['overall_valid'] = all(result['checks'].values())

        if result['overall_valid']:
            logger.info(f"✅ Model validation passed: {model_path}")
        else:
            failed_checks = [k for k, v in result['checks'].items() if not v]
            logger.warning(f"⚠️ Model validation failed: {failed_checks}")

    except Exception as e:
        # Fail fast on infrastructure issues during model validation
        logger.error(f"❌ CRITICAL: Model validation infrastructure failure: {e}")
        logger.error("🔍 Model validation infrastructure failure - check file permissions, disk space, and model directory integrity")
        raise RuntimeError(f"Model validation infrastructure failure - requires investigation: {e}") from e

    return result

def _check_lora_structure(model_path: Path, result: Dict) -> bool:
    """Check for valid LoRA adapter structure"""
    adapters_dir = model_path / "adapters"
    if not adapters_dir.exists():
        return False

    adapters_file = adapters_dir / "adapters.safetensors"
    config_file = adapters_dir / "adapter_config.json"

    if not adapters_file.exists():
        result['warnings'].append("LoRA adapters directory exists but missing adapters.safetensors")
        return False

    if not config_file.exists():
        result['warnings'].append("LoRA adapters directory exists but missing adapter_config.json")
        return False

    return True

def _check_fused_structure(model_path: Path, result: Dict) -> bool:
    """Check for valid fused model structure"""
    model_file = model_path / "model.safetensors"
    config_file = model_path / "config.json"

    if not model_file.exists():
        return False

    if not config_file.exists():
        result['warnings'].append("Fused model file exists but missing config.json")
        return False

    return True

def _check_peft_structure(model_path: Path, result: Dict) -> bool:
    """Check for valid PEFT adapter structure (from MLX conversion)"""
    adapter_model_file = model_path / "adapter_model.safetensors"
    adapter_config_file = model_path / "adapter_config.json"

    if not adapter_model_file.exists():
        return False

    if not adapter_config_file.exists():
        result['warnings'].append("PEFT adapter model exists but missing adapter_config.json")
        return False

    return True

def _validate_config_files(model_path: Path, result: Dict) -> bool:
    """Validate JSON config files are parseable"""
    config_files = list(model_path.glob("**/*.json"))

    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON in {config_file}: {e}")
            return False
        except Exception as e:
            # Fail fast on infrastructure issues reading config files
            logger.error(f"❌ CRITICAL: Config file access failure for {config_file}: {e}")
            logger.error("🔍 Config file access failure - check file permissions and disk integrity")
            raise RuntimeError(f"Config file access failure - infrastructure issue requires investigation: {e}") from e

    return True

def _check_reasonable_sizes(model_path: Path, result: Dict) -> bool:
    """Check that model files have reasonable sizes"""
    model_files = list(model_path.glob("**/*.safetensors"))

    if not model_files:
        result['errors'].append("No .safetensors files found")
        return False

    for model_file in model_files:
        size_mb = model_file.stat().st_size / (1024 * 1024)

        if size_mb < 0.1:  # Less than 100KB
            result['warnings'].append(f"Model file {model_file.name} is very small ({size_mb:.1f}MB)")
        elif size_mb > 50000:  # More than 50GB
            result['warnings'].append(f"Model file {model_file.name} is very large ({size_mb:.1f}MB)")

    return True

def _check_no_placeholders(model_path: Path, result: Dict) -> bool:
    """Check for obvious placeholder or test files"""
    text_files = list(model_path.glob("**/*.txt"))

    for text_file in text_files:
        try:
            with open(text_file, 'r', errors='ignore') as f:
                content = f.read()
            if any(placeholder in content.lower() for placeholder in
                   ['placeholder', 'todo', 'fixme', 'mock', 'test data']):
                result['warnings'].append(f"Possible placeholder content in {text_file.name}")
                return False
        except:
            continue

    return True