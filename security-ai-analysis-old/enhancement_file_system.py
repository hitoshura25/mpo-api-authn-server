#!/usr/bin/env python3
"""
AI Security Enhancement File System Management

This module provides file system validation and directory management
for the AI Security Model Enhancement implementation.

Functions:
- ensure_enhanced_directories(): Create enhanced directory structure
- validate_file_system_paths(): Validate base system components  
- validate_all_implementation_paths(): Comprehensive validation
- update_gitignore_patterns(): Add enhanced directories to .gitignore

Usage:
    from enhancement_file_system import validate_all_implementation_paths
    validation_results, success = validate_all_implementation_paths()
"""

import sys
from pathlib import Path
from typing import Dict, Tuple, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from config_manager import OLMoSecurityConfig
except ImportError:
    print("❌ Could not import config_manager. Ensure you're running from security-ai-analysis directory.")
    sys.exit(1)


def ensure_enhanced_directories() -> List[str]:
    """
    Create and validate enhanced directory structure for AI security enhancements.
    
    Returns:
        List of created directory paths
    """
    config = OLMoSecurityConfig()
    base_dir = Path(__file__).parent  # security-ai-analysis directory
    
    required_dirs = [
        base_dir / "enhanced_datasets" / "code-aware-training",
        base_dir / "enhanced_datasets" / "validation", 
        base_dir / "knowledge_base" / "code_examples",
        base_dir / "knowledge_base" / "embeddings",
        base_dir / "quality_assessment" / "validation_reports",
        base_dir / "quality_assessment" / "syntax_checks",
        base_dir / "quality_assessment" / "improvement_tracking"
    ]
    
    created_dirs = []
    for dir_path in required_dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(dir_path))
    
    if created_dirs:
        print(f"✅ Created {len(created_dirs)} enhanced directories:")
        for dir_path in created_dirs:
            print(f"   📁 {dir_path}")
    else:
        print("✅ All enhanced directories already exist")
    
    return created_dirs


def validate_file_system_paths() -> bool:
    """
    Validate all expected file system paths exist and are accessible.
    
    Returns:
        True if validation passes, False otherwise
    """
    try:
        config = OLMoSecurityConfig()
        
        # Validate shared models directory
        shared_models = config.base_models_dir
        if not shared_models.exists():
            print(f"❌ CRITICAL: Shared models directory not found: {shared_models}")
            print("🔍 Shared models directory missing indicates incomplete setup or infrastructure issues requiring investigation")
            raise RuntimeError(f"Shared models directory missing - setup incomplete, requires investigation: {shared_models}")
        
        # Validate fine-tuned models directory  
        fine_tuned_dir = shared_models.parent / "fine-tuned"
        if not fine_tuned_dir.exists():
            fine_tuned_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created fine-tuned models directory: {fine_tuned_dir}")
        
        # Validate base model exists
        try:
            base_model_path = config.get_base_model_path()
            if not Path(base_model_path).exists():
                print(f"❌ CRITICAL: Base model not found: {base_model_path}")
                print("🔍 Base model missing indicates incomplete setup or infrastructure issues requiring investigation")
                raise RuntimeError(f"Base model missing - setup incomplete, requires investigation: {base_model_path}")
        except FileNotFoundError as e:
            print("❌ CRITICAL: Base model path could not be determined")
            print("🔍 Base model path determination failure indicates configuration corruption or setup issues requiring investigation")
            raise RuntimeError(f"Base model path determination failed - configuration issue requires investigation: {e}") from e
        
        # Ensure enhanced directories exist
        ensure_enhanced_directories()
        
        print("✅ File system validation passed")
        return True
        
    except Exception as e:
        # Fail fast on configuration corruption or infrastructure issues
        print(f"❌ CRITICAL: File system validation failed: {e}")
        print("🔍 Configuration corruption or infrastructure issue - check file permissions, disk space, and configuration integrity")
        raise RuntimeError(f"File system validation failed - infrastructure issue requires investigation: {e}") from e


