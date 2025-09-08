#!/usr/bin/env python3
"""
GitHub Actions Security Artifact Polling Daemon

✅ VALIDATED: Based on GitHub CLI official documentation
- gh run list syntax validated against GitHub CLI manual
- gh run download syntax confirmed via local testing
- All GitHub API interactions use official CLI commands

This daemon monitors GitHub Actions for new security scan artifacts and triggers
local OLMo analysis when new scans complete on the main branch.

Key Features:
- Polls GitHub Actions every 5 minutes for new security scans
- Downloads artifacts automatically when new scans are detected
- Triggers local OLMo-2-1B analysis with MLX optimization
- Maintains state to avoid duplicate processing
- Comprehensive logging and error handling
- macOS LaunchAgent compatible

Usage:
    # Run manually for testing
    python3 security_artifact_daemon.py --test-mode
    
    # Run as daemon (production mode)
    python3 security_artifact_daemon.py
"""

import os
import sys
import json
import time
import subprocess
import shutil
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging with expanded path
import os
log_file = os.path.expanduser('~/olmo-security-analysis/daemon.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SecurityArtifactDaemon:
    """Polls GitHub Actions for security artifacts and triggers local analysis."""
    
    def __init__(self, 
                 repo: str = "hitoshura25/mpo-api-authn-server",
                 data_dir: str = "~/olmo-security-analysis",
                 poll_interval: int = 300):  # 5 minutes
        
        self.repo = repo
        self.data_dir = Path(data_dir).expanduser()
        self.poll_interval = poll_interval
        self.running = False
        
        # State management
        self.state_file = self.data_dir / "daemon_state.json"
        self.artifacts_dir = self.data_dir / "artifacts"
        self.analysis_dir = self.data_dir / "analysis"
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize state
        self.state = self._load_state()
        
        logger.info(f"Initialized SecurityArtifactDaemon for repo: {repo}")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Poll interval: {poll_interval} seconds")
    
    def _load_state(self) -> Dict:
        """Load daemon state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Loaded state: last processed run {state.get('last_run_id', 'none')}")
                    return state
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        
        return {
            'last_run_id': None,
            'last_check_time': None,
            'processed_runs': []
        }
    
    def _save_state(self):
        """Save daemon state to file."""
        try:
            self.state['last_check_time'] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def check_prerequisites(self) -> bool:
        """Check if GitHub CLI and required tools are available."""
        required_tools = ['gh', 'python3']
        missing_tools = []
        
        for tool in required_tools:
            if not shutil.which(tool):
                missing_tools.append(tool)
                logger.error(f"❌ {tool} is not available")
            else:
                logger.info(f"✅ {tool} is available")
        
        if missing_tools:
            logger.error(f"Missing tools: {', '.join(missing_tools)}")
            logger.error("Install GitHub CLI: https://cli.github.com/")
            return False
        
        # Check GitHub CLI authentication
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True, text=True, check=True, timeout=30
            )
            logger.info("✅ GitHub CLI authentication verified")
            return True
        except subprocess.CalledProcessError as e:
            logger.error("❌ GitHub CLI not authenticated")
            logger.error("Run: gh auth login")
            return False
        except subprocess.TimeoutExpired:
            logger.error("❌ GitHub CLI authentication check timed out")
            return False
    
    def get_latest_security_run(self) -> Optional[Dict]:
        """
        Get the latest successful Main CI/CD run on main branch.
        
        ✅ VALIDATED: gh run list syntax confirmed against GitHub CLI manual
        Source: https://cli.github.com/manual/gh_run_list
        """
        logger.info("🔍 Checking for latest Main CI/CD security run...")
        
        try:
            # ✅ VALIDATED: Official GitHub CLI syntax tested locally
            result = subprocess.run([
                "gh", "run", "list",
                "--repo", self.repo,
                "--workflow", "main-ci-cd.yml",
                "--branch", "main", 
                "--status", "success",
                "--limit", "1",
                "--json", "databaseId,createdAt,headSha,conclusion,workflowName"
            ], capture_output=True, text=True, check=True, timeout=30)
            
            runs = json.loads(result.stdout)
            if not runs:
                logger.info("No successful Main CI/CD runs found")
                return None
            
            latest_run = runs[0]
            run_id = str(latest_run['databaseId'])
            created_at = latest_run['createdAt']
            head_sha = latest_run['headSha']
            
            logger.info(f"Latest run: {run_id} (SHA: {head_sha[:8]}, {created_at})")
            return {
                'run_id': run_id,
                'created_at': created_at,
                'head_sha': head_sha,
                'conclusion': latest_run['conclusion']
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get latest run: {e.stderr}")
            return None
        except subprocess.TimeoutExpired:
            logger.error("GitHub CLI timeout while fetching runs")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse run list JSON: {e}")
            return None
    
    def download_security_artifacts(self, run_id: str) -> Optional[Path]:
        """
        Download security artifacts for the specified run.
        
        ✅ VALIDATED: gh run download syntax confirmed via local testing
        Source: https://cli.github.com/manual/gh_run_download
        """
        logger.info(f"📥 Downloading security artifacts for run {run_id}...")
        
        # Create run-specific directory
        run_dir = self.artifacts_dir / f"run_{run_id}"
        if run_dir.exists():
            logger.info(f"Artifacts already exist for run {run_id}, cleaning up...")
            shutil.rmtree(run_dir)
        
        # Security artifact patterns (from original implementation)
        patterns = [
            "*zap*", "*trivy*", "*sarif*", "*osv*", 
            "*gitleaks*", "*semgrep*", "*checkov*"
        ]
        
        try:
            # ✅ VALIDATED: Official GitHub CLI download command
            download_command = [
                "gh", "run", "download", run_id,
                "-R", self.repo,
                "-D", str(run_dir)
            ]
            for pattern in patterns:
                download_command.extend(["--pattern", pattern])
            
            logger.info(f"Running: {' '.join(download_command)}")
            result = subprocess.run(
                download_command, 
                check=True, 
                capture_output=True, 
                text=True, 
                timeout=600  # 10 minutes for download
            )
            
            # Check if any artifacts were actually downloaded
            if not any(run_dir.iterdir()) if run_dir.exists() else True:
                logger.warning(f"No security artifacts found for run {run_id}")
                return None
            
            logger.info(f"✅ Artifacts downloaded to: {run_dir}")
            
            # List downloaded artifacts
            artifact_files = list(run_dir.rglob("*"))
            logger.info(f"Downloaded {len(artifact_files)} files:")
            for artifact_file in artifact_files[:10]:  # Show first 10
                logger.info(f"  - {artifact_file.name}")
            if len(artifact_files) > 10:
                logger.info(f"  ... and {len(artifact_files) - 10} more files")
            
            return run_dir
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download artifacts: {e.stderr}")
            return None
        except subprocess.TimeoutExpired:
            logger.error("Artifact download timed out")
            return None
    
    def trigger_local_analysis(self, artifacts_dir: Path, run_info: Dict) -> bool:
        """Trigger local OLMo analysis on the downloaded artifacts."""
        logger.info(f"🤖 Starting local OLMo analysis for run {run_info['run_id']}...")
        
        # Output directory for this analysis
        analysis_output = self.analysis_dir / f"analysis_{run_info['run_id']}"
        analysis_output.mkdir(exist_ok=True)
        
        # Path to enhanced process_artifacts.py script
        process_script = Path(__file__).parent.parent / "security-ai-analysis" / "process_artifacts.py"
        
        if not process_script.exists():
            logger.error(f"Process script not found: {process_script}")
            return False
        
        try:
            # Run local analysis with enhanced script
            analysis_command = [
                sys.executable, str(process_script),
                "--local-mode",
                "--artifacts-dir", str(artifacts_dir),
                "--output-dir", str(analysis_output),
                "--model-name", "/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4",  # MLX-optimized OLMo-2-1B
                "--branch", "main",
                "--commit", run_info['head_sha']
            ]
            
            logger.info(f"Running analysis: {' '.join(analysis_command)}")
            
            result = subprocess.run(
                analysis_command,
                check=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour for analysis
            )
            
            logger.info("✅ Local OLMo analysis completed successfully")
            logger.info(f"Analysis output: {analysis_output}")
            
            # Log analysis summary
            if result.stdout:
                logger.info("Analysis stdout summary:")
                for line in result.stdout.strip().split('\\n')[-10:]:  # Last 10 lines
                    logger.info(f"  {line}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Local analysis failed: {e}")
            if e.stderr:
                logger.error(f"Analysis stderr: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Local analysis timed out after 1 hour")
            return False
    
    def process_new_run(self, run_info: Dict) -> bool:
        """Process a new security run."""
        run_id = run_info['run_id']
        
        if run_id in self.state.get('processed_runs', []):
            logger.info(f"Run {run_id} already processed, skipping")
            return True
        
        logger.info(f"🆕 Processing new run: {run_id}")
        
        # Download artifacts
        artifacts_dir = self.download_security_artifacts(run_id)
        if not artifacts_dir:
            logger.error(f"Failed to download artifacts for run {run_id}")
            return False
        
        # Trigger local analysis
        analysis_success = self.trigger_local_analysis(artifacts_dir, run_info)
        if not analysis_success:
            logger.error(f"Local analysis failed for run {run_id}")
            return False
        
        # Update state
        self.state['last_run_id'] = run_id
        if 'processed_runs' not in self.state:
            self.state['processed_runs'] = []
        self.state['processed_runs'].append(run_id)
        
        # Keep only last 50 processed runs to prevent unbounded growth
        self.state['processed_runs'] = self.state['processed_runs'][-50:]
        
        self._save_state()
        
        logger.info(f"✅ Successfully processed run {run_id}")
        return True
    
    def poll_cycle(self) -> bool:
        """Execute one polling cycle."""
        logger.info("🔄 Starting polling cycle...")
        
        try:
            # Get latest security run
            latest_run = self.get_latest_security_run()
            if not latest_run:
                logger.info("No runs to process")
                return True
            
            current_run_id = latest_run['run_id']
            
            # Check if this is a new run
            if current_run_id != self.state.get('last_run_id'):
                logger.info(f"New run detected: {current_run_id}")
                return self.process_new_run(latest_run)
            else:
                logger.info(f"No new runs (latest: {current_run_id})")
                return True
                
        except Exception as e:
            logger.error(f"Polling cycle failed: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def run_daemon(self, test_mode: bool = False):
        """Run the daemon main loop."""
        logger.info("🚀 Starting Security Artifact Daemon...")
        logger.info(f"Repository: {self.repo}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        logger.info(f"Test mode: {test_mode}")
        
        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed, exiting")
            return 1
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.running = True
        
        try:
            if test_mode:
                logger.info("Running single test cycle...")
                success = self.poll_cycle()
                logger.info(f"Test cycle result: {'SUCCESS' if success else 'FAILED'}")
                return 0 if success else 1
            else:
                logger.info("Starting continuous polling...")
                while self.running:
                    try:
                        self.poll_cycle()
                        
                        if self.running:  # Check if we should continue
                            logger.info(f"💤 Sleeping for {self.poll_interval} seconds...")
                            for _ in range(self.poll_interval):
                                if not self.running:
                                    break
                                time.sleep(1)
                        
                    except KeyboardInterrupt:
                        logger.info("Received keyboard interrupt")
                        break
                    except Exception as e:
                        logger.error(f"Unexpected error in main loop: {e}")
                        if self.running:
                            logger.info("Continuing after error...")
                
                logger.info("Daemon stopped")
                return 0
                
        except Exception as e:
            logger.error(f"Daemon failed: {e}")
            return 1


def main():
    """Main entry point for the security artifact daemon."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="GitHub Actions Security Artifact Polling Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single test cycle
  python3 security_artifact_daemon.py --test-mode
  
  # Run as daemon (production)
  python3 security_artifact_daemon.py --repo your-org/your-repo
  
  # Custom polling interval (default: 300 seconds = 5 minutes)
  python3 security_artifact_daemon.py --poll-interval 600
        """
    )
    
    parser.add_argument("--repo", default="hitoshura25/mpo-api-authn-server",
                       help="GitHub repository in format owner/repo")
    parser.add_argument("--data-dir", default="~/olmo-security-analysis",
                       help="Directory for data storage")
    parser.add_argument("--poll-interval", type=int, default=300,
                       help="Polling interval in seconds (default: 300 = 5 minutes)")
    parser.add_argument("--test-mode", action="store_true",
                       help="Run single test cycle and exit")
    
    args = parser.parse_args()
    
    try:
        # Create and run daemon
        daemon = SecurityArtifactDaemon(
            repo=args.repo,
            data_dir=args.data_dir,
            poll_interval=args.poll_interval
        )
        
        return daemon.run_daemon(test_mode=args.test_mode)
        
    except KeyboardInterrupt:
        logger.info("🛑 Daemon interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Daemon failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())