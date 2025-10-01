#!/usr/bin/env python3
"""
Process downloaded GitHub Actions security artifacts with OLMo - Configurable Phase Architecture

This version implements a flexible 8-phase architecture with configurable execution:
1. Parsing - Extract vulnerabilities from security scan files
2. Vulnerability Analysis - Initial AI analysis of vulnerabilities
3. RAG Enhancement - Knowledge augmentation using RAG
4. Analysis Summary - Combined final analysis results
5. Narrativization - Create rich security narratives
6. Datasets - Prepare training and validation datasets
7. Training - Fine-tune models using datasets
8. Upload - Upload models and datasets to HuggingFace Hub

Individual phases can be executed using --only-* flags for isolated testing and development.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Fix HuggingFace tokenizers parallelism warning
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import zipfile
import shutil
import subprocess
import random
from typing import List, Dict, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from parsers.trivy_parser import parse_trivy_json
from parsers.checkov_parser import parse_checkov_json
from parsers.sarif_parser import parse_sarif_json
from parsers.semgrep_parser import parse_semgrep_sarif
from parsers.osv_parser import parse_osv_json
from parsers.zap_parser import parse_zap_json
from config_manager import OLMoSecurityConfig
from sequential_pipeline_integration import run_sequential_fine_tuning_phase, is_sequential_fine_tuning_available
import argparse
import logging

logger = logging.getLogger(__name__)


# Phase constants to avoid string repetition and typos
class Phases:
    PARSING = "parsing"
    VULNERABILITY_ANALYSIS = "vulnerability-analysis"
    RAG_ENHANCEMENT = "rag-enhancement"
    ANALYSIS_SUMMARY = "analysis-summary"
    NARRATIVIZATION = "narrativization"
    DATASETS = "datasets"
    TRAINING = "training"
    UPLOAD = "upload"

    # List for validation
    ALL_PHASES = [
        PARSING, VULNERABILITY_ANALYSIS, RAG_ENHANCEMENT, ANALYSIS_SUMMARY,
        NARRATIVIZATION, DATASETS, TRAINING, UPLOAD
    ]

    # Input requirements mapping
    PHASE_INPUTS = {
        PARSING: [],  # Uses --artifacts-dir
        VULNERABILITY_ANALYSIS: ['parsed_input'],
        RAG_ENHANCEMENT: ['vulnerability_analysis_input'],
        ANALYSIS_SUMMARY: ['rag_enhanced_input'],
        NARRATIVIZATION: ['analyzed_input'],
        DATASETS: ['narrativized_input', 'parsed_input'],  # Both needed
        TRAINING: ['train_input', 'validation_input', 'narrativized_input'],
        UPLOAD: ['dataset_files']  # model_dir automatically resolved via TrainingRunManager
    }


def extract_artifacts(zip_dir: str, output_dir: str):
    """
    Extract all zip files from GitHub Actions artifacts
    """
    zip_path = Path(zip_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"📦 Extracting artifacts from {zip_dir}...")

    extracted_files = []
    for zip_file in zip_path.glob("*.zip"):
        print(f"  Extracting {zip_file.name}...")

        # Create subdirectory for this artifact
        artifact_dir = output_path / zip_file.stem
        artifact_dir.mkdir(exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file, 'r') as z:
                z.extractall(artifact_dir)
                extracted_files.extend([
                    artifact_dir / name for name in z.namelist()
                ])
            print(f"    ✅ Extracted to {artifact_dir}")
        except Exception as e:
            logger.error(f"❌ CRITICAL: Artifact extraction failure for {zip_file}: {e}")
            logger.error("🔍 Artifact extraction failure indicates corrupted downloads or infrastructure issues requiring investigation")
            raise RuntimeError(f"Artifact extraction failure for {zip_file} requires investigation: {e}") from e

    return extracted_files


def find_security_files(directory: str):
    """
    Find all security scan result files in the extracted artifacts
    """
    scan_files = {
        'trivy': [],
        'checkov': [],
        'semgrep': [],
        'osv': [],
        'sarif': [],
        'zap': []
    }

    dir_path = Path(directory)

    # Search for security scan files
    for file_path in dir_path.rglob("*"):
        if not file_path.is_file():
            continue

        file_name = file_path.name.lower()
        file_str = str(file_path).lower()

        # Identify file type based on name and content
        if 'trivy' in file_str:
            if file_path.suffix in ['.json', '.sarif']:
                scan_files['trivy'].append(str(file_path))
        elif 'checkov' in file_str:
            if file_path.suffix in ['.json', '.sarif']:
                scan_files['checkov'].append(str(file_path))
        elif 'semgrep' in file_str and file_path.suffix in ['.json', '.sarif']:
            # Prefer SARIF over JSON for semgrep to avoid duplication
            # Check if we already have a semgrep file from the same directory
            file_dir = file_path.parent
            existing_semgrep = [f for f in scan_files['semgrep'] if Path(f).parent == file_dir]

            if not existing_semgrep:
                # No existing file, add this one
                scan_files['semgrep'].append(str(file_path))
            elif file_path.suffix == '.sarif':
                # Replace JSON with SARIF (prefer SARIF)
                scan_files['semgrep'] = [f for f in scan_files['semgrep'] if Path(f).parent != file_dir]
                scan_files['semgrep'].append(str(file_path))
            # If existing is SARIF and current is JSON, skip current (keep SARIF)
        elif 'osv' in file_str and file_path.suffix == '.json':
            scan_files['osv'].append(str(file_path))
        elif file_path.suffix == '.sarif' and 'semgrep' not in file_str:
            # Only add SARIF files that are NOT semgrep (to avoid duplication)
            scan_files['sarif'].append(str(file_path))
        elif 'zap' in file_str and file_path.suffix == '.json':
            scan_files['zap'].append(str(file_path))

    # Report findings
    print("\n📁 Found security scan files:")
    for scan_type, files in scan_files.items():
        if files:
            print(f"  {scan_type}: {len(files)} file(s)")
            for f in files[:3]:  # Show first 3
                print(f"    - {Path(f).name}")

    return scan_files


def parse_vulnerabilities_phase(scan_files: dict, output_dir: str) -> Tuple[List, Path, Path]:
    """
    Phase 1: Parse security scan files and extract vulnerabilities

    Input:
        - scan_files: dict with scan tool files
        - output_dir: Output directory for results

    Output Files:
        - parsed_vulnerabilities_{timestamp}.json: Array of vulnerability objects
        - parsing_summary_{timestamp}.json: Summary statistics

    Returns:
        (all_vulnerabilities: List, vulnerabilities_file: Path, summary_file: Path)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_vulnerabilities = []

    # Process each scan type with enhanced logging
    print(f"\n📂 Starting vulnerability parsing from {len(scan_files)} scan types...", flush=True)
    for scan_type, files in scan_files.items():
        if not files:
            continue

        print(f"\n📊 Processing {scan_type} scans ({len(files)} files)...", flush=True)

        for file_index, file_path in enumerate(files, 1):
            print(f"  [{file_index}/{len(files)}] Processing {Path(file_path).name}...", flush=True)

            try:
                # Parse based on type
                if scan_type == 'trivy':
                    if file_path.endswith('.sarif'):
                        vulns = parse_sarif_json(file_path)
                    else:
                        vulns = parse_trivy_json(file_path)
                elif scan_type == 'checkov':
                    if file_path.endswith('.sarif'):
                        vulns = parse_sarif_json(file_path)
                    else:
                        vulns = parse_checkov_json(file_path)
                elif scan_type == 'semgrep':
                    vulns = parse_semgrep_sarif(file_path)
                elif scan_type == 'osv':
                    vulns = parse_osv_json(file_path)
                elif scan_type == 'sarif':
                    vulns = parse_sarif_json(file_path)
                elif scan_type == 'zap':
                    vulns = parse_zap_json(file_path)
                else:
                    continue

                if vulns:
                    print(f"    Found {len(vulns)} vulnerabilities")
                    all_vulnerabilities.extend(vulns)
                else:
                    print(f"    No vulnerabilities found")

            except RuntimeError:
                # Let RuntimeError bubble up - indicates corrupted scan data requiring investigation
                raise
            except Exception as e:
                logger.error(f"❌ CRITICAL: File processing failure for {file_path}: {e}")
                logger.error("🔍 File processing failure indicates infrastructure issues or dependency problems requiring investigation")
                raise RuntimeError(f"File processing failure for {file_path} requires investigation: {e}") from e

    # Generate summary from real parsed vulnerabilities
    summary = {
        'total_analyzed': len(all_vulnerabilities),
        'successful': len(all_vulnerabilities),
        'failed': 0,
        'by_tool': {},
        'by_severity': {},
        'analysis_timestamp': datetime.now().isoformat()
    }

    # Count by tool from real parsed data
    for vuln in all_vulnerabilities:
        tool = vuln.get('tool', 'unknown')
        summary['by_tool'][tool] = summary['by_tool'].get(tool, 0) + 1

    # Create results from real parsed vulnerabilities
    results = []
    for vuln in all_vulnerabilities:
        results.append({
            'status': 'success',
            'vulnerability': vuln,
            'tool': vuln.get('tool', 'unknown'),
            'id': vuln.get('id', 'unknown')
        })

    # Save files with unique names for parsing phase
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save parsed vulnerabilities
    vulnerabilities_file = output_path / f"parsed_vulnerabilities_{timestamp}.json"
    with open(vulnerabilities_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Parsed vulnerabilities saved to: {vulnerabilities_file}")

    # Save parsing summary
    summary_file = output_path / f"parsing_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Parsing summary saved to: {summary_file}")

    print(f"📊 Parsed {len(all_vulnerabilities)} vulnerabilities successfully")
    print(f"🎯 By tool: {summary['by_tool']}")

    return all_vulnerabilities, vulnerabilities_file, summary_file


