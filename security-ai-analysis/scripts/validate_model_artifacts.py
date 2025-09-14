#!/usr/bin/env python3
"""
Model Artifact Validation System

Validates that uploaded models meet HuggingFace community standards
and contain functional artifacts rather than placeholder files.

This prevents non-functional model uploads that violate community expectations.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_model_artifacts(model_path: Path) -> Dict[str, Any]:
    """
    Validate model meets HuggingFace community standards
    
    Args:
        model_path: Path to model directory
    
    Returns:
        Dictionary with validation results and details
    """
    
    logger.info(f"🔍 Validating model artifacts at: {model_path}")
    
    validation_results = {
        'path': str(model_path),
        'overall_valid': False,
        'checks': {
            'directory_exists': False,
            'weights_valid': False,
            'tokenizer_functional': False, 
            'config_valid': False,
            'model_card_complete': False,
            'no_placeholder_files': False
        },
        'details': {},
        'errors': [],
        'warnings': []
    }
    
    try:
        # Check 1: Directory exists
        if not model_path.exists():
            validation_results['errors'].append(f"Model directory does not exist: {model_path}")
            return validation_results
            
        if not model_path.is_dir():
            validation_results['errors'].append(f"Model path is not a directory: {model_path}")
            return validation_results
            
        validation_results['checks']['directory_exists'] = True
        logger.info("✅ Model directory exists")
        
        # Check 2: Validate weights files
        weights_result = _validate_model_weights(model_path)
        validation_results['checks']['weights_valid'] = weights_result['valid']
        validation_results['details']['weights'] = weights_result
        
        # Check 3: Validate tokenizer files
        tokenizer_result = _validate_tokenizer_files(model_path)
        validation_results['checks']['tokenizer_functional'] = tokenizer_result['valid']
        validation_results['details']['tokenizer'] = tokenizer_result
        
        # Check 4: Validate configuration files
        config_result = _validate_config_files(model_path)
        validation_results['checks']['config_valid'] = config_result['valid']
        validation_results['details']['config'] = config_result
        
        # Check 5: Validate model card
        model_card_result = _validate_model_card(model_path)
        validation_results['checks']['model_card_complete'] = model_card_result['valid']
        validation_results['details']['model_card'] = model_card_result
        
        # Check 6: Check for placeholder files (critical)
        placeholder_result = _check_placeholder_files(model_path)
        validation_results['checks']['no_placeholder_files'] = placeholder_result['valid']
        validation_results['details']['placeholder_check'] = placeholder_result
        
        # Overall validation
        all_checks_passed = all(validation_results['checks'].values())
        validation_results['overall_valid'] = all_checks_passed
        
        # Collect errors and warnings
        for check_name, check_result in validation_results['details'].items():
            if 'errors' in check_result:
                validation_results['errors'].extend(check_result['errors'])
            if 'warnings' in check_result:
                validation_results['warnings'].extend(check_result['warnings'])
        
        if validation_results['overall_valid']:
            logger.info("✅ All model artifact validations passed")
        else:
            failed_checks = [k for k, v in validation_results['checks'].items() if not v]
            logger.error(f"❌ Model validation failed. Failed checks: {failed_checks}")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"❌ Model validation error: {e}")
        validation_results['errors'].append(f"Validation error: {str(e)}")
        return validation_results

def _validate_model_weights(model_path: Path) -> Dict[str, Any]:
    """Validate model weight files"""
    
    result = {
        'valid': False,
        'files_found': [],
        'errors': [],
        'warnings': []
    }
    
    # Check for weight files
    weight_files = [
        'model.safetensors',
        'pytorch_model.bin',
        'adapter_model.safetensors',  # LoRA adapter weights
        'model.pt'
    ]
    
    found_weights = []
    for weight_file in weight_files:
        file_path = model_path / weight_file
        if file_path.exists():
            found_weights.append(weight_file)
            
            # Check if it's a real weight file vs placeholder
            try:
                file_size = file_path.stat().st_size
                if file_size < 1000:  # Less than 1KB is likely placeholder
                    result['warnings'].append(f"Suspiciously small weight file: {weight_file} ({file_size} bytes)")
                else:
                    result['files_found'].append(weight_file)
                    
            except Exception as e:
                result['errors'].append(f"Could not check weight file {weight_file}: {e}")
    
    if found_weights:
        result['valid'] = True
        logger.info(f"✅ Found weight files: {', '.join(found_weights)}")
    else:
        result['errors'].append("No valid weight files found (model.safetensors, pytorch_model.bin, etc.)")
        logger.error("❌ No model weight files found")
    
    return result

def _validate_tokenizer_files(model_path: Path) -> Dict[str, Any]:
    """Validate tokenizer files"""
    
    result = {
        'valid': False,
        'files_found': [],
        'errors': [],
        'warnings': []
    }
    
    # Check for tokenizer files
    tokenizer_files = [
        'tokenizer.json',
        'tokenizer_config.json',
        'vocab.txt',
        'merges.txt',
        'special_tokens_map.json'
    ]
    
    found_tokenizer_files = []
    for tokenizer_file in tokenizer_files:
        file_path = model_path / tokenizer_file
        if file_path.exists():
            
            # Check if it's a real tokenizer file vs placeholder
            try:
                file_size = file_path.stat().st_size
                if file_size < 100:  # Less than 100 bytes is likely placeholder
                    result['warnings'].append(f"Suspiciously small tokenizer file: {tokenizer_file} ({file_size} bytes)")
                else:
                    found_tokenizer_files.append(tokenizer_file)
                    
            except Exception as e:
                result['errors'].append(f"Could not check tokenizer file {tokenizer_file}: {e}")
    
    if found_tokenizer_files:
        result['valid'] = True
        result['files_found'] = found_tokenizer_files
        logger.info(f"✅ Found tokenizer files: {', '.join(found_tokenizer_files)}")
    else:
        result['errors'].append("No valid tokenizer files found")
        logger.error("❌ No tokenizer files found")
    
    return result

def _validate_config_files(model_path: Path) -> Dict[str, Any]:
    """Validate configuration files"""
    
    result = {
        'valid': False,
        'files_found': [],
        'errors': [],
        'warnings': []
    }
    
    # Check for config files
    config_files = [
        'config.json',
        'generation_config.json',
        'adapter_config.json'
    ]
    
    found_config_files = []
    for config_file in config_files:
        file_path = model_path / config_file
        if file_path.exists():
            
            try:
                # Validate it's actual JSON
                with open(file_path, 'r') as f:
                    config_data = json.load(f)
                    
                # Check if it's meaningful content vs placeholder
                if isinstance(config_data, dict) and len(config_data) > 0:
                    found_config_files.append(config_file)
                else:
                    result['warnings'].append(f"Config file appears empty or invalid: {config_file}")
                    
            except json.JSONDecodeError:
                result['warnings'].append(f"Config file not valid JSON: {config_file}")
            except Exception as e:
                result['errors'].append(f"Could not validate config file {config_file}: {e}")
    
    if found_config_files:
        result['valid'] = True
        result['files_found'] = found_config_files
        logger.info(f"✅ Found config files: {', '.join(found_config_files)}")
    else:
        result['errors'].append("No valid configuration files found")
        logger.error("❌ No valid configuration files found")
    
    return result

def _validate_model_card(model_path: Path) -> Dict[str, Any]:
    """Validate model card (README.md)"""
    
    result = {
        'valid': False,
        'content_length': 0,
        'errors': [],
        'warnings': []
    }
    
    readme_path = model_path / "README.md"
    
    if not readme_path.exists():
        result['errors'].append("No README.md model card found")
        logger.error("❌ No model card (README.md) found")
        return result
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        result['content_length'] = len(content)
        
        # Basic content validation
        if len(content) < 200:
            result['warnings'].append("Model card is very short (< 200 characters)")
        
        # Check for essential sections
        essential_sections = ['Model Details', 'Usage', 'Training', 'Performance']
        missing_sections = []
        
        for section in essential_sections:
            if section.lower() not in content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            result['warnings'].append(f"Model card missing recommended sections: {', '.join(missing_sections)}")
        
        result['valid'] = True
        logger.info(f"✅ Model card found ({len(content)} characters)")
        
    except Exception as e:
        result['errors'].append(f"Could not read model card: {e}")
        logger.error(f"❌ Could not validate model card: {e}")
    
    return result

def _check_placeholder_files(model_path: Path) -> Dict[str, Any]:
    """Check for placeholder files (critical for community standards)"""
    
    result = {
        'valid': True,
        'placeholder_files': [],
        'errors': [],
        'warnings': []
    }
    
    # Check all files in model directory
    try:
        for file_path in model_path.rglob('*'):
            if file_path.is_file():
                
                # Check if file contains placeholder content
                try:
                    # Only check text-readable files
                    if file_path.suffix in ['.json', '.txt', '.md', '.py', '.yaml', '.yml']:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        # Look for actual placeholder file indicators (more specific)
                        # Exclude legitimate vocabulary tokens containing "placeholder"
                        placeholder_indicators = [
                            '# Placeholder for',
                            'Generated by MLX fine-tuning process', 
                            '# This is a placeholder',
                            'placeholder file',
                            'placeholder content',
                            'TODO: replace this placeholder'
                        ]
                        
                        # Skip tokenizer files that legitimately contain "placeholder" as vocab tokens
                        if file_path.name in ['tokenizer.json', 'vocab.json', 'merges.txt']:
                            # Only check for explicit placeholder comments, not vocab entries
                            explicit_placeholder_indicators = [
                                '# Placeholder for',
                                'Generated by MLX fine-tuning process',
                                '# This is a placeholder', 
                                'TODO: replace this placeholder',
                                '/* placeholder */'
                            ]
                            for indicator in explicit_placeholder_indicators:
                                if indicator.lower() in content.lower():
                                    result['placeholder_files'].append(str(file_path.relative_to(model_path)))
                                    break
                        else:
                            # For non-tokenizer files, use broader placeholder detection
                            for indicator in placeholder_indicators:
                                if indicator.lower() in content.lower():
                                    result['placeholder_files'].append(str(file_path.relative_to(model_path)))
                                    break
                                
                except Exception:
                    # Skip files that can't be read as text
                    continue
    
    except Exception as e:
        result['errors'].append(f"Error checking for placeholder files: {e}")
    
    if result['placeholder_files']:
        result['valid'] = False
        result['errors'].append(f"Found placeholder files: {', '.join(result['placeholder_files'])}")
        logger.error(f"❌ Found {len(result['placeholder_files'])} placeholder files")
    else:
        logger.info("✅ No placeholder files detected")
    
    return result

def main():
    """CLI interface for model validation"""
    
    if len(sys.argv) != 2:
        print("Usage: python validate_model_artifacts.py <model_directory>")
        sys.exit(1)
    
    model_path = Path(sys.argv[1])
    
    print("=" * 60)
    print("🔍 Model Artifact Validation")
    print("=" * 60)
    
    results = validate_model_artifacts(model_path)
    
    # Print summary
    print("\n📋 Validation Summary:")
    print(f"Model Path: {results['path']}")
    print(f"Overall Valid: {'✅ Yes' if results['overall_valid'] else '❌ No'}")
    
    print("\n📊 Individual Checks:")
    for check_name, passed in results['checks'].items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name.replace('_', ' ').title()}")
    
    if results['errors']:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  • {error}")
    
    if results['warnings']:
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  • {warning}")
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_valid'] else 1)

if __name__ == "__main__":
    main()