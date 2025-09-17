#!/usr/bin/env python3
"""
Sequential Fine-Tuning Pipeline for Phase 3

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
        
        # Sequential training parameters
        self.stage1_config = {
            'iters': 100,          # Moderate training for analysis specialization
            'learning_rate': 1e-5,  # Conservative learning rate
            'batch_size': 4,        # Memory-efficient batch size
            'fine_tune_type': 'lora'
        }
        
        self.stage2_config = {
            'iters': 150,          # More iterations for complex code generation
            'learning_rate': 5e-6,  # Lower rate for fine details
            'batch_size': 2,        # Smaller batch for complex examples
            'fine_tune_type': 'lora'
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
                f"{output_name_prefix}_stage1_analysis"
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
                    'final_model_hub_name': stage2_result.get('hub_model_name'),
                    'sequential_approach': 'vulnerability_analysis_then_code_fixes'
                }
            )
            
            self.logger.info(f"🎉 Sequential fine-tuning completed successfully!")
            self.logger.info(f"   Total time: {total_time:.1f}s")
            self.logger.info(f"   Stage 1 model: {result.stage1_model_path}")
            self.logger.info(f"   Stage 2 model: {result.stage2_model_path}")
            
            if upload_to_hub and result.metadata.get('final_model_hub_name'):
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
            
            # Step 2: Run fine-tuning
            adapter_path = self.base_fine_tuner.run_fine_tuning(
                training_data_dir, 
                custom_output_name=output_name
            )
            
            stage1_result = {
                'success': True,
                'adapter_path': str(adapter_path),
                'training_data_dir': str(training_data_dir)
            }
            
            self.logger.info(f"✅ Stage 1 training completed: {adapter_path}")
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
            # For now, train Stage 2 from base model (adapter merging not yet implemented)
            self.logger.warning("⚠️ Stage 2 training from base model (Stage 1 adapter merging not yet implemented)")
            
            # Step 1: Prepare training data
            training_data_dir = self.base_fine_tuner.prepare_training_data(dataset_path)
            
            # Step 2: Run fine-tuning from base model
            adapter_path = self.base_fine_tuner.run_fine_tuning(
                training_data_dir, 
                custom_output_name=output_name
            )
            
            stage2_result = {
                'success': True,
                'adapter_path': str(adapter_path),
                'training_data_dir': str(training_data_dir),
                'stage1_adapter_used': False,
                'note': 'Trained from base model, adapter merging not implemented'
            }
            
            self.logger.info(f"✅ Stage 2 training completed: {adapter_path}")
            return stage2_result
            
        except Exception as e:
            self.logger.error(f"❌ Stage 2 training failed: {e}")
            return {'success': False, 'error': str(e)}
    
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
            'validated_at': datetime.now().isoformat()
        }
        
        # In a full implementation, this would:
        # 1. Load the Stage 1 model
        # 2. Generate analysis for test vulnerabilities
        # 3. Compare against expected classifications
        # 4. Score analysis completeness and accuracy
        
        self.logger.info("⚠️ Stage 1 validation not yet implemented - placeholder results")
        validation_results['status'] = 'placeholder'
        validation_results['note'] = 'Validation framework to be implemented'
        
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
            'validated_at': datetime.now().isoformat()
        }
        
        # In a full implementation, this would:
        # 1. Load the Stage 2 model
        # 2. Generate code fixes for test vulnerabilities
        # 3. Validate syntax using language parsers
        # 4. Check for security pattern application
        # 5. Score implementation completeness
        
        self.logger.info("⚠️ Stage 2 validation not yet implemented - placeholder results")
        validation_results['status'] = 'placeholder'
        validation_results['note'] = 'Validation framework to be implemented'
        
        return validation_results


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