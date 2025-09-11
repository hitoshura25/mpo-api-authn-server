# Daemon Architecture Deep Dive

## Overview

The AI Security Analysis daemon system provides continuous, automated processing of security vulnerabilities discovered by GitHub Actions workflows. This document explains the technical architecture, path resolution mechanisms, and integration patterns that enable seamless automated operation.

## System Architecture

### Component Interaction Flow

```
LaunchAgent (macOS) → security_artifact_daemon.py → process_artifacts.py → Analysis Results
      ↓                        ↓                          ↓                    ↓
 Scheduled Run         GitHub Actions Poll        MLX-Optimized AI        HuggingFace Dataset
 (Every 5 min)         (Download Artifacts)       (Generate Narratives)   (Research Publication)
```

### Core Components

1. **LaunchAgent (`com.mpo.security-analysis.daemon.plist`)**
   - macOS system daemon scheduler
   - Runs daemon script every 5 minutes
   - Handles process lifecycle management

2. **Daemon Script (`local-analysis/security_artifact_daemon.py`)**
   - Polls GitHub Actions for new security artifacts
   - Downloads and organizes artifact data
   - Calls analysis pipeline with appropriate parameters

3. **Analysis Pipeline (`security-ai-analysis/process_artifacts.py`)**
   - Processes downloaded artifacts using MLX-optimized AI
   - Generates rich vulnerability narratives
   - Creates training datasets in JSONL format

## Path Resolution Architecture

### Working Directory Strategy

The daemon system uses **project-relative path resolution** to ensure portability across different development environments.

**Primary Working Directory**: `/Users/yourname/mpo-api-authn-server`
- LaunchAgent sets this as WorkingDirectory in plist
- All subsequent path resolution is relative to this root
- Enables consistent operation regardless of user home directory

### Directory Structure & Purpose

```
/Users/yourname/mpo-api-authn-server/          # Project root (daemon working directory)
├── security-ai-analysis/                      # Analysis system directory
│   ├── data/                                  # Project-specific data storage
│   │   ├── artifacts/                         # Raw GitHub Actions downloads
│   │   │   └── run_12345_*/                   # Individual workflow run artifacts
│   │   └── security_artifacts/                # Processed artifacts ready for analysis
│   │       ├── semgrep.sarif                  # Processed security scan results
│   │       ├── trivy.sarif                    # Container vulnerability results
│   │       └── ...                            # Other security tool outputs
│   ├── results/                               # Analysis outputs and datasets
│   │   ├── olmo_analysis_results_*.json       # Complete AI analysis results
│   │   ├── train_*.jsonl                      # Training datasets
│   │   ├── validation_*.jsonl                 # Validation datasets
│   │   ├── daemon_stdout.log                  # Daemon operation logs
│   │   └── daemon_stderr.log                  # Daemon error logs
│   └── venv/                                  # Project-specific Python environment
├── local-analysis/                            # Daemon and integration scripts
│   └── security_artifact_daemon.py            # Main daemon script
└── ~/shared-olmo-models/                      # Shared AI models (external to project)
    └── base/OLMo-2-1B-mlx-q4/                 # MLX-optimized model files
```

### Path Resolution Mechanisms

#### 1. Project Root Discovery
```python
# In daemon script
project_root = Path.cwd()  # LaunchAgent sets working directory to project root
analysis_dir = project_root / "security-ai-analysis"
```

#### 2. Data Directory Management
```python
# Artifact download location (raw GitHub Actions data)
artifacts_dir = analysis_dir / "data" / "artifacts" / f"run_{run_id}_{timestamp}"

# Processed artifacts location (ready for analysis)
security_artifacts_dir = analysis_dir / "data" / "security_artifacts"

# Analysis output location
results_dir = analysis_dir / "results"
```

#### 3. Model Path Resolution
```python
# Uses portable configuration system
from config_manager import get_default_config
config = get_default_config()
model_path = config.get_base_model_path()  # Resolves to ~/shared-olmo-models/base/OLMo-2-1B-mlx-q4
```

## Integration Patterns

### Daemon ↔ Analysis Pipeline Integration

#### Parameter Passing Strategy
```python
# Daemon calls analysis pipeline with simplified interface
analysis_command = [
    sys.executable, str(process_script),
    "--artifacts-dir", str(security_artifacts_dir),  # Processed artifacts location
    "--output-dir", str(results_dir),                # Analysis results location
    "--model-name", self._get_model_path(),          # AI model configuration
    "--branch", "main",                              # Source branch context
    "--commit", run_info['head_sha']                 # Specific commit reference
]
```

#### Data Flow Architecture
1. **Download Phase**: 
   - Raw artifacts downloaded to `data/artifacts/run_*/`
   - GitHub Actions workflow outputs preserved exactly

2. **Processing Phase**:
   - Artifacts copied/processed to `data/security_artifacts/`
   - SARIF files consolidated and validated
   - Ready for AI analysis consumption

