import json
import sys
from pathlib import Path
import argparse
import logging
import subprocess
from typing import Any, Dict, List
from datetime import datetime

from config_manager import OLMoSecurityConfig
from parsers.trivy_parser import parse_trivy_json
from parsers.checkov_parser import parse_checkov_json
from parsers.sarif_parser import parse_sarif_json
from parsers.semgrep_parser import parse_semgrep_sarif
from parsers.osv_parser import parse_osv_json
from parsers.zap_parser import parse_zap_json
from vulnerability_categorizer import VulnerabilityCategorizor
from rag_enhanced_olmo_analyzer import RAGEnhancedOLMoAnalyzer
from create_narrativized_dataset import SecurityNarrativizer
from url_to_code_mapper import URLToCodeMapper
from public_dataset_loader import PublicDatasetLoader
from multi_approach_fix_generator import MultiApproachFixGenerator
from build_knowledge_base import build_knowledge_base_from_narrativized_file
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Phase constants to avoid string repetition and typos
class Phases:
    PARSING = "parsing"
    CATEGORIZATION = "categorization"
    NARRATIVE = "narrative"
    DATASETS = "datasets"
    TRAINING = "training"
    UPLOAD = "upload"

    # List for validation
    ALL_PHASES = [
        PARSING, CATEGORIZATION, NARRATIVE, DATASETS, TRAINING, UPLOAD
    ]

    # Input requirements mapping
    PHASE_INPUTS = {
        PARSING: [],  # Uses --artifacts-dir
        CATEGORIZATION: ['parsed_input'],
        NARRATIVE: ['categorized_input'],
        DATASETS: ['narrativized_input'],
        TRAINING: ['train_dataset_input', 'validation_dataset_input'],
        UPLOAD: ['adapter_input', 'train_dataset_input', 'validation_dataset_input'],
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

        if 'trivy' in file_str and file_path.suffix in ['.json', '.sarif']:
            scan_files['trivy'].append(str(file_path))
        elif 'checkov' in file_str and file_path.suffix in ['.json', '.sarif']:
            scan_files['checkov'].append(str(file_path))
        elif 'semgrep' in file_str and file_path.suffix in ['.json', '.sarif']:
            scan_files['semgrep'].append(str(file_path))
        elif 'osv' in file_str and file_path.suffix == '.json':
            scan_files['osv'].append(str(file_path))
        elif 'zap' in file_str and file_path.suffix == '.json':
            scan_files['zap'].append(str(file_path))
        elif file_path.suffix == '.sarif' and 'semgrep' not in file_str and 'trivy' not in file_str and 'checkov' not in file_str:
            scan_files['sarif'].append(str(file_path))

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
        'trivy': lambda path: parse_sarif_json(path) if path.endswith('.sarif') else parse_trivy_json(path),
        'checkov': lambda path: parse_sarif_json(path) if path.endswith('.sarif') else parse_checkov_json(path),
        'semgrep': parse_semgrep_sarif,
        'osv': parse_osv_json,
        'sarif': parse_sarif_json,
        'zap': parse_zap_json,
    }

    # Step 1: Parse vulnerabilities from all files
    for scan_type, files in scan_files.items():
        if not files:
            continue
        logger.info(f"Parsing {len(files)} files for scan type: {scan_type}")
        parser_func = parser_map.get(scan_type)
        if not parser_func:
            continue
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

