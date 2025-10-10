import json
import sys
from pathlib import Path
import argparse
import logging
import subprocess
from typing import Any, Dict, List, Optional
from datetime import datetime

from config_manager import OLMoSecurityConfig
from parsers.sarif_trivy_parser import parse_trivy_sarif
from parsers.sarif_checkov_parser import parse_checkov_sarif
from parsers.semgrep_parser import parse_semgrep_json
from parsers.osv_parser import parse_osv_json_enhanced
from parsers.zap_parser import parse_zap_json
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Phase constants to avoid string repetition and typos
class Phases:
    PARSING = "parsing"
    DATASETS = "datasets"
    TRAINING = "training"
    UPLOAD = "upload"

    # List for validation
    ALL_PHASES = [
        PARSING, DATASETS, TRAINING, UPLOAD
    ]

    # Input requirements mapping
    PHASE_INPUTS = {
        PARSING: [],  # Uses --artifacts-dir
        DATASETS: ['parsed_vulnerabilities_input'],
        TRAINING: ['train_dataset_input', 'validation_dataset_input', 'test_dataset_input'],
        UPLOAD: ['adapter_input', 'train_dataset_input', 'validation_dataset_input', 'test_dataset_input'],
    }

def find_security_files(directory: str) -> dict:
    """
    Finds all security scan result files in the specified directory.
    (Reused from the original script)
    """
    scan_files = {
        'trivy': [], 'checkov': [], 'semgrep': [],
        'osv': [], 'sarif': [], 'zap': []
    }
    dir_path = Path(directory)
    logger.info(f"Searching for security files in: {dir_path.resolve()}")

    for file_path in dir_path.rglob("*"):
        if not file_path.is_file():
            continue

        file_str = str(file_path).lower()

        if 'trivy' in file_str and file_path.suffix in ['.sarif']:
            scan_files['trivy'].append(str(file_path))
        elif 'checkov' in file_str and file_path.suffix in ['.sarif']:
            scan_files['checkov'].append(str(file_path))
        elif 'semgrep' in file_str and file_path.suffix in ['.json']:
            scan_files['semgrep'].append(str(file_path))
        elif 'osv' in file_str and file_path.suffix == '.json':
            scan_files['osv'].append(str(file_path))
        elif 'zap' in file_str and file_path.suffix == '.json':
            scan_files['zap'].append(str(file_path))

    logger.info("Found security scan files:")
    for scan_type, files in scan_files.items():
        if files:
            logger.info(f"  - {scan_type}: {len(files)} file(s)")
    return scan_files