3. **Analysis Phase**:
   - `process_artifacts.py` automatically detects processed artifacts
   - MLX-optimized AI model analyzes vulnerability data
   - Rich narratives generated with remediation guidance

4. **Output Phase**:
   - Results written to `results/` directory
   - Training datasets created in JSONL format
   - Logs capture complete operation history

### Artifact Directory Evolution

**Why Multiple Directory Levels?**

Different directory structures serve specific purposes in the processing pipeline:

- **`data/artifacts/run_***`**: Raw GitHub Actions downloads
  - Preserves original workflow artifact structure
  - Enables debugging of download/extraction issues
  - Maintains audit trail of source data

- **`data/security_artifacts/`**: Processed artifacts ready for analysis
  - Standardized format for AI processing
  - Consolidated SARIF files from multiple tools
  - Default location for `process_artifacts.py`

- **`results/`**: Final analysis outputs and datasets
  - AI-generated vulnerability explanations
  - Training datasets for model fine-tuning
  - Publication-ready research data

This separation enables:
- **Debugging**: Clear distinction between raw and processed data
- **Flexibility**: Analysis can work with custom artifact sources
- **Reliability**: Processing failures don't corrupt source artifacts
- **Auditability**: Complete data lineage from source to publication

## LaunchAgent Template System

### Template Architecture

The LaunchAgent system uses a **minimal template substitution approach**:

```xml
<!-- Templates use simple variable substitution -->
<string>{{PROJECT_ROOT}}/security-ai-analysis/venv/bin/python3</string>
<string>{{PROJECT_ROOT}}/local-analysis/security_artifact_daemon.py</string>
```

### Setup Script Integration

```python
# setup_launchagent.py resolves PROJECT_ROOT dynamically
project_root = Path(__file__).parent.parent.absolute()
plist_content = plist_content.replace('{{PROJECT_ROOT}}', str(project_root))
```

**Benefits of Minimal Approach**:
- **Simplicity**: Only one variable to substitute
- **Reliability**: Reduces configuration complexity
- **Maintainability**: Easy to understand and modify
- **Portability**: Works across different user environments

## Environment Integration

### Python Environment Management

```xml
<!-- LaunchAgent plist configuration -->
<key>EnvironmentVariables</key>
<dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    <key>PYTHONPATH</key>
    <string>{{PROJECT_ROOT}}/security-ai-analysis:{{PROJECT_ROOT}}</string>
</dict>
```

**Purpose**:
- **PATH**: Ensures system tools (gh, python3) are accessible
- **PYTHONPATH**: Enables module imports from both analysis and project directories
- **Working Directory**: Set to project root for consistent relative path resolution

### Configuration System Integration

The daemon integrates seamlessly with the portable configuration system:

```python
# Daemon uses same config system as manual analysis
config = get_default_config()
model_path = config.get_base_model_path()
```

**Key Benefits**:
- **Consistency**: Same configuration used in automated and manual modes
- **Portability**: Configuration adapts to different environments automatically
- **Maintainability**: Single source of truth for system configuration

## Security & Reliability Patterns

### Process Isolation
- Each daemon run operates in isolated process space
- Virtual environment ensures dependency consistency
- Project-relative paths prevent system interference

### Error Handling & Logging
- Comprehensive logging to `daemon_stdout.log` and `daemon_stderr.log`
- Graceful handling of GitHub API failures
- Automatic retry logic for transient network issues

### Resource Management
- LaunchAgent ThrottleInterval prevents excessive resource usage
- Process cleanup ensures no zombie processes
- Memory-efficient model loading with MLX optimization

## Troubleshooting Architecture

### Common Path Resolution Issues

**Problem**: Daemon can't find project files
- **Cause**: LaunchAgent working directory misconfiguration
- **Solution**: Verify plist WorkingDirectory matches project root

**Problem**: Python module import failures  
- **Cause**: PYTHONPATH not including analysis directory
- **Solution**: Check EnvironmentVariables in LaunchAgent plist

**Problem**: Model not found errors
- **Cause**: Shared model directory not accessible
- **Solution**: Verify `~/shared-olmo-models/base/OLMo-2-1B-mlx-q4/` exists

### Debugging Workflow

1. **Check LaunchAgent Status**: `launchctl list com.mpo.security-analysis.daemon`
2. **Examine Logs**: `tail -f security-ai-analysis/results/daemon_*.log`
3. **Test Manual Run**: `python3 local-analysis/security_artifact_daemon.py --test-mode`
4. **Verify Configuration**: Ensure portable config system loads correctly

## Future Architecture Considerations

### Scalability Patterns
- Multi-repository support through configuration templates
- Parallel processing for multiple artifact sources
- Container-based deployment for server environments

### Monitoring Integration
- Health check endpoints for system monitoring
- Metrics collection for performance analysis
- Alert integration for failure notifications

### Cross-Platform Extensions
- Windows Task Scheduler equivalent
- Linux systemd service configuration
- Docker container deployment patterns

The daemon architecture provides a robust, maintainable foundation for continuous security analysis while maintaining simplicity and portability across different development environments.