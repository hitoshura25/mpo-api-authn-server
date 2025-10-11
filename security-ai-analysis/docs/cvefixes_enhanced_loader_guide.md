# Enhanced CVEfixes Dataset Loader Guide

## Overview

The enhanced CVEfixes dataset loader (`cvefixes_dataset_loader_enhanced.py`) provides comprehensive vulnerability data extraction with:

- **SQLite3 database queries** instead of SQL regex parsing
- **Chunked JSONL checkpointing** for granular resume capability
- **Enhanced Git metadata** extraction (author, version tags, repo stats)
- **Robust error handling** with UTF-8 fallback and exponential backoff retries

## Quick Start

### 1. One-Time Setup: Create SQLite Database

The CVEfixes data comes as a compressed SQL dump. Convert it to SQLite database:

```bash
cd security-ai-analysis

# If you have the gzipped file:
gzcat data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes_v1.0.8.sql.gz | \
    sqlite3 data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes.db

# If you have the uncompressed SQL file:
sqlite3 data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes.db < \
    data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes_v1.0.8.sql
```

**Time:** ~10 minutes for 48GB SQL file

### 2. Run Extraction (Test Mode)

Test with a small limit first:

```bash
python cvefixes_dataset_loader_enhanced.py \
    --output-dir test_cvefixes_output \
    --limit 10 \
    --workers 2
```

**Expected output:**
```
🚀 Starting Enhanced CVEfixes Data Extraction Pipeline
   Database: data/public_datasets/CVEfixes_v1.0.8/Data/CVEfixes.db
   Output directory: test_cvefixes_output
   Workers: 2
   Chunk size: 100
   ⚠️  LIMIT: 10 CVEs (testing mode)

Loading CVE data from SQLite database...
Loaded 10 CVE records from database
  Unique CVEs: 10
  Unique commits: 10
  Unique repositories: 8

📋 Processing 10 new CVEs (0 already completed)
Progress: 5/10 (50.0%) | Success: 5, Failed: 0
Progress: 10/10 (100.0%) | Success: 10, Failed: 0

💾 Flushed chunk 0 with 10 records

✅ EXTRACTION COMPLETE
   Successfully processed: 10
   Failed: 0
   Total completed: 10

📊 Assembling final Parquet dataset from all chunks...
✅ Assembled 10 records into test_cvefixes_output/cvefixes_dataset.parquet
   Columns: ['cve_id', 'hash', 'repo_url', 'cve_description', ...]
   File size: 0.1 MB
```

### 3. Run Full Extraction

For production run with all 12K+ CVEs:

```bash
python cvefixes_dataset_loader_enhanced.py \
    --output-dir cvefixes_full_output \
    --workers 8 \
    --chunk-size 100 \
    --git-timeout 300
```

**Estimated time:** 12-24 hours (same as original, but with 10x more data)

## Output Structure

```
output_dir/
├── completed_chunks/
│   ├── chunk_0000.jsonl  # CVEs 0-99 (one JSON per line)
│   ├── chunk_0001.jsonl  # CVEs 100-199
│   ├── chunk_0002.jsonl  # CVEs 200-299
│   └── ...               # ~121 chunks for 12K CVEs
├── errors.jsonl          # Failed extractions (one JSON per line)
├── progress.json         # Current extraction progress
├── metadata.json         # Extraction run metadata
└── cvefixes_dataset.parquet  # Final assembled dataset
```

### Chunk File Format (JSONL)

Each line in `chunk_XXXX.jsonl` is a complete JSON record:

```jsonl
{"cve_id": "CVE-2024-00001", "hash": "abc123", "cve_description": "...", "vulnerable_code": "...", ...}
{"cve_id": "CVE-2024-00002", "hash": "def456", "cve_description": "...", "vulnerable_code": "...", ...}
```

### Error File Format

Each line in `errors.jsonl` contains error details:

```jsonl
{"timestamp": "2025-10-10T10:30:45", "cve_id": "CVE-2024-99999", "error_type": "TimeoutExpired", "error_message": "...", ...}
```

## Resume After Failure

The script automatically resumes from where it left off:

```bash
# Same command - will skip already completed CVEs
python cvefixes_dataset_loader_enhanced.py \
    --output-dir cvefixes_full_output \
    --workers 8
```

