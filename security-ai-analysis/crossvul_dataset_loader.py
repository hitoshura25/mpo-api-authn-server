#!/usr/bin/env python3
"""
CrossVul Dataset Loader for Sequential Fine-Tuning

Extracts multi-language vulnerability pairs from CrossVul dataset:
- Source: https://zenodo.org/records/4734050
- Structure: bad/good file pairs organized by CWE and language
- Coverage: 13,067 pairs across 173 CWE categories, 48+ languages
- Output: Chat-formatted training data for MLX fine-tuning

Usage:
    # Basic extraction (all languages) - dataset auto-downloads if needed
    python crossvul_dataset_loader.py \\
        --output-dir crossvul_output

    # Filter by specific languages
    python crossvul_dataset_loader.py \\
        --output-dir crossvul_output \\
        --languages java python javascript go

    # Upload to HuggingFace after extraction
    python crossvul_dataset_loader.py \\
        --output-dir crossvul_output \\
        --upload-to-hf username/crossvul-security-fixes

Note: Dataset automatically downloads to output_dir/dataset_final_sorted if not present.

Dataset Structure:
    dataset_final_sorted/
    ├── CWE-{ID}/           # Organized by vulnerability type
    │   ├── c/              # Language-specific subdirectories
    │   │   ├── bad_123_0   # Vulnerable code
    │   │   ├── good_123_0  # Patched code
    │   │   └── ...
    │   ├── java/
    │   ├── py/
    │   └── ...
"""

import logging
import json
import argparse
import os
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
import pandas as pd
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# NOTE: CrossVul files have NO extensions!
# Language is detected from directory name (e.g., CWE-79/java/bad_1163_0)
# See detect_language_from_directory() for language mapping

# Initialize CWE database (uses local vendored data from cwe2 library)
try:
    from cwe2.database import Database
    CWE_DATABASE = Database()
    logging.info("✅ CWE database loaded successfully")
except ImportError:
    logging.error(
        "❌ Missing required package 'cwe2'. Install with:\n"
        "   pip install cwe2\n"
        "   or: pip install -r requirements.txt"
    )
    raise


class SkipReason(Enum):
    """Reasons why a vulnerability pair was skipped during extraction."""
    UNREADABLE_VULNERABLE = "unreadable_vulnerable_file"
    UNREADABLE_FIXED = "unreadable_fixed_file"
    IDENTICAL_FILES = "identical_files"
    FILES_TOO_SHORT = "files_too_short"
    FILE_TOO_LARGE = "file_too_large"


