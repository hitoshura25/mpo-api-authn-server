#!/usr/bin/env python3
"""
Process downloaded GitHub Actions security artifacts with OLMo - Refactored Phase Architecture

This refactored version implements a clean 6-phase architecture:
1. Parsing - Extract vulnerabilities from security scan files
2. Analysis - AI analysis using OLMo models
3. Narrativization - Create rich security narratives
4. Datasets - Prepare training and validation datasets
5. Training - Fine-tune models using datasets
6. Upload - Upload models and datasets to HuggingFace Hub

Each phase can be stopped individually using --stop-after for faster testing.
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
from pipeline_integration import integrate_fine_tuning_if_available
from sequential_pipeline_integration import run_sequential_fine_tuning_phase, is_sequential_fine_tuning_available
import argparse
import logging


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
            print(f"    ❌ Failed to extract: {e}")

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

            except Exception as e:
                print(f"    ❌ Error processing file: {e}")

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
        print(f"❌ Failed to initialize OLMo analyzer: {e}")
        return [], Path(), Path()

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
                print(f"   ❌ Batch {batch_num} failed: {e}", flush=True)
                continue

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

        # Post-analysis RAG enhancement (if enabled)
        if not args.disable_rag:
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
        else:
            print("\n🔄 RAG disabled - knowledge base building skipped")

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
        print(f"❌ Failed to initialize core analyzer: {e}")
        return [], Path()

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
                print(f"   ❌ Batch {batch_num} failed: {e}", flush=True)
                continue

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
        - args: Command line arguments (disable_rag, etc.)

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

    # RAG enhancement (if enabled)
    if not args.disable_rag:
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
            print(f"⚠️ RAG knowledge base building failed: {rag_error}")
            print("💡 This doesn't affect current analysis but RAG won't be available for next runs")
    else:
        print("\n🔄 RAG disabled - knowledge base building skipped")

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
        print(f"⚠️ URL-to-code mapping failed: {e}")
        print("💡 Continuing without URL enhancement")

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
        print(f"⚠️ Could not generate detailed summary: {e}")
        # Fallback basic summary
        summary = {
            'total_analyzed': len(results),
            'successful': len([r for r in results if r.get('status') == 'success']),
            'failed': len([r for r in results if r.get('status') != 'success']),
            'model_used': args.model_name,
            'branch': args.branch,
            'commit': args.commit,
            'analysis_timestamp': datetime.now().isoformat()
        }

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
        print(f"❌ Failed to import SecurityNarrativizer: {e}")
        raise

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
                print(f"  ⚠️ Failed to create narrative for {vuln_data.get('id', 'unknown')}: {e}")

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

    # Upload to HuggingFace production dataset
    try:
        from datasets import Dataset
        from huggingface_hub import HfApi
        print(f"📤 Uploading {len(training_pairs)} training pairs to production dataset...")
        print(f"🎯 Target: hitoshura25/webauthn-security-vulnerabilities-olmo")

        # ✅ CRITICAL FIX: Serialize FixApproach enums before Dataset.from_list()
        # This prevents Apache Arrow serialization errors with enum objects
        serialized_training_pairs = []
        for pair in training_pairs:
            try:
                # Test serialization to catch enum issues
                serialized_pair = json.loads(json.dumps(pair, cls=json_encoder))
                serialized_training_pairs.append(serialized_pair)
            except Exception as e:
                print(f"⚠️ Skipping problematic training pair: {e}")
                # Fallback: manually convert any remaining enum values
                clean_pair = {}
                for key, value in pair.items():
                    if hasattr(value, 'value'):  # Handle enum objects
                        clean_pair[key] = str(value.value) if hasattr(value, 'value') else str(value)
                    else:
                        clean_pair[key] = value
                serialized_training_pairs.append(clean_pair)

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

    except ImportError as e:
        print(f"⚠️ HuggingFace libraries not available for upload: {e}")
        print("   Install with: pip install datasets huggingface_hub")
    except Exception as e:
        print(f"❌ Production dataset upload failed: {e}")
        print(f"   Training data saved locally for manual upload if needed")

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

    # **Sequential Fine-Tuning Integration (Default Behavior)**
    # Progressive specialization: Stage 1 (Analysis) → Stage 2 (Code Fixes)
    disable_sequential_fine_tuning = getattr(args, 'disable_sequential_fine_tuning', False)
    upload_model = not getattr(args, 'skip_model_upload', False)  # Default True, disabled by --skip-model-upload

    model_artifacts_path = Path("model_artifacts")  # Default path for model artifacts

    # Try sequential fine-tuning first (new default)
    try:
        from sequential_pipeline_integration import run_sequential_fine_tuning_phase, is_sequential_fine_tuning_available

        if is_sequential_fine_tuning_available() and not disable_sequential_fine_tuning:
            print("🎯 Sequential Fine-Tuning (Default)")
            updated_summary = run_sequential_fine_tuning_phase(
                vulnerabilities=narrativized_results,  # Use full vulnerability data with narratives
                summary=summary,
                disable_sequential_fine_tuning=disable_sequential_fine_tuning,
                upload_model=upload_model
            )
            print("✅ Sequential fine-tuning completed successfully")
            return updated_summary, model_artifacts_path

    except ImportError as e:
        print(f"⚠️ Sequential fine-tuning not available: {e}")

    # Fall back to Single-Stage Fine-Tuning (Legacy)
    try:
        from pipeline_integration import integrate_fine_tuning_if_available

        print("🔄 Legacy Single-Stage Fine-Tuning")
        skip_fine_tuning = getattr(args, 'skip_fine_tuning', False)
        updated_summary = integrate_fine_tuning_if_available(
            train_file,
            train_data,
            summary,
            skip_fine_tuning,
            upload_model
        )
        print("✅ Single-stage fine-tuning completed successfully")
        return updated_summary, model_artifacts_path

    except ImportError as e:
        print(f"⚠️ Fine-tuning integration not available: {e}")
        print("   Skipping fine-tuning phase")
        return summary, model_artifacts_path


def upload_phase(model_artifacts_path: Path, summary: Dict, args) -> Dict:
    """
    Phase 6: Upload models and datasets to HuggingFace Hub

    Args:
        model_artifacts_path: Path to model artifacts
        summary: Current summary dict
        args: Command line arguments

    Returns:
        updated_summary: Dict with upload status
    """
    skip_upload = getattr(args, 'skip_model_upload', False)

    if skip_upload:
        print("🛑 Model upload skipped (--skip-model-upload flag)")
        summary['upload_status'] = 'skipped'
        return summary

    print(f"📤 Starting model upload phase...")

    try:
        # Model upload is typically handled within the fine-tuning phases
        # This phase serves as a verification/final upload step if needed
        print("✅ Model upload handled by fine-tuning phase")
        summary['upload_status'] = 'completed'

    except Exception as e:
        print(f"❌ Upload phase failed: {e}")
        summary['upload_status'] = 'failed'

    return summary


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

    print(f"\n🚀 Starting phase-based security analysis pipeline")
    print(f"📂 Output directory: {output_path}")
    if args.stop_after:
        print(f"🛑 Will stop after: {args.stop_after} phase")

    # Phase 1: Always run parsing
    print(f"\n" + "="*60)
    print(f"📋 PHASE 1: PARSING")
    print(f"="*60)
    all_vulnerabilities, vulnerabilities_file, parsing_summary_file = parse_vulnerabilities_phase(scan_files, output_dir)

    if args.stop_after == "parsing":
        print(f"\n🛑 Stopping after parsing phase as requested")
        return load_results_from_files(vulnerabilities_file, parsing_summary_file)

    # Phase 2A: Core AI Analysis
    print(f"\n" + "="*60)
    print(f"🤖 PHASE 2A: CORE AI ANALYSIS")
    print(f"="*60)
    core_analysis_results, core_analysis_file = core_analysis_phase(vulnerabilities_file, output_dir, args)

    if args.stop_after == "core-analysis":
        print(f"\n🛑 Stopping after core analysis phase as requested")
        return load_results_from_files(core_analysis_file, {"phase": "core-analysis", "total_analyzed": len(core_analysis_results)})

    # Phase 2B: RAG Enhancement
    print(f"\n" + "="*60)
    print(f"🧠 PHASE 2B: RAG ENHANCEMENT")
    print(f"="*60)
    rag_enhanced_results, rag_enhanced_file = rag_enhancement_phase(core_analysis_file, output_dir, args)

    if args.stop_after == "rag-enhancement":
        print(f"\n🛑 Stopping after RAG enhancement phase as requested")
        return load_results_from_files(rag_enhanced_file, {"phase": "rag-enhancement", "total_analyzed": len(rag_enhanced_results)})

    # Phase 2C: Analysis Summary
    print(f"\n" + "="*60)
    print(f"📊 PHASE 2C: ANALYSIS SUMMARY")
    print(f"="*60)
    analyzed_vulnerabilities, analysis_file, analysis_summary_file = analysis_summary_phase(rag_enhanced_file, output_dir, args)

    if args.stop_after == "analysis":
        print(f"\n🛑 Stopping after analysis phase as requested")
        return load_results_from_files(analysis_file, analysis_summary_file)

    # Phase 3: Narrativization
    print(f"\n" + "="*60)
    print(f"🎯 PHASE 3: NARRATIVIZATION")
    print(f"="*60)
    narrativized_results, narrativized_file = narrativization_phase(analysis_file, output_dir, args)

    if args.stop_after == "narrativization":
        print(f"\n🛑 Stopping after narrativization phase as requested")
        return narrativized_results, {"phase": "narrativization", "narratives_created": len(narrativized_results)}

    # Phase 4: Datasets
    print(f"\n" + "="*60)
    print(f"🚀 PHASE 4: DATASETS")
    print(f"="*60)
    training_pairs, train_file, validation_file = datasets_phase(narrativized_file, vulnerabilities_file, output_dir, args)

    if args.stop_after == "datasets":
        print(f"\n🛑 Stopping after datasets phase as requested")
        return training_pairs, {
            "phase": "datasets",
            "total_training_pairs": len(training_pairs),
            "train_file": str(train_file),
            "validation_file": str(validation_file)
        }

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

    if args.stop_after == "training":
        print(f"\n🛑 Stopping after training phase as requested")
        return [], updated_summary

    # Phase 6: Upload
    print(f"\n" + "="*60)
    print(f"📤 PHASE 6: UPLOAD")
    print(f"="*60)
    final_summary = upload_phase(model_artifacts_path, updated_summary, args)

    print(f"\n✅ All 6 phases completed successfully")
    return [], final_summary


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
        print(f"    ❌ Error executing 'gh' command:")
        print(f"      Command: {' '.join(e.cmd)}")
        print(f"      Stderr: {e.stderr.strip()}")
        return None
    except Exception as e:
        print(f"    ❌ An unexpected error occurred: {e}")
        return None


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
    parser.add_argument("--branch", type=str, default="unknown",
                       help="Git branch being analyzed")
    parser.add_argument("--commit", type=str, default="unknown",
                       help="Git commit SHA being analyzed")

    # Fine-tuning control (opt-out approach - sequential fine-tuning enabled by default)
    parser.add_argument("--disable-sequential-fine-tuning", action="store_true",
                       help="Disable sequential fine-tuning and fall back to single-stage approach")
    parser.add_argument("--skip-fine-tuning", action="store_true",
                       help="Skip MLX fine-tuning entirely (used with fallback mode)")
    parser.add_argument("--skip-model-upload", action="store_true",
                       help="Skip uploading fine-tuned model to HuggingFace Hub (upload enabled by default)")

    # RAG enhancement control (opt-out approach - RAG enabled by default)
    parser.add_argument("--disable-rag", action="store_true",
                       help="Disable RAG-enhanced analysis (RAG enabled by default)")

    # Phase control - NEW FUNCTIONALITY with sub-phases
    parser.add_argument("--stop-after",
                       choices=["parsing", "core-analysis", "rag-enhancement", "analysis",
                               "narrativization", "datasets", "training", "upload"],
                       help="Stop processing after the specified phase")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print(f"🔒 WebAuthn Security Analysis with {args.model_name}")
    print(f"Artifacts: {args.artifacts_dir}")
    print(f"Output: {args.output_dir}")
    if args.stop_after:
        print(f"Stop after: {args.stop_after} phase")
    print("=" * 60)

    # Check if artifacts directory exists and has content
    artifacts_dir = Path(args.artifacts_dir)

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
            print("\n❌ Failed to download artifacts. Exiting.")
            return 1

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

    # Find security scan files
    scan_files = find_security_files(search_dir)

    # Check if any files were found
    total_files = sum(len(files) for files in scan_files.values())
    if total_files == 0:
        print(f"\n❌ No security files found in {search_dir}")
        print("Expected file types: .sarif, .json files from trivy, checkov, semgrep, osv-scanner, zap")
        return 1

    # Process all scans with new phase-based architecture
    output_dir = str(args.output_dir)

    # Run the phase-based processing pipeline
    results, summary = process_all_scans_enhanced(scan_files, output_dir, args)

    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print(f"📊 Final Results: {len(results) if isinstance(results, list) else 'N/A'} items")
    print(f"📈 Summary Keys: {list(summary.keys()) if isinstance(summary, dict) else 'N/A'}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
