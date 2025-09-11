# AI Security Analysis System

## What Does This System Do?

This system automatically analyzes security vulnerabilities using advanced AI models to generate high-quality explanations and remediation guidance. It's designed to help developers understand security issues and learn how to fix them effectively.

**Key Capabilities:**
- 🔍 **Processes real security scan results** from 8+ professional tools (Trivy, Semgrep, etc.)
- 🤖 **AI-powered analysis** using OLMo-2-1B model optimized for Apple Silicon (20-30x faster)
- 📖 **Rich explanations** with context, impact assessment, and step-by-step remediation
- 🔄 **Automated workflow** from vulnerability detection to training dataset creation
- 📊 **Research contribution** via published datasets for AI security research

**Real-World Impact:**
- Processes 440+ actual vulnerabilities from production security scans
- Creates training datasets for improving AI security capabilities
- Provides immediate actionable guidance for vulnerability remediation

## How The System Works

```
GitHub Actions Security Scans → Artifact Download → AI Analysis → Rich Narratives → Training Datasets
```

### Complete Workflow

1. **Security Scanning**: Professional FOSS tools (Trivy, Semgrep, etc.) scan code and generate findings
2. **Automated Monitoring**: Daemon polls GitHub Actions every 5 minutes for new security artifacts  
3. **AI Processing**: OLMo-2-1B model analyzes each vulnerability with MLX optimization
4. **Rich Narrativization**: Creates detailed explanations with remediation guidance
5. **Dataset Creation**: Produces training datasets in JSONL format for AI research
6. **Publication**: Results published to HuggingFace for community benefit

### Two Usage Modes

**🔄 Automated Mode (Production)**
- Daemon runs continuously via macOS LaunchAgent
- Automatically processes new security findings
- Zero user intervention required

**⚡ Manual Mode (Development/Testing)**
- Run analysis on-demand with custom data
- Process existing security artifacts
- Test with sample vulnerabilities

## Complete Setup From Scratch

### Prerequisites
- macOS with Apple Silicon (M1/M2/M3) for optimal performance
- Python 3.9+
- GitHub CLI (`gh`) - Install with `brew install gh`
- Git repository access

### Step 1: Initial Setup (5 minutes)

```bash
# Clone the repository
git clone https://github.com/hitoshura25/mpo-api-authn-server.git
cd mpo-api-authn-server

# Run automated setup (creates everything needed)
python3 security-ai-analysis/setup.py
```

**What setup.py does:**
- ✅ Creates project directory structure (`data/`, `results/`, `venv/`)
- ✅ Creates shared model directory (`~/shared-olmo-models/`)  
- ✅ Sets up virtual environment with all dependencies
- ✅ Downloads and converts OLMo-2-1B model to MLX format (~2GB download)
- ✅ Validates entire system is ready to use

### Step 2: Authenticate with GitHub

```bash
# Required for downloading security artifacts from GitHub Actions
gh auth login
```

### Step 3: Test the System

```bash
# Activate the project environment
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

# Test configuration loads correctly
python3 -c "from config_manager import OLMoSecurityConfig; print('✅ Config loaded!')"

# Test the main pipeline (uses sample data)
python3 process_artifacts.py --artifacts-dir "test_data"

# Test with real GitHub Actions artifacts (auto-downloads latest)
python3 process_artifacts.py
```

**Expected Output:**
- Analysis results appear in `results/` directory
- Rich narratives with explanations and remediation guidance
- Training datasets in JSONL format
- Processing ~0.8 seconds per vulnerability with MLX optimization

## Understanding the Daemon System

The daemon system provides continuous automated processing of new security findings.

### How Path Resolution Works

**Working Directory**: The daemon runs from your project root (`/Users/yourname/mpo-api-authn-server`)

**Key Directories**:
- `security-ai-analysis/data/security_artifacts/` - Downloaded GitHub Actions artifacts
- `security-ai-analysis/results/` - AI analysis outputs  
- `local-analysis/` - Contains daemon script
- `~/shared-olmo-models/` - Shared AI models (reused across projects)

### How Daemon Integrates with Analysis

1. **Daemon downloads artifacts** to `data/security_artifacts/`
2. **Daemon calls process_artifacts.py** with default directories
3. **process_artifacts.py automatically finds** downloaded artifacts 
4. **Results appear in** `results/` directory

**Why different directory structures?**
- `data/artifacts/run_***` - Raw GitHub Actions downloads (daemon uses this)
- `data/security_artifacts/` - Processed artifacts ready for analysis
- `results/` - Final analysis outputs

The system automatically handles the flow between these directories.

## LaunchAgent Setup (Automated Mode)

To run the system continuously in the background:

### Install the Daemon

```bash
cd security-ai-analysis
python3 setup_launchagent.py --dry-run  # Preview first
python3 setup_launchagent.py           # Install LaunchAgent
```

**What this does:**
- Creates `~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist`
- Configures daemon to run every 5 minutes
- Sets up proper paths and environment variables
- Starts the daemon automatically

### Monitor Daemon Activity

```bash
# Check if daemon is running
launchctl list com.mpo.security-analysis.daemon

# View real-time logs
tail -f security-ai-analysis/results/daemon_stdout.log
tail -f security-ai-analysis/results/daemon_stderr.log

# Test daemon manually (safe, exits after one cycle)
cd /Users/yourname/mpo-api-authn-server  # Use your actual path
source security-ai-analysis/venv/bin/activate
python3 local-analysis/security_artifact_daemon.py --test-mode
```

### Control the Daemon

```bash
# Stop daemon
launchctl unload ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist

# Start daemon
launchctl load ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist

# Restart daemon (after changes)
launchctl unload ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist
launchctl load ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist
```

