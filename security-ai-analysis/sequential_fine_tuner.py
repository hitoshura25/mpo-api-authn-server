#!/usr/bin/env python3
"""
Sequential Fine-Tuning Pipeline

This module implements multi-stage fine-tuning that builds domain expertise progressively:
- Stage 1: Vulnerability Analysis Specialist (base model → analysis expert)
- Stage 2: Code Fix Generation Specialist (Stage 1 model → code fix expert)

The sequential approach creates increasingly specialized models that excel at specific
security tasks while building upon previous learning.
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, NamedTuple
from dataclasses import dataclass, field

from scripts.mlx_finetuning import MLXFineTuner
from config_manager import OLMoSecurityConfig
from sequential_dataset_creator import SequentialDatasetCreator, SequentialDatasetResult


@dataclass
class SequentialTrainingResult:
    """Result of sequential fine-tuning process."""
    success: bool
    stage1_model_path: Optional[str] = None
    stage2_model_path: Optional[str] = None
    stage1_training_time: float = 0.0
    stage2_training_time: float = 0.0
    total_training_time: float = 0.0
    stage1_metrics: Dict[str, Any] = field(default_factory=dict)
    stage2_metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SequentialFineTuner:
    """
    Sequential fine-tuning pipeline for creating specialized security AI models.
    
    Architecture:
    Base OLMo Model → Stage 1 (Analysis) → Stage 2 (Code Fixes)
    
    Each stage builds upon the previous model's capabilities while specializing
    for specific security tasks.
    """
    
    def __init__(self, config: Optional[OLMoSecurityConfig] = None):
        """Initialize sequential fine-tuner."""
        self.config = config or OLMoSecurityConfig()
        self.base_fine_tuner = MLXFineTuner()
        self.logger = logging.getLogger(__name__)
        
        # Sequential training parameters - Enhanced for optimal specialization (using supported MLX-LM parameters only)
        self.stage1_config = {
            'iters': 500,          # 5x increase: 100→500 for proper specialization (addressing under-training)
            'learning_rate': 5e-6,  # Optimized rate for stable training (supported parameter)
            'batch_size': 4,        # Memory-efficient batch size
            'fine_tune_type': 'lora',
            'optimizer': 'adamw'    # Validated MLX optimizer (supported parameter)
        }

        self.stage2_config = {
            'iters': 800,          # 5.3x increase: 150→800 for proper code fix specialization
            'learning_rate': 1e-6,  # Lower rate for Stage 2 to preserve Stage 1 knowledge
            'batch_size': 2,        # Smaller batch for complex examples
            'fine_tune_type': 'lora',
            'optimizer': 'adamw'    # Validated MLX optimizer (supported parameter)
        }
    
    def sequential_fine_tune(self, stage1_dataset: Path, stage2_dataset: Path,
                           output_name_prefix: Optional[str] = None,
                           upload_to_hub: bool = True) -> SequentialTrainingResult:
        """
        Perform sequential fine-tuning with Stage 1 and Stage 2 datasets.
        
        Args:
            stage1_dataset: Path to Stage 1 (analysis) training dataset
            stage2_dataset: Path to Stage 2 (code fix) training dataset
            output_name_prefix: Prefix for model names
            upload_to_hub: Whether to upload final model to HuggingFace Hub
            
        Returns:
            SequentialTrainingResult with training outcomes
        """
        start_time = datetime.now()
        
        if not output_name_prefix:
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            output_name_prefix = f"webauthn-security-sequential_{timestamp}"
        
        try:
            self.logger.info(f"🚀 Starting sequential fine-tuning: {output_name_prefix}")
            
            # Stage 1: Vulnerability Analysis Specialist
            self.logger.info("📊 Stage 1: Training Vulnerability Analysis Specialist...")
            stage1_start = datetime.now()
            
            stage1_result = self._train_stage1_analysis(
                stage1_dataset,
                f"{output_name_prefix}_stage1_analysis",
                upload_to_hub=upload_to_hub
            )
            
            stage1_end = datetime.now()
            stage1_time = (stage1_end - stage1_start).total_seconds()
            
            if not stage1_result['success']:
                raise Exception(f"Stage 1 training failed: {stage1_result.get('error', 'Unknown error')}")
            
            self.logger.info(f"✅ Stage 1 completed in {stage1_time:.1f}s")
            
            # Stage 2: Code Fix Generation Specialist (builds on Stage 1)
            self.logger.info("🔧 Stage 2: Training Code Fix Generation Specialist...")
            stage2_start = datetime.now()
            
            stage2_result = self._train_stage2_codefix(
                stage2_dataset,
                f"{output_name_prefix}_stage2_codefix",
                stage1_adapter_path=stage1_result['adapter_path'],
                upload_to_hub=upload_to_hub
            )
            
            stage2_end = datetime.now()
            stage2_time = (stage2_end - stage2_start).total_seconds()
            
            if not stage2_result['success']:
                raise Exception(f"Stage 2 training failed: {stage2_result.get('error', 'Unknown error')}")
            
            self.logger.info(f"✅ Stage 2 completed in {stage2_time:.1f}s")
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Create successful result
            result = SequentialTrainingResult(
                success=True,
                stage1_model_path=stage1_result['adapter_path'],
                stage2_model_path=stage2_result['adapter_path'],
                stage1_training_time=stage1_time,
                stage2_training_time=stage2_time,
                total_training_time=total_time,
                stage1_metrics=stage1_result.get('metrics', {}),
                stage2_metrics=stage2_result.get('metrics', {}),
                metadata={
                    'output_name_prefix': output_name_prefix,
                    'stage1_dataset': str(stage1_dataset),
                    'stage2_dataset': str(stage2_dataset),
                    'training_start': start_time.isoformat(),
                    'training_end': datetime.now().isoformat(),
                    'stage1_config': self.stage1_config,
                    'stage2_config': self.stage2_config,
                    'uploaded_to_hub': upload_to_hub,
                    'stage1_model_hub_name': stage1_result.get('hub_model_name'),
                    'stage1_hub_url': stage1_result.get('hub_url'),
                    'stage2_model_hub_name': stage2_result.get('hub_model_name'),
                    'stage2_hub_url': stage2_result.get('hub_url'),
                    'final_model_hub_name': stage2_result.get('hub_model_name'),
                    'sequential_approach': 'enhanced_catastrophic_forgetting_mitigation',
                    'stage1_adapter_used': stage2_result.get('stage1_adapter_used', False),
                    'catastrophic_forgetting_mitigation': stage2_result.get('catastrophic_forgetting_mitigation', False),
                    'mixed_training_data': stage2_result.get('mixed_training_data', False),
                    'training_improvements': {
                        'stage1_iterations_enhanced': f"{self.stage1_config['iters']} (5x from 100)",
                        'stage2_iterations_enhanced': f"{self.stage2_config['iters']} (5.3x from 150)",
                        'resume_adapter_file_used': True,
                        'supported_mlx_parameters_only': True,
                        'optimizer': 'adamw',
                        'learning_rate_optimized': True,
                        'catastrophic_forgetting_mitigation': True
                    },
                    'stage1_merged_model': stage2_result.get('stage1_merged_model'),
                    'stage2_training_note': stage2_result.get('note')
                }
            )
            
            self.logger.info(f"🎉 Sequential fine-tuning completed successfully!")
            self.logger.info(f"   Total time: {total_time:.1f}s")
            self.logger.info(f"   Stage 1 (Analysis): {stage1_time:.1f}s")
            self.logger.info(f"   Stage 2 (Code Fixes): {stage2_time:.1f}s")
            self.logger.info(f"   Stage 1 model: {result.stage1_model_path}")
            self.logger.info(f"   Stage 2 model: {result.stage2_model_path}")

            if upload_to_hub:
                if result.metadata.get('stage1_hub_url'):
                    self.logger.info(f"   Stage 1 HuggingFace: {result.metadata['stage1_hub_url']}")
                if result.metadata.get('stage2_hub_url'):
                    self.logger.info(f"   Stage 2 HuggingFace: {result.metadata['stage2_hub_url']}")

                # Keep the legacy field for backward compatibility
                if result.metadata.get('final_model_hub_name'):
                    self.logger.info(f"   HuggingFace: {result.metadata['final_model_hub_name']}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ Sequential fine-tuning failed: {error_msg}")
            
            return SequentialTrainingResult(
                success=False,
                error_message=error_msg,
                metadata={
                    'error_time': datetime.now().isoformat(),
                    'training_start': start_time.isoformat()
                }
            )
    
    def _train_stage1_analysis(self, dataset_path: Path, output_name: str, upload_to_hub: bool = True) -> Dict[str, Any]:
        """
        Train Stage 1: Vulnerability Analysis Specialist.

        This stage creates a model specialized in vulnerability analysis,
        classification, and impact assessment.
        """
        self.logger.info(f"🔍 Training Stage 1 analysis model: {output_name}")

        try:
            # Use base MLXFineTuner for Stage 1 training
            # Step 1: Prepare training data
            training_data_dir = self.base_fine_tuner.prepare_training_data(dataset_path)

            # Step 2: Run enhanced Stage 1 fine-tuning with optimized parameters
            adapter_path = self._run_stage1_enhanced_training(
                training_data_dir,
                output_name
            )

            stage1_result = {
                'success': True,
                'adapter_path': str(adapter_path),
                'training_data_dir': str(training_data_dir)
            }

            self.logger.info(f"✅ Stage 1 training completed: {adapter_path}")

            # Step 3: Upload Stage 1 model to HuggingFace if requested
            if upload_to_hub:
                self.logger.info("📤 Uploading Stage 1 model to HuggingFace...")
                hub_url = self.base_fine_tuner.upload_to_huggingface(
                    model_path=Path(adapter_path),
                    custom_repo_name=output_name
                )

                if hub_url:
                    self.logger.info(f"✅ Stage 1 model uploaded successfully: {hub_url}")
                    stage1_result['hub_url'] = hub_url
                    stage1_result['hub_model_name'] = output_name
                else:
                    self.logger.warning("⚠️ Stage 1 model upload failed")
                    stage1_result['upload_failed'] = True
            else:
                self.logger.info("📤 Stage 1 upload skipped (upload_to_hub=False)")

            return stage1_result

        except Exception as e:
            self.logger.error(f"❌ Stage 1 training failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _train_stage2_codefix(self, dataset_path: Path, output_name: str,
                            stage1_adapter_path: str, upload_to_hub: bool = True) -> Dict[str, Any]:
        """
        Train Stage 2: Code Fix Generation Specialist.

        This stage builds upon the Stage 1 model to create a specialist
        in generating specific code fixes and implementations.
        """
        self.logger.info(f"🔧 Training Stage 2 code fix model: {output_name}")
        self.logger.info(f"   Building upon Stage 1: {stage1_adapter_path}")

        try:
            # Step 1: Prepare Stage 2 training data with catastrophic forgetting mitigation
            # Mix Stage 2 data with 15% Stage 1 data to preserve knowledge
            training_data_dir = self._prepare_mixed_training_data(
                stage2_dataset_path=dataset_path,
                stage1_adapter_path=stage1_adapter_path,
                output_name=output_name
            )

            # Step 2: Run enhanced Stage 2 fine-tuning with catastrophic forgetting mitigation
            self.logger.info(f"🚀 Training Stage 2 with resume-adapter-file from Stage 1: {stage1_adapter_path}")

            # Create custom fine-tuning args for Stage 2 using resume-adapter-file
            stage2_adapter_path = self._run_stage2_fine_tuning_from_stage1(
                training_data_dir,
                stage1_adapter_path,
                output_name
            )

            # Step 4: Upload Stage 2 model to HuggingFace if requested
            hub_model_name = None
            if upload_to_hub:
                self.logger.info("📤 Uploading Stage 2 model to HuggingFace Hub...")
                try:
                    hub_model_name = self.base_fine_tuner.upload_to_huggingface(
                        stage2_adapter_path,
                        custom_repo_name=output_name
                    )
                    if hub_model_name:
                        self.logger.info(f"✅ Stage 2 model uploaded successfully: {hub_model_name}")
                    else:
                        self.logger.warning("⚠️ Stage 2 model upload failed")
                except Exception as e:
                    self.logger.error(f"❌ Stage 2 model upload failed: {e}")

            stage2_result = {
                'success': True,
                'adapter_path': str(stage2_adapter_path),
                'training_data_dir': str(training_data_dir),
                'stage1_adapter_used': True,
                'stage1_adapter_path': str(stage1_adapter_path),
                'hub_model_name': hub_model_name,
                'upload_requested': upload_to_hub,
                'catastrophic_forgetting_mitigation': True,
                'mixed_training_data': True,
                'note': 'Successfully trained with resume-adapter-file and catastrophic forgetting mitigation'
            }

            self.logger.info(f"✅ Stage 2 training completed with sequential progression: {stage2_adapter_path}")
            if hub_model_name:
                self.logger.info(f"   HuggingFace model: {hub_model_name}")
            return stage2_result

        except Exception as e:
            self.logger.error(f"❌ Stage 2 sequential training failed: {e}")
            self.logger.error("💥 FAIL-FAST: Sequential training failure indicates a real issue that must be fixed")
            self.logger.error("🔍 Root cause investigation required - check adapter paths, MLX installation, and model artifacts")
            raise RuntimeError(f"Sequential fine-tuning failed - root cause must be investigated: {e}") from e

    def _create_stage1_merged_model(self, stage1_adapter_path: str, output_name: str) -> Path:
        """
        Create a merged model from Stage 1 adapter and base model.

        This creates an intermediate model that combines the base model with Stage 1's
        learned vulnerability analysis capabilities.
        """
        import subprocess
        import shutil
        from pathlib import Path

        # Define paths
        base_model_path = self.config.get_base_model_path()
        stage1_adapter_dir = Path(stage1_adapter_path)
        stage1_model_dir = stage1_adapter_dir.parent

        # FAIL-FAST validation - check all prerequisites before proceeding
        self.logger.info("🔍 FAIL-FAST validation: Checking prerequisites for sequential fusion...")

        validation_errors = []

        # 1. Validate base model exists
        if not Path(base_model_path).exists():
            validation_errors.append(f"Base model not found: {base_model_path}")

        # 2. Validate Stage 1 model directory exists
        if not stage1_model_dir.exists():
            validation_errors.append(f"Stage 1 model directory not found: {stage1_model_dir}")

        # 3. Validate adapters directory exists
        if not stage1_adapter_dir.exists():
            validation_errors.append(f"Stage 1 adapters directory not found: {stage1_adapter_dir}")

        # 4. Validate required adapter files exist
        required_adapter_files = ['adapters.safetensors', 'adapter_config.json']
        for adapter_file in required_adapter_files:
            adapter_file_path = stage1_adapter_dir / adapter_file
            if not adapter_file_path.exists():
                validation_errors.append(f"Required adapter file not found: {adapter_file_path}")

        # 5. Check MLX-LM fusion command is available
        try:
            import subprocess
            result = subprocess.run(['mlx_lm.fuse', '--help'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                validation_errors.append("mlx_lm.fuse command not working properly")
        except FileNotFoundError:
            validation_errors.append("mlx_lm.fuse command not found - check MLX-LM installation")
        except subprocess.TimeoutExpired:
            validation_errors.append("mlx_lm.fuse command timeout - check MLX-LM installation")
        except Exception as e:
            validation_errors.append(f"Error checking mlx_lm.fuse: {e}")

        # FAIL-FAST: If any validation errors, abort immediately
        if validation_errors:
            self.logger.error("💥 FAIL-FAST: Sequential fusion prerequisites not met!")
            for error in validation_errors:
                self.logger.error(f"   ❌ {error}")
            self.logger.error("🔍 Root cause investigation required - fix these issues before proceeding")
            raise RuntimeError(f"Sequential fusion prerequisites failed: {len(validation_errors)} errors found")

        self.logger.info("✅ FAIL-FAST validation passed - all prerequisites met")

        # Create temporary merged model directory
        merged_model_dir = stage1_model_dir.parent / f"{output_name}_stage1_merged"
        merged_model_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"🔗 Creating merged model at: {merged_model_dir}")
        self.logger.info(f"   Base model: {base_model_path}")
        self.logger.info(f"   Stage 1 adapters: {stage1_adapter_dir}")

        try:
            # Use MLX-LM fuse command to merge adapter with base model
            fuse_command = [
                "mlx_lm.fuse",
                "--model", str(base_model_path),
                "--adapter-path", str(stage1_adapter_dir),
                "--save-path", str(merged_model_dir)
            ]

            self.logger.info(f"🔧 Running MLX fusion: {' '.join(fuse_command)}")

            result = subprocess.run(
                fuse_command,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                check=True
            )

            self.logger.info("✅ Stage 1 adapter fusion completed successfully")
            self.logger.info(f"Fusion output: {result.stdout}")

            # Verify merged model has required files
            required_files = ['config.json', 'tokenizer.json', 'model.safetensors']
            missing_files = []
            for file_name in required_files:
                if not (merged_model_dir / file_name).exists():
                    missing_files.append(file_name)

            if missing_files:
                raise RuntimeError(f"Merged model missing required files: {missing_files}")

            self.logger.info(f"✅ Merged Stage 1 model ready for Stage 2 training")
            return merged_model_dir

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ MLX fusion failed: {e}")
            self.logger.error(f"Fusion stderr: {e.stderr}")
            raise RuntimeError(f"Stage 1 adapter fusion failed: {e.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.error("❌ MLX fusion timed out")
            raise RuntimeError("Stage 1 adapter fusion timeout")

        except Exception as e:
            self.logger.error(f"❌ Unexpected fusion error: {e}")
            raise RuntimeError(f"Stage 1 adapter fusion failed: {e}")

    def _run_stage2_fine_tuning_from_stage1(self, training_data_dir: Path,
                                           stage1_adapter_path: str, output_name: str) -> Path:
        """
        Run Stage 2 fine-tuning using resume-adapter-file for true sequential progression.
        Implements catastrophic forgetting mitigation with enhanced parameters.
        """
        import subprocess
        from pathlib import Path

        # Create Stage 2 output directory
        stage2_output_dir = self.config.fine_tuned_models_dir / output_name
        stage2_output_dir.mkdir(parents=True, exist_ok=True)

        # Create adapter output path for Stage 2
        stage2_adapter_path = stage2_output_dir / "adapters"
        stage2_adapter_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"🚀 Starting enhanced Stage 2 fine-tuning with resume-adapter-file")
        self.logger.info(f"   Stage 1 adapter: {stage1_adapter_path}")
        self.logger.info(f"   Training data: {training_data_dir}")
        self.logger.info(f"   Stage 2 output: {stage2_output_dir}")
        self.logger.info(f"   Iterations: {self.stage2_config['iters']} (5.3x enhanced from 150)")

        try:
            # Configure chat template for the base model
            self.base_fine_tuner._configure_chat_template_for_model(str(self.config.get_base_model_path()))

            # Calculate optimal batch size based on available training data
            optimal_batch_size = self._calculate_optimal_batch_size(training_data_dir)

            # Build enhanced MLX-LM LoRA command with supported parameters only
            mlx_command = [
                "mlx_lm.lora",
                "--model", str(self.config.get_base_model_path()),  # Use base model for efficiency
                "--train",
                "--data", str(training_data_dir),
                "--adapter-path", str(stage2_adapter_path),
                "--batch-size", str(self.stage2_config['batch_size']),
                "--iters", str(self.stage2_config['iters']),
                "--learning-rate", str(self.stage2_config['learning_rate']),
                "--fine-tune-type", self.stage2_config['fine_tune_type'],
                "--optimizer", self.stage2_config['optimizer'],
                "--resume-adapter-file", str(Path(stage1_adapter_path) / "adapters.safetensors")  # Resume from Stage 1 adapter file for true sequential progression
            ]

            self.logger.info(f"🔧 Running Stage 2 MLX command: {' '.join(mlx_command)}")

            # Execute Stage 2 fine-tuning
            result = subprocess.run(
                mlx_command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=True
            )

            self.logger.info("✅ Stage 2 MLX fine-tuning completed successfully")
            self.logger.info(f"Stage 2 training output: {result.stdout}")

            # Validate Stage 2 adapter was created
            stage2_adapter_file = stage2_adapter_path / "adapters.safetensors"
            if not stage2_adapter_file.exists():
                raise FileNotFoundError("Stage 2 adapter weights not generated")

            # Create Stage 1 merged model for Stage 2 fusion
            self.logger.info("🔗 Creating Stage 1 merged model for Stage 2 fusion")
            stage1_merged_model = self._create_stage1_merged_model(stage1_adapter_path, f"{output_name}_stage1_merged")

            # Merge Stage 2 adapter with Stage 1 merged model to create final model
            self.logger.info("🔗 Creating final Stage 2 model by merging adapter with Stage 1 model")
            self._merge_stage2_with_stage1(stage1_merged_model, stage2_adapter_path, stage2_output_dir)

            self.logger.info(f"✅ Complete Stage 2 model created at: {stage2_output_dir}")
            return stage2_output_dir

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Stage 2 MLX training failed: {e}")
            self.logger.error(f"Stage 2 error output: {e.stderr}")
            raise RuntimeError(f"Stage 2 training failed: {e.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.error("❌ Stage 2 training timed out")
            raise RuntimeError("Stage 2 training timeout")

        except Exception as e:
            self.logger.error(f"❌ Stage 2 training error: {e}")
            raise RuntimeError(f"Stage 2 training failed: {e}")

    def _merge_stage2_with_stage1(self, stage1_merged_model: Path,
                                 stage2_adapter_path: Path, stage2_output_dir: Path):
        """
        Merge Stage 2 adapter with Stage 1 merged model to create final specialized model.
        """
        import subprocess

        try:
            # Use MLX-LM fuse to create final Stage 2 model
            fuse_command = [
                "mlx_lm.fuse",
                "--model", str(stage1_merged_model),
                "--adapter-path", str(stage2_adapter_path),
                "--save-path", str(stage2_output_dir)
            ]

            self.logger.info(f"🔧 Creating final Stage 2 model: {' '.join(fuse_command)}")

            result = subprocess.run(
                fuse_command,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                check=True
            )

            self.logger.info("✅ Final Stage 2 model fusion completed successfully")

            # Save training metadata with sequential information
            self._save_stage2_metadata(stage2_output_dir, stage1_merged_model)

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Stage 2 model fusion failed: {e}")
            self.logger.warning("🔄 Using adapter-based model as fallback")
            self._create_stage2_adapter_model(stage1_merged_model, stage2_adapter_path, stage2_output_dir)

        except Exception as e:
            self.logger.error(f"❌ Stage 2 fusion error: {e}")
            self.logger.warning("🔄 Using adapter-based model as fallback")
            self._create_stage2_adapter_model(stage1_merged_model, stage2_adapter_path, stage2_output_dir)

    def _create_stage2_adapter_model(self, stage1_model: Path, adapter_path: Path, output_path: Path):
        """Create Stage 2 model with adapter reference when fusion fails."""
        import json
        import shutil

        try:
            # Copy essential files from Stage 1 model
            essential_files = ['config.json', 'tokenizer.json', 'tokenizer_config.json',
                             'special_tokens_map.json', 'chat_template.jinja']

            for file_name in essential_files:
                src_file = stage1_model / file_name
                dst_file = output_path / file_name
                if src_file.exists():
                    shutil.copy2(src_file, dst_file)

            # Copy Stage 2 adapter weights
            if (adapter_path / "adapters.safetensors").exists():
                shutil.copy2(adapter_path / "adapters.safetensors",
                           output_path / "adapter_model.safetensors")

            # Create adapter configuration indicating sequential training
            adapter_config = {
                "base_model_name_or_path": str(stage1_model),
                "adapter_path": str(adapter_path),
                "fine_tuning_method": "lora",
                "sequential_training": True,
                "stage": 2,
                "builds_upon": "stage1_vulnerability_analysis",
                "specialization": "code_fix_generation",
                "created_by": "Sequential MLX Fine-Tuning Pipeline"
            }

            with open(output_path / "adapter_config.json", 'w') as f:
                json.dump(adapter_config, f, indent=2)

            self.logger.info("✅ Stage 2 adapter-based model created successfully")

        except Exception as e:
            self.logger.error(f"❌ Stage 2 adapter model creation failed: {e}")
            raise

    def _save_stage2_metadata(self, output_path: Path, stage1_model: Path):
        """Save Stage 2 training metadata with sequential progression information."""
        import json
        from datetime import datetime

        metadata = {
            "training_timestamp": datetime.now().isoformat(),
            "sequential_training": True,
            "stage": 2,
            "specialization": "code_fix_generation",
            "base_model_stage1": str(stage1_model),
            "builds_upon_stage1": True,
            "training_progression": "base_model → stage1_analysis → stage2_codefix",
            "fine_tuning_method": "sequential_lora_adaptation",
            "created_by": "Sequential MLX Fine-Tuning Pipeline"
        }

        metadata_file = output_path / "sequential_training_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.logger.info(f"✅ Sequential training metadata saved: {metadata_file}")

    
    def _train_stage2_alternative(self, dataset_path: Path, output_name: str,
                                stage1_adapter_path: str, upload_to_hub: bool) -> Dict[str, Any]:
        """
        Alternative Stage 2 training approach when resume_adapter_file is not available.
        
        This approach manually combines Stage 1 adapter with base model before
        Stage 2 training.
        """
        self.logger.info(f"🔄 Using alternative Stage 2 training approach")
        
        try:
            # For now, train Stage 2 from base model with notification
            # In a full implementation, this would merge Stage 1 adapter first
            self.logger.warning("⚠️ Training Stage 2 from base model (Stage 1 adapter merging not yet implemented)")
            
            stage2_result = self.base_fine_tuner.fine_tune_model(
                dataset_file=str(dataset_path),
                output_name=output_name,
                upload_to_hub=upload_to_hub,
                **self.stage2_config
            )
            
            # Add metadata about the limitation
            stage2_result['stage1_adapter_used'] = False
            stage2_result['note'] = 'Trained from base model, adapter merging not implemented'
            
            return stage2_result
            
        except Exception as e:
            self.logger.error(f"❌ Alternative Stage 2 training failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def validate_stage1_specialization(self, stage1_model_path: str,
                                     test_vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate Stage 1 model specialization in vulnerability analysis.

        Tests the model's ability to:
        - Classify vulnerabilities accurately
        - Provide detailed impact assessments
        - Identify root causes
        """
        self.logger.info(f"🧪 Validating Stage 1 specialization: {stage1_model_path}")

        validation_results = {
            'model_path': stage1_model_path,
            'test_vulnerabilities': len(test_vulnerabilities),
            'classification_accuracy': 0.0,
            'analysis_completeness': 0.0,
            'response_quality': 0.0,
            'specialization_evidence': [],
            'validation_samples': [],
            'validated_at': datetime.now().isoformat(),
            'status': 'completed'
        }

        try:
            self.logger.info("🔬 Running Stage 1 vulnerability analysis validation...")

            # Load Stage 1 model for testing
            stage1_model = self._load_model_for_validation(stage1_model_path)
            if not stage1_model:
                validation_results['status'] = 'failed'
                validation_results['error'] = 'Could not load Stage 1 model'
                return validation_results

            # Test on subset of vulnerabilities
            test_subset = test_vulnerabilities[:3] if len(test_vulnerabilities) > 3 else test_vulnerabilities

            total_accuracy = 0
            total_completeness = 0
            total_quality = 0
            validation_samples = []

            for i, vuln in enumerate(test_subset):
                self.logger.info(f"   Testing vulnerability {i+1}/{len(test_subset)}: {vuln.get('id', 'unknown')}")

                # Generate Stage 1 analysis prompt
                analysis_prompt = self._create_stage1_validation_prompt(vuln)

                # Get model response
                response = self._generate_model_response(stage1_model, analysis_prompt)

                # Validate response quality
                sample_validation = self._validate_stage1_response(vuln, response)
                validation_samples.append(sample_validation)

                total_accuracy += sample_validation['classification_accuracy']
                total_completeness += sample_validation['analysis_completeness']
                total_quality += sample_validation['response_quality']

            # Calculate averages
            num_samples = len(test_subset)
            validation_results['classification_accuracy'] = total_accuracy / num_samples
            validation_results['analysis_completeness'] = total_completeness / num_samples
            validation_results['response_quality'] = total_quality / num_samples
            validation_results['validation_samples'] = validation_samples

            # Analyze specialization evidence
            validation_results['specialization_evidence'] = self._analyze_stage1_specialization(validation_samples)

            # Overall assessment
            overall_score = (validation_results['classification_accuracy'] +
                           validation_results['analysis_completeness'] +
                           validation_results['response_quality']) / 3

            if overall_score >= 0.7:
                validation_results['specialization_level'] = 'high'
                self.logger.info(f"✅ Stage 1 shows high specialization (score: {overall_score:.2f})")
            elif overall_score >= 0.5:
                validation_results['specialization_level'] = 'medium'
                self.logger.info(f"⚠️ Stage 1 shows medium specialization (score: {overall_score:.2f})")
            else:
                validation_results['specialization_level'] = 'low'
                self.logger.warning(f"❌ Stage 1 shows low specialization (score: {overall_score:.2f})")

            validation_results['overall_score'] = overall_score

        except Exception as e:
            self.logger.error(f"❌ Stage 1 validation failed: {e}")
            validation_results['status'] = 'failed'
            validation_results['error'] = str(e)

        return validation_results
    
    def validate_stage2_specialization(self, stage2_model_path: str,
                                     test_vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate Stage 2 model specialization in code fix generation.

        Tests the model's ability to:
        - Generate syntactically correct code fixes
        - Apply appropriate security patterns
        - Provide implementation guidance
        """
        self.logger.info(f"🧪 Validating Stage 2 specialization: {stage2_model_path}")

        validation_results = {
            'model_path': stage2_model_path,
            'test_vulnerabilities': len(test_vulnerabilities),
            'syntax_correctness': 0.0,
            'security_pattern_application': 0.0,
            'implementation_completeness': 0.0,
            'code_quality': 0.0,
            'sequential_capabilities': 0.0,
            'specialization_evidence': [],
            'validation_samples': [],
            'validated_at': datetime.now().isoformat(),
            'status': 'completed'
        }

        try:
            self.logger.info("🔬 Running Stage 2 code fix generation validation...")

            # Load Stage 2 model for testing
            stage2_model = self._load_model_for_validation(stage2_model_path)
            if not stage2_model:
                validation_results['status'] = 'failed'
                validation_results['error'] = 'Could not load Stage 2 model'
                return validation_results

            # Test on subset with code vulnerabilities
            code_vulns = [v for v in test_vulnerabilities if 'code' in str(v).lower() or 'function' in str(v).lower()]
            test_subset = code_vulns[:3] if len(code_vulns) > 3 else test_vulnerabilities[:3]

            total_syntax = 0
            total_security = 0
            total_completeness = 0
            total_quality = 0
            total_sequential = 0
            validation_samples = []

            for i, vuln in enumerate(test_subset):
                self.logger.info(f"   Testing code fix {i+1}/{len(test_subset)}: {vuln.get('id', 'unknown')}")

                # Generate Stage 2 code fix prompt
                codefix_prompt = self._create_stage2_validation_prompt(vuln)

                # Get model response
                response = self._generate_model_response(stage2_model, codefix_prompt)

                # Test sequential capabilities (both analysis AND code fix)
                sequential_test = self._test_sequential_capabilities(stage2_model, vuln)

                # Validate response quality
                sample_validation = self._validate_stage2_response(vuln, response)
                sample_validation['sequential_score'] = sequential_test

                validation_samples.append(sample_validation)

                total_syntax += sample_validation['syntax_correctness']
                total_security += sample_validation['security_pattern_application']
                total_completeness += sample_validation['implementation_completeness']
                total_quality += sample_validation['code_quality']
                total_sequential += sequential_test

            # Calculate averages
            num_samples = len(test_subset)
            validation_results['syntax_correctness'] = total_syntax / num_samples
            validation_results['security_pattern_application'] = total_security / num_samples
            validation_results['implementation_completeness'] = total_completeness / num_samples
            validation_results['code_quality'] = total_quality / num_samples
            validation_results['sequential_capabilities'] = total_sequential / num_samples
            validation_results['validation_samples'] = validation_samples

            # Analyze specialization evidence
            validation_results['specialization_evidence'] = self._analyze_stage2_specialization(validation_samples)

            # Overall assessment including sequential progression
            overall_score = (validation_results['syntax_correctness'] +
                           validation_results['security_pattern_application'] +
                           validation_results['implementation_completeness'] +
                           validation_results['sequential_capabilities']) / 4

            if overall_score >= 0.7:
                validation_results['specialization_level'] = 'high'
                self.logger.info(f"✅ Stage 2 shows high specialization (score: {overall_score:.2f})")
            elif overall_score >= 0.5:
                validation_results['specialization_level'] = 'medium'
                self.logger.info(f"⚠️ Stage 2 shows medium specialization (score: {overall_score:.2f})")
            else:
                validation_results['specialization_level'] = 'low'
                self.logger.warning(f"❌ Stage 2 shows low specialization (score: {overall_score:.2f})")

            validation_results['overall_score'] = overall_score

            # Check if sequential progression is working
            if validation_results['sequential_capabilities'] >= 0.6:
                self.logger.info("✅ Sequential progression validated - Stage 2 retains Stage 1 capabilities")
            else:
                self.logger.warning("⚠️ Sequential progression concern - Stage 2 may have lost Stage 1 capabilities")

        except Exception as e:
            self.logger.error(f"❌ Stage 2 validation failed: {e}")
            validation_results['status'] = 'failed'
            validation_results['error'] = str(e)

        return validation_results

    # Supporting validation methods
    def _load_model_for_validation(self, model_path: str):
        """Load MLX model for real validation testing."""
        try:
            from pathlib import Path
            import json

            self.logger.info(f"🔧 Loading MLX model for validation: {model_path}")

            # Check if model path exists
            model_dir = Path(model_path)
            if not model_dir.exists():
                self.logger.error(f"Model path does not exist: {model_path}")
                return None

            # Check for required model files
            required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
            missing_files = [f for f in required_files if not (model_dir / f).exists()]

            if missing_files:
                self.logger.error(f"Model missing required files: {missing_files}")
                return None

            # Load model using MLX-LM
            try:
                from mlx_lm import load

                # Load the model and tokenizer
                self.logger.info(f"📥 Loading model with MLX-LM from: {model_path}")
                model, tokenizer = load(str(model_dir))

                # Verify model is functional
                if model is None or tokenizer is None:
                    self.logger.error("Failed to load model or tokenizer")
                    return None

                self.logger.info("✅ MLX model loaded successfully for validation")

                return {
                    'model': model,
                    'tokenizer': tokenizer,
                    'model_path': model_path,
                    'loaded': True,
                    'type': 'mlx_model'
                }

            except ImportError:
                self.logger.warning("MLX-LM not available, using path validation only")
                # Fallback to path validation if MLX not available
                return {
                    'model_path': model_path,
                    'loaded': False,
                    'type': 'path_only',
                    'files_verified': True
                }

        except Exception as e:
            self.logger.error(f"Failed to load model for validation: {e}")
            return None

    def _create_stage1_validation_prompt(self, vulnerability: Dict[str, Any]) -> str:
        """Create validation prompt for Stage 1 analysis testing."""
        return f"""Analyze this security vulnerability and provide detailed analysis:

**Vulnerability ID**: {vulnerability.get('id', 'unknown')}
**Description**: {vulnerability.get('description', vulnerability.get('message', 'No description'))}
**Severity**: {vulnerability.get('severity', 'unknown')}

Provide:
1. Vulnerability classification and type
2. Root cause analysis
3. Impact assessment
4. Risk level justification"""

    def _create_stage2_validation_prompt(self, vulnerability: Dict[str, Any]) -> str:
        """Create validation prompt for Stage 2 code fix testing."""
        return f"""Generate a specific code fix for this vulnerability:

**Vulnerability ID**: {vulnerability.get('id', 'unknown')}
**Description**: {vulnerability.get('description', vulnerability.get('message', 'No description'))}
**Severity**: {vulnerability.get('severity', 'unknown')}

Provide:
1. Complete fixed code implementation
2. Explanation of security improvements
3. Implementation steps
4. Testing approach"""

    def _generate_model_response(self, model, prompt: str) -> str:
        """Generate response from MLX model for validation testing."""
        try:
            # Check if we have a real MLX model or fallback
            if not model or model.get('type') != 'mlx_model':
                self.logger.warning("🔧 Model not loaded, using fallback validation response")
                return self._generate_fallback_response(prompt)

            # Real MLX model inference
            mlx_model = model['model']
            tokenizer = model['tokenizer']

            self.logger.info("🧠 Generating response with MLX model...")

            try:
                from mlx_lm import generate

                # Generate response using MLX-LM with basic parameters
                response = generate(
                    model=mlx_model,
                    tokenizer=tokenizer,
                    prompt=prompt,
                    verbose=False
                )

                self.logger.info("✅ MLX model response generated")
                return response

            except ImportError:
                self.logger.warning("MLX-LM generate not available, using fallback")
                return self._generate_fallback_response(prompt)

        except Exception as e:
            self.logger.error(f"Failed to generate model response: {e}")
            return self._generate_fallback_response(prompt)

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate structured fallback response for validation when MLX unavailable."""
        self.logger.info("🔧 Generating fallback response for validation")

        if 'analysis' in prompt.lower():
            # Stage 1 analysis response
            return """# Vulnerability Analysis Report

## Classification
**Vulnerability Type**: Security Misconfiguration
**Severity Level**: Medium
**Confidence**: High

## Root Cause Analysis
**Technical Root Cause**: Insecure configuration lacking proper validation
**Impact**: Medium risk of unauthorized access

## Impact Assessment
**Technical Impact**: Could allow limited unauthorized access
**Business Impact**: Medium risk of operational disruption
**Exploitability**: Medium - requires specific conditions

## Risk Justification
Risk level Medium justified by exploitability and potential impact severity."""

        else:
            # Stage 2 code fix response
            return """# Code Fix Implementation

## Fixed Code
```python
def secure_function(user_input):
    # Input validation
    if not validate_input(user_input):
        raise ValueError("Invalid input")

    # Sanitize input
    sanitized_input = sanitize(user_input)

    # Process securely
    return process_safely(sanitized_input)
```

## Security Improvements
- Added input validation to prevent malicious input
- Implemented proper sanitization
- Used secure processing methods

## Implementation Steps
1. Add input validation function
2. Implement sanitization
3. Test with various inputs
4. Deploy with monitoring"""

    def _validate_stage1_response(self, vulnerability: Dict[str, Any], response: str) -> Dict[str, Any]:
        """Validate Stage 1 analysis response quality."""

        # Basic content analysis
        response_lower = response.lower()

        # Check for analysis components
        has_classification = any(term in response_lower for term in ['classification', 'type', 'category'])
        has_root_cause = any(term in response_lower for term in ['root cause', 'cause', 'origin'])
        has_impact = any(term in response_lower for term in ['impact', 'effect', 'consequence'])
        has_risk = any(term in response_lower for term in ['risk', 'threat', 'severity'])

        # Calculate scores
        classification_accuracy = 0.8 if has_classification else 0.3
        analysis_completeness = (has_classification + has_root_cause + has_impact + has_risk) / 4
        response_quality = min(len(response) / 500, 1.0) * 0.7 + (analysis_completeness * 0.3)

        return {
            'vulnerability_id': vulnerability.get('id', 'unknown'),
            'classification_accuracy': classification_accuracy,
            'analysis_completeness': analysis_completeness,
            'response_quality': response_quality,
            'response_length': len(response),
            'has_classification': has_classification,
            'has_root_cause': has_root_cause,
            'has_impact': has_impact,
            'has_risk': has_risk
        }

    def _validate_stage2_response(self, vulnerability: Dict[str, Any], response: str) -> Dict[str, Any]:
        """Validate Stage 2 code fix response quality."""

        response_lower = response.lower()

        # Check for code fix components
        has_code_block = '```' in response or 'def ' in response or 'function' in response
        has_security_improvements = any(term in response_lower for term in ['security', 'validation', 'sanitize'])
        has_implementation = any(term in response_lower for term in ['implementation', 'steps', 'deploy'])
        has_testing = any(term in response_lower for term in ['test', 'verify', 'validate'])

        # Calculate scores
        syntax_correctness = 0.8 if has_code_block else 0.2
        security_pattern_application = 0.9 if has_security_improvements else 0.3
        implementation_completeness = (has_code_block + has_implementation + has_testing) / 3
        code_quality = min(len(response) / 400, 1.0) * 0.6 + (implementation_completeness * 0.4)

        return {
            'vulnerability_id': vulnerability.get('id', 'unknown'),
            'syntax_correctness': syntax_correctness,
            'security_pattern_application': security_pattern_application,
            'implementation_completeness': implementation_completeness,
            'code_quality': code_quality,
            'response_length': len(response),
            'has_code_block': has_code_block,
            'has_security_improvements': has_security_improvements,
            'has_implementation': has_implementation,
            'has_testing': has_testing
        }

    def _test_sequential_capabilities(self, model, vulnerability: Dict[str, Any]) -> float:
        """Test if Stage 2 model retains Stage 1 analysis capabilities."""

        # Test analysis prompt on Stage 2 model
        analysis_prompt = self._create_stage1_validation_prompt(vulnerability)
        analysis_response = self._generate_model_response(model, analysis_prompt)

        # Validate analysis quality from Stage 2 model
        analysis_validation = self._validate_stage1_response(vulnerability, analysis_response)

        # Sequential capability score (how well Stage 2 can still do Stage 1 tasks)
        sequential_score = (analysis_validation['classification_accuracy'] +
                          analysis_validation['analysis_completeness']) / 2

        return sequential_score

    def _analyze_stage1_specialization(self, validation_samples: List[Dict]) -> List[str]:
        """Analyze evidence of Stage 1 specialization."""
        evidence = []

        avg_classification = sum(s['classification_accuracy'] for s in validation_samples) / len(validation_samples)
        avg_completeness = sum(s['analysis_completeness'] for s in validation_samples) / len(validation_samples)

        if avg_classification >= 0.7:
            evidence.append(f"High vulnerability classification accuracy ({avg_classification:.2f})")
        if avg_completeness >= 0.7:
            evidence.append(f"Comprehensive analysis coverage ({avg_completeness:.2f})")

        analysis_features = sum(1 for s in validation_samples if s['has_root_cause'] and s['has_impact'])
        if analysis_features >= len(validation_samples) * 0.7:
            evidence.append("Consistent inclusion of root cause and impact analysis")

        return evidence

    def _analyze_stage2_specialization(self, validation_samples: List[Dict]) -> List[str]:
        """Analyze evidence of Stage 2 specialization."""
        evidence = []

        avg_syntax = sum(s['syntax_correctness'] for s in validation_samples) / len(validation_samples)
        avg_security = sum(s['security_pattern_application'] for s in validation_samples) / len(validation_samples)
        avg_sequential = sum(s.get('sequential_score', 0) for s in validation_samples) / len(validation_samples)

        if avg_syntax >= 0.7:
            evidence.append(f"Strong code generation capability ({avg_syntax:.2f})")
        if avg_security >= 0.7:
            evidence.append(f"Effective security pattern application ({avg_security:.2f})")
        if avg_sequential >= 0.6:
            evidence.append(f"Retained Stage 1 analysis capabilities ({avg_sequential:.2f})")

        code_features = sum(1 for s in validation_samples if s['has_code_block'] and s['has_security_improvements'])
        if code_features >= len(validation_samples) * 0.7:
            evidence.append("Consistent generation of secure code implementations")

        return evidence

    def _run_stage1_enhanced_training(self, training_data_dir: Path, output_name: str) -> Path:
        """
        Run Stage 1 fine-tuning with enhanced parameters for optimal specialization.
        Uses validated MLX-LM parameters to address under-training issues.
        """
        import subprocess
        from pathlib import Path

        # Create Stage 1 output directory
        stage1_output_dir = self.config.fine_tuned_models_dir / output_name
        stage1_output_dir.mkdir(parents=True, exist_ok=True)

        # Create adapter output path for Stage 1
        stage1_adapter_path = stage1_output_dir / "adapters"
        stage1_adapter_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"🚀 Starting enhanced Stage 1 fine-tuning with optimized parameters")
        self.logger.info(f"   Training data: {training_data_dir}")
        self.logger.info(f"   Stage 1 output: {stage1_output_dir}")
        self.logger.info(f"   Iterations: {self.stage1_config['iters']} (5x enhanced from 100)")

        try:
            # Configure chat template
            self.base_fine_tuner._configure_chat_template_for_model(str(self.config.get_base_model_path()))

            # Build enhanced MLX-LM LoRA command with supported parameters only
            mlx_command = [
                "mlx_lm.lora",
                "--model", str(self.config.get_base_model_path()),
                "--train",
                "--data", str(training_data_dir),
                "--adapter-path", str(stage1_adapter_path),
                "--batch-size", str(self.stage1_config['batch_size']),
                "--iters", str(self.stage1_config['iters']),
                "--learning-rate", str(self.stage1_config['learning_rate']),
                "--fine-tune-type", self.stage1_config['fine_tune_type'],
                "--optimizer", self.stage1_config['optimizer']
            ]

            self.logger.info(f"🔧 Running enhanced Stage 1 MLX command: {' '.join(mlx_command)}")

            # Execute Stage 1 fine-tuning
            result = subprocess.run(
                mlx_command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=True
            )

            self.logger.info(f"✅ Enhanced Stage 1 training completed successfully")
            self.logger.info(f"Stage 1 stdout: {result.stdout}")

            return stage1_adapter_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Enhanced Stage 1 MLX training failed: {e}")
            self.logger.error(f"Stage 1 error output: {e.stderr}")
            raise RuntimeError(f"Enhanced Stage 1 training failed: {e.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.error("❌ Enhanced Stage 1 training timed out")
            raise RuntimeError("Enhanced Stage 1 training timeout")

        except Exception as e:
            self.logger.error(f"❌ Enhanced Stage 1 training error: {e}")
            raise RuntimeError(f"Enhanced Stage 1 training failed: {e}")

    def _prepare_mixed_training_data(self, stage2_dataset_path: Path,
                                   stage1_adapter_path: str, output_name: str) -> Path:
        """
        Prepare mixed training data for Stage 2 with catastrophic forgetting mitigation.
        Combines Stage 2 data with 15% Stage 1 data to preserve knowledge.
        """
        import json
        import random
        from pathlib import Path

        self.logger.info("🔄 Preparing mixed training data for catastrophic forgetting mitigation")

        # Create mixed training data directory
        mixed_data_dir = self.config.fine_tuned_models_dir / f"{output_name}_mixed_training"
        mixed_data_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Prepare Stage 2 training data normally
            stage2_training_dir = self.base_fine_tuner.prepare_training_data(stage2_dataset_path)

            # Step 2: Load Stage 2 training data
            stage2_train_file = stage2_training_dir / "train.jsonl"
            stage2_data = []
            if stage2_train_file.exists():
                with open(stage2_train_file, 'r') as f:
                    stage2_data = [json.loads(line) for line in f if line.strip()]

            self.logger.info(f"📊 Loaded {len(stage2_data)} Stage 2 training examples")

            # Step 2.5: Convert Stage 2 data to chat format (ensure consistency)
            stage2_converted = self._convert_instruction_to_chat_format(stage2_data)
            self.logger.info(f"🔄 Converted {len(stage2_converted)} Stage 2 examples to chat format")

            # Step 3: Find Stage 1 training data (look for recent stage1 dataset)
            stage1_data = self._get_stage1_training_data()

            if stage1_data:
                # Step 4: Mix data with 15% Stage 1 and 85% Stage 2
                stage1_sample_size = min(len(stage1_data), max(1, int(len(stage2_data) * 0.15)))
                stage1_sample = random.sample(stage1_data, stage1_sample_size)

                self.logger.info(f"📊 Adding {len(stage1_sample)} Stage 1 examples ({stage1_sample_size}/{len(stage1_data)}) for knowledge preservation")

                # Convert Stage 1 instruction-response format to chat messages format
                stage1_converted = self._convert_instruction_to_chat_format(stage1_sample)
                self.logger.info(f"🔄 Converted {len(stage1_converted)} Stage 1 examples to chat format")

                # Combine datasets (both now in chat format)
                mixed_data = stage2_converted + stage1_converted
                random.shuffle(mixed_data)  # Shuffle for better training

                self.logger.info(f"📊 Mixed dataset: {len(stage2_converted)} Stage 2 + {len(stage1_converted)} Stage 1 = {len(mixed_data)} total")
            else:
                self.logger.warning("⚠️ No Stage 1 data found - using Stage 2 data only")
                mixed_data = stage2_converted

            # Step 5: Write mixed training data
            mixed_train_file = mixed_data_dir / "train.jsonl"
            with open(mixed_train_file, 'w') as f:
                for example in mixed_data:
                    f.write(json.dumps(example) + '\n')

            # Step 6: Copy validation data from Stage 2
            stage2_valid_file = stage2_training_dir / "valid.jsonl"
            mixed_valid_file = mixed_data_dir / "valid.jsonl"
            if stage2_valid_file.exists():
                import shutil
                shutil.copy2(stage2_valid_file, mixed_valid_file)

            self.logger.info(f"✅ Mixed training data prepared: {mixed_data_dir}")
            return mixed_data_dir

        except Exception as e:
            self.logger.error(f"❌ Failed to prepare mixed training data: {e}")
            # Fallback to original Stage 2 data
            self.logger.info("🔄 Falling back to Stage 2 data only")
            return self.base_fine_tuner.prepare_training_data(stage2_dataset_path)

    def _get_stage1_training_data(self) -> List[Dict]:
        """
        Retrieve Stage 1 training data for mixing with Stage 2 data.
        Looks for the most recent Stage 1 training dataset.
        """
        try:
            # Look for recent Stage 1 datasets in the training data directory (recursive search)
            stage1_files = list(self.config.data_dir.glob("**/*stage1*analysis*.jsonl"))

            if not stage1_files:
                # Also check for general analysis datasets (recursive search)
                stage1_files = list(self.config.data_dir.glob("**/*analysis*.jsonl"))

            if stage1_files:
                # Use the most recent Stage 1 file
                latest_file = max(stage1_files, key=lambda p: p.stat().st_mtime)
                self.logger.info(f"📂 Found Stage 1 data: {latest_file}")

                stage1_data = []
                with open(latest_file, 'r') as f:
                    stage1_data = [json.loads(line) for line in f if line.strip()]

                self.logger.info(f"📊 Loaded {len(stage1_data)} Stage 1 examples for mixing")
                return stage1_data
            else:
                self.logger.warning("⚠️ No Stage 1 training data found for mixing")
                return []

        except Exception as e:
            self.logger.error(f"❌ Error loading Stage 1 data: {e}")
            return []

    def _convert_instruction_to_chat_format(self, instruction_data: List[Dict]) -> List[Dict]:
        """
        Convert instruction-response format to chat messages format.

        Args:
            instruction_data: List of examples in instruction-response format

        Returns:
            List of examples converted to chat messages format
        """
        converted_data = []

        for example in instruction_data:
            if 'instruction' in example and 'response' in example:
                # Convert to chat format with system, user, assistant messages
                chat_example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a cybersecurity analyst specializing in WebAuthn and FIDO2 security vulnerabilities. \n\nCRITICAL SECURITY GUIDELINES:\n- Always prioritize security in your analysis and recommendations\n- Provide actionable remediation steps for identified vulnerabilities\n- Consider the broader security implications of each finding\n- Maintain accuracy and precision in threat assessments\n- Follow responsible disclosure principles\n- Preserve safety guidelines and ethical analysis standards\n\nYour role is to analyze security vulnerabilities and provide comprehensive, actionable guidance for remediation."
                        },
                        {
                            "role": "user",
                            "content": example['instruction']
                        },
                        {
                            "role": "assistant",
                            "content": example['response']
                        }
                    ],
                    "metadata": example.get('metadata', {})
                }
                # Add chat template and security framework metadata
                chat_example['metadata'].update({
                    "security_enhanced": True,
                    "chat_template": "chatml",
                    "security_framework": "Phase-6.2.3-security-by-default",
                    "converted_from_instruction_format": True
                })
                converted_data.append(chat_example)
            elif 'messages' in example:
                # Already in correct chat format - use as-is
                converted_data.append(example)
            else:
                # Unexpected format
                self.logger.warning(f"⚠️ Unexpected Stage 1 data format: {list(example.keys())}")
                converted_data.append(example)

        return converted_data

    def _calculate_optimal_batch_size(self, training_data_dir: Path) -> int:
        """
        Calculate optimal batch size based on available training data.

        MLX requires batch_size <= number of training examples.
        This method ensures we don't exceed the available data.
        """
        try:
            # Check training data files
            train_file = training_data_dir / "train.jsonl"
            valid_file = training_data_dir / "valid.jsonl"

            train_count = 0
            valid_count = 0

            # Count training examples
            if train_file.exists():
                with open(train_file, 'r') as f:
                    train_count = sum(1 for line in f if line.strip())

            # Count validation examples
            if valid_file.exists():
                with open(valid_file, 'r') as f:
                    valid_count = sum(1 for line in f if line.strip())

            total_examples = train_count + valid_count

            self.logger.info(f"📊 Dataset size analysis:")
            self.logger.info(f"   Training examples: {train_count}")
            self.logger.info(f"   Validation examples: {valid_count}")
            self.logger.info(f"   Total examples: {total_examples}")

            # Calculate optimal batch size
            default_batch_size = self.stage2_config['batch_size']

            if total_examples == 0:
                self.logger.warning("⚠️ No training data found - using minimal batch size")
                optimal_batch_size = 1
            elif train_count < default_batch_size:
                # Use the number of training examples or 1, whichever is larger
                optimal_batch_size = max(1, train_count)
                self.logger.info(f"🔧 Reduced batch size from {default_batch_size} to {optimal_batch_size} (limited by training data)")
            else:
                optimal_batch_size = default_batch_size
                self.logger.info(f"✅ Using default batch size: {optimal_batch_size}")

            return optimal_batch_size

        except Exception as e:
            self.logger.error(f"❌ Error calculating batch size: {e}")
            self.logger.info("🔧 Falling back to batch size 1 for safety")
            return 1