def categorize_vulnerabilities_phase(parsed_vulns_file: Path, output_dir: Path) -> Path:
    """
    PHASE 2:
    - Categorizes each vulnerability by security domain.
    - Saves the aggregated, categorized list to a single JSON file.
    """
    if not parsed_vulns_file.exists():
        raise FileNotFoundError(f"Parsed vulnerabilities file not found: {parsed_vulns_file}")
    
    all_vulnerabilities = []
    with open(parsed_vulns_file, 'r') as f:
        all_vulnerabilities = json.load(f)

    if not all_vulnerabilities:
        raise ValueError("No vulnerabilities found in the parsed input file.")
    else:
        logger.info("Categorizing vulnerabilities by security domain...")
        categorizer = VulnerabilityCategorizor()
        categorized_vulnerabilities = []
        for vuln in all_vulnerabilities:
            try:
                category, confidence = categorizer.categorize_vulnerability(vuln)
                vuln['security_category'] = category
                vuln['category_confidence'] = confidence
                categorized_vulnerabilities.append(vuln)
            except Exception as e:
                raise ValueError(f"Failed to categorize vulnerability {vuln.get('id', 'N/A')}: {e}")

        logger.info(f"Successfully categorized {len(categorized_vulnerabilities)} vulnerabilities.")

    output_file = output_dir / "categorized_vulnerabilities.json"
    with open(output_file, 'w') as f:
        json.dump(categorized_vulnerabilities, f, indent=2)

    logger.info(f"✅ Phase 2 complete. Output saved to: {output_file}")
    return output_file

def analyze_and_narrate_phase(categorized_vulns_file: Path, output_dir: Path) -> Path:
    """
    PHASE: Analyze & Narrate
    - Uses RAG-enhanced analyzer to generate AI analysis for each vulnerability
    - Generates descriptive narratives using SecurityNarrativizer
    - Maps URLs to code for DAST/ZAP findings
    - Saves combined analysis to JSON file
    """
    logger.info("🚀 Starting Phase: Analyze & Narrate")

    if not categorized_vulns_file.exists():
        raise FileNotFoundError(f"Categorized vulnerabilities file not found: {categorized_vulns_file}")

    # Load categorized vulnerabilities
    with open(categorized_vulns_file, 'r') as f:
        categorized_vulnerabilities = json.load(f)

    if not categorized_vulnerabilities:
        raise ValueError("No categorized vulnerabilities found in input file")

    logger.info(f"Loaded {len(categorized_vulnerabilities)} categorized vulnerabilities")

    # Initialize analyzers once
    logger.info("Initializing RAG-enhanced analyzer and narrativizer...")
    try:
        rag_analyzer = RAGEnhancedOLMoAnalyzer(enable_rag=True)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize RAG-enhanced analyzer: {e}")

    narrativizer = SecurityNarrativizer()

    # Initialize URL-to-code mapper for ZAP findings
    project_root = Path(__file__).parent.parent
    url_mapper = URLToCodeMapper(project_root)

    # Process each vulnerability
    narrativized_analyses = []

    for idx, vuln in enumerate(categorized_vulnerabilities, 1):
        logger.info(f"Processing vulnerability {idx}/{len(categorized_vulnerabilities)}: {vuln.get('id', 'N/A')}")

        try:
            # Step 1: URL-to-code mapping for ZAP/DAST findings
            if vuln.get('tool') == 'zap' and 'url' in vuln:
                route_mapping = url_mapper.find_route_handler(vuln['url'])
                if route_mapping:
                    vuln['code_context'] = route_mapping
                    logger.info(f"  Mapped URL to code: {route_mapping.get('file_path', 'N/A')}")

            # Step 2: Generate AI analysis using RAG-enhanced analyzer
            analysis_result = rag_analyzer.analyze_vulnerability(vuln)
            analysis_result_file = output_dir / "rag_analysis" / f"{vuln.get('id', 'unknown').replace('/', '_')}_analysis.json"
            analysis_result_file.parent.mkdir(parents=True, exist_ok=True)

            with open(analysis_result_file, 'w') as f:
                json.dump(analysis_result, f, indent=2)

            # TODO: Revisit using other analysis field (i.e. raw_analysis or enhanced_analysis)
            baseline_analysis = analysis_result.get('baseline_analysis')
            if not baseline_analysis:
                raise ValueError("Baseline analysis returned empty result")
            ai_analysis = f"Impact: {baseline_analysis.get('impact', 'N/A')}. Remediation: {baseline_analysis.get('remediation', 'N/A')}. Prevention: {baseline_analysis.get('prevention', 'N/A')}"
                
            # Step 3: Generate narrative description
            narrative = narrativizer.narrativize_vulnerability(vuln)

            # Step 4: Create combined output structure
            narrativized_entry = {
                "vulnerability": vuln,
                "ai_analysis": ai_analysis,
                "narrative": narrative
            }

            narrativized_analyses.append(narrativized_entry)

        except Exception as e:
            raise RuntimeError(f"Error processing vulnerability {vuln.get('id', 'N/A')}: {e}")

    # Save output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "narrativized_analyses.json"

    with open(output_file, 'w') as f:
        json.dump(narrativized_analyses, f, indent=2)

    logger.info(f"✅ Narrativization phase complete. Narrativized {len(narrativized_analyses)} vulnerabilities")
    logger.info(f"Output saved to: {output_file}")

    # Rebuild knowledge base for future RAG-enhanced analyses
    logger.info("=" * 60)
    logger.info("🧠 Rebuilding knowledge base...")
    logger.info("=" * 60)

    if build_knowledge_base_from_narrativized_file(output_file):
        logger.info("✅ Knowledge base updated successfully")
    else:
        raise RuntimeError("Failed to update knowledge base")

    return output_file

