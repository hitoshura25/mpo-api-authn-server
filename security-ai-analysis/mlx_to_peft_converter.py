#!/usr/bin/env python3
"""
MLX LoRA to HuggingFace PEFT Format Converter

Converts MLX LoRA adapter format to HuggingFace PEFT standard format for
successful upload to HuggingFace Hub. This addresses the format incompatibility
discovered through evidence-based research.

MLX Format: adapters.safetensors with parameters like "model.layers.6.self_attn.q_proj.lora_a"
PEFT Format: adapter_model.safetensors with parameters like "base_model.model.layers.6.self_attn.q_proj.lora_A.weight"
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from safetensors.numpy import load_file, save_file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def convert_mlx_to_peft_format(mlx_adapter_path: Path, output_path: Path,
                               base_model_path: str) -> Dict[str, Any]:
    """
    Convert MLX LoRA adapter to HuggingFace PEFT format.

    Args:
        mlx_adapter_path: Path to MLX adapter directory (contains adapters.safetensors)
        output_path: Path to output PEFT adapter directory
        base_model_path: Path to base model for metadata

    Returns:
        Dictionary with conversion results and metadata
    """
    logger.info(f"🔄 Converting MLX adapter to PEFT format")
    logger.info(f"   MLX adapter: {mlx_adapter_path}")
    logger.info(f"   Output: {output_path}")

    try:
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Load MLX adapter weights
        mlx_weights_file = mlx_adapter_path / "adapters.safetensors"
        mlx_config_file = mlx_adapter_path / "adapter_config.json"

        if not mlx_weights_file.exists():
            raise FileNotFoundError(f"MLX adapter weights not found: {mlx_weights_file}")
        if not mlx_config_file.exists():
            raise FileNotFoundError(f"MLX adapter config not found: {mlx_config_file}")

        logger.info("📂 Loading MLX adapter weights...")
        mlx_data = load_file(str(mlx_weights_file))

        # Extract parameter names and tensors from safetensors format (dict of numpy arrays)
        logger.info(f"📊 Loaded {len(mlx_data)} MLX parameters")

        # Step 2: Load MLX configuration
        with open(mlx_config_file, 'r') as f:
            mlx_config = json.load(f)

        # Step 3: Convert parameter names to PEFT format
        logger.info("🔧 Converting parameter names to PEFT format...")
        peft_weights = {}

        for mlx_param_name, tensor_data in mlx_data.items():
            # Convert MLX naming to PEFT naming
            peft_param_name = convert_parameter_name(mlx_param_name)

            # Store converted parameter with tensor data (numpy array)
            peft_weights[peft_param_name] = tensor_data

        logger.info(f"✅ Converted {len(peft_weights)} parameters to PEFT format")

        # Step 4: Create PEFT adapter configuration
        peft_config = create_peft_config(mlx_config, base_model_path)

        # Step 5: Save PEFT format files
        # Save adapter weights
        peft_weights_file = output_path / "adapter_model.safetensors"
        save_file(peft_weights, str(peft_weights_file))
        logger.info(f"💾 Saved PEFT weights: {peft_weights_file}")

        # Save adapter config
        peft_config_file = output_path / "adapter_config.json"
        with open(peft_config_file, 'w') as f:
            json.dump(peft_config, f, indent=2)
        logger.info(f"💾 Saved PEFT config: {peft_config_file}")

        # Step 6: Generate model card
        model_card_content = generate_model_card(mlx_config, base_model_path)
        model_card_file = output_path / "README.md"
        with open(model_card_file, 'w') as f:
            f.write(model_card_content)
        logger.info(f"💾 Generated model card: {model_card_file}")

        # Return conversion results
        conversion_result = {
            'success': True,
            'mlx_input_path': str(mlx_adapter_path),
            'peft_output_path': str(output_path),
            'files_created': [
                str(peft_weights_file),
                str(peft_config_file),
                str(model_card_file)
            ],
            'parameters_converted': len(peft_weights),
            'base_model': base_model_path,
            'conversion_metadata': {
                'mlx_config': mlx_config,
                'peft_config': peft_config
            }
        }

        logger.info("✅ MLX to PEFT conversion completed successfully")
        return conversion_result

    except Exception as e:
        logger.error(f"❌ MLX to PEFT conversion failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'mlx_input_path': str(mlx_adapter_path),
            'peft_output_path': str(output_path)
        }


def convert_parameter_name(mlx_param_name: str) -> str:
    """
    Convert MLX parameter name to HuggingFace PEFT format.

    MLX format: "model.layers.6.self_attn.q_proj.lora_a"
    PEFT format: "base_model.model.layers.6.self_attn.q_proj.lora_A.weight"
    """
    # Add base_model.model prefix for PEFT format
    if not mlx_param_name.startswith("base_model.model."):
        peft_name = f"base_model.{mlx_param_name}"
    else:
        peft_name = mlx_param_name

    # Convert lora_a/lora_b to lora_A.weight/lora_B.weight
    if peft_name.endswith(".lora_a"):
        peft_name = peft_name.replace(".lora_a", ".lora_A.weight")
    elif peft_name.endswith(".lora_b"):
        peft_name = peft_name.replace(".lora_b", ".lora_B.weight")

    return peft_name


def create_peft_config(mlx_config: Dict[str, Any], base_model_path: str) -> Dict[str, Any]:
    """
    Create HuggingFace PEFT configuration from MLX configuration.

    Args:
        mlx_config: MLX adapter configuration
        base_model_path: Path to base model

    Returns:
        PEFT configuration dictionary
    """
    # Extract LoRA parameters from MLX config
    lora_params = mlx_config.get('lora_parameters', {})

    # Create PEFT configuration with minimum required fields
    peft_config = {
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "target_modules": [
            "q_proj",
            "v_proj",
            "k_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj"
        ],
        "r": lora_params.get('rank', 8),
        "lora_alpha": lora_params.get('scale', 20.0),
        "lora_dropout": lora_params.get('dropout', 0.0),
        "bias": "none",
        "base_model_name_or_path": base_model_path,
        "inference_mode": False,
        "init_lora_weights": True
    }

    return peft_config


def _map_local_path_to_hf_model_id(local_path: str) -> str:
    """
    Map local model path to HuggingFace model ID for metadata compatibility.

    Args:
        local_path: Local file system path to model

    Returns:
        HuggingFace model ID or cleaned path
    """
    # Known mappings for common models
    path_mappings = {
        'OLMo-2-1B': 'allenai/OLMo-2-1B',
        'OLMo-2-1B-mlx': 'allenai/OLMo-2-1B',
        'OLMo-2-1B-mlx-q4': 'allenai/OLMo-2-1B',
        'OLMo-1B': 'allenai/OLMo-1B-hf',
        'OLMo-7B': 'allenai/OLMo-7B-hf',
        'llama-2-7b': 'meta-llama/Llama-2-7b-hf',
        'llama-2-13b': 'meta-llama/Llama-2-13b-hf',
        'mistral-7b': 'mistralai/Mistral-7B-v0.1'
    }

    # Extract model name from path
    from pathlib import Path
    path_obj = Path(local_path)
    model_name = path_obj.name

    # Check for exact matches first
    if model_name in path_mappings:
        return path_mappings[model_name]

    # Check for partial matches (e.g., OLMo-2-1B-mlx-q4 -> allenai/OLMo-2-1B)
    for pattern, hf_id in path_mappings.items():
        if pattern in model_name:
            return hf_id

    # If no mapping found, try to extract a reasonable model name
    # Remove common MLX/quantization suffixes
    clean_name = model_name.replace('-mlx', '').replace('-q4', '').replace('-q8', '')

    # If it looks like a HuggingFace path already, return as-is
    if '/' in clean_name:
        return clean_name

    # Return the cleaned name with a note
    return f"{clean_name}"


def generate_model_card(mlx_config: Dict[str, Any], base_model_path: str) -> str:
    """
    Generate HuggingFace-compliant model card with proper metadata.

    Args:
        mlx_config: MLX adapter configuration
        base_model_path: Path to base model

    Returns:
        Model card content as string
    """
    # Extract training details from MLX config
    iterations = mlx_config.get('iters', 'N/A')
    learning_rate = mlx_config.get('learning_rate', 'N/A')
    lora_params = mlx_config.get('lora_parameters', {})
    rank = lora_params.get('rank', 8)

    # Map local path to HuggingFace model ID
    hf_model_id = _map_local_path_to_hf_model_id(base_model_path)

    model_card = f"""---
