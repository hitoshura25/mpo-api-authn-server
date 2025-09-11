# AI Security Portability Implementation Plan - V2

## Executive Summary

This document provides a comprehensive, test-driven implementation plan to make the AI Security Dataset Research Initiative portable across different development environments. The plan addresses key architectural decisions around model sharing, fine-tuning capabilities, and workflow simplification while maintaining the current working system's 20-30X MLX performance improvement.

## Current System Analysis (Pre-Portability)

### ✅ Working Components
- **Complete 4-phase pipeline**: Analysis → Narrativization → Fine-tuning dataset → HuggingFace Upload  
- **Production dataset**: Live at `hitoshura25/webauthn-security-vulnerabilities-olmo`
- **MLX optimization**: 214.6 tokens/sec on Apple Silicon (20-30X improvement)
- **Local automation**: LaunchAgent daemon polling GitHub every 5 minutes

### 🚨 Hardcoded Dependencies Found
**Analysis completed**: 8 files with hardcoded `/Users/vinayakmenon/olmo-security-analysis` or `~/olmo-security-analysis` paths:

1. **security-ai-analysis/process_artifacts.py:791** - Default model path argument
2. **security-ai-analysis/analysis/olmo_analyzer.py:22** - Constructor default parameter  
3. **security-ai-analysis/README.md** - Documentation examples (3 locations)
4. **local-analysis/security_artifact_daemon.py** - Log file (line 46), data_dir default (line 65), model path (line 284), argument default (line 460)
5. **local-analysis/huggingface_uploader.py** - Documentation examples (3 locations)
6. **local-analysis/olmo2_mlx_setup.py** - Constructor default (line 37), argument default (line 229)

## Architectural Decision: Hybrid Approach

### Key Insights
1. **Models ARE shareable**: Base OLMo models (1.2-2.1GB) can be reused across projects
2. **Fine-tuning planned**: Missing `mlx_finetuning.py` component would create project-specific models worth sharing
3. **Virtual environments NOT shareable**: Project-specific dependencies 
4. **Workflow complexity**: External venv + project directory is confusing
5. **Data/Results separation critical**: Project-specific intermediate processing vs valuable reusable artifacts

### Chosen Architecture: **Shared Models with Direct Path Configuration**

```
~/shared-olmo-models/           # External (shareable across projects)
├── base/
│   ├── OLMo-2-1B-mlx-q4/      # 1.2GB base model
│   └── OLMo-2-1B-mlx/         # 2.1GB base model  
└── fine-tuned/                # Future: project-specific fine-tuned models
    └── webauthn-security-v1/   # This project's fine-tuned model

security-ai-analysis/          # In-project (self-contained system)
├── scripts/                   # Setup and testing scripts (self-contained)
│   ├── setup.py              # Main setup script
│   └── tests/                # Validation test scripts
│       ├── test-phase1.sh    # Configuration system validation
│       ├── test-phase2.sh    # Model management validation  
│       ├── test-phase3.sh    # Daemon/LaunchAgent validation
│       ├── test-integration.sh # End-to-end integration test
│       └── test-config-variations.sh # Config variation testing (prevents masking)
├── venv/                      # Project-specific virtual environment (.gitignored)
├── data/                      # Project-specific analysis data (.gitignored) 
├── results/                   # Project-specific results (.gitignored)
└── [source files]            # Tracked in git (config_manager.py, etc.)

# Configuration only for external directories
config/olmo-security-config.yaml:
  base_models_dir: "~/shared-olmo-models/base"
  fine_tuned_models_dir: "~/shared-olmo-models/fine-tuned"
  # Project directories (data/, results/, venv/) are fixed
```

