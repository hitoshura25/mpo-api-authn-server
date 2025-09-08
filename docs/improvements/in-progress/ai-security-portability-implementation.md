# AI Security Dataset Research Initiative - Portability Implementation Plan

## Executive Summary

This document provides a comprehensive plan to make the fully working AI Security Dataset Research Initiative portable across different development environments while preserving the current working system. The system processes 440+ vulnerabilities with 20-30X MLX performance improvement and maintains a production HuggingFace dataset.

## Current Working System Analysis

### ✅ Production System Status
- **Complete 4-phase pipeline**: Analysis → Narrativization → Fine-tuning → HuggingFace Upload
- **Production dataset**: Live at `hitoshura25/webauthn-security-vulnerabilities-olmo`
- **Local automation**: LaunchAgent daemon polling GitHub every 5 minutes
- **MLX optimization**: 20-30X faster processing on Apple Silicon

### 🔍 Current Hardcoded Dependencies

#### File Paths (Non-Portable)
```python
# From process_artifacts.py line 791
--model-name "/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4"

# From security_artifact_daemon.py line 284
--model-name "/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4"

# From security_artifact_daemon.py line 46
log_file = os.path.expanduser('~/olmo-security-analysis/daemon.log')

# From security_artifact_daemon.py line 65
data_dir: str = "~/olmo-security-analysis"
```

#### LaunchAgent Configuration (User-Specific)
```xml
<!-- From com.webauthn.security-artifact-daemon.plist -->
<string>/Users/vinayakmenon/olmo-security-analysis/venv/bin/python3</string>
<string>/Users/vinayakmenon/mpo-api-authn-server/local-analysis/security_artifact_daemon.py</string>
<string>/Users/vinayakmenon/olmo-security-analysis</string>
<string>/Users/vinayakmenon/mpo-api-authn-server</string>
```

#### Documentation Examples
```bash
# From README.md
source /Users/vinayakmenon/olmo-security-analysis/venv/bin/activate
--model-name "/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4"
cd /Users/vinayakmenon/mpo-api-authn-server/local-analysis
```

### 🏗️ Working Architecture Components