base_model: {hf_model_id}
base_model_relation: adapter
library_name: peft
peft_type: LORA
tags:
- security
- vulnerability-analysis
- webauthn
- mlx-converted
license: apache-2.0
---

# WebAuthn Security LoRA Adapter

This LoRA adapter specializes the base model for WebAuthn security vulnerability analysis.

**Converted from MLX format to HuggingFace PEFT format for compatibility.**

## Model Details

- **Base Model**: {hf_model_id}
- **Adapter Type**: LoRA (Low-Rank Adaptation)
- **Target Modules**: q_proj, v_proj, k_proj, o_proj, gate_proj, up_proj, down_proj
- **LoRA Rank**: {rank}
- **LoRA Alpha**: {lora_params.get('scale', 20.0)}
- **LoRA Dropout**: {lora_params.get('dropout', 0.0)}

## Training Details

- **Training Framework**: MLX-LM (converted to PEFT format)
- **Training Data**: WebAuthn security vulnerabilities
- **Iterations**: {iterations}
- **Learning Rate**: {learning_rate}
- **Optimizer**: {mlx_config.get('optimizer', 'adamw')}
- **Fine-tune Type**: {mlx_config.get('fine_tune_type', 'lora')}

## Usage

Load this adapter with the PEFT library:

```python
from peft import PeftModel, PeftConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load configuration and model
config = PeftConfig.from_pretrained("path/to/this/adapter")
base_model = AutoModelForCausalLM.from_pretrained(config.base_model_name_or_path)
model = PeftModel.from_pretrained(base_model, "path/to/this/adapter")

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path)

# Use for inference
inputs = tokenizer("Analyze this WebAuthn vulnerability:", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=100)
response = tokenizer.decode(outputs[0], skip_special_tokens=True)
```

