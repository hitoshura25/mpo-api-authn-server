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
import zipfile
import shutil
import subprocess

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from parsers.trivy_parser import parse_trivy_json
from parsers.checkov_parser import parse_checkov_json
from parsers.sarif_parser import parse_sarif_json
from parsers.semgrep_parser import parse_semgrep_json
from parsers.osv_parser import parse_osv_json
from parsers.zap_parser import parse_zap_json
from analysis.olmo_analyzer import OLMoSecurityAnalyzer


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
        if 'trivy' in file_str and file_path.suffix == '.json':
            scan_files['trivy'].append(str(file_path))
        elif 'checkov' in file_str:
            if file_path.suffix in ['.json', '.sarif']:
                scan_files['checkov'].append(str(file_path))
        elif 'semgrep' in file_str and file_path.suffix == '.json':
            scan_files['semgrep'].append(str(file_path))
        elif 'osv' in file_str and file_path.suffix == '.json':
            scan_files['osv'].append(str(file_path))
        elif file_path.suffix == '.sarif':
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


def process_all_scans(scan_files: dict, output_dir: str):
    """
    Process all found security scan files with OLMo
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize OLMo analyzer
    print("\n🤖 Initializing OLMo Security Analyzer...")
    analyzer = OLMoSecurityAnalyzer()
    print("✅ OLMo analyzer initialized successfully", flush=True)
    
    all_vulnerabilities = []
    
    # Process each scan type
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
    
    # Analyze with OLMo
    if all_vulnerabilities:
        print(f"\n🔍 Starting analysis of {len(all_vulnerabilities)} total vulnerabilities with OLMo...", flush=True)
        
        # Process ALL vulnerabilities in batches
        batch_size = 20  # Process 20 at a time for memory efficiency
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
            print(f"   Calling analyzer.batch_analyze()...", flush=True)
            
            batch_results = analyzer.batch_analyze(
                batch,
                max_items=len(batch)
            )
            print(f"   ✅ Batch {batch_num} completed, got {len(batch_results)} results", flush=True)
            results.extend(batch_results)
            
            # Optional: Add a small delay between batches to avoid overloading
            if i + batch_size < len(all_vulnerabilities):
                print("  Preparing next batch...")
        
        # Generate summary report
        summary = analyzer.generate_summary_report(results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = output_path / f"olmo_analysis_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Save summary
        summary_file = output_path / f"olmo_analysis_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"💾 Summary saved to: {summary_file}")
        
        # Print summary
        print("\n📈 Analysis Summary:")
        print(f"  Total Analyzed: {summary['total_analyzed']}")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        
        if summary['by_severity']:
            print("\n  By Severity:")
            for sev, count in summary['by_severity'].items():
                print(f"    {sev}: {count}")
        
        if summary['by_tool']:
            print("\n  By Tool:")
            for tool, count in summary['by_tool'].items():
                print(f"    {tool}: {count}")
        
        return results, summary
    else:
        print("\n⚠️ No vulnerabilities found to analyze")
        return [], {}


def download_latest_artifacts(output_dir: str) -> Path | None:
    """
    Downloads artifacts from the latest successful GitHub Actions run on the default branch.
    """
    output_path = Path(output_dir)

    # 1. Check if 'gh' CLI is installed
    if not shutil.which("gh"):
        print("❌ 'gh' CLI not found. Please install it and authenticate: https://cli.github.com/")
        return None

    print("📥 Downloading latest security artifacts using 'gh' CLI...")

    # 2. Clean up existing directory
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
    print("=" * 60)
    print("🔒 WebAuthn Security Analysis with OLMo")
    print("=" * 60)

    # Download latest artifacts from GitHub Actions
    artifact_dir = "data/security_artifacts"
    downloaded_path = download_latest_artifacts(artifact_dir)

    if not downloaded_path:
        print("\n❌ Failed to download artifacts. Exiting.")
        return 1

    print(f"\n📂 Using artifact directory: {downloaded_path}")

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
    output_dir = "data/olmo_analysis_results"
    results, summary = process_all_scans(scan_files, output_dir)

    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
