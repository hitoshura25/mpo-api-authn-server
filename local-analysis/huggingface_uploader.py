#!/usr/bin/env python3
"""
HuggingFace Hub Integration for Security Analysis Results

✅ VALIDATED: Based on HuggingFace Hub official documentation
- huggingface_hub.upload_folder() API syntax validated
- Repository creation and management confirmed
- Authentication methods verified

This script uploads OLMo security analysis results to HuggingFace Hub for
open source sharing and research collaboration.

Features:
- Automatic dataset creation and organization
- Metadata generation with analysis details
- Progress tracking and error handling
- Support for both public and private repositories
- Incremental uploads with version tracking

Usage:
    python3 huggingface_uploader.py --analysis-dir /path/to/analysis --repo-name webauthn-security-analysis
    python3 huggingface_uploader.py --analysis-dir /path/to/analysis --organization your-org --private
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check for HuggingFace Hub dependencies
try:
    from huggingface_hub import HfApi, create_repo, upload_folder, login
    from huggingface_hub.utils import RepositoryNotFoundError
    HF_AVAILABLE = True
except ImportError:
    logger.error("❌ HuggingFace Hub not available")
    logger.error("Install with: pip install huggingface_hub datasets")
    HF_AVAILABLE = False


class HuggingFaceUploader:
    """Uploads security analysis results to HuggingFace Hub."""
    
    def __init__(self,
                 repo_name: str = "webauthn-security-analysis",
                 organization: Optional[str] = None,
                 private: bool = False,
                 license: str = "apache-2.0"):
        
        if not HF_AVAILABLE:
            raise RuntimeError("HuggingFace Hub dependencies not available")
        
        self.repo_name = repo_name
        self.organization = organization
        self.private = private
        self.license = license
        self.api = HfApi()
        
        # Construct full repository ID
        if organization:
            self.repo_id = f"{organization}/{repo_name}"
        else:
            # Get current user to construct full repo ID
            try:
                user_info = self.api.whoami()
                username = user_info["name"]
                self.repo_id = f"{username}/{repo_name}"
            except Exception as e:
                logger.error(f"❌ Failed to get username: {e}")
                raise
        
        logger.info(f"Initialized HuggingFace uploader for repo: {self.repo_id}")
        logger.info(f"Private: {private}, License: {license}")
    
    def check_authentication(self) -> bool:
        """Check if user is authenticated with HuggingFace Hub."""
        try:
            user_info = self.api.whoami()
            logger.info(f"✅ Authenticated as: {user_info['name']}")
            return True
        except Exception as e:
            logger.error(f"❌ Not authenticated with HuggingFace Hub: {e}")
            logger.error("Run: huggingface-cli login")
            return False
    
    def create_or_get_repo(self) -> bool:
        """Create repository if it doesn't exist."""
        try:
            # Check if repo exists
            repo_info = self.api.repo_info(self.repo_id, repo_type="dataset")
            logger.info(f"✅ Repository exists: {self.repo_id}")
            return True
            
        except RepositoryNotFoundError:
            logger.info(f"Repository does not exist, creating: {self.repo_id}")
            
            try:
                # ✅ VALIDATED: create_repo API syntax from HuggingFace docs
                create_repo(
                    repo_id=self.repo_id,
                    repo_type="dataset",
                    private=self.private,
                    exist_ok=True
                )
                logger.info(f"✅ Repository created: {self.repo_id}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to create repository: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking repository: {e}")
            return False
    
    def prepare_upload_directory(self, analysis_dir: Path) -> Path:
        """Prepare analysis results for upload."""
        upload_dir = analysis_dir / "huggingface_upload"
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        upload_dir.mkdir(exist_ok=True)
        
        logger.info(f"📁 Preparing upload directory: {upload_dir}")
        
        # Copy analysis results
        results_dir = upload_dir / "analysis_results"
        results_dir.mkdir(exist_ok=True)
        
        # Find all analysis result files
        result_files = []
        for pattern in ["*olmo_analysis_*.json", "*summary_*.json"]:
            result_files.extend(analysis_dir.glob(pattern))
        
        logger.info(f"Found {len(result_files)} analysis files to upload")
        
        for result_file in result_files:
            dest_file = results_dir / result_file.name
            shutil.copy2(result_file, dest_file)
            logger.info(f"  Copied: {result_file.name}")
        
        # Generate dataset metadata
        self._generate_dataset_card(upload_dir, result_files)
        self._generate_dataset_metadata(upload_dir, result_files)
        
        return upload_dir
    
    def _generate_dataset_card(self, upload_dir: Path, result_files: List[Path]):
        """Generate README.md for the dataset."""
        readme_content = f"""# WebAuthn Security Analysis Dataset
        
## Overview

This dataset contains security analysis results from a real-world WebAuthn authentication server, analyzed using the OLMo-2-1B language model with specialized security prompting.

## Dataset Description

- **Source**: Production WebAuthn server security scans
- **Analysis Model**: OLMo-2-1B with 4096 token context length
- **Security Tools**: 8 FOSS security tools (Trivy, Semgrep, Checkov, GitLeaks, OSV-Scanner, OWASP ZAP, Dependabot, SARIF)
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
- **License**: {self.license}

## Contents

- `analysis_results/`: Detailed OLMo analysis results in JSON format
- `metadata.json`: Dataset metadata and statistics

## Files

"""
        
        for result_file in result_files:
            file_size = result_file.stat().st_size / 1024  # KB
            readme_content += f"- `analysis_results/{result_file.name}`: {file_size:.1f} KB\\n"
        
        readme_content += f"""
## Usage

This dataset is designed for:
- Security vulnerability analysis research
- AI/ML model training for cybersecurity
- Benchmarking security analysis capabilities
- Educational purposes in security research

## Citation

If you use this dataset in your research, please cite:

```
@dataset{{webauthn_security_analysis,
  title={{WebAuthn Security Analysis Dataset}},
  author={{Generated by OLMo-2-1B}},
  year={{{datetime.now().year}}},
  publisher={{HuggingFace Hub}},
  howpublished={{\\url{{https://huggingface.co/datasets/{self.repo_id}}}}}
}}
```

## Methodology

The analysis was performed using:
1. **Security Scanning**: Comprehensive scanning with 8 FOSS tools
2. **Vulnerability Extraction**: Automated parsing of security scan results
3. **AI Analysis**: OLMo-2-1B model with specialized security prompting
4. **Quality Assurance**: Batch processing with error handling and validation

## Model Information

- **Model**: OLMo-2-1B (Allen Institute for AI)
- **Context Length**: 4096 tokens (2X larger than OLMo-1B)
- **Architecture**: RMSNorm + SwiGLU + rotary embeddings
- **Optimization**: MLX framework for Apple Silicon (3-4X faster inference)
- **Domain**: Security vulnerability analysis and remediation
"""
        
        readme_path = upload_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        logger.info(f"Generated README.md ({len(readme_content)} chars)")
    
    def _generate_dataset_metadata(self, upload_dir: Path, result_files: List[Path]):
        """Generate dataset metadata."""
        metadata = {
            "dataset_info": {
                "name": self.repo_name,
                "description": "WebAuthn Security Analysis Dataset generated by OLMo-2-1B",
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "license": self.license,
                "homepage": f"https://huggingface.co/datasets/{self.repo_id}"
            },
            "analysis_info": {
                "model_used": "OLMo-2-1B",
                "context_length": 4096,
                "architecture": "RMSNorm + SwiGLU + rotary embeddings",
                "optimization": "MLX framework for Apple Silicon",
                "security_tools": [
                    "Trivy", "Semgrep", "Checkov", "GitLeaks", 
                    "OSV-Scanner", "OWASP ZAP", "Dependabot", "SARIF"
                ]
            },
            "files": [],
            "statistics": {
                "total_files": len(result_files),
                "total_size_kb": sum(f.stat().st_size for f in result_files) / 1024
            }
        }
        
        # Add file information
        for result_file in result_files:
            file_info = {
                "filename": result_file.name,
                "size_kb": result_file.stat().st_size / 1024,
                "modified": datetime.fromtimestamp(result_file.stat().st_mtime).isoformat()
            }
            metadata["files"].append(file_info)
        
        metadata_path = upload_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Generated metadata.json with {len(result_files)} files")
    
    def upload_analysis_results(self, analysis_dir: Path) -> bool:
        """Upload analysis results to HuggingFace Hub."""
        logger.info(f"🚀 Starting upload process for: {analysis_dir}")
        
        # Check authentication
        if not self.check_authentication():
            return False
        
        # Create or get repository
        if not self.create_or_get_repo():
            return False
        
        # Prepare upload directory
        upload_dir = self.prepare_upload_directory(analysis_dir)
        
        try:
            logger.info(f"📤 Uploading to HuggingFace Hub: {self.repo_id}")
            
            # ✅ VALIDATED: upload_folder API syntax from HuggingFace docs
            upload_info = upload_folder(
                folder_path=str(upload_dir),
                repo_id=self.repo_id,
                repo_type="dataset",
                commit_message=f"Update security analysis results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                commit_description="Automated upload of OLMo-2-1B security analysis results"
            )
            
            logger.info("✅ Upload completed successfully!")
            logger.info(f"   Repository: https://huggingface.co/datasets/{self.repo_id}")
            logger.info(f"   Commit: {upload_info.oid[:8]}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return False
        finally:
            # Cleanup upload directory
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
                logger.info("Cleaned up temporary upload directory")


def main():
    """Main entry point for HuggingFace uploader."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upload OLMo security analysis results to HuggingFace Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload to personal repository
  python3 huggingface_uploader.py --analysis-dir ~/olmo-security-analysis/analysis/analysis_12345
  
  # Upload to organization repository (private)
  python3 huggingface_uploader.py \\
    --analysis-dir ~/olmo-security-analysis/analysis/analysis_12345 \\
    --organization my-org --private
  
  # Custom repository name
  python3 huggingface_uploader.py \\
    --analysis-dir ~/olmo-security-analysis/analysis/analysis_12345 \\
    --repo-name custom-security-dataset
        """
    )
    
    parser.add_argument("--analysis-dir", type=Path, required=True,
                       help="Directory containing analysis results to upload")
    parser.add_argument("--repo-name", default="webauthn-security-analysis",
                       help="HuggingFace repository name")
    parser.add_argument("--organization", 
                       help="HuggingFace organization (optional)")
    parser.add_argument("--private", action="store_true",
                       help="Create private repository")
    parser.add_argument("--license", default="apache-2.0",
                       help="Dataset license (default: apache-2.0)")
    
    args = parser.parse_args()
    
    if not HF_AVAILABLE:
        logger.error("❌ HuggingFace Hub dependencies not available")
        logger.error("Install with: pip install huggingface_hub datasets")
        return 1
    
    if not args.analysis_dir.exists():
        logger.error(f"❌ Analysis directory does not exist: {args.analysis_dir}")
        return 1
    
    try:
        # Create uploader and upload results
        uploader = HuggingFaceUploader(
            repo_name=args.repo_name,
            organization=args.organization,
            private=args.private,
            license=args.license
        )
        
        success = uploader.upload_analysis_results(args.analysis_dir)
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Upload interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())