def analysis_phase(vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path, Path]:
    """
    Phase 2: AI analysis of parsed vulnerabilities

    Input:
        - vulnerabilities_file: Path to parsed_vulnerabilities_*.json from Phase 1
        - output_dir: Output directory for analysis results
        - args: Command line arguments (model_name, branch, commit, etc.)

    Output Files:
        - analyzed_vulnerabilities_{timestamp}.json: AI-analyzed vulnerability objects
        - analysis_summary_{timestamp}.json: Analysis statistics and metadata

    Returns:
        (analyzed_vulnerabilities: List, analysis_file: Path, summary_file: Path)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load vulnerabilities from Phase 1 output
    print(f"\n🔄 Loading vulnerabilities from Phase 1: {vulnerabilities_file}")
    with open(vulnerabilities_file, 'r') as f:
        parsed_results = json.load(f)

    # Extract vulnerability objects from parsing results
    all_vulnerabilities = []
    for result in parsed_results:
        if result.get('status') == 'success' and 'vulnerability' in result:
            all_vulnerabilities.append(result['vulnerability'])

    print(f"📊 Loaded {len(all_vulnerabilities)} vulnerabilities for analysis")

    # Initialize OLMo analyzer for analysis phase
    print(f"\n🤖 Initializing {args.model_name} Security Analyzer...")
    print(f"   Branch: {args.branch}")
    print(f"   Commit: {args.commit}")

    try:
        # Import OLMoSecurityAnalyzer only when needed for analysis phase
        from analysis.olmo_analyzer import OLMoSecurityAnalyzer

        # Initialize baseline analyzer first (RAG will be added post-analysis)
        print("🤖 Initializing baseline OLMo analyzer for initial vulnerability processing...")
        analyzer = OLMoSecurityAnalyzer(
            model_name=args.model_name
        )
        print("✅ Baseline OLMo analyzer initialized successfully", flush=True)
    except Exception as e:
        logger.error(f"❌ CRITICAL: OLMo analyzer initialization failure: {e}")
        logger.error("🔍 Analyzer initialization failure indicates model dependency issues or infrastructure problems requiring investigation")
        raise RuntimeError(f"OLMo analyzer initialization failure requires investigation: {e}") from e

    # Enhanced analysis with OLMo-2-1B
    if all_vulnerabilities:
        print(f"\n🔍 Starting analysis of {len(all_vulnerabilities)} total vulnerabilities with {args.model_name}...", flush=True)

        # Process ALL vulnerabilities in batches with enhanced batch size for OLMo-2-1B
        batch_size = 30 if "OLMo-2" in args.model_name else 20  # Larger batches for OLMo-2
        results = []

        print(f"📊 Will process {len(all_vulnerabilities)} vulnerabilities in batches of {batch_size}", flush=True)
        total_batches = (len(all_vulnerabilities) + batch_size - 1) // batch_size
        print(f"📊 Total batches needed: {total_batches}", flush=True)

        for i in range(0, len(all_vulnerabilities), batch_size):
            batch = all_vulnerabilities[i:i+batch_size]
            batch_end = min(i+batch_size, len(all_vulnerabilities))
            batch_num = i//batch_size + 1

            print(f"\n🔄 Starting batch {batch_num}/{total_batches}: vulnerabilities {i+1}-{batch_end} of {len(all_vulnerabilities)}", flush=True)
            print(f"   Batch size: {len(batch)} vulnerabilities", flush=True)
            print(f"   Using {args.model_name} with enhanced context length", flush=True)

            try:
                batch_results = analyzer.batch_analyze(
                    batch,
                    max_items=len(batch)
                )
                print(f"   ✅ Batch {batch_num} completed, got {len(batch_results)} results", flush=True)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"❌ CRITICAL: Enhanced analysis batch {batch_num} failure: {e}")
                logger.error("🔍 Enhanced analysis batch failure indicates model processing issues or data corruption requiring investigation")
                raise RuntimeError(f"Enhanced analysis batch {batch_num} failure requires investigation: {e}") from e

            # Optional: Add a small delay between batches to avoid overloading
            if i + batch_size < len(all_vulnerabilities):
                print("  Preparing next batch...")

        # Generate enhanced summary report
        summary = analyzer.generate_summary_report(results)
        summary['model_used'] = args.model_name
        summary['branch'] = args.branch
        summary['commit'] = args.commit
        summary['analysis_timestamp'] = datetime.now().isoformat()

        # Save results with enhanced metadata
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results (FIXED FILE NAME to match test expectations)
        analysis_file = output_path / f"analyzed_vulnerabilities_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Analysis results saved to: {analysis_file}")

        # Save summary
        summary_file = output_path / f"analysis_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"💾 Analysis summary saved to: {summary_file}")

        # Post-analysis RAG enhancement (always enabled)
        print("\n🧠 Building RAG knowledge base with fresh analysis results...")
        try:
            from build_knowledge_base import main as build_kb_main
            import sys
            from io import StringIO

            # Capture build output to avoid cluttering the main process output
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()

            try:
                # Build knowledge base using the fresh analysis results
                sys.argv = ['build_knowledge_base.py', '--results-file', str(analysis_file), '--verbose']
                build_kb_main()

                # Restore stdout for our messages
                sys.stdout = old_stdout
                print("✅ RAG knowledge base built successfully with fresh analysis data", flush=True)

                # Initialize RAG-enhanced analyzer for verification
                from rag_enhanced_olmo_analyzer import RAGEnhancedOLMoAnalyzer
                rag_analyzer = RAGEnhancedOLMoAnalyzer(
                    model_name=args.model_name,
                    enable_rag=True
                )
                rag_status = rag_analyzer.get_rag_status()

                if rag_status['status'] == 'active':
                    kb_stats = rag_status['knowledge_base']
                    print(f"📊 RAG ready: {kb_stats['total_vectors']} vulnerability patterns available for enhanced analysis", flush=True)
                    print("💡 Future runs will use RAG-enhanced analysis by default", flush=True)
                else:
                    print(f"⚠️ RAG status: {rag_status['status']} - knowledge base built but with limited functionality", flush=True)

            except Exception as inner_e:
                sys.stdout = old_stdout
                raise inner_e

        except Exception as rag_error:
            print(f"⚠️ RAG knowledge base building failed: {rag_error}")
            print("💡 This doesn't affect current analysis but RAG won't be available for next runs")

        # Print enhanced summary
        print("\n📈 Analysis Summary:")
        print(f"  Model Used: {summary.get('model_used', 'Unknown')}")
        print(f"  Total Analyzed: {summary['total_analyzed']}")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Branch: {summary.get('branch', 'Unknown')}")
        print(f"  Commit: {summary.get('commit', 'Unknown')[:8]}...")

        if summary['by_severity']:
            print("\n  By Severity:")
            for sev, count in summary['by_severity'].items():
                print(f"    {sev}: {count}")

        if summary['by_tool']:
            print("\n  By Tool:")
            for tool, count in summary['by_tool'].items():
                print(f"    {tool}: {count}")

        return results, analysis_file, summary_file
    else:
        print("\n⚠️ No vulnerabilities found to analyze")
        return [], Path(), Path()


def core_analysis_phase(vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path]:
    """
    Phase 2A: Core AI analysis of parsed vulnerabilities (without RAG)

    Input:
        - vulnerabilities_file: Path to parsed_vulnerabilities_*.json from Phase 1
        - output_dir: Output directory for core analysis results
        - args: Command line arguments (model_name, branch, commit, etc.)

    Output Files:
        - core_analysis_results_{timestamp}.json: Raw AI analysis results

    Returns:
        (analysis_results: List, core_analysis_file: Path)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load vulnerabilities from Phase 1 output
    print(f"\n🔄 Loading vulnerabilities for core analysis: {vulnerabilities_file}")
    with open(vulnerabilities_file, 'r') as f:
        parsed_results = json.load(f)

    # Extract vulnerability objects from parsing results
    all_vulnerabilities = []
    for result in parsed_results:
        if result.get('status') == 'success' and 'vulnerability' in result:
            all_vulnerabilities.append(result['vulnerability'])

    print(f"📊 Loaded {len(all_vulnerabilities)} vulnerabilities for core analysis")

    # Initialize OLMo analyzer for core analysis
    print(f"\n🤖 Initializing {args.model_name} Security Analyzer for core analysis...")

    try:
        # Import OLMoSecurityAnalyzer only when needed
        from analysis.olmo_analyzer import OLMoSecurityAnalyzer

        analyzer = OLMoSecurityAnalyzer(model_name=args.model_name)
        print("✅ Core analyzer initialized successfully", flush=True)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Core analyzer initialization failure: {e}")
        logger.error("🔍 Core analyzer initialization failure indicates model dependency issues or infrastructure problems requiring investigation")
        raise RuntimeError(f"Core analyzer initialization failure requires investigation: {e}") from e

    # Core AI analysis processing
    if all_vulnerabilities:
        print(f"\n🔍 Starting core analysis of {len(all_vulnerabilities)} vulnerabilities...", flush=True)

        # Process vulnerabilities in batches
        batch_size = 30 if "OLMo-2" in args.model_name else 20
        results = []

        print(f"📊 Processing in batches of {batch_size}", flush=True)
        total_batches = (len(all_vulnerabilities) + batch_size - 1) // batch_size

        for i in range(0, len(all_vulnerabilities), batch_size):
            batch = all_vulnerabilities[i:i+batch_size]
            batch_end = min(i+batch_size, len(all_vulnerabilities))
            batch_num = i//batch_size + 1

            print(f"\n🔄 Core analysis batch {batch_num}/{total_batches}: vulnerabilities {i+1}-{batch_end}", flush=True)

            try:
                batch_results = analyzer.batch_analyze(batch, max_items=len(batch))
                print(f"   ✅ Batch {batch_num} completed, got {len(batch_results)} results", flush=True)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"❌ CRITICAL: Core analysis batch {batch_num} failure: {e}")
                logger.error("🔍 Core analysis batch failure indicates model processing issues or data corruption requiring investigation")
                raise RuntimeError(f"Core analysis batch {batch_num} failure requires investigation: {e}") from e

        # Save core analysis results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        core_analysis_file = output_path / f"core_analysis_results_{timestamp}.json"

        with open(core_analysis_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Core analysis results saved to: {core_analysis_file}")

        return results, core_analysis_file
    else:
        print("\n⚠️ No vulnerabilities found for core analysis")
        return [], Path()


def rag_enhancement_phase(core_analysis_file: Path, output_dir: str, args) -> Tuple[List, Path]:
    """
    Phase 2B: RAG enhancement of core analysis results

    Input:
        - core_analysis_file: Path to core_analysis_results_*.json from Phase 2A
        - output_dir: Output directory for RAG-enhanced results
        - args: Command line arguments

    Output Files:
        - rag_enhanced_analysis_{timestamp}.json: RAG-enhanced analysis results

    Returns:
        (enhanced_results: List, rag_enhanced_file: Path)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load core analysis results
    print(f"\n🔄 Loading core analysis results for RAG enhancement: {core_analysis_file}")
    with open(core_analysis_file, 'r') as f:
        results = json.load(f)

    print(f"📊 Loaded {len(results)} analysis results for RAG enhancement")

    # RAG enhancement (always enabled)
    print("\n🧠 Building RAG knowledge base with fresh analysis results...")
    try:
        from build_knowledge_base import main as build_kb_main
        import sys
        from io import StringIO

        # Capture build output to avoid cluttering the main process output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            # Build knowledge base using the fresh analysis results
            sys.argv = ['build_knowledge_base.py', '--results-file', str(core_analysis_file), '--verbose']
            build_kb_main()

            # Restore stdout for our messages
            sys.stdout = old_stdout
            print("✅ RAG knowledge base built successfully with fresh analysis data", flush=True)

            # Initialize RAG-enhanced analyzer for verification
            from rag_enhanced_olmo_analyzer import RAGEnhancedOLMoAnalyzer
            rag_analyzer = RAGEnhancedOLMoAnalyzer(
                model_name=args.model_name,
                enable_rag=True
            )
            rag_status = rag_analyzer.get_rag_status()

            if rag_status['status'] == 'active':
                kb_stats = rag_status['knowledge_base']
                print(f"📊 RAG ready: {kb_stats['total_vectors']} vulnerability patterns available", flush=True)
                print("💡 Future runs will use RAG-enhanced analysis by default", flush=True)
            else:
                print(f"⚠️ RAG status: {rag_status['status']} - knowledge base built but with limited functionality", flush=True)

        except Exception as inner_e:
            sys.stdout = old_stdout
            raise inner_e

    except Exception as rag_error:
        logger.error(f"❌ CRITICAL: RAG knowledge base building failure: {rag_error}")
        logger.error("🔍 RAG knowledge base building failure indicates data corruption or dependency issues requiring investigation")
        raise RuntimeError(f"RAG knowledge base building failure requires investigation: {rag_error}") from rag_error

    # Save RAG-enhanced results (same content, but indicates RAG processing completed)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rag_enhanced_file = output_path / f"rag_enhanced_analysis_{timestamp}.json"

    with open(rag_enhanced_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 RAG-enhanced analysis saved to: {rag_enhanced_file}")

    return results, rag_enhanced_file


def analysis_summary_phase(rag_enhanced_file: Path, output_dir: str, args) -> Tuple[List, Path, Path]:
    """
    Phase 2C: Generate analysis summary and final formatted results

    Input:
        - rag_enhanced_file: Path to rag_enhanced_analysis_*.json from Phase 2B
        - output_dir: Output directory for final analysis results
        - args: Command line arguments (model_name, branch, commit, etc.)

    Output Files:
        - analyzed_vulnerabilities_{timestamp}.json: Final analysis results (for integration tests)
        - analysis_summary_{timestamp}.json: Analysis statistics and metadata

    Returns:
        (analysis_results: List, analysis_file: Path, summary_file: Path)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load RAG-enhanced analysis results
    print(f"\n🔄 Loading RAG-enhanced results for summary generation: {rag_enhanced_file}")
    with open(rag_enhanced_file, 'r') as f:
        results = json.load(f)

    print(f"📊 Loaded {len(results)} enhanced results for summary generation")

    # **URL-to-Code Mapping Enhancement**
    print(f"🗺️ Applying URL-to-code mapping to enhance ZAP/DAST vulnerabilities...")
    try:
        from url_to_code_mapper import URLToCodeMapper, enhance_vulnerability_with_url_mapping

        # Initialize URL mapper with project root
        project_root = Path.cwd().parent  # Go up one level from security-ai-analysis to project root
        url_mapper = URLToCodeMapper(project_root=project_root)
        enhanced_count = 0

        for result in results:
            if result.get('status') == 'success' and 'vulnerability' in result:
                vulnerability = result['vulnerability']

                # Apply URL-to-code mapping for ZAP and other URL-based vulnerabilities
                if enhance_vulnerability_with_url_mapping(vulnerability, url_mapper):
                    enhanced_count += 1

        print(f"✅ URL-to-code mapping completed: {enhanced_count} vulnerabilities enhanced")

    except Exception as e:
        logger.error(f"❌ CRITICAL: URL-to-code mapping failure: {e}")
        logger.error("🔍 URL-to-code mapping failure indicates infrastructure or dependency issues requiring investigation")
        raise RuntimeError(f"URL-to-code mapping failure requires investigation: {e}") from e

    # Generate summary report (need to recreate analyzer for summary generation)
    try:
        from analysis.olmo_analyzer import OLMoSecurityAnalyzer
        analyzer = OLMoSecurityAnalyzer(model_name=args.model_name)

        summary = analyzer.generate_summary_report(results)
        summary['model_used'] = args.model_name
        summary['branch'] = args.branch
        summary['commit'] = args.commit
        summary['analysis_timestamp'] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"❌ CRITICAL: Analysis summary generation failure: {e}")
        logger.error("🔍 Analysis summary generation failure indicates model dependency issues or data corruption requiring investigation")
        raise RuntimeError(f"Analysis summary generation failure requires investigation: {e}") from e

    # Save final results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save final analysis results (CRITICAL: This file name is expected by integration tests)
    analysis_file = output_path / f"analyzed_vulnerabilities_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Final analysis results saved to: {analysis_file}")

    # Save analysis summary
    summary_file = output_path / f"analysis_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Analysis summary saved to: {summary_file}")

    # Print enhanced summary
    print("\n📈 Analysis Summary:")
    print(f"  Model Used: {summary.get('model_used', 'Unknown')}")
    print(f"  Total Analyzed: {summary['total_analyzed']}")
    print(f"  Successful: {summary['successful']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Branch: {summary.get('branch', 'Unknown')}")
    print(f"  Commit: {summary.get('commit', 'Unknown')[:8]}...")

    if summary.get('by_severity'):
        print("\n  By Severity:")
        for sev, count in summary['by_severity'].items():
            print(f"    {sev}: {count}")

    if summary.get('by_tool'):
        print("\n  By Tool:")
        for tool, count in summary['by_tool'].items():
            print(f"    {tool}: {count}")

    return results, analysis_file, summary_file