def parse_vulnerabilities_phase(artifacts_dir: str, output_dir: Path) -> Path:
    """
    PHASE 1:
    - Parses various security scan files to extract vulnerabilities.
    - Saves the list to a single JSON file.
    """
    logger.info("🚀 Starting Phase 1: Parse Vulnerabilities")

    # Find all security files in the provided artifacts directory
    scan_files = find_security_files(artifacts_dir)
    total_files = sum(len(files) for files in scan_files.values())
    if total_files == 0:
        logger.error(f"CRITICAL: No security files found in {artifacts_dir}. Aborting.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    all_vulnerabilities = []
    parser_map = {
        'trivy': parse_trivy_sarif,
        'checkov': parse_checkov_sarif,
        'semgrep': parse_semgrep_json,
        'osv': parse_osv_json_enhanced,
        'zap': parse_zap_json,
    }

    # Step 1: Parse vulnerabilities from all files
    for scan_type, files in scan_files.items():
        if not files:
            continue
        logger.info(f"Determing parser for scan type: {scan_type}")
        parser_func = parser_map.get(scan_type)
        if not parser_func:
            continue
        logger.info(f"Parsing {len(files)} files for scan type: {scan_type}")
        for file_path in files:
            try:
                vulns = parser_func(file_path)
                if vulns:
                    all_vulnerabilities.extend(vulns)
            except Exception as e:
                raise RuntimeError(f"Error parsing {file_path} with {scan_type} parser: {e}")

    logger.info(f"Parsed a total of {len(all_vulnerabilities)} vulnerabilities.")

    output_file = output_dir / "parsed_vulnerabilities.json"
    with open(output_file, 'w') as f:
        json.dump(all_vulnerabilities, f, indent=2)

    logger.info(f"✅ Parse vulnerabilities phase complete. Output saved to: {output_file}")
    return output_file

def construct_datasets_phase(parsed_vulns_file: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    """
    PHASE: Construct Datasets
    - Loads public datasets (CVEfixes)
    - Generates specific fixes for deterministic vulnerabilities
    - Applies data augmentation (semantic variations, self-mixup, context blending)
    - Processes narratives into training pairs
    - Combines and splits into train/validation/test sets (80/10/10)
    """
    logger.info("🚀 Starting Phase: Construct Datasets")

    if not parsed_vulns_file.exists():
        raise FileNotFoundError(f"Parsed vulnerabilities file not found: {parsed_vulns_file}")

    # Load parsed vulnerabilities
    with open(parsed_vulns_file, 'r') as f:
        parsed_vulns = json.load(f)

    logger.info(f"Loaded {len(parsed_vulns)} parsed vulnerabilities")

    all_training_pairs = []

    # SOURCE 1: Load Public Data
    #logger.info("📚 Source 1: Loading public datasets...")
    #public_loader = PublicDatasetLoader()
    #public_examples = public_loader.load_public_datasets()  # Load all available data
    #all_training_pairs.extend(public_examples)
    #logger.info(f"   Added {len(public_examples)} examples from public datasets")

    # SOURCE 2: Generate Specific Fixes
    logger.info("🔧 Source 2: Generating specific fixes...")
    specific_fixes = _generate_specific_fixes(parsed_vulns)
    logger.info(f"   Generated {len(specific_fixes)} specific fix examples")

    # CRITICAL: Split BEFORE augmentation to keep test set pure (ground truth)
    # Test set must contain only original examples for valid evaluation
    # Using stratified split to ensure consistent test set across runs
    logger.info("📊 Splitting original examples with stratified sampling by tool...")
    original_train, original_val, test_pairs = _stratified_split_by_tool(specific_fixes)

    logger.info(f"   Final split: {len(original_train)} train / {len(original_val)} val / {len(test_pairs)} test")

    # SOURCE 3: Data Augmentation (ONLY for train/val sets)
    # Test set remains pure original examples for valid evaluation
    logger.info("🎨 Source 3: Applying data augmentation to train/val sets...")
    augmented_train = _augment_training_pairs(original_train)
    augmented_val = _augment_training_pairs(original_val)
    logger.info(f"   Augmented: +{len(augmented_train)} train examples, +{len(augmented_val)} val examples")

    # Combine original + augmented for train/val
    train_pairs = original_train + augmented_train
    val_pairs = original_val + augmented_val

    # Shuffle each set independently
    random.shuffle(train_pairs)
    random.shuffle(val_pairs)

    logger.info(f"📊 Final dataset sizes:")
    logger.info(f"   Train set: {len(train_pairs)} examples ({len(original_train)} original + {len(augmented_train)} augmented)")
    logger.info(f"   Validation set: {len(val_pairs)} examples ({len(original_val)} original + {len(augmented_val)} augmented)")
    logger.info(f"   Test set: {len(test_pairs)} examples (100% original, no augmentation)")

    # Save as JSONL
    output_dir.mkdir(parents=True, exist_ok=True)
    train_file = output_dir / "train_dataset.jsonl"
    val_file = output_dir / "validation_dataset.jsonl"
    test_file = output_dir / "test_dataset.jsonl"

    with open(train_file, 'w') as f:
        for pair in train_pairs:
            f.write(json.dumps(pair) + '\n')

    with open(val_file, 'w') as f:
        for pair in val_pairs:
            f.write(json.dumps(pair) + '\n')

    with open(test_file, 'w') as f:
        for pair in test_pairs:
            f.write(json.dumps(pair) + '\n')

    logger.info(f"✅ Phase complete.")
    logger.info(f"   Train dataset: {train_file}")
    logger.info(f"   Validation dataset: {val_file}")
    logger.info(f"   Test dataset: {test_file}")

    return train_file, val_file, test_file


def _stratified_split_by_tool(training_pairs: List[Dict[str, Any]], random_seed: int = 42) -> tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Split training pairs into train/val/test sets using stratified sampling by tool.

    Ensures each tool (Trivy, Semgrep, OSV, ZAP, Checkov) is represented proportionally
    in all three sets, providing consistent evaluation across runs.

    Args:
        training_pairs: List of training examples with metadata containing 'tool' field
        random_seed: Fixed random seed for reproducibility (default: 42)

    Returns:
        Tuple of (train_pairs, val_pairs, test_pairs)
    """
    # Group vulnerabilities by tool
    tool_groups = {}
    for pair in training_pairs:
        tool = pair.get('metadata', {}).get('tool', 'unknown')
        if tool not in tool_groups:
            tool_groups[tool] = []
        tool_groups[tool].append(pair)

    # Set fixed seed for reproducibility
    random.seed(random_seed)

    train_pairs = []
    val_pairs = []
    test_pairs = []

    logger.info(f"📊 Stratified split by tool:")

    # Split each tool's vulnerabilities proportionally
    for tool, pairs in tool_groups.items():
        # Shuffle within tool group
        random.shuffle(pairs)
        count = len(pairs)

        # Calculate split sizes
        if count >= 10:
            # Standard 80/10/10 split for tools with enough data
            train_size = int(count * 0.8)
            val_size = int(count * 0.1)
            test_size = count - train_size - val_size  # Remainder goes to test
        else:
            # For small datasets, ensure at least 1 in test and val if possible
            test_size = max(1, int(count * 0.1))
            val_size = max(1, int(count * 0.1)) if count > test_size else 0
            train_size = count - test_size - val_size

            # Edge case: if only 1-2 examples, put in test for evaluation
            if count <= 2:
                test_size = count
                val_size = 0
                train_size = 0

        # Split the tool's pairs
        tool_train = pairs[:train_size]
        tool_val = pairs[train_size:train_size + val_size]
        tool_test = pairs[train_size + val_size:]

        train_pairs.extend(tool_train)
        val_pairs.extend(tool_val)
        test_pairs.extend(tool_test)

        logger.info(f"   {tool}: {count} total → {len(tool_train)} train / {len(tool_val)} val / {len(tool_test)} test")

    # Final shuffle of combined sets (but maintain tool distribution)
    random.shuffle(train_pairs)
    random.shuffle(val_pairs)
    random.shuffle(test_pairs)

    return train_pairs, val_pairs, test_pairs


def _create_system_prompt(category: str) -> str:
    """
    Create tool-specific system prompt based on security category.

    Args:
        category: Security category (dependency_vulnerabilities, code_vulnerability, etc.)

    Returns:
        Specialized system prompt optimized for the category
    """
    if category in ['dependency_vulnerabilities', 'dependency_security']:
        return """You are a dependency security specialist.

EXPERTISE: Version constraints, semver, Gradle/Maven/npm dependency management

TASK: Provide precise dependency upgrade instructions
- Specify exact versions (no ranges)
- Use correct build syntax (Gradle Kotlin DSL, package.json)
- Include security rationale

OUTPUT: implementation("group:artifact:VERSION")"""

    elif category == 'code_vulnerability':
        return """You are a secure code specialist.

EXPERTISE: OWASP patterns, Kotlin/Java security APIs, WebAuthn

TASK: Provide minimal code fixes that eliminate vulnerabilities
- Preserve functionality
- Use appropriate security libraries
- Include security comments

OUTPUT: Fixed code block with brief explanation"""

    elif category == 'web_security':
        return """You are a web security specialist.

EXPERTISE: HTTP security headers, CORS, session security, KTor framework

TASK: Provide framework-native security configurations
- Use KTor install() syntax
- Follow strict security policies

OUTPUT: KTor configuration code"""

    elif category == 'configuration_security':
        return """You are a DevOps security specialist.

EXPERTISE: GitHub Actions, IaC security, least-privilege permissions

TASK: Provide minimal security configuration fixes
- Use platform-specific syntax (YAML, HCL)
- Preserve functionality

OUTPUT: Corrected configuration"""

    else:
        # Fallback for unknown categories
        return """You are a cybersecurity analyst specializing in WebAuthn and FIDO2 security vulnerabilities.

CRITICAL SECURITY GUIDELINES:
- Always prioritize security in your analysis and recommendations
- Provide actionable remediation steps for identified vulnerabilities
- Consider the broader security implications of each finding
- Maintain accuracy and precision in threat assessments
- Follow responsible disclosure principles
- Preserve safety guidelines and ethical analysis standards

Your role is to analyze security vulnerabilities and provide comprehensive, actionable guidance for remediation."""


def _create_vulnerability_prompt(vuln: Dict) -> str:
    """
    Create tool-specific user prompt based on vulnerability data.

    Args:
        vuln: Vulnerability dictionary with tool, security_category, and vulnerability details

    Returns:
        Formatted user prompt for the training pair
    """
    tool = vuln.get('tool', '')
    category = vuln.get('security_category', 'unknown')

    # Dependency vulnerabilities (OSV, Trivy)
    if category in ['dependency_vulnerabilities', 'dependency_security']:
        current_version = vuln.get('installed_version')
        if not current_version:
            raise ValueError(f"Installed version information missing in vulnerability data: ${vuln}")
        fixed_version = vuln.get('fixed_version')
        if not fixed_version:
            raise ValueError(f"Fixed version information missing in vulnerability data: ${vuln}")
        package = vuln.get('package_name', vuln.get('title', 'Unknown'))
        return f"""Vulnerability: {vuln.get('id', 'Unknown')}
Severity: {vuln.get('severity', 'Unknown')}
Tool: {tool}
Package: {package}
Current Version: {current_version}
Fixed Version: {fixed_version}
Description: {vuln.get('summary', vuln.get('description', vuln.get('message', 'No description')))}

STRICT CONSTRAINTS:
- Do NOT add sections beyond what's specified above
- Do NOT include "Alternative Approaches" or similar sections
- Code blocks: ONLY the fix, no surrounding context
- Explanations: EXACTLY 2-3 sentences, no more
- Follow the markdown format exactly as shown"""

    # Code vulnerabilities (Semgrep)
    elif category == 'code_vulnerability':
        code_context = vuln.get('code_context', {})
        vulnerable_code = code_context.get('vulnerable_code', 'N/A')

        return f"""Vulnerability: {vuln.get('id', 'Unknown')}
Severity: {vuln.get('severity', 'Unknown')}
Tool: {tool}
File: {vuln.get('file_path', 'Unknown')}
Line: {vuln.get('start', {}).get('line', 'Unknown')}
Message: {vuln.get('message', 'No description')}

Vulnerable Code:
{vulnerable_code}

STRICT CONSTRAINTS:
- Do NOT add sections beyond what's specified above
- Do NOT include "Alternative Approaches" or similar sections
- Code blocks: ONLY the fix, no surrounding context
- Explanations: EXACTLY 2-3 sentences, no more
- Follow the markdown format exactly as shown"""

    # Web/HTTP security (ZAP)
    elif category == 'web_security':
        return f"""Alert: {vuln.get('alert', 'Unknown')}
Severity: {vuln.get('severity', 'Unknown')}
Tool: {tool}
URL: {vuln.get('uri', 'Unknown')}
Description: {vuln.get('description', 'No description')}
Solution: {vuln.get('solution', 'No solution provided')}

STRICT CONSTRAINTS:
- Do NOT add sections beyond what's specified above
- Do NOT include "Alternative Approaches" or similar sections
- Code blocks: ONLY the fix, no surrounding context
- Explanations: EXACTLY 2-3 sentences, no more
- Follow the markdown format exactly as shown"""

    # Configuration security (Checkov)
    elif category == 'configuration_security':
        code_context = vuln.get('code_context', {})
        vulnerable_code = code_context.get('vulnerable_code', 'N/A')
        config_type = vuln.get('config_type', 'Unknown')

        return f"""Rule: {vuln.get('rule_name', vuln.get('id', 'Unknown'))}
Severity: {vuln.get('severity', 'Unknown')}
Tool: {tool}
File: {vuln.get('file_path', 'Unknown')}
Config Type: {config_type}
Message: {vuln.get('message', 'No description')}

Current Configuration:
{vulnerable_code}

STRICT CONSTRAINTS:
- Do NOT add sections beyond what's specified above
- Do NOT include "Alternative Approaches" or similar sections
- Code blocks: ONLY the fix, no surrounding context
- Explanations: EXACTLY 2-3 sentences, no more
- Follow the markdown format exactly as shown"""

    # Fallback for unknown categories
    else:
        return f"""Fix the following security issue:

ID: {vuln.get('id', 'Unknown')}
Severity: {vuln.get('severity', 'Unknown')}
Tool: {tool}
Category: {category}
Description: {vuln.get('message', vuln.get('description', 'No description'))}"""


def _format_assistant_response(fix_data: Dict) -> str:
    """
    Format the fix data into a comprehensive assistant response.

    Args:
        fix_data: Fix dictionary with description, fixed_code, explanation, and alternatives

    Returns:
        Formatted assistant response for the training pair
    """
    description = fix_data.get('description', '')
    fixed_code = fix_data.get('fixed_code', '')
    explanation = fix_data.get('explanation', '')
    alternatives = fix_data.get('alternatives', [])

    # Build comprehensive response
    response_parts = []

    # Primary fix
    if description:
        response_parts.append(f"## Fix: {description}\n")

    if fixed_code:
        response_parts.append(f"```\n{fixed_code}\n```\n")

    if explanation:
        response_parts.append(f"### Explanation\n{explanation}\n")

    # Alternative approaches
    if alternatives:
        response_parts.append("### Alternative Approaches\n")
        for i, alt in enumerate(alternatives, 1):
            alt_desc = alt.get('description', '')
            alt_code = alt.get('fixed_code', '')
            alt_exp = alt.get('explanation', '')

            if alt_desc:
                response_parts.append(f"\n**Alternative {i}: {alt_desc}**\n")
            if alt_code:
                response_parts.append(f"```\n{alt_code}\n```\n")
            if alt_exp:
                response_parts.append(f"{alt_exp}\n")

    return '\n'.join(response_parts).strip()


def _generate_specific_fixes(parsed_vulns: List[Dict]) -> List[Dict[str, Any]]:
    """
    Generate training pairs from parsed vulnerabilities with pre-generated fixes.

    Uses the enhanced parsing architecture where all tools (OSV, Trivy, Semgrep, ZAP, Checkov)
    generate fixes during parsing. This function creates tool-specific prompts and formats
    the pre-generated fixes into MLX-compatible training pairs.

    Args:
        parsed_vulns: List of flat vulnerability dictionaries with 'fix' field containing:
            - description: Fix description
            - fixed_code: The fixed code/configuration
            - explanation: Detailed explanation
            - alternatives: List of alternative fixes (optional)

    Returns:
        List of training pairs in MLX-compatible chat format:
        {
            "messages": [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ],
            "metadata": {
                "quality": "high",
                "source": "generated",
                "vulnerability_id": "...",
                "tool": "osv|trivy|semgrep|zap|checkov",
                "security_category": "...",
                "confidence": 0.0-1.0,
                ...
            }
        }
    """
    specific_fixes = []

    for vuln in parsed_vulns:
        # Vulnerabilities are now flat objects with pre-generated fixes
        tool = vuln.get('tool')
        vuln_id = vuln.get('id')
        fix_data = vuln.get('fix')

        if not vuln_id:
            logger.error(f"Missing vulnerability ID in entry: {vuln}")
            raise ValueError("Each vulnerability must have an 'id' field")

        if not tool:
            logger.error(f"Missing tool information for vulnerability {vuln_id}")
            raise ValueError(f"Missing tool information for vulnerability {vuln_id}")

        if not fix_data:
            logger.error(f"No fix data found for {vuln_id} from {tool}")
            raise ValueError(f"Missing fix data for vulnerability {vuln_id} from {tool}")

        try:
            # Get security category for tool-specific prompt generation
            security_category = vuln.get('security_category', 'unknown')

            # Generate tool-specific system prompt based on category
            system_content = _create_system_prompt(security_category)

            # Generate tool-specific user prompt based on vulnerability category
            user_content = _create_vulnerability_prompt(vuln)

            # Use the pre-generated fix from parsing phase
            # Primary fix has description, fixed_code, and explanation
            assistant_content = _format_assistant_response(fix_data)

            if assistant_content:
                specific_fixes.append({
                    "messages": [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": assistant_content}
                    ],
                    "metadata": {
                        "quality": "high",
                        "source": "generated",
                        "vulnerability_id": vuln_id,
                        "tool": tool,
                        "security_category": vuln.get('security_category', 'unknown'),
                        "confidence": fix_data.get('confidence', 0.7),
                        "chat_template": "chatml",
                        "security_framework": "webauthn-security-analysis"
                    }
                })
        except Exception as e:
            # FAIL FAST - don't suppress exceptions
            logger.error(f"Could not generate training pair for {vuln_id}: {e}")
            raise RuntimeError(f"Error generating training pair for vulnerability {vuln_id}: {e}")

    return specific_fixes


def _augment_training_pairs(training_pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Augment training pairs using research-backed data augmentation techniques.

    Applies semantic variations, self-mixup, and context blending to increase
    dataset diversity and improve model generalization on small datasets.

    Args:
        training_pairs: Original training pairs in ChatML format

    Returns:
        List of augmented training pairs (target: 3x original count)
    """
    from dataset_augmentor import SecurityDataAugmentor, AugmentationConfig
    import yaml

    # Load augmentation config from YAML
    config = OLMoSecurityConfig()
    config_file = Path(__file__).parent.parent / "config" / "olmo-security-config.yaml"

    with open(config_file, 'r') as f:
        raw_config = yaml.safe_load(f)

    aug_config = AugmentationConfig.from_config(raw_config)

    # Initialize augmentor
    augmentor = SecurityDataAugmentor(aug_config)

    # Generate augmented examples
    augmented_pairs = augmentor.augment_training_data(training_pairs)

    return augmented_pairs


def train_model_phase(train_dataset: Path, validation_dataset: Path, test_dataset: Path):
    """
    PHASE: Train Model (with automatic evaluation)
    - Creates structured training run directory with manifest
    - Applies quality-weighted sampling to prioritize high-quality examples
    - Fine-tunes model using MLX LoRA
    - Automatically evaluates model on test dataset
    - Saves all artifacts and results to run directory

    Args:
        train_dataset: Path to train_dataset.jsonl
        validation_dataset: Path to validation_dataset.jsonl
        test_dataset: Path to test_dataset.jsonl

    Returns:
        TrainingRun instance with trained model and evaluation results
    """
    logger.info("🚀 Starting Phase: Train Model")
    config = OLMoSecurityConfig()

    if not train_dataset.exists():
        raise FileNotFoundError(f"Train dataset not found: {train_dataset}")
    if not validation_dataset.exists():
        raise FileNotFoundError(f"Validation dataset not found: {validation_dataset}")
    if not test_dataset.exists():
        raise FileNotFoundError(f"Test dataset not found: {test_dataset}")

    # Import managers
    from mlx_trainer import MLXTrainer
    from training_run_manager import TrainingRunManager

    # Create training run with structured directory
    run_manager = TrainingRunManager(config)

    training_params = {
        "learning_rate": config.fine_tuning.learning_rate,
        "batch_size": config.fine_tuning.batch_size,
        "num_iters": config.fine_tuning.max_stage1_iters,
        "quality_weight_multiplier": 2.5
    }

    # Create run (this copies datasets to train.jsonl/valid.jsonl)
    training_run = run_manager.create_run(
        train_dataset=train_dataset,
        validation_dataset=validation_dataset,
        training_params=training_params
    )

    logger.info(f"Train dataset: {train_dataset}")
    logger.info(f"Validation dataset: {validation_dataset}")
    logger.info(f"Test dataset: {test_dataset}")
    logger.info(f"Training run: {training_run.run_id}")
    logger.info(f"Training data directory: {training_run.training_data_path}")

    # Initialize trainer with config
    trainer = MLXTrainer(
        config=config,
        output_dir=training_run.adapters_path
    )

    # Run training (uses training_run.training_data_path with train.jsonl/valid.jsonl)
    adapter_path = trainer.train(
        training_data_dir=training_run.training_data_path
    )

    logger.info(f"✅ Training complete.")
    logger.info(f"   Training run: {training_run.run_dir}")
    logger.info(f"   Adapter artifacts: {adapter_path}")

    logger.info("🔬 Running evaluation...")
    eval_results = run_manager.evaluate(training_run, test_dataset)

    metrics = eval_results.get('metrics', {})
    logger.info(f"✅ Evaluation complete.")
    logger.info(f"   Exact Match: {metrics.get('exact_match_percentage', 0):.2f}%")
    logger.info(f"   Avg CodeBLEU: {metrics.get('avg_codebleu', 0):.4f}")
    logger.info(f"   Test Examples: {eval_results.get('total_examples', 0)}")

    return training_run



def _analyze_datasets(train_file: Path, val_file: Path, test_file: Path) -> Dict[str, Any]:
    """
    Analyze datasets for statistics to include in model/dataset cards.

    Args:
        train_file: Path to training dataset
        val_file: Path to validation dataset
        test_file: Path to test dataset

    Returns:
        Dictionary with dataset statistics
    """
    stats = {
        "train_count": 0,
        "val_count": 0,
        "test_count": 0,
        "quality_distribution": {"high": 0, "medium": 0, "low": 0, "unknown": 0},
        "source_distribution": {}
    }

    # Analyze training dataset
    with open(train_file, 'r') as f:
        for line in f:
            if line.strip():
                stats["train_count"] += 1
                try:
                    example = json.loads(line)
                    metadata = example.get('metadata')
                    if not metadata:
                        raise ValueError("Missing metadata field in training example")

                    # Track quality
                    quality = metadata.get('quality')
                    if not quality:
                        raise ValueError("Missing quality field in metadata")
                    stats["quality_distribution"][quality] = stats["quality_distribution"].get(quality, 0) + 1

                    # Track source
                    source = metadata.get('source')
                    if not source:
                        raise ValueError("Missing source field in metadata")
                    stats["source_distribution"][source] = stats["source_distribution"].get(source, 0) + 1
                except json.JSONDecodeError:
                    continue

    # Analyze validation dataset
    with open(val_file, 'r') as f:
        for line in f:
            if line.strip():
                stats["val_count"] += 1

    # Analyze test dataset if provided
    if test_file and test_file.exists():
        with open(test_file, 'r') as f:
            for line in f:
                if line.strip():
                    stats["test_count"] += 1

    return stats


def upload_artifacts_phase(
    adapter_path: Path,
    train_dataset: Path,
    validation_dataset: Path,
    test_dataset: Path,
    skip_upload: bool = False
) -> Dict[str, Any]:
    """
    PHASE: Upload Artifacts to HuggingFace Hub

    Uploads model, datasets, and training artifacts with comprehensive documentation.

    Args:
        adapter_path: Path to trained model adapter
        train_dataset: Path to training dataset (train.jsonl)
        validation_dataset: Path to validation dataset (valid.jsonl)
        test_dataset: Path to test dataset (test.jsonl)
        skip_upload: If True, skip actual upload operations

    Returns:
        Dictionary with upload status and URLs
    """
    logger.info("=" * 60)
    logger.info("📤 Phase 6: Upload Artifacts")
    logger.info("=" * 60)

    from artifact_uploader import ArtifactUploader

    # Initialize uploader
    uploader = ArtifactUploader(skip_upload=skip_upload)

    results = {
        "model_url": None,
        "dataset_url": None,
        "staging_dir": str(uploader.staging_dir),
        "skipped": skip_upload
    }

    # Analyze datasets for metadata
    logger.info("📊 Analyzing datasets for statistics...")
    dataset_stats = _analyze_datasets(train_dataset, validation_dataset, test_dataset)
    logger.info(f"   Dataset statistics: {dataset_stats}")
    logger.info(f"   Train examples: {dataset_stats['train_count']}")
    logger.info(f"   Validation examples: {dataset_stats['val_count']}")
    if test_dataset:
        logger.info(f"   Test examples: {dataset_stats['test_count']}")
    logger.info(f"   Quality distribution: {dataset_stats['quality_distribution']}")

    # Load training metadata if available
    training_metadata = {}
    metadata_file = adapter_path / "training_metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Training metadata file not found: {metadata_file}")

    with open(metadata_file, 'r') as f:
        training_metadata = json.load(f)

    # Combine metadata
    upload_metadata = {
        **training_metadata,
        "dataset_stats": dataset_stats,
        "upload_timestamp": datetime.now().isoformat()
    }

    # Upload artifacts (both model and dataset with synchronized timestamps)
    try:
        logger.info("📤 Uploading artifacts to HuggingFace Hub...")
        upload_results = uploader.upload_artifacts(
            adapter_path,
            train_dataset,
            validation_dataset,
            upload_metadata,
            test_dataset
        )

        if skip_upload:
            logger.info("   ⚠️ Upload skipped as per configuration.")
            return results

        if not upload_results["model_url"]:
            raise ValueError("Model upload returned empty URL")
        if not upload_results["dataset_url"]:
            raise ValueError("Dataset upload returned empty URL")

        results["model_url"] = upload_results["model_url"]
        results["dataset_url"] = upload_results["dataset_url"]
        logger.info(f"   ✅ Model uploaded: {results['model_url']}")
        logger.info(f"   ✅ Dataset uploaded: {results['dataset_url']}")
    except Exception as e:
        logger.error(f"   ❌ Upload failed: {e}")
        raise RuntimeError(f"Artifact upload failed: {e}")

    logger.info("✅ Phase complete.")
    logger.info(f"   Model: {results['model_url']}")
    logger.info(f"   Dataset: {results['dataset_url']}")
    logger.info(f"   Staging: {results['staging_dir']}")

    return results


def get_active_only_phase(args) -> str:
    """Get the single active --only-* phase flag, or None for multi-phase"""

    only_flags = {
        Phases.PARSING: args.only_parsing,
        Phases.DATASETS: args.only_datasets,
        Phases.TRAINING: args.only_training,
        Phases.UPLOAD: args.only_upload,
    }

    active_phases = [phase for phase, flag in only_flags.items() if flag]

    if len(active_phases) > 1:
        raise ValueError(f"Error: Cannot specify multiple --only-* flags: {', '.join(active_phases)}")

    return active_phases[0] if active_phases else None

def validate_phase_inputs(phase: str, args):
    """Validate that required input files exist for the specified phase"""
    required_inputs = Phases.PHASE_INPUTS[phase]
    missing_inputs = []

    for input_name in required_inputs:
        input_value = getattr(args, input_name, None)
        if not input_value:
            missing_inputs.append(f"--{input_name.replace('_', '-')}")
        elif hasattr(input_value, 'exists') and not input_value.exists():
            raise ValueError(f"Error: Input file does not exist: {input_value}")

    if missing_inputs:
        raise ValueError(f"Error: --only-{phase} requires: {', '.join(missing_inputs)}")

def run_full_pipeline(artifacts_dir: str, output_dir: Path, skip_upload: bool = False):
    # --- Execute Pipeline Phases ---

    # Phase: Parse
    parsed_vulns_file = parse_vulnerabilities_phase(artifacts_dir, output_dir)

    # Phase: Construct Datasets
    train_file, val_file, test_file = construct_datasets_phase(parsed_vulns_file, output_dir)

    # Phase: Train Model (with automatic evaluation)
    training_run = train_model_phase(
        train_file,
        val_file,
        test_file
    )

    # Phase: Upload Artifacts
    upload_results = upload_artifacts_phase(
        training_run.adapters_path,
        train_file,
        val_file,
        test_file,
        skip_upload=skip_upload
    )

    # Load evaluation results from training run
    eval_results_file = training_run.evaluation_results_path / "evaluation_results.json"
    eval_results = {}
    if eval_results_file.exists():
        import json
        with open(eval_results_file, 'r') as f:
            eval_results = json.load(f)

    logger.info("\n✅ Full pipeline completed successfully!")
    logger.info(f"   Final outputs:")
    logger.info(f"   Parsed vulnerabilities: {parsed_vulns_file}")
    logger.info(f"   Train dataset: {train_file}")
    logger.info(f"   Validation dataset: {val_file}")
    logger.info(f"   Test dataset: {test_file}")
    logger.info(f"   Training run: {training_run.run_dir}")
    logger.info(f"   Adapter artifacts: {training_run.adapters_path}")
    logger.info(f"   Evaluation metrics:")
    logger.info(f"     - Exact Match: {eval_results.get('metrics', {}).get('exact_match_percentage', 0):.2f}%")
    logger.info(f"     - Avg CodeBLEU: {eval_results.get('metrics', {}).get('avg_codebleu', 0):.4f}")
    if upload_results.get("model_url"):
        logger.info(f"   Model URL: {upload_results['model_url']}")
    if upload_results.get("dataset_url"):
        logger.info(f"   Dataset URL: {upload_results['dataset_url']}")

def execute_single_phase(phase: str, args):
    """Execute a single phase with provided inputs"""
    print(f"\n🎯 Executing single phase: {phase}")

    output_dir = args.output_dir

    if phase == Phases.PARSING:
        # Extract scan files from artifacts directory
        vulnerabilities_file = parse_vulnerabilities_phase(args.artifacts_dir, output_dir)
        print(f"✅ Parsing completed. Output files:")
        print(f"   Parsed vulnerabilities: {vulnerabilities_file}")
        return 0, {"phase": phase, "vulnerabilities_file": str(vulnerabilities_file)}

    elif phase == Phases.DATASETS:
        parsed_vulnerabilities_file = args.parsed_vulnerabilities_input
        train_file, val_file, test_file = construct_datasets_phase(parsed_vulnerabilities_file, output_dir)
        print(f"✅ Dataset construction completed. Output files:")
        print(f"   Train dataset: {train_file}")
        print(f"   Validation dataset: {val_file}")
        print(f"   Test dataset: {test_file}")
        return 0, {"phase": phase, "train_file": str(train_file), "val_file": str(val_file), "test_file": str(test_file)}

    elif phase == Phases.TRAINING:
        train_dataset = args.train_dataset_input
        validation_dataset = args.validation_dataset_input
        test_dataset = args.test_dataset_input

        training_run = train_model_phase(
            train_dataset,
            validation_dataset,
            test_dataset
        )
        print(f"✅ Model training and evaluation completed. Output files:")
        print(f"   Training run: {training_run.run_dir}")
        print(f"   Adapter artifacts: {training_run.adapters_path}")
        print(f"   Evaluation results: {training_run.run_dir / 'evaluation'}")
        return 0, {"phase": phase, "training_run": str(training_run.run_dir)}

    elif phase == Phases.UPLOAD:
        adapter_path = args.adapter_input
        train_dataset = args.train_dataset_input
        validation_dataset = args.validation_dataset_input
        test_dataset = args.test_dataset_input
        skip_upload = bool(args.skip_upload)

        upload_results = upload_artifacts_phase(
            adapter_path,
            train_dataset,
            validation_dataset,
            test_dataset,
            skip_upload=skip_upload
        )
        print(f"✅ Upload completed.")
        if upload_results.get("model_url"):
            print(f"   Model: {upload_results['model_url']}")
        if upload_results.get("dataset_url"):
            print(f"   Dataset: {upload_results['dataset_url']}")
        if upload_results.get("staging_dir"):
            print(f"   Staging: {upload_results['staging_dir']}")
        return 0, {"phase": phase, **upload_results}

    else:
        raise ValueError(f"Unknown phase: {phase}")

def ensure_base_model_ready(config: OLMoSecurityConfig) -> bool:
    """
    Ensure base model is downloaded and ready for training.
    Automatically runs setup.py if model is missing.

    Args:
        config: Configuration object

    Returns:
        True if model is ready, False if setup failed
    """
    try:
        # Check if base model exists
        model_path = config.get_base_model_path()
        logger.info(f"✅ Base model found: {model_path}")
        return True
    except FileNotFoundError:
        # Model missing - run setup.py
        logger.warning(f"⚠️  Base model not found: {config.default_base_model}")
        logger.info("📥 Running setup.py to download and convert base model...")
        logger.info("   This may take several minutes on first run...")

        setup_script = Path(__file__).parent / "setup.py"

        if not setup_script.exists():
            logger.error(f"❌ setup.py not found at {setup_script}")
            logger.error("   Please run setup.py manually to download the base model")
            return False

        # Run setup.py
        result = subprocess.run(
            [sys.executable, str(setup_script)],
            capture_output=True,
            text=True
        )

        # Show setup output
        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"   {line}")

        if result.returncode == 0:
            logger.info("✅ Base model setup completed successfully")
            return True
        else:
            logger.error("❌ Base model setup failed")
            if result.stderr:
                logger.error("Setup errors:")
                for line in result.stderr.splitlines():
                    logger.error(f"   {line}")
            return False

