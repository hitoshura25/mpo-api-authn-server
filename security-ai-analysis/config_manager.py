"""
AI Security Analysis Configuration Manager

Provides centralized, portable configuration management for the AI Security Dataset
Research Initiative. Supports environment variable overrides and fail-fast validation.

This replaces hardcoded paths throughout the codebase with configurable,
portable paths that work across different development environments.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class OLMoSecurityConfig:
    """
    Centralized configuration manager for AI Security Analysis system.
    
    Manages paths for:
    - External shared model directories (base and fine-tuned models)
    - Internal project directories (data, results, venv)
    - Model configuration settings
    
    Supports environment variable overrides for testing and CI environments.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration from YAML file with environment variable overrides.
        
        Args:
            config_file: Path to YAML configuration file. If None, uses default location.
        """
        # Load configuration from YAML file
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "olmo-security-config.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Configure external model directories (shareable across projects)
        # Environment variable overrides support testing and CI
        base_models_dir = os.getenv('OLMO_BASE_MODELS_DIR', config['base_models_dir'])
        fine_tuned_models_dir = os.getenv('OLMO_FINE_TUNED_MODELS_DIR', config['fine_tuned_models_dir'])
        
        self.base_models_dir = Path(base_models_dir).expanduser()
        self.fine_tuned_models_dir = Path(fine_tuned_models_dir).expanduser()
        
        # Configure project directories (fixed within project structure)
        # These are NOT configurable - they follow standard project layout
        project_root = Path(__file__).parent.parent
        self.venv_dir = project_root / "security-ai-analysis" / "venv"
        self.data_dir = project_root / "security-ai-analysis" / "data"
        self.results_dir = project_root / "security-ai-analysis" / "results"
        
        # Model configuration with environment variable override
        self.default_base_model = os.getenv('OLMO_DEFAULT_BASE_MODEL', 
                                          config.get('default_base_model', 'OLMo-2-1B-mlx-q4'))
        
    def get_base_model_path(self, model_name: Optional[str] = None) -> Path:
        """
        Get path to base model (pre-trained, shareable across projects).
        
        Args:
            model_name: Name of the model. If None, uses default_base_model.
            
        Returns:
            Path to the model directory.
            
        Raises:
            FileNotFoundError: If the model directory doesn't exist.
        """
        model_name = model_name or self.default_base_model
        model_path = self.base_models_dir / model_name
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Base model '{model_name}' not found at {model_path}. "
                f"Base models directory: {self.base_models_dir}"
            )
        return model_path
    
    def get_fine_tuned_model_path(self, model_name: str) -> Path:
        """
        Get path to fine-tuned model (project-specific, shareable results).
        
        Args:
            model_name: Name of the fine-tuned model.
            
        Returns:
            Path to the fine-tuned model directory.
            
        Raises:
            FileNotFoundError: If the model directory doesn't exist.
        """
        model_path = self.fine_tuned_models_dir / model_name
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Fine-tuned model '{model_name}' not found at {model_path}. "
                f"Fine-tuned models directory: {self.fine_tuned_models_dir}"
            )
        return model_path
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration for debugging and validation.
        
        Returns:
            Dictionary containing all configuration paths and settings.
        """
        return {
            'base_models_dir': str(self.base_models_dir),
            'fine_tuned_models_dir': str(self.fine_tuned_models_dir),
            'venv_dir': str(self.venv_dir),
            'data_dir': str(self.data_dir),
            'results_dir': str(self.results_dir),
            'default_base_model': self.default_base_model,
            'environment_overrides': {
                'OLMO_BASE_MODELS_DIR': os.getenv('OLMO_BASE_MODELS_DIR'),
                'OLMO_FINE_TUNED_MODELS_DIR': os.getenv('OLMO_FINE_TUNED_MODELS_DIR'),
                'OLMO_DEFAULT_BASE_MODEL': os.getenv('OLMO_DEFAULT_BASE_MODEL'),
            }
        }


# For convenience, provide a default instance
def get_default_config() -> OLMoSecurityConfig:
    """Get the default configuration instance."""
    return OLMoSecurityConfig()