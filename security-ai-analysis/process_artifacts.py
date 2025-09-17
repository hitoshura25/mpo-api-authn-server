#!/usr/bin/env python3
"""
Process downloaded GitHub Actions security artifacts with OLMo
This script handles the actual security scan outputs from your WebAuthn project
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
from parsers.semgrep_parser import parse_semgrep_json
from parsers.osv_parser import parse_osv_json
from parsers.zap_parser import parse_zap_json
from analysis.olmo_analyzer import OLMoSecurityAnalyzer
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


def process_all_scans_enhanced(scan_files: dict, output_dir: str, args) -> Tuple[List, Dict]:
    """
    Enhanced processing with OLMo-2-1B support and improved error handling.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize OLMo analyzer with enhanced configuration
    print(f"\\n🤖 Initializing {args.model_name} Security Analyzer...")
    print(f"   Branch: {args.branch}")
    print(f"   Commit: {args.commit}")
    
    try:
        # Initialize baseline analyzer first (RAG will be added post-analysis)
        print("🤖 Initializing baseline OLMo analyzer for initial vulnerability processing...")
        analyzer = OLMoSecurityAnalyzer(
            model_name=args.model_name
        )
        print("✅ Baseline OLMo analyzer initialized successfully", flush=True)
    except Exception as e:
        print(f"❌ Failed to initialize OLMo analyzer: {e}")
        return [], {}
    
    all_vulnerabilities = []
    
    # Process each scan type with enhanced logging
    print(f"\\n📂 Starting vulnerability parsing from {len(scan_files)} scan types...", flush=True)
    for scan_type, files in scan_files.items():
        if not files:
            continue
            
        print(f"\\n📊 Processing {scan_type} scans ({len(files)} files)...", flush=True)
        
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
                    vulns = parse_semgrep_json(file_path)
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
    
    # Enhanced analysis with OLMo-2-1B
    if all_vulnerabilities:
        print(f"\\n🔍 Starting analysis of {len(all_vulnerabilities)} total vulnerabilities with {args.model_name}...", flush=True)
        
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
            
            print(f"\\n🔄 Starting batch {batch_num}/{total_batches}: vulnerabilities {i+1}-{batch_end} of {len(all_vulnerabilities)}", flush=True)
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
        
        # Save detailed results
        results_file = output_path / f"olmo_analysis_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\\n💾 Detailed results saved to: {results_file}")
        
        # Save summary
        summary_file = output_path / f"olmo_analysis_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"💾 Summary saved to: {summary_file}")
        
        # Post-analysis RAG enhancement (if enabled)
        if not args.disable_rag:
            print("\\n🧠 Building RAG knowledge base with fresh analysis results...")
            try:
                from build_knowledge_base import main as build_kb_main
                import sys
                from io import StringIO
                
                # Capture build output to avoid cluttering the main process output
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()
                
                try:
                    # Build knowledge base using the fresh analysis results
                    sys.argv = ['build_knowledge_base.py', '--results-file', str(results_file), '--verbose']
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
            print("\\n🔄 RAG disabled - knowledge base building skipped")
        
        
        # Print enhanced summary
        print("\\n📈 Analysis Summary:")
        print(f"  Model Used: {summary.get('model_used', 'Unknown')}")
        print(f"  Total Analyzed: {summary['total_analyzed']}")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Branch: {summary.get('branch', 'Unknown')}")
        print(f"  Commit: {summary.get('commit', 'Unknown')[:8]}...")
        
        if summary['by_severity']:
            print("\\n  By Severity:")
            for sev, count in summary['by_severity'].items():
                print(f"    {sev}: {count}")
        
        if summary['by_tool']:
            print("\\n  By Tool:")
            for tool, count in summary['by_tool'].items():
                print(f"    {tool}: {count}")
        
        # **Phase 2: Narrativization Integration**
        print("\\n" + "="*60)
        print("🎯 Phase 2: Creating Rich Security Narratives")
        print("="*60)
        
        try:
            from create_narrativized_dataset import SecurityNarrativizer
            
            narrativized_results = []
            narrativizer = SecurityNarrativizer()
            
            print(f"📝 Creating narratives for {len(results)} analysis results...")
            
            for item in results:
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
            print(f"✅ Narrativized dataset saved to: {narrativized_file}")
            print(f"📊 Created {len(narrativized_results)} narratives")
            
            # **Phase 3: Fine-tuning Dataset Preparation**
            print("\\n" + "="*60)
            print("🚀 Phase 3: Preparing Fine-Tuning Dataset")  
            print("="*60)
            
            if narrativized_results:
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
                    from enhanced_dataset_creator import EnhancedDatasetCreator
                    
                    # Create enhanced dataset
                    enhanced_creator = EnhancedDatasetCreator()
                    enhanced_result = enhanced_creator.create_enhanced_dataset(
                        all_vulnerabilities, 
                        dataset_name=f"enhanced_security_dataset_{timestamp}"
                    )
                    
                    if enhanced_result.success:
                        print(f"✅ Enhanced dataset creation successful!")
                        print(f"  📊 Original vulnerabilities: {enhanced_result.original_examples_count}")
                        print(f"  📈 Enhanced examples: {enhanced_result.enhanced_examples_count}")
                        print(f"  🎯 Enhancement ratio: {enhanced_result.creation_metadata.get('enhancement_ratio', 0):.1f}x")
                        
                        # Convert enhanced examples to training pairs format
                        enhanced_training_pairs = []
                        for example in enhanced_result.enhanced_examples:
                            enhanced_training_pairs.append({
                                'instruction': example.instruction,
                                'response': example.response,
                                'metadata': example.metadata
                            })
                        
                        # Save enhanced dataset separately with custom filename
                        enhanced_file = output_path / f"enhanced_train_{timestamp}.jsonl"
                        # Temporarily modify the dataset name in metadata to use our desired filename
                        original_dataset_name = enhanced_result.creation_metadata.get('dataset_name')
                        enhanced_result.creation_metadata['dataset_name'] = f"enhanced_train_{timestamp}"
                        enhanced_creator.save_enhanced_dataset(enhanced_result, format='jsonl')
                        # Restore original dataset name
                        if original_dataset_name:
                            enhanced_result.creation_metadata['dataset_name'] = original_dataset_name
                        print(f"💾 Enhanced dataset saved to: enhanced_datasets/code-aware-training/")
                        
                        # Combine with standard training pairs for comprehensive dataset
                        combined_training_pairs = training_pairs + enhanced_training_pairs
                        print(f"🔗 Combined dataset: {len(training_pairs)} standard + {len(enhanced_training_pairs)} enhanced = {len(combined_training_pairs)} total")
                        
                        # Use combined dataset for training
                        training_pairs = combined_training_pairs
                        
                    else:
                        print(f"⚠️ Enhanced dataset creation failed: {enhanced_result.error_message}")
                        print(f"   Continuing with standard narrativized dataset only...")
                        
                except ImportError as e:
                    print(f"⚠️ Enhanced dataset creator not available: {e}")
                    print(f"   Continuing with standard narrativized dataset only...")
                except Exception as e:
                    print(f"⚠️ Enhanced dataset creation error: {e}")
                    print(f"   Continuing with standard narrativized dataset only...")
                
                # Split into training and validation sets (80/20)
                import random
                random.shuffle(training_pairs)
                split_point = int(len(training_pairs) * 0.8)
                train_data = training_pairs[:split_point]
                val_data = training_pairs[split_point:]
                
                # Save training set  
                train_file = output_path / f"train_{timestamp}.jsonl"
                with open(train_file, 'w') as f:
                    for item in train_data:
                        f.write(json.dumps(item) + '\n')
                
                # Save validation set
                val_file = output_path / f"validation_{timestamp}.jsonl"
                with open(val_file, 'w') as f:
                    for item in val_data:
                        f.write(json.dumps(item) + '\n')
                
                # Create dataset info file
                dataset_info = {
                    'created_at': timestamp,
                    'total_examples': len(training_pairs),
                    'train_examples': len(train_data), 
                    'validation_examples': len(val_data),
                    'source_vulnerabilities': len(narrativized_results)
                }
                
                info_file = output_path / f"dataset_info_{timestamp}.json"
                with open(info_file, 'w') as f:
                    json.dump(dataset_info, f, indent=2)
                
                print(f"✅ Fine-tuning dataset prepared:")
                print(f"  📚 Training examples: {len(train_data)}")
                print(f"  📖 Validation examples: {len(val_data)}") 
                print(f"  💾 Files saved:")
                print(f"    - {train_file}")
                print(f"    - {val_file}")
                print(f"    - {info_file}")
                
                # **Phase 4: Production Dataset Upload**
                print("\\n" + "="*60)
                print("🚀 Phase 4: Uploading to Production HuggingFace Dataset")
                print("="*60)
                
                try:
                    from datasets import Dataset
                    from huggingface_hub import HfApi
                    
                    print(f"📤 Uploading {len(training_pairs)} training pairs to production dataset...")
                    print(f"🎯 Target: hitoshura25/webauthn-security-vulnerabilities-olmo")
                    
                    # Create HuggingFace Dataset from training pairs
                    dataset = Dataset.from_list(training_pairs)
                    
                    # Upload to production dataset (PUBLIC)
                    dataset.push_to_hub(
                        repo_id="hitoshura25/webauthn-security-vulnerabilities-olmo",
                        private=False,  # PUBLIC dataset for research community
                        token=True      # Use saved HuggingFace token
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
                
                # **Phase 3: Sequential Fine-Tuning Integration (New Default Behavior)**
                # Progressive specialization: Stage 1 (Analysis) → Stage 2 (Code Fixes)
                disable_sequential_fine_tuning = args.disable_sequential_fine_tuning if args else False
                upload_model = not (args.skip_model_upload if args else False)  # Default True, disabled by --skip-model-upload
                
                # Try sequential fine-tuning first (new default)
                if is_sequential_fine_tuning_available() and not disable_sequential_fine_tuning:
                    print("🎯 Using Phase 3: Sequential Fine-Tuning (Default)")
                    summary = run_sequential_fine_tuning_phase(
                        vulnerabilities=narrativized_results,  # Use full vulnerability data with narratives
                        summary=summary,
                        disable_sequential_fine_tuning=disable_sequential_fine_tuning,
                        upload_model=upload_model
                    )
                else:
                    # Fall back to Phase 5: Single-Stage Fine-Tuning (Legacy)
                    print("🔄 Falling back to Phase 5: Single-Stage Fine-Tuning")
                    skip_fine_tuning = args.skip_fine_tuning if args else False
                    summary = integrate_fine_tuning_if_available(train_file, train_data, summary, skip_fine_tuning, upload_model)
                
            else:
                print("⚠️ No narrativized results available for fine-tuning dataset preparation")
        
        except ImportError as e:
            print(f"⚠️ Narrativization module not available: {e}")
            print("   Phase 2 and Phase 3 will be skipped")
        except Exception as e:
            print(f"❌ Error in Phase 2/3: {e}")
        
        return results, summary
    else:
        print("\\n⚠️ No vulnerabilities found to analyze")
        return [], {}


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
        description="Process security artifacts with OLMo analysis",
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
    print("=" * 60)

    # Check if artifacts directory exists and has content
    artifacts_dir = Path(args.artifacts_dir)
    
    if artifacts_dir.exists() and any(artifacts_dir.iterdir()):
        # Directory exists and has content - process existing artifacts
        print(f"📂 Using existing artifacts directory: {artifacts_dir}")
        downloaded_path = artifacts_dir
        
    else:
        # Directory is empty/missing - download latest artifacts there
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

    # Process all scans
    output_dir = str(args.output_dir)
    
    # Enhanced processing with OLMo-2-1B
    results, summary = process_all_scans_enhanced(scan_files, output_dir, args)

    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
