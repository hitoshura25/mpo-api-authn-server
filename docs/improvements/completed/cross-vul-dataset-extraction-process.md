# CrossVul Dataset Extraction Process

**Date**: 2025-10-13
**Purpose**: Extract multi-language vulnerability/fix pairs from CrossVul dataset for Stage 1 sequential fine-tuning
**Status**: In Progress

---

## Overview

CrossVul is a cross-language vulnerability dataset containing **13,067 vulnerable/fixed code pairs** across **173 CWE categories** and **48+ programming languages**. This document describes how to extract and format this data for use in the sequential fine-tuning pipeline.

**Key Design Principle**: CrossVul script extracts RAW data → process_artifacts.py creates training chat messages

---

## Current State

### What Exists
- ✅ `crossvul_dataset_loader.py` - Initial extraction script (has bugs)
- ✅ Dataset downloaded to `data/crossvul_extraction/dataset_final_sorted/`
- ✅ Auto-download from Zenodo working (367 MB → 1.4 GB extracted)

### Current Issues
1. **❌ Language Detection Bug**: Script looks for file extensions (`.java`), but files have NO extensions
   - Example: `CWE-79/java/bad_1163_0` (no `.java` extension)
   - Result: Script finds 0 matching pairs

2. **❌ Wrong Output Format**: Creates train/val/test splits with chat messages
   - Should output: Single JSONL with raw vulnerability data
   - Reason: `process_artifacts.py` should create chat messages (separation of concerns)

---

## Dataset Structure

### Directory Organization
```
dataset_final_sorted/
├── CWE-79/                    # XSS vulnerabilities
│   ├── java/                  # Language subdirectory
│   │   ├── bad_1163_0         # Vulnerable code (NO extension!)
│   │   ├── good_1163_0        # Fixed code (NO extension!)
│   │   ├── bad_1164_0
│   │   ├── good_1164_0
│   │   └── ...
│   ├── py/                    # Python files
│   ├── js/                    # JavaScript files
│   └── ...
├── CWE-89/                    # SQL Injection
│   ├── java/
│   ├── py/
│   └── ...
├── CWE-119/                   # Buffer Overflow
└── ... (173 CWE categories total)
```

### File Naming Convention
- **Vulnerable**: `bad_<id>_<variant>`
- **Fixed**: `good_<id>_<variant>`
- **Pairing**: `bad_1163_0` matches `good_1163_0`
- **NO FILE EXTENSIONS**: Language detected from parent directory name

### Language Directories

**Common Languages**:
- `java/` - Java files
- `py/` - Python files
- `js/` - JavaScript files
- `go/` - Go files
- `rb/` - Ruby files
- `c/` - C files
- `cpp/` - C++ files
- `cs/` - C# files
- `php/` - PHP files

**Web/Config Languages**:
- `html/`, `htm/` - HTML
- `css/` - CSS
- `xml/` - XML
- `json/` - JSON
- `yaml/`, `yml/` - YAML

**Other**:
- `Other/` - Mixed/unknown languages (skip these)

---

## Required Output Format

### File: `crossvul_dataset.jsonl`

**One JSON object per line** (JSONL format):

```jsonl
{"cwe_id": "CWE-79", "cwe_description": "Cross-site Scripting (XSS) - Improper Neutralization of Input", "language": "java", "vulnerable_code": "... full content ...", "fixed_code": "... full content ...", "file_pair_id": "1163_0", "source": "crossvul", "language_dir": "java"}
{"cwe_id": "CWE-89", "cwe_description": "SQL Injection", "language": "python", "vulnerable_code": "...", "fixed_code": "...", "file_pair_id": "2045_1", "source": "crossvul", "language_dir": "py"}
```

### Field Descriptions

```python
{
    # CWE Classification
    "cwe_id": "CWE-79",                    # CWE identifier
    "cwe_description": "Cross-site Scripting (XSS) - Improper Neutralization of Input",

    # Language Information
    "language": "java",                    # Normalized language name
    "language_dir": "java",                # Original directory name

    # Vulnerability Data (RAW CODE)
    "vulnerable_code": "... full content of bad_1163_0 ...",
    "fixed_code": "... full content of good_1163_0 ...",

    # Identity & Metadata
    "file_pair_id": "1163_0",             # Unique identifier (from filename)
    "source": "crossvul"                  # Dataset source identifier
}
```

### Why This Format?

1. **Simple**: Just raw vulnerability/fix pairs, no formatting
2. **Flexible**: `process_artifacts.py` can create ANY prompt structure
3. **Reusable**: Can be loaded by different training pipelines
4. **Separation of Concerns**:
   - CrossVul script = data extraction
   - process_artifacts.py = training message creation

