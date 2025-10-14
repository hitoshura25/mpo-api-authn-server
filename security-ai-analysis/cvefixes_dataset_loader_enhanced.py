#!/usr/bin/env python3
"""
Enhanced CVEfixes Dataset Loader

Extracts comprehensive vulnerability data from CVEfixes v1.0.8 using:
- Automatic dataset download from Zenodo (12.7 GB, one-time)
- SQLite3 database queries (instead of SQL regex parsing)
- Repository-based processing (1 repo = 1 file, 64% more efficient)
- Enhanced Git metadata extraction
- Robust error handling with UTF-8 fallback and retries

Usage:
    # Basic usage (dataset downloads automatically if not present)
    python cvefixes_dataset_loader_enhanced.py \\
        --output-dir cvefixes_output \\
        --workers 8

    # Testing with limited records
    python cvefixes_dataset_loader_enhanced.py \\
        --output-dir cvefixes_output \\
        --limit 10

    # Keep downloaded ZIP file (saves 12.7 GB disk space by default)
    python cvefixes_dataset_loader_enhanced.py \\
        --output-dir cvefixes_output \\
        --keep-db-zip

    # Run with debug output (verbose mode)
    python cvefixes_dataset_loader_enhanced.py \\
        --output-dir cvefixes_output \\
        --verbose  # Or -v for short

    # Upload to HuggingFace after extraction
    python cvefixes_dataset_loader_enhanced.py \\
        --output-dir cvefixes_output \\
        --upload-to-hf username/dataset-name

Dataset Download:
    The script automatically downloads CVEfixes v1.0.8 from Zenodo if not found locally:
    - Source: https://zenodo.org/records/13118970
    - Size: 12.7 GB compressed → 11.84 GB extracted
    - Version: v1.0.8 (July 28, 2024)
    - One-time download with resume capability
"""

import logging
import subprocess
import shutil
import time
import json
import sqlite3
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime
import pandas as pd
import argparse
import os
import fcntl
import concurrent.futures
from typing import Dict, List, Set, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ChunkedCheckpointer:
    """
    Assembles repository-based JSONL chunks into final Parquet dataset.

    Output structure:
        output_dir/
        └── completed_chunks/
            ├── repo_<hash>.jsonl  # Repository 1
            ├── repo_<hash>.jsonl  # Repository 2
            └── ...
    """

    def __init__(self, output_dir: Path, chunk_size: int = 100):
        self.output_dir = Path(output_dir)
        self.chunks_dir = self.output_dir / "completed_chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

    def assemble_parquet(self, output_filename: str = "cvefixes_dataset.parquet") -> pd.DataFrame:
        """Combine all repository chunks into final Parquet file."""
        logging.info("📊 Assembling final Parquet dataset from all repository chunks...")

        all_records = []
        chunk_files = sorted(self.chunks_dir.glob("repo_*.jsonl"))

        for chunk_file in chunk_files:
            with open(chunk_file, 'r') as f:
                for line in f:
                    if line.strip():
                        all_records.append(json.loads(line))

        if not all_records:
            logging.warning("No records found to assemble into Parquet")
            return None

        df = pd.DataFrame(all_records)
        parquet_path = self.output_dir / output_filename
        df.to_parquet(parquet_path, index=False)

        logging.info(f"✅ Assembled {len(df)} records into {parquet_path}")
        logging.info(f"   Columns: {list(df.columns)}")
        logging.info(f"   File size: {parquet_path.stat().st_size / (1024*1024):.1f} MB")

        return df


def safe_decode(byte_string: bytes) -> str:
    """
    Decode bytes with UTF-8 fallback chain.

    Tries: UTF-8 → latin-1 → UTF-8 with errors ignored
    """
    if isinstance(byte_string, str):
        return byte_string

    try:
        return byte_string.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return byte_string.decode('latin-1')
        except Exception:
            return byte_string.decode('utf-8', errors='ignore')


def write_checkpoint_atomic(checkpoint_file: Path, cve_data: dict) -> None:
    """
    Write checkpoint file atomically with file locking to prevent race conditions.

    Uses exclusive file locking (fcntl.LOCK_EX) to ensure only one thread can
    write to the checkpoint file at a time. This prevents JSON corruption when
    multiple threads try to write checkpoint files concurrently.

    Args:
        checkpoint_file: Path to checkpoint file
        cve_data: CVE data dictionary to write

    Raises:
        IOError: If file locking or writing fails
    """
    # Write to temporary file first (atomic rename pattern)
    temp_file = checkpoint_file.with_suffix('.tmp')

    try:
        # Open file with exclusive lock
        with open(temp_file, 'w') as f:
            # Acquire exclusive lock (blocks until available)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                # Write JSON data
                json.dump(cve_data, f)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            finally:
                # Release lock (automatically released on close, but explicit is better)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Atomic rename (POSIX guarantees atomicity)
        temp_file.rename(checkpoint_file)

    except Exception as e:
        # Cleanup temp file on error
        if temp_file.exists():
            temp_file.unlink()
        raise IOError(f"Failed to write checkpoint {checkpoint_file.name}: {e}") from e