def narrativization_phase(analyzed_vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path]:
    """
    Phase 3: Create rich security narratives from analyzed vulnerabilities

    Args:
        analyzed_vulnerabilities_file: Path to analyzed vulnerabilities JSON file
        output_dir: Output directory for narrativized dataset
        args: Command line arguments

    Returns:
        (narrativized_results: List, narrativized_file: Path)
    """
    output_path = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"🔄 Loading analyzed vulnerabilities: {analyzed_vulnerabilities_file}")
    with open(analyzed_vulnerabilities_file, 'r') as f:
        analyzed_results = json.load(f)

    print(f"📊 Loaded {len(analyzed_results)} analyzed vulnerabilities for narrativization")

    # Import narrativizer (only when needed)
    try:
        from create_narrativized_dataset import SecurityNarrativizer
        narrativizer = SecurityNarrativizer()
        print("✅ SecurityNarrativizer initialized successfully")
    except ImportError as e:
        logger.error(f"❌ CRITICAL: SecurityNarrativizer dependency missing: {e}")
        logger.error("🔍 SecurityNarrativizer dependency missing indicates installation or environment issues requiring investigation")
        raise RuntimeError(f"SecurityNarrativizer dependency missing - requires investigation: {e}") from e

    narrativized_results = []
    print(f"📝 Creating narratives for {len(analyzed_results)} analysis results...")

    for item in analyzed_results:
        if item.get('status') == 'success':
            vuln_data = item.get('vulnerability', {})

            # Create narrativized version
            try:
                narrative = narrativizer.narrativize_vulnerability(vuln_data)

                narrativized_item = {
                    'vulnerability_id': vuln_data.get('id', 'unknown'),
                    'original_analysis': item.get('analysis', ''),
                    'narrative': narrative,
                    'created_at': timestamp
                }

                narrativized_results.append(narrativized_item)

            except Exception as e:
                logger.error(f"❌ CRITICAL: Narrativization failure for vulnerability {vuln_data.get('id', 'unknown')}: {e}")
                logger.error("🔍 Narrativization failure indicates model processing issues or data corruption requiring investigation")
                raise RuntimeError(f"Narrativization failure for vulnerability {vuln_data.get('id', 'unknown')} requires investigation: {e}") from e

    # Save narrativized dataset
    narrativized_file = output_path / f"narrativized_dataset_{timestamp}.json"
    with open(narrativized_file, 'w') as f:
        json.dump(narrativized_results, f, indent=2)

    print(f"💾 Narrativized dataset saved to: {narrativized_file}")
    print(f"📊 Created {len(narrativized_results)} narratives")

    return narrativized_results, narrativized_file