---

## Implementation Plan

### Phase 1: Fix Language Detection

**Problem**: Current code tries to detect file extensions, but files have none.

**Current Code** (WRONG):
```python
def detect_file_extension(filepath: Path) -> Optional[str]:
    """Detect file extension, handling files without extensions."""
    # Check for double extensions first (.test.php, .inc.php, etc.)
    suffixes = filepath.suffixes
    if len(suffixes) >= 2:
        double_ext = ''.join(suffixes[-2:])
        if double_ext in EXTENSION_TO_LANGUAGE:
            return double_ext

    # Single extension
    if filepath.suffix:
        return filepath.suffix

    # ❌ FAILS: Files like 'bad_1163_0' have NO suffix!
```

**New Code** (CORRECT):
```python
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
        # Add more mappings as needed
    }

    return DIRECTORY_TO_LANGUAGE.get(lang_dir.lower())
```

### Phase 2: Simplify Output Format

**Remove**:
- ❌ `create_training_example()` - No chat messages, just raw data
- ❌ `save_dataset_splits()` - No train/val/test splits

**Keep** (for HuggingFace upload):
- ✅ `create_dataset_card()` - Update for raw format description
- ✅ `upload_to_huggingface()` - Upload raw JSONL to share dataset

**New Function**:
```python
def create_raw_vulnerability_record(pair: Dict) -> Optional[Dict]:
    """
    Create a raw vulnerability record from a bad/good file pair.

    Args:
        pair: Dictionary with bad_file, good_file, CWE info, language

    Returns:
        Dictionary with raw vulnerability data (no chat formatting)
    """
    # Read vulnerable code
    vulnerable_code = read_file_safe(pair['bad_file'])
    if not vulnerable_code:
        return None

    # Read fixed code
    fixed_code = read_file_safe(pair['good_file'])
    if not fixed_code:
        return None

    # Skip if files are identical (data quality issue)
    if vulnerable_code.strip() == fixed_code.strip():
        logging.debug(f"Skipping identical files: {pair['file_id']}")
        return None

    # Skip if files are too short (likely not real vulnerability examples)
    if len(vulnerable_code.strip()) < 50 or len(fixed_code.strip()) < 50:
        logging.debug(f"Skipping short files: {pair['file_id']}")
        return None

    # Return RAW data record
    return {
        'cwe_id': pair['cwe_id'],
        'cwe_description': pair['cwe_description'],
        'language': pair['language'],
        'vulnerable_code': vulnerable_code,
        'fixed_code': fixed_code,
        'file_pair_id': pair['file_id'],
        'source': 'crossvul',
        'language_dir': pair['language_dir']
    }
```

### Phase 3: Update Main Logic

**New Main Flow**:
```python
def main():
    # 1. Download dataset if needed (existing logic - works)
    dataset_path = ensure_crossvul_dataset_available(...)

    # 2. Find all bad/good file pairs (fix language detection)
    pairs = find_matching_pairs(dataset_path, language_filter)

    # 3. Extract raw vulnerability records
    records = []
    for pair in pairs:
        record = create_raw_vulnerability_record(pair)
        if record:
            records.append(record)

    # 4. Save to single JSONL file
    output_file = output_dir / "crossvul_dataset.jsonl"
    with open(output_file, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    # 5. Log statistics
    logging.info(f"✅ Extracted {len(records)} vulnerability pairs")
    logging.info(f"   Output: {output_file}")
```

### Phase 4: Update CLI Arguments

**Simplify Arguments**:
```python
parser.add_argument(
    "--output-dir",
    type=Path,
    default=Path("data/public_datasets"),
    help="Output directory for crossvul_dataset.jsonl"
)

parser.add_argument(
    "--languages",
    nargs='+',
    default=None,
    help="Filter by languages (e.g., java python js go). Default: all"
)

parser.add_argument(
    "--limit",
    type=int,
    default=None,
    help="Limit number of pairs to process (for testing)"
)

# REMOVE: --train-ratio, --val-ratio, --test-ratio
```

---

## HuggingFace Upload

### Why Upload Raw Dataset?

1. **Public Sharing**: Share extracted dataset with community (save others 1-2 hours of extraction)
2. **Convenience**: `process_artifacts.py` can load directly from HuggingFace (no local extraction needed)
3. **Versioning**: Track dataset versions on HuggingFace
4. **Reproducibility**: Anyone can use exact same dataset

### Upload Flow