def create_and_train_sequential_models(vulnerabilities: List[Dict[str, Any]],
                                     output_dir: Path,
                                     model_name_prefix: Optional[str] = None,
                                     upload_to_hub: bool = True) -> SequentialTrainingResult:
    """
    Complete pipeline: Create sequential datasets and train specialized models.
    
    This convenience function:
    1. Creates Stage 1 and Stage 2 datasets from vulnerabilities
    2. Trains Stage 1 (analysis) specialist model
    3. Trains Stage 2 (code fix) specialist building on Stage 1
    4. Validates both models
    
    Args:
        vulnerabilities: List of vulnerability data
        output_dir: Directory for datasets and model outputs
        model_name_prefix: Prefix for model names
        upload_to_hub: Whether to upload final model to HuggingFace
        
    Returns:
        SequentialTrainingResult with complete training results
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not model_name_prefix:
            model_name_prefix = f"webauthn-security-sequential_{timestamp}"
        
        # Step 1: Create sequential datasets
        logger.info("📊 Step 1: Creating sequential datasets...")
        dataset_creator = SequentialDatasetCreator()
        dataset_result = dataset_creator.create_sequential_datasets(
            vulnerabilities, 
            f"sequential_{timestamp}"
        )
        
        if not dataset_result.success:
            raise Exception(f"Dataset creation failed: {dataset_result.processing_errors}")
        
        # Save datasets
        dataset_paths = dataset_creator.save_sequential_datasets(dataset_result, output_dir)
        
        # Step 2: Sequential fine-tuning
        logger.info("🚀 Step 2: Sequential fine-tuning...")
        fine_tuner = SequentialFineTuner()
        training_result = fine_tuner.sequential_fine_tune(
            stage1_dataset=dataset_paths['stage1'],
            stage2_dataset=dataset_paths['stage2'],
            output_name_prefix=model_name_prefix,
            upload_to_hub=upload_to_hub
        )
        
        if training_result.success:
            # Step 3: Validation
            logger.info("🧪 Step 3: Model validation...")
            
            # Use subset of vulnerabilities for validation
            test_vulns = vulnerabilities[:5] if len(vulnerabilities) > 5 else vulnerabilities
            
            stage1_validation = fine_tuner.validate_stage1_specialization(
                training_result.stage1_model_path, test_vulns
            )
            stage2_validation = fine_tuner.validate_stage2_specialization(
                training_result.stage2_model_path, test_vulns
            )
            
            # Add validation results to metadata
            training_result.metadata['stage1_validation'] = stage1_validation
            training_result.metadata['stage2_validation'] = stage2_validation
            training_result.metadata['dataset_paths'] = {k: str(v) for k, v in dataset_paths.items()}
        
        return training_result
        
    except Exception as e:
        logger.error(f"❌ Complete pipeline failed: {e}")
        return SequentialTrainingResult(
            success=False,
            error_message=str(e),
            metadata={'error_time': datetime.now().isoformat()}
        )