def datasets_phase(narrativized_file: Path, vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path, Path]:
    """
    Phase 4: Prepare training and validation datasets with enhanced code-aware examples

    Args:
        narrativized_file: Path to narrativized dataset JSON file
        vulnerabilities_file: Path to raw vulnerability data from parsing phase
        output_dir: Output directory for dataset files
        args: Command line arguments

    Returns:
        (training_pairs: List, train_file: Path, validation_file: Path)
    """
    output_path = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"🔄 Loading narrativized results: {narrativized_file}")
    with open(narrativized_file, 'r') as f:
        narrativized_results = json.load(f)

    print(f"📚 Preparing fine-tuning dataset from {len(narrativized_results)} narratives...")

    # **Standard Training Pairs (Original)**
    training_pairs = []

    for item in narrativized_results:
        # Create training pair
        vulnerability_info = f"Vulnerability ID: {item['vulnerability_id']}"

        training_pair = {
            'instruction': f"Analyze this security vulnerability and provide remediation guidance:\\n\\n{vulnerability_info}",
            'response': item['narrative'],
            'metadata': {
                'vulnerability_id': item['vulnerability_id'],
                'created_at': timestamp
            }
        }

        training_pairs.append(training_pair)

    # **Enhanced Training Pairs (Code-Aware)**
    print(f"🚀 Creating enhanced code-aware training dataset...")
    try:
        from enhanced_dataset_creator import EnhancedDatasetCreator, EnumJSONEncoder

        # Load raw vulnerability data for enhanced dataset creator
        print(f"🔄 Loading raw vulnerability data: {vulnerabilities_file}")
        with open(vulnerabilities_file, 'r') as f:
            raw_vulnerability_data = json.load(f)

        # Extract successful vulnerability objects for enhancement
        raw_vulnerabilities = []
        for item in raw_vulnerability_data:
            if item.get('status') == 'success' and 'vulnerability' in item:
                raw_vulnerabilities.append(item['vulnerability'])

        print(f"📊 Loaded {len(raw_vulnerabilities)} raw vulnerabilities for code-aware enhancement")

        # Get dataset name for enhanced creation
        dataset_name = f"webauthn-security-vulnerabilities-{timestamp}"

        creator = EnhancedDatasetCreator()
        enhanced_result = creator.create_enhanced_dataset(
            raw_vulnerabilities,  # ✅ FIXED: Now using raw vulnerability data
            dataset_name=dataset_name
        )

        if enhanced_result.success:
            print(f"✅ Enhanced dataset creation successful!")
            print(f"  📊 Original examples: {enhanced_result.creation_metadata.get('original_count', 0)}")
            print(f"  🚀 Enhanced examples: {enhanced_result.creation_metadata.get('enhanced_count', 0)}")
            print(f"  🎯 Enhancement ratio: {enhanced_result.creation_metadata.get('enhancement_ratio', 0):.1f}x")

            # Convert enhanced examples to training pairs format
            enhanced_training_pairs = []
            for example in enhanced_result.enhanced_examples:
                enhanced_training_pairs.append({
                    'instruction': example.instruction,
                    'response': example.response,
                    'metadata': example.metadata
                })

            if dataset_name:
                enhanced_result.creation_metadata['dataset_name'] = dataset_name
            print(f"💾 Enhanced dataset saved to: enhanced_datasets/code-aware-training/")

            # Combine with standard training pairs for comprehensive dataset
            combined_training_pairs = training_pairs + enhanced_training_pairs
            print(f"🔗 Combined dataset: {len(training_pairs)} standard + {len(enhanced_training_pairs)} enhanced = {len(combined_training_pairs)} total")

            # Use combined dataset for training
            training_pairs = combined_training_pairs

        else:
            print(f"⚠️ Enhanced dataset creation failed: {enhanced_result.error_message}")

    except ImportError as e:
        print(f"⚠️ Enhanced dataset creator not available: {e}")
        print(f"   Continuing with standard narrativized dataset only...")

    # Split into training and validation sets (80/20)
    random.shuffle(training_pairs)
    split_point = int(len(training_pairs) * 0.8)
    train_data = training_pairs[:split_point]
    val_data = training_pairs[split_point:]

    # Determine which JSON encoder to use
    try:
        from enhanced_dataset_creator import EnumJSONEncoder
        json_encoder = EnumJSONEncoder
        print("✅ Using EnumJSONEncoder for proper enum serialization")
    except ImportError:
        json_encoder = None
        print("⚠️ EnumJSONEncoder not available, using default JSON encoder")

    # Save training set
    train_file = output_path / f"train_{timestamp}.jsonl"
    with open(train_file, 'w') as f:
        for item in train_data:
            f.write(json.dumps(item, cls=json_encoder) + '\n')

    # Save validation set
    validation_file = output_path / f"validation_{timestamp}.jsonl"
    with open(validation_file, 'w') as f:
        for item in val_data:
            f.write(json.dumps(item, cls=json_encoder) + '\n')

    print(f"💾 Training dataset saved to: {train_file}")
    print(f"💾 Validation dataset saved to: {validation_file}")
    print(f"📊 Dataset split: {len(train_data)} training, {len(val_data)} validation examples")

    # Save dataset metadata
    dataset_info = {
        'created_at': timestamp,
        'total_examples': len(training_pairs),
        'train_examples': len(train_data),
        'validation_examples': len(val_data),
        'source_vulnerabilities': len(narrativized_results)
    }

    dataset_info_file = output_path / f"dataset_info_{timestamp}.json"
    with open(dataset_info_file, 'w') as f:
        json.dump(dataset_info, f, indent=2)

    print(f"💾 Dataset info saved to: {dataset_info_file}")

    # Store metadata for upload phase instead of uploading directly
    print(f"💾 Storing dataset metadata for upload phase...")

    # Check if enhanced dataset creator is available for proper enum serialization
    json_encoder_available = False
    try:
        from enhanced_dataset_creator import EnumJSONEncoder
        json_encoder_available = True
        print("✅ EnumJSONEncoder available for upload phase")
    except ImportError:
        print("⚠️ EnumJSONEncoder not available, will use default JSON encoder")

    # Store upload metadata on args object for upload phase to use
    args.dataset_upload_metadata = {
        'training_pairs': training_pairs,
        'json_encoder_available': json_encoder_available,
        'dataset_name': 'hitoshura25/webauthn-security-vulnerabilities-olmo',
        'repo_type': 'dataset',
        'private': False,
        'created_at': timestamp,
        'local_files': {
            'train_file': str(train_file),
            'validation_file': str(validation_file)
        }
    }

    print(f"✅ Dataset metadata stored for upload phase")
    print(f"📊 {len(training_pairs)} training examples ready for upload")
    print(f"🎯 Target: hitoshura25/webauthn-security-vulnerabilities-olmo")
    print(f"📁 Upload will be handled by upload phase (use --only-upload to upload separately)")

    return training_pairs, train_file, validation_file


def training_phase(train_file: Path, train_data: List, narrativized_results: List, summary: Dict, args) -> Tuple[Dict, Path]:
    """
    Phase 5: Fine-tune models using prepared training datasets

    Args:
        train_file: Path to training JSONL file
        train_data: List of training examples
        narrativized_results: List of narrativized vulnerabilities for sequential training
        summary: Current analysis summary dict
        args: Command line arguments

    Returns:
        (updated_summary: Dict, model_artifacts_path: Path)
    """
    print(f"🔄 Starting model fine-tuning phase...")

    # **Sequential Fine-Tuning (Always Enabled)**
    # Progressive specialization: Stage 1 (Analysis) → Stage 2 (Code Fixes)
    # Training phase never uploads - always save locally only

    # Use configuration-based path management
    config = OLMoSecurityConfig()
    model_artifacts_path = Path(config.fine_tuned_models_dir).expanduser()
    print(f"📁 Using configured fine-tuned models directory: {model_artifacts_path}")

    # Sequential fine-tuning (mandatory - fail if not available)
    from sequential_pipeline_integration import run_sequential_fine_tuning_phase, is_sequential_fine_tuning_available

    if not is_sequential_fine_tuning_available():
        raise RuntimeError("Sequential fine-tuning is not available but is required. Please check your environment setup.")

    print("🎯 Sequential Fine-Tuning (Always Enabled)")
    print("📁 Training phase: Saving models locally only (uploads handled by separate phase)")
    updated_summary = run_sequential_fine_tuning_phase(
        vulnerabilities=narrativized_results,  # Use full vulnerability data with narratives
        summary=summary
    )
    print("✅ Sequential fine-tuning completed successfully")
    return updated_summary, model_artifacts_path