## Daily Usage Patterns

### Manual Analysis (Development)

```bash
# Activate environment
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis

# Process latest GitHub Actions artifacts
python3 process_artifacts.py

# Process specific artifact directory
python3 process_artifacts.py --artifacts-dir "path/to/custom/artifacts"

# Process with custom output location
python3 process_artifacts.py --output-dir "custom_results"

# Test with sample data
python3 process_artifacts.py --artifacts-dir "test_data"
```

### Understanding Results

**Generated Files:**
- `results/olmo_analysis_results_YYYYMMDD_HHMMSS.json` - Complete analysis with explanations
- `results/narrativized_dataset_YYYYMMDD_HHMMSS.json` - Rich training narratives
- `results/train_YYYYMMDD_HHMMSS.jsonl` - Training dataset for fine-tuning
- `results/validation_YYYYMMDD_HHMMSS.jsonl` - Validation dataset
- `results/dataset_info_YYYYMMDD_HHMMSS.json` - Dataset metadata

**Analysis Content:**
- Vulnerability details and severity assessment
- Root cause analysis with code context
- Step-by-step remediation instructions
- Best practices and prevention guidance

## Troubleshooting Guide

### Setup Issues

**Problem**: `setup.py` fails with model download error
```bash
# Check virtual environment
source security-ai-analysis/venv/bin/activate
pip install mlx-lm transformers>=4.39.3

# Test model download manually
python3 -c "from model_manager import OLMoModelManager; OLMoModelManager().setup_project_structure()"
```

**Problem**: Configuration errors
```bash
# Validate configuration
python3 -c "from config_manager import get_default_config; print(get_default_config().get_config_summary())"

# Check model path
ls ~/shared-olmo-models/base/OLMo-2-1B-mlx-q4/
```

### Runtime Issues

**Problem**: `process_artifacts.py` can't find artifacts
- Check if GitHub CLI is authenticated: `gh auth status`
- Verify repository access: `gh repo view hitoshura25/mpo-api-authn-server`
- Check artifact directory: `ls -la data/security_artifacts/`

**Problem**: Daemon not processing new artifacts
```bash
# Check daemon status
launchctl list com.mpo.security-analysis.daemon

# View daemon logs for errors
tail -50 security-ai-analysis/results/daemon_stderr.log

# Test daemon manually
python3 local-analysis/security_artifact_daemon.py --test-mode
```

**Problem**: Model performance issues
- Verify Apple Silicon optimization: Model should process ~0.8 seconds per vulnerability
- Check MLX installation: `python3 -c "import mlx.core; print('✅ MLX working')"`
- Monitor memory usage during processing

### Common Error Messages

**"No module named 'mlx_lm'"**
```bash
source security-ai-analysis/venv/bin/activate
pip install mlx-lm
```

**"Config file not found"**
```bash
# Verify config file exists
ls config/olmo-security-config.yaml
```

**"Model not found"**
```bash
# Check model directory
ls ~/shared-olmo-models/base/OLMo-2-1B-mlx-q4/
# Re-run setup if empty
python3 setup.py
```

## Advanced Configuration

### Custom Model Paths

Edit `config/olmo-security-config.yaml`:
```yaml
base_models_dir: "/custom/path/to/models"
default_base_model: "your-preferred-model"
```

### Environment Variable Overrides

```bash
export OLMO_BASE_MODELS_DIR="/custom/models"
export OLMO_DEFAULT_BASE_MODEL="custom-model-name"
python3 process_artifacts.py
```

### Different Repositories

```bash
# Process artifacts from different repository
cd local-analysis
python3 security_artifact_daemon.py --repo "other-org/other-repo" --test-mode
```

## Architecture Overview (For Developers)

### Core Components

**`process_artifacts.py`** - Main pipeline integrating:
- Artifact download and validation
- MLX-optimized security analysis  
- Rich narrativization
- Training dataset creation

**`analysis/olmo_analyzer.py`** - MLX-optimized OLMo-2 security analyzer

**`local-analysis/security_artifact_daemon.py`** - Continuous monitoring daemon

**`config_manager.py`** - Portable configuration system

### Directory Structure

```
security-ai-analysis/
├── setup.py              # Automated setup
├── setup_launchagent.py  # Daemon installation
├── process_artifacts.py  # Main pipeline
├── config_manager.py     # Configuration
├── analysis/             # AI analysis components
├── config/               # YAML configuration
├── templates/            # LaunchAgent template
├── data/                 # Project-specific artifacts
├── results/              # Analysis outputs
├── test_data/            # Sample vulnerabilities
└── venv/                 # Project environment

~/shared-olmo-models/     # Shared across projects
├── base/                 # Base models
└── fine-tuned/           # Fine-tuned models (future)
```

### Sharing Philosophy

**Shared Across Projects** (High-Value, Reusable):
- AI models in `~/shared-olmo-models/`
- Published datasets on HuggingFace
- Source code (fully portable)

**Project-Specific** (Temporary Processing):
- Raw security artifacts (`data/`)
- Intermediate results (`results/`)  
- Virtual environment (`venv/`)

---

## Getting Help

- **System Issues**: Check logs in `results/daemon_*.log`
- **Model Problems**: Verify `~/shared-olmo-models/base/OLMo-2-1B-mlx-q4/` exists
- **GitHub Access**: Ensure `gh auth status` shows authentication
- **Performance**: Expected ~0.8 seconds per vulnerability on Apple Silicon

**Production Dataset**: https://huggingface.co/datasets/hitoshura25/webauthn-security-vulnerabilities-olmo