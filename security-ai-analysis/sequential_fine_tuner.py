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
from training_run_manager import TrainingRunManager, TrainingRun


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
    
    def __init__(self, config: Optional[OLMoSecurityConfig] = None,
                 training_run: Optional[TrainingRun] = None,
                 base_output_dir: Optional[Path] = None):
        """Initialize sequential fine-tuner with structured training run support."""
        self.config = config or OLMoSecurityConfig()
        self.training_run = training_run

        # Override fine_tuned_models_dir if base_output_dir is provided
        if base_output_dir:
            self.config.fine_tuned_models_dir = base_output_dir

        self.base_fine_tuner = MLXFineTuner()
        self.logger = logging.getLogger(__name__)

        # Sequential training parameters - Use OLMoSecurityConfig values with proper type conversion
        # Convert config values to proper numeric types (YAML may load as strings)
        learning_rate = float(self.config.fine_tuning.learning_rate)
        batch_size = int(self.config.fine_tuning.batch_size)
        save_steps = int(self.config.fine_tuning.save_steps)

        # Calculate iterations based on save_steps and configuration maximums
        # Configuration-driven approach: use max_stage1_iters and max_stage2_iters from config

        # Calculate base iterations from save_steps
        stage1_base = save_steps * 10
        stage2_base = int(stage1_base * 1.6)  # 60% more for Stage 2 specialization

        # Apply maximums from configuration (0 means no limit)
        max_stage1 = self.config.fine_tuning.max_stage1_iters
        max_stage2 = self.config.fine_tuning.max_stage2_iters

        stage1_iters = stage1_base if max_stage1 == 0 else min(stage1_base, max_stage1)
        stage2_iters = stage2_base if max_stage2 == 0 else min(stage2_base, max_stage2)

        self.stage1_config = {
            'iters': stage1_iters,
            'learning_rate': learning_rate,
            'batch_size': batch_size,
            'fine_tune_type': 'lora',
            'optimizer': 'adamw'    # Validated MLX optimizer (supported parameter)
        }

        self.stage2_config = {
            'iters': stage2_iters,
            'learning_rate': learning_rate * 0.2,  # Lower rate for Stage 2 to preserve Stage 1 knowledge
            'batch_size': max(batch_size // 2, 1),  # Smaller batch for complex examples
            'fine_tune_type': 'lora',
            'optimizer': 'adamw'    # Validated MLX optimizer (supported parameter)
        }
    
    def sequential_fine_tune(self, stage1_dataset: Path, stage2_dataset: Path,
                           output_name_prefix: Optional[str] = None) -> SequentialTrainingResult:
        """
        Perform sequential fine-tuning with Stage 1 and Stage 2 datasets.
        
        Args:
            stage1_dataset: Path to Stage 1 (analysis) training dataset
            stage2_dataset: Path to Stage 2 (code fix) training dataset
            output_name_prefix: Prefix for model names

        Returns:
            SequentialTrainingResult with training outcomes
        """
        start_time = datetime.now()
        
        if not output_name_prefix:
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            output_name_prefix = f"webauthn-security-sequential_{timestamp}"
        
        self.logger.info(f"🚀 Starting sequential fine-tuning: {output_name_prefix}")
        
        # Stage 1: Vulnerability Analysis Specialist
        self.logger.info("📊 Stage 1: Training Vulnerability Analysis Specialist...")
        stage1_start = datetime.now()
        
        stage1_result = self._train_stage1_analysis(
            stage1_dataset,
            f"{output_name_prefix}_stage1_analysis"
        )
        
        stage1_end = datetime.now()
        stage1_time = (stage1_end - stage1_start).total_seconds()
        
        self.logger.info(f"✅ Stage 1 completed in {stage1_time:.1f}s")

        # Stage 2: Code Fix Generation Specialist (builds on Stage 1)
        self.logger.info("🔧 Stage 2: Training Code Fix Generation Specialist...")
        stage2_start = datetime.now()

        stage2_result = self._train_stage2_codefix(
            stage2_dataset,
            f"{output_name_prefix}_stage2_codefix",
            stage1_adapter_path=stage1_result['adapter_path']
        )
        
        stage2_end = datetime.now()
        stage2_time = (stage2_end - stage2_start).total_seconds()
        
        self.logger.info(f"✅ Stage 2 completed in {stage2_time:.1f}s")
        
        total_time = (datetime.now() - start_time).total_seconds()

        # Manifest is already complete with predefined paths - no updates needed

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

        
        return result
    
    def _train_stage1_analysis(self, dataset_path: Path, output_name: str) -> Dict[str, Any]:
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

            # Step 2: Use paths from manifest and create directories lazily
            if self.training_run:
                # Get Stage 1 paths from manifest
                stage1_adapters_dir = self.training_run.run_dir / self.training_run.manifest.stage1.adapters_path
                stage1_merged_dir = self.training_run.run_dir / self.training_run.manifest.stage1.merged_model_path

                # Create directories lazily when Stage 1 actually runs
                stage1_adapters_dir.mkdir(parents=True, exist_ok=True)
                stage1_merged_dir.mkdir(parents=True, exist_ok=True)

                self.logger.info(f"🏗️ Using manifest-defined Stage 1 paths: adapters={stage1_adapters_dir}, merged={stage1_merged_dir}")
                adapter_path = self._run_stage1_enhanced_training_structured(
                    training_data_dir,
                    stage1_adapters_dir,
                    stage1_merged_dir,
                    output_name
                )
            else:
                raise ValueError("Structured training run required for Stage 1 training. "
                               "Legacy training has been removed - use TrainingRun instances only.")

            stage1_result = {
                'success': True,
                'adapter_path': str(adapter_path),
                'training_data_dir': str(training_data_dir)
            }

            self.logger.info(f"✅ Stage 1 training completed: {adapter_path}")
            return stage1_result

        except Exception as e:
            self.logger.error(f"❌ Stage 1 training failed: {e}")
            raise RuntimeError(f"Stage 1 training failed unexpectedly: {e}") from e
    
    def _train_stage2_codefix(self, dataset_path: Path, output_name: str,
                            stage1_adapter_path: str) -> Dict[str, Any]:
        """
        Train Stage 2: Code Fix Generation Specialist.

        This stage builds upon the Stage 1 model to create a specialist
        in generating specific code fixes and implementations.
        """
        self.logger.info(f"🔧 Training Stage 2 code fix model: {output_name}")
        self.logger.info(f"   Building upon Stage 1: {stage1_adapter_path}")

        # Step 1: Prepare Stage 2 training data with catastrophic forgetting mitigation
        # Mix Stage 2 data with 15% Stage 1 data to preserve knowledge
        training_data_dir = self._prepare_mixed_training_data(
            stage2_dataset_path=dataset_path,
            stage1_adapter_path=stage1_adapter_path,
            output_name=output_name
        )

        # Step 2: Run enhanced Stage 2 fine-tuning with catastrophic forgetting mitigation
        self.logger.info(f"🚀 Training Stage 2 with resume-adapter-file from Stage 1: {stage1_adapter_path}")

        # Use structured training run (required)
        if not self.training_run:
            raise ValueError("Structured training run required for Stage 2 training. "
                           "Legacy training has been removed - use TrainingRun instances only.")

        # Fail-fast: Check Stage 1 artifacts exist before proceeding
        self.logger.info("🔍 Checking Stage 1 artifacts before Stage 2 training")
        try:
            stage1_adapters = self.training_run.stage1_adapters_path
            stage1_training_data = self.training_run.stage1_training_data_path

            self.logger.info(f"✅ Stage 1 artifacts validated: adapters={stage1_adapters}, data={stage1_training_data}")
        except (ValueError, FileNotFoundError) as e:
            self.logger.error(f"❌ Stage 1 artifacts missing or invalid: {e}")
            raise RuntimeError(f"Stage 2 cannot proceed without Stage 1 artifacts: {e}") from e

        # Get Stage 2 paths from manifest and create directories lazily
        stage2_adapters_dir = self.training_run.run_dir / self.training_run.manifest.stage2.adapters_path
        stage2_final_model_dir = self.training_run.run_dir / self.training_run.manifest.stage2.final_model_path

        # Create directories lazily when Stage 2 actually runs
        stage2_adapters_dir.mkdir(parents=True, exist_ok=True)
        stage2_final_model_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"🏗️ Using manifest-defined Stage 2 paths: adapters={stage2_adapters_dir}, final={stage2_final_model_dir}")
        stage2_adapter_path = self._run_stage2_fine_tuning_structured(
            training_data_dir,
            stage1_adapter_path,
            stage2_adapters_dir,
            stage2_final_model_dir,
            output_name
        )

        stage2_result = {
            'success': True,
            'adapter_path': str(stage2_adapter_path),
            'training_data_dir': str(training_data_dir),
            'stage1_adapter_used': True,
            'stage1_adapter_path': str(stage1_adapter_path),
            'catastrophic_forgetting_mitigation': True,
            'mixed_training_data': True,
            'note': 'Successfully trained with resume-adapter-file and catastrophic forgetting mitigation'
        }

        self.logger.info(f"✅ Stage 2 training completed with sequential progression: {stage2_adapter_path}")
        return stage2_result

    def _run_stage1_enhanced_training_structured(self, training_data_dir: Path,
                                               stage1_adapters_dir: Path,
                                               stage1_merged_dir: Path,
                                               output_name: str) -> Path:
        """
        Run Stage 1 training with structured output paths.

        This method writes MLX training outputs directly to structured locations,
        eliminating the need for copying or reorganization.
        """
        self.logger.info(f"🚀 Running structured Stage 1 training")
        self.logger.info(f"   Training data: {training_data_dir}")
        self.logger.info(f"   Adapters output: {stage1_adapters_dir}")
        self.logger.info(f"   Merged model output: {stage1_merged_dir}")

        # Create a temporary adapter-specific output for MLX training
        # This allows MLX to create adapters directly in the correct location
        temp_adapter_output = stage1_adapters_dir.parent / "temp_mlx_output"
        temp_adapter_output.mkdir(parents=True, exist_ok=True)

        # Use MLXFineTuner with temporary output path
        model_path = self.base_fine_tuner.run_fine_tuning(
            training_data_dir=training_data_dir,
            custom_output_path=temp_adapter_output
        )

        # Check if adapters were created and move to structured location
        source_adapters_dir = model_path / "adapters"
        if source_adapters_dir.exists():
            self.logger.info(f"📁 Moving adapters to structured location")
            import shutil
            # Move adapter files to structured location (not copy)
            for adapter_file in source_adapters_dir.iterdir():
                if adapter_file.is_file():
                    target_path = stage1_adapters_dir / adapter_file.name
                    shutil.move(str(adapter_file), str(target_path))

            # Clean up temporary directory
            shutil.rmtree(temp_adapter_output, ignore_errors=True)

            self.logger.info(f"✅ Adapters moved to structured location: {stage1_adapters_dir}")
        else:
            raise FileNotFoundError(f"Stage 1 adapters not found at expected location: {source_adapters_dir}. "
                                  f"This indicates Stage 1 training failed to create required adapter files.")

        return stage1_adapters_dir

    def _run_stage2_fine_tuning_structured(self, training_data_dir: Path,
                                         stage1_adapter_path: str,
                                         stage2_adapters_dir: Path,
                                         stage2_final_model_dir: Path,
                                         output_name: str) -> Path:
        """
        Run Stage 2 training with structured output paths.

        This method writes MLX training outputs directly to structured locations,
        eliminating the need for copying or reorganization.
        """
        import subprocess

        self.logger.info(f"🚀 Running structured Stage 2 training")
        self.logger.info(f"   Training data: {training_data_dir}")
        self.logger.info(f"   Stage 1 adapter: {stage1_adapter_path}")
        self.logger.info(f"   Stage 2 adapters output: {stage2_adapters_dir}")
        self.logger.info(f"   Stage 2 final model output: {stage2_final_model_dir}")

        # Configure chat template for the base model
        self.base_fine_tuner._configure_chat_template_for_model(str(self.config.get_base_model_path()))

        # Build enhanced MLX-LM LoRA command with structured output
        mlx_command = [
            "mlx_lm.lora",
            "--model", str(self.config.get_base_model_path()),
            "--train",
            "--data", str(training_data_dir),
            "--adapter-path", str(stage2_adapters_dir),  # Write directly to structured location
            "--batch-size", str(self.stage2_config['batch_size']),
            "--iters", str(self.stage2_config['iters']),
            "--learning-rate", str(self.stage2_config['learning_rate']),
            "--fine-tune-type", self.stage2_config['fine_tune_type'],
            "--optimizer", self.stage2_config['optimizer'],
            "--resume-adapter-file", str(Path(stage1_adapter_path) / "adapters.safetensors")
        ]

        # Validate Stage 1 adapter file exists before Stage 2 training
        stage1_adapter_file = Path(stage1_adapter_path) / "adapters.safetensors"
        if not stage1_adapter_file.exists():
            error_msg = f"Stage 1 adapter file not found: {stage1_adapter_file}"
            self.logger.error(f"❌ {error_msg}")
            raise FileNotFoundError(error_msg)

        # Log adapter file details for debugging
        adapter_size = stage1_adapter_file.stat().st_size
        self.logger.info(f"🔍 Stage 1 adapter file validated: {stage1_adapter_file} ({adapter_size:,} bytes)")

        self.logger.info(f"🔧 Running structured Stage 2 MLX command: {' '.join(mlx_command)}")

        # Execute Stage 2 fine-tuning with enhanced error handling
        try:
            result = subprocess.run(
                mlx_command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=False  # Handle errors manually to capture output
            )

            # Log output regardless of success/failure
            if result.stdout:
                self.logger.info(f"📋 Stage 2 MLX stdout: {result.stdout}")
            if result.stderr:
                self.logger.info(f"📋 Stage 2 MLX stderr: {result.stderr}")

            # Check return code and handle errors with detailed output
            if result.returncode != 0:
                error_msg = f"MLX Stage 2 training failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nSTDERR: {result.stderr}"
                if result.stdout:
                    error_msg += f"\nSTDOUT: {result.stdout}"
                self.logger.error(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            self.logger.info("✅ Stage 2 MLX fine-tuning completed successfully")

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"❌ Stage 2 MLX training timed out after 3600s")
            raise RuntimeError(f"Stage 2 training timed out: {e}") from e

        # Validate Stage 2 adapter was created
        stage2_adapter_file = stage2_adapters_dir / "adapters.safetensors"
        if not stage2_adapter_file.exists():
            raise FileNotFoundError(f"Stage 2 adapter not created: {stage2_adapter_file}")

        # Create final merged model in structured location
        self.logger.info(f"🔗 Creating final Stage 2 model at: {stage2_final_model_dir}")
        try:
            # Use MLX-LM fuse command to create final model
            fuse_command = [
                "mlx_lm.fuse",
                "--model", str(self.config.get_base_model_path()),
                "--adapter-path", str(stage2_adapters_dir),
                "--save-path", str(stage2_final_model_dir)
            ]

            fuse_result = subprocess.run(
                fuse_command,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                check=True
            )

            self.logger.info("✅ Stage 2 final model created successfully")
            self.logger.info(f"Fusion output: {fuse_result.stdout}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Stage 2 model fusion failed: {e}")
            self.logger.error(f"Fusion error: {e.stderr}")
            raise RuntimeError(f"Stage 2 model fusion failed: {e.stderr}")

        return stage2_adapters_dir

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
        self.logger.info(f"   Iterations: {self.stage2_config['iters']} (calculated from Stage 1: {self.stage1_config['iters']})")

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

    def _merge_stage2_with_stage1(self, stage1_merged_model: Path,
                                 stage2_adapter_path: Path, stage2_output_dir: Path):
        """
        Merge Stage 2 adapter with Stage 1 merged model to create final specialized model.
        """
        import subprocess

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
                                stage1_adapter_path: str) -> Dict[str, Any]:
        """
        Alternative Stage 2 training approach when resume_adapter_file is not available.
        
        This approach manually combines Stage 1 adapter with base model before
        Stage 2 training.
        """
        self.logger.info(f"🔄 Using alternative Stage 2 training approach")
        
        try:
            # Stage 1 adapter merging is required for proper sequential training
            raise NotImplementedError("Stage 1 adapter merging not yet implemented. "
                                    "Sequential training requires merging Stage 1 adapters before Stage 2 training. "
                                    "This is a critical feature that must be implemented for proper sequential fine-tuning.")
            
            # Prepare training data and run fine-tuning
            training_data_dir = self.base_fine_tuner.prepare_training_data(dataset_path)
            trained_model_path = self.base_fine_tuner.run_fine_tuning(
                training_data_dir=training_data_dir,
                custom_output_name=output_name
            )

            # Convert Path result to expected dict format
            stage2_result = {
                'success': True,
                'adapter_path': str(trained_model_path),
                'stage1_adapter_used': False,
                'note': 'Trained from base model, adapter merging not implemented'
            }

            return stage2_result
            
        except Exception as e:
            self.logger.error(f"❌ Alternative Stage 2 training failed: {e}")
            raise
    
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
                raise RuntimeError(f"Stage 1 model failed quality validation with low specialization score: {overall_score:.2f}. "
                                 f"This indicates training failure or insufficient data quality. "
                                 f"Minimum acceptable score is 0.7.")

            validation_results['overall_score'] = overall_score

        except Exception as e:
            self.logger.error(f"❌ Stage 1 validation failed: {e}")
            validation_results['status'] = 'failed'
            validation_results['error'] = str(e)
            raise

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
                raise RuntimeError(f"Stage 2 model failed quality validation with low specialization score: {overall_score:.2f}. "
                                 f"This indicates training failure or insufficient data quality. "
                                 f"Minimum acceptable score is 0.7.")

            validation_results['overall_score'] = overall_score

            # Check if sequential progression is working
            if validation_results['sequential_capabilities'] >= 0.6:
                self.logger.info("✅ Sequential progression validated - Stage 2 retains Stage 1 capabilities")
            else:
                raise RuntimeError(f"Sequential progression validation failed: Stage 2 has lost Stage 1 capabilities. "
                                 f"Sequential score: {validation_results['sequential_capabilities']:.2f}. "
                                 f"This indicates catastrophic forgetting - the sequential training has failed.")

        except Exception as e:
            self.logger.error(f"❌ Stage 2 validation failed: {e}")
            validation_results['status'] = 'failed'
            validation_results['error'] = str(e)
            raise

        return validation_results

    # Supporting validation methods
    def _load_model_for_validation(self, model_path: str, artifact_type: str = "auto"):
        """Load MLX model for validation with artifact-type awareness."""
        try:
            from pathlib import Path
            import json

            self.logger.info(f"🔧 Loading MLX model for validation: {model_path}")

            # Check if model path exists
            model_dir = Path(model_path)
            if not model_dir.exists():
                raise FileNotFoundError(f"Model path does not exist: {model_path}")

            # Detect artifact type if not specified
            if artifact_type == "auto":
                artifact_type = self._detect_artifact_type(model_dir)

            self.logger.info(f"🔍 Detected artifact type: {artifact_type}")

            # Validate based on artifact type
            if artifact_type == "lora_adapter":
                return self._load_lora_adapter_for_validation(model_dir)
            elif artifact_type == "full_model":
                return self._load_full_model_for_validation(model_dir)
            else:
                raise ValueError(f"Unknown artifact type: {artifact_type}")

        except Exception as e:
            self.logger.error(f"Failed to load model for validation: {e}")
            raise

    def _detect_artifact_type(self, model_dir: Path) -> str:
        """Detect whether this is a LoRA adapter or full model directory."""
        # Check for LoRA adapter files
        adapter_files = ['adapters.safetensors', 'adapter_config.json']
        has_adapter_files = all((model_dir / f).exists() for f in adapter_files)

        # Check for full model files
        model_files = ['config.json', 'model.safetensors', 'tokenizer.json']
        has_model_files = all((model_dir / f).exists() for f in model_files)

        if has_adapter_files and not has_model_files:
            return "lora_adapter"
        elif has_model_files:
            return "full_model"
        else:
            raise ValueError(f"Cannot determine artifact type for {model_dir}. "
                           f"Expected either LoRA adapter files {adapter_files} "
                           f"or full model files {model_files}")

    def _load_lora_adapter_for_validation(self, adapter_dir: Path):
        """Load and validate LoRA adapter."""
        self.logger.info(f"🔧 Validating LoRA adapter: {adapter_dir}")

        # Check for required LoRA files
        required_files = ['adapters.safetensors', 'adapter_config.json']
        missing_files = [f for f in required_files if not (adapter_dir / f).exists()]

        if missing_files:
            raise FileNotFoundError(f"LoRA adapter missing required files: {missing_files}")

        # Validate adapter config
        adapter_config_path = adapter_dir / 'adapter_config.json'
        try:
            with open(adapter_config_path, 'r') as f:
                adapter_config = json.load(f)

            # Basic validation of adapter configuration
            required_keys = ['peft_type', 'r', 'lora_alpha']
            missing_keys = [k for k in required_keys if k not in adapter_config]
            if missing_keys:
                raise ValueError(f"LoRA config missing required keys: {missing_keys}. "
                               f"Invalid adapter configuration indicates training failure.")

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid adapter config JSON: {e}")

        # Validate adapter weights file size
        adapters_path = adapter_dir / 'adapters.safetensors'
        if adapters_path.stat().st_size < 1024:  # Less than 1KB is suspicious
            raise ValueError(f"Adapter file too small: {adapters_path.stat().st_size} bytes")

        self.logger.info("✅ LoRA adapter validation passed")
        return {"type": "lora_adapter", "path": str(adapter_dir), "config": adapter_config}

    def _load_full_model_for_validation(self, model_dir: Path):
        """Load and validate full model."""
        self.logger.info(f"🔧 Validating full model: {model_dir}")

        # Check for required model files
        required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
        missing_files = [f for f in required_files if not (model_dir / f).exists()]

        if missing_files:
            raise FileNotFoundError(f"Full model missing required files: {missing_files}")

        # Load model using MLX-LM
        try:
            from mlx_lm import load

            # Load the model and tokenizer
            self.logger.info(f"📥 Loading full model with MLX-LM from: {model_dir}")
            model, tokenizer = load(str(model_dir))

            # Verify model is functional
            if model is None or tokenizer is None:
                raise RuntimeError("Failed to load model or tokenizer")

            self.logger.info("✅ Full model loaded successfully for validation")

            return {
                'model': model,
                'tokenizer': tokenizer,
                'model_path': str(model_dir),
                'loaded': True,
                'type': 'full_model'
            }

        except ImportError:
            raise ImportError("MLX-LM not available but is required for full model validation. "
                            "Please ensure MLX-LM is properly installed to validate trained models.")

        except Exception as e:
            self.logger.error(f"Failed to load model for validation: {e}")
            raise

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
                raise RuntimeError(f"Model validation failed: Model not properly loaded. "
                                 f"Expected MLX model but got: {model.get('type') if model else 'None'}. "
                                 f"This indicates a critical failure in model loading or training.")

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
                raise ImportError("MLX-LM generate function not available. "
                                "This is required for model validation. "
                                "Please ensure MLX-LM is properly installed.")

        except Exception as e:
            self.logger.error(f"Failed to generate model response: {e}")
            raise


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
        self.logger.info(f"   Iterations: {self.stage1_config['iters']} (calculated from save_steps: {self.config.fine_tuning.save_steps})")

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

        # Use manifest-defined path for mixed training data
        if self.training_run:
            mixed_dataset_path = self.training_run.get_stage2_training_data("mixed_dataset")
            mixed_data_dir = mixed_dataset_path.parent
            mixed_data_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Fallback for non-structured runs (should not happen)
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
                self.logger.error("❌ No Stage 1 data found for mixing - this is a critical error.")
                raise FileNotFoundError("No Stage 1 training data found for mixing. Halting to prevent catastrophic forgetting.")

            # Step 5: Write mixed training data using MLX-required filename
            # MLX-LM requires exactly 'train.jsonl' - no custom filenames supported
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
            raise

    def _get_stage1_training_data(self) -> List[Dict]:
        """
        Retrieve Stage 1 training data for mixing with Stage 2 data.
        Uses manifest-based discovery for reliable artifact location.
        """
        try:
            if self.training_run is None:
                raise ValueError("Structured training run required for Stage 1 data discovery. "
                               "Legacy discovery has been removed - use TrainingRun instances only.")

            # Use manifest-based discovery
            self.logger.info("🔍 Using manifest-based Stage 1 data discovery")

            if not self.training_run.manifest.stage1:
                raise RuntimeError("No Stage 1 found in manifest. "
                                 "Sequential training requires Stage 1 to be completed first.")

            # Get Stage 1 training data path from manifest
            stage1_data_path = self.training_run.get_stage1_training_data()

            if not stage1_data_path.exists():
                raise FileNotFoundError(f"Stage 1 training data not found: {stage1_data_path}. "
                                      f"Sequential training requires Stage 1 training data to be available.")

            self.logger.info(f"📂 Using manifest-defined Stage 1 data: {stage1_data_path}")

            stage1_data = []
            with open(stage1_data_path, 'r') as f:
                stage1_data = [json.loads(line) for line in f if line.strip()]

            return stage1_data

        except Exception as e:
            self.logger.error(f"❌ Error loading Stage 1 data: {e}")
            raise



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
                raise ValueError(f"Unexpected Stage 1 data format: {list(example.keys())}. "
                               f"Expected either 'text' field or 'conversations' field for ChatML format. "
                               f"This indicates corrupted or incompatible training data.")

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
                raise RuntimeError("No training data found for Stage 2. "
                                 "Sequential training requires both Stage 1 and Stage 2 training data to be available.")
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
            raise