def validate_all_implementation_paths() -> Tuple[Dict, bool]:
    """
    Validate all file system paths assumed in the implementation plan.
    
    Returns:
        Tuple of (validation_results_dict, overall_success_boolean)
    """
    try:
        config = OLMoSecurityConfig()
        validation_results = {}
        
        print("🔍 Starting comprehensive file system validation...")
        
        # 1. Configuration files
        project_root = Path(__file__).parent.parent  # Get project root relative to current file
        config_file = project_root / "config" / "olmo-security-config.yaml"
        validation_results['config_file'] = config_file.exists()
        
        # 2. Existing source files that need modification
        source_files = [
            Path(__file__).parent / "process_artifacts.py",
            Path(__file__).parent / "analysis" / "olmo_analyzer.py",
            Path(__file__).parent / "scripts" / "mlx_finetuning.py",
            Path(__file__).parent / "config_manager.py",
            Path(__file__).parent / "setup.py"
        ]
        
        for file_path in source_files:
            validation_results[f'source_{file_path.name}'] = file_path.exists()
        
        # 3. Shared models directory structure
        shared_models = config.base_models_dir
        validation_results['shared_models_base'] = shared_models.exists()
        validation_results['shared_models_fine_tuned'] = (shared_models.parent / "fine-tuned").exists()
        
        # 4. Base model availability
        try:
            base_model_path = config.get_base_model_path()
            validation_results['base_model'] = Path(base_model_path).exists()
            validation_results['base_model_path'] = str(base_model_path)
        except FileNotFoundError:
            validation_results['base_model'] = False
            validation_results['base_model_path'] = "Not found"
        
        # 5. Fine-tuned models
        fine_tuned_dir = shared_models.parent / "fine-tuned"
        if fine_tuned_dir.exists():
            fine_tuned_models = [d for d in fine_tuned_dir.iterdir() 
                               if d.is_dir() and "webauthn-security" in d.name]
            validation_results['fine_tuned_models_count'] = len(fine_tuned_models)
            if fine_tuned_models:
                latest_model = max(fine_tuned_models, key=lambda x: x.stat().st_mtime)
                validation_results['latest_fine_tuned'] = latest_model.name
            else:
                validation_results['latest_fine_tuned'] = None
        else:
            validation_results['fine_tuned_models_count'] = 0
            validation_results['latest_fine_tuned'] = None
        
        # 6. Required Python packages (simulate import checks)
        required_packages = [
            'mlx_lm', 'transformers', 'datasets', 'sentence_transformers', 
            'faiss', 'tree_sitter', 'numpy', 'scipy'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))  # Handle package name variations
                validation_results[f'package_{package}'] = True
            except ImportError:
                validation_results[f'package_{package}'] = False
        
        # Print validation report
        print("\n📋 File System Validation Report:")
        print("=" * 50)
        
        failed_validations = []
        for key, value in validation_results.items():
            status = "✅" if value else "❌"
            print(f"{status} {key}: {value}")
            
            # Count failures (but allow latest_fine_tuned to be None)
            if not value and key != 'latest_fine_tuned':
                failed_validations.append(key)
        
        print("=" * 50)
        
        if failed_validations:
            print(f"❌ CRITICAL: {len(failed_validations)} validation(s) failed:")
            for failed in failed_validations:
                print(f"   • {failed}")
            print("🔍 Validation failures indicate incomplete setup or dependency issues requiring investigation")

            missing_packages = [k.replace('package_', '') for k in failed_validations if k.startswith('package_')]
            error_details = f"{len(failed_validations)} validation failures: {', '.join(failed_validations[:5])}"
            if missing_packages:
                error_details += f" (missing packages: {', '.join(missing_packages)})"

            raise RuntimeError(f"System validation failed - setup incomplete, requires investigation: {error_details}")
        else:
            print("🎉 All validations passed! System ready for enhancement implementation.")

        return validation_results, True  # Only reached if validations pass
        
    except Exception as e:
        # Fail fast on configuration corruption or infrastructure issues
        print(f"❌ CRITICAL: Implementation path validation failed: {e}")
        print("🔍 Configuration corruption or infrastructure issue - check file permissions, disk space, and system configuration")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Implementation path validation failed - infrastructure issue requires investigation: {e}") from e


def update_gitignore_patterns() -> bool:
    """
    Update .gitignore with patterns for enhanced directories.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Find project root .gitignore
        project_root = Path(__file__).parent.parent
        gitignore_path = project_root / ".gitignore"
        
        if not gitignore_path.exists():
            print(f"❌ CRITICAL: .gitignore not found at: {gitignore_path}")
            print("🔍 .gitignore missing indicates repository structure issues or incomplete project setup requiring investigation")
            raise RuntimeError(f".gitignore missing - repository structure issue requires investigation: {gitignore_path}")
        
        # Read current .gitignore content
        with open(gitignore_path, 'r') as f:
            current_content = f.read()
        
        # Enhanced directories patterns to add
        enhanced_patterns = [
            "# Enhanced AI Analysis generated files",
            "security-ai-analysis/enhanced_datasets/",
            "security-ai-analysis/knowledge_base/",
            "security-ai-analysis/quality_assessment/",
            "",
            "# Training artifacts and temporary files",
            "security-ai-analysis/fine-tuning/",
            "security-ai-analysis/**/*.log",
            "security-ai-analysis/**/training_*",
            "security-ai-analysis/**/validation_*", 
            "security-ai-analysis/**/.cache/"
        ]
        
        # Check if patterns are already present
        patterns_to_add = []
        for pattern in enhanced_patterns:
            if pattern not in current_content:
                patterns_to_add.append(pattern)
        
        if not patterns_to_add:
            print("✅ All enhanced .gitignore patterns already present")
            return True
        
        # Add new patterns to .gitignore
        with open(gitignore_path, 'a') as f:
            f.write("\n\n")
            f.write("\n".join(patterns_to_add))
        
        print(f"✅ Added {len(patterns_to_add)} new .gitignore patterns")
        for pattern in patterns_to_add:
            if pattern and not pattern.startswith("#"):
                print(f"   📁 {pattern}")
        
        return True
        
    except Exception as e:
        # Fail fast on file system issues
        print(f"❌ CRITICAL: Failed to update .gitignore: {e}")
        print("🔍 File system issue - check file permissions, disk space, and repository access")
        raise RuntimeError(f"Gitignore update failed - infrastructure issue requires investigation: {e}") from e


def main():
    """
    Main function for testing file system validation.
    """
    print("🚀 AI Security Enhancement File System Validation")
    print("=" * 60)
    
    # Run comprehensive validation
    validation_results, success = validate_all_implementation_paths()
    
    print("\n🎯 Running .gitignore update...")
    update_gitignore_patterns()

    print("\n🎉 File system setup completed successfully!")
    print("💡 System ready for AI security enhancement implementation")

    return True


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except RuntimeError as e:
        print(f"\n❌ CRITICAL: File system setup failed: {e}")
        sys.exit(1)