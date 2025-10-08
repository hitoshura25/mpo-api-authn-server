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
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class LoRASection:
    """LoRA-specific configuration for parameter-efficient fine-tuning"""
    rank: int
    alpha: int
    dropout: float
    target_modules: List[str]


@dataclass
class FineTuningSection:
    """Fine-tuning specific configuration"""
    # Directories
    workspace_dir: Path
    default_output_name: str

    # Training parameters
    learning_rate: float
    batch_size: int
    max_epochs: int
    warmup_steps: int
    save_steps: int
    eval_steps: int
    max_stage1_iters: int
    max_stage2_iters: int

    # LoRA settings
    lora: LoRASection

    # MLX settings
    quantization: str
    memory_efficient: bool
    gradient_checkpointing: bool

    # HuggingFace settings
    upload_enabled: bool
    default_repo_prefix: str
    private_repos: bool
    skip_in_daemon: bool
    upload_staging_dir: Path


@dataclass
class KnowledgeBaseSection:
    """Knowledge base specific configuration"""
    base_dir: Path
    embeddings_model: str
    vector_store_type: str


@dataclass
class ValidationSection:
    """Model validation specific configuration"""
    stage1_threshold: float
    stage2_threshold: float
    sequential_threshold: float


@dataclass
class MultiDomainValidationSection:
    """Multi-domain validation thresholds"""
    overall_threshold: float
    category_minimum: float
    high_specialization: float
    medium_specialization: float


@dataclass
class MultiDomainSection:
    """Multi-domain security specialization configuration (always enabled)"""
    target_categories: List[str]
    category_weights: Dict[str, float]
    validation: MultiDomainValidationSection


