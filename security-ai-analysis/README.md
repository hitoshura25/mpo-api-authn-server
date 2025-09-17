# AI Security Analysis System

## What Does This System Do?

This system automatically analyzes security vulnerabilities using advanced AI models to generate high-quality explanations and remediation guidance. It's designed to help developers understand security issues and learn how to fix them effectively.

**Key Capabilities:**
- 🔍 **Processes real security scan results** from 8+ professional tools (Trivy, Semgrep, etc.)
- 🤖 **AI-powered analysis** using OLMo-2-1B-Instruct model optimized for Apple Silicon (20-30X faster)
- 📖 **Rich explanations** with context, impact assessment, and step-by-step remediation
- 🔄 **Automated workflow** from vulnerability detection to training dataset creation
- 📊 **Research contribution** via published datasets for AI security research

**Real-World Impact:**
- Processes 340 actual vulnerabilities from production security scans
- Creates training datasets for improving AI security capabilities  
- Provides immediate actionable guidance for vulnerability remediation

## How The System Works

```
GitHub Actions Security Scans → Artifact Download → AI Analysis → Rich Narratives → Training Datasets
```

### Complete 4-Phase AI Enhancement Workflow

1. **Phase 1: Enhanced Dataset Creation**: Professional FOSS tools scan code → 5x enhanced security patterns → Rich training datasets
2. **Phase 2: RAG-Enhanced Analysis**: Context-aware vulnerability analysis with retrieval augmentation → Detailed narratives
3. **Phase 3: Sequential Fine-Tuning** ⭐ **NEW DEFAULT**: Progressive specialization with two models:
   - **Stage 1**: Vulnerability Analysis Specialist (base model → analysis expert)
   - **Stage 2**: Code Fix Generation Specialist (Stage 1 model → code fix expert)
4. **Phase 4: Production Upload**: Specialized models and datasets published to HuggingFace Hub

**Automated Monitoring**: Daemon polls GitHub Actions every 5 minutes for new security artifacts and runs complete 4-phase AI enhancement pipeline

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
- Processing time: ~0.8 seconds per vulnerability with MLX optimization

**For Fine-Tuning (Phase 5):**
Optional advanced feature - see [MLX Installation Guide](../docs/development/mlx-installation-guide.md) for Apple Silicon setup.

## Advanced Documentation

For comprehensive fine-tuning usage patterns and advanced configurations:
- 📚 **[Fine-Tuning Usage Guide](../docs/development/ai-security-fine-tuning-usage.md)** - Complete integration modes, configuration options, and troubleshooting
- 🛠️ **[MLX Installation Guide](../docs/development/mlx-installation-guide.md)** - Step-by-step Apple Silicon setup for Phase 5 fine-tuning

## Understanding the Daemon System

The daemon system provides continuous automated processing of new security findings through a simple workflow:

1. **Polls GitHub Actions** every 5 minutes for new security artifacts
2. **Downloads and processes** artifacts automatically  
3. **Runs AI analysis** using the main pipeline
4. **Generates results** in the `results/` directory

The daemon handles all directory management and file processing automatically - just monitor the logs to see activity.

📚 **For detailed daemon configuration and troubleshooting**: See [Fine-Tuning Usage Guide - Daemon Management](../docs/development/ai-security-fine-tuning-usage.md#daemon-system-management)

## LaunchAgent Setup (Automated Mode)

For continuous background processing:

### Install and Monitor

```bash
# Install the daemon (runs every 5 minutes)
cd security-ai-analysis
python3 setup_launchagent.py

# Check if running
launchctl list com.mpo.security-analysis.daemon

# View activity logs
tail -f security-ai-analysis/results/daemon_stdout.log
```

### Basic Control

```bash
# Stop/start daemon
launchctl unload ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist
launchctl load ~/Library/LaunchAgents/com.mpo.security-analysis.daemon.plist
```

📚 **For comprehensive daemon management**: See [Fine-Tuning Usage Guide - Daemon Management](../docs/development/ai-security-fine-tuning-usage.md#daemon-system-management) for detailed configuration, testing, and troubleshooting.

## Daily Usage Patterns

### Manual Analysis (Development)

```bash
# Activate environment and run main pipeline
source security-ai-analysis/venv/bin/activate
cd security-ai-analysis
python3 process_artifacts.py

# Test with sample data
python3 process_artifacts.py --artifacts-dir "test_data"
```

📚 **For comprehensive usage patterns**: See [Fine-Tuning Usage Guide](../docs/development/ai-security-fine-tuning-usage.md) for all command options, integration modes, and advanced configurations.

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
- Verify Apple Silicon optimization: Model should process vulnerabilities in ~0.8 seconds each
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

**For Advanced Troubleshooting:**
- Fine-tuning issues: [Fine-Tuning Usage Guide - Error Handling](../docs/development/ai-security-fine-tuning-usage.md#error-handling--troubleshooting)
- MLX installation problems: [MLX Installation Guide - Troubleshooting](../docs/development/mlx-installation-guide.md#troubleshooting)

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

### System Architecture

**Component Flow**: LaunchAgent → security_artifact_daemon.py → process_artifacts.py → Analysis Results

**Data Pipeline**: GitHub Actions Security Scans → Artifact Download → MLX-Optimized AI Analysis → Rich Narratives → Training Datasets → HuggingFace Publication

**Directory Structure**: Raw artifacts (`data/`) → Analysis processing → Published results (`results/`)

The system maintains data lineage from source to publication with automated processing and human-readable outputs.

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
└── fine-tuned/           # Fine-tuned models
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
- **Performance**: Expected processing time ~0.8 seconds per vulnerability on Apple Silicon

**Production Dataset**: https://huggingface.co/datasets/hitoshura25/webauthn-security-vulnerabilities-olmo

---

**Last Updated**: 2025-09-14  
**Version**: 2.0