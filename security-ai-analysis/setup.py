#!/usr/bin/env python3
"""
AI Security Analysis Setup Script

Creates portable project structure with shared model support for the
AI Security Dataset Research Initiative.

This script automates the complete setup process:
1. Creates project directory structure (data/, results/, venv/)
2. Creates shared model directories (~/shared-olmo-models/)
3. Sets up virtual environment with dependencies
4. Validates model configuration and availability
5. Reports setup status and next steps

Usage:
    cd security-ai-analysis
    python3 setup.py
    
    # Or from project root:
    cd mpo-api-authn-server
    python3 security-ai-analysis/setup.py
"""

import sys
import subprocess
from pathlib import Path

# Add current directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from model_manager import OLMoModelManager
from config_manager import OLMoSecurityConfig


def print_banner():
    """Print setup banner with project information."""
    print("🚀 AI Security Analysis System Setup")
    print("=" * 60)
    print("📖 Setting up portable AI Security Dataset Research Initiative")
    print("🏗️  Creating project structure with shared model support")
    print("🔧 Configuring virtual environment and dependencies")
    print()


def print_step(step_num: int, total_steps: int, description: str):
    """Print formatted step information."""
    print(f"📋 Step {step_num}/{total_steps}: {description}")


def download_olmo_model(model_name: str, target_dir: Path) -> bool:
    """
    Download and convert OLMo model to MLX format.
    
    Args:
        model_name: Name of the model to download (e.g., 'OLMo-2-1B-mlx-q4')
        target_dir: Directory where the model should be stored
        
    Returns:
        True if download successful, False otherwise
    """
    try:
        import subprocess
        import sys
        
        # Map config model names to actual available models
        model_mapping = {
            'OLMo-2-1B-mlx-q4': 'allenai/OLMo-2-0425-1B',  # Use base 1B model
            'OLMo-2-1B-mlx': 'allenai/OLMo-2-0425-1B-Instruct',  # Use instruct variant
        }
        
        actual_model = model_mapping.get(model_name, model_name)
        model_dir = target_dir / model_name
        
        print(f"   📥 Downloading {actual_model} to {model_dir}")
        print(f"   🔄 Converting to MLX format for Apple Silicon optimization")
        
        # Ensure parent directory exists, but handle model directory carefully
        model_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # If model directory exists but is empty, remove it for MLX convert
        if model_dir.exists():
            if not any(model_dir.iterdir()):  # Directory is empty
                import shutil
                shutil.rmtree(model_dir)
                print(f"   🔧 Removed empty model directory for fresh download")
            else:
                print(f"   ✅ Model directory contains files, skipping download")
                return True
        
        # Get the virtual environment python from project directory
        project_dir = Path(__file__).parent  # security-ai-analysis directory
        venv_python = project_dir / "venv" / "bin" / "python"
        if not venv_python.exists():
            venv_python = sys.executable  # Fallback to system python
        
        # Use mlx-lm to download and convert model
        # mlx_lm.convert supports converting HuggingFace models to MLX format
        cmd = [
            str(venv_python), '-c', f'''
import sys
sys.path.append(".")
try:
    from mlx_lm import convert
    print("   🔧 Converting {actual_model} to MLX format...")
    convert(
        "{actual_model}",
        mlx_path="{model_dir}",
        quantize=True,
        q_bits=4,
        q_group_size=64
    )
    print("   ✅ Model conversion completed")
except ImportError as e:
    print(f"   ❌ mlx-lm not available: {{e}}")
    print("   🔄 Falling back to transformers download...")
    from transformers import AutoTokenizer, AutoModelForCausalLM
    print("   📥 Downloading model files...")
    tokenizer = AutoTokenizer.from_pretrained("{actual_model}")
    model = AutoModelForCausalLM.from_pretrained("{actual_model}")
    tokenizer.save_pretrained("{model_dir}")
    model.save_pretrained("{model_dir}")
    print("   ✅ Model download completed")
except Exception as e:
    print(f"   ❌ Model download failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        ]
        
        # Run subprocess with error capture
        print(f"   🔧 Executing model download subprocess...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        
        # Show output for debugging
        if result.stdout:
            print(f"   📋 Output: {result.stdout}")
        if result.stderr:
            print(f"   ⚠️  Error: {result.stderr}")
        
        if result.returncode == 0:
            print(f"   ✅ Model {model_name} successfully installed")
            # Verify the model was actually downloaded
            if any(model_dir.iterdir()):
                return True
            else:
                print(f"   ❌ Model directory is empty after download")
                return False
        else:
            print(f"   ❌ Model download subprocess failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Model download timed out after 30 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Model download failed with error: {e}")
        return False


class SetupManager:
    """Enhanced setup manager with model download capabilities."""
    
    def __init__(self):
        self.manager = OLMoModelManager()
        self.config = self.manager.config
    
    def _download_default_model(self) -> bool:
        """Download the default model if it doesn't exist."""
        try:
            default_model = self.config.default_base_model
            model_path = self.config.base_models_dir / default_model
            
            if model_path.exists():
                print(f"   ✅ Model {default_model} already exists")
                return True
                
            print(f"   🔍 Default model {default_model} not found, downloading...")
            return download_olmo_model(default_model, self.config.base_models_dir)
            
        except Exception as e:
            print(f"   ❌ Model download setup failed: {e}")
            return False


def main():
    """Main setup function."""
    print_banner()
    
    try:
        # Initialize enhanced setup manager
        setup_manager = SetupManager()
        manager = setup_manager.manager
        config = setup_manager.config
        
        # Step 1: Create project structure
        total_steps = 7  # Updated to include model download
        print_step(1, total_steps, "Creating project directory structure")
        
        created_dirs = manager.setup_project_structure()
        print("   ✅ Created directories:")
        for name, description in created_dirs.items():
            print(f"      • {description}")
        print()
        
        # Step 2: Create virtual environment
        print_step(2, total_steps, "Creating virtual environment")
        
        # Always try to create/validate virtual environment 
        # (create_virtual_environment handles existing/incomplete envs)
        if manager.create_virtual_environment():
            print("   ✅ Virtual environment ready")
        else:
            print("   ❌ Failed to create virtual environment")
            return False
        print()
        
        # Step 3: Install dependencies
        print_step(3, total_steps, "Installing dependencies")
        
        requirements_file = Path(__file__).parent / "requirements.txt"
        if not requirements_file.exists():
            print(f"   ⚠️  Requirements file not found: {requirements_file}")
            print("   ⏭️  Skipping dependency installation")
        else:
            print(f"   📦 Installing from {requirements_file}")
            if manager.install_dependencies(requirements_file):
                print("   ✅ Dependencies installed successfully")
            else:
                print("   ❌ Failed to install dependencies")
                print("   💡 You may need to install manually:")
                print(f"      source {config.venv_dir}/bin/activate")
                print(f"      pip install -r {requirements_file}")
        print()
        
        # Step 4: Validate setup
        print_step(4, total_steps, "Validating setup")
        
        validation_results = manager.validate_setup()
        all_valid = True
        
        validation_checks = [
            ('directories_created', 'Directory structure'),
            ('virtual_environment', 'Virtual environment'),
            ('venv_python_functional', 'Virtual environment Python'),
            ('model_config_valid', 'Model configuration')
        ]
        
        for check, description in validation_checks:
            status = "✅" if validation_results.get(check, False) else "❌"
            print(f"   {status} {description}")
            if not validation_results.get(check, False):
                all_valid = False
                
        if all_valid:
            print("   🎉 Setup validation passed!")
        else:
            print("   ⚠️  Some validation checks failed")
        print()
        
        # Step 5: Check model availability
        print_step(5, total_steps, "Checking model availability")
        
        model_info = manager.get_model_info()
        
        print(f"   📁 Base models directory: {model_info['directories']['base_models_dir']}")
        print(f"   📁 Fine-tuned models directory: {model_info['directories']['fine_tuned_models_dir']}")
        print(f"   🤖 Default model: {model_info['models']['default_base_model']}")
        
        if model_info['models']['default_model_available']:
            print(f"   ✅ Default model available at: {model_info['models']['default_model_path']}")
        else:
            print(f"   ⚠️  Default model not found (this is normal for fresh setup)")
            print(f"   💡 Models can be downloaded separately when needed")
        
        available_base = model_info['models']['available_base_models']
        available_fine_tuned = model_info['models']['available_fine_tuned_models']
        
        if available_base:
            print(f"   📊 Available base models: {', '.join(available_base)}")
        if available_fine_tuned:
            print(f"   📊 Available fine-tuned models: {', '.join(available_fine_tuned)}")
            
        print(f"   📈 Total models available: {model_info['models']['total_available_models']}")
        print()
        
        # Step 6: Download model if needed (after dependencies are installed)
        print_step(6, total_steps, "Downloading default model")
        if not model_info['models']['default_model_available']:
            print("   🔍 Default model not found, attempting download...")
            if setup_manager._download_default_model():
                print("   ✅ Model download completed successfully!")
                # Refresh model info after download
                model_info = manager.get_model_info()
                print(f"   📊 Total models now available: {model_info['models']['total_available_models']}")
            else:
                print("   ⚠️  Model download failed - system will use fallback mode")
                print("   💡 Model download requires dependencies to be installed first")
                print("   💡 Try running: pip install mlx-lm transformers")
        else:
            print("   ✅ Default model already available")
        print()
        
        # Step 7: Report completion and next steps
        print_step(7, total_steps, "Setup complete!")
        
        print("   🎉 AI Security Analysis System setup completed successfully!")
        print()
        print("📁 Directory Structure Created:")
        print(f"   🗂️  Project root: {Path.cwd()}")
        print(f"   🐍 Virtual environment: {config.venv_dir}")
        print(f"   📊 Data directory: {config.data_dir}")
        print(f"   📊 Results directory: {config.results_dir}")
        print(f"   🤖 Shared models: ~/shared-olmo-models/")
        print()
        
        print("🚀 Quick Start Guide:")
        print("   1. Activate virtual environment:")
        print(f"      source {config.venv_dir}/bin/activate")
        print()
        print("   2. Navigate to analysis directory:")
        print("      cd security-ai-analysis")
        print()
        print("   3. Test the system:")
        print("      python3 process_artifacts.py --help")
        print("      python3 -c \"from config_manager import OLMoSecurityConfig; print('Config loaded!')\"")
        print()
        print("   4. Run validation tests:")
        print("      scripts/tests/test-phase1.sh")
        print("      scripts/tests/test-phase2.sh")
        print()
        
        
        print("📚 Configuration:")
        print(f"   Config file: config/olmo-security-config.yaml")
        print(f"   Environment overrides: OLMO_BASE_MODELS_DIR, OLMO_DEFAULT_BASE_MODEL, etc.")
        print()
        
        print("✅ Setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Setup failed with error: {e}")
        print("🔧 Please check the error message and try again.")
        print("💡 You may need to install Python dependencies manually.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)