def construct_datasets_phase(narrativized_file: Path, output_dir: Path) -> tuple[Path, Path]:
    """
    PHASE 3: Construct Datasets
    - Loads public datasets (CVEfixes)
    - Generates specific fixes for deterministic vulnerabilities
    - Processes narratives into training pairs
    - Combines and splits into train/validation sets
    """
    logger.info("🚀 Starting Phase 3: Construct Datasets")

    if not narrativized_file.exists():
        raise FileNotFoundError(f"Narrativized file not found: {narrativized_file}")

    # Load narrativized analyses
    with open(narrativized_file, 'r') as f:
        narrativized_analyses = json.load(f)

    logger.info(f"Loaded {len(narrativized_analyses)} narrativized analyses")

    all_training_pairs = []

    # SOURCE 1: Load Public Data
    logger.info("📚 Source 1: Loading public datasets...")
    public_loader = PublicDatasetLoader()
    public_examples = public_loader.load_public_datasets()  # Load all available data
    all_training_pairs.extend(public_examples)
    logger.info(f"   Added {len(public_examples)} examples from public datasets")

    # SOURCE 2: Generate Specific Fixes
    logger.info("🔧 Source 2: Generating specific fixes...")
    specific_fixes = _generate_specific_fixes(narrativized_analyses)
    all_training_pairs.extend(specific_fixes)
    logger.info(f"   Added {len(specific_fixes)} specific fix examples")

    # SOURCE 3: Process AI Narratives
    logger.info("📝 Source 3: Processing AI narratives...")
    narrative_examples = _process_narratives_to_training_pairs(narrativized_analyses, specific_fixes)
    all_training_pairs.extend(narrative_examples)
    logger.info(f"   Added {len(narrative_examples)} narrative-based examples")

    # Combine and shuffle
    logger.info(f"📊 Total training pairs: {len(all_training_pairs)}")
    random.shuffle(all_training_pairs)

    # Split 80/20 train/validation
    split_idx = int(len(all_training_pairs) * 0.8)
    train_pairs = all_training_pairs[:split_idx]
    val_pairs = all_training_pairs[split_idx:]

    logger.info(f"   Train set: {len(train_pairs)} examples")
    logger.info(f"   Validation set: {len(val_pairs)} examples")

    # Save as JSONL
    output_dir.mkdir(parents=True, exist_ok=True)
    train_file = output_dir / "train_dataset.jsonl"
    val_file = output_dir / "validation_dataset.jsonl"

    with open(train_file, 'w') as f:
        for pair in train_pairs:
            f.write(json.dumps(pair) + '\n')

    with open(val_file, 'w') as f:
        for pair in val_pairs:
            f.write(json.dumps(pair) + '\n')

    logger.info(f"✅ Phase 3 complete.")
    logger.info(f"   Train dataset: {train_file}")
    logger.info(f"   Validation dataset: {val_file}")

    return train_file, val_file


