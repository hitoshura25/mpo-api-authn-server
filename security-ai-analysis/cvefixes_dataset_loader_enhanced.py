#!/usr/bin/env python3
"""
Enhanced CVEfixes Dataset Loader

Extracts comprehensive vulnerability data from CVEfixes v1.0.8 using:
- SQLite3 database queries (instead of SQL regex parsing)
- Repository-based processing (1 repo = 1 file, 64% more efficient)
- Enhanced Git metadata extraction
- Robust error handling with UTF-8 fallback and retries

Usage:
    # One-time: Convert SQL dump to SQLite database
    gzcat data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes_v1.0.8.sql.gz | \\
    sqlite3 data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes.db

    # Run extraction
    python cvefixes_dataset_loader_enhanced.py \\
        --output-dir cvefixes_output \\
        --workers 8 \\
        --limit 10  # For testing

    # Run with debug output (verbose mode)
    python cvefixes_dataset_loader_enhanced.py \\
        --output-dir cvefixes_output \\
        --verbose  # Or -v for short
"""

import logging
import subprocess
import shutil
import time
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
import pandas as pd
import argparse
import os
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

                # Write checkpoint immediately after processing
                checkpoint_file = checkpoint_dir / f"{cve_id}.json"
                with open(checkpoint_file, 'w') as f:
                    json.dump(cve_data, f)
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
    args = parser.parse_args()

    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("🐛 Debug logging enabled")

    # Auto-detect database path if not specified
    if args.db_path is None:
        args.db_path = (
            Path(__file__).parent /
            "data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes.db"
        )

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

    if not repos_to_process:
        logging.info("✅ All repositories have already been processed. Assembling final dataset...")
        # Assemble parquet from existing chunks
        checkpointer = ChunkedCheckpointer(args.output_dir, chunk_size=100)
        checkpointer.assemble_parquet()
        return

    logging.info(f"📋 Processing {len(repos_to_process)} repositories ({skipped_repos} already completed)")

    total_repos = len(repos_to_process)
    processed_repos = 0
    failed_repos = 0
    total_cves_processed = 0
    total_cves_failed = 0

    # Create error log file
    error_file = args.output_dir / "errors.jsonl"

    # Process repositories in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all repository processing tasks
        future_to_repo = {
            executor.submit(
                process_repository_cves,
                repo_url,
                cve_fixes,
                args.git_timeout,
                work_repos_dir,
                args.output_dir
            ): repo_url
            for repo_url, cve_fixes in repos_to_process.items()
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

    # Final statistics
    logging.info("=" * 80)
    logging.info("✅ EXTRACTION COMPLETE")
    logging.info(f"   Repositories processed: {processed_repos}")
    logging.info(f"   Repositories failed: {failed_repos}")
    logging.info(f"   Total repositories (including previous runs): {skipped_repos + processed_repos}")
    logging.info(f"   CVEs extracted: {total_cves_processed}")
    logging.info(f"   CVEs failed: {total_cves_failed}")
    logging.info("=" * 80)

    # Assemble final Parquet dataset
    logging.info("📊 Assembling final Parquet dataset from all repository chunks...")
    checkpointer = ChunkedCheckpointer(args.output_dir, chunk_size=100)
    checkpointer.assemble_parquet()

    logging.info(f"🎉 All done! Results saved to: {args.output_dir}")
    logging.info(f"   - Repo chunks: {chunks_dir} ({len(list(chunks_dir.glob('repo_*.jsonl')))} files)")
    logging.info(f"   - Errors: {error_file}")
    logging.info(f"   - Final dataset: {args.output_dir / 'cvefixes_dataset.parquet'}")


if __name__ == "__main__":
    main()