def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (doubles each retry)

    Returns:
        Function result if successful

    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except subprocess.TimeoutExpired as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logging.warning(f"Timeout on attempt {attempt + 1}/{max_retries}, retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise
        except subprocess.CalledProcessError as e:
            last_exception = e
            if attempt < max_retries - 1 and "429" in str(e):  # Rate limit
                delay = initial_delay * (2 ** attempt)
                logging.warning(f"Rate limit on attempt {attempt + 1}/{max_retries}, retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise

    raise last_exception


def get_git_env() -> dict:
    """
    Get environment with GitHub token for git authentication.

    Configures git credential helper to use GH_TOKEN environment variable
    for automatic authentication with GitHub without prompts.

    Returns:
        Dictionary with environment variables including git credential config
    """
    env = os.environ.copy()
    gh_token = os.getenv('GH_TOKEN')
    if gh_token:
        # Configure git credential helper to use GH_TOKEN
        env['GIT_ASKPASS'] = 'echo'
        env['GH_TOKEN'] = gh_token
        # For GitHub URLs, use token in HTTP extraheader
        env['GIT_CONFIG_COUNT'] = '1'
        env['GIT_CONFIG_KEY_0'] = 'credential.https://github.com.helper'
        env['GIT_CONFIG_VALUE_0'] = f'!f() {{ echo "username=x-access-token"; echo "password={gh_token}"; }}; f'
    return env


def get_repo_filename(repo_url: str) -> str:
    """
    Generate filesystem-safe filename from repo URL.

    Uses SHA256 hash of repo URL to ensure:
    - Consistent naming
    - Filesystem safety (no special characters)
    - Collision resistance

    Args:
        repo_url: Git repository URL

    Returns:
        Filename like "repo_<hash>.jsonl"
    """
    url_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
    return f"repo_{url_hash}.jsonl"


def extract_security_keywords(text: str) -> List[str]:
    """
    Extract security-related keywords from commit message/description.

    Returns list of matched security pattern categories.
    """
    if not text:
        return []

    text_lower = text.lower()

    security_patterns = {
        'sanitization': ['sanitize', 'escape', 'encode', 'filter'],
        'validation': ['validate', 'check', 'verify', 'assert'],
        'authentication': ['auth', 'login', 'credential', 'token'],
        'authorization': ['permission', 'access control', 'privilege'],
        'cryptography': ['encrypt', 'decrypt', 'hash', 'crypto', 'cipher'],
        'input_handling': ['input', 'user data', 'untrusted'],
    }

    matched_categories = []
    for category, keywords in security_patterns.items():
        if any(keyword in text_lower for keyword in keywords):
            matched_categories.append(category)

    return matched_categories


def run_git_gc(repo_dir: str, aggressive: bool = False, timeout: int = 300) -> bool:
    """
    Run git garbage collection to consolidate pack files and reduce disk usage.

    Args:
        repo_dir: Path to git repository
        aggressive: Use aggressive gc (slower but more space savings)
        timeout: Timeout in seconds for gc operation

    Returns:
        True if gc succeeded, False otherwise
    """
    try:
        gc_args = ['git', 'gc']
        if aggressive:
            gc_args.append('--aggressive')
        else:
            gc_args.append('--auto')  # Only run if needed

        logging.debug(f"🧹 Running git gc in {repo_dir}...")
        subprocess.run(
            gc_args,
            cwd=repo_dir,
            check=True,
            capture_output=True,
            timeout=timeout,
            env=get_git_env()
        )
        logging.debug(f"✅ Git gc completed successfully")
        return True

    except subprocess.TimeoutExpired:
        logging.warning(f"⚠️  Git gc timed out after {timeout}s (non-critical)")
        return False
    except subprocess.CalledProcessError as e:
        logging.warning(f"⚠️  Git gc failed (non-critical): {e}")
        return False
    except Exception as e:
        logging.warning(f"⚠️  Git gc error (non-critical): {e}")
        return False


def prefetch_commits_in_batches(
    repo_dir: str,
    cves_to_process: List[Dict[str, Any]],
    git_timeout: int,
    batch_size: int = 50,
    gc_interval: int = 250
) -> Set[str]:
    """
    Pre-fetch commits in batches to optimize git storage and reduce duplication.

    Fetches commits in batches instead of individually, which allows git to
    create efficient pack files. Runs periodic git gc to consolidate packs
    and prevent the .git folder from growing to 100+ GB.

    Args:
        repo_dir: Path to cloned repository
        cves_to_process: List of CVE records with commit hashes
        git_timeout: Timeout for git operations
        batch_size: Number of commits to fetch per batch (default: 50)
        gc_interval: Run git gc after this many commits (default: 250)

    Returns:
        Set of commit hashes that failed to fetch
    """
    total_commits = len(cves_to_process)
    logging.info(f"📥 Pre-fetching {total_commits} commits in batches of {batch_size}...")

    failed_commits = set()
    commits_fetched = 0

    # Process commits in batches
    for batch_idx in range(0, total_commits, batch_size):
        batch = cves_to_process[batch_idx:batch_idx + batch_size]
        commit_hashes = [cve['hash'] for cve in batch]
        batch_num = batch_idx // batch_size + 1
        total_batches = (total_commits + batch_size - 1) // batch_size

        try:
            # Fetch entire batch at once (git optimizes this into efficient pack)
            logging.debug(f"🔄 Fetching batch {batch_num}/{total_batches} ({len(commit_hashes)} commits)...")

            def fetch_batch():
                subprocess.run(
                    ['git', 'fetch', 'origin'] + commit_hashes,
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=git_timeout,
                    env=get_git_env()
                )

            retry_with_backoff(fetch_batch, max_retries=2)
            commits_fetched += len(commit_hashes)
            logging.info(f"✅ Fetched batch {batch_num}/{total_batches} ({commits_fetched}/{total_commits} commits)")

        except Exception as e:
            # Batch fetch failed, fall back to individual fetches for this batch
            logging.warning(f"⚠️  Batch {batch_num} fetch failed, trying individual fetches: {e}")

            for cve in batch:
                commit_hash = cve['hash']
                cve_id = cve['cve_id']
                try:
                    def fetch_single():
                        subprocess.run(
                            ['git', 'fetch', 'origin', commit_hash],
                            cwd=repo_dir,
                            check=True,
                            capture_output=True,
                            text=True,
                            timeout=git_timeout,
                            env=get_git_env()
                        )

                    retry_with_backoff(fetch_single, max_retries=2)
                    commits_fetched += 1

                except Exception as fetch_error:
                    logging.warning(f"⚠️  Failed to fetch {cve_id} ({commit_hash}): {fetch_error}")
                    failed_commits.add(commit_hash)

        # Run git gc periodically to consolidate pack files
        if commits_fetched > 0 and commits_fetched % gc_interval == 0:
            logging.info(f"🧹 Running git gc after {commits_fetched} commits to consolidate packs...")
            run_git_gc(repo_dir, aggressive=False, timeout=300)

    # Final progress log
    success_count = commits_fetched - len(failed_commits)
    logging.info(f"✅ Pre-fetch complete: {success_count}/{total_commits} commits fetched successfully")

    if failed_commits:
        logging.warning(f"⚠️  {len(failed_commits)} commits failed pre-fetch (will retry during processing)")

    return failed_commits


def create_cvefixes_dataset_card(
    repo_id: str,
    num_records: int,
    num_repositories: int,
    num_cves: int,
    languages: List[str],
    date_range: tuple,
    severity_distribution: dict
) -> str:
    """
    Generate minimal HuggingFace dataset card for CVEfixes dataset.

    Simplified version following HuggingFace best practices - includes only
    essential information (description, usage, citation, license).

    Args:
        repo_id: HuggingFace repository ID
        num_records: Total number of records
        num_repositories: Number of unique repositories
        num_cves: Number of unique CVEs
        languages: List of programming languages (unused in minimal version)
        date_range: Tuple of (earliest_date, latest_date) (unused in minimal version)
        severity_distribution: Dictionary of severity counts (unused in minimal version)

    Returns:
        Markdown formatted dataset card (minimal version)
    """
    card = f"""---
license: apache-2.0
task_categories:
- text-generation
language:
- code
size_categories:
- 10K<n<100K
---

# CVEfixes Security Vulnerabilities Dataset

Security vulnerability data from [CVEfixes v1.0.8](https://github.com/secureIT-project/CVEfixes) with **{num_records:,}** vulnerability fix records across **{num_cves:,}** unique CVEs and **{num_repositories:,}** repositories.

Contains CVE metadata (descriptions, CVSS scores, CWE classifications), git commit data, and code diffs showing vulnerable vs fixed code.

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("{repo_id}")
```

## Citation

If you use this dataset, please cite the original CVEfixes paper:

```bibtex
@inproceedings{{bhandari2021cvefixes,
  title={{CVEfixes: Automated Collection of Vulnerabilities and Their Fixes from Open-Source Software}},
  author={{Bhandari, Guru and Naseer, Amara and Moonen, Leon}},
  booktitle={{Proceedings of the 17th International Conference on Predictive Models and Data Analytics in Software Engineering}},
  pages={{30--39}},
  year={{2021}}
}}
```

## License

Apache License 2.0 - Derived from [CVEfixes](https://github.com/secureIT-project/CVEfixes)
"""

    return card


def shard_and_upload_via_folder(
    df: pd.DataFrame,
    output_dir: Path,
    repo_id: str,
    private: bool,
    token: str,
    readme_content: str,
    shard_size_mb: int = 500
) -> str:
    """
    Manually shard dataset and upload via upload_folder to avoid metadata generation.

    This approach bypasses HuggingFace's automatic YAML metadata generation by:
    1. Manually creating Parquet shards with HuggingFace naming convention
    2. Using upload_folder() to upload pre-structured directory
    3. Avoiding push_to_hub() which triggers metadata generation

    Args:
        df: Pandas DataFrame with dataset records
        output_dir: Base output directory for temporary files
        repo_id: HuggingFace repository ID (username/dataset-name)
        private: Make repository private
        token: HuggingFace API token
        readme_content: README.md content to upload
        shard_size_mb: Target size per shard in MB (default: 500)

    Returns:
        HuggingFace repository URL

    Raises:
        Exception: If upload fails
    """
    from huggingface_hub import HfApi

    api = HfApi(token=token)

    # Create temporary upload structure
    upload_dir = output_dir / "hf_upload_folder"
    data_dir = upload_dir / "data"

    # Clean up any existing upload directory
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    data_dir.mkdir(parents=True, exist_ok=True)

    logging.info(f"📦 Creating manual shards in: {upload_dir}")

    # Calculate rows per shard based on target size
    # Estimate row size from memory usage
    estimated_row_size_bytes = df.memory_usage(deep=True).sum() / len(df)
    target_size_bytes = shard_size_mb * 1024 * 1024
    rows_per_shard = max(1, int(target_size_bytes / estimated_row_size_bytes))

    # Calculate number of shards
    num_shards = (len(df) + rows_per_shard - 1) // rows_per_shard

    logging.info(f"   Estimated row size: {estimated_row_size_bytes / 1024:.1f} KB")
    logging.info(f"   Rows per shard: {rows_per_shard:,}")
    logging.info(f"   Number of shards: {num_shards}")

    # Create shards with HuggingFace naming convention
    for shard_idx in range(num_shards):
        start_idx = shard_idx * rows_per_shard
        end_idx = min((shard_idx + 1) * rows_per_shard, len(df))
        shard_df = df.iloc[start_idx:end_idx]

        # HuggingFace expects: data/train-XXXXX-of-XXXXX.parquet
        shard_filename = f"train-{shard_idx:05d}-of-{num_shards:05d}.parquet"
        shard_path = data_dir / shard_filename

        shard_df.to_parquet(shard_path, index=False)
        shard_size_mb = shard_path.stat().st_size / (1024 * 1024)

        logging.info(f"   ✅ Created {shard_filename} ({len(shard_df):,} rows, {shard_size_mb:.1f} MB)")

    # Write README.md to upload directory
    readme_path = upload_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    logging.info(f"   ✅ Created README.md")

    # Create repository if it doesn't exist
    logging.info(f"⬆️  Creating/updating repository: {repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)

    # Upload entire folder structure at once
    logging.info(f"⬆️  Uploading {num_shards} shards + README via upload_folder()...")
    api.upload_folder(
        folder_path=str(upload_dir),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Upload CVEfixes dataset ({len(df):,} records, {num_shards} shards)"
    )

    # Cleanup temporary folder
    logging.info(f"🧹 Cleaning up temporary upload folder...")
    shutil.rmtree(upload_dir)

    hf_url = f"https://huggingface.co/datasets/{repo_id}"
    logging.info(f"✅ Upload complete: {hf_url}")

    return hf_url


def upload_cvefixes_to_huggingface(
    df: pd.DataFrame,
    parquet_file: Path,
    output_dir: Path,
    repo_id: str,
    private: bool,
    token: Optional[str]
) -> str:
    """
    Upload processed CVEfixes dataset to HuggingFace Hub.

    Args:
        df: Pandas DataFrame with dataset records (pre-loaded, no duplicate read)
        parquet_file: Path to original Parquet file (for logging only)
        output_dir: Output directory
        repo_id: HuggingFace repository ID (username/dataset-name)
        private: Make repository private
        token: HuggingFace API token (or None to use HF_TOKEN env var)

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

    logging.info(f"\n📤 Uploading dataset to HuggingFace: {repo_id}")
    logging.info(f"📊 Dataset: {len(df):,} records (pre-loaded)")

    # Calculate dataset statistics for README
    logging.info("📊 Calculating dataset statistics...")
    dataset_stats = {
        'num_records': len(df),
        'num_repositories': df['repo_url'].nunique(),
        'num_cves': df['cve_id'].nunique(),
        'languages': df['language'].unique().tolist() if 'language' in df.columns else [],
        'date_range': (
            df['commit_date'].min() if 'commit_date' in df.columns else 'N/A',
            df['commit_date'].max() if 'commit_date' in df.columns else 'N/A'
        ),
        'severity_distribution': df['severity'].value_counts().to_dict() if 'severity' in df.columns else {}
    }

    # Generate dataset card
    logging.info("📝 Generating dataset card...")
    dataset_card = create_cvefixes_dataset_card(
        repo_id=repo_id,
        num_records=dataset_stats['num_records'],
        num_repositories=dataset_stats['num_repositories'],
        num_cves=dataset_stats['num_cves'],
        languages=dataset_stats['languages'],
        date_range=dataset_stats['date_range'],
        severity_distribution=dataset_stats['severity_distribution']
    )

    # Use manual sharding approach to avoid 413 metadata generation errors
    logging.info(f"⬆️  Uploading dataset via manual sharding approach...")
    logging.info(f"   This bypasses HuggingFace's automatic YAML metadata generation")

    try:
        hf_url = shard_and_upload_via_folder(
            df=df,
            output_dir=output_dir,
            repo_id=repo_id,
            private=private,
            token=token,
            readme_content=dataset_card,
            shard_size_mb=500  # Target 500MB per shard
        )
        logging.info(f"✅ Dataset uploaded successfully: {hf_url}")
        return hf_url

    except Exception as e:
        # If manual sharding fails, fall back to graceful 413 handling approach
        logging.warning(f"⚠️  Manual sharding upload failed: {e}")
        logging.info(f"   Attempting fallback with datasets library...")

        dataset = load_dataset("parquet", data_files=str(parquet_file))
        api = HfApi(token=token)
        upload_succeeded = False

        # Save dataset card locally for fallback
        readme_path = output_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(dataset_card)

        try:
            dataset.card_data = None  # Disable automatic card generation
            dataset.push_to_hub(
                repo_id,
                private=private,
                token=token,
                create_pr=False,
                embed_external_files=False
            )
            upload_succeeded = True
            logging.info(f"✅ Dataset upload completed successfully (fallback method)")

        except Exception as fallback_error:
            error_message = str(fallback_error)

            # Check if this is the known 413 error
            if "413" in error_message or "Payload Too Large" in error_message:
                logging.warning(f"⚠️  Fallback also got 413 error: {fallback_error}")
                logging.info(f"   Checking if files were uploaded despite error...")

                try:
                    repo_files = api.list_repo_files(repo_id=repo_id, repo_type="dataset", token=token)
                    data_files = [f for f in repo_files if f.startswith("data/train-") and f.endswith(".parquet")]

                    if data_files:
                        logging.info(f"✅ Found {len(data_files)} data files in repository:")
                        logging.info(f"   {data_files[0]} through {data_files[-1]}")
                        upload_succeeded = True
                    else:
                        raise Exception(f"Upload failed - no data files found: {fallback_error}")

                except Exception as verify_error:
                    raise Exception(f"Upload failed and could not verify: {fallback_error}")
            else:
                raise

        # Upload README.md if fallback succeeded
        if upload_succeeded:
            logging.info(f"⬆️  Uploading README.md (fallback method)...")
            api.upload_file(
                path_or_fileobj=str(readme_path),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
                commit_message="Add dataset card"
            )
            logging.info(f"✅ README.md uploaded successfully")

        hf_url = f"https://huggingface.co/datasets/{repo_id}"
        logging.info(f"✅ Dataset uploaded successfully (via fallback): {hf_url}")
        return hf_url


def download_with_progress(url: str, output_path: Path, timeout: int = 3600) -> bool:
    """
    Download file from URL with progress bar and resume capability.

    Args:
        url: URL to download from
        output_path: Path where file will be saved
        timeout: Timeout in seconds for download operation

    Returns:
        True if download successful, False otherwise

    Raises:
        Exception: If download fails after retries
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
        logging.info(f"📥 Resuming download from {resume_byte_pos / (1024**3):.2f} GB...")

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

    Raises:
        Exception: If extraction fails
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
            logging.info(f"🧹 Deleting ZIP file to save space: {zip_path}")
            zip_path.unlink()
            logging.info(f"✅ Deleted {zip_path.name} ({zip_path.stat().st_size / (1024**3) if zip_path.exists() else 0:.2f} GB saved)")

        return True

    except zipfile.BadZipFile as e:
        logging.error(f"❌ Invalid ZIP file: {e}")
        raise
    except Exception as e:
        logging.error(f"❌ Extraction failed: {e}")
        raise


def ensure_cvefixes_dataset_available(dataset_dir: Path, keep_db_zip: bool = False) -> Path:
    """
    Ensure CVEfixes dataset is available, downloading from Zenodo if needed.

    This function:
    1. Checks if dataset already exists (database, SQL files, or extracted data)
    2. If not found, downloads CVEfixes v1.0.8 from Zenodo (12.7 GB)
    3. Extracts the ZIP file (11.84 GB uncompressed)
    4. Optionally deletes ZIP to save space (default behavior)

    Args:
        dataset_dir: Base directory for dataset (e.g., data/public_datasets)
        keep_db_zip: Keep ZIP file after extraction (default: delete to save space)

    Returns:
        Path to extracted CVEfixes dataset directory

    Raises:
        Exception: If download or extraction fails
    """
    dataset_dir = Path(dataset_dir)
    cvefixes_dir = dataset_dir / "CVEfixes_v1.0.8"
    data_dir = cvefixes_dir / "Data"

    # Check if dataset already exists
    # Look for: database file, SQL files, or Data directory
    db_file = data_dir / "CVEfixes.db"
    sql_files = list(data_dir.glob("CVEfixes*.sql*")) if data_dir.exists() else []

    if db_file.exists():
        logging.info(f"✅ CVEfixes database already exists: {db_file}")
        return cvefixes_dir
    elif sql_files:
        logging.info(f"✅ CVEfixes SQL files found: {sql_files[0]}")
        return cvefixes_dir
    elif data_dir.exists() and any(data_dir.iterdir()):
        logging.info(f"✅ CVEfixes data directory already exists: {data_dir}")
        return cvefixes_dir

    # Dataset not found, download from Zenodo
    logging.info("📥 CVEfixes dataset not found locally. Downloading from Zenodo...")
    logging.info("   Source: https://zenodo.org/records/13118970")
    logging.info("   Version: CVEfixes v1.0.8 (July 28, 2024)")
    logging.info("   Size: 12.7 GB compressed → 11.84 GB extracted")
    logging.info("   ⚠️  This is a one-time download and may take 10-30 minutes depending on connection speed.")

    # Zenodo download URL
    zenodo_url = "https://zenodo.org/records/13118970/files/CVEfixes_v1.0.8.zip?download=1"
    zip_path = dataset_dir / "CVEfixes_v1.0.8.zip"

    try:
        # Download ZIP file
        logging.info(f"📥 Downloading CVEfixes v1.0.8 from Zenodo...")
        download_with_progress(zenodo_url, zip_path, timeout=7200)  # 2 hour timeout

        # Extract ZIP file
        extract_zip_with_progress(zip_path, dataset_dir, keep_zip=keep_db_zip)

        # Verify extraction
        if not cvefixes_dir.exists():
            raise FileNotFoundError(
                f"Extraction completed but dataset directory not found: {cvefixes_dir}\n"
                f"Expected structure: {cvefixes_dir}/Data/CVEfixes_v1.0.8.sql.gz"
            )

        logging.info(f"✅ CVEfixes dataset ready: {cvefixes_dir}")
        return cvefixes_dir

    except Exception as e:
        # Cleanup on failure
        logging.error(f"❌ Failed to download/extract CVEfixes dataset: {e}")
        if zip_path.exists():
            logging.info(f"🧹 Cleaning up partial download: {zip_path}")
            zip_path.unlink()
        raise


def create_sqlite_database_if_needed(db_path: Path) -> bool:
    """
    Create SQLite database from SQL file if it doesn't exist.

    Looks for SQL file in same directory as database path.
    Tries both .sql and .sql.gz extensions.

    Args:
        db_path: Path where SQLite database should exist

    Returns:
        True if database was created, False if already existed

    Raises:
        FileNotFoundError: If neither SQL nor database file exists
    """
    if db_path.exists():
        return False

    # Look for SQL source file in same directory
    sql_dir = db_path.parent
    sql_name_base = db_path.stem  # e.g., "CVEfixes" from "CVEfixes.db"

    # Try to find SQL file (with or without version numbers)
    # Patterns: CVEfixes.sql, CVEfixes.sql.gz, CVEfixes_v1.0.8.sql, CVEfixes_v1.0.8.sql.gz
    sql_candidates = list(sql_dir.glob(f"{sql_name_base}*.sql"))
    sql_gz_candidates = list(sql_dir.glob(f"{sql_name_base}*.sql.gz"))

    # Prefer exact name match, then versioned files
    sql_file = None
    sql_gz_file = None

    # Check for uncompressed SQL
    for candidate in sorted(sql_candidates):
        if candidate.stem == sql_name_base:  # Exact match (e.g., CVEfixes.sql)
            sql_file = candidate
            break
    if not sql_file and sql_candidates:  # Use versioned file (e.g., CVEfixes_v1.0.8.sql)
        sql_file = sql_candidates[0]

    # Check for compressed SQL
    for candidate in sorted(sql_gz_candidates):
        # Remove .gz to get base name
        base_name = candidate.stem  # e.g., "CVEfixes_v1.0.8.sql" from "CVEfixes_v1.0.8.sql.gz"
        base_name = Path(base_name).stem  # Remove .sql to get "CVEfixes_v1.0.8"
        if base_name == sql_name_base:  # Exact match
            sql_gz_file = candidate
            break
    if not sql_gz_file and sql_gz_candidates:  # Use versioned file
        sql_gz_file = sql_gz_candidates[0]

    # Check for uncompressed SQL file first
    if sql_file and sql_file.exists():
        logging.info(f"📦 SQLite database not found. Creating from {sql_file.name}...")
        logging.info(f"   This is a one-time operation and will take ~10 minutes for 48GB file.")

        try:
            # Import SQL file into SQLite database
            with open(sql_file, 'r') as f:
                subprocess.run(
                    ['sqlite3', str(db_path)],
                    stdin=f,
                    check=True,
                    capture_output=True,
                    timeout=900  # 15 minute timeout
                )

            logging.info(f"✅ Successfully created SQLite database: {db_path}")
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            logging.info(f"   Database size: {db_size_mb:.1f} MB")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to create database: {e}")
            # Clean up partial database
            if db_path.exists():
                db_path.unlink()
            raise

    # Try compressed SQL file
    elif sql_gz_file and sql_gz_file.exists():
        logging.info(f"📦 SQLite database not found. Creating from {sql_gz_file.name}...")
        logging.info(f"   This is a one-time operation and will take ~10 minutes.")

        try:
            # Decompress and import in one pipeline: gzcat file.sql.gz | sqlite3 db
            subprocess.run(
                f'gzcat "{sql_gz_file}" | sqlite3 "{db_path}"',
                shell=True,
                check=True,
                capture_output=True,
                timeout=900  # 15 minute timeout
            )

            logging.info(f"✅ Successfully created SQLite database: {db_path}")
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
            logging.info(f"   Database size: {db_size_mb:.1f} MB")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to create database: {e}")
            # Clean up partial database
            if db_path.exists():
                db_path.unlink()
            raise

    else:
        # Neither database nor SQL source file found
        raise FileNotFoundError(
            f"Cannot create SQLite database. No source SQL file found.\n"
            f"Expected one of:\n"
            f"  - {sql_file} (uncompressed)\n"
            f"  - {sql_gz_file} (gzipped)\n"
            f"  - {db_path} (existing database)\n\n"
            f"Please ensure CVEfixes SQL dump is present in: {sql_dir}"
        )


def load_cvefixes_from_db(db_path: Path, limit: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load CVE data from SQLite database grouped by repository.

    Uses SQL joins to combine data from:
    - fixes: CVE → commit mapping
    - cve: CVE descriptions, CVSS scores, severity
    - cwe_classification: CVE → CWE mapping
    - cwe: CWE names and descriptions

    Args:
        db_path: Path to CVEfixes.db SQLite database
        limit: Optional limit on number of records to load

    Returns:
        Dictionary mapping repo_url → list of CVE fix records for that repo
    """
    logging.info(f"Loading CVE data from SQLite database: {db_path}")

    # Auto-create database if it doesn't exist
    create_sqlite_database_if_needed(db_path)

    conn = sqlite3.connect(str(db_path))

    # Query with LEFT JOINs to get all metadata
    # Note: Some CVEs may not have CWE classifications
    query = """
        SELECT
            fx.cve_id,
            fx.hash,
            fx.repo_url,
            cv.description as cve_description,
            cv.cvss2_base_score,
            cv.cvss3_base_score,
            cv.published_date,
            cv.severity,
            cc.cwe_id,
            cw.cwe_name,
            cw.description as cwe_description
        FROM fixes fx
        LEFT JOIN cve cv ON fx.cve_id = cv.cve_id
        LEFT JOIN cwe_classification cc ON cv.cve_id = cc.cve_id
        LEFT JOIN cwe cw ON cc.cwe_id = cw.cwe_id
    """

    if limit:
        query += f" LIMIT {limit}"

    df = pd.read_sql_query(query, conn)
    conn.close()

    logging.info(f"Loaded {len(df)} CVE records from database")
    logging.info(f"  Unique CVEs: {df['cve_id'].nunique()}")
    logging.info(f"  Unique commits: {df['hash'].nunique()}")
    logging.info(f"  Unique repositories: {df['repo_url'].nunique()}")

    # Group by repository
    repos_data = {}
    for repo_url, group in df.groupby('repo_url'):
        repos_data[repo_url] = group.to_dict('records')

    logging.info(f"📦 Grouped into {len(repos_data)} repositories")

    return repos_data


def process_repository_cves(
    repo_url: str,
    cve_fixes: List[Dict[str, Any]],
    git_timeout: int,
    work_repos_dir: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Process all CVE fixes for a single repository.

    Clones the repository once and extracts data for all commits/CVEs.

    Args:
        repo_url: Git repository URL
        cve_fixes: List of CVE fix records for this repo
        git_timeout: Timeout in seconds for Git operations
        work_repos_dir: Directory for working Git repositories
        output_dir: Output directory for chunk files

    Returns:
        Dictionary with processing results:
        - success: boolean
        - repo_url: repository URL
        - cves_processed: number of CVEs successfully processed
        - cves_failed: number of CVEs that failed
        - results: list of extracted CVE data
        - errors: list of error details
    """
    cve_fixes_length = len(cve_fixes)
    logging.info(f"📦 Processing repository: {repo_url} ({cve_fixes_length} CVEs)")

    # Check if already processed
    repo_filename = get_repo_filename(repo_url)
    chunks_dir = output_dir / "completed_chunks"
    repo_file_path = chunks_dir / repo_filename

    if repo_file_path.exists():
        logging.info(f"✅ Repo already processed: {repo_url} (skipping)")
        return {
            'success': True,
            'repo_url': repo_url,
            'cves_processed': cve_fixes_length,
            'cves_failed': 0,
            'results': [],
            'errors': [],
            'skipped': True
        }

    # Per-CVE checkpoint directory for incremental progress
    checkpoint_dir = chunks_dir / f"{Path(repo_filename).stem}_cves"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Load already-processed CVEs from checkpoint directory
    processed_cve_ids = set()
    existing_checkpoints = {}

    if checkpoint_dir.exists():
        for checkpoint_file in checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    cve_data = json.load(f)
                    cve_id = cve_data.get('cve_id')
                    if cve_id:
                        processed_cve_ids.add(cve_id)
                        existing_checkpoints[cve_id] = cve_data
            except Exception as e:
                logging.warning(f"⚠️  Failed to load checkpoint {checkpoint_file.name}: {e}")

    # Filter out already-processed CVEs
    cves_to_process = [cve for cve in cve_fixes if cve['cve_id'] not in processed_cve_ids]
    cves_to_process_length = len(cves_to_process)

    if processed_cve_ids:
        logging.info(f"📋 Found {len(processed_cve_ids)} already-processed CVEs, {cves_to_process_length} remaining")

    # If all CVEs already processed, consolidate and return
    if not cves_to_process:
        logging.info(f"✅ All CVEs already checkpointed for {repo_url}, consolidating...")
        results = list(existing_checkpoints.values())

        # Write consolidated file
        chunks_dir.mkdir(parents=True, exist_ok=True)
        with open(repo_file_path, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + '\n')

        # Cleanup checkpoint directory
        shutil.rmtree(checkpoint_dir, ignore_errors=True)

        return {
            'success': True,
            'repo_url': repo_url,
            'cves_processed': len(results),
            'cves_failed': 0,
            'results': [],
            'errors': [],
            'skipped': True
        }

    # Create working directory with consistent hash-based naming (matches chunk file naming)
    repo_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
    work_dir_name = f"repo_{repo_hash}"
    work_dir_path = work_repos_dir / work_dir_name
    temp_dir = str(work_dir_path)

    if work_dir_path.exists():
        shutil.rmtree(work_dir_path)
    os.makedirs(temp_dir, exist_ok=True)

    results = []
    errors = []

    try:
        # Clone repository once for all CVEs
        logging.info(f"🔄 Cloning {repo_url}...")

        def clone_repo():
            subprocess.run(
                ['git', 'clone', '--depth', '2', repo_url, temp_dir],
                check=True,
                capture_output=True,
                text=True,
                timeout=git_timeout,
                env=get_git_env()
            )

        retry_with_backoff(clone_repo, max_retries=3)
        logging.debug(f"✅ Cloned repository: {repo_url}")

        # Process each CVE fix in this repository (only unprocessed CVEs)
        for idx, cve_record in enumerate(cves_to_process, start=1):
            commit_hash = cve_record['hash']
            cve_id = cve_record['cve_id']
            logging.info(f"🔍 Processing {cve_id} at commit {commit_hash} ({idx}/{cves_to_process_length})...")
            try:
                # Fetch specific commit if needed
                def fetch_commit():
                    subprocess.run(
                        ['git', 'fetch', 'origin', commit_hash],
                        cwd=temp_dir,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=git_timeout,
                        env=get_git_env()
                    )

                logging.debug(f"🔄 Fetching commit {commit_hash} for {cve_id} ({idx}/{len(cves_to_process)})...")
                retry_with_backoff(fetch_commit, max_retries=2)
                logging.debug(f"✅ Fetched commit {commit_hash}")

                # Extract commit data (reuse existing logic)
                cve_data = extract_commit_data(temp_dir, commit_hash, cve_record, git_timeout)
                results.append(cve_data)

                # Write checkpoint immediately after processing (with file locking)
                checkpoint_file = checkpoint_dir / f"{cve_id}.json"
                write_checkpoint_atomic(checkpoint_file, cve_data)
                logging.debug(f"💾 Checkpointed {cve_id} ({idx}/{len(cves_to_process)})")

            except Exception as e:
                error_msg = f"Failed extracting {cve_id} from {commit_hash}: {e}"
                logging.warning(f"⚠️  {error_msg}")
                errors.append({
                    'cve_id': cve_id,
                    'commit_hash': commit_hash,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                })

        # Consolidate all checkpoints (existing + newly processed) into final file
        all_results = list(existing_checkpoints.values()) + results
        chunks_dir.mkdir(parents=True, exist_ok=True)
        with open(repo_file_path, 'w') as f:
            for result in all_results:
                f.write(json.dumps(result) + '\n')

        # Cleanup checkpoint directory after successful consolidation
        shutil.rmtree(checkpoint_dir, ignore_errors=True)

        total_processed = len(existing_checkpoints) + len(results)
        logging.info(f"✅ Completed {repo_url}: {total_processed}/{cve_fixes_length} CVEs extracted")

        return {
            'success': True,
            'repo_url': repo_url,
            'cves_processed': len(results),
            'cves_failed': len(errors),
            'results': results,
            'errors': errors,
            'skipped': False
        }

    except Exception as e:
        error_msg = f"Repository clone/processing failed for {repo_url}: {e}"
        logging.error(f"❌ {error_msg}")

        return {
            'success': False,
            'repo_url': repo_url,
            'cves_processed': 0,
            'cves_failed': len(cve_fixes),
            'results': [],
            'errors': [{
                'repo_url': repo_url,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'affects_cves': [rec['cve_id'] for rec in cve_fixes]
            }],
            'skipped': False
        }

    finally:
        # Cleanup working directory
        if work_dir_path.exists():
            logging.info(f"🧹 Cleaning up: {temp_dir}")
            shutil.rmtree(work_dir_path, ignore_errors=True)


def process_large_repository_with_cve_parallelism(
    repo_url: str,
    cve_fixes: List[Dict[str, Any]],
    git_timeout: int,
    work_repos_dir: Path,
    output_dir: Path,
    max_workers: int
) -> Dict[str, Any]:
    """
    Process large repository with CVE-level parallelism using shared clone.

    For repos with many CVEs, clone once then process CVEs in parallel using
    multiple workers. Each worker operates on the same clone with git handling
    internal locking for concurrent operations.

    Args:
        repo_url: Git repository URL
        cve_fixes: List of CVE fix records for this repo
        git_timeout: Timeout in seconds for Git operations
        work_repos_dir: Directory for working Git repositories
        output_dir: Output directory for chunk files
        max_workers: Number of parallel workers for CVE processing

    Returns:
        Dictionary with processing results (same format as process_repository_cves)
    """
    cve_fixes_length = len(cve_fixes)
    logging.info(f"🔧 Processing LARGE repository with CVE parallelism: {repo_url} ({cve_fixes_length} CVEs)")

    # Check if already processed
    repo_filename = get_repo_filename(repo_url)
    chunks_dir = output_dir / "completed_chunks"
    repo_file_path = chunks_dir / repo_filename

    if repo_file_path.exists():
        logging.info(f"✅ Repo already processed: {repo_url} (skipping)")
        return {
            'success': True,
            'repo_url': repo_url,
            'cves_processed': cve_fixes_length,
            'cves_failed': 0,
            'results': [],
            'errors': [],
            'skipped': True
        }

    # Per-CVE checkpoint directory for incremental progress
    checkpoint_dir = chunks_dir / f"{Path(repo_filename).stem}_cves"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Load already-processed CVEs from checkpoint directory
    processed_cve_ids = set()
    existing_checkpoints = {}

    if checkpoint_dir.exists():
        for checkpoint_file in checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    cve_data = json.load(f)
                    cve_id = cve_data.get('cve_id')
                    if cve_id:
                        processed_cve_ids.add(cve_id)
                        existing_checkpoints[cve_id] = cve_data
            except Exception as e:
                logging.warning(f"⚠️  Failed to load checkpoint {checkpoint_file.name}: {e}")

    # Filter out already-processed CVEs
    cves_to_process = [cve for cve in cve_fixes if cve['cve_id'] not in processed_cve_ids]
    cves_to_process_length = len(cves_to_process)

    if processed_cve_ids:
        logging.info(f"📋 Found {len(processed_cve_ids)} already-processed CVEs, {cves_to_process_length} remaining")

    # If all CVEs already processed, consolidate and return
    if not cves_to_process:
        logging.info(f"✅ All CVEs already checkpointed for {repo_url}, consolidating...")
        results = list(existing_checkpoints.values())

        # Write consolidated file
        chunks_dir.mkdir(parents=True, exist_ok=True)
        with open(repo_file_path, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + '\n')

        # Cleanup checkpoint directory
        shutil.rmtree(checkpoint_dir, ignore_errors=True)

        return {
            'success': True,
            'repo_url': repo_url,
            'cves_processed': len(results),
            'cves_failed': 0,
            'results': [],
            'errors': [],
            'skipped': True
        }

    # Create working directory with consistent hash-based naming
    repo_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
    work_dir_name = f"repo_{repo_hash}"
    work_dir_path = work_repos_dir / work_dir_name
    temp_dir = str(work_dir_path)

    if work_dir_path.exists():
        shutil.rmtree(work_dir_path)
    os.makedirs(temp_dir, exist_ok=True)

    errors = []

    try:
        # Clone repository once for all CVEs using partial clone
        # --filter=blob:none downloads all commits/trees but fetches blobs on-demand
        # This allows proper git gc deduplication while minimizing initial clone size
        logging.info(f"🔄 Cloning {repo_url} (partial clone: commits + trees only)...")

        def clone_repo():
            subprocess.run(
                ['git', 'clone', '--filter=blob:none', repo_url, temp_dir],
                check=True,
                capture_output=True,
                text=True,
                timeout=git_timeout,
                env=get_git_env()
            )

        retry_with_backoff(clone_repo, max_retries=3)
        logging.info(f"✅ Cloned repository (blobs will be fetched on-demand)")

        # PRE-FETCH PHASE: Fetch all commits in batches to optimize storage
        failed_fetches = prefetch_commits_in_batches(
            repo_dir=temp_dir,
            cves_to_process=cves_to_process,
            git_timeout=git_timeout,
            batch_size=50,
            gc_interval=250
        )

        # Run final aggressive gc after all fetches (allow 20 min for large repos)
        logging.info("🧹 Running final git gc to consolidate pack files...")
        run_git_gc(temp_dir, aggressive=True, timeout=1200)

        logging.info(f"⚡ Processing {cves_to_process_length} CVEs with {max_workers} workers (fetch-free)...")

        # Process CVEs in parallel using thread pool
        results_count = 0
        errors_count = 0

        def process_single_cve(cve_record):
            """Process a single CVE from the shared clone (assumes already fetched)."""
            commit_hash = cve_record['hash']
            cve_id = cve_record['cve_id']

            try:
                # Try extraction first (commit should already be fetched)
                try:
                    cve_data = extract_commit_data(temp_dir, commit_hash, cve_record, git_timeout)

                except subprocess.CalledProcessError as e:
                    # Commit not available, fetch individually and retry
                    if commit_hash in failed_fetches or 'unknown revision' in str(e).lower():
                        logging.warning(f"⚠️  Commit {commit_hash} not available for {cve_id}, fetching...")

                        def fetch_commit():
                            subprocess.run(
                                ['git', 'fetch', 'origin', commit_hash],
                                cwd=temp_dir,
                                check=True,
                                capture_output=True,
                                text=True,
                                timeout=git_timeout,
                                env=get_git_env()
                            )

                        retry_with_backoff(fetch_commit, max_retries=2)
                        cve_data = extract_commit_data(temp_dir, commit_hash, cve_record, git_timeout)
                    else:
                        # Different error, re-raise
                        raise

                # Extract commit data (should work now)
                # cve_data already set above

                # Write checkpoint immediately after processing (with file locking)
                checkpoint_file = checkpoint_dir / f"{cve_id}.json"
                write_checkpoint_atomic(checkpoint_file, cve_data)

                return {'success': True, 'cve_id': cve_id, 'data': cve_data}

            except Exception as e:
                error_msg = f"Failed extracting {cve_id} from {commit_hash}: {e}"
                logging.warning(f"⚠️  {error_msg}")
                return {
                    'success': False,
                    'cve_id': cve_id,
                    'error': {
                        'cve_id': cve_id,
                        'commit_hash': commit_hash,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                }

        # Submit all CVE processing tasks to thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as cve_executor:
            futures = [cve_executor.submit(process_single_cve, cve) for cve in cves_to_process]

            # Wait for all CVEs to complete with progress logging
            for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                result = future.result()

                if result['success']:
                    results_count += 1
                else:
                    errors_count += 1
                    errors.append(result['error'])

                # Log progress every 50 CVEs
                if idx % 50 == 0:
                    progress_pct = idx / cves_to_process_length * 100
                    logging.info(f"   Progress: {idx}/{cves_to_process_length} CVEs ({progress_pct:.1f}%)")

        # Consolidate all checkpoints (existing + newly processed) into final file
        all_results = list(existing_checkpoints.values())

        # Load newly processed checkpoints
        for checkpoint_file in checkpoint_dir.glob("*.json"):
            cve_id = checkpoint_file.stem
            if cve_id not in existing_checkpoints:  # Only load new ones
                try:
                    with open(checkpoint_file, 'r') as f:
                        all_results.append(json.load(f))
                except Exception as e:
                    logging.warning(f"⚠️  Failed to load checkpoint {checkpoint_file.name} during consolidation: {e}")

        chunks_dir.mkdir(parents=True, exist_ok=True)
        with open(repo_file_path, 'w') as f:
            for result in all_results:
                f.write(json.dumps(result) + '\n')

        # Cleanup checkpoint directory after successful consolidation
        shutil.rmtree(checkpoint_dir, ignore_errors=True)

        total_processed = len(existing_checkpoints) + results_count
        logging.info(f"✅ Completed {repo_url}: {total_processed}/{cve_fixes_length} CVEs extracted")

        return {
            'success': True,
            'repo_url': repo_url,
            'cves_processed': results_count,
            'cves_failed': errors_count,
            'results': [],  # Results already written to checkpoints
            'errors': errors,
            'skipped': False
        }

    except Exception as e:
        error_msg = f"Repository clone/processing failed for {repo_url}: {e}"
        logging.error(f"❌ {error_msg}")

        return {
            'success': False,
            'repo_url': repo_url,
            'cves_processed': 0,
            'cves_failed': len(cve_fixes),
            'results': [],
            'errors': [{
                'repo_url': repo_url,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'affects_cves': [rec['cve_id'] for rec in cve_fixes]
            }],
            'skipped': False
        }

    finally:
        # Log .git folder size before cleanup (to verify storage optimization)
        if work_dir_path.exists():
            git_dir = work_dir_path / ".git"
            if git_dir.exists():
                try:
                    # Calculate .git folder size
                    git_size_bytes = sum(f.stat().st_size for f in git_dir.rglob('*') if f.is_file())
                    git_size_mb = git_size_bytes / (1024 * 1024)
                    logging.info(f"📦 .git folder size: {git_size_mb:.1f} MB (before cleanup)")
                except Exception as e:
                    logging.debug(f"Could not calculate .git size: {e}")

            # Cleanup working directory
            logging.info(f"🧹 Cleaning up: {temp_dir}")
            shutil.rmtree(work_dir_path, ignore_errors=True)


def extract_commit_data(
    repo_dir: str,
    commit_hash: str,
    cve_metadata: Dict[str, Any],
    git_timeout: int
) -> Dict[str, Any]:
    """
    Extract commit data from an already-cloned repository.

    This is the core extraction logic separated from cloning.

    Args:
        repo_dir: Path to cloned repository
        commit_hash: Commit hash to extract
        cve_metadata: CVE/CWE metadata from database
        git_timeout: Timeout for git commands

    Returns:
        Dictionary with comprehensive commit data + CVE metadata
    """
    # Get commit message and date
    logging.debug(f"🔍 Extracting data for commit {commit_hash}...")
    commit_info_process = subprocess.run(
        ['git', 'show', '-s', '--format=%B%n%ci', commit_hash],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        timeout=60,
        env=get_git_env()
    )
    commit_info = safe_decode(commit_info_process.stdout).strip().split('\n')
    commit_message = "\n".join(commit_info[:-1])
    commit_date = commit_info[-1]

    # Get version tag
    try:
        logging.debug(f"🔍 Getting version tag for commit {commit_hash}...")
        version_process = subprocess.run(
            ['git', 'describe', '--tags', '--always', commit_hash],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            timeout=30,
            env=get_git_env()
        )
        version_tag = safe_decode(version_process.stdout).strip()
    except subprocess.CalledProcessError:
        version_tag = None

    # Get diff output
    logging.debug(f"🔍 Getting diff output for commit {commit_hash}...")
    diff_process = subprocess.run(
        ['git', 'show', '--format=', commit_hash],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        timeout=60,
        env=get_git_env()
    )
    diff_output = safe_decode(diff_process.stdout)

    # Get diff with enhanced context
    logging.debug(f"🔍 Getting diff with context for commit {commit_hash}...")
    diff_context_process = subprocess.run(
        ['git', 'show', '--format=', '-U5', commit_hash],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        timeout=60,
        env=get_git_env()
    )
    diff_with_context = safe_decode(diff_context_process.stdout)

    # Get diff stats per file
    logging.debug(f"🔍 Getting diff stats for commit {commit_hash}...")
    diff_stats_process = subprocess.run(
        ['git', 'show', '--numstat', '--format=', commit_hash],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        timeout=60,
        env=get_git_env()
    )
    diff_stats_output = safe_decode(diff_stats_process.stdout)

    # Parse diff stats into dictionary
    diff_stats = {}
    for line in diff_stats_output.strip().split('\n'):
        if line:
            parts = line.split('\t')
            if len(parts) == 3:
                added, deleted, filename = parts
                diff_stats[filename] = {
                    'lines_added': int(added) if added != '-' else 0,
                    'lines_deleted': int(deleted) if deleted != '-' else 0
                }

    # Get repository statistics
    try:
        # Total files in repo
        logging.debug(f"🔍 Getting total files and commits in repository {repo_dir}...")
        files_count_process = subprocess.run(
            ['git', 'ls-files'],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            timeout=30,
            env=get_git_env()
        )
        repo_total_files = len(safe_decode(files_count_process.stdout).strip().split('\n'))

        # Total commits in repo (approximate from current branch)
        logging.debug(f"🔍 Getting total commits in repository {repo_dir}...")
        commits_count_process = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            timeout=30,
            env=get_git_env()
        )
        repo_total_commits = int(safe_decode(commits_count_process.stdout).strip())
    except subprocess.CalledProcessError:
        repo_total_files = None
        repo_total_commits = None

    # Get file paths from diff
    file_paths = [
        line.split(' b/')[-1]
        for line in diff_output.split('\n')
        if line.startswith('+++ b/')
    ]

    # Detect language from file extensions
    language = 'Unknown'
    if file_paths:
        extensions = [Path(fp).suffix for fp in file_paths if fp]
        if extensions:
            most_common_ext = max(set(extensions), key=extensions.count)
            LANG_MAP = {
                # Web
                '.js': 'JavaScript',
                '.ts': 'TypeScript',
                '.html': 'HTML',
                '.css': 'CSS',
                '.php': 'PHP',
                '.rb': 'Ruby',
                '.erb': 'Ruby',
                # Backend
                '.py': 'Python',
                '.java': 'Java',
                '.kt': 'Kotlin',
                '.go': 'Go',
                '.rs': 'Rust',
                '.cs': 'C#',
                '.fs': 'F#',
                '.scala': 'Scala',
                '.swift': 'Swift',
                # C/C++
                '.c': 'C',
                '.h': 'C',
                '.cpp': 'C++',
                '.hpp': 'C++',
                '.cc': 'C++',
                '.hh': 'C++',
                # Shell
                '.sh': 'Shell',
                '.bash': 'Shell',
                # Other
                '.pl': 'Perl',
                '.pm': 'Perl',
                '.lua': 'Lua',
                '.r': 'R',
                '.m': 'Objective-C',
                '.mm': 'Objective-C++',
                '.sql': 'SQL',
                '.xml': 'XML',
                '.json': 'JSON',
                '.yaml': 'YAML',
                '.yml': 'YAML',
                '.md': 'Markdown',
            }
            language = LANG_MAP.get(most_common_ext, 'Other')

    # Parse diff to separate vulnerable and fixed code
    vulnerable_code = []
    fixed_code = []
    for line in diff_output.split('\n'):
        if line.startswith('-') and not line.startswith('---'):
            vulnerable_code.append(line[1:])
        elif line.startswith('+') and not line.startswith('+++'):
            fixed_code.append(line[1:])

    # Combine all data
    result = {
        # Core identifiers (from cve_metadata)
        'cve_id': cve_metadata.get('cve_id'),
        'hash': commit_hash,
        'repo_url': cve_metadata.get('repo_url'),

        # CVE metadata (from database)
        'cve_description': cve_metadata.get('cve_description'),
        'cvss2_base_score': cve_metadata.get('cvss2_base_score'),
        'cvss3_base_score': cve_metadata.get('cvss3_base_score'),
        'published_date': cve_metadata.get('published_date'),
        'severity': cve_metadata.get('severity'),

        # CWE classification (from database)
        'cwe_id': cve_metadata.get('cwe_id'),
        'cwe_name': cve_metadata.get('cwe_name'),
        'cwe_description': cve_metadata.get('cwe_description'),

        # Git commit metadata
        'commit_message': commit_message,
        'commit_date': commit_date,
        'version_tag': version_tag,

        # Repository metadata
        'repo_total_files': repo_total_files,
        'repo_total_commits': repo_total_commits,

        # File changes
        'file_paths': file_paths,
        'language': language,
        'diff_stats': diff_stats,
        'diff_with_context': diff_with_context,

        # Code changes
        'vulnerable_code': "\n".join(vulnerable_code),
        'fixed_code': "\n".join(fixed_code),

        # Security annotations
        'security_keywords': extract_security_keywords(commit_message),
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced CVEfixes dataset extractor with repository-based processing (64% more efficient)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="cvefixes_output",
        help="Output directory for chunks and final Parquet (default: cvefixes_output)"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to CVEfixes.db SQLite database (default: auto-detect from script location)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count(),
        help="Number of parallel workers (default: CPU count)"
    )
    parser.add_argument(
        "--git-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for Git operations (default: 300)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of CVE records to load (for testing)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug output"
    )
    parser.add_argument(
        "--large-repo-threshold",
        type=int,
        default=100,
        help="CVE count threshold for large repo processing (default: 100)"
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
        "--keep-db-zip",
        action="store_true",
        help="Keep downloaded ZIP file after extraction (default: delete to save space)"
    )
    args = parser.parse_args()

    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("🐛 Debug logging enabled")

    # Ensure CVEfixes dataset is available (auto-download from Zenodo if needed)
    dataset_base_dir = Path(__file__).parent / "data/public_datasets"
    try:
        cvefixes_dir = ensure_cvefixes_dataset_available(
            dataset_dir=dataset_base_dir,
            keep_db_zip=args.keep_db_zip
        )
    except Exception as e:
        logging.error(f"❌ Failed to ensure dataset availability: {e}")
        logging.error("   Please check your internet connection or download manually from:")
        logging.error("   https://zenodo.org/records/13118970")
        return

    # Auto-detect database path if not specified
    if args.db_path is None:
        args.db_path = cvefixes_dir / "Data" / "CVEfixes.db"

    logging.info("🚀 Starting Repository-Based CVEfixes Data Extraction Pipeline")
    logging.info(f"   Database: {args.db_path}")
    logging.info(f"   Output directory: {args.output_dir}")
    logging.info(f"   Workers: {args.workers}")
    logging.info(f"   Git timeout: {args.git_timeout}s")
    if args.limit:
        logging.info(f"   ⚠️  LIMIT: {args.limit} CVE records (testing mode)")

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Create working directory
    work_repos_dir = args.output_dir / "work_repos"
    work_repos_dir.mkdir(parents=True, exist_ok=True)

    logging.info(f"   Working repos: {work_repos_dir}")

    # Save extraction metadata
    chunks_dir = args.output_dir / "completed_chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = args.output_dir / "metadata.json"

    with open(metadata_file, 'w') as f:
        json.dump({
            'extraction_start': datetime.now().isoformat(),
            'database_path': str(args.db_path),
            'workers': args.workers,
            'git_timeout': args.git_timeout,
            'limit': args.limit,
            'approach': 'repository-based (1 repo = 1 file)'
        }, f, indent=2)

    # Load CVE data grouped by repository
    repos_data = load_cvefixes_from_db(args.db_path, limit=args.limit)

    if not repos_data:
        logging.error("No repository data loaded from database. Exiting.")
        return

    # Count total CVEs for progress tracking
    total_cves = sum(len(fixes) for fixes in repos_data.values())
    logging.info(f"📊 Total CVEs to extract: {total_cves}")

    # Filter out already processed repositories
    repos_to_process = {}
    skipped_repos = 0

    for repo_url, cve_fixes in repos_data.items():
        repo_filename = get_repo_filename(repo_url)
        repo_file_path = chunks_dir / repo_filename

        if not repo_file_path.exists():
            repos_to_process[repo_url] = cve_fixes
        else:
            skipped_repos += 1

    # Check if final Parquet already exists (prioritize this check)
    parquet_file = args.output_dir / 'cvefixes_dataset.parquet'

    if parquet_file.exists():
        # Parquet already assembled, check what to do
        logging.info(f"✅ Parquet file already exists: {parquet_file}")

        # If uploading to HuggingFace, skip assembly and go straight to upload
        if args.upload_to_hf:
            logging.info(f"📤 Skipping Parquet assembly, proceeding directly to HuggingFace upload...")
            # Load existing Parquet once
            df = pd.read_parquet(parquet_file)

            try:
                hf_url = upload_cvefixes_to_huggingface(
                    df=df,
                    parquet_file=parquet_file,
                    output_dir=args.output_dir,
                    repo_id=args.upload_to_hf,
                    private=args.hf_private,
                    token=args.hf_token
                )
                logging.info(f"✅ Dataset available at: {hf_url}")
            except Exception as e:
                logging.error(f"❌ Failed to upload to HuggingFace: {e}")

            return
        else:
            logging.info("   Parquet file already exists. Use --upload-to-hf to upload to HuggingFace.")
            return

    # Parquet doesn't exist - check if we need to assemble from completed chunks
    if not repos_to_process:
        # All repositories processed, need to assemble from chunks
        logging.info("✅ All repositories have already been processed. Assembling final dataset...")
        checkpointer = ChunkedCheckpointer(args.output_dir, chunk_size=100)
        checkpointer.assemble_parquet()
        return

    logging.info(f"📋 Processing {len(repos_to_process)} repositories ({skipped_repos} already completed)")

    # Separate small and large repositories based on threshold
    small_repos = {}
    large_repos = {}

    for repo_url, cve_fixes in repos_to_process.items():
        if len(cve_fixes) >= args.large_repo_threshold:
            large_repos[repo_url] = cve_fixes
        else:
            small_repos[repo_url] = cve_fixes

    logging.info(f"   Small repos (<{args.large_repo_threshold} CVEs): {len(small_repos)}")
    logging.info(f"   Large repos (≥{args.large_repo_threshold} CVEs): {len(large_repos)}")

    total_repos = len(repos_to_process)
    processed_repos = 0
    failed_repos = 0
    total_cves_processed = 0
    total_cves_failed = 0

    # Create error log file
    error_file = args.output_dir / "errors.jsonl"

    # PHASE 1: Process small repositories in parallel (existing approach)
    if small_repos:
        logging.info(f"\n📦 PHASE 1: Processing {len(small_repos)} small repositories in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Submit all small repository processing tasks
            future_to_repo = {
                executor.submit(
                    process_repository_cves,
                    repo_url,
                    cve_fixes,
                    args.git_timeout,
                    work_repos_dir,
                    args.output_dir
                ): repo_url
                for repo_url, cve_fixes in small_repos.items()
            }

        # Process completed tasks
        for future in concurrent.futures.as_completed(future_to_repo):
            repo_url = future_to_repo[future]

            try:
                result = future.result()

                if result['success'] and not result.get('skipped', False):
                    processed_repos += 1
                    total_cves_processed += result['cves_processed']
                    total_cves_failed += result['cves_failed']

                    # Log any per-CVE errors within the repo
                    if result['errors']:
                        with open(error_file, 'a') as f:
                            for error in result['errors']:
                                f.write(json.dumps({
                                    'timestamp': datetime.now().isoformat(),
                                    'repo_url': repo_url,
                                    **error
                                }) + '\n')

                elif not result['success']:
                    failed_repos += 1
                    total_cves_failed += result['cves_failed']

                    # Log repo-level failure
                    with open(error_file, 'a') as f:
                        for error in result['errors']:
                            f.write(json.dumps({
                                'timestamp': datetime.now().isoformat(),
                                **error
                            }) + '\n')

                # Log progress every 5 repos
                if processed_repos % 5 == 0:
                    progress_pct = (processed_repos + failed_repos) / total_repos * 100
                    logging.info(
                        f"Progress: {processed_repos + failed_repos}/{total_repos} repos "
                        f"({progress_pct:.1f}%) | CVEs: {total_cves_processed} extracted, {total_cves_failed} failed"
                    )

            except Exception as exc:
                failed_repos += 1
                logging.error(f"❌ Unexpected error processing {repo_url}: {exc}")

                with open(error_file, 'a') as f:
                    f.write(json.dumps({
                        'timestamp': datetime.now().isoformat(),
                        'repo_url': repo_url,
                        'error_type': type(exc).__name__,
                        'error_message': str(exc),
                    }) + '\n')

    # PHASE 2: Process large repositories sequentially with CVE-level parallelism
    if large_repos:
        logging.info(f"\n🔧 PHASE 2: Processing {len(large_repos)} large repositories with CVE parallelism...")
        for repo_url, cve_fixes in large_repos.items():
            logging.info(f"\n{'='*60}")
            try:
                result = process_large_repository_with_cve_parallelism(
                    repo_url,
                    cve_fixes,
                    args.git_timeout,
                    work_repos_dir,
                    args.output_dir,
                    args.workers  # Use all workers for CVE parallelism
                )

                if result['success'] and not result.get('skipped', False):
                    processed_repos += 1
                    total_cves_processed += result['cves_processed']
                    total_cves_failed += result['cves_failed']

                    # Log any per-CVE errors within the repo
                    if result['errors']:
                        with open(error_file, 'a') as f:
                            for error in result['errors']:
                                f.write(json.dumps({
                                    'timestamp': datetime.now().isoformat(),
                                    'repo_url': repo_url,
                                    **error
                                }) + '\n')

                elif not result['success']:
                    failed_repos += 1
                    total_cves_failed += result['cves_failed']

                    # Log repo-level failure
                    with open(error_file, 'a') as f:
                        for error in result['errors']:
                            f.write(json.dumps({
                                'timestamp': datetime.now().isoformat(),
                                **error
                            }) + '\n')

                # Log progress
                progress_pct = (processed_repos + failed_repos) / total_repos * 100
                logging.info(
                    f"\n📊 Overall Progress: {processed_repos + failed_repos}/{total_repos} repos "
                    f"({progress_pct:.1f}%) | CVEs: {total_cves_processed} extracted, {total_cves_failed} failed"
                )

            except Exception as exc:
                failed_repos += 1
                logging.error(f"❌ Unexpected error processing large repo {repo_url}: {exc}")

                with open(error_file, 'a') as f:
                    f.write(json.dumps({
                        'timestamp': datetime.now().isoformat(),
                        'repo_url': repo_url,
                        'error_type': type(exc).__name__,
                        'error_message': str(exc),
                    }) + '\n')

    # Final statistics
    logging.info("\n" + "=" * 80)
    logging.info("✅ EXTRACTION COMPLETE")
    logging.info(f"   Repositories processed: {processed_repos}")
    logging.info(f"   Repositories failed: {failed_repos}")
    logging.info(f"   Total repositories (including previous runs): {skipped_repos + processed_repos}")
    logging.info(f"   CVEs extracted: {total_cves_processed}")
    logging.info(f"   CVEs failed: {total_cves_failed}")
    logging.info("=" * 80)

    # Assemble final Parquet dataset
    checkpointer = ChunkedCheckpointer(args.output_dir, chunk_size=100)
    df = checkpointer.assemble_parquet()

    logging.info(f"🎉 All done! Results saved to: {args.output_dir}")
    logging.info(f"   - Repo chunks: {chunks_dir} ({len(list(chunks_dir.glob('repo_*.jsonl')))} files)")
    logging.info(f"   - Errors: {error_file}")
    logging.info(f"   - Final dataset: {args.output_dir / 'cvefixes_dataset.parquet'}")

    # Upload to HuggingFace if requested
    if args.upload_to_hf and df is not None:
        try:
            hf_url = upload_cvefixes_to_huggingface(
                df=df,
                parquet_file=args.output_dir / 'cvefixes_dataset.parquet',
                output_dir=args.output_dir,
                repo_id=args.upload_to_hf,
                private=args.hf_private,
                token=args.hf_token
            )
            logging.info(f"✅ Dataset available at: {hf_url}")
        except Exception as e:
            logging.error(f"❌ Failed to upload to HuggingFace: {e}")


if __name__ == "__main__":
    main()