```python
def upload_to_huggingface(
    output_file: Path,  # crossvul_dataset.jsonl
    repo_id: str,
    private: bool,
    token: Optional[str],
    dataset_stats: Dict
) -> str:
    """Upload raw CrossVul dataset to HuggingFace."""
    from datasets import load_dataset
    from huggingface_hub import HfApi

    # Load as HuggingFace dataset (single split called 'train')
    dataset = load_dataset('json', data_files=str(output_file))

    logger.info(f"📦 Dataset loaded: {len(dataset['train'])} records")

    # Generate dataset card for raw format
    dataset_card = create_dataset_card(
        repo_id=repo_id,
        num_examples=dataset_stats['num_examples'],
        num_cwes=dataset_stats['num_cwes'],
        languages=dataset_stats['languages'],
        language_distribution=dataset_stats['language_distribution'],
        cwe_distribution=dataset_stats['cwe_distribution']
    )

    # Save card locally
    readme_path = output_file.parent / "README.md"
    with open(readme_path, 'w') as f:
        f.write(dataset_card)

    # Upload dataset (raw JSONL as single 'train' split)
    logger.info(f"⬆️  Uploading to HuggingFace: {repo_id} (private={private})")
    dataset.push_to_hub(repo_id, private=private, token=token)

    # Upload README separately (avoids YAML validation size limits)
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset"
    )

    hf_url = f"https://huggingface.co/datasets/{repo_id}"
    logger.info(f"✅ Dataset uploaded: {hf_url}")

    return hf_url
```

### Dataset Card (Raw Format)

Update `create_dataset_card()` to describe raw vulnerability data:

```markdown
# CrossVul Multi-Language Vulnerability Dataset (Raw Format)

**Raw vulnerability/fix pairs** extracted from CrossVul dataset - ready for custom training pipelines.

## Dataset Description

This dataset contains **X,XXX vulnerability/fix code pairs** from the CrossVul dataset in a simple, reusable format. Each record is a raw vulnerability with its corresponding fix, without any training-specific formatting.

## Format

Each record contains:
- `cwe_id`: CWE vulnerability classification (e.g., "CWE-79")
- `cwe_description`: Human-readable CWE description
- `language`: Programming language (e.g., "java", "python")
- `vulnerable_code`: Complete code with vulnerability
- `fixed_code`: Complete patched/secure code
- `file_pair_id`: Unique identifier for this vulnerability pair
- `source`: "crossvul"
- `language_dir`: Original directory name in dataset

## Usage

### Load from HuggingFace
```python
from datasets import load_dataset

# Load raw vulnerability data
dataset = load_dataset("hitoshura25/crossvul-vulnerabilities-raw")

for record in dataset['train']:
    print(f"CWE: {record['cwe_id']}")
    print(f"Language: {record['language']}")
    print(f"Vulnerable:\n{record['vulnerable_code'][:200]}...")
    print(f"Fixed:\n{record['fixed_code'][:200]}...")
```

### Transform into Training Format
```python
# Example: Create chat-based training pairs
def create_training_pair(record):
    return {
        "messages": [
            {"role": "system", "content": "You are a security expert..."},
            {"role": "user", "content": f"Fix {record['cwe_id']} in:\n{record['vulnerable_code']}"},
            {"role": "assistant", "content": record['fixed_code']}
        ],
        "metadata": {"cwe_id": record['cwe_id'], "language": record['language']}
    }
```

### Integration with process_artifacts.py

This raw format allows `process_artifacts.py` to:
1. Load from HuggingFace (no local extraction needed)
2. Create custom prompt templates
3. Mix with other datasets (CVEfixes, WebAuthn scans)
4. Apply domain-specific formatting

```python
from datasets import load_dataset

# Load raw data
crossvul = load_dataset("hitoshura25/crossvul-vulnerabilities-raw")