def upload_phase(model_artifacts_path: Path, summary: Dict, args) -> Dict:
    """
    Phase 6: Upload models and datasets to HuggingFace Hub

    Args:
        model_artifacts_path: Path to model artifacts (can be string or Path)
        summary: Current summary dict
        args: Command line arguments

    Returns:
        updated_summary: Dict with upload status
    """
    skip_upload = getattr(args, 'skip_model_upload', False)

    if skip_upload:
        print("🛑 Upload skipped (--skip-model-upload flag)")
        summary['upload_status'] = 'skipped'
        return summary

    print(f"📤 Starting upload phase...")
    print(f"🔄 This phase handles both model and dataset uploads to HuggingFace Hub")

    # Convert to Path object if string
    if isinstance(model_artifacts_path, str):
        model_artifacts_path = Path(model_artifacts_path)

    upload_results = {
        'models_uploaded': 0,
        'datasets_uploaded': 0,
        'errors': []
    }

    try:
        # 1. Upload Models
        print(f"📦 Uploading models from: {model_artifacts_path}")
        models_uploaded = _upload_models(model_artifacts_path, upload_results, args)

        # 2. Upload Datasets
        print(f"📊 Uploading datasets...")
        datasets_uploaded = _upload_datasets(args, upload_results)

        # Update summary with results
        summary['upload_status'] = 'completed'
        summary['upload_results'] = {
            'models_uploaded': models_uploaded,
            'datasets_uploaded': datasets_uploaded,
            'total_uploads': models_uploaded + datasets_uploaded
        }

        if upload_results['errors']:
            summary['upload_results']['errors'] = upload_results['errors']
            print(f"⚠️  Upload completed with {len(upload_results['errors'])} warnings/errors")

        print(f"✅ Upload phase completed successfully")
        print(f"   Models uploaded: {models_uploaded}")
        print(f"   Datasets uploaded: {datasets_uploaded}")

    except ValueError as e:
        # Re-raise validation errors to fail fast at the top level
        if "Model validation failed" in str(e) or "Invalid model structure" in str(e):
            print(f"❌ FAIL FAST: Upload phase failed due to validation error: {e}")
            summary['upload_status'] = 'failed'
            summary['upload_error'] = str(e)
            raise  # Re-raise to fail the entire process
        else:
            print(f"❌ Upload phase failed: {e}")
            summary['upload_status'] = 'failed'
            summary['upload_error'] = str(e)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Upload phase failure: {e}")
        logger.error("🔍 Upload phase failure indicates dependency issues or infrastructure problems requiring investigation")
        raise RuntimeError(f"Upload phase failure requires investigation: {e}") from e

    return summary



def _get_latest_structured_model() -> Path:
    """
    Get the latest trained model using structured TrainingRunManager.

    Returns the Stage 2 final model from the most recently completed training run.

    Returns:
        Path to the final model directory
    """
    from config_manager import OLMoSecurityConfig
    from training_run_manager import TrainingRunManager

    try:
        config = OLMoSecurityConfig()
        training_run_manager = TrainingRunManager(config)

        # Get the latest completed training run
        latest_run = training_run_manager.get_latest_run()

        print(f"🎯 Found latest training run: {latest_run.run_id}")

        # Get the Stage 2 final model (complete model for upload)
        stage2_final_model = latest_run.stage2_final_model_path

        print(f"📋 Selected Stage 2 final model: {stage2_final_model}")
        return stage2_final_model

    except FileNotFoundError as e:
        raise RuntimeError(f"No completed training runs found. {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to find latest model using structured discovery: {e}")


def _upload_models(model_artifacts_path: Path, upload_results: dict, args) -> int:
    """
    Upload trained models to HuggingFace Hub

    Returns:
        Number of models uploaded
    """
    models_uploaded = 0

    try:
        print(f"📤 Uploading models to HuggingFace Hub...")

        if not model_artifacts_path or not model_artifacts_path.exists():
            print(f"⚠️  Model artifacts path not found: {model_artifacts_path}")
            upload_results['errors'].append(f"Model artifacts path not found: {model_artifacts_path}")
            return models_uploaded

        print(f"🔍 Scanning for models in: {model_artifacts_path}")

        # Import model uploader for upload functionality
        from model_uploader import ModelUploader
        from datetime import datetime

        # Initialize model uploader with skip flag support
        skip_upload = getattr(args, 'skip_model_upload', False)
        uploader = ModelUploader(skip_upload=skip_upload)

        # Use structured TrainingRunManager to find the latest model
        try:
            actual_model_path = _get_latest_structured_model()
            print(f"🎯 Found structured model directory: {actual_model_path}")
        except RuntimeError as e:
            raise RuntimeError(f"Failed to find trained model using structured discovery: {e}. "
                             "Legacy discovery has been removed - ensure training creates structured output.")

        if not actual_model_path.exists():
            print(f"⚠️  Model path not found: {actual_model_path}")
            upload_results['errors'].append(f"Model path not found: {actual_model_path}")
            return models_uploaded

        print(f"📁 Using model artifacts: {actual_model_path}")

        # Upload the entire fine-tuned model directory
        # This handles MLX adapters, safetensors files, and complete model structures
        try:
            print(f"📦 Uploading fine-tuned model: {actual_model_path}")

            # Generate a model name based on the directory if it has a timestamp, otherwise use current timestamp
            if actual_model_path.name.startswith('webauthn-security-sequential_'):
                # Use the existing timestamp from the directory name
                model_name = actual_model_path.name
            else:
                # Generate a new timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                model_name = f"webauthn-security-model_{timestamp}"

            # Upload using ModelUploader
            hub_url = uploader.upload_to_huggingface(
                model_path=actual_model_path,
                custom_repo_name=model_name
            )

            if hub_url:
                print(f"✅ Model uploaded successfully: {hub_url}")
                models_uploaded += 1
            else:
                error_msg = f"Model upload failed for: {actual_model_path}"
                print(f"❌ {error_msg}")
                upload_results['errors'].append(error_msg)

        except ValueError as e:
            # Re-raise validation errors to fail fast (don't convert to warnings)
            if "Model validation failed" in str(e) or "Invalid model structure" in str(e):
                print(f"❌ FAIL FAST: {e}")
                raise  # Re-raise to fail the entire process
            else:
                # Other ValueError types can be handled as errors
                error_msg = f"Model upload failed for {actual_model_path}: {e}"
                print(f"❌ {error_msg}")
                upload_results['errors'].append(error_msg)
        except Exception as e:
            logger.error(f"❌ CRITICAL: Model upload failure for {actual_model_path}: {e}")
            logger.error("🔍 Model upload failure indicates dependency issues or infrastructure problems requiring investigation")
            raise RuntimeError(f"Model upload failure for {actual_model_path} requires investigation: {e}") from e

        if models_uploaded > 0:
            print(f"✅ Successfully uploaded {models_uploaded} models")
        else:
            print(f"⚠️  No models were uploaded successfully")

    except ImportError as e:
        logger.error(f"❌ CRITICAL: MLX fine tuner dependency missing for model upload: {e}")
        logger.error("🔍 MLX fine tuner dependency missing - check installation and environment setup")
        raise RuntimeError(f"MLX fine tuner dependency missing - requires investigation: {e}") from e
    except ValueError as e:
        # Re-raise validation errors to fail fast at the top level
        if "Model validation failed" in str(e) or "Invalid model structure" in str(e):
            print(f"❌ FAIL FAST (outer): {e}")
            raise  # Re-raise to fail the entire process
        else:
            logger.error(f"❌ CRITICAL: Model upload failure (ValueError): {e}")
            logger.error("🔍 Model upload ValueError indicates validation or configuration issues requiring investigation")
            raise RuntimeError(f"Model upload failure (ValueError) requires investigation: {e}") from e
    except Exception as e:
        logger.error(f"❌ CRITICAL: Model upload failure (general): {e}")
        logger.error("🔍 Model upload failure indicates dependency issues or infrastructure problems requiring investigation")
        raise RuntimeError(f"Model upload failure requires investigation: {e}") from e

    return models_uploaded