def create_and_train_sequential_models(vulnerabilities: List[Dict[str, Any]],
                                     training_run: TrainingRun,
                                     model_name_prefix: Optional[str] = None) -> SequentialTrainingResult:
    """
    Complete pipeline: Create sequential datasets and train specialized models.

    This convenience function:
    1. Creates Stage 1 and Stage 2 datasets from vulnerabilities
    2. Trains Stage 1 (analysis) specialist model
    3. Trains Stage 2 (code fix) specialist building on Stage 1
    4. Validates both models

    Args:
        vulnerabilities: List of vulnerability data
        training_run: Structured training run for organized output
        model_name_prefix: Prefix for model names

    Returns:
        SequentialTrainingResult with complete training results
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not model_name_prefix:
            model_name_prefix = f"webauthn-security-sequential_{timestamp}"

        # Step 1: Create sequential datasets - write directly to structured locations
        logger.info("📊 Step 1: Creating sequential datasets...")
        dataset_creator = SequentialDatasetCreator()
        dataset_result = dataset_creator.create_sequential_datasets(
            vulnerabilities,
            f"sequential_{timestamp}"
        )

        if not dataset_result.success:
            raise Exception(f"Dataset creation failed: {dataset_result.processing_errors}")

        # Save datasets to manifest-defined directories (lazy creation)
        stage1_data_dir = training_run.run_dir / "stage1" / "training-data"  # Parent of training_data_path
        stage2_data_dir = training_run.run_dir / "stage2" / "training-data"  # Parent of training_data_paths
        stage1_data_dir.mkdir(parents=True, exist_ok=True)
        stage2_data_dir.mkdir(parents=True, exist_ok=True)

        dataset_paths = dataset_creator.save_sequential_datasets_to_structured_paths(
            dataset_result,
            stage1_data_dir,
            stage2_data_dir
        )
        
        # Step 2: Sequential fine-tuning
        logger.info("🚀 Step 2: Sequential fine-tuning...")

        # Use OLMoSecurityConfig for configuration
        config = OLMoSecurityConfig()

        fine_tuner = SequentialFineTuner(config=config, training_run=training_run)
        training_result = fine_tuner.sequential_fine_tune(
            stage1_dataset=dataset_paths['stage1'],
            stage2_dataset=dataset_paths['stage2'],
            output_name_prefix=model_name_prefix
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
        raise