def _generate_specific_fixes(narrativized_analyses: List[Dict]) -> List[Dict[str, Any]]:
    """
    Generate specific fixes for deterministic vulnerabilities (e.g., dependency upgrades) in MLX chat format.

    Returns training pairs in MLX-compatible chat format:
    {
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ],
        "metadata": {...}
    }
    """
    specific_fixes = []
    fix_generator = MultiApproachFixGenerator()

    # System message for security analysis
    system_message = """You are a cybersecurity analyst specializing in WebAuthn and FIDO2 security vulnerabilities.

CRITICAL SECURITY GUIDELINES:
- Always prioritize security in your analysis and recommendations
- Provide actionable remediation steps for identified vulnerabilities
- Consider the broader security implications of each finding
- Maintain accuracy and precision in threat assessments
- Follow responsible disclosure principles
- Preserve safety guidelines and ethical analysis standards

Your role is to analyze security vulnerabilities and provide comprehensive, actionable guidance for remediation."""

    for analysis in narrativized_analyses:
        vuln = analysis['vulnerability']
        tool = vuln.get('tool', '')
        vuln_id = vuln.get('id', '')

        # Check for deterministic fixes (Trivy/OSV dependency vulnerabilities)
        if tool in ['trivy', 'sarif-trivy', 'osv', 'osv-scanner']:
            # Try to generate a specific fix
            try:
                # Generate fixes and check success
                result = fix_generator.generate_fixes(vuln, code_context=None)
                if not result.success:
                    logger.error(f"Fix generation failed for {vuln_id}: {result.error_message}")
                    raise RuntimeError(f"Fix generation failed for {vuln_id}: {result.error_message}")

                fixes = result.fixes
                if fixes and len(fixes) > 0:
                    primary_fix = fixes[0]  # Use the primary fix approach (SecurityFix dataclass)

                    # Create training pair in MLX chat format
                    user_content = f"Based on the following analysis, provide the fix.\n\nAnalysis: {analysis['ai_analysis']}\n\nContext: {analysis.get('narrative', '')[:500]}"

                    # SecurityFix is a dataclass - use attribute access, not dict.get()
                    assistant_content = primary_fix.fixed_code or primary_fix.description

                    if assistant_content:
                        specific_fixes.append({
                            "messages": [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_content},
                                {"role": "assistant", "content": assistant_content}
                            ],
                            "metadata": {
                                "quality": "high",
                                "source": "generated",
                                "vulnerability_id": vuln_id,
                                "tool": tool,
                                "chat_template": "chatml",
                                "security_framework": "webauthn-security-analysis"
                            }
                        })
            except Exception as e:
                # FAIL FAST - don't suppress exceptions
                logger.error(f"Could not generate specific fix for {vuln_id}: {e}")
                raise RuntimeError(f"Error generating specific fix for vulnerability {vuln_id}: {e}")

    return specific_fixes


def _process_narratives_to_training_pairs(narrativized_analyses: List[Dict], specific_fixes: List[Dict]) -> List[Dict[str, Any]]:
    """
    Process narratives into training pairs in MLX chat format.
    If a specific fix exists, use it as response. Otherwise, use narrative/analysis as response.

    Returns training pairs in MLX-compatible chat format:
    {
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ],
        "metadata": {...}
    }
    """
    narrative_pairs = []

    # Create a mapping of vulnerability IDs to specific fixes
    fix_map = {fix['metadata']['vulnerability_id']: fix for fix in specific_fixes if 'vulnerability_id' in fix.get('metadata', {})}

    # System message for security analysis
    system_message = """You are a cybersecurity analyst specializing in WebAuthn and FIDO2 security vulnerabilities.

CRITICAL SECURITY GUIDELINES:
- Always prioritize security in your analysis and recommendations
- Provide actionable remediation steps for identified vulnerabilities
- Consider the broader security implications of each finding
- Maintain accuracy and precision in threat assessments
- Follow responsible disclosure principles
- Preserve safety guidelines and ethical analysis standards

Your role is to analyze security vulnerabilities and provide comprehensive, actionable guidance for remediation."""

    for analysis in narrativized_analyses:
        vuln = analysis['vulnerability']
        vuln_id = vuln.get('id', '')

        # Check if we have a specific fix for this vulnerability
        if vuln_id in fix_map:
            # Use the specific fix (extract assistant content from messages)
            fix = fix_map[vuln_id]
            user_content = f"Based on the following analysis, provide remediation guidance.\n\nAnalysis: {analysis['ai_analysis']}\n\nContext: {analysis.get('narrative', '')[:500]}"
            # Extract assistant content from fix messages
            assistant_content = fix['messages'][2]['content']  # Assistant is the 3rd message (index 2)
            quality = "high"
        else:
            # Use narrative as fallback
            user_content = f"Based on the following analysis, provide remediation guidance.\n\nAnalysis: {analysis['ai_analysis']}\n\nContext: {analysis.get('narrative', '')[:500]}"
            assistant_content = analysis['ai_analysis']  # Use AI analysis as response
            quality = "low"

        # Create MLX chat format
        narrative_pairs.append({
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content}
            ],
            "metadata": {
                "quality": quality,
                "source": "narrative",
                "vulnerability_id": vuln_id,
                "tool": vuln.get('tool', 'unknown'),
                "chat_template": "chatml",
                "security_framework": "webauthn-security-analysis"
            }
        })

    return narrative_pairs