def main():
    """
    Main orchestrator for the security analysis pipeline.
    """
    parser = argparse.ArgumentParser(description="Refactored Security Analysis Pipeline")
    parser.add_argument("--artifacts-dir", type=Path, required=True, help="Directory containing security scan artifacts (e.g., extracted zip files).")
    parser.add_argument("--output-dir", type=Path, default=Path("results"), help="Directory to save phase outputs.")
    
    # Single-phase execution flags
    phase_group = parser.add_argument_group('Single Phase Execution')
    phase_group.add_argument("--only-parsing", action="store_true", help="Execute only parsing phase")
    phase_group.add_argument("--only-datasets", action="store_true", help="Execute only dataset construction phase")
    phase_group.add_argument("--only-training", action="store_true", help="Execute only model training phase (includes automatic evaluation)")
    phase_group.add_argument("--only-upload", action="store_true", help="Execute only artifact upload phase")

    # Upload control flags
    upload_group = parser.add_argument_group('Upload Options')
    upload_group.add_argument("--skip-upload", action="store_true", help="Skip artifact upload in full pipeline (default: False)")

    # Input file arguments
    input_group = parser.add_argument_group('Phase Input Files')
    input_group.add_argument("--parsed-input", type=Path,
                            help="Parsed vulnerabilities file (for categorization)")
    input_group.add_argument("--parsed-vulnerabilities-input", type=Path,
                            help="Parsed vulnerabilities file (for dataset construction)")
    input_group.add_argument("--train-dataset-input", type=Path,
                            help="Training dataset file (for model training and upload)")
    input_group.add_argument("--validation-dataset-input", type=Path,
                            help="Validation dataset file (for model training and upload)")
    input_group.add_argument("--test-dataset-input", type=Path,
                            help="Test dataset file (for automatic evaluation during training and upload)")
    input_group.add_argument("--adapter-input", type=Path,
                            help="Trained adapter directory (for upload)")

    args = parser.parse_args()

    config = OLMoSecurityConfig()
    if not ensure_base_model_ready(config):
        logger.error("❌ Cannot proceed: Base model setup failed")
        logger.error("   Please ensure:")
        logger.error("   1. Virtual environment is activated: source ./venv/bin/activate")
        logger.error("   2. mlx-lm is installed: pip install mlx-lm")
        logger.error("   3. Internet connection is available")
        return 1

    single_phase = get_active_only_phase(args)

    if single_phase:
        # Validate inputs for single phase
        validate_phase_inputs(single_phase, args)

        print("=" * 60)
        print(f"🎯 Single Phase Execution: {single_phase}")
        print(f"Artifacts: {args.artifacts_dir}")
        print(f"Output: {args.output_dir}")
        print("=" * 60)

        # Execute single phase
        result, summary = execute_single_phase(single_phase, args)

        print(f"\n✅ Single phase '{single_phase}' completed successfully")
        print(f"Summary: {summary}")
        return result

    run_full_pipeline(str(args.artifacts_dir), args.output_dir, skip_upload=args.skip_upload)

if __name__ == "__main__":
    main()