**How it works:**
1. Scans all `chunk_*.jsonl` files in `completed_chunks/`
2. Builds set of completed CVE IDs
3. Skips already processed CVEs
4. Continues from next unprocessed CVE

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--output-dir` | `cvefixes_output` | Output directory for chunks and final Parquet |
| `--db-path` | Auto-detect | Path to CVEfixes.db SQLite database |
| `--workers` | CPU count | Number of parallel worker threads |
| `--chunk-size` | 100 | Number of CVEs per JSONL chunk file |
| `--git-timeout` | 300 | Timeout in seconds for Git operations |
| `--limit` | None | Limit number of CVEs (for testing) |

## Data Schema

### Complete Record Structure

```python
{
    # Core identifiers
    'cve_id': 'CVE-2024-12345',
    'hash': 'abc123...',
    'repo_url': 'https://github.com/torvalds/linux',

    # CVE metadata (from SQLite cve table)
    'cve_description': 'SQL injection vulnerability in...',
    'cvss2_base_score': 7.5,
    'cvss3_base_score': 8.1,
    'severity': 'HIGH',
    'published_date': '2024-01-15',

    # CWE classification (from SQLite cwe table)
    'cwe_id': 'CWE-89',
    'cwe_name': 'SQL Injection',
    'cwe_description': 'Improper neutralization of special elements...',

    # Git commit metadata
    'commit_message': 'Fix SQL injection in user login',
    'commit_date': '2024-01-10 14:32:15 +0000',
    'author_name': 'John Doe',           # NEW
    'author_email': 'john@example.com',   # NEW
    'version_tag': 'v2.3.1',              # NEW

    # Repository metadata
    'repo_total_files': 1234,             # NEW
    'repo_total_commits': 5678,           # NEW

    # File changes
    'file_paths': ['src/auth/login.c'],
    'language': 'C',
    'diff_stats': {                       # NEW
        'src/auth/login.c': {
            'lines_added': 15,
            'lines_deleted': 8
        }
    },
    'diff_with_context': '...',          # NEW (5 lines context)

    # Code changes
    'vulnerable_code': 'SELECT * FROM users WHERE name = "' + input + '"',
    'fixed_code': 'SELECT * FROM users WHERE name = ?',

    # Security annotations
    'security_keywords': ['validation', 'sanitization'],  # NEW
}
```

## Use Cases

### 1. OLMo Fine-Tuning Dataset

Filter for specific languages and vulnerability types:

```python
import pandas as pd

df = pd.read_parquet('cvefixes_dataset.parquet')

# Filter for Java/Kotlin vulnerabilities
df_training = df[df['language'].isin(['Java', 'Kotlin', 'JavaScript'])]

# Filter for specific CWE types
df_training = df_training[df_training['cwe_id'].isin(['CWE-79', 'CWE-89', 'CWE-20'])]

# Select relevant columns
df_training = df_training[['vulnerable_code', 'fixed_code', 'cwe_name', 'cve_description']]

df_training.to_parquet('olmo_training_dataset.parquet')
```

### 2. Security Research Analysis

Analyze CVE trends and severity distributions:

```python
# Severity distribution by programming language
severity_by_lang = df.groupby(['language', 'severity']).size().unstack(fill_value=0)

# Most common CWE types
cwe_counts = df.groupby('cwe_name').size().sort_values(ascending=False)

# Average CVSS scores by repository
cvss_by_repo = df.groupby('repo_url')['cvss3_base_score'].mean().sort_values(ascending=False)
```

### 3. Public Dataset Publication

Remove PII before publishing:

```python
# Remove author email for privacy
df_public = df.drop(columns=['author_email'])

df_public.to_parquet('cvefixes_public_dataset.parquet')
```

## Troubleshooting

### Error: "SQLite database not found"

**Solution:** Create the database first:
```bash
gzcat CVEfixes_v1.0.8.sql.gz | sqlite3 CVEfixes.db
```

### Error: "Git timeout"

**Solution:** Increase timeout:
```bash
python cvefixes_dataset_loader_enhanced.py --git-timeout 600
```

### Error: "UnicodeDecodeError"

**Solution:** The script automatically handles this with UTF-8 fallback. If you still see errors, check `errors.jsonl` for details.

### Resume not working

**Solution:** Check that `--output-dir` matches previous run exactly.

## Performance Tips

1. **Adjust workers:** More workers = faster, but higher memory usage
   ```bash
   --workers 16  # For machines with 16+ cores
   ```

2. **Larger chunks:** Fewer files, but less granular resume
   ```bash
   --chunk-size 500  # ~24 files instead of ~121
   ```

3. **Monitor progress:**
   ```bash
   # Watch progress.json in real-time
   watch -n 10 cat cvefixes_output/progress.json

   # Count completed CVEs
   jq '. | length' cvefixes_output/completed_chunks/*.jsonl | paste -sd+ | bc

   # Count errors
   wc -l cvefixes_output/errors.jsonl
   ```

## Comparison with Original Script

| Feature | Original (Gemini) | Enhanced |
|---------|------------------|----------|
| Data source | SQL regex parsing | SQLite queries |
| CVE metadata | ❌ Not extracted | ✅ Descriptions, CVSS, severity |
| CWE data | ❌ Not extracted | ✅ CWE names, descriptions |
| Author info | ❌ Not extracted | ✅ Name and email |
| Version tags | ❌ Not extracted | ✅ Git describe tags |
| Repo stats | ❌ Not extracted | ✅ File count, commit count |
| Checkpointing | Parquet every 100 commits | JSONL chunks (100 CVEs) |
| Resume granularity | Every 100 commits | Every CVE |
| File count | 1 Parquet | ~121 JSONL chunks |
| Error logging | Console only | Structured errors.jsonl |
| UTF-8 handling | errors='ignore' | UTF-8 → latin-1 → ignore |
| Retry logic | ❌ No retries | ✅ 3 retries with backoff |

## Credits

Based on the CVEfixes dataset:
- Paper: Bhandari et al., "CVEfixes: Automated Collection of Vulnerabilities and Their Fixes from Open-Source Software" (PROMISE '21)
- DOI: 10.5281/zenodo.4476563
- GitHub: https://github.com/secureIT-project/CVEfixes

Enhanced by AI-assisted development for the WebAuthn security fine-tuning project.