class OLMoSecurityConfig:
    """
    Unified configuration manager for AI Security Analysis system.

    Manages all configuration aspects:
    - External shared model directories (base and fine-tuned models)
    - Internal project directories (data, results, venv)
    - Fine-tuning parameters and workspace management
    - Knowledge base configuration
    - MLX optimization settings
    - HuggingFace upload configuration

    Supports comprehensive environment variable overrides (OLMO_* prefix) for all settings.
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
        self.data_dir = project_root / "security-ai-analysis" / "data"
        self.results_dir = project_root / "security-ai-analysis" / "results"
        
        # Model configuration with environment variable override
        self.default_base_model = os.getenv('OLMO_DEFAULT_BASE_MODEL',
                                          config.get('default_base_model', 'OLMo-2-1B-mlx-q4'))

        # HuggingFace model ID for the base model (for reproducibility in uploads)
        # This is the publicly accessible model identifier on HuggingFace Hub
        self.base_model_hf_id = os.getenv('OLMO_BASE_MODEL_HF_ID',
                                         config.get('base_model_hf_id', 'allenai/OLMo-2-0425-1B-Instruct'))

        # Load nested configuration sections
        self.fine_tuning = self._load_fine_tuning_section(config, project_root)
        self.knowledge_base = self._load_knowledge_base_section(config, project_root)
        self.validation = self._load_validation_section(config)
        self.multi_domain = self._load_multi_domain_section(config)
        
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
            'data_dir': str(self.data_dir),
            'results_dir': str(self.results_dir),
            'default_base_model': self.default_base_model,
            'environment_overrides': {
                'OLMO_BASE_MODELS_DIR': os.getenv('OLMO_BASE_MODELS_DIR'),
                'OLMO_FINE_TUNED_MODELS_DIR': os.getenv('OLMO_FINE_TUNED_MODELS_DIR'),
                'OLMO_DEFAULT_BASE_MODEL': os.getenv('OLMO_DEFAULT_BASE_MODEL'),
            }
        }

    def _load_fine_tuning_section(self, config: Dict[str, Any], project_root: Path) -> FineTuningSection:
        """Load fine-tuning configuration section with environment variable overrides."""
        ft_config = config.get('fine_tuning', {})
        if not ft_config:
            raise ValueError("Fine-tuning configuration section not found in config file")

        # Resolve workspace directory with environment variable override
        workspace_dir = Path(
            os.getenv('OLMO_WORKSPACE_DIR', str(project_root / ft_config['workspace_dir']))
        ).expanduser()

        # Training parameters with environment variable overrides
        train_config = ft_config.get('training', {})

        # MLX settings
        mlx_config = ft_config.get('mlx', {})

        # LoRA settings
        lora_config = ft_config.get('lora', {})

        # HuggingFace settings
        hf_config = ft_config.get('huggingface', {})

        # Resolve upload staging directory
        upload_staging_dir = Path(
            os.getenv('OLMO_UPLOAD_STAGING_DIR', str(workspace_dir / hf_config.get('upload_staging_dir', 'upload_staging')))
        ).expanduser()

        return FineTuningSection(
            workspace_dir=workspace_dir,
            default_output_name=ft_config['default_output_name'],
            # Training parameters with environment overrides
            learning_rate=float(os.getenv('OLMO_LEARNING_RATE', train_config.get('learning_rate', 2e-5))),
            batch_size=int(os.getenv('OLMO_BATCH_SIZE', train_config.get('batch_size', 1))),
            max_epochs=int(os.getenv('OLMO_MAX_EPOCHS', train_config.get('max_epochs', 3))),
            warmup_steps=int(os.getenv('OLMO_WARMUP_STEPS', train_config.get('warmup_steps', 100))),
            save_steps=int(os.getenv('OLMO_SAVE_STEPS', train_config.get('save_steps', 500))),
            eval_steps=int(os.getenv('OLMO_EVAL_STEPS', train_config.get('eval_steps', 250))),
            max_stage1_iters=int(os.getenv('OLMO_MAX_STAGE1_ITERS', train_config.get('max_stage1_iters', 100))),
            max_stage2_iters=int(os.getenv('OLMO_MAX_STAGE2_ITERS', train_config.get('max_stage2_iters', 150))),
            # LoRA settings
            lora=LoRASection(
                rank=int(os.getenv('OLMO_LORA_RANK', lora_config.get('rank', 8))),
                alpha=int(os.getenv('OLMO_LORA_ALPHA', lora_config.get('alpha', 16))),
                dropout=float(os.getenv('OLMO_LORA_DROPOUT', lora_config.get('dropout', 0.05))),
                target_modules=lora_config.get('target_modules', ["q_proj", "v_proj"])
            ),
            # MLX settings
            quantization=mlx_config.get('quantization', 'q4'),
            memory_efficient=mlx_config.get('memory_efficient', True),
            gradient_checkpointing=mlx_config.get('gradient_checkpointing', True),
            # HuggingFace settings
            upload_enabled=hf_config.get('upload_enabled', True),
            default_repo_prefix=hf_config.get('default_repo_prefix', 'hitoshura25'),
            private_repos=hf_config.get('private_repos', False),
            skip_in_daemon=ft_config.get('skip_in_daemon', False),
            upload_staging_dir=upload_staging_dir
        )

    def _load_knowledge_base_section(self, config: Dict[str, Any], project_root: Path) -> KnowledgeBaseSection:
        """Load knowledge base configuration section with environment variable overrides."""
        kb_config = config.get('knowledge_base', {})

        # Resolve knowledge base directory with environment variable override
        base_dir = Path(
            os.getenv('OLMO_KNOWLEDGE_BASE_DIR', str(project_root / kb_config.get('base_dir', 'security-ai-analysis/knowledge_base')))
        ).expanduser()

        return KnowledgeBaseSection(
            base_dir=base_dir,
            embeddings_model=kb_config.get('embeddings_model', 'sentence-transformers/all-MiniLM-L6-v2'),
            vector_store_type=kb_config.get('vector_store_type', 'faiss')
        )

    def _load_validation_section(self, config: Dict[str, Any]) -> ValidationSection:
        """Load validation configuration section with environment variable overrides."""
        val_config = config.get('validation', {})

        return ValidationSection(
            stage1_threshold=float(os.getenv('OLMO_STAGE1_VALIDATION_THRESHOLD', val_config.get('stage1_threshold', 0.7))),
            stage2_threshold=float(os.getenv('OLMO_STAGE2_VALIDATION_THRESHOLD', val_config.get('stage2_threshold', 0.7))),
            sequential_threshold=float(os.getenv('OLMO_SEQUENTIAL_VALIDATION_THRESHOLD', val_config.get('sequential_threshold', 0.6)))
        )

    def _load_multi_domain_section(self, config: Dict[str, Any]) -> MultiDomainSection:
        """Load multi-domain security specialization configuration with environment variable overrides."""
        md_config = config.get('multi_domain', {})

        # Default categories and weights if not specified
        default_categories = [
            'webauthn_security', 'web_security', 'code_vulnerabilities',
            'container_security', 'dependency_vulnerabilities',
            'mobile_security', 'infrastructure_security'
        ]

        default_weights = {
            'webauthn_security': 1.5,
            'web_security': 1.2,
            'code_vulnerabilities': 1.0,
            'container_security': 0.9,
            'dependency_vulnerabilities': 0.8,
            'mobile_security': 0.7,
            'infrastructure_security': 0.6
        }

        # Load validation section with defaults
        val_config = md_config.get('validation', {})
        validation_section = MultiDomainValidationSection(
            overall_threshold=float(os.getenv('OLMO_MULTI_DOMAIN_OVERALL_THRESHOLD', val_config.get('overall_threshold', 0.75))),
            category_minimum=float(os.getenv('OLMO_MULTI_DOMAIN_CATEGORY_MIN', val_config.get('category_minimum', 0.40))),
            high_specialization=float(os.getenv('OLMO_MULTI_DOMAIN_HIGH_THRESHOLD', val_config.get('high_specialization', 0.75))),
            medium_specialization=float(os.getenv('OLMO_MULTI_DOMAIN_MEDIUM_THRESHOLD', val_config.get('medium_specialization', 0.60)))
        )

        # Load target categories with environment variable override
        target_categories_env = os.getenv('OLMO_MULTI_DOMAIN_TARGET_CATEGORIES')
        if target_categories_env:
            target_categories = [cat.strip() for cat in target_categories_env.split(',')]
        else:
            target_categories = md_config.get('target_categories', default_categories)

        # Load category weights with environment variable override
        category_weights_env = os.getenv('OLMO_MULTI_DOMAIN_CATEGORY_WEIGHTS')
        if category_weights_env:
            try:
                import json
                category_weights = json.loads(category_weights_env)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in OLMO_MULTI_DOMAIN_CATEGORY_WEIGHTS environment variable: {category_weights_env}. Error: {e}") from e
        else:
            category_weights = md_config.get('category_weights', default_weights)

        return MultiDomainSection(
            target_categories=target_categories,
            category_weights=category_weights,
            validation=validation_section
        )

    def get_workspace_path(self) -> Path:
        """Get fine-tuning workspace directory."""
        return self.fine_tuning.workspace_dir

    def get_training_runs_dir(self) -> Path:
        """Get structured training runs directory."""
        return self.fine_tuned_models_dir / "training-runs"

    def get_output_model_path(self, custom_name: Optional[str] = None) -> Path:
        """Get path where fine-tuned model will be saved (legacy single-model format)."""
        model_name = custom_name or self.fine_tuning.default_output_name
        return self.fine_tuned_models_dir / model_name

    def setup_workspace(self):
        """Create fine-tuning workspace directories."""
        subdirs = ['training_data', 'checkpoints', 'logs', 'temp']

        for subdir in subdirs:
            dir_path = self.fine_tuning.workspace_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)

        # Create shared model directories if they don't exist
        self.fine_tuned_models_dir.mkdir(parents=True, exist_ok=True)

    def validate_fine_tuning_configuration(self) -> bool:
        """Validate fine-tuning configuration and required dependencies."""
        errors = []

        # Check base model availability
        try:
            base_model_path = self.get_base_model_path()
        except FileNotFoundError as e:
            errors.append(str(e))

        # Validate training parameters
        if self.fine_tuning.learning_rate <= 0:
            errors.append(f"Invalid learning rate: {self.fine_tuning.learning_rate}")

        if self.fine_tuning.batch_size <= 0:
            errors.append(f"Invalid batch size: {self.fine_tuning.batch_size}")

        if self.fine_tuning.max_epochs <= 0:
            errors.append(f"Invalid max epochs: {self.fine_tuning.max_epochs}")

        # Check workspace can be created
        try:
            self.fine_tuning.workspace_dir.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            # Fail fast on permission issues - infrastructure problem
            raise RuntimeError(f"Workspace directory creation failed - permission issue requires investigation: {e}") from e
        except OSError as e:
            # Fail fast on disk/filesystem issues - infrastructure problem
            raise RuntimeError(f"Workspace directory creation failed - filesystem issue requires investigation: {e}") from e
        except Exception as e:
            errors.append(f"Cannot create workspace parent directory: {e}")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            return False

        return True


# For convenience, provide a default instance
def get_default_config() -> OLMoSecurityConfig:
    """Get the default configuration instance."""
    return OLMoSecurityConfig()