# Transform into your training format
training_pairs = [create_training_pair(r) for r in crossvul['train']]
```

## Statistics

- **Total Examples**: X,XXX
- **CWE Categories**: XXX
- **Languages**: XX
- **Format**: Raw JSONL (no train/val/test splits)

### Top Languages

| Language | Examples |
|----------|----------|
| java     | X,XXX    |
| python   | X,XXX    |
| ...      | ...      |

### Top CWE Categories

| CWE ID  | Description | Examples |
|---------|-------------|----------|
| CWE-79  | XSS         | X,XXX    |
| CWE-89  | SQL Injection | X,XXX  |
| ...     | ...         | ...      |

## Citation

If you use this dataset, please cite the original CrossVul paper:

```bibtex
@inproceedings{wartschinski2022vulnrepair,
  title={VulnRepair: Learning to Repair Vulnerable Code with Graph Neural Networks},
  author={Wartschinski, Laura and Noller, Yannic and Vogel, Thomas and Kehrer, Timo and Grunske, Lars},
  booktitle={Proceedings of the 44th International Conference on Software Engineering},
  year={2022}
}
```

## License

Apache License 2.0 - Derived from [CrossVul Dataset](https://zenodo.org/records/4734050)

## Extraction Process

This dataset was extracted using `crossvul_dataset_loader.py` from the original CrossVul dataset:
- Downloaded from Zenodo (367 MB compressed)
- Extracted vulnerable/fixed code pairs
- Filtered by quality (minimum file size, non-identical pairs)
- Organized by CWE classification and programming language

Source: https://zenodo.org/records/4734050
```

## Integration with process_artifacts.py

### How process_artifacts.py Will Use CrossVul Data

**Two Loading Modes** (HuggingFace or Local):

**New Function in process_artifacts.py**:

```python
def load_crossvul_dataset(crossvul_file: Path) -> List[Dict[str, Any]]:
    """
    Load CrossVul raw data and convert to training pairs.

    Args:
        crossvul_file: Path to crossvul_dataset.jsonl

    Returns:
        List of training pairs in MLX-compatible chat format
    """
    training_pairs = []

    with open(crossvul_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue

            vuln = json.loads(line)

            # Create system prompt (reuse existing function)
            system_content = _create_system_prompt("code_vulnerability")

            # Create user prompt from vulnerability data
            user_content = f"""Vulnerability Type: {vuln['cwe_id']} - {vuln['cwe_description']}
Language: {vuln['language']}
Task: Fix the security vulnerability in the code below.

## Vulnerable Code:
```{vuln['language']}
{vuln['vulnerable_code']}
```

Provide the complete fixed code that addresses the security vulnerability."""

            # Create assistant response from fixed code
            assistant_content = f"""## Fixed Code:
```{vuln['language']}
{vuln['fixed_code']}
```

**Changes Made**: Fixed {vuln['cwe_id']} vulnerability by applying secure coding practices."""

            # Create training pair
            training_pairs.append({
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content}
                ],
                "metadata": {
                    "quality": "medium",  # CrossVul is automated, not manually verified
                    "source": "crossvul",
                    "vulnerability_id": f"{vuln['cwe_id']}_{vuln['file_pair_id']}",
                    "tool": "crossvul",
                    "security_category": "code_vulnerability",
                    "confidence": 0.6,  # Lower than CVEfixes (0.8) or generated (0.7)
                    "cwe_id": vuln['cwe_id'],
                    "language": vuln['language']
                }
            })

    logging.info(f"Loaded {len(training_pairs)} CrossVul examples")
    return training_pairs
```

**Integration Point in construct_datasets_phase()**:

```python
def construct_datasets_phase(parsed_vulns_file: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    """
    PHASE: Construct Datasets
    - Loads public datasets (CrossVul, CVEfixes) ← NEW
    - Generates specific fixes for deterministic vulnerabilities
    - Applies data augmentation
    - Splits into train/validation/test sets (80/10/10)
    """
    logger.info("🚀 Starting Phase: Construct Datasets")

    all_training_pairs = []

    # SOURCE 1: Load Public Datasets (NEW)
    logger.info("📚 Source 1: Loading public datasets...")

    # Load CrossVul dataset
    crossvul_file = Path("data/public_datasets/crossvul_dataset.jsonl")
    if crossvul_file.exists():
        crossvul_examples = load_crossvul_dataset(crossvul_file)
        all_training_pairs.extend(crossvul_examples)
        logger.info(f"   Added {len(crossvul_examples)} CrossVul examples")
    else:
        logger.warning(f"   CrossVul dataset not found: {crossvul_file}")

    # Load CVEfixes dataset (if available)
    cvefixes_file = Path("data/public_datasets/cvefixes_dataset.jsonl")
    if cvefixes_file.exists():
        cvefixes_examples = load_cvefixes_dataset(cvefixes_file)
        all_training_pairs.extend(cvefixes_examples)
        logger.info(f"   Added {len(cvefixes_examples)} CVEfixes examples")

    # SOURCE 2: Generate Specific Fixes (WebAuthn-specific)
    logger.info("🔧 Source 2: Generating WebAuthn-specific fixes...")
    specific_fixes = _generate_specific_fixes(parsed_vulns)
    all_training_pairs.extend(specific_fixes)
    logger.info(f"   Generated {len(specific_fixes)} WebAuthn-specific examples")

    # Rest of the function continues as before...
    # (Split, augment, save)
```

