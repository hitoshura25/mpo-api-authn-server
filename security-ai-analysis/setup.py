#!/usr/bin/env python3
"""
Base Model Setup Script for AI Security Analysis

Downloads and optimizes the OLMo base model for Apple Silicon using MLX.

This script:
1. Checks if the default base model exists
2. Downloads from HuggingFace if missing
3. Converts to MLX format with 4-bit quantization
4. Validates model artifacts

Prerequisites:
- Virtual environment activated with mlx-lm installed
- Apple Silicon Mac (M1/M2/M3)

Usage:
    source ./venv/bin/activate
    python3 setup.py
"""

import sys
import subprocess
from pathlib import Path

# Add current directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import OLMoSecurityConfig


def print_banner():
    """Print setup banner with project information."""
    print("=" * 60)
    print("🚀 OLMo Base Model Setup")
    print("=" * 60)
    print("📥 Downloading and optimizing model for Apple Silicon")
    print("🔧 Using MLX framework with 4-bit quantization")
    print()


def download_and_convert_model(hf_model_id: str, output_dir: Path) -> bool:
    """
    Download model from HuggingFace and convert to MLX format.

    Args:
        hf_model_id: HuggingFace model ID (e.g., 'allenai/OLMo-2-1B-1124-Instruct')
        output_dir: Where to save the MLX-converted model

    Returns:
        True if download successful, False otherwise
    """
    try:
        print(f"📥 Downloading: {hf_model_id}")
        print(f"📁 Output: {output_dir}")
        print("🔧 Converting to MLX format (4-bit quantized)...")
        print()

        # Ensure parent directory exists
        output_dir.parent.mkdir(parents=True, exist_ok=True)

        # Check if model already exists and has files
        if output_dir.exists() and any(output_dir.iterdir()):
            print("✅ Model already exists, skipping download")
            return True

        # Remove empty directory if exists
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
            print("🔧 Removed empty model directory for fresh download")

        # Execute MLX conversion using subprocess
        cmd = [
            sys.executable, '-c', f'''
import sys
try:
    from mlx_lm import convert
    print("🔧 Converting {hf_model_id} to MLX format...")
    convert(
        "{hf_model_id}",
        mlx_path="{output_dir}",
        quantize=True,
        q_bits=4,
        q_group_size=64
    )
    print("✅ Conversion completed")
except ImportError:
    print("❌ mlx-lm not installed")
    print("💡 Install: pip install mlx-lm")
    sys.exit(1)
except Exception as e:
    print(f"❌ Conversion failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        ]

        print("🔧 Executing model download and conversion subprocess...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

        # Show output for debugging
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            # Verify the model was actually downloaded
            if output_dir.exists() and any(output_dir.iterdir()):
                print(f"✅ Model {output_dir.name} successfully installed")
                return True
            else:
                print(f"❌ Model directory is empty after download")
                return False
        else:
            print(f"❌ Download failed with return code {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ Model download timed out after 30 minutes")
        return False
    except Exception as e:
        print(f"❌ Model download failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def configure_chat_template(model_path: Path) -> bool:
    """
    Configure ChatML template for OLMo model if not already set.

    Checks if the model has a chat template configured. If not, adds ChatML
    special tokens and template. Safe to run multiple times (idempotent).

    Args:
        model_path: Path to the model directory

    Returns:
        True if template is configured (or already was), False on error
    """
    try:
        from transformers import AutoTokenizer

        print("🔍 Checking chat template configuration...")

        # Load the tokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)

        # Check if chat template already exists
        if hasattr(tokenizer, 'chat_template') and tokenizer.chat_template:
            print("✅ Chat template already configured")
            return True

        print("⚠️  Chat template not found, configuring...")

        # Add ChatML special tokens if they don't exist
        special_tokens_to_add = []
        vocab = tokenizer.get_vocab()

        if "<|im_start|>" not in vocab:
            special_tokens_to_add.append("<|im_start|>")
        if "<|im_end|>" not in vocab:
            special_tokens_to_add.append("<|im_end|>")

        if special_tokens_to_add:
            tokenizer.add_special_tokens({"additional_special_tokens": special_tokens_to_add})
            print(f"   Added special tokens: {special_tokens_to_add}")

        # Configure ChatML template
        chat_template = """{% for message in messages %}{% if message['role'] == 'system' %}<|im_start|>system
{{ message['content'] }}<|im_end|>
{% elif message['role'] == 'user' %}<|im_start|>user
{{ message['content'] }}<|im_end|>
{% elif message['role'] == 'assistant' %}<|im_start|>assistant
{{ message['content'] }}<|im_end|>
{% endif %}{% endfor %}{% if add_generation_prompt %}<|im_start|>assistant
{% endif %}"""

        tokenizer.chat_template = chat_template

        # Save the updated tokenizer
        tokenizer.save_pretrained(str(model_path))

        print("✅ ChatML template configured successfully")
        print("   - Special tokens added for ChatML format")
        print("   - Template supports system/user/assistant roles")

        return True

    except Exception as e:
        print(f"❌ Failed to configure chat template: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main setup function."""
    print_banner()

    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = OLMoSecurityConfig()
        print(f"   Base models directory: {config.base_models_dir}")
        print(f"   Default model: {config.default_base_model}")
        print()

        # Model mapping: config name -> HuggingFace ID
        # Maps our internal model names to actual HuggingFace repositories
        model_mapping = {
            'OLMo-2-1B-mlx-q4': 'allenai/OLMo-2-0425-1B',
            'OLMo-2-1B-mlx': 'allenai/OLMo-2-0425-1B-Instruct',
        }

        # Get HuggingFace model ID
        default_model = config.default_base_model
        hf_model_id = model_mapping.get(default_model, default_model)
        model_dir = config.base_models_dir / default_model

        # Check if model exists
        print("🔍 Checking for existing model...")
        if model_dir.exists() and any(model_dir.iterdir()):
            print(f"✅ Model already exists: {model_dir}")
            print()

            # Always verify/configure chat template for existing model
            if not configure_chat_template(model_dir):
                print("❌ Failed to configure chat template for existing model")
                return False

            print()
            print("✅ Setup complete!")
            print()
            print("🚀 Next steps:")
            print("   1. Model is ready for use")
            print("   2. Run: python3 process_artifacts.py --help")
            return True

        print("⚠️  Model not found, downloading...")
        print()

        # Download and convert model
        success = download_and_convert_model(hf_model_id, model_dir)

        if success:
            print()
            print("=" * 60)
            print("✅ Model download complete!")
            print("=" * 60)
            print(f"📁 Model location: {model_dir}")
            print(f"🔧 Format: MLX 4-bit quantized")
            print(f"🖥️  Optimized for: Apple Silicon (M1/M2/M3)")
            print()

            # Configure chat template for newly downloaded model
            if not configure_chat_template(model_dir):
                print("❌ Failed to configure chat template")
                return False

            print()
            print("=" * 60)
            print("✅ Model setup complete!")
            print("=" * 60)
            print()
            print("🚀 Next steps:")
            print("   1. Model is ready for use in fine-tuning")
            print("   2. Run: python3 process_artifacts.py --help")
            print("   3. See: docs/improvements/in-progress/gemini-refactor-plan.md")
            return True
        else:
            print()
            print("=" * 60)
            print("❌ Model setup failed")
            print("=" * 60)
            print()
            print("💡 Troubleshooting:")
            print("   1. Ensure virtual environment is activated:")
            print("      source ./venv/bin/activate")
            print()
            print("   2. Install mlx-lm if not present:")
            print("      pip install mlx-lm")
            print()
            print("   3. Check internet connection")
            print()
            print("   4. Verify Apple Silicon Mac (M1/M2/M3)")
            print()
            print("   5. Check disk space (~4GB required)")
            return False

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Setup failed with error: {e}")
        print("=" * 60)
        print()
        print("💡 Common issues:")
        print("   1. Config file missing: config/olmo-security-config.yaml")
        print("   2. Python dependencies not installed")
        print("   3. Not running on Apple Silicon")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