**Benefits**: 
- **Models shared across projects** (supports OLMo's open mission)  
- **Direct path references** (no symlink complexity or cross-platform issues)
- **Explicit configuration** (all paths visible in YAML config)
- **Simple workflow** (activate venv in project, run scripts)
- **Supports future fine-tuning** with configurable fine-tuned model directory
- **Standard .gitignore approach** (like node_modules/, build/)
- **Cross-platform compatibility** (no symlink dependencies)
- **Optimal sharing separation** (valuable artifacts shared, temporary processing local)
- **Self-contained system** (all AI security scripts and tests in one directory for portability)

### Sharing Philosophy Analysis

**🎯 What Gets Shared (High-Value, Reusable)**:
- **Base Models**: `~/shared-olmo-models/base/` - OLMo-2-1B variants reused across projects
- **Fine-tuned Models**: `~/shared-olmo-models/fine-tuned/` - Project-specific models (future: webauthn-security-v1)
- **Training Datasets**: Published to HuggingFace (`hitoshura25/webauthn-security-vulnerabilities-olmo`)
- **Source Code**: All processing scripts in git (fully shareable)

**🏠 What Stays Local (Project-Specific, Temporary)**:
- **Raw Security Artifacts** (`data/`): Downloaded GitHub Actions artifacts (JSON/SARIF), project-specific
- **Intermediate Processing** (`results/`): Analysis outputs before final dataset creation, work-in-progress
- **Virtual Environment** (`venv/`): Project-specific dependencies, not reusable
- **Development Artifacts**: Logs, debugging outputs, partial results

**✅ Alignment with OLMo's Open Mission**:
- **High-value outputs** (models, datasets) are shared externally and published
- **Temporary processing files** remain local to avoid cluttering shared spaces
- **Each project has different security contexts** (WebAuthn vs other domains)
- **Final datasets already shared** via HuggingFace for community benefit
- **Separation optimizes for what matters**: Reusable artifacts vs temporary processing

**🤝 Decision Rationale**: This approach correctly separates temporary project processing (local) from valuable reusable artifacts (shared), maximizing sharing benefits while maintaining clean development workflow.

## Test-Driven Implementation Plan

### Phase 1: Create Portable Configuration System (4-6 hours)

**Objective**: Replace all hardcoded paths with configuration-driven approach

#### 1.1 Create Enhanced Configuration Manager
**File**: `security-ai-analysis/config_manager.py`
```python
class OLMoSecurityConfig:
    def __init__(self, config_file: Optional[Path] = None):
        # Load configuration from YAML file
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "olmo-security-config.yaml"
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Configure model directories (external, shareable)
        self.base_models_dir = Path(config['base_models_dir']).expanduser()
        self.fine_tuned_models_dir = Path(config['fine_tuned_models_dir']).expanduser()
        
        # Configure project directories (fixed within project structure)
        project_root = Path(__file__).parent.parent
        self.venv_dir = project_root / "security-ai-analysis" / "venv"
        self.data_dir = project_root / "security-ai-analysis" / "data"
        self.results_dir = project_root / "security-ai-analysis" / "results"
        
        # Model configuration
        self.default_base_model = config.get('default_base_model', 'OLMo-2-1B-mlx-q4')
        
    def get_base_model_path(self, model_name: Optional[str] = None) -> Path:
        """Get path to base model (pre-trained, shareable across projects)"""
        model_name = model_name or self.default_base_model
        model_path = self.base_models_dir / model_name
        
        if not model_path.exists():
            raise FileNotFoundError(f"Base model {model_name} not found at {model_path}")
        return model_path
    
    def get_fine_tuned_model_path(self, model_name: str) -> Path:
        """Get path to fine-tuned model (project-specific, shareable results)"""
        model_path = self.fine_tuned_models_dir / model_name
        
        if not model_path.exists():
            raise FileNotFoundError(f"Fine-tuned model {model_name} not found at {model_path}")
        return model_path
```

#### 1.2 Simplified YAML Configuration
**File**: `config/olmo-security-config.yaml`
```yaml
# External directories (shareable across projects)
base_models_dir: "~/shared-olmo-models/base"
fine_tuned_models_dir: "~/shared-olmo-models/fine-tuned"

# Model configuration
default_base_model: "OLMo-2-1B-mlx-q4"

# Environment variable overrides (for testing/CI)
# OLMO_BASE_MODELS_DIR: override base_models_dir
# OLMO_FINE_TUNED_MODELS_DIR: override fine_tuned_models_dir
# OLMO_DEFAULT_BASE_MODEL: override default_base_model
```

**Note**: Project directories (`data/`, `results/`, `venv/`) are fixed within `security-ai-analysis/` and synchronized with `.gitignore`. Only external model directories are configurable.

#### 1.3 Test-Driven Validation
**Test Script**: `security-ai-analysis/scripts/tests/test-phase1.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Phase 1 Validation Tests"

# Test 1: Config manager loads without errors
python3 -c "from security-ai-analysis.config_manager import OLMoSecurityConfig; config = OLMoSecurityConfig(); print('✅ Config loads')"

# Test 2: Model path detection works
python3 -c "
from security-ai-analysis.config_manager import OLMoSecurityConfig
config = OLMoSecurityConfig()
try:
    path = config.get_base_model_path('OLMo-2-1B-mlx-q4')
    print(f'✅ Model found at: {path}')
except FileNotFoundError as e:
    print(f'⚠️  Model not found (expected for fresh setup): {e}')
"

# Test 3: No hardcoded paths remain in updated files  
if grep -r "olmo-security-analysis" security-ai-analysis/analysis/olmo_analyzer.py; then
    echo "❌ Hardcoded paths still exist"
    exit 1
else
    echo "✅ No hardcoded paths found"
fi

echo "✅ Phase 1 validation complete"
```

#### 1.4 Implementation Steps
1. Create `config_manager.py`
2. Update `analysis/olmo_analyzer.py` to use config
3. Update `process_artifacts.py` to use config  
4. Run validation tests
5. **Checkpoint**: All tests pass before proceeding

### Phase 2: Model Management & Setup Automation (3-4 hours)

**Objective**: Automated model download and project setup

#### 2.1 Enhanced Model Manager
**File**: `security-ai-analysis/model_manager.py`
```python
class OLMoModelManager:
    def __init__(self):
        self.config = OLMoSecurityConfig()
        
    def setup_project_structure(self):
        """Create project directories and shared model directories"""
        # Create project directories  
        for directory in [self.config.venv_dir, self.config.data_dir, self.config.results_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Create shared model directories (external, shareable)
        self.config.base_models_dir.mkdir(parents=True, exist_ok=True)
        self.config.fine_tuned_models_dir.mkdir(parents=True, exist_ok=True)
            
    def ensure_base_model_available(self, model_name: Optional[str] = None) -> Path:
        """Download base model if not available, return path"""
        model_name = model_name or self.config.default_base_model
        model_path = self.config.base_models_dir / model_name
        
        if model_path.exists():
            return model_path
            
        # Implementation for MLX model download/conversion would go here
        raise FileNotFoundError(f"Model {model_name} not found and download not implemented yet")
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models"""
        return {
            'base_models_dir': str(self.config.base_models_dir),
            'fine_tuned_models_dir': str(self.config.fine_tuned_models_dir),
            'default_base_model': self.config.default_base_model,
            'available_base_models': [p.name for p in self.config.base_models_dir.iterdir() if p.is_dir()] if self.config.base_models_dir.exists() else [],
            'available_fine_tuned_models': [p.name for p in self.config.fine_tuned_models_dir.iterdir() if p.is_dir()] if self.config.fine_tuned_models_dir.exists() else []
        }
```

#### 2.2 Project Setup Script  
**File**: `security-ai-analysis/scripts/setup.py`
```python
#!/usr/bin/env python3
"""
AI Security Analysis Setup Script
Creates portable project structure with shared model support
"""

def main():
    print("🚀 Setting up AI Security Analysis System")
    
    # 1. Create project structure
    manager = OLMoModelManager()
    manager.setup_project_structure()
    
    # 2. Create virtual environment in project
    venv_path = Path(__file__).parent.parent / "security-ai-analysis" / "venv"
    if not venv_path.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        
    # 3. Install dependencies
    pip_path = venv_path / "bin" / "pip"
    req_path = Path(__file__).parent.parent / "security-ai-analysis" / "requirements.txt"
    subprocess.run([str(pip_path), "install", "-r", str(req_path)], check=True)
    
    # 4. Check model availability and show information
    model_info = manager.get_model_info()
    print(f"📁 Base models directory: {model_info['base_models_dir']}")
    print(f"📁 Fine-tuned models directory: {model_info['fine_tuned_models_dir']}")
    print(f"📁 Available base models: {model_info['available_base_models']}")
    
    try:
        model_path = manager.ensure_base_model_available()
        print(f"✅ Default model available: {model_path}")
    except FileNotFoundError as e:
        print(f"⚠️  Default model not found (will need manual download): {e}")
    
    print("✅ Setup complete!")
    print(f"🐍 Virtual env: security-ai-analysis/venv/")
    print(f"📊 Data: security-ai-analysis/data/")
    print(f"📊 Results: security-ai-analysis/results/")
    print(f"📁 Shared models: ~/shared-olmo-models/")
```

#### 2.3 Validation Tests
**Test Script**: `security-ai-analysis/scripts/tests/test-phase2.sh`
```bash
#!/bin/bash
echo "🧪 Phase 2 Validation Tests"

# Test 1: Setup script works
python3 security-ai-analysis/scripts/setup.py

# Test 2: Project structure created
test -d security-ai-analysis/venv && echo "✅ Virtual env created"
test -d ~/shared-olmo-models/base && echo "✅ Base models directory created"
test -d ~/shared-olmo-models/fine-tuned && echo "✅ Fine-tuned models directory created"
test -d security-ai-analysis/data && echo "✅ Data directory created"
test -d security-ai-analysis/results && echo "✅ Results directory created"

# Test 3: Virtual environment works
source security-ai-analysis/venv/bin/activate
python3 -c "import transformers; print('✅ Dependencies installed')"

# Test 4: Updated scripts work with new paths
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis
python3 process_artifacts.py --help | grep -q "OLMo" && echo "✅ Process script works"

echo "✅ Phase 2 validation complete"
```

### Phase 3: LaunchAgent & Daemon Portability (2-3 hours)

**Objective**: Update LaunchAgent and daemon to work with new structure

#### 3.1 Portable Daemon Updates
**File**: `local-analysis/security_artifact_daemon.py` updates:
```python
def __init__(self, repo: str = "hitoshura25/mpo-api-authn-server"):
    # Use project-based paths
    project_root = Path(__file__).parent.parent
    self.config = OLMoSecurityConfig()
    
    self.data_dir = self.config.data_dir
    self.analysis_dir = self.config.results_dir
    
    # Log to project location
    log_file = self.config.results_dir / "daemon.log"
```

#### 3.2 LaunchAgent Template
**File**: `security-ai-analysis/templates/daemon.plist.template`
```xml
<dict>
    <key>ProgramArguments</key>
    <array>
        <string>{{PROJECT_ROOT}}/security-ai-analysis/venv/bin/python3</string>
        <string>{{PROJECT_ROOT}}/local-analysis/security_artifact_daemon.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{{PROJECT_ROOT}}</string>
</dict>
```

#### 3.3 Validation Tests
**Test Script**: `security-ai-analysis/scripts/tests/test-phase3.sh`
```bash
#!/bin/bash
echo "🧪 Phase 3 Validation Tests"

# Test 1: Daemon uses project paths
source security-ai-analysis/venv/bin/activate
python3 local-analysis/security_artifact_daemon.py --test-mode --data-dir security-ai-analysis/data

# Test 2: LaunchAgent template generation
python3 -c "
import os
from pathlib import Path
template_path = Path('security-ai-analysis/templates/daemon.plist.template')
content = template_path.read_text()
project_root = Path.cwd()
result = content.replace('{{PROJECT_ROOT}}', str(project_root))
print('✅ Template generation works')
print(f'Python path: {project_root}/security-ai-analysis/venv/bin/python3')
"

echo "✅ Phase 3 validation complete"
```

### Phase 4: Documentation & .gitignore Updates (1-2 hours)

**Objective**: Update all documentation and add proper .gitignore

#### 4.1 .gitignore Updates
**File**: `security-ai-analysis/.gitignore`
```
# Virtual environment (project-specific dependencies)
venv/

# Data and results (project-specific intermediate processing)
# These contain temporary artifacts, not valuable shareable outputs
data/          # Raw security artifacts (JSON/SARIF from GitHub Actions)
results/       # Intermediate analysis before final dataset creation

# Python cache
__pycache__/
*.pyc
*.pyo
```

#### 4.2 Documentation Updates
**Files to update**:
- `security-ai-analysis/README.md`
- `security-ai-analysis/docs/GETTING_STARTED.md` (create)
- `local-analysis/README.md`

#### 4.3 Getting Started Guide
**File**: `security-ai-analysis/docs/GETTING_STARTED.md`
```markdown
# Getting Started

## Quick Setup (2 minutes)

1. Clone repository:
```bash
git clone https://github.com/hitoshura25/mpo-api-authn-server.git
cd mpo-api-authn-server
```

2. Run setup:
```bash
python3 security-ai-analysis/scripts/setup.py
```

3. Activate and test:
```bash
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis  
python3 process_artifacts.py --help
```

## Architecture

- **Models**: Shared at `~/shared-olmo-models/` (reusable across projects)
- **Virtual Environment**: `security-ai-analysis/venv/` (project-specific)
- **Data**: `security-ai-analysis/data/` (project-specific, .gitignored)
```

### Phase 5: Configuration Validation & Integration Testing (3-4 hours)

**Objective**: Comprehensive testing with fresh environment simulation + config variation testing to prevent masking issues

#### 5.1 Complete Integration Test
**Test Script**: `security-ai-analysis/scripts/tests/test-integration.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Complete Integration Test"

# Simulate fresh environment
export TEST_HOME="/tmp/ai-security-test-$(date +%s)"
mkdir -p "$TEST_HOME"
cd "$TEST_HOME"

# Test complete workflow
git clone https://github.com/hitoshura25/mpo-api-authn-server.git
cd mpo-api-authn-server

# Test setup
python3 security-ai-analysis/scripts/setup.py

# Test analysis workflow  
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

# Create test data
mkdir -p test_data
echo '{"test": "sample vulnerability"}' > test_data/sample.json

# Test analysis
python3 process_artifacts.py --local-mode --artifacts-dir test_data

# Test daemon
cd ../local-analysis
python3 security_artifact_daemon.py --test-mode

echo "✅ Complete integration test passed"

# Cleanup
cd /
rm -rf "$TEST_HOME"
```

#### 5.2 Configuration Variation Testing (CRITICAL)
**Test Script**: `security-ai-analysis/scripts/tests/test-config-variations.sh`
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Configuration Variation Testing (Prevents Masking Issues)"
echo "This test validates that config changes are actually honored"

# Create test environment
TEST_DIR="/tmp/config-validation-test-$(date +%s)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Clone repository
git clone https://github.com/hitoshura25/mpo-api-authn-server.git
cd mpo-api-authn-server

# Test 1: Validate default config loads
echo "📋 Test 1: Default config validation"
python3 -c "
from security_ai_analysis.config_manager import OLMoSecurityConfig
config = OLMoSecurityConfig()
print(f'Base models dir: {config.base_models_dir}')
print(f'Fine-tuned models dir: {config.fine_tuned_models_dir}')
print('✅ Default config loads successfully')
"

# Test 2: Create alternative config with different paths
echo "📋 Test 2: Alternative config with different paths"
ALT_CONFIG="config/test-olmo-security-config.yaml"
cat > "$ALT_CONFIG" << EOF
# Alternative configuration for testing
base_models_dir: "/tmp/test-base-models-$(date +%s)"
fine_tuned_models_dir: "/tmp/test-fine-tuned-$(date +%s)"
default_base_model: "test-model-variant"
EOF

echo "Created alternative config:"
cat "$ALT_CONFIG"

# Test 3: Validate alternative config is honored
echo "📋 Test 3: Validate alternative config paths are used"
python3 -c "
import sys
from pathlib import Path
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig

# Load alternative config
alt_config_path = Path('$ALT_CONFIG')
config = OLMoSecurityConfig(config_file=alt_config_path)

print(f'Alternative base models dir: {config.base_models_dir}')
print(f'Alternative fine-tuned models dir: {config.fine_tuned_models_dir}')
print(f'Alternative default model: {config.default_base_model}')

# Validate paths are different from defaults
if '/tmp/test-base-models-' not in str(config.base_models_dir):
    raise AssertionError('Alternative config not loaded - base_models_dir unchanged')
if '/tmp/test-fine-tuned-' not in str(config.fine_tuned_models_dir):
    raise AssertionError('Alternative config not loaded - fine_tuned_models_dir unchanged')
if config.default_base_model != 'test-model-variant':
    raise AssertionError('Alternative config not loaded - default_base_model unchanged')

print('✅ Alternative configuration properly loaded and honored')
"

# Test 4: Environment variable override testing
echo "📋 Test 4: Environment variable override testing"
export OLMO_BASE_MODELS_DIR="/tmp/env-override-base-$(date +%s)"
export OLMO_DEFAULT_BASE_MODEL="env-override-model"

python3 -c "
import os
import sys
from pathlib import Path
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig

# Load config with environment overrides
config = OLMoSecurityConfig()

expected_base = os.environ.get('OLMO_BASE_MODELS_DIR')
expected_model = os.environ.get('OLMO_DEFAULT_BASE_MODEL')

print(f'Environment base dir: {expected_base}')
print(f'Config base dir: {config.base_models_dir}')
print(f'Environment model: {expected_model}')
print(f'Config model: {config.default_base_model}')

if expected_base not in str(config.base_models_dir):
    raise AssertionError('Environment variable override not working for base_models_dir')
if config.default_base_model != expected_model:
    raise AssertionError('Environment variable override not working for default_base_model')

print('✅ Environment variable overrides working correctly')
"

# Test 5: Validate hardcoded path elimination
echo "📋 Test 5: Validate no hardcoded paths remain in codebase"
HARDCODED_PATTERNS=(
    "olmo-security-analysis"
    "/Users/vinayakmenon/olmo-security-analysis"
    "~/olmo-security-analysis"
)

for pattern in "${HARDCODED_PATTERNS[@]}"; do
    echo "Checking for hardcoded pattern: $pattern"
    if find security-ai-analysis local-analysis -name "*.py" -exec grep -l "$pattern" {} \; | grep -v __pycache__ | head -1; then
        echo "❌ FAILURE: Hardcoded path '$pattern' still exists in codebase"
        exit 1
    else
        echo "✅ No hardcoded paths found for: $pattern"
    fi
done

echo "✅ All configuration variation tests passed"
echo "✅ Configuration changes are properly honored"
echo "✅ No hardcoded paths remain in codebase"

# Cleanup
cd /
rm -rf "$TEST_DIR"
echo "✅ Configuration validation complete"
```

## Risk Mitigation & Rollback Plan

### Low-Risk Approach
- **Incremental phases**: Each phase independently testable
- **Backward compatibility**: Existing hardcoded paths still work during transition
- **Git branching**: All changes on feature branch until complete

### Rollback Procedures
```bash
# Phase-level rollback
git checkout main -- security-ai-analysis/analysis/olmo_analyzer.py

# Complete rollback
git reset --hard main
git clean -fd
```

## Success Criteria

### Must Pass All Tests
1. **Phase 1**: Configuration system loads, no hardcoded paths in updated files
2. **Phase 2**: Setup script creates structure, virtual env works, scripts run
3. **Phase 3**: Daemon works with project paths, LaunchAgent template generates  
4. **Phase 4**: Documentation accurate, .gitignore prevents unwanted files
5. **Phase 5**: Fresh environment setup works end-to-end + **CRITICAL**: Config variations are honored (prevents masking)

### Performance Maintained
- **MLX Performance**: 214.6 tokens/sec maintained
- **Pipeline Function**: All 4 phases (Analysis → Narrativization → Dataset → Upload) work
- **Daemon Operation**: LaunchAgent polling every 5 minutes works

## Implementation Timeline

**Total Estimated Time**: 14-20 hours across multiple sessions
- **Phase 1**: 4-6 hours (configuration system)
- **Phase 2**: 3-4 hours (model management)  
- **Phase 3**: 2-3 hours (daemon/LaunchAgent)
- **Phase 4**: 1-2 hours (documentation)
- **Phase 5**: 3-4 hours (integration + **critical** config variation testing)

## For Future Claude Sessions

### Context Summary
- **Working system**: 4-phase AI security pipeline with MLX optimization
- **Architecture choice**: Shared models + project-contained components  
- **8 hardcoded paths**: Identified and documented for systematic replacement
- **Test-driven**: Each phase has validation script that must pass

### Current Status Tracking
- **Branch**: Feature branch with implementation plan
- **Baseline**: All existing functionality works with hardcoded paths
- **Next**: Begin Phase 1 implementation and validation

**⚠️ Critical**: Do not proceed to next phase until current phase validation passes completely.