def train_model_phase(train_dataset: Path, validation_dataset: Path) -> Path:
    """
    PHASE 4: Train Model
    - Creates structured training run directory with manifest
    - Applies quality-weighted sampling to prioritize high-quality examples
    - Fine-tunes model using MLX LoRA
    - Saves adapter artifacts

    Args:
        train_dataset: Path to train_dataset.jsonl
        validation_dataset: Path to validation_dataset.jsonl

    Returns:
        Path to trained adapter directory
    """
    logger.info("🚀 Starting Phase 4: Train Model")
    config = OLMoSecurityConfig()

    if not train_dataset.exists():
        raise FileNotFoundError(f"Train dataset not found: {train_dataset}")
    if not validation_dataset.exists():
        raise FileNotFoundError(f"Validation dataset not found: {validation_dataset}")

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

    logger.info(f"✅ Phase 4 complete.")
    logger.info(f"   Training run: {training_run.run_dir}")
    logger.info(f"   Adapter artifacts: {adapter_path}")

    return adapter_path


def _analyze_datasets(train_file: Path, val_file: Path) -> Dict[str, Any]:
    """
    Analyze datasets for statistics to include in model/dataset cards.

    Returns:
        Dictionary with dataset statistics
    """
    stats = {
        "train_count": 0,
        "val_count": 0,
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

    return stats


def upload_artifacts_phase(
    adapter_path: Path,
    train_dataset: Path,
    validation_dataset: Path,
    skip_upload: bool = False
) -> Dict[str, Any]:
    """
    PHASE 6: Upload Artifacts to HuggingFace Hub

    Uploads model, datasets, and training artifacts with comprehensive documentation.

    Args:
        adapter_path: Path to trained model adapter
        train_dataset: Path to training dataset (train.jsonl)
        validation_dataset: Path to validation dataset (valid.jsonl)
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
    dataset_stats = _analyze_datasets(train_dataset, validation_dataset)
    logger.info(f"   Dataset statistics: {dataset_stats}")
    logger.info(f"   Train examples: {dataset_stats['train_count']}")
    logger.info(f"   Validation examples: {dataset_stats['val_count']}")
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
            upload_metadata
        )

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

    logger.info("✅ Phase 6 complete.")
    logger.info(f"   Model: {results['model_url']}")
    logger.info(f"   Dataset: {results['dataset_url']}")
    logger.info(f"   Staging: {results['staging_dir']}")

    return results


def get_active_only_phase(args) -> str:
    """Get the single active --only-* phase flag, or None for multi-phase"""

    only_flags = {
        Phases.PARSING: args.only_parsing,
        Phases.CATEGORIZATION: args.only_categorization,
        Phases.NARRATIVE: args.only_narrativization,
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

    # Phase 1: Parse
    parsed_vulns_file = parse_vulnerabilities_phase(artifacts_dir, output_dir)

    # Phase 2: Categorize
    categorized_vulns_file = categorize_vulnerabilities_phase(parsed_vulns_file, output_dir)

    # Phase 3: Analyze & Narrate
    narrativized_file = analyze_and_narrate_phase(categorized_vulns_file, output_dir)

    # Phase 4: Construct Datasets
    train_file, val_file = construct_datasets_phase(narrativized_file, output_dir)

    # Phase 5: Train Model
    adapter_path = train_model_phase(
        train_file,
        val_file
    )

    # Phase 6: Upload Artifacts
    upload_results = upload_artifacts_phase(
        adapter_path,
        train_file,
        val_file,
        skip_upload=skip_upload
    )

    logger.info("\n✅ Full pipeline completed successfully!")
    logger.info(f"   Final outputs:")
    logger.info(f"   Parsed vulnerabilities: {parsed_vulns_file}")
    logger.info(f"   Categorized vulnerabilities: {categorized_vulns_file}")
    logger.info(f"   Narrativized analyses: {narrativized_file}")
    logger.info(f"   Train dataset: {train_file}")
    logger.info(f"   Validation dataset: {val_file}")
    logger.info(f"   Adapter artifacts: {adapter_path}")
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

    elif phase == Phases.CATEGORIZATION:
        vulnerabilities_file = args.parsed_input
        categorization_file = categorize_vulnerabilities_phase(vulnerabilities_file, output_dir)
        print(f"✅ Categorization completed. Output files:")
        print(f"   Categorization  results: {categorization_file}")
        return 0, {"phase": phase, "categorization_file": str(categorization_file)}
    
    elif phase == Phases.NARRATIVE:
        categories_file = args.categorized_input
        narrativization_file = analyze_and_narrate_phase(categories_file, output_dir)
        print(f"✅ Narrativization completed. Output files:")
        print(f"   Narrativization results: {narrativization_file}")
        return 0, {"phase": phase, "narrativization_file": str(narrativization_file)}

    elif phase == Phases.DATASETS:
        narrativized_file = args.narrativized_input
        train_file, val_file = construct_datasets_phase(narrativized_file, output_dir)
        print(f"✅ Dataset construction completed. Output files:")
        print(f"   Train dataset: {train_file}")
        print(f"   Validation dataset: {val_file}")
        return 0, {"phase": phase, "train_file": str(train_file), "val_file": str(val_file)}

    elif phase == Phases.TRAINING:
        train_dataset = args.train_dataset_input
        validation_dataset = args.validation_dataset_input

        adapter_path = train_model_phase(
            train_dataset,
            validation_dataset
        )
        print(f"✅ Model training completed. Output files:")
        print(f"   Adapter artifacts: {adapter_path}")
        return 0, {"phase": phase, "adapter_path": str(adapter_path)}

    elif phase == Phases.UPLOAD:
        adapter_path = args.adapter_input
        train_dataset = args.train_dataset_input
        validation_dataset = args.validation_dataset_input
        skip_upload = getattr(args, 'skip_upload', False)

        upload_results = upload_artifacts_phase(
            adapter_path,
            train_dataset,
            validation_dataset,
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
    phase_group.add_argument("--only-categorization", action="store_true", help="Execute only categorization phase")
    phase_group.add_argument("--only-narrativization", action="store_true", help="Execute only narrative analysis phase")
    phase_group.add_argument("--only-datasets", action="store_true", help="Execute only dataset construction phase")
    phase_group.add_argument("--only-training", action="store_true", help="Execute only model training phase")
    phase_group.add_argument("--only-upload", action="store_true", help="Execute only artifact upload phase")

    # Upload control flags
    upload_group = parser.add_argument_group('Upload Options')
    upload_group.add_argument("--skip-upload", action="store_true", help="Skip artifact upload in full pipeline (default: False)")

    # Input file arguments
    input_group = parser.add_argument_group('Phase Input Files')
    input_group.add_argument("--parsed-input", type=Path,
                            help="Parsed vulnerabilities file (for categorization)")
    input_group.add_argument("--categorized-input", type=Path,
                            help="Categorized vulnerabilities file (for narrative analysis)")
    input_group.add_argument("--narrativized-input", type=Path,
                            help="Narrativized analyses file (for dataset construction)")
    input_group.add_argument("--train-dataset-input", type=Path,
                            help="Training dataset file (for model training and upload)")
    input_group.add_argument("--validation-dataset-input", type=Path,
                            help="Validation dataset file (for model training and upload)")
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