def _upload_datasets(args, upload_results: dict) -> int:
    """
    Upload training datasets to HuggingFace Hub

    Returns:
        Number of datasets uploaded
    """
    datasets_uploaded = 0

    try:
        # Check for dataset metadata from datasets phase
        dataset_metadata = getattr(args, 'dataset_upload_metadata', None)
        if not dataset_metadata:
            print(f"ℹ️  No dataset upload metadata found - datasets phase may not have run")
            return datasets_uploaded

        print(f"📤 Uploading datasets to HuggingFace Hub...")
        print(f"🎯 Target: hitoshura25/webauthn-security-vulnerabilities-olmo")

        # Import HuggingFace libraries
        from datasets import Dataset
        from huggingface_hub import HfApi

        # Get training pairs and serialization info from metadata
        training_pairs = dataset_metadata.get('training_pairs', [])
        json_encoder_available = dataset_metadata.get('json_encoder_available', False)

        if not training_pairs:
            print(f"⚠️  No training pairs found in metadata")
            return datasets_uploaded

        print(f"📊 Processing {len(training_pairs)} training pairs for upload...")

        # Determine JSON encoder (same logic as datasets phase)
        json_encoder = None
        if json_encoder_available:
            try:
                from enhanced_dataset_creator import EnumJSONEncoder
                json_encoder = EnumJSONEncoder
                print("✅ Using EnumJSONEncoder for proper enum serialization")
            except ImportError:
                print("⚠️ EnumJSONEncoder not available, using default JSON encoder")

        # ✅ CRITICAL FIX: Serialize FixApproach enums before Dataset.from_list()
        # This prevents Apache Arrow serialization errors with enum objects
        serialized_training_pairs = []
        for pair in training_pairs:
            try:
                # Test serialization to catch enum issues
                serialized_pair = json.loads(json.dumps(pair, cls=json_encoder))
                serialized_training_pairs.append(serialized_pair)
            except Exception as e:
                logger.error(f"❌ CRITICAL: Training pair serialization failure: {e}")
                logger.error("🔍 Training pair serialization failure indicates data corruption or enum handling issues requiring investigation")
                raise RuntimeError(f"Training pair serialization failure requires investigation: {e}") from e

        print(f"✅ Serialized {len(serialized_training_pairs)} training pairs for upload")

        # Create HuggingFace Dataset from serialized training pairs
        dataset = Dataset.from_list(serialized_training_pairs)

        # Upload to production dataset (PUBLIC)
        dataset.push_to_hub(
            "hitoshura25/webauthn-security-vulnerabilities-olmo",
            token=True,  # Use default HF token
            private=False  # Public dataset
        )

        print(f"✅ SUCCESS: Production dataset updated!")
        print(f"🔗 Dataset URL: https://huggingface.co/datasets/hitoshura25/webauthn-security-vulnerabilities-olmo")
        print(f"📊 Uploaded {len(training_pairs)} training examples")

        datasets_uploaded = 1

    except ImportError as e:
        logger.error(f"❌ CRITICAL: HuggingFace libraries dependency missing for dataset upload: {e}")
        logger.error("🔍 HuggingFace libraries dependency missing - install with: pip install datasets huggingface_hub")
        raise RuntimeError(f"HuggingFace libraries dependency missing - requires investigation: {e}") from e
    except Exception as e:
        logger.error(f"❌ CRITICAL: Dataset upload failure: {e}")
        logger.error("🔍 Dataset upload failure indicates dependency issues or infrastructure problems requiring investigation")
        raise RuntimeError(f"Dataset upload failure requires investigation: {e}") from e

    return datasets_uploaded


def load_results_from_files(results_file: Path, summary_data) -> Tuple[List, Dict]:
    """
    Helper function to load results from file and return with summary

    Args:
        results_file: Path to results JSON file
        summary_data: Either Path to summary file or Dict with summary data

    Returns:
        Tuple of (results_list, summary_dict)
    """
    # Load results from file
    if results_file.exists():
        with open(results_file, 'r') as f:
            results = json.load(f)
    else:
        results = []

    # Load summary from file or use provided dict
    if isinstance(summary_data, Path) and summary_data.exists():
        with open(summary_data, 'r') as f:
            summary = json.load(f)
    elif isinstance(summary_data, dict):
        summary = summary_data
    else:
        summary = {}

    return results, summary


