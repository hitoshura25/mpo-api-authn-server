"""
AI Security Analysis Model Manager

Provides model management functionality for the AI Security Dataset Research
Initiative. Handles model availability checking, project setup, and shared
model directory management.

This component automates project structure creation and provides information
about available models without requiring them to be downloaded.
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

from config_manager import OLMoSecurityConfig


class OLMoModelManager:
    """
    Model management and project setup for AI Security Analysis system.
    
    Responsibilities:
    - Create and manage project directory structure
    - Create and manage shared model directories (external, shareable)
    - Provide information about available models
    - Set up virtual environments and dependencies
    - Model availability checking without requiring downloads
    """
    
    def __init__(self):
        """Initialize model manager with configuration."""
        self.config = OLMoSecurityConfig()
        
    def setup_project_structure(self) -> Dict[str, str]:
        """
        Create complete project directory structure.
        
        Creates both project-specific directories and external shared model
        directories. Project directories are fixed within the project structure,
        while model directories are configurable via config.
        
        Returns:
            Dictionary summarizing created directories and their purposes.
        """
        created_dirs = {}
        
        # Create project directories (fixed within project structure)
        project_dirs = {
            'venv': (self.config.venv_dir, 'Project-specific virtual environment'),
            'data': (self.config.data_dir, 'Raw security artifacts (JSON/SARIF from GitHub Actions)'),
            'results': (self.config.results_dir, 'Intermediate analysis before final dataset creation')
        }
        
        for name, (directory, description) in project_dirs.items():
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs[f'project_{name}'] = f"{directory} - {description}"
            
        # Create shared model directories (external, shareable across projects)
        model_dirs = {
            'base_models': (self.config.base_models_dir, 'Pre-trained base models (shareable across projects)'),
            'fine_tuned_models': (self.config.fine_tuned_models_dir, 'Project-specific fine-tuned models')
        }
        
        for name, (directory, description) in model_dirs.items():
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs[f'shared_{name}'] = f"{directory} - {description}"
            
        return created_dirs
        
    def ensure_base_model_available(self, model_name: Optional[str] = None) -> Path:
        """
        Check if base model is available, return path if found.
        
        Args:
            model_name: Name of the model to check. If None, uses default_base_model.
            
        Returns:
            Path to the model directory if it exists.
            
        Raises:
            FileNotFoundError: If the model directory doesn't exist.
            
        Note:
            This method does NOT download models - it only checks availability.
            Model download/conversion would be implemented separately when needed.
        """
        model_name = model_name or self.config.default_base_model
        model_path = self.config.base_models_dir / model_name
        
        if model_path.exists():
            return model_path
            
        # Model not found - provide helpful error message
        available_models = self.get_available_base_models()
        available_str = ', '.join(available_models) if available_models else 'none'
        
        raise FileNotFoundError(
            f"Base model '{model_name}' not found at {model_path}. "
            f"Available models: {available_str}. "
            f"Model download/conversion not implemented yet."
        )
        
    def get_available_base_models(self) -> List[str]:
        """
        Get list of available base models.
        
        Returns:
            List of base model names (directory names) that exist.
        """
        if not self.config.base_models_dir.exists():
            return []
            
        return [
            p.name for p in self.config.base_models_dir.iterdir() 
            if p.is_dir() and not p.name.startswith('.')
        ]
        
    def get_available_fine_tuned_models(self) -> List[str]:
        """
        Get list of available fine-tuned models.
        
        Returns:
            List of fine-tuned model names (directory names) that exist.
        """
        if not self.config.fine_tuned_models_dir.exists():
            return []
            
        return [
            p.name for p in self.config.fine_tuned_models_dir.iterdir() 
            if p.is_dir() and not p.name.startswith('.')
        ]
        
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about model configuration and availability.
        
        Returns:
            Dictionary containing:
            - Directory paths for base and fine-tuned models
            - Default model configuration
            - Lists of available models
            - Model availability status
            - Project directory information
        """
        available_base = self.get_available_base_models()
        available_fine_tuned = self.get_available_fine_tuned_models()
        
        # Check if default model is available
        default_model_available = False
        default_model_path = None
        try:
            default_model_path = self.ensure_base_model_available()
            default_model_available = True
        except FileNotFoundError:
            pass
            
        return {
            'directories': {
                'base_models_dir': str(self.config.base_models_dir),
                'fine_tuned_models_dir': str(self.config.fine_tuned_models_dir),
                'project_venv_dir': str(self.config.venv_dir),
                'project_data_dir': str(self.config.data_dir),
                'project_results_dir': str(self.config.results_dir),
            },
            'models': {
                'default_base_model': self.config.default_base_model,
                'default_model_available': default_model_available,
                'default_model_path': str(default_model_path) if default_model_path else None,
                'available_base_models': available_base,
                'available_fine_tuned_models': available_fine_tuned,
                'total_available_models': len(available_base) + len(available_fine_tuned)
            },
            'status': {
                'base_models_dir_exists': self.config.base_models_dir.exists(),
                'fine_tuned_models_dir_exists': self.config.fine_tuned_models_dir.exists(),
                'project_venv_exists': self.config.venv_dir.exists(),
                'project_structure_ready': (
                    self.config.venv_dir.exists() and 
                    self.config.data_dir.exists() and 
                    self.config.results_dir.exists()
                )
            }
        }
        
    def create_virtual_environment(self) -> bool:
        """
        Create virtual environment in project-specific location.
        
        Returns:
            True if virtual environment was created or already exists.
            False if creation failed.
        """
        # Check if virtual environment exists and is functional
        if self.config.venv_dir.exists():
            # Verify it's a proper venv by checking for key files
            python_path = self.config.venv_dir / "bin" / "python"
            pip_path = self.config.venv_dir / "bin" / "pip"
            if python_path.exists() and pip_path.exists():
                return True
            else:
                # Directory exists but is incomplete - remove and recreate
                import shutil
                shutil.rmtree(self.config.venv_dir)
                print(f"   🔧 Removing incomplete virtual environment...")
            
        try:
            # Ensure parent directory exists
            self.config.venv_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Create virtual environment
            subprocess.run([
                sys.executable, "-m", "venv", str(self.config.venv_dir)
            ], check=True, capture_output=True, text=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to create virtual environment: {e}")
            return False
            
    def install_dependencies(self, requirements_file: Optional[Path] = None) -> bool:
        """
        Install dependencies in the project virtual environment.
        
        Args:
            requirements_file: Path to requirements.txt. If None, uses default location.
            
        Returns:
            True if dependencies were installed successfully.
            False if installation failed.
        """
        if not self.config.venv_dir.exists():
            print("Virtual environment not found. Creating...")
            if not self.create_virtual_environment():
                return False
                
        # Default requirements file location
        if requirements_file is None:
            requirements_file = Path(__file__).parent / "requirements.txt"
            
        if not requirements_file.exists():
            print(f"Requirements file not found: {requirements_file}")
            return False
            
        # Install dependencies using pip from virtual environment
        pip_path = self.config.venv_dir / "bin" / "pip"
        if not pip_path.exists():
            # Windows support
            pip_path = self.config.venv_dir / "Scripts" / "pip.exe"
            if not pip_path.exists():
                print("pip not found in virtual environment")
                return False
                
        try:
            subprocess.run([
                str(pip_path), "install", "-r", str(requirements_file)
            ], check=True, capture_output=True, text=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            return False
            
    def validate_setup(self) -> Dict[str, bool]:
        """
        Validate that the complete setup is working correctly.
        
        Returns:
            Dictionary with validation results for different components.
        """
        results = {}
        
        # Check directory structure
        results['directories_created'] = (
            self.config.venv_dir.exists() and
            self.config.data_dir.exists() and
            self.config.results_dir.exists() and
            self.config.base_models_dir.exists() and
            self.config.fine_tuned_models_dir.exists()
        )
        
        # Check virtual environment
        python_path = self.config.venv_dir / "bin" / "python"
        if not python_path.exists():
            python_path = self.config.venv_dir / "Scripts" / "python.exe"
        results['virtual_environment'] = python_path.exists()
        
        # Check if we can import the config manager from the venv
        if results['virtual_environment']:
            try:
                # Test basic Python functionality in venv
                subprocess.run([
                    str(python_path), "-c", "import sys; print('Virtual env Python works')"
                ], check=True, capture_output=True, text=True)
                results['venv_python_functional'] = True
            except subprocess.CalledProcessError:
                results['venv_python_functional'] = False
        else:
            results['venv_python_functional'] = False
            
        # Check model configuration
        results['model_config_valid'] = True
        try:
            self.get_model_info()
        except Exception:
            results['model_config_valid'] = False
            
        return results


def main():
    """Main function for direct script execution."""
    manager = OLMoModelManager()
    
    print("🔧 AI Security Analysis Model Manager")
    print("=" * 50)
    
    model_info = manager.get_model_info()
    
    print(f"📁 Base models directory: {model_info['directories']['base_models_dir']}")
    print(f"📁 Fine-tuned models directory: {model_info['directories']['fine_tuned_models_dir']}")
    print(f"📁 Project venv: {model_info['directories']['project_venv_dir']}")
    print(f"📁 Project data: {model_info['directories']['project_data_dir']}")
    print(f"📁 Project results: {model_info['directories']['project_results_dir']}")
    print()
    
    print(f"🤖 Default model: {model_info['models']['default_base_model']}")
    print(f"✅ Default model available: {model_info['models']['default_model_available']}")
    print(f"📊 Available base models: {model_info['models']['available_base_models']}")
    print(f"📊 Available fine-tuned models: {model_info['models']['available_fine_tuned_models']}")
    print(f"📈 Total models: {model_info['models']['total_available_models']}")


if __name__ == "__main__":
    main()