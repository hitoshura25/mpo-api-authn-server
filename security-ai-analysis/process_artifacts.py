import json
import sys
from pathlib import Path
import argparse
import logging

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Phase constants to avoid string repetition and typos
class Phases:
    PARSING = "parsing"
    CATEGORIZATION = "categorization"
    NARRATIVE = "narrative"

    # List for validation
    ALL_PHASES = [
        PARSING, CATEGORIZATION, NARRATIVE
    ]

    # Input requirements mapping
    PHASE_INPUTS = {
        PARSING: [],  # Uses --artifacts-dir
        CATEGORIZATION: ['parsed_input'],
        NARRATIVE: ['categorized_input'],
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
            
            structured_analysis = analysis_result.get('structured_analysis')
            if not structured_analysis:
                raise ValueError("Structured analysis returned empty result")
            ai_analysis = f"Impact: {structured_analysis.get('impact', 'N/A')}. Remediation: {structured_analysis.get('remediation', 'N/A')}. Prevention: {structured_analysis.get('prevention', 'N/A')}"
                
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
    return output_file

def get_active_only_phase(args) -> str:
    """Get the single active --only-* phase flag, or None for multi-phase"""

    only_flags = {
        Phases.PARSING: args.only_parsing,
        Phases.CATEGORIZATION: args.only_categorization,
        Phases.NARRATIVE: args.only_narrativization,
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

def run_full_pipeline(artifacts_dir: str, output_dir: Path):
    # --- Execute Pipeline Phases ---

    # Phase 1
    parsed_vulns_file = parse_vulnerabilities_phase(artifacts_dir, output_dir)
    categorized_vulns_file = categorize_vulnerabilities_phase(parsed_vulns_file, output_dir)
    narratived_file = analyze_and_narrate_phase(categorized_vulns_file, output_dir)


    # (Future phases will be called here)
    # phase_2_analyze_and_narrate(categorized_vulns_file, ...)
    logger.info("\n✅ Pipeline finished.")

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
    else:
        raise ValueError(f"Unknown phase: {phase}")

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

    # Input file arguments
    input_group = parser.add_argument_group('Phase Input Files')
    input_group.add_argument("--parsed-input", type=Path,
                            help="Parsed vulnerabilities file (for categorization)")
    input_group.add_argument("--categorized-input", type=Path,
                            help="Categorized vulnerabilities file (for narrative analysis)")
    args = parser.parse_args()

    # Check for single-phase execution
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

    run_full_pipeline(str(args.artifacts_dir), args.output_dir)

if __name__ == "__main__":
    main()