## Conversion Notes

This adapter was originally trained using MLX-LM and converted to HuggingFace PEFT format using an evidence-based conversion pipeline that:

1. Converts MLX parameter naming (`lora_a/lora_b`) to PEFT format (`lora_A.weight/lora_B.weight`)
2. Adds proper `base_model.model.` prefixes to parameter names
3. Generates PEFT-compatible configuration with required fields
4. Maintains full compatibility with HuggingFace ecosystem

## Performance

This adapter enhances the base model's capability for:
- WebAuthn security vulnerability analysis
- Code fix generation for security issues
- Security-aware code recommendations

## License

Apache 2.0
"""

    return model_card


def validate_peft_adapter(peft_path: Path) -> Dict[str, Any]:
    """
    Validate converted PEFT adapter meets HuggingFace standards.

    Args:
        peft_path: Path to PEFT adapter directory

    Returns:
        Validation results dictionary
    """
    logger.info(f"🔍 Validating PEFT adapter: {peft_path}")

    validation_results = {
        'valid': False,
        'files_found': [],
        'errors': [],
        'warnings': []
    }

    try:
        # Check required files
        required_files = ["adapter_model.safetensors", "adapter_config.json", "README.md"]

        for file_name in required_files:
            file_path = peft_path / file_name
            if file_path.exists():
                validation_results['files_found'].append(file_name)
            else:
                validation_results['errors'].append(f"Missing required file: {file_name}")

        # Validate adapter config if it exists
        config_file = peft_path / "adapter_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)

            # Check required PEFT fields
            required_fields = ["peft_type", "target_modules"]
            for field in required_fields:
                if field not in config:
                    validation_results['errors'].append(f"Missing required config field: {field}")

        # Check if adapter weights file is valid
        weights_file = peft_path / "adapter_model.safetensors"
        if weights_file.exists():
            try:
                weights_data = load_file(str(weights_file))
                param_count = len(weights_data)
                logger.info(f"📊 Validated {param_count} adapter parameters")
            except Exception as e:
                validation_results['errors'].append(f"Invalid adapter weights file: {e}")

        # Determine overall validity
        validation_results['valid'] = len(validation_results['errors']) == 0

        if validation_results['valid']:
            logger.info("✅ PEFT adapter validation passed")
        else:
            logger.error(f"❌ PEFT adapter validation failed: {validation_results['errors']}")

        return validation_results

    except Exception as e:
        logger.error(f"❌ PEFT validation error: {e}")
        validation_results['errors'].append(str(e))
        return validation_results


if __name__ == "__main__":
    # Example usage
    mlx_path = Path("/Users/vinayakmenon/shared-olmo-models/fine-tuned/webauthn-security-sequential_20250918_212112_stage1_analysis/adapters")
    output_path = Path("/Users/vinayakmenon/shared-olmo-models/fine-tuned/peft_converted_stage1")
    base_model = "/Users/vinayakmenon/shared-olmo-models/base/OLMo-2-1B-mlx-q4"

    # Convert MLX to PEFT format
    result = convert_mlx_to_peft_format(mlx_path, output_path, base_model)

    if result['success']:
        # Validate converted adapter
        validation = validate_peft_adapter(output_path)
        print("Conversion successful!" if validation['valid'] else "Conversion completed but validation failed")
    else:
        print(f"Conversion failed: {result['error']}")