#!/usr/bin/env python3
"""
Pipeline Integration for MLX Fine-Tuning

Provides integration functions for adding fine-tuning to the security analysis pipeline.
This module handles Phase 5: MLX Fine-Tuning as part of the complete analysis workflow.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

def run_fine_tuning_phase(
    train_file: Path, 
    train_data: List[Dict], 
    summary: Dict[str, Any],
    skip_fine_tuning: bool = False,
    upload_model: bool = True
) -> Dict[str, Any]:
    """
    Execute Phase 5: MLX Fine-Tuning as part of the pipeline
    
    Args:
        train_file: Path to training dataset file
        train_data: Training data list for metadata
        summary: Analysis summary dictionary to update
        skip_fine_tuning: CLI flag to skip fine-tuning (opt-out, default False)
        upload_model: Upload model to HuggingFace (default True, disabled by --skip-model-upload)
    
    Returns:
        Updated summary dictionary with fine-tuning results
    """
    
    # Check CLI opt-out first (development/testing mode)
    if skip_fine_tuning:
        print("\n" + "="*60)
        print("⏭️  Phase 5: MLX Fine-Tuning (SKIPPED)")
        print("🔧 Fine-tuning disabled via --skip-fine-tuning flag")
        print("   This is for development/testing - remove flag for complete pipeline")
        print("="*60)
        summary['fine_tuning'] = {'status': 'skipped', 'reason': 'disabled via CLI --skip-fine-tuning flag'}
        return summary
    
    print("\n" + "="*60)
    print("🚀 Phase 5: MLX Fine-Tuning (Default Behavior)")
    print("="*60)
    
    try:
        from fine_tuning_config import FineTuningConfig
        
        # Load fine-tuning configuration
        ft_config = FineTuningConfig.load_from_config()
        
        # Check if fine-tuning should be skipped (emergency override per original design)
        if ft_config.skip_in_daemon:
            print("⚠️  Fine-tuning skipped (emergency override: skip_in_daemon=true)")
            print("   This should only be used when fine-tuning is broken and needs temporary disable")
            summary['fine_tuning'] = {'status': 'skipped', 'reason': 'emergency override - skip_in_daemon=true'}
            return summary
            
        print(f"🎯 Starting MLX fine-tuning with dataset: {train_file}")
        print(f"📊 Training examples: {len(train_data)}")
        print(f"📁 Output model: {ft_config.output_model_name}")
        
        # Import and initialize MLX fine-tuner
        try:
            # Import within try block since MLX might not be available
            from scripts.mlx_finetuning import MLXFineTuner
            
            fine_tuner = MLXFineTuner(ft_config)
            
            # Convert dataset format for MLX fine-tuning
            print("🔄 Preparing training data for MLX...")
            mlx_training_file = fine_tuner.prepare_training_data(train_file)
            
            # Run fine-tuning
            print("⚡ Starting MLX fine-tuning process...")
            fine_tuned_model_path = fine_tuner.run_fine_tuning(mlx_training_file)
            
            print(f"✅ Fine-tuning completed successfully!")
            print(f"📁 Model saved to: {fine_tuned_model_path}")
            
            # Upload to HuggingFace if enabled (default enabled, disabled by --skip-model-upload)
            should_upload = upload_model or ft_config.upload_enabled
            
            if should_upload:
                if upload_model:
                    print("📤 Uploading fine-tuned model to HuggingFace (default behavior)...")
                else:
                    print("📤 Uploading fine-tuned model to HuggingFace (config enabled)...")
                
                repo_url = fine_tuner.upload_to_huggingface(fine_tuned_model_path)
                if repo_url:
                    print(f"✅ Model uploaded: {repo_url}")
                    summary['fine_tuning_upload'] = {'status': 'completed', 'url': repo_url}
                else:
                    print("❌ Model upload failed (check logs)")
                    summary['fine_tuning_upload'] = {'status': 'failed'}
            else:
                print("📤 HuggingFace model upload disabled (--skip-model-upload)")
            
            # Update summary with fine-tuning info
            summary['fine_tuning'] = {
                'status': 'completed',
                'model_path': str(fine_tuned_model_path),
                'training_examples': len(train_data),
                'base_model': ft_config.base_model_name,
                'output_model': ft_config.output_model_name,
                'upload_requested': upload_model,
                'upload_enabled': should_upload
            }
            
        except ImportError as e:
            # Legitimate opt-out: MLX not available (platform limitation)
            print(f"⚠️  MLX fine-tuning not available: {e}")
            print("   This is expected if MLX is not installed or not on Apple Silicon")
            summary['fine_tuning'] = {'status': 'skipped', 'reason': 'MLX not available'}
            
        except RuntimeError as e:
            if "MLX not available" in str(e):
                # Legitimate opt-out: MLX unavailable on this platform
                print(f"⚠️  MLX fine-tuning not available: {e}")
                print("   This is expected if MLX is not installed or not on Apple Silicon")
                summary['fine_tuning'] = {'status': 'skipped', 'reason': 'MLX not available'}
            else:
                # Other runtime errors should fail fast
                print(f"❌ CRITICAL: Runtime error during fine-tuning: {e}")
                logger.error(f"Critical runtime error: {e}", exc_info=True)
                raise  # Re-raise to fail fast
            
        except (OSError, PermissionError) as e:
            # Fail fast on serious system issues
            print(f"❌ CRITICAL: System error during fine-tuning: {e}")
            logger.error(f"Critical system error: {e}", exc_info=True)
            raise  # Re-raise to fail fast
            
        except Exception as e:
            # Fail fast on unexpected errors (disk space, model corruption, etc.)
            print(f"❌ CRITICAL: Fine-tuning failed with unexpected error: {e}")
            print("   This indicates a serious issue that requires investigation")
            logger.error(f"Critical fine-tuning error: {e}", exc_info=True)
            raise  # Re-raise to fail fast
    
    except ImportError as e:
        # Configuration module missing - this should fail fast
        print(f"❌ CRITICAL: Fine-tuning configuration module not available: {e}")
        logger.error(f"Critical config error: {e}", exc_info=True)
        raise  # Re-raise to fail fast
    
    return summary

def add_fine_tuning_cli_args(parser):
    """
    Add fine-tuning related CLI arguments to argument parser
    
    Args:
        parser: argparse.ArgumentParser instance to extend
    """
    parser.add_argument(
        "--skip-fine-tuning", 
        action="store_true", 
        help="Skip fine-tuning phase (emergency override)"
    )
    parser.add_argument(
        "--fine-tuning-upload", 
        action="store_true", 
        help="Force enable HuggingFace model upload (overrides config)"
    )
    parser.add_argument(
        "--fine-tuning-output-name", 
        type=str, 
        help="Custom output model name for fine-tuning"
    )
    
def apply_cli_overrides(ft_config, args):
    """
    Apply CLI argument overrides to fine-tuning configuration
    
    Args:
        ft_config: FineTuningConfig instance
        args: Parsed CLI arguments
        
    Returns:
        Modified ft_config with CLI overrides applied
    """
    if hasattr(args, 'skip_fine_tuning') and args.skip_fine_tuning:
        ft_config.skip_in_daemon = True
        logger.info("CLI override: Fine-tuning disabled via --skip-fine-tuning")
    
    if hasattr(args, 'fine_tuning_upload') and args.fine_tuning_upload:
        ft_config.upload_enabled = True
        logger.info("CLI override: HuggingFace upload enabled via --fine-tuning-upload")
    
    if hasattr(args, 'fine_tuning_output_name') and args.fine_tuning_output_name:
        ft_config.output_model_name = args.fine_tuning_output_name
        logger.info(f"CLI override: Output model name set to {args.fine_tuning_output_name}")
    
    return ft_config

def is_fine_tuning_available() -> bool:
    """
    Check if fine-tuning is available (configuration and MLX)
    
    Returns:
        True if fine-tuning can be performed, False otherwise
    """
    try:
        from fine_tuning_config import FineTuningConfig
        from scripts.mlx_finetuning import MLXFineTuner
        
        # Try to load configuration
        config = FineTuningConfig.load_from_config()
        
        # Try to initialize MLX fine-tuner (will check MLX availability)
        fine_tuner = MLXFineTuner(config)
        
        return True
        
    except ImportError:
        # Legitimate case: MLX or config not available
        return False
    except RuntimeError as e:
        if "MLX not available" in str(e):
            # Legitimate case: MLX not available on this platform
            return False
        else:
            # Other runtime errors should fail fast
            logger.error(f"Critical runtime error checking availability: {e}", exc_info=True)
            raise
    except Exception as e:
        # Fail fast on serious errors
        logger.error(f"Critical error checking fine-tuning availability: {e}", exc_info=True)
        raise

def get_fine_tuning_status() -> Dict[str, Any]:
    """
    Get current fine-tuning system status
    
    Returns:
        Status dictionary with availability and configuration info
    """
    status = {
        'available': False,
        'config_loaded': False,
        'mlx_available': False,
        'error': None
    }
    
    try:
        from fine_tuning_config import FineTuningConfig
        config = FineTuningConfig.load_from_config()
        status['config_loaded'] = True
        
        # Check MLX availability
        try:
            from scripts.mlx_finetuning import MLXFineTuner
            fine_tuner = MLXFineTuner(config)
            status['mlx_available'] = True  # Fixed: Should be True if no exception
        except ImportError as e:
            # Legitimate opt-out: MLX not available
            status['error'] = f"MLX not available: {e}"
        except RuntimeError as e:
            if "MLX not available" in str(e):
                # Legitimate opt-out: MLX unavailable on this platform
                status['error'] = f"MLX not available: {e}"
            else:
                # Other runtime errors should fail fast
                logger.error(f"Critical MLX runtime error: {e}", exc_info=True)
                raise
        except (OSError, PermissionError) as e:
            # Fail fast on system errors
            logger.error(f"Critical system error initializing MLX: {e}", exc_info=True)
            raise
        except Exception as e:
            # Fail fast on other serious errors (configuration, model corruption, etc.)
            logger.error(f"Critical MLX initialization error: {e}", exc_info=True)
            raise
        
        if status['config_loaded'] and status['mlx_available']:
            status['available'] = True
            
    except ImportError as e:
        # Legitimate opt-out: Configuration module not available
        status['error'] = f"Configuration not available: {e}"
    except (OSError, PermissionError) as e:
        # Fail fast on system errors
        logger.error(f"Critical system error loading config: {e}", exc_info=True)
        raise
    except Exception as e:
        # Fail fast on serious configuration errors (corrupted YAML, etc.)
        logger.error(f"Critical configuration error: {e}", exc_info=True)
        raise
    
    return status

# Convenience function for direct integration
def integrate_fine_tuning_if_available(train_file: Path, train_data: List[Dict], summary: Dict[str, Any], skip_fine_tuning: bool = False, upload_model: bool = True) -> Dict[str, Any]:
    """
    Convenience function to integrate fine-tuning if available
    
    This function checks availability first and only runs fine-tuning if everything is ready.
    Used for daemon integration where we want graceful fallback behavior.
    
    Args:
        train_file: Training dataset file path
        train_data: Training data for metadata  
        summary: Analysis summary to update
        skip_fine_tuning: CLI flag to skip fine-tuning (opt-out, default False)
        upload_model: Upload model to HuggingFace (default True, disabled by --skip-model-upload)
        
    Returns:
        Updated summary with fine-tuning status
    """
    if not train_file.exists():
        logger.warning(f"Training file not found: {train_file}")
        summary['fine_tuning'] = {'status': 'skipped', 'reason': 'Training file not found'}
        return summary
    
    if not train_data:
        logger.warning("No training data available for fine-tuning")
        summary['fine_tuning'] = {'status': 'skipped', 'reason': 'No training data'}
        return summary
    
    # Check if fine-tuning is available before attempting
    status = get_fine_tuning_status()
    if not status['available']:
        print(f"⚠️  Fine-tuning not available: {status.get('error', 'Unknown error')}")
        summary['fine_tuning'] = {'status': 'skipped', 'reason': status.get('error', 'Not available')}
        return summary
    
    # Everything looks good, run fine-tuning
    return run_fine_tuning_phase(train_file, train_data, summary, skip_fine_tuning, upload_model)

if __name__ == "__main__":
    # Test the integration functions
    print("🧪 Testing fine-tuning integration...")
    
    status = get_fine_tuning_status()
    print(f"Fine-tuning status: {status}")
    
    if status['available']:
        print("✅ Fine-tuning is available and ready to use")
    else:
        print(f"⚠️  Fine-tuning not available: {status.get('error', 'Unknown')}")