#### Core Pipeline Components
1. **process_artifacts.py** - Integrated 4-phase pipeline (868 lines)
2. **security_artifact_daemon.py** - LaunchAgent daemon (488 lines)  
3. **analysis/olmo_analyzer.py** - MLX-optimized analyzer
4. **create_narrativized_dataset.py** - Narrativization logic
5. **parsers/** - Security tool parsers (trivy, checkov, semgrep, etc.)

#### MLX Model Integration
- **Model Location**: `/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4`
- **Performance**: 214.6 tokens/sec on Apple Silicon
- **Integration**: Direct model path references in analyzer initialization

#### LaunchAgent Automation
- **Plist File**: User-specific paths to Python executable and scripts
- **Environment**: PATH, PYTHONPATH, working directory all hardcoded
- **Logging**: User-specific log file paths

## Implementation Plan Overview

### Phase-Based Approach (Safe & Incremental)

Each phase is designed for independent implementation with validation checkpoints and rollback procedures.

```
Phase 1: Environment Variable Implementation (2-3 hours)
    ↓
Phase 2: Automatic Model Detection & Download (4-5 hours)
    ↓  
Phase 3: Configuration File System (3-4 hours)
    ↓
Phase 4: LaunchAgent Portability (2-3 hours)
    ↓
Phase 5: Documentation Updates (2-3 hours)
    ↓
Phase 6: Testing & Validation (3-4 hours)
```

**Total Estimated Time**: 16-22 hours of implementation across multiple sessions

---

## Phase 1: Environment Variable Implementation

### Objective
Replace hardcoded paths with environment variables while maintaining backward compatibility.

### 1.1 Environment Variables Definition

```bash
# Core directory structure
export OLMO_BASE_DIR="$HOME/olmo-security-analysis"
export OLMO_MODEL_DIR="$OLMO_BASE_DIR/models"
export OLMO_DATA_DIR="$OLMO_BASE_DIR/data"
export OLMO_ANALYSIS_DIR="$OLMO_BASE_DIR/analysis"

# Model configuration
export OLMO_MODEL_PATH="$OLMO_MODEL_DIR/OLMo-2-1B-mlx-q4"
export OLMO_MODEL_NAME="OLMo-2-1B-mlx-q4"

# Project paths
export WEBAUTHN_PROJECT_DIR="$HOME/mpo-api-authn-server"
export WEBAUTHN_SECURITY_ANALYSIS_DIR="$WEBAUTHN_PROJECT_DIR/security-ai-analysis"

# GitHub repository
export GITHUB_REPO="hitoshura25/mpo-api-authn-server"

# Virtual environment
export OLMO_VENV_PATH="$OLMO_BASE_DIR/venv"
```

### 1.2 Script Modifications

#### A. process_artifacts.py Changes

**Current Code (Line 791)**:
```python
parser.add_argument("--model-name", type=str, default="/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4",
                   help="OLMo-2-1B model to use for analysis")
```

**New Code**:
```python
# Get default model path from environment with fallback
default_model_path = os.getenv(
    'OLMO_MODEL_PATH', 
    os.path.expanduser('~/olmo-security-analysis/models/OLMo-2-1B-mlx-q4')
)

parser.add_argument("--model-name", type=str, default=default_model_path,
                   help="OLMo-2-1B model to use for analysis (set OLMO_MODEL_PATH to override)")
```

#### B. security_artifact_daemon.py Changes

**Current Code (Line 46)**:
```python
log_file = os.path.expanduser('~/olmo-security-analysis/daemon.log')
```

**New Code**:
```python
# Get log directory from environment with fallback
olmo_base_dir = os.getenv('OLMO_BASE_DIR', os.path.expanduser('~/olmo-security-analysis'))
log_file = os.path.join(olmo_base_dir, 'daemon.log')
```

**Current Code (Line 65)**:
```python
def __init__(self, 
             repo: str = "hitoshura25/mpo-api-authn-server",
             data_dir: str = "~/olmo-security-analysis",
             poll_interval: int = 300):
```

**New Code**:
```python
def __init__(self, 
             repo: str = None,
             data_dir: str = None,
             poll_interval: int = 300):
    
    # Use environment variables with fallbacks
    self.repo = repo or os.getenv('GITHUB_REPO', "hitoshura25/mpo-api-authn-server")
    data_dir_default = os.getenv('OLMO_BASE_DIR', "~/olmo-security-analysis")
    data_dir = data_dir or data_dir_default
```

**Current Code (Line 284)**:
```python
"--model-name", "/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4",
```

**New Code**:
```python
"--model-name", os.getenv('OLMO_MODEL_PATH', 
    os.path.expanduser('~/olmo-security-analysis/models/OLMo-2-1B-mlx-q4')),
```

### 1.3 Validation Checkpoint

```bash
# Test environment variable override
export OLMO_BASE_DIR="/tmp/test-olmo"
export OLMO_MODEL_PATH="/tmp/test-olmo/models/test-model"

# Verify script picks up new paths
python3 process_artifacts.py --help | grep "default:"
python3 security_artifact_daemon.py --test-mode --repo test/test
```

### 1.4 Rollback Procedure

If changes cause issues:
1. Revert modified files: `git checkout -- process_artifacts.py security_artifact_daemon.py`
2. Validate current system still works: `python3 process_artifacts.py --help`
3. Re-test existing functionality with hardcoded paths

---

## Phase 2: Automatic Model Detection & Download

### Objective
Implement automatic MLX model detection and download to eliminate manual setup requirements.

### 2.1 Model Detection Logic

#### A. Create model_manager.py

```python
#!/usr/bin/env python3
"""
Automatic OLMo MLX Model Management
Handles detection, download, and caching of MLX-optimized models
"""
import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging

class OLMoMLXModelManager:
    """Manages OLMo MLX model detection and download."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.getenv(
            'OLMO_BASE_DIR', 
            os.path.expanduser('~/olmo-security-analysis')
        ))
        self.models_dir = self.base_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # MLX model configurations
        self.available_models = {
            "OLMo-2-1B-mlx-q4": {
                "url": "mlx-community/OLMo-2-1B-1124-4bit",
                "local_name": "OLMo-2-1B-mlx-q4",
                "size_gb": 1.2,
                "description": "4-bit quantized OLMo-2-1B optimized for Apple Silicon"
            },
            "OLMo-2-1B-mlx": {
                "url": "mlx-community/OLMo-2-1B-1124",  
                "local_name": "OLMo-2-1B-mlx",
                "size_gb": 2.1,
                "description": "Full precision OLMo-2-1B for Apple Silicon"
            }
        }
        
        self.logger = logging.getLogger(__name__)
    
    def detect_available_models(self) -> Dict[str, Dict]:
        """Detect locally available MLX models."""
        available = {}
        
        for model_name, config in self.available_models.items():
            model_path = self.models_dir / config["local_name"]
            if self.is_valid_mlx_model(model_path):
                available[model_name] = {
                    **config,
                    "path": str(model_path),
                    "status": "available"
                }
                self.logger.info(f"✅ Found MLX model: {model_name} at {model_path}")
        
        return available
    
    def is_valid_mlx_model(self, model_path: Path) -> bool:
        """Check if path contains a valid MLX model."""
        if not model_path.exists():
            return False
        
        # Check for required MLX model files
        required_files = ["config.json", "tokenizer.json"]
        mlx_files = list(model_path.glob("*.safetensors")) or list(model_path.glob("*.npz"))
        
        has_required = all((model_path / f).exists() for f in required_files)
        has_weights = len(mlx_files) > 0
        
        return has_required and has_weights
    
    def download_model(self, model_name: str) -> Optional[Path]:
        """Download and cache an MLX model."""
        if model_name not in self.available_models:
            self.logger.error(f"Unknown model: {model_name}")
            return None
        
        config = self.available_models[model_name]
        local_path = self.models_dir / config["local_name"]
        
        if self.is_valid_mlx_model(local_path):
            self.logger.info(f"Model {model_name} already exists at {local_path}")
            return local_path
        
        self.logger.info(f"Downloading {model_name} (~{config['size_gb']}GB)...")
        
        try:
            # Use huggingface-hub to download
            result = subprocess.run([
                sys.executable, "-c",
                f"""
import os
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="{config['url']}", 
    local_dir="{local_path}",
    local_dir_use_symlinks=False
)
print(f"Downloaded to: {local_path}")
"""
            ], capture_output=True, text=True, check=True)
            
            if self.is_valid_mlx_model(local_path):
                self.logger.info(f"✅ Successfully downloaded {model_name}")
                return local_path
            else:
                self.logger.error(f"Downloaded model appears invalid: {local_path}")
                return None
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to download {model_name}: {e.stderr}")
            return None
    
    def get_best_model(self) -> Tuple[str, Optional[Path]]:
        """Get the best available model, downloading if necessary."""
        # Check for existing models
        available = self.detect_available_models()
        
        # Prefer 4-bit quantized for speed
        if "OLMo-2-1B-mlx-q4" in available:
            model_path = Path(available["OLMo-2-1B-mlx-q4"]["path"])
            return "OLMo-2-1B-mlx-q4", model_path
        
        if "OLMo-2-1B-mlx" in available:
            model_path = Path(available["OLMo-2-1B-mlx"]["path"])
            return "OLMo-2-1B-mlx", model_path
        
        # No models available, download the preferred one
        self.logger.info("No MLX models found locally, downloading OLMo-2-1B-mlx-q4...")
        
        model_path = self.download_model("OLMo-2-1B-mlx-q4")
        if model_path:
            return "OLMo-2-1B-mlx-q4", model_path
        
        # Fallback to full precision if 4-bit fails
        self.logger.info("4-bit download failed, trying full precision...")
        model_path = self.download_model("OLMo-2-1B-mlx")
        if model_path:
            return "OLMo-2-1B-mlx", model_path
        
        return "none", None

def get_model_path() -> Optional[str]:
    """Convenience function to get the best available model path."""
    manager = OLMoMLXModelManager()
    model_name, model_path = manager.get_best_model()
    
    if model_path:
        print(f"Using MLX model: {model_name} at {model_path}")
        return str(model_path)
    else:
        print("❌ No MLX models available")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    model_path = get_model_path()
    if model_path:
        print(f"Model path: {model_path}")
        exit(0)
    else:
        exit(1)
```

### 2.2 Integration into Scripts

#### A. Modify process_artifacts.py

Add at the top after imports:
```python
from pathlib import Path
import sys

# Add local model manager
sys.path.append(str(Path(__file__).parent))
from model_manager import get_model_path
```

Update argument parser:
```python
# Auto-detect best MLX model or use environment override
default_model_path = os.getenv('OLMO_MODEL_PATH') or get_model_path()
if not default_model_path:
    print("❌ No MLX models available. Install with: pip install huggingface_hub")
    print("Models will be auto-downloaded on first run.")
    default_model_path = os.path.expanduser('~/olmo-security-analysis/models/OLMo-2-1B-mlx-q4')

parser.add_argument("--model-name", type=str, default=default_model_path,
                   help="OLMo-2-1B MLX model path (auto-detected or set OLMO_MODEL_PATH)")
```

### 2.3 Validation Checkpoint

```bash
# Test auto-detection with no existing models
rm -rf /tmp/test-olmo-models
export OLMO_BASE_DIR="/tmp/test-olmo-models"

# Test model manager
python3 model_manager.py

# Test integration  
python3 process_artifacts.py --help
```

### 2.4 Rollback Procedure

1. Remove new `model_manager.py` file
2. Revert changes to `process_artifacts.py`
3. Verify original hardcoded paths still work

---

## Phase 3: Configuration File System

### Objective
Implement centralized configuration file for all settings with environment variable overrides.

### 3.1 Configuration File Format

#### A. Create config/olmo-security-config.yaml

```yaml
# OLMo Security Analysis Configuration
# This file provides default settings for portable deployment

# Base directories (can be overridden with environment variables)
directories:
  base_dir: "~/olmo-security-analysis"
  data_dir: "${base_dir}/data"
  models_dir: "${base_dir}/models"
  analysis_dir: "${base_dir}/analysis"
  
# Model configuration
model:
  preferred_name: "OLMo-2-1B-mlx-q4"
  auto_download: true
  fallback_models:
    - "OLMo-2-1B-mlx"
    - "OLMo-2-1B-mlx-q4"

# GitHub repository
github:
  repo: "hitoshura25/mpo-api-authn-server"
  workflow: "main-ci-cd.yml"
  branch: "main"
  
# Daemon settings
daemon:
  poll_interval: 300  # 5 minutes
  log_level: "INFO"
  max_processed_runs: 50
  
# Analysis settings
analysis:
  batch_size: 30
  timeout_seconds: 3600  # 1 hour
  
# HuggingFace dataset
huggingface:
  dataset_repo: "hitoshura25/webauthn-security-vulnerabilities-olmo"
  private: false

# Environment variable overrides (these take precedence)
env_overrides:
  base_dir: "OLMO_BASE_DIR"
  model_path: "OLMO_MODEL_PATH"
  github_repo: "GITHUB_REPO"
  poll_interval: "OLMO_POLL_INTERVAL"
```

#### B. Create config_manager.py

```python
#!/usr/bin/env python3
"""
OLMo Security Configuration Manager
Handles loading and merging of configuration from files and environment variables
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

class OLMoSecurityConfig:
    """Manages configuration for OLMo Security Analysis system."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Find configuration file
        if config_file:
            self.config_file = Path(config_file)
        else:
            # Look for config in standard locations
            search_paths = [
                Path(__file__).parent / "config" / "olmo-security-config.yaml",
                Path.cwd() / "config" / "olmo-security-config.yaml",
                Path.home() / ".olmo-security-config.yaml"
            ]
            
            self.config_file = None
            for path in search_paths:
                if path.exists():
                    self.config_file = path
                    break
        
        # Load configuration
        self._config = self._load_config()
        self._resolve_variables()
        
        self.logger.info(f"Loaded config from: {self.config_file}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_file or not self.config_file.exists():
            self.logger.warning("No config file found, using defaults")
            return self._get_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
                self.logger.info(f"Loaded config from {self.config_file}")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'directories': {
                'base_dir': '~/olmo-security-analysis',
                'data_dir': '${base_dir}/data',
                'models_dir': '${base_dir}/models',
                'analysis_dir': '${base_dir}/analysis'
            },
            'model': {
                'preferred_name': 'OLMo-2-1B-mlx-q4',
                'auto_download': True,
                'fallback_models': ['OLMo-2-1B-mlx', 'OLMo-2-1B-mlx-q4']
            },
            'github': {
                'repo': 'hitoshura25/mpo-api-authn-server',
                'workflow': 'main-ci-cd.yml', 
                'branch': 'main'
            },
            'daemon': {
                'poll_interval': 300,
                'log_level': 'INFO',
                'max_processed_runs': 50
            },
            'env_overrides': {
                'base_dir': 'OLMO_BASE_DIR',
                'model_path': 'OLMO_MODEL_PATH',
                'github_repo': 'GITHUB_REPO'
            }
        }
    
    def _resolve_variables(self):
        """Resolve variables and apply environment overrides."""
        # Expand user paths
        for key, value in self._config.get('directories', {}).items():
            if isinstance(value, str):
                # First expand ~ to user home
                expanded = os.path.expanduser(value)
                # Then resolve ${variable} references
                if '${' in expanded:
                    base_dir = os.path.expanduser(self._config['directories'].get('base_dir', '~/olmo-security-analysis'))
                    expanded = expanded.replace('${base_dir}', base_dir)
                self._config['directories'][key] = expanded
        
        # Apply environment overrides
        overrides = self._config.get('env_overrides', {})
        for config_key, env_var in overrides.items():
            env_value = os.getenv(env_var)
            if env_value:
                if '.' in config_key:
                    # Handle nested keys like 'directories.base_dir'
                    parts = config_key.split('.')
                    current = self._config
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = env_value
                else:
                    self._config[config_key] = env_value
                
                self.logger.info(f"Override: {config_key} = {env_value} (from {env_var})")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support."""
        parts = key.split('.')
        current = self._config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def get_directories(self) -> Dict[str, str]:
        """Get all directory paths."""
        return self._config.get('directories', {})
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration."""
        return self._config.get('model', {})
    
    def get_github_config(self) -> Dict[str, str]:
        """Get GitHub configuration."""
        return self._config.get('github', {})
    
    def get_daemon_config(self) -> Dict[str, Any]:
        """Get daemon configuration."""
        return self._config.get('daemon', {})

# Global config instance
_config_instance = None

def get_config() -> OLMoSecurityConfig:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = OLMoSecurityConfig()
    return _config_instance
```

### 3.2 Update Scripts to Use Configuration

#### A. Modify security_artifact_daemon.py

Add at the top:
```python
from config_manager import get_config

# Load configuration
config = get_config()
dirs = config.get_directories()
daemon_config = config.get_daemon_config()
github_config = config.get_github_config()
```

Update initialization:
```python
# Replace hardcoded paths with config
log_file = os.path.join(dirs['base_dir'], 'daemon.log')

class SecurityArtifactDaemon:
    def __init__(self, 
                 repo: str = None,
                 data_dir: str = None,
                 poll_interval: int = None):
        
        # Use configuration with overrides
        self.repo = repo or github_config.get('repo')
        self.data_dir = Path(data_dir or dirs['base_dir']).expanduser()
        self.poll_interval = poll_interval or daemon_config.get('poll_interval', 300)
```

### 3.3 Validation Checkpoint

```bash
# Create test config
mkdir -p config
cat > config/olmo-security-config.yaml << EOF
directories:
  base_dir: "/tmp/test-config"
daemon:
  poll_interval: 120
EOF

# Test config loading
python3 config_manager.py
python3 security_artifact_daemon.py --test-mode
```

### 3.4 Rollback Procedure

1. Remove new config files: `rm -rf config/ config_manager.py`
2. Revert daemon script changes
3. Verify original functionality with environment variables

---

## Phase 4: LaunchAgent Portability

### Objective
Create templated LaunchAgent configuration that works for any user and system.

### 4.1 Template-Based LaunchAgent

#### A. Create templates/com.webauthn.security-artifact-daemon.plist.template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Service Identity -->
    <key>Label</key>
    <string>com.webauthn.security-artifact-daemon</string>
    
    <!-- Program Configuration (templated) -->
    <key>ProgramArguments</key>
    <array>
        <string>{{OLMO_VENV_PYTHON}}</string>
        <string>{{DAEMON_SCRIPT_PATH}}</string>
        <string>--repo</string>
        <string>{{GITHUB_REPO}}</string>
        <string>--data-dir</string>
        <string>{{OLMO_BASE_DIR}}</string>
        <string>--poll-interval</string>
        <string>{{POLL_INTERVAL}}</string>
    </array>
    
    <!-- Working Directory -->
    <key>WorkingDirectory</key>
    <string>{{WEBAUTHN_PROJECT_DIR}}</string>
    
    <!-- Environment Variables -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>PYTHONPATH</key>
        <string>{{WEBAUTHN_PROJECT_DIR}}</string>
        <key>OLMO_BASE_DIR</key>
        <string>{{OLMO_BASE_DIR}}</string>
        <key>OLMO_MODEL_PATH</key>
        <string>{{OLMO_MODEL_PATH}}</string>
    </dict>
    
    <!-- Execution Settings -->
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    
    <!-- Resource Limits -->
    <key>SoftResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>4096</integer>
    </dict>
    
    <!-- Logging -->
    <key>StandardOutPath</key>
    <string>{{OLMO_BASE_DIR}}/daemon-stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>{{OLMO_BASE_DIR}}/daemon-stderr.log</string>
    
    <!-- Process Settings -->
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>Nice</key>
    <integer>10</integer>
    
    <!-- User Session Awareness -->
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    
    <!-- Throttling -->
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

#### B. Create setup_launchagent.py

```python
#!/usr/bin/env python3
"""
LaunchAgent Setup Script for OLMo Security Daemon
Creates user-specific LaunchAgent plist from template
"""
import os
import sys
from pathlib import Path
import shutil
import subprocess
from config_manager import get_config

def setup_launchagent():
    """Setup LaunchAgent for current user."""
    print("🚀 Setting up OLMo Security LaunchAgent...")
    
    # Load configuration
    config = get_config()
    dirs = config.get_directories()
    daemon_config = config.get_daemon_config()
    github_config = config.get_github_config()
    
    # Template variables
    template_vars = {
        'OLMO_VENV_PYTHON': find_python_executable(),
        'DAEMON_SCRIPT_PATH': find_daemon_script(),
        'GITHUB_REPO': github_config.get('repo', 'hitoshura25/mpo-api-authn-server'),
        'OLMO_BASE_DIR': dirs.get('base_dir'),
        'WEBAUTHN_PROJECT_DIR': find_project_root(),
        'POLL_INTERVAL': str(daemon_config.get('poll_interval', 300)),
        'OLMO_MODEL_PATH': dirs.get('models_dir') + '/OLMo-2-1B-mlx-q4'
    }
    
    # Validate all paths exist or can be created
    if not validate_setup(template_vars):
        return False
    
    # Load template
    template_path = Path(__file__).parent / "templates" / "com.webauthn.security-artifact-daemon.plist.template"
    if not template_path.exists():
        print(f"❌ Template not found: {template_path}")
        return False
    
    # Generate plist content
    with open(template_path, 'r') as f:
        plist_content = f.read()
    
    for key, value in template_vars.items():
        plist_content = plist_content.replace(f"{{{{{key}}}}}", value)
    
    # Write to LaunchAgents directory
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(exist_ok=True)
    
    plist_path = launch_agents_dir / "com.webauthn.security-artifact-daemon.plist"
    
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
        subprocess.run(['launchctl', 'unload', str(plist_path)], 
                      capture_output=True, check=False)  # Ignore errors if not loaded
        subprocess.run(['launchctl', 'load', str(plist_path)], 
                      capture_output=True, check=True)
        print("✅ LaunchAgent loaded successfully")
        
        # Check status
        result = subprocess.run(['launchctl', 'list', 'com.webauthn.security-artifact-daemon'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ LaunchAgent is running")
        else:
            print("⚠️ LaunchAgent may not be running properly")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to load LaunchAgent: {e}")
        return False
    
    print("\n📋 Setup Summary:")
    for key, value in template_vars.items():
        print(f"  {key}: {value}")
    
    return True

def find_python_executable() -> str:
    """Find the best Python executable to use."""
    # Check for virtual environment first
    venv_python = Path(os.getenv('OLMO_VENV_PATH', '~/olmo-security-analysis/venv')).expanduser() / 'bin' / 'python3'
    if venv_python.exists():
        return str(venv_python)
    
    # Fall back to system python
    python_paths = ['/usr/local/bin/python3', '/usr/bin/python3', '/opt/homebrew/bin/python3']
    for path in python_paths:
        if Path(path).exists():
            return path
    
    # Last resort - use which python3
    result = subprocess.run(['which', 'python3'], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    
    raise ValueError("No suitable Python executable found")

def find_daemon_script() -> str:
    """Find the daemon script path."""
    # Look relative to this script
    script_path = Path(__file__).parent.parent / "local-analysis" / "security_artifact_daemon.py"
    if script_path.exists():
        return str(script_path)
    
    # Look in current project
    script_path = Path.cwd() / "local-analysis" / "security_artifact_daemon.py"
    if script_path.exists():
        return str(script_path)
    
    raise ValueError("Daemon script not found")

def find_project_root() -> str:
    """Find the WebAuthn project root directory."""
    # Start from daemon script location
    try:
        daemon_path = Path(find_daemon_script())
        project_root = daemon_path.parent.parent
        return str(project_root)
    except:
        pass
    
    # Fall back to current directory
    return str(Path.cwd())

def validate_setup(template_vars: dict) -> bool:
    """Validate that all required paths and executables exist."""
    print("🔍 Validating setup...")
    
    # Check Python executable
    python_path = Path(template_vars['OLMO_VENV_PYTHON'])
    if not python_path.exists():
        print(f"❌ Python executable not found: {python_path}")
        return False
    print(f"✅ Python executable: {python_path}")
    
    # Check daemon script
    daemon_path = Path(template_vars['DAEMON_SCRIPT_PATH'])
    if not daemon_path.exists():
        print(f"❌ Daemon script not found: {daemon_path}")
        return False
    print(f"✅ Daemon script: {daemon_path}")
    
    # Check/create base directory
    base_dir = Path(template_vars['OLMO_BASE_DIR'])
    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Base directory: {base_dir}")
    
    # Check project directory
    project_dir = Path(template_vars['WEBAUTHN_PROJECT_DIR'])
    if not project_dir.exists():
        print(f"❌ Project directory not found: {project_dir}")
        return False
    print(f"✅ Project directory: {project_dir}")
    
    return True

if __name__ == "__main__":
    success = setup_launchagent()
    exit(0 if success else 1)
```

### 4.2 Cross-Platform Alternatives

#### A. Create setup_daemon.py (Universal)

```python
#!/usr/bin/env python3
"""
Universal Daemon Setup Script
Supports macOS LaunchAgent, Linux systemd, and manual execution
"""
import os
import sys
import platform
from pathlib import Path

def setup_daemon():
    """Setup daemon for current platform."""
    system = platform.system().lower()
    
    if system == "darwin":
        from setup_launchagent import setup_launchagent
        return setup_launchagent()
    elif system == "linux":
        return setup_systemd()
    else:
        print(f"⚠️ Unsupported platform: {system}")
        print("Manual execution instructions:")
        print_manual_instructions()
        return False

def setup_systemd():
    """Setup systemd service for Linux."""
    print("🐧 Setting up systemd service...")
    # Implementation for Linux systemd
    print("⚠️ systemd setup not yet implemented")
    print("Use manual execution for now")
    print_manual_instructions()
    return False

def print_manual_instructions():
    """Print manual execution instructions."""
    print("\n📋 Manual Execution Instructions:")
    print("1. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("")
    print("2. Run daemon manually:")
    print("   python3 local-analysis/security_artifact_daemon.py")
    print("")
    print("3. Or run in background:")
    print("   nohup python3 local-analysis/security_artifact_daemon.py > daemon.log 2>&1 &")
```

### 4.3 Validation Checkpoint

```bash
# Test LaunchAgent setup with clean environment
export OLMO_BASE_DIR="/tmp/test-launchagent"
python3 setup_launchagent.py

# Check if plist was created correctly
ls -la ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist
launchctl list | grep webauthn
```

### 4.4 Rollback Procedure

```bash
# Stop and remove LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist
rm ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist

# Restore original if backup exists  
if [ -f ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist.backup ]; then
    mv ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist.backup \
       ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist
    launchctl load ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist
fi
```

---

## Phase 5: Documentation Updates

### Objective
Remove all hardcoded paths from documentation and create setup guides for new developers.

### 5.1 Update README.md

#### A. Replace Usage Section

**Current Content**:
```bash
source /Users/vinayakmenon/olmo-security-analysis/venv/bin/activate
--model-name "/Users/vinayakmenon/olmo-security-analysis/models/OLMo-2-1B-mlx-q4"
cd /Users/vinayakmenon/mpo-api-authn-server/local-analysis
```

**New Content**:
```bash
# Activate virtual environment (auto-detected or set OLMO_VENV_PATH)
source $(python3 -c "from config_manager import get_config; print(get_config().get_directories()['base_dir'])")/venv/bin/activate

# Run with auto-detected MLX model
python3 process_artifacts.py --local-mode --artifacts-dir "data" --output-dir "data/results"

# Test daemon (detects configuration automatically)
cd local-analysis
python3 security_artifact_daemon.py --test-mode
```

### 5.2 Create Getting Started Guide

#### A. Create docs/GETTING_STARTED.md

```markdown
# Getting Started with OLMo Security Analysis

This guide walks you through setting up the OLMo Security Analysis system on a new machine.

## Prerequisites

- **macOS**: Apple Silicon Mac (M1/M2/M3) for MLX optimization
- **Python**: Python 3.9+ with pip
- **GitHub CLI**: `brew install gh` and `gh auth login`
- **Git**: Access to the WebAuthn repository

## Quick Setup (5 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/hitoshura25/mpo-api-authn-server.git
cd mpo-api-authn-server
```

### 2. Run Auto-Setup
```bash
# This script handles everything: virtual environment, dependencies, models, configuration
python3 scripts/setup_olmo_security.py
```

### 3. Test the System
```bash
# Test local analysis
python3 security-ai-analysis/process_artifacts.py --help

# Test daemon (single cycle)
python3 local-analysis/security_artifact_daemon.py --test-mode
```

### 4. Setup Automatic Daemon (Optional)
```bash
# Setup LaunchAgent for continuous operation
python3 setup_launchagent.py
```

## Manual Setup (Advanced)

If you prefer manual setup or need customization:

### 1. Environment Setup
```bash
# Create virtual environment
python3 -m venv ~/olmo-security-analysis/venv
source ~/olmo-security-analysis/venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install mlx transformers huggingface-hub datasets
```

### 2. Configuration
```bash
# Create custom config (optional)
mkdir -p config
cp templates/olmo-security-config.yaml config/

# Set environment variables (optional)
export OLMO_BASE_DIR="$HOME/olmo-security-analysis"
export GITHUB_REPO="your-org/your-repo"  # If using different repo
```

### 3. Model Setup
```bash
# Models will auto-download on first use, or manually:
python3 model_manager.py
```

## Verification

Verify everything is working:

```bash
# Check configuration
python3 -c "from config_manager import get_config; print(get_config().get_directories())"

# Check model availability  
python3 model_manager.py

# Test full pipeline
python3 security-ai-analysis/process_artifacts.py --local-mode --artifacts-dir test_data
```

## Customization

### Custom Data Directory
```bash
export OLMO_BASE_DIR="/custom/path/olmo-analysis"
```

### Different Repository
```bash
export GITHUB_REPO="your-org/your-security-repo"
```

### Custom Model
```bash
export OLMO_MODEL_PATH="/path/to/your/mlx/model"
```

## Troubleshooting

### Model Download Fails
```bash
# Install HuggingFace Hub
pip install huggingface-hub

# Login to HuggingFace (if needed)
huggingface-cli login
```

### GitHub CLI Issues
```bash
# Re-authenticate
gh auth login --scopes repo,workflow
```

### LaunchAgent Issues
```bash
# Check status
launchctl list | grep webauthn

# View logs
tail -f ~/olmo-security-analysis/daemon-stdout.log
```

## Support

- **Issues**: Open GitHub issue with logs and system info
- **Documentation**: See `docs/improvements/completed/` for detailed implementation docs
- **Configuration**: All settings in `config/olmo-security-config.yaml`
```

### 5.3 Create Auto-Setup Script

#### A. Create scripts/setup_olmo_security.py

```python
#!/usr/bin/env python3
"""
OLMo Security Analysis Auto-Setup Script
Handles complete system setup for new developers
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🚀 OLMo Security Analysis Auto-Setup")
    print("=" * 50)
    
    # Detect environment
    if not is_apple_silicon():
        print("⚠️ This system is optimized for Apple Silicon Macs")
        print("MLX acceleration will not be available")
        if not confirm("Continue anyway?"):
            return 1
    
    # Setup directories
    setup_directories()
    
    # Setup virtual environment
    setup_virtual_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Setup configuration
    setup_configuration()
    
    # Download models (optional, they auto-download later)
    if confirm("Download MLX models now? (1-2GB, optional)"):
        download_models()
    
    # Verify setup
    verify_setup()
    
    print("\n✅ Setup Complete!")
    print("\nNext steps:")
    print("1. Test: python3 local-analysis/security_artifact_daemon.py --test-mode")
    print("2. Setup daemon: python3 setup_launchagent.py")
    print("3. View docs: docs/GETTING_STARTED.md")
    
    return 0

def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon."""
    try:
        result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
        return result.stdout.strip() == 'arm64'
    except:
        return False

def setup_directories():
    """Create required directories."""
    print("\n📁 Setting up directories...")
    
    base_dir = Path.home() / "olmo-security-analysis"
    directories = [
        base_dir,
        base_dir / "data",
        base_dir / "models", 
        base_dir / "analysis",
        base_dir / "artifacts"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")

def setup_virtual_environment():
    """Setup Python virtual environment."""
    print("\n🐍 Setting up virtual environment...")
    
    venv_path = Path.home() / "olmo-security-analysis" / "venv"
    
    if venv_path.exists():
        print(f"  ✅ Virtual environment already exists: {venv_path}")
        return
    
    try:
        subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], check=True)
        print(f"  ✅ Created virtual environment: {venv_path}")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to create virtual environment: {e}")
        raise

def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing dependencies...")
    
    venv_python = Path.home() / "olmo-security-analysis" / "venv" / "bin" / "python3"
    
    dependencies = [
        "mlx",
        "transformers",
        "huggingface-hub",
        "datasets",
        "pyyaml",
        "requests"
    ]
    
    # Install from requirements.txt if it exists
    requirements_file = Path.cwd() / "requirements.txt"
    if requirements_file.exists():
        try:
            subprocess.run([str(venv_python), '-m', 'pip', 'install', '-r', str(requirements_file)], check=True)
            print("  ✅ Installed from requirements.txt")
        except subprocess.CalledProcessError:
            print("  ⚠️ Failed to install from requirements.txt, installing individually")
    
    # Install additional MLX dependencies
    for dep in dependencies:
        try:
            subprocess.run([str(venv_python), '-m', 'pip', 'install', dep], check=True)
            print(f"  ✅ {dep}")
        except subprocess.CalledProcessError:
            print(f"  ⚠️ Failed to install {dep}")

def setup_configuration():
    """Setup configuration files."""
    print("\n⚙️ Setting up configuration...")
    
    config_dir = Path.cwd() / "config"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "olmo-security-config.yaml"
    if not config_file.exists():
        # Copy from template if it exists
        template_file = Path.cwd() / "templates" / "olmo-security-config.yaml"
        if template_file.exists():
            shutil.copy2(template_file, config_file)
            print(f"  ✅ Created config from template: {config_file}")
        else:
            # Create basic config
            basic_config = """# OLMo Security Analysis Configuration
directories:
  base_dir: "~/olmo-security-analysis"
  data_dir: "${base_dir}/data"
  models_dir: "${base_dir}/models"
  analysis_dir: "${base_dir}/analysis"

model:
  preferred_name: "OLMo-2-1B-mlx-q4"
  auto_download: true

github:
  repo: "hitoshura25/mpo-api-authn-server"
  workflow: "main-ci-cd.yml"
  branch: "main"

daemon:
  poll_interval: 300
  log_level: "INFO"
"""
            with open(config_file, 'w') as f:
                f.write(basic_config)
            print(f"  ✅ Created basic config: {config_file}")
    else:
        print(f"  ✅ Config already exists: {config_file}")

def download_models():
    """Download MLX models."""
    print("\n🤖 Downloading MLX models...")
    
    venv_python = Path.home() / "olmo-security-analysis" / "venv" / "bin" / "python3"
    model_script = Path.cwd() / "model_manager.py"
    
    if model_script.exists():
        try:
            subprocess.run([str(venv_python), str(model_script)], check=True)
            print("  ✅ Models downloaded successfully")
        except subprocess.CalledProcessError:
            print("  ⚠️ Model download failed (they will auto-download when needed)")
    else:
        print("  ⚠️ Model manager not found, models will auto-download when needed")

def verify_setup():
    """Verify the setup works."""
    print("\n🔍 Verifying setup...")
    
    venv_python = Path.home() / "olmo-security-analysis" / "venv" / "bin" / "python3"
    
    # Test imports
    test_script = """
try:
    import mlx
    print("✅ MLX import successful")
except ImportError:
    print("⚠️ MLX import failed")

try:
    import transformers
    print("✅ Transformers import successful")
except ImportError:
    print("⚠️ Transformers import failed")

try:
    from config_manager import get_config
    config = get_config()
    print(f"✅ Configuration loaded: {config.get_directories()['base_dir']}")
except Exception as e:
    print(f"⚠️ Configuration load failed: {e}")
"""
    
    try:
        result = subprocess.run([str(venv_python), '-c', test_script], 
                              capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("  ⚠️ Verification failed:")
        print(e.stderr)

def confirm(message: str) -> bool:
    """Ask for user confirmation."""
    response = input(f"{message} [Y/n]: ").strip().lower()
    return response in ('', 'y', 'yes')

if __name__ == "__main__":
    exit(main())
```

### 5.4 Validation Checkpoint

```bash
# Test getting started guide with fresh environment
rm -rf /tmp/test-getting-started
export HOME="/tmp/test-getting-started"

# Run auto-setup
python3 scripts/setup_olmo_security.py

# Verify documentation is accurate
cat docs/GETTING_STARTED.md
```

### 5.5 Rollback Procedure

1. Revert README.md changes: `git checkout -- security-ai-analysis/README.md`
2. Remove new documentation: `rm -rf docs/GETTING_STARTED.md scripts/setup_olmo_security.py`
3. Verify original documentation still works

---

## Phase 6: Testing & Validation

### Objective
Comprehensive testing to ensure portability while preserving current functionality.

### 6.1 Test Environments

#### A. Clean macOS System Test

```bash
#!/bin/bash
# test_clean_macos.sh - Simulate fresh macOS setup

# Create isolated test environment
export TEST_HOME="/tmp/olmo-portability-test"
export HOME="$TEST_HOME"
export OLMO_BASE_DIR="$TEST_HOME/olmo-security-analysis"

mkdir -p "$TEST_HOME"
cd "$TEST_HOME"

# Clone repository
git clone https://github.com/hitoshura25/mpo-api-authn-server.git
cd mpo-api-authn-server

# Test auto-setup
echo "🧪 Testing auto-setup..."
python3 scripts/setup_olmo_security.py

# Test configuration loading
echo "🧪 Testing configuration..."
python3 -c "from config_manager import get_config; print('Config loaded:', get_config().get_directories())"

# Test model detection
echo "🧪 Testing model detection..."
python3 model_manager.py

# Test daemon
echo "🧪 Testing daemon..."
python3 local-analysis/security_artifact_daemon.py --test-mode

# Test LaunchAgent setup
echo "🧪 Testing LaunchAgent setup..."
python3 setup_launchagent.py

echo "✅ Clean macOS test complete"
```

#### B. Different User Test

```bash
#!/bin/bash
# test_different_user.sh - Test with different username/paths

# Create test user environment
export TEST_USER="testuser"
export HOME="/Users/$TEST_USER"
export OLMO_BASE_DIR="$HOME/custom-olmo-path"
export GITHUB_REPO="different-org/different-repo"

# Test all components work with custom paths
echo "🧪 Testing with custom paths..."
echo "  Home: $HOME"
echo "  Base: $OLMO_BASE_DIR" 
echo "  Repo: $GITHUB_REPO"

# Run test suite
python3 scripts/setup_olmo_security.py
python3 -c "from config_manager import get_config; print(get_config().get('github.repo'))"
```

### 6.2 Regression Testing

#### A. Current Functionality Test

```bash
#!/bin/bash
# test_current_functionality.sh - Ensure existing system still works

echo "🔙 Testing existing functionality..."

# Test with original hardcoded paths (should still work due to fallbacks)
export OLMO_BASE_DIR=""  # Clear environment variables
export OLMO_MODEL_PATH=""

# Test original commands
cd /Users/vinayakmenon/mpo-api-authn-server
python3 security-ai-analysis/process_artifacts.py --help

# Test daemon with original paths
python3 local-analysis/security_artifact_daemon.py --test-mode

# Test LaunchAgent still works
launchctl list | grep webauthn

echo "✅ Current functionality preserved"
```

#### B. Performance Regression Test

```python
#!/usr/bin/env python3
# test_performance.py - Ensure MLX performance is preserved

import time
import tempfile
from pathlib import Path

def test_mlx_performance():
    """Test that MLX optimization is still working."""
    print("⚡ Testing MLX performance...")
    
    # Create minimal test vulnerability
    test_vuln = {
        'id': 'test-vuln-1',
        'title': 'Test Vulnerability',
        'description': 'Test description for performance testing',
        'severity': 'HIGH'
    }
    
    # Initialize analyzer
    from analysis.olmo_analyzer import OLMoSecurityAnalyzer
    analyzer = OLMoSecurityAnalyzer()
    
    # Time single analysis
    start_time = time.time()
    result = analyzer.analyze_vulnerability(test_vuln)
    duration = time.time() - start_time
    
    print(f"  Analysis time: {duration:.2f} seconds")
    
    # MLX should be under 2 seconds for single analysis
    if duration < 2.0:
        print("  ✅ MLX performance maintained")
        return True
    else:
        print("  ⚠️ Performance may be degraded")
        return False

if __name__ == "__main__":
    success = test_mlx_performance()
    exit(0 if success else 1)
```

### 6.3 Integration Testing

#### A. End-to-End Pipeline Test

```python
#!/usr/bin/env python3
# test_end_to_end.py - Test complete pipeline works

import tempfile
import json
from pathlib import Path

def test_complete_pipeline():
    """Test the complete 4-phase pipeline."""
    print("🔄 Testing complete pipeline...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test security data
        test_data_dir = temp_path / "test_artifacts"
        test_data_dir.mkdir()
        
        # Create sample Trivy scan result
        trivy_data = {
            "Results": [{
                "Target": "test-target",
                "Vulnerabilities": [{
                    "VulnerabilityID": "CVE-2023-TEST",
                    "PkgName": "test-package",
                    "Severity": "HIGH",
                    "Title": "Test Vulnerability",
                    "Description": "Test vulnerability for pipeline testing"
                }]
            }]
        }
        
        with open(test_data_dir / "trivy-results.json", 'w') as f:
            json.dump(trivy_data, f)
        
        # Test pipeline
        import subprocess
        result = subprocess.run([
            'python3', 'security-ai-analysis/process_artifacts.py',
            '--local-mode',
            '--artifacts-dir', str(test_data_dir),
            '--output-dir', str(temp_path / "output")
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("  ✅ Pipeline completed successfully")
            
            # Check output files exist
            output_dir = temp_path / "output"
            if any(output_dir.glob("olmo_analysis_results_*.json")):
                print("  ✅ Analysis results generated")
            if any(output_dir.glob("narrativized_dataset_*.json")):
                print("  ✅ Narrativized dataset generated")
            if any(output_dir.glob("train_*.jsonl")):
                print("  ✅ Training dataset generated")
                
            return True
        else:
            print(f"  ❌ Pipeline failed: {result.stderr}")
            return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    exit(0 if success else 1)
```

### 6.4 Validation Checklist

#### A. Pre-Implementation Checklist
- [ ] Current system status documented
- [ ] All hardcoded paths identified
- [ ] Backup of working configuration created
- [ ] Test environment prepared

#### B. Phase Completion Checklist
- [ ] **Phase 1**: Environment variables work, fallbacks preserved
- [ ] **Phase 2**: Model auto-detection works, download functionality tested
- [ ] **Phase 3**: Configuration file loads, environment overrides work
- [ ] **Phase 4**: LaunchAgent template generates correctly
- [ ] **Phase 5**: Documentation updated, auto-setup script works
- [ ] **Phase 6**: All tests pass, performance maintained

#### C. Final Validation Checklist
- [ ] Clean macOS setup works from scratch
- [ ] Current production system unaffected
- [ ] Different user/path configurations work  
- [ ] MLX performance maintained (214+ tokens/sec)
- [ ] All 4 pipeline phases complete successfully
- [ ] HuggingFace dataset upload still works
- [ ] LaunchAgent daemon runs correctly
- [ ] Documentation accurate and complete

### 6.5 Rollback Procedures

#### A. Quick Rollback (Single Phase)
```bash
# Identify failed phase
echo "Rolling back Phase X changes..."

# Revert specific files
git checkout HEAD -- [modified-files-from-phase]

# Restore backups if needed
if [ -f "backup_file" ]; then
    mv backup_file original_file
fi

# Test original functionality
python3 local-analysis/security_artifact_daemon.py --test-mode
```

#### B. Complete Rollback (All Changes)
```bash
# Nuclear option - revert all portability changes
git stash  # Save any uncommitted work
git reset --hard HEAD  # Reset to before portability implementation

# Restore original LaunchAgent if needed
if [ -f ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist.backup ]; then
    mv ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist.backup \
       ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist
    launchctl unload ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist
    launchctl load ~/Library/LaunchAgents/com.webauthn.security-artifact-daemon.plist
fi

# Verify original system works
launchctl list | grep webauthn
```

#### C. Selective Rollback (Preserve Some Changes)
```bash
# Keep beneficial changes but revert problematic ones
git reset HEAD~N  # Go back N commits
git add -p  # Selectively stage changes to keep
git commit -m "Selective rollback: keep working features"
```

---

## Risk Mitigation

### High-Risk Areas
1. **MLX Model Integration**: Changes to model loading could break 20-30X performance
2. **LaunchAgent Configuration**: Incorrect plist could prevent daemon startup
3. **Environment Variable Resolution**: Could cause scripts to fail silently
4. **Configuration File Parsing**: YAML errors could break initialization

### Mitigation Strategies
1. **Incremental Implementation**: Each phase independently testable
2. **Backward Compatibility**: All changes include fallbacks to current behavior
3. **Comprehensive Testing**: Multiple test environments and scenarios
4. **Quick Rollback**: Clear rollback procedures for each phase
5. **Validation Checkpoints**: Verify functionality after each change

### Success Criteria
- [ ] **Zero Disruption**: Current working system unaffected during implementation
- [ ] **Performance Maintained**: MLX optimization speed preserved
- [ ] **Feature Complete**: All 4 pipeline phases work in portable system
- [ ] **Documentation Accurate**: New developers can set up system successfully
- [ ] **Cross-Session Continuity**: Any Claude session can follow this plan

---

## Conclusion

This implementation plan provides a systematic approach to making the AI Security Dataset Research Initiative portable while preserving the fully functional production system. The phase-based approach with validation checkpoints ensures safe implementation across multiple Claude sessions.

**Key Benefits**:
- **Preserves Working System**: Current production functionality untouched
- **Enables Portability**: Works on any macOS system with minimal setup
- **Maintains Performance**: MLX optimization preserved
- **Cross-Session Safe**: Each phase can be implemented independently
- **Comprehensive Testing**: Multiple validation strategies ensure reliability

**Next Steps**:
1. Begin with Phase 1 (Environment Variables) as it has lowest risk
2. Validate each phase thoroughly before proceeding
3. Create automated test suite for regression testing
4. Document any discovered edge cases for future sessions

The system will remain fully functional throughout implementation, with the ability to rollback at any point if issues arise.