def process_all_scans_enhanced(scan_files: dict, output_dir: str, args) -> Tuple[List, Dict]:
    """
    Orchestrates security analysis phases with --stop-after support

    Complete 6-Phase Architecture:
        1. Parsing - Extract vulnerabilities from security scan files
        2A. Core Analysis - AI processing without RAG
        2B. RAG Enhancement - Knowledge base building and enhancement
        2C. Analysis Summary - Summary generation and formatting
        3. Narrativization - Create rich security narratives
        4. Datasets - Prepare training and validation datasets with enhanced examples
        5. Training - Fine-tune models using sequential or single-stage approaches
        6. Upload - Upload models and datasets to HuggingFace Hub

    Stop-After Options:
        parsing, core-analysis, rag-enhancement, analysis, narrativization, datasets, training, upload
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n🚀 Starting complete security analysis pipeline")
    print(f"📂 Output directory: {output_path}")

    # Phase 1: Always run parsing
    print(f"\n" + "="*60)
    print(f"📋 PHASE 1: PARSING")
    print(f"="*60)
    all_vulnerabilities, vulnerabilities_file, parsing_summary_file = parse_vulnerabilities_phase(scan_files, output_dir)

    # Phase 2A: Core AI Analysis
    print(f"\n" + "="*60)
    print(f"🤖 PHASE 2A: CORE AI ANALYSIS")
    print(f"="*60)
    core_analysis_results, core_analysis_file = core_analysis_phase(vulnerabilities_file, output_dir, args)

    # Phase 2B: RAG Enhancement
    print(f"\n" + "="*60)
    print(f"🧠 PHASE 2B: RAG ENHANCEMENT")
    print(f"="*60)
    rag_enhanced_results, rag_enhanced_file = rag_enhancement_phase(core_analysis_file, output_dir, args)

    # Phase 2C: Analysis Summary
    print(f"\n" + "="*60)
    print(f"📊 PHASE 2C: ANALYSIS SUMMARY")
    print(f"="*60)
    analyzed_vulnerabilities, analysis_file, analysis_summary_file = analysis_summary_phase(rag_enhanced_file, output_dir, args)

    # Phase 3: Narrativization
    print(f"\n" + "="*60)
    print(f"🎯 PHASE 3: NARRATIVIZATION")
    print(f"="*60)
    narrativized_results, narrativized_file = narrativization_phase(analysis_file, output_dir, args)

    # Phase 4: Datasets
    print(f"\n" + "="*60)
    print(f"🚀 PHASE 4: DATASETS")
    print(f"="*60)
    training_pairs, train_file, validation_file = datasets_phase(narrativized_file, vulnerabilities_file, output_dir, args)

    # Phase 5: Training
    print(f"\n" + "="*60)
    print(f"🏋️ PHASE 5: TRAINING")
    print(f"="*60)

    # Load analysis summary for training phase
    with open(analysis_summary_file, 'r') as f:
        analysis_summary = json.load(f)

    # Extract training data for compatibility with legacy integrations
    train_data = []
    with open(train_file, 'r') as f:
        for line in f:
            train_data.append(json.loads(line.strip()))

    updated_summary, model_artifacts_path = training_phase(
        train_file, train_data, narrativized_results, analysis_summary, args
    )

    # Phase 6: Upload
    print(f"\n" + "="*60)
    print(f"📤 PHASE 6: UPLOAD")
    print(f"="*60)
    final_summary = upload_phase(model_artifacts_path, updated_summary, args)

    print(f"\n✅ All 6 phases completed successfully")
    return [], final_summary


def artifact_download_phase(artifacts_dir: Path) -> str:
    """
    Phase 0: Artifact Download and Preparation

    Handles artifact directory validation, downloading, and extraction.
    Returns the search directory for security file scanning.

    Args:
        artifacts_dir: Path to artifacts directory from CLI arguments

    Returns:
        search_dir: String path to directory containing security scan files

    Raises:
        RuntimeError: If artifact download or extraction fails
    """
    print(f"\n📦 Artifact Download and Preparation Phase")
    print(f"="*60)

    if artifacts_dir.exists() and any(artifacts_dir.iterdir()):
        # Directory exists and has content - process existing artifacts
        print(f"📂 Using existing artifacts directory: {artifacts_dir}")
        downloaded_path = artifacts_dir

    elif artifacts_dir.exists():
        # Directory exists but is empty - check if it has any scan files first
        print(f"📂 Using existing artifacts directory: {artifacts_dir}")
        downloaded_path = artifacts_dir

    else:
        # Directory doesn't exist - download latest artifacts there
        print(f"📥 Downloading latest artifacts to: {artifacts_dir}")
        downloaded_path = download_latest_artifacts(str(artifacts_dir))

        if not downloaded_path:
            logger.error("❌ CRITICAL: Artifact download failed")
            logger.error("🔍 Artifact download failure indicates GitHub CLI issues or network problems requiring investigation")
            raise RuntimeError("Artifact download failed - requires investigation")

        print(f"✅ Downloaded artifacts to: {downloaded_path}")

    # Check for zip files (gh run download creates zips)
    zip_files = list(downloaded_path.glob("*.zip"))
    if zip_files:
        print(f"\n📦 Found {len(zip_files)} zip file(s) to extract")
        extract_dir = downloaded_path / "extracted"
        extract_artifacts(str(downloaded_path), str(extract_dir))
        search_dir = str(extract_dir)
    else:
        # If no zips, maybe artifacts were not zipped. Search the download dir directly.
        print("\n⚠️ No .zip artifacts found. Searching for report files directly in download directory.")
        search_dir = str(downloaded_path)

    print(f"✅ Artifact preparation completed, search directory: {search_dir}")
    return search_dir


def download_latest_artifacts(output_dir: str) -> Path | None:
    """
    Downloads artifacts from the latest successful GitHub Actions run on the default branch.
    """
    output_path = Path(output_dir)

    print("🔍 Setting up artifact download...")

    # 2. Remove existing directory if it exists
    if output_path.exists():
        print(f"  Removing existing directory: {output_path}")
        shutil.rmtree(output_path)

    try:
        # 3. Get the current repo by running gh command from the project root
        project_root = Path(__file__).parent.parent
        print(f"  Finding current GitHub repository (from {project_root})...")
        repo_proc = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True, text=True, check=True, cwd=project_root
        )
        repo = repo_proc.stdout.strip()
        if not repo:
            print("    ❌ Could not determine repository. Are you in a git repo with a GitHub remote?")
            return None
        print(f"    ✅ Found repository: {repo}")

        # 4. Get the default branch
        print("  Finding default branch...")
        branch_proc = subprocess.run(
            ["gh", "repo", "view", repo, "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"],
            capture_output=True, text=True, check=True
        )
        default_branch = branch_proc.stdout.strip()
        print(f"    ✅ Default branch is '{default_branch}'")

        # 5. Get the latest successful run ID on the default branch from Main CI/CD workflow
        print(f"  Finding latest successful Main CI/CD run on branch '{default_branch}'...")
        # Filter specifically for the Main CI/CD workflow that generates security artifacts
        run_id_proc = subprocess.run(
            ["gh", "run", "list", "-R", repo, "-b", default_branch, "--workflow", "main-ci-cd.yml", "--status", "success", "--limit", "1", "--json", "databaseId", "-q", ".[0].databaseId"],
            capture_output=True, text=True, check=True
        )
        run_id = run_id_proc.stdout.strip()
        if not run_id:
            print(f"    ❌ No successful Main CI/CD runs found on branch '{default_branch}'.")
            print(f"    💡 Make sure the Main CI/CD pipeline has run successfully on main branch.")
            return None
        print(f"    ✅ Found Main CI/CD run ID: {run_id}")

        # 6. Download artifacts for that run
        print(f"  Downloading artifacts for run {run_id} to {output_path}...")
        # Define patterns for the security artifacts we care about
        patterns = [
            "*zap*",
            "*trivy*",
            "*sarif*",
            "*osv*",
            "*gitleaks*",
            "*semgrep*",
            "*checkov*",
        ]
        download_command = [
            "gh", "run", "download", run_id,
            "-R", repo,
            "-D", str(output_path)
        ]
        for p in patterns:
            download_command.extend(["--pattern", p])

        print(f"    Filtering with patterns: {', '.join(patterns)}")
        # The -D flag creates the directory.
        subprocess.run(download_command, check=True, capture_output=True, text=True)

        if not any(output_path.iterdir()):
             print(f"    ⚠️ No artifacts were downloaded. The run may not have produced any matching artifacts.")
        else:
            print(f"    ✅ Artifacts downloaded to {output_path}")

        return output_path

    except subprocess.CalledProcessError as e:
        # Fail fast on dependency issues
        print(f"❌ CRITICAL: GitHub CLI dependency failure:")
        print(f"      Command: {' '.join(e.cmd)}")
        print(f"      Stderr: {e.stderr.strip()}")
        print("🔍 GitHub CLI is required for artifact download - check installation and authentication")
        raise RuntimeError(f"GitHub CLI dependency failure - requires investigation: {e}") from e
    except Exception as e:
        # Fail fast on other infrastructure issues
        print(f"❌ CRITICAL: Artifact download infrastructure failure: {e}")
        print("🔍 Check system dependencies, network connectivity, and GitHub access")
        raise RuntimeError(f"Artifact download infrastructure failure - requires investigation: {e}") from e


def get_active_only_phase(args) -> str:
    """Get the single active --only-* phase flag, or None for multi-phase"""
    from typing import Optional

    only_flags = {
        Phases.PARSING: args.only_parsing,
        Phases.VULNERABILITY_ANALYSIS: args.only_vulnerability_analysis,
        Phases.RAG_ENHANCEMENT: args.only_rag_enhancement,
        Phases.ANALYSIS_SUMMARY: args.only_analysis_summary,
        Phases.NARRATIVIZATION: args.only_narrativization,
        Phases.DATASETS: args.only_datasets,
        Phases.TRAINING: args.only_training,
        Phases.UPLOAD: args.only_upload
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


def load_phase_input(input_path: Path):
    """Load JSON data from phase input file"""
    if not input_path.exists():
        raise ValueError(f"Input file not found: {input_path}")

    with open(input_path, 'r') as f:
        return json.load(f)


def load_jsonl_input(input_path: Path):
    """Load JSONL data from phase input file (one JSON object per line)"""
    if not input_path.exists():
        raise ValueError(f"Input file not found: {input_path}")

    data = []
    with open(input_path, 'r') as f:
        for line in f:
            if line.strip():  # Skip empty lines
                data.append(json.loads(line.strip()))
    return data


def execute_single_phase(phase: str, args):
    """Execute a single phase with provided inputs"""
    print(f"\n🎯 Executing single phase: {phase}")

    output_dir = str(args.output_dir)

    if phase == Phases.PARSING:
        # Extract scan files from artifacts directory
        scan_files = find_security_files(args.artifacts_dir)
        all_vulnerabilities, vulnerabilities_file, summary_file = parse_vulnerabilities_phase(scan_files, output_dir)
        print(f"✅ Parsing completed. Output files:")
        print(f"   Parsed vulnerabilities: {vulnerabilities_file}")
        print(f"   Summary: {summary_file}")
        return 0, {"phase": phase, "vulnerabilities_file": str(vulnerabilities_file), "vulnerabilities_count": len(all_vulnerabilities)}

    elif phase == Phases.VULNERABILITY_ANALYSIS:
        vulnerabilities_file = args.parsed_input
        all_vulnerabilities, analysis_file = core_analysis_phase(vulnerabilities_file, output_dir, args)
        print(f"✅ Vulnerability analysis completed. Output files:")
        print(f"   Analysis results: {analysis_file}")
        return 0, {"phase": phase, "analysis_file": str(analysis_file), "vulnerabilities_processed": len(all_vulnerabilities)}

    elif phase == Phases.RAG_ENHANCEMENT:
        vulnerability_analysis_file = args.vulnerability_analysis_input
        enhanced_vulnerabilities, rag_file = rag_enhancement_phase(vulnerability_analysis_file, output_dir, args)
        print(f"✅ RAG enhancement completed. Output file:")
        print(f"   RAG enhanced results: {rag_file}")
        return 0, {"phase": phase, "rag_file": str(rag_file), "vulnerabilities_processed": len(enhanced_vulnerabilities)}

    elif phase == Phases.ANALYSIS_SUMMARY:
        rag_enhanced_file = args.rag_enhanced_input
        analyzed_vulnerabilities, analysis_file, summary_file = analysis_summary_phase(rag_enhanced_file, output_dir, args)
        print(f"✅ Analysis summary completed. Output files:")
        print(f"   Final analysis: {analysis_file}")
        print(f"   Summary: {summary_file}")
        return 0, {"phase": phase, "analysis_file": str(analysis_file), "vulnerabilities_processed": len(analyzed_vulnerabilities)}

    elif phase == Phases.NARRATIVIZATION:
        analyzed_file = args.analyzed_input
        narrativized_results, narrativized_file = narrativization_phase(analyzed_file, output_dir, args)
        print(f"✅ Narrativization completed. Output file:")
        print(f"   Narrativized results: {narrativized_file}")
        return 0, {"phase": phase, "narrativized_file": str(narrativized_file), "narratives_created": len(narrativized_results)}

    elif phase == Phases.DATASETS:
        narrativized_file = args.narrativized_input
        parsed_file = args.parsed_input
        dataset_results, train_file, validation_file = datasets_phase(narrativized_file, parsed_file, output_dir, args)
        print(f"✅ Datasets phase completed. Output files:")
        print(f"   Training dataset: {train_file}")
        print(f"   Validation dataset: {validation_file}")
        return 0, {"phase": phase, "train_file": str(train_file), "validation_file": str(validation_file), "datasets_created": len(dataset_results) if dataset_results else 0}

    elif phase == Phases.TRAINING:
        train_file = args.train_input
        validation_file = args.validation_input
        narrativized_data = load_phase_input(args.narrativized_input)
        train_data = load_jsonl_input(train_file)  # JSONL files need line-by-line loading

        # Create dummy summary for compatibility
        summary = {"phase": "training", "single_phase_execution": True}
        training_summary, model_path = training_phase(train_file, train_data, narrativized_data, summary, args)
        print(f"✅ Training completed. Model artifacts:")
        print(f"   Model path: {model_path}")
        return 0, {"phase": phase, "model_path": str(model_path) if model_path else 'none', "training_summary": training_summary}

    elif phase == Phases.UPLOAD:
        # Use structured discovery to find latest trained model
        try:
            model_dir = _get_latest_structured_model()
            print(f"🎯 Using structured discovery for upload: {model_dir}")
        except RuntimeError as e:
            print(f"❌ Structured model discovery failed: {e}")
            return 1, {"phase": phase, "error": str(e)}

        # Create dummy summary for compatibility
        summary = {"phase": "upload", "single_phase_execution": True}
        try:
            upload_summary = upload_phase(model_dir, summary, args)
            print(f"✅ Upload completed.")
            return 0, {"phase": phase, "upload_summary": upload_summary}
        except ValueError as e:
            # Re-raise validation errors to fail fast in single-phase execution
            if "Model validation failed" in str(e) or "Invalid model structure" in str(e):
                print(f"❌ FAIL FAST: Upload phase failed due to validation error: {e}")
                return 1, {"phase": phase, "error": str(e), "upload_summary": summary}
            else:
                raise  # Re-raise other ValueError types

    else:
        raise ValueError(f"Unknown phase: {phase}")


def _display_completion_summary(results: List, summary: Dict):
    """
    Display contextually appropriate completion summary based on execution mode and results.

    Args:
        results: List of analysis results (empty for completed full pipeline)
        summary: Summary dictionary with execution context and results
    """
    if not isinstance(summary, dict):
        print(f"📋 Process Summary: Operations completed")
        return

    # Detect execution context from summary structure
    is_full_pipeline = (summary.get('upload_status') and
                       summary.get('sequential_fine_tuning') and
                       summary.get('total_analyzed'))

    is_single_upload = (summary.get('upload_status') and
                       summary.get('single_phase_execution'))

    has_analysis_results = isinstance(results, list) and len(results) > 0

    if is_full_pipeline:
        # Complete 6-phase pipeline results
        upload_results = summary.get('upload_results', {})
        models_uploaded = upload_results.get('models_uploaded', 0)
        datasets_uploaded = upload_results.get('datasets_uploaded', 0)
        vulnerabilities_analyzed = summary.get('total_analyzed', 0)
        sequential_training = summary.get('sequential_fine_tuning', {})

        print(f"🎯 Complete Pipeline Results:")
        print(f"   📊 Vulnerabilities Analyzed: {vulnerabilities_analyzed}")
        print(f"   🤖 Sequential Training: {sequential_training.get('stage1_score', 'N/A')}/{sequential_training.get('stage2_score', 'N/A')} scores")
        print(f"   📦 Uploads: {models_uploaded} models, {datasets_uploaded} datasets")

    elif is_single_upload:
        # Single upload phase results
        upload_results = summary.get('upload_results', {})
        models_uploaded = upload_results.get('models_uploaded', 0)
        datasets_uploaded = upload_results.get('datasets_uploaded', 0)
        print(f"📦 Upload Results: {models_uploaded} models, {datasets_uploaded} datasets uploaded")

    elif has_analysis_results:
        # Analysis-focused phases
        print(f"📊 Analysis Results: {len(results)} vulnerability analyses completed")

    else:
        # Generic completion for other phases
        phase_info = summary.get('phase', 'operations')
        print(f"📋 Process Summary: {phase_info.title()} completed successfully")


def main():
    """
    Main entry point for processing security artifacts
    """
    # Initialize configuration for default model path
    config = OLMoSecurityConfig()

    # Get default model path from configuration, with fallback
    try:
        default_model = str(config.get_base_model_path())
    except FileNotFoundError:
        default_model = None
        print(f"⚠️  Default model not found at {config.base_models_dir}/{config.default_base_model}")
        print("🔄 Will use fallback mode if no model specified")

    parser = argparse.ArgumentParser(
        description="Process security artifacts with OLMo analysis - Refactored Phase Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Directory configuration
    parser.add_argument("--artifacts-dir", type=Path, default="data/security_artifacts",
                       help="Directory for security artifacts (default: data/security_artifacts)")
    parser.add_argument("--output-dir", type=Path, default="results",
                       help="Output directory for analysis results (default: results)")
    parser.add_argument("--model-name", type=str, default=default_model,
                       help="OLMo-2-1B model to use for analysis (defaults to configured model)")
    # Auto-detect git information
    try:
        import subprocess
        git_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                           cwd=Path(__file__).parent.parent,
                                           stderr=subprocess.DEVNULL).decode().strip()
        git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                           cwd=Path(__file__).parent.parent,
                                           stderr=subprocess.DEVNULL).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_branch = "unknown"
        git_commit = "unknown"

    parser.add_argument("--branch", type=str, default=git_branch,
                       help=f"Git branch being analyzed (auto-detected: {git_branch})")
    parser.add_argument("--commit", type=str, default=git_commit,
                       help=f"Git commit SHA being analyzed (auto-detected: {git_commit[:8]}...)")

    # Upload control
    parser.add_argument("--skip-model-upload", action="store_true",
                       help="Skip all uploads to HuggingFace Hub (models and datasets) - only affects upload phase")

    # Single-phase execution flags
    phase_group = parser.add_argument_group('Single Phase Execution')
    phase_group.add_argument("--only-parsing", action="store_true",
                            help="Execute only parsing phase")
    phase_group.add_argument("--only-vulnerability-analysis", action="store_true",
                            help="Execute only vulnerability analysis phase")
    phase_group.add_argument("--only-rag-enhancement", action="store_true",
                            help="Execute only RAG enhancement phase")
    phase_group.add_argument("--only-analysis-summary", action="store_true",
                            help="Execute only analysis summary phase")
    phase_group.add_argument("--only-narrativization", action="store_true",
                            help="Execute only narrativization phase")
    phase_group.add_argument("--only-datasets", action="store_true",
                            help="Execute only datasets phase")
    phase_group.add_argument("--only-training", action="store_true",
                            help="Execute only training phase")
    phase_group.add_argument("--only-upload", action="store_true",
                            help="Execute only upload phase")

    # Input file arguments
    input_group = parser.add_argument_group('Phase Input Files')
    input_group.add_argument("--parsed-input", type=Path,
                            help="Parsed vulnerabilities file (for vulnerability-analysis+)")
    input_group.add_argument("--vulnerability-analysis-input", type=Path,
                            help="Vulnerability analysis results file (for rag-enhancement+)")
    input_group.add_argument("--rag-enhanced-input", type=Path,
                            help="RAG enhanced results file (for analysis-summary+)")
    input_group.add_argument("--analyzed-input", type=Path,
                            help="Analyzed vulnerabilities file (for narrativization+)")
    input_group.add_argument("--narrativized-input", type=Path,
                            help="Narrativized vulnerabilities file (for datasets+)")
    input_group.add_argument("--train-input", type=Path,
                            help="Training dataset file (for training)")
    input_group.add_argument("--validation-input", type=Path,
                            help="Validation dataset file (for training)")
    input_group.add_argument("--dataset-files", type=str,
                            help="Comma-separated dataset files (for upload)")

    args = parser.parse_args()

    # ===== SHARED SETUP LOGIC =====
    # Setup logging (shared by both single-phase and multi-phase)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Log comprehensive configuration (shared by both execution modes)
    print("\n🔧 Configuration Summary:")

    # Fine-tuning configuration
    try:
        config = OLMoSecurityConfig()

        def get_config_source(env_var, env_value):
            if env_value is not None:
                return "(env override)"
            return "(yaml config)"

        print(f"  workspace_dir: {config.fine_tuning.workspace_dir} {get_config_source('OLMO_WORKSPACE_DIR', os.getenv('OLMO_WORKSPACE_DIR'))}")
        print(f"  base_models_dir: {config.base_models_dir} {get_config_source('OLMO_BASE_MODELS_DIR', os.getenv('OLMO_BASE_MODELS_DIR'))}")
        print(f"  fine_tuned_models_dir: {config.fine_tuned_models_dir} {get_config_source('OLMO_FINE_TUNED_MODELS_DIR', os.getenv('OLMO_FINE_TUNED_MODELS_DIR'))}")
        print(f"  max_epochs: {config.fine_tuning.max_epochs} {get_config_source('OLMO_MAX_EPOCHS', os.getenv('OLMO_MAX_EPOCHS'))}")
        print(f"  save_steps: {config.fine_tuning.save_steps} {get_config_source('OLMO_SAVE_STEPS', os.getenv('OLMO_SAVE_STEPS'))}")
        print(f"  eval_steps: {config.fine_tuning.eval_steps} {get_config_source('OLMO_EVAL_STEPS', os.getenv('OLMO_EVAL_STEPS'))}")
        print(f"  learning_rate: {config.fine_tuning.learning_rate} {get_config_source('OLMO_LEARNING_RATE', os.getenv('OLMO_LEARNING_RATE'))}")
        print(f"  batch_size: {config.fine_tuning.batch_size} {get_config_source('OLMO_BATCH_SIZE', os.getenv('OLMO_BATCH_SIZE'))}")
        print(f"  max_stage1_iters: {config.fine_tuning.max_stage1_iters} {get_config_source('OLMO_MAX_STAGE1_ITERS', os.getenv('OLMO_MAX_STAGE1_ITERS'))}")
        print(f"  max_stage2_iters: {config.fine_tuning.max_stage2_iters} {get_config_source('OLMO_MAX_STAGE2_ITERS', os.getenv('OLMO_MAX_STAGE2_ITERS'))}")

    except Exception as e:
        logger.error(f"❌ CRITICAL: Fine-tuning configuration loading failure: {e}")
        logger.error("🔍 Fine-tuning configuration loading failure indicates configuration corruption or dependency issues requiring investigation")
        raise RuntimeError(f"Fine-tuning configuration loading failure requires investigation: {e}") from e

    # Knowledge base configuration
    kb_dir = os.getenv('OLMO_KNOWLEDGE_BASE_DIR')
    if kb_dir:
        print(f"  knowledge_base_dir: {kb_dir} (env override)")
    else:
        print(f"  knowledge_base_dir: security-ai-analysis/knowledge_base (default)")

    # ===== EXECUTION MODE SELECTION =====
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

    # Multi-phase execution
    print("=" * 60)
    print(f"🔒 WebAuthn Security Analysis with {args.model_name}")
    print(f"Artifacts: {args.artifacts_dir}")
    print(f"Output: {args.output_dir}")
    print("=" * 60)

    # Artifact download and preparation phase
    artifacts_dir = Path(args.artifacts_dir)
    search_dir = artifact_download_phase(artifacts_dir)

    # Find security scan files
    scan_files = find_security_files(search_dir)

    # Check if any files were found (fail-fast validation)
    total_files = sum(len(files) for files in scan_files.values())
    if total_files == 0:
        logger.error(f"❌ CRITICAL: No security files found in {search_dir}")
        logger.error("🔍 No security files found indicates missing CI pipeline output or incorrect directory - requires investigation")
        logger.error("Expected file types: .sarif, .json files from trivy, checkov, semgrep, osv-scanner, zap")
        raise RuntimeError(f"No security files found in {search_dir} - requires investigation")

    # Process all scans with new phase-based architecture
    output_dir = str(args.output_dir)

    # Run the phase-based processing pipeline
    results, summary = process_all_scans_enhanced(scan_files, output_dir, args)

    print("\n" + "=" * 60)
    print("✅ Processing complete!")

    # Display contextually appropriate completion summary
    _display_completion_summary(results, summary)

    print(f"📈 Summary Keys: {list(summary.keys()) if isinstance(summary, dict) else 'N/A'}")
    print("=" * 60)

    return 0

if __name__ == "__main__":
    exit(main())