---

## Expected Results

### Dataset Statistics
- **Total Pairs**: ~10,000-13,000 (depending on quality filtering)
- **Languages**: Java, Python, JavaScript, Go, Ruby, C, C++, PHP, etc.
- **CWE Categories**: 173 different vulnerability types
- **File Size**: ~50-100 MB (raw JSONL)

### Quality Tiers
- **CrossVul**: `quality: "medium"` (automated extraction, not manually verified)
- **CVEfixes**: `quality: "high"` (real CVE fixes with commit context)
- **WebAuthn**: `quality: "high"` (project-specific, generated from actual scans)

### Training Split Strategy
After loading public + WebAuthn data, `process_artifacts.py` will:
1. **Stratify by tool**: Ensure each tool (CrossVul, CVEfixes, OSV, Trivy, etc.) represented in all splits
2. **80/10/10 split**: Train/Val/Test
3. **Augmentation**: Only on train/val sets (test set remains pure for evaluation)

---

## Usage Example

### Step 1: Extract and Upload CrossVul Data
```bash
cd security-ai-analysis

# Activate virtual environment
source .venv/bin/activate

# Extract CrossVul data and upload to HuggingFace (auto-downloads if needed)
python crossvul_dataset_loader.py \
    --output-dir data/crossvul_extraction \
    --upload-to-hf hitoshura25/crossvul-vulnerabilities-raw \
    --hf-token $HF_TOKEN

# Output:
#  - Local: data/public_datasets/crossvul_dataset.jsonl
#  - HuggingFace: https://huggingface.co/datasets/hitoshura25/crossvul-vulnerabilities-raw
```

### Step 2: Use in Training Pipeline (Load from HuggingFace)
```bash
# Full pipeline (now includes CrossVul data)
python process_artifacts.py \
    --artifacts-dir scans/webauthn_scan_2025-10-13 \
    --output-dir results/

# process_artifacts.py will:
# 1. Load crossvul_dataset.jsonl (if exists)
# 2. Parse WebAuthn vulnerability scans
# 3. Combine public + WebAuthn data
# 4. Create train/val/test splits
# 5. Train model with ALL data
```

---

## Testing & Validation

### Quick Test (Small Sample)
```bash
# Extract just 100 pairs for testing
python crossvul_dataset_loader.py \
    --output-dir test_output \
    --languages java python \
    --limit 100

# Verify output format
head -1 test_output/crossvul_dataset.jsonl | jq .
```

### Full Extraction
```bash
# Extract all supported languages
python crossvul_dataset_loader.py \
    --output-dir data/public_datasets \
    --languages java python javascript go ruby c cpp cs php

# Expected: ~8,000-10,000 pairs
```

### Validation Checks
```bash
# Count total records
wc -l data/public_datasets/crossvul_dataset.jsonl

# Check language distribution
cat data/public_datasets/crossvul_dataset.jsonl | \
    jq -r '.language' | sort | uniq -c

# Check CWE distribution
cat data/public_datasets/crossvul_dataset.jsonl | \
    jq -r '.cwe_id' | sort | uniq -c | head -20
```

---

## File Locations

```
security-ai-analysis/
├── crossvul_dataset_loader.py         # Script to modify
├── data/
│   ├── crossvul_extraction/
│   │   └── dataset_final_sorted/      # Downloaded dataset (1.4 GB)
│   └── public_datasets/
│       └── crossvul_dataset.jsonl     # Output (50-100 MB)
└── process_artifacts.py               # Will load crossvul_dataset.jsonl
```

---

## Next Steps

1. **Fix crossvul_dataset_loader.py**:
   - ✅ Fix language detection (use directory name)
   - ✅ Remove train/val/test splits
   - ✅ Remove chat message creation
   - ✅ Output simple JSONL format

2. **Update process_artifacts.py**:
   - Add `load_crossvul_dataset()` function
   - Integrate into `construct_datasets_phase()`
   - Test with combined public + WebAuthn data

3. **Test Sequential Training**:
   - Verify CrossVul data loads correctly
   - Check training with combined dataset
   - Evaluate model performance on test set

---

## References

- **CrossVul Paper**: [VulnRepair: Learning to Repair Vulnerable Code with Graph Neural Networks](https://zenodo.org/records/4734050)
- **Dataset**: https://zenodo.org/records/4734050
- **Format**: Bad/good file pairs organized by CWE and language
- **Size**: 367 MB compressed, 1.4 GB extracted, 13,067 pairs