def download_with_progress(url: str, output_path: Path, timeout: int = 3600) -> bool:
    """
    Download file from URL with progress bar and resume capability.

    Args:
        url: URL to download from
        output_path: Path where file will be saved
        timeout: Timeout in seconds for download operation

    Returns:
        True if download successful, False otherwise
    """
    try:
        import requests
        from tqdm import tqdm
    except ImportError:
        raise ImportError(
            "Missing required packages. Install with:\n"
            "pip install requests tqdm"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if partial download exists
    resume_byte_pos = 0
    if output_path.exists():
        resume_byte_pos = output_path.stat().st_size
        logging.info(f"📥 Resuming download from {resume_byte_pos / (1024**2):.1f} MB...")

    # Set up headers for resume
    headers = {}
    if resume_byte_pos > 0:
        headers['Range'] = f'bytes={resume_byte_pos}-'

    try:
        # Make request with stream=True for chunk download
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)
        response.raise_for_status()

        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        if resume_byte_pos > 0:
            total_size += resume_byte_pos

        # Open file in append mode if resuming, write mode otherwise
        mode = 'ab' if resume_byte_pos > 0 else 'wb'

        # Download with progress bar
        with open(output_path, mode) as f:
            with tqdm(
                total=total_size,
                initial=resume_byte_pos,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=output_path.name
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        logging.info(f"✅ Download completed: {output_path}")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Download failed: {e}")
        raise


def extract_zip_with_progress(zip_path: Path, extract_to: Path, keep_zip: bool = False) -> bool:
    """
    Extract ZIP file with progress bar.

    Args:
        zip_path: Path to ZIP file
        extract_to: Directory to extract to
        keep_zip: Keep ZIP file after extraction (default: delete)

    Returns:
        True if extraction successful, False otherwise
    """
    try:
        from tqdm import tqdm
    except ImportError:
        raise ImportError(
            "Missing required package. Install with:\n"
            "pip install tqdm"
        )

    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    logging.info(f"📦 Extracting {zip_path.name} to {extract_to}...")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of files in archive
            file_list = zip_ref.namelist()
            total_files = len(file_list)

            # Extract with progress bar
            with tqdm(total=total_files, desc="Extracting", unit="files") as pbar:
                for file in file_list:
                    zip_ref.extract(file, extract_to)
                    pbar.update(1)

        logging.info(f"✅ Extraction completed: {extract_to}")

        # Delete ZIP file if requested
        if not keep_zip:
            zip_size_mb = zip_path.stat().st_size / (1024**2)
            logging.info(f"🧹 Deleting ZIP file to save space: {zip_path}")
            zip_path.unlink()
            logging.info(f"✅ Deleted {zip_path.name} ({zip_size_mb:.1f} MB saved)")

        return True

    except zipfile.BadZipFile as e:
        logging.error(f"❌ Invalid ZIP file: {e}")
        raise
    except Exception as e:
        logging.error(f"❌ Extraction failed: {e}")
        raise


def ensure_crossvul_dataset_available(dataset_dir: Path, keep_zip: bool = False) -> Path:
    """
    Ensure CrossVul dataset is available, downloading from Zenodo if needed.

    This function:
    1. Checks if dataset already exists (dataset_final_sorted directory)
    2. If not found, downloads CrossVul from Zenodo (~367 MB)
    3. Extracts the ZIP file (~1.4 GB uncompressed)
    4. Optionally deletes ZIP to save space (default behavior)

    Args:
        dataset_dir: Base directory for dataset (e.g., data/public_datasets)
        keep_zip: Keep ZIP file after extraction (default: delete to save space)

    Returns:
        Path to extracted dataset_final_sorted directory

    Raises:
        Exception: If download or extraction fails
    """
    dataset_dir = Path(dataset_dir)
    dataset_final_sorted = dataset_dir / "dataset_final_sorted"

    # Check if dataset already exists
    if dataset_final_sorted.exists() and any(dataset_final_sorted.iterdir()):
        logging.info(f"✅ CrossVul dataset already exists: {dataset_final_sorted}")
        return dataset_final_sorted

    # Dataset not found, download from Zenodo
    logging.info("📥 CrossVul dataset not found locally. Downloading from Zenodo...")
    logging.info("   Source: https://zenodo.org/records/4734050")
    logging.info("   Version: CrossVul dataset")
    logging.info("   Size: 367 MB compressed → ~1.4 GB extracted")
    logging.info("   MD5: aa95465e9dc98ce222ab2f3aa7af5997")
    logging.info("   ⚠️  This is a one-time download and may take 5-15 minutes depending on connection speed.")

    # Zenodo download URL (direct download link)
    zenodo_url = "https://zenodo.org/records/4734050/files/dataset.zip?download=1"
    zip_path = dataset_dir / "crossvul_dataset.zip"

    try:
        # Download ZIP file
        logging.info(f"📥 Downloading CrossVul dataset from Zenodo...")
        download_with_progress(zenodo_url, zip_path, timeout=3600)  # 1 hour timeout

        # Extract ZIP file
        extract_zip_with_progress(zip_path, dataset_dir, keep_zip=keep_zip)

        # Verify extraction
        if not dataset_final_sorted.exists():
            raise FileNotFoundError(
                f"Extraction completed but dataset directory not found: {dataset_final_sorted}\n"
                f"Expected structure: {dataset_final_sorted}/CWE-*/language/"
            )

        logging.info(f"✅ CrossVul dataset ready: {dataset_final_sorted}")
        return dataset_final_sorted

    except Exception as e:
        # Cleanup on failure
        logging.error(f"❌ Failed to download/extract CrossVul dataset: {e}")
        if zip_path.exists():
            logging.info(f"🧹 Cleaning up partial download: {zip_path}")
            zip_path.unlink()
        raise


def detect_language_from_directory(file_path: Path) -> Optional[str]:
    """
    Detect language from parent directory name.

    CrossVul files have NO extensions, so we use the directory name.
    Example: CWE-79/java/bad_1163_0 → language = "java"

    Args:
        file_path: Path to the file (e.g., .../CWE-79/java/bad_1163_0)

    Returns:
        Normalized language name (e.g., "java", "python", "javascript")
    """
    # Get parent directory name
    lang_dir = file_path.parent.name

    # Map directory names to standard language names
    DIRECTORY_TO_LANGUAGE = {
        'java': 'java',
        'py': 'python',
        'js': 'javascript',
        'go': 'go',
        'rb': 'ruby',
        'c': 'c',
        'cpp': 'cpp',
        'cc': 'cpp',
        'cxx': 'cpp',
        'cs': 'csharp',
        'php': 'php',
        'ts': 'typescript',
        'kt': 'kotlin',
        'rs': 'rust',
        'swift': 'swift',
        'scala': 'scala',
        'html': 'html',
        'htm': 'html',
        'css': 'css',
        'xml': 'xml',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'sh': 'shell',
        'bash': 'shell',
        'cgi': 'perl',
        'coffee': 'coffeescript',
        'as': 'actionscript',
        'inc': 'php',  # PHP includes
        'ctp': 'php',  # CakePHP template
        'jelly': 'xml',  # Jenkins Jelly
        'h': 'c',  # C headers
        # Skip 'Other' - mixed/unknown
    }

    return DIRECTORY_TO_LANGUAGE.get(lang_dir.lower())


def read_file_safe(filepath: Path, max_size_kb: int = 500) -> Optional[str]:
    """
    Read file contents safely with size limits and encoding fallbacks.

    Args:
        filepath: Path to file
        max_size_kb: Maximum file size in KB (default: 500KB)

    Returns:
        File contents as string, or None if read fails
    """
    try:
        # Check file size first
        file_size_kb = filepath.stat().st_size / 1024
        if file_size_kb > max_size_kb:
            logging.debug(f"Skipping large file: {filepath} ({file_size_kb:.1f} KB)")
            return None

        # Try UTF-8 first
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception:
                # Final fallback - read as binary and decode with errors ignored
                with open(filepath, 'rb') as f:
                    return f.read().decode('utf-8', errors='ignore')

    except Exception as e:
        logging.warning(f"Failed to read file {filepath}: {e}")
        return None


def get_cwe_description(cwe_id: str) -> Optional[str]:
    """
    Get CWE description from the cwe2 database.

    Args:
        cwe_id: CWE identifier (e.g., "CWE-79" or "79")

    Returns:
        Human-readable CWE description, or None if not found
    """
    try:
        # Extract numeric ID (handle both "CWE-79" and "79" formats)
        numeric_id = int(cwe_id.replace('CWE-', ''))

        # Query cwe2 database
        weakness = CWE_DATABASE.get(numeric_id)

        if weakness and weakness.name:
            # Format: "CWE Name - Brief Description"
            # Use extended_description if available, otherwise description
            desc = weakness.extended_description or weakness.description

            # Handle cases where description might be a tuple or list
            if isinstance(desc, (tuple, list)):
                desc = ' '.join(str(d) for d in desc if d)
            elif desc:
                desc = str(desc)

            if desc:
                # Truncate long descriptions to first sentence
                first_sentence = desc.split('.')[0].strip() + '.'
                # Limit length to avoid extremely long descriptions
                if len(first_sentence) > 200:
                    first_sentence = first_sentence[:197] + '...'
                return f"{weakness.name} - {first_sentence}"
            else:
                return weakness.name

        return None

    except (ValueError, AttributeError, TypeError) as e:
        logging.debug(f"Could not retrieve CWE description for {cwe_id}: {e}")
        return None


def find_matching_pairs(dataset_dir: Path, language_filter: Optional[Set[str]] = None) -> List[Dict]:
    """
    Find all matching bad/good file pairs in CrossVul dataset.

    Args:
        dataset_dir: Path to dataset_final_sorted directory
        language_filter: Optional set of languages to include (e.g., {'java', 'py', 'js'})

    Returns:
        List of dictionaries with pair metadata
    """
    logging.info(f"Scanning {dataset_dir} for bad/good pairs...")

    pairs = []
    cwe_dirs = sorted([d for d in dataset_dir.iterdir() if d.is_dir() and d.name.startswith('CWE-')])

    for cwe_dir in cwe_dirs:
        cwe_id = cwe_dir.name
        cwe_description = get_cwe_description(cwe_id)

        if not cwe_description:
            logging.error(f"Could not find description for {cwe_id}")
            raise ValueError(f"Invalid CWE ID: {cwe_id}")

        # Find all language subdirectories
        lang_dirs = [d for d in cwe_dir.iterdir() if d.is_dir()]

        for lang_dir in lang_dirs:
            lang_name = lang_dir.name

            # Apply language filter if specified
            if language_filter and lang_name not in language_filter:
                continue

            # Find all bad files
            bad_files = sorted([f for f in lang_dir.iterdir() if f.is_file() and f.name.startswith('bad_')])

            for bad_file in bad_files:
                # Construct corresponding good file name
                # bad_5795_5 → good_5795_5
                good_file_name = bad_file.name.replace('bad_', 'good_', 1)
                good_file = lang_dir / good_file_name

                # Verify good file exists
                if not good_file.exists():
                    logging.warning(f"Missing good pair for {bad_file}")
                    continue

                # Detect language from directory name (files have NO extensions)
                normalized_lang = detect_language_from_directory(bad_file)
                if not normalized_lang:
                    logging.debug(f"Could not detect language for {bad_file} (directory: {lang_name})")
                    continue

                pairs.append({
                    'cwe_id': cwe_id,
                    'cwe_description': cwe_description,
                    'language': normalized_lang,
                    'language_dir': lang_name,  # Original directory name
                    'bad_file': bad_file,
                    'good_file': good_file,
                    'file_id': bad_file.stem.replace('bad_', '')  # Extract numeric ID
                })

    logging.info(f"Found {len(pairs)} matching bad/good pairs")
    return pairs


def create_raw_vulnerability_record(pair: Dict) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Create a raw vulnerability record from a bad/good file pair.

    This function creates RAW data records WITHOUT chat formatting.
    Chat message formatting should be done in process_artifacts.py.

    Args:
        pair: Dictionary with bad_file, good_file, CWE info, language

    Returns:
        Tuple of (record, skip_info):
        - record: Dictionary with raw vulnerability data (None if skipped)
        - skip_info: Dictionary with skip details (None if not skipped)
    """
    # Read vulnerable code
    vulnerable_code = read_file_safe(pair['bad_file'])
    if not vulnerable_code:
        skip_info = {
            'skip_reason': SkipReason.UNREADABLE_VULNERABLE.value,
            'cwe_id': pair['cwe_id'],
            'language': pair['language'],
            'file_pair_id': pair['file_id'],
            'bad_file': str(pair['bad_file']),
            'good_file': str(pair['good_file']),
            'details': f"Could not read vulnerable file: {pair['bad_file']}"
        }
        logging.debug(f"Skipping unreadable vulnerable file: {pair['bad_file']}")
        return (None, skip_info)

    # Read fixed code
    fixed_code = read_file_safe(pair['good_file'])
    if not fixed_code:
        skip_info = {
            'skip_reason': SkipReason.UNREADABLE_FIXED.value,
            'cwe_id': pair['cwe_id'],
            'language': pair['language'],
            'file_pair_id': pair['file_id'],
            'bad_file': str(pair['bad_file']),
            'good_file': str(pair['good_file']),
            'details': f"Could not read fixed file: {pair['good_file']}"
        }
        logging.debug(f"Skipping unreadable fixed file: {pair['good_file']}")
        return (None, skip_info)

    # Skip if files are identical (data quality issue)
    if vulnerable_code.strip() == fixed_code.strip():
        skip_info = {
            'skip_reason': SkipReason.IDENTICAL_FILES.value,
            'cwe_id': pair['cwe_id'],
            'language': pair['language'],
            'file_pair_id': pair['file_id'],
            'bad_file': str(pair['bad_file']),
            'good_file': str(pair['good_file']),
            'details': f"Vulnerable and fixed code are identical ({len(vulnerable_code)} chars)"
        }
        logging.debug(f"Skipping identical files: {pair['file_id']}")
        return (None, skip_info)

    # Skip if files are too short (likely not real vulnerability examples)
    vuln_len = len(vulnerable_code.strip())
    fixed_len = len(fixed_code.strip())
    if vuln_len < 50 or fixed_len < 50:
        skip_info = {
            'skip_reason': SkipReason.FILES_TOO_SHORT.value,
            'cwe_id': pair['cwe_id'],
            'language': pair['language'],
            'file_pair_id': pair['file_id'],
            'bad_file': str(pair['bad_file']),
            'good_file': str(pair['good_file']),
            'details': f"Files too short - Vulnerable: {vuln_len} chars, Fixed: {fixed_len} chars (minimum: 50 chars each)"
        }
        logging.debug(f"Skipping short files: {pair['file_id']}")
        return (None, skip_info)

    # Return RAW data record (no skip)
    record = {
        'cwe_id': pair['cwe_id'],
        'cwe_description': pair['cwe_description'],
        'language': pair['language'],
        'vulnerable_code': vulnerable_code,
        'fixed_code': fixed_code,
        'file_pair_id': pair['file_id'],
        'source': 'crossvul',
        'language_dir': pair['language_dir']
    }
    return (record, None)


def create_dataset_card(
    repo_id: str,
    num_examples: int,
    num_cwes: int,
    languages: List[str],
    language_distribution: Dict[str, int],
    cwe_distribution: Dict[str, int]
) -> str:
    """Generate HuggingFace dataset card for CrossVul dataset."""

    # Top 10 languages by count
    top_languages = sorted(language_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
    lang_table = "\n".join([f"| {lang} | {count:,} |" for lang, count in top_languages])

    # Top 10 CWEs by count
    top_cwes = sorted(cwe_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
    cwe_table = "\n".join([
        f"| {cwe} | {get_cwe_description(cwe) or 'Unknown'} | {count:,} |"
        for cwe, count in top_cwes
    ])

    card = f"""---
license: apache-2.0
task_categories:
- text-generation
language:
- code
size_categories:
- 10K<n<100K
tags:
- security
- vulnerability
- code-fix
- cwe
---

# CrossVul Multi-Language Security Vulnerability Dataset

Security vulnerability dataset from [CrossVul](https://zenodo.org/records/4734050) with **{num_examples:,}** before/after code pairs across **{num_cwes}** CWE categories and **{len(languages)}** programming languages.

Contains vulnerable code examples paired with their secure fixes, ideal for training AI models on security code remediation.

## Dataset Statistics

- **Total Examples**: {num_examples:,}
- **CWE Categories**: {num_cwes}
- **Languages**: {len(languages)}
- **Format**: Raw vulnerability records (JSON Lines)

### Top Languages

| Language | Examples |
|----------|----------|
{lang_table}

### Top CWE Categories

| CWE ID | Description | Examples |
|--------|-------------|----------|
{cwe_table}

## Usage

```python
from datasets import load_dataset

# Load raw vulnerability dataset
dataset = load_dataset("{repo_id}")

# Example raw record format
record = dataset['train'][0]
print(record)
# {{
#   'cwe_id': 'CWE-79',
#   'cwe_description': 'Cross-site Scripting (XSS)',
#   'language': 'java',
#   'vulnerable_code': '...',
#   'fixed_code': '...',
#   'file_pair_id': '1163_0',
#   'source': 'crossvul',
#   'language_dir': 'java'
# }}
```

## Processing for Training

This dataset contains **raw vulnerability data**. To use for training:

### Step 1: Transform into Chat Format (process_artifacts.py)
```python
# Transform raw records into chat-formatted training pairs
def transform_to_chat(record):
    return {{
        'messages': [
            {{'role': 'system', 'content': 'Security expert...'}},
            {{'role': 'user', 'content': f"Fix {{record['cwe_id']}} in {{record['language']}}:\\n{{record['vulnerable_code']}}"}},
            {{'role': 'assistant', 'content': f"Fixed code:\\n{{record['fixed_code']}}"}}
        ]
    }}
```

### Step 2: Sequential Fine-Tuning
```python
# Stage 1: General security training (this dataset)
model = train_on_crossvul(
    model_path="base-model",
    dataset="{repo_id}",
    transform_fn=transform_to_chat
)

# Stage 2: Project-specific adaptation
model = specialized_training(
    base_model=model,
    project_data="your-vulnerability-dataset",
    memory_replay=0.15  # 15% CrossVul to prevent forgetting
)
```

## Citation

If you use this dataset, please cite the original CrossVul paper:

```bibtex
@inproceedings{{wartschinski2022vulnrepair,
  title={{VulnRepair: Learning to Repair Vulnerable Code with Graph Neural Networks}},
  author={{Wartschinski, Laura and Noller, Yannic and Vogel, Thomas and Kehrer, Timo and Grunske, Lars}},
  booktitle={{Proceedings of the 44th International Conference on Software Engineering}},
  year={{2022}}
}}
```

## License

Apache License 2.0 - Derived from [CrossVul Dataset](https://zenodo.org/records/4734050)

## Dataset Preprocessing

This dataset was processed from the original CrossVul dataset using automated scripts to:
- Match vulnerable/fixed code pairs (bad_*/good_* files)
- Detect programming language from directory structure
- Filter by file size and quality (<500KB, >50 chars)
- Extract CWE metadata and descriptions
- Output raw JSON Lines format (no chat formatting)

**Note**: This is a raw dataset. Use `process_artifacts.py` to transform into chat-formatted training data.

Preprocessing script: [crossvul_dataset_loader.py](https://github.com/your-repo/security-ai-analysis)
"""

    return card

def upload_to_huggingface(
    dataset_path: Path,
    repo_id: str,
    private: bool,
    token: Optional[str],
    dataset_stats: Dict
) -> str:
    """
    Upload CrossVul raw dataset to HuggingFace Hub.

    Args:
        dataset_path: Path to single JSONL file
        repo_id: HuggingFace repository ID (username/dataset-name)
        private: Make repository private
        token: HuggingFace API token (or None to use HF_TOKEN env var)
        dataset_stats: Statistics dictionary for dataset card

    Returns:
        HuggingFace repository URL
    """
    try:
        from datasets import load_dataset
        from huggingface_hub import HfApi
    except ImportError:
        raise ImportError(
            "Missing required packages. Install with:\n"
            "pip install datasets huggingface_hub"
        )

    # Use token from argument or environment
    if token is None:
        token = os.getenv('HF_TOKEN')

    if not token:
        raise ValueError(
            "HuggingFace token required. Provide via --hf-token or HF_TOKEN environment variable"
        )

    logging.info(f"📦 Loading dataset from {dataset_path}...")

    # Load dataset from single JSONL file
    # HuggingFace convention: upload as 'train' split even if it's raw data
    data_files = {'train': str(dataset_path)}
    dataset = load_dataset('json', data_files=data_files)

    logging.info(f"📊 Dataset loaded: {len(dataset['train'])} raw vulnerability records")

    # Generate dataset card
    logging.info("📝 Generating dataset card...")
    dataset_card = create_dataset_card(
        repo_id=repo_id,
        num_examples=dataset_stats['num_examples'],
        num_cwes=dataset_stats['num_cwes'],
        languages=dataset_stats['languages'],
        language_distribution=dataset_stats['language_distribution'],
        cwe_distribution=dataset_stats['cwe_distribution']
    )

    # Save dataset card locally
    readme_path = dataset_path.parent / "README.md"
    with open(readme_path, 'w') as f:
        f.write(dataset_card)
    logging.info(f"✅ Dataset card saved to {readme_path}")

    # Upload dataset to HuggingFace WITHOUT card to avoid YAML validation
    logging.info(f"⬆️  Uploading dataset to HuggingFace: {repo_id} (private={private})...")
    dataset.push_to_hub(
        repo_id,
        private=private,
        token=token
    )

    # Upload README.md separately using HfApi (avoids YAML validation size limits)
    logging.info(f"⬆️  Uploading README.md separately...")
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
    )

    hf_url = f"https://huggingface.co/datasets/{repo_id}"
    logging.info(f"✅ Dataset uploaded successfully: {hf_url}")

    return hf_url


def main():
    parser = argparse.ArgumentParser(
        description="CrossVul dataset loader for multi-language security vulnerability training"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("crossvul_output"),
        help="Output directory for processed dataset (dataset auto-downloads here if not present)"
    )
    parser.add_argument(
        "--languages",
        nargs='+',
        default=None,
        help="Filter by languages (e.g., java python js go). Default: all languages"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of examples to process (for testing)"
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=500,
        help="Maximum file size in KB (default: 500)"
    )
    parser.add_argument(
        "--upload-to-hf",
        type=str,
        default=None,
        help="Upload dataset to HuggingFace Hub (format: username/dataset-name)"
    )
    parser.add_argument(
        "--hf-private",
        action="store_true",
        help="Make HuggingFace dataset private (default: public)"
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        default=None,
        help="HuggingFace API token (default: use HF_TOKEN env var)"
    )
    parser.add_argument(
        "--keep-zip",
        action="store_true",
        help="Keep downloaded ZIP file after extraction (default: delete to save space)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug output"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("🐛 Debug logging enabled")

    logging.info("🚀 Starting CrossVul Dataset Extraction")
    logging.info(f"   Output: {args.output_dir}")
    if args.languages:
        logging.info(f"   Language filter: {', '.join(args.languages)}")

    # Ensure CrossVul dataset is available in output directory (auto-download from Zenodo if needed)
    dataset_path = args.output_dir / "dataset_final_sorted"

    if not dataset_path.exists() or not any(dataset_path.iterdir()):
        logging.info(f"📥 Dataset not found at {dataset_path}, downloading from Zenodo...")
        try:
            dataset_path = ensure_crossvul_dataset_available(
                dataset_dir=args.output_dir,
                keep_zip=args.keep_zip
            )
        except Exception as e:
            logging.error(f"❌ Failed to download dataset: {e}")
            logging.error("   Please check your internet connection or download manually from:")
            logging.error("   https://zenodo.org/records/4734050")
            return
    else:
        logging.info(f"✅ Dataset found at: {dataset_path}")

    # Convert language filter to set of directory names
    language_filter = set(args.languages) if args.languages else None

    # Find all matching bad/good pairs
    pairs = find_matching_pairs(dataset_path, language_filter)

    if not pairs:
        logging.error("❌ No matching pairs found!")
        return

    # Apply limit if specified
    if args.limit:
        pairs = pairs[:args.limit]
        logging.info(f"⚠️  LIMITED to {args.limit} pairs for testing")

    # Process pairs into raw vulnerability records
    logging.info(f"\n📝 Processing {len(pairs)} pairs into raw vulnerability records...")
    records = []
    skipped_pairs = []
    skip_reason_counts = defaultdict(int)

    for idx, pair in enumerate(pairs, start=1):
        if idx % 500 == 0:
            logging.info(f"   Progress: {idx}/{len(pairs)} pairs processed ({len(records)} valid, {len(skipped_pairs)} skipped)")

        record, skip_info = create_raw_vulnerability_record(pair)
        if record:
            records.append(record)
        else:
            skipped_pairs.append(skip_info)
            skip_reason_counts[skip_info['skip_reason']] += 1

    logging.info(f"✅ Processed {len(records)} valid records ({len(skipped_pairs)} skipped)")

    # Log skip reason breakdown
    if skipped_pairs:
        logging.info(f"\n📋 Skip Reason Breakdown:")
        for reason, count in sorted(skip_reason_counts.items(), key=lambda x: x[1], reverse=True):
            logging.info(f"   {reason}: {count}")

    if not records:
        logging.error("❌ No valid records created!")
        return

    # Calculate dataset statistics
    language_distribution = defaultdict(int)
    cwe_distribution = defaultdict(int)

    for record in records:
        language_distribution[record['language']] += 1
        cwe_distribution[record['cwe_id']] += 1

    dataset_stats = {
        'num_examples': len(records),
        'num_cwes': len(cwe_distribution),
        'languages': sorted(language_distribution.keys()),
        'language_distribution': dict(language_distribution),
        'cwe_distribution': dict(cwe_distribution)
    }

    # Log statistics
    logging.info(f"\n📊 Dataset Statistics:")
    logging.info(f"   Total records: {len(records)}")
    logging.info(f"   Unique CWEs: {len(cwe_distribution)}")
    logging.info(f"   Languages: {len(language_distribution)}")
    logging.info(f"   Top languages: {', '.join([f'{k}({v})' for k, v in sorted(language_distribution.items(), key=lambda x: x[1], reverse=True)[:5]])}")

    # Save dataset as single JSONL file (no train/val/test splits - let process_artifacts.py handle that)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = args.output_dir / "crossvul_dataset.jsonl"

    logging.info(f"💾 Saving {len(records)} records to {dataset_path}...")
    with open(dataset_path, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    logging.info(f"✅ Dataset saved to {dataset_path}")

    # Save skipped pairs to separate file
    if skipped_pairs:
        skipped_path = args.output_dir / "skipped_pairs.jsonl"
        logging.info(f"💾 Saving {len(skipped_pairs)} skipped pairs to {skipped_path}...")
        with open(skipped_path, 'w') as f:
            for skip_info in skipped_pairs:
                f.write(json.dumps(skip_info) + '\n')
        logging.info(f"✅ Skipped pairs saved to {skipped_path}")

    # Save metadata
    metadata_path = args.output_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump({
            **dataset_stats,
            'extraction_date': datetime.now().isoformat(),
            'source': 'CrossVul',
            'source_url': 'https://zenodo.org/records/4734050',
            'language_filter': args.languages,
            'max_file_size_kb': args.max_file_size,
            'format': 'raw_vulnerability_records',
            'note': 'This is raw data - use process_artifacts.py to create chat-formatted training data',
            'skipped_pairs_count': len(skipped_pairs),
            'skip_reason_breakdown': dict(skip_reason_counts) if skipped_pairs else {}
        }, f, indent=2)
    logging.info(f"✅ Metadata saved to {metadata_path}")

    # Upload to HuggingFace if requested
    if args.upload_to_hf:
        try:
            hf_url = upload_to_huggingface(
                dataset_path=dataset_path,
                repo_id=args.upload_to_hf,
                private=args.hf_private,
                token=args.hf_token,
                dataset_stats=dataset_stats
            )
            logging.info(f"✅ Dataset available at: {hf_url}")
        except Exception as e:
            logging.error(f"❌ Failed to upload to HuggingFace: {e}")

    logging.info(f"\n🎉 All done! Raw dataset saved to: {args.output_dir}")
    logging.info(f"   Dataset file: {dataset_path}")
    logging.info(f"   Total records: {len(records)}")
    if skipped_pairs:
        logging.info(f"   Skipped pairs: {len(skipped_pairs)} (see skipped_pairs.jsonl)")
    logging.info(f"   Next step: Use process_artifacts.py to create chat-formatted training data")


if __name__ == "__main__":
    main()
