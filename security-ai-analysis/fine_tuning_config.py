"""
Fine-Tuning Configuration Manager

Provides centralized configuration management for MLX fine-tuning operations.
Extends the existing OLMoSecurityConfig system with fine-tuning specific settings.

This module handles:
- Fine-tuning hyperparameters
- Model output paths and naming  
- HuggingFace upload configuration
- MLX-specific optimization settings
- Workspace directory management
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


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
    max_stage1_iters: int
    max_stage2_iters: int
    
    # MLX settings
    quantization: str
    memory_efficient: bool
    gradient_checkpointing: bool
    
    # HuggingFace upload settings
    upload_enabled: bool
    repo_prefix: str
    private_repos: bool
    
    # Daemon control
    skip_in_daemon: bool
    
    @classmethod
    def load_from_config(cls, config_file: Optional[Path] = None) -> 'FineTuningConfig':
        """Load fine-tuning configuration from YAML file"""
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "olmo-security-config.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract fine-tuning configuration
        ft_config = config.get('fine_tuning', {})
        if not ft_config:
            raise ValueError("Fine-tuning configuration section not found in config file")
        
        # Resolve paths with environment variable overrides
        project_root = Path(__file__).parent.parent
        workspace_dir = Path(
            os.getenv('OLMO_WORKSPACE_DIR', str(project_root / ft_config['workspace_dir']))
        ).expanduser()
        
        base_models_dir = Path(
            os.getenv('OLMO_BASE_MODELS_DIR', config['base_models_dir'])
        ).expanduser()
        
        fine_tuned_models_dir = Path(
            os.getenv('OLMO_FINE_TUNED_MODELS_DIR', config['fine_tuned_models_dir'])
        ).expanduser()
        
        # HuggingFace settings
        hf_config = ft_config.get('huggingface', {})
        
        # Training settings
        train_config = ft_config.get('training', {})
        
        # MLX settings
        mlx_config = ft_config.get('mlx', {})
        
        return cls(
            workspace_dir=workspace_dir,
            base_models_dir=base_models_dir,
            fine_tuned_models_dir=fine_tuned_models_dir,
            base_model_name=os.getenv('OLMO_DEFAULT_BASE_MODEL', config['default_base_model']),
            output_model_name=ft_config['default_output_name'],
            learning_rate=float(os.getenv('OLMO_LEARNING_RATE', train_config.get('learning_rate', 2e-5))),
            batch_size=int(os.getenv('OLMO_BATCH_SIZE', train_config.get('batch_size', 1))),  # Reduced from 4 to 1 to avoid Metal GPU memory issues
            max_epochs=int(os.getenv('OLMO_MAX_EPOCHS', train_config.get('max_epochs', 3))),
            warmup_steps=int(os.getenv('OLMO_WARMUP_STEPS', train_config.get('warmup_steps', 100))),
            save_steps=int(os.getenv('OLMO_SAVE_STEPS', train_config.get('save_steps', 500))),
            eval_steps=int(os.getenv('OLMO_EVAL_STEPS', train_config.get('eval_steps', 250))),
            max_stage1_iters=int(os.getenv('OLMO_MAX_STAGE1_ITERS', train_config.get('max_stage1_iters', 100))),
            max_stage2_iters=int(os.getenv('OLMO_MAX_STAGE2_ITERS', train_config.get('max_stage2_iters', 150))),
            quantization=mlx_config.get('quantization', 'q4'),
            memory_efficient=mlx_config.get('memory_efficient', True),
            gradient_checkpointing=mlx_config.get('gradient_checkpointing', True),
            upload_enabled=hf_config.get('upload_enabled', True),
            repo_prefix=hf_config.get('default_repo_prefix', 'hitoshura25'),
            private_repos=hf_config.get('private_repos', False),
            skip_in_daemon=ft_config.get('skip_in_daemon', False)
        )
    
    def get_base_model_path(self) -> Path:
        """Get path to base model for fine-tuning"""
        model_path = self.base_models_dir / self.base_model_name
        if not model_path.exists():
            raise FileNotFoundError(f"Base model not found: {model_path}")
        return model_path
    
    def get_output_model_path(self, custom_name: Optional[str] = None) -> Path:
        """Get path where fine-tuned model will be saved"""
        model_name = custom_name or self.output_model_name
        return self.fine_tuned_models_dir / model_name
    
    def setup_workspace(self):
        """Create fine-tuning workspace directories"""
        subdirs = ['training_data', 'checkpoints', 'logs', 'temp']
        
        for subdir in subdirs:
            dir_path = self.workspace_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created workspace directory: {dir_path}")
        
        # Create shared model directories if they don't exist
        self.fine_tuned_models_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Fine-tuning workspace initialized: {self.workspace_dir}")
    
    def validate_configuration(self) -> bool:
        """Validate configuration and required dependencies"""
        errors = []
        
        # Check base model availability
        try:
            base_model_path = self.get_base_model_path()
            logger.debug(f"Base model found: {base_model_path}")
        except FileNotFoundError as e:
            errors.append(str(e))
        
        # Validate training parameters
        if float(self.learning_rate) <= 0:
            errors.append(f"Invalid learning rate: {self.learning_rate}")
        
        if self.batch_size <= 0:
            errors.append(f"Invalid batch size: {self.batch_size}")
        
        if self.max_epochs <= 0:
            errors.append(f"Invalid max epochs: {self.max_epochs}")
        
        # Check workspace can be created
        try:
            self.workspace_dir.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create workspace parent directory: {e}")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            return False
        
        logger.info("✅ Fine-tuning configuration validation passed")
        return True
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging/debugging"""
        return {
            'workspace_dir': str(self.workspace_dir),
            'base_models_dir': str(self.base_models_dir),
            'fine_tuned_models_dir': str(self.fine_tuned_models_dir),
            'base_model_name': self.base_model_name,
            'output_model_name': self.output_model_name,
            'training_params': {
                'learning_rate': self.learning_rate,
                'batch_size': self.batch_size,
                'max_epochs': self.max_epochs,
                'warmup_steps': self.warmup_steps
            },
            'mlx_settings': {
                'quantization': self.quantization,
                'memory_efficient': self.memory_efficient,
                'gradient_checkpointing': self.gradient_checkpointing
            },
            'upload_settings': {
                'upload_enabled': self.upload_enabled,
                'repo_prefix': self.repo_prefix,
                'private_repos': self.private_repos
            },
            'daemon_control': {
                'skip_in_daemon': self.skip_in_daemon
            }
        }


def get_default_config() -> FineTuningConfig:
    """Get default fine-tuning configuration (convenience function)"""
    return FineTuningConfig.load_from_config()


# Test configuration loading when run directly
if __name__ == "__main__":
    try:
        config = get_default_config()
        print("✅ Fine-tuning configuration loaded successfully!")
        print("\nConfiguration Summary:")
        summary = config.get_config_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        print(f"\nValidation: {config.validate_configuration()}")
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        exit(1)