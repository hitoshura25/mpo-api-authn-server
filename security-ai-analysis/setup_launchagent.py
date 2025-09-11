#!/usr/bin/env python3
"""
Simple LaunchAgent Setup Script for OLMo Security Daemon
Creates user-specific LaunchAgent plist from template using current portable configuration.
"""
import sys
import subprocess
import shutil
from pathlib import Path

# Add current directory to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config_manager import get_default_config

def setup_launchagent(dry_run=False):
    """Setup LaunchAgent for current user using minimal template substitution."""
    print("🚀 Setting up OLMo Security LaunchAgent...")
    
    # Get current project root (where daemon script is launched from)
    project_root = Path(__file__).parent.parent.absolute()
    print(f"📁 Project root: {project_root}")
    
    # Validate required files exist
    daemon_script = project_root / "local-analysis" / "security_artifact_daemon.py"
    venv_python = project_root / "security-ai-analysis" / "venv" / "bin" / "python3"
    template_path = Path(__file__).parent / "templates" / "daemon.plist.template"
    
    if not daemon_script.exists():
        print(f"❌ Daemon script not found: {daemon_script}")
        return False
    
    if not venv_python.exists():
        print(f"❌ Virtual environment Python not found: {venv_python}")
        print("💡 Run setup.py first to create virtual environment")
        return False
        
    if not template_path.exists():
        print(f"❌ Template not found: {template_path}")
        return False
    
    print(f"✅ Daemon script: {daemon_script}")
    print(f"✅ Python executable: {venv_python}")
    print(f"✅ Template file: {template_path}")
    
    # Load template and substitute PROJECT_ROOT
    with open(template_path, 'r') as f:
        plist_content = f.read()
    
    # Simple substitution - just replace {{PROJECT_ROOT}} with actual project path
    plist_content = plist_content.replace('{{PROJECT_ROOT}}', str(project_root))
    
    if dry_run:
        print("\n📄 Generated plist content:")
        print(plist_content)
        print(f"\n📋 Substituted PROJECT_ROOT: {project_root}")
        return True
    
    # Write to LaunchAgents directory
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(exist_ok=True)
    
    plist_path = launch_agents_dir / "com.mpo.security-analysis.daemon.plist"
    
    # Backup existing plist if it exists
    if plist_path.exists():
        backup_path = plist_path.with_suffix('.plist.backup')
        shutil.copy2(plist_path, backup_path)
        print(f"📂 Backed up existing plist to: {backup_path}")
    
    # Write new plist
    with open(plist_path, 'w') as f:
        f.write(plist_content)
    
    print(f"✅ LaunchAgent plist created: {plist_path}")
    
    # Load the LaunchAgent
    try:
        # Unload first (ignore errors if not loaded)
        subprocess.run(['launchctl', 'unload', str(plist_path)], 
                      capture_output=True, check=False)
        
        # Load the new configuration
        result = subprocess.run(['launchctl', 'load', str(plist_path)], 
                               capture_output=True, text=True, check=True)
        print("✅ LaunchAgent loaded successfully")
        
        # Check status
        status_result = subprocess.run(['launchctl', 'list', 'com.mpo.security-analysis.daemon'],
                                     capture_output=True, text=True)
        if status_result.returncode == 0:
            print("✅ LaunchAgent is running")
            # Show some status info
            lines = status_result.stdout.strip().split('\n')
            if len(lines) >= 3:
                print(f"   PID: {lines[0]}")
                print(f"   Exit Code: {lines[1]}")
        else:
            print("⚠️ LaunchAgent may not be running properly")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to load LaunchAgent: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        return False
    
    print(f"\n📋 Setup Summary:")
    print(f"   Project Root: {project_root}")
    print(f"   LaunchAgent: {plist_path}")
    print(f"   Log files: {project_root}/security-ai-analysis/results/daemon_*.log")
    
    print(f"\n💡 Useful Commands:")
    print(f"   Check status: launchctl list com.mpo.security-analysis.daemon")
    print(f"   View logs: tail -f {project_root}/security-ai-analysis/results/daemon_stdout.log")
    print(f"   Stop daemon: launchctl unload {plist_path}")
    print(f"   Restart daemon: launchctl unload {plist_path} && launchctl load {plist_path}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup OLMo Security LaunchAgent')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show generated plist content without creating files')
    args = parser.parse_args()
    
    success = setup_launchagent(dry_run=args.dry_run)
    exit(0 if success else 1)