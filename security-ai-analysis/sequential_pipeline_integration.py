#!/usr/bin/env python3
"""
Sequential Fine-Tuning Pipeline Integration

Provides integration functions for Sequential Fine-Tuning as part of the complete
security analysis pipeline. This module implements the new default behavior that creates
specialized models for vulnerability analysis and code fix generation.

Architecture:
- Stage 1: Vulnerability Analysis Specialist (base model → analysis expert)
- Stage 2: Code Fix Generation Specialist (Stage 1 model → code fix expert)

This replaces the single-stage fine-tuning approach with progressive specialization
for maximum accuracy and usefulness.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from sequential_fine_tuner import SequentialFineTuner, create_and_train_sequential_models
from sequential_dataset_creator import SequentialDatasetCreator

logger = logging.getLogger(__name__)

def run_sequential_fine_tuning_phase(
    vulnerabilities: List[Dict],
    summary: Dict[str, Any],
    upload_model: bool = True
) -> Dict[str, Any]:
    """
    Execute Sequential Fine-Tuning (always enabled)

    Creates specialized datasets and trains two models:
    1. Stage 1: Vulnerability Analysis Specialist
    2. Stage 2: Code Fix Generation Specialist (builds on Stage 1)

    Args:
        vulnerabilities: List of processed vulnerability data with narratives
        summary: Analysis summary dictionary to update
        upload_model: Upload final model to HuggingFace (default True, disabled by --skip-model-upload)

    Returns:
        Updated summary dictionary with sequential fine-tuning results
    """
    print("\n" + "="*60)
    print("🚀 Sequential Fine-Tuning (Default Behavior)")
    print("🎯 Creating specialized models for maximum accuracy")
    print("="*60)
    
    try:
        # Validate input data
        if not vulnerabilities:
            print("⚠️  No vulnerability data available for sequential fine-tuning")
            summary['sequential_fine_tuning'] = {
                'status': 'skipped', 
                'reason': 'No vulnerability data available'
            }
            return summary
        
        print(f"📊 Processing {len(vulnerabilities)} vulnerabilities for sequential training")
        
        # Create output directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data/sequential_fine_tuning") / f"run_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        model_name_prefix = f"webauthn-security-sequential_{timestamp}"
        
        print(f"📁 Output directory: {output_dir}")
        print(f"🏷️  Model prefix: {model_name_prefix}")
        
        # Run complete sequential fine-tuning pipeline
        print("🔄 Starting complete sequential fine-tuning pipeline...")
        sequential_result = create_and_train_sequential_models(
            vulnerabilities=vulnerabilities,
            output_dir=output_dir,
            model_name_prefix=model_name_prefix,
            upload_to_hub=upload_model
        )
        
        if sequential_result.success:
            print(f"✅ Sequential fine-tuning completed successfully!")
            print(f"   Total time: {sequential_result.total_training_time:.1f}s")
            print(f"   Stage 1 (Analysis): {sequential_result.stage1_training_time:.1f}s")
            print(f"   Stage 2 (Code Fixes): {sequential_result.stage2_training_time:.1f}s")
            print(f"   Stage 1 model: {sequential_result.stage1_model_path}")
            print(f"   Stage 2 model: {sequential_result.stage2_model_path}")
            
            if upload_model and sequential_result.metadata.get('final_model_hub_name'):
                print(f"   HuggingFace: {sequential_result.metadata['final_model_hub_name']}")
            
            # Update summary with successful results
            summary['sequential_fine_tuning'] = {
                'status': 'completed',
                'approach': 'sequential_two_stage',
                'stage1_model_path': sequential_result.stage1_model_path,
                'stage2_model_path': sequential_result.stage2_model_path,
                'stage1_training_time': sequential_result.stage1_training_time,
                'stage2_training_time': sequential_result.stage2_training_time,
                'total_training_time': sequential_result.total_training_time,
                'vulnerabilities_processed': len(vulnerabilities),
                'output_directory': str(output_dir),
                'model_name_prefix': model_name_prefix,
                'upload_requested': upload_model,
                'metadata': sequential_result.metadata
            }
            
            # Add validation results if available
            if 'stage1_validation' in sequential_result.metadata:
                summary['sequential_fine_tuning']['stage1_validation'] = sequential_result.metadata['stage1_validation']
            if 'stage2_validation' in sequential_result.metadata:
                summary['sequential_fine_tuning']['stage2_validation'] = sequential_result.metadata['stage2_validation']
        
        else:
            # Sequential fine-tuning failed
            error_msg = sequential_result.error_message or "Unknown error"
            print(f"❌ Sequential fine-tuning failed: {error_msg}")
            
            summary['sequential_fine_tuning'] = {
                'status': 'failed',
                'error': error_msg,
                'approach': 'sequential_two_stage',
                'vulnerabilities_processed': len(vulnerabilities),
                'metadata': sequential_result.metadata
            }
            
            # Consider fallback to single-stage on failure
            print("🔄 Consider using --disable-sequential-fine-tuning for single-stage fallback")
            
    except ImportError as e:
        # Sequential fine-tuning modules not available - fail fast
        print(f"❌ CRITICAL: Sequential fine-tuning modules not available: {e}")
        print("   Sequential fine-tuning is required but modules are missing")
        summary['sequential_fine_tuning'] = {
            'status': 'critical_failure',
            'reason': f'Sequential modules not available: {e}',
            'error': 'Missing required sequential fine-tuning modules'
        }
        raise RuntimeError(f"Sequential fine-tuning is required but modules are not available: {e}")
        
    except Exception as e:
        # Fail fast on serious errors
        print(f"❌ CRITICAL: Sequential fine-tuning failed with unexpected error: {e}")
        print("   This indicates a serious issue that requires investigation")
        logger.error(f"Critical sequential fine-tuning error: {e}", exc_info=True)
        
        summary['sequential_fine_tuning'] = {
            'status': 'critical_failure',
            'error': str(e),
            'approach': 'sequential_two_stage'
        }
        
        raise  # Re-raise to fail fast
    
    return summary


def is_sequential_fine_tuning_available() -> bool:
    """
    Check if sequential fine-tuning is available (all required modules)
    
    Returns:
        True if sequential fine-tuning can be performed, False otherwise
    """
    try:
        # Try to import all required sequential fine-tuning modules
        from sequential_fine_tuner import SequentialFineTuner, create_and_train_sequential_models
        from sequential_dataset_creator import SequentialDatasetCreator
        from scripts.mlx_finetuning import MLXFineTuner
        from fine_tuning_config import FineTuningConfig
        
        # Try basic initialization to verify dependencies
        config = FineTuningConfig.load_from_config()
        fine_tuner = SequentialFineTuner(config)
        
        return True
        
    except ImportError as e:
        # Expected case: Some modules not available
        logger.info(f"Sequential fine-tuning not available: {e}")
        return False
    except Exception as e:
        # Unexpected errors should fail fast
        logger.error(f"Critical error checking sequential fine-tuning availability: {e}", exc_info=True)
        raise

def get_sequential_fine_tuning_status() -> Dict[str, Any]:
    """
    Get current sequential fine-tuning system status
    
    Returns:
        Status dictionary with availability and module information
    """
    status = {
        'available': False,
        'sequential_modules_loaded': False,
        'mlx_available': False,
        'config_loaded': False,
        'error': None
    }
    
    try:
        # Check sequential fine-tuning modules
        from sequential_fine_tuner import SequentialFineTuner
        from sequential_dataset_creator import SequentialDatasetCreator
        status['sequential_modules_loaded'] = True
        
        # Check MLX and configuration
        from scripts.mlx_finetuning import MLXFineTuner
        from fine_tuning_config import FineTuningConfig
        
        config = FineTuningConfig.load_from_config()
        status['config_loaded'] = True
        
        # Try initializing sequential fine-tuner
        fine_tuner = SequentialFineTuner(config)
        status['mlx_available'] = True
        
        # All checks passed
        status['available'] = True
        
    except ImportError as e:
        status['error'] = f"Module import failed: {e}"
    except Exception as e:
        status['error'] = f"Initialization failed: {e}"
        logger.error(f"Sequential fine-tuning status check error: {e}", exc_info=True)
    
    return status

if __name__ == "__main__":
    # Test the sequential fine-tuning integration
    print("🧪 Testing sequential fine-tuning integration...")
    
    status = get_sequential_fine_tuning_status()
    print(f"Sequential fine-tuning status: {status}")
    
    if status['available']:
        print("✅ Sequential fine-tuning is available and ready to use")
    else:
        print(f"⚠️  Sequential fine-tuning not available: {status.get('error', 'Unknown')}")
        print("   Will fall back to single-stage fine-tuning")