# AI Security Dataset Research Initiative

## 🎯 Project Overview

This initiative transforms security vulnerabilities from a production WebAuthn authentication server into a valuable research contribution for AI safety and security remediation. We're using real-world security findings to improve how AI models (specifically OLMo) generate actionable security fixes.

**Core Problem We're Solving:**

- Current AI models give vague security advice: "Review and apply security best practices"
- We need specific, actionable fixes: "Replace `permissions: write-all` with `permissions: contents: read`"

**Our Solution:**

- Fine-tune OLMo on real security vulnerabilities and their fixes
- Create a comprehensive dataset from actual security scan results
- Build an automated pipeline from vulnerability detection to AI-powered remediation

---

## 📊 Current Implementation Status

### ✅ Completed Components

#### 1. **Security Scanning Infrastructure**

- **8 Professional Security Tools** integrated and operational:
    - **Checkov**: Infrastructure as Code security
    - **Trivy**: Container and dependency scanning
    - **Semgrep**: Custom WebAuthn security rules (14 rules)
    - **OWASP ZAP**: Dynamic application security testing
    - **OSV-Scanner**: Open source vulnerability detection
    - **Gitleaks**: Secrets scanning
    - **Dependabot**: Dependency vulnerability alerts
    - **SARIF**: Unified security reporting format

- **Findings**: Currently detecting ~100+ vulnerabilities across the codebase
- **Integration**: GitHub Actions workflows with artifact storage

#### 2. **OLMo Analysis System** (`security-ai-analysis/`)

```
security-ai-analysis/
├── parsers/                 # Security tool output parsers
│   ├── trivy_parser.py     # Parses Trivy JSON
│   ├── checkov_parser.py   # Parses Checkov results
│   ├── semgrep_parser.py   # Parses Semgrep findings
│   ├── sarif_parser.py     # Handles SARIF format
│   ├── osv_parser.py       # OSV scanner results
│   └── zap_parser.py       # OWASP ZAP findings
├── analysis/
│   └── olmo_analyzer.py    # OLMo model integration (optimized)
├── main.py                  # CLI interface
├── process_artifacts.py    # Batch processing (ALL vulnerabilities)
├── create_security_dataset.py       # Evaluation dataset creation
├── create_narrativized_dataset.py   # Rich context generation
└── prepare_finetuning_dataset.py    # Fine-tuning preparation
```

**Key Features:**

- Processes ALL vulnerabilities in batches (not limited to 20)
- Optimized prompting for OLMo (temperature=0.3, repetition_penalty=1.2)
- Structured output with impact/remediation/prevention sections
- Model caching for performance

#### 3. **Dataset Creation Pipeline**

Following the successful "health journal" approach from Google Gemini notes:

- **Narrativization**: Converts raw vulnerabilities into rich, contextual stories
- **Real Fixes**: Extracts actual security fixes from git history
- **WebAuthn-Specific**: Includes domain-specific security patterns

Example narrative structure:

```
Security Issue Found: CKV2_GHA_1
Problem: GitHub Actions workflow has excessive permissions
Impact: Could allow unauthorized repository modifications
Specific Fix: Replace 'permissions: write-all' with minimal required permissions
Validation: Checkov scan should pass after fix
```

#### 4. **GitHub Actions Automation**

- **`olmo-security-analysis.yml`**: Complete workflow for analysis and dataset creation
- **`automated-security-analysis.yml`**: Triggers after security scans
- **Trigger Options**:
    - **Manual**: `workflow_dispatch` with customizable parameters
    - **Auto-PR**: Triggers on PRs modifying `security-ai-analysis/` code
    - **Callable**: Can be invoked by other workflows
- **Features**:
    - Automatic artifact download from latest security scans
    - OLMo model caching (~2GB)
    - Fine-tuning dataset generation
    - Google Colab notebook creation
    - Optional Hugging Face Hub upload (disabled for PRs)

---

## 🚀 Next Steps for New Session

### Immediate Actions (Ready to Execute)

#### 1. **Run the Complete Pipeline**

```bash
# In GitHub Actions UI:
1. Go to Actions tab
2. Select "OLMo Security Analysis"
3. Run workflow with default settings
4. Wait for completion (~30 minutes)
5. Download artifact: olmo-finetuning-dataset-{run-id}
```

#### 2. **Fine-Tune OLMo** (Primary Goal)

```python
# Google Colab Process:
1. Upload finetuning_dataset.zip to Google Drive
2. Open finetune_olmo_colab.ipynb in Colab
3. Enable GPU runtime (T4)
4. Run all cells
# Result: Fine-tuned OLMo model saved to Drive
```

#### 3. **Test Fine-Tuned Model**

```python
# After fine-tuning, test with real vulnerabilities:
prompt = "Fix the GitHub Actions permission vulnerability in .github/workflows/deploy.yml"
# Should generate specific YAML fix, not generic advice
```

### Development Tasks

#### Priority 1: Improve Dataset Quality

- [ ] Add more WebAuthn-specific security patterns
- [ ] Collect more real fixes from git history
- [ ] Create vulnerability→patch pairs from actual PRs
- [ ] Add validation examples (how to verify fix works)

#### Priority 2: Enhance Model Performance

- [ ] Test different fine-tuning hyperparameters
- [ ] Experiment with LoRA/QLoRA for efficient training
- [ ] Create specialized prompts for different vulnerability types
- [ ] Implement few-shot examples in prompts

#### Priority 3: Production Integration

- [ ] Create API endpoint for remediation generation
- [ ] Build PR automation (generate fix PRs automatically)
- [ ] Add validation pipeline (verify fixes don't break functionality)
- [ ] Implement feedback loop from merged fixes

---

## 📁 File Structure & Purpose

### Core Scripts

- **`process_artifacts.py`**: Main entry point, downloads and analyzes security scans
- **`create_narrativized_dataset.py`**: Transforms vulnerabilities into training narratives
- **`prepare_finetuning_dataset.py`**: Formats data for OLMo fine-tuning
- **`olmo_analyzer.py`**: Optimized OLMo integration with better prompting

### Workflows

- **`.github/workflows/olmo-security-analysis.yml`**: Complete pipeline workflow
- **`.github/workflows/automated-security-analysis.yml`**: Automatic trigger after scans

### Generated Artifacts (Don't Commit)

- `data/olmo_analysis_results/`: Analysis outputs
- `data/security_artifacts/`: Downloaded scan results
- `data/finetuning_dataset/`: Prepared training data
- `venv/`, `__pycache__/`: Python artifacts

---

## 🔬 Technical Details

### Current OLMo Configuration

```python
model = "allenai/OLMo-1B"  # Using 1B parameter version
temperature = 0.3          # Lower for consistent output
max_tokens = 150          # Focused responses
repetition_penalty = 1.2   # Reduce repetitive text
trust_remote_code = True   # Required for OLMo
```

### Dataset Statistics (Typical Run)

- **Total Vulnerabilities**: ~100-150
- **By Severity**: HIGH (40%), MEDIUM (35%), LOW (25%)
- **By Tool**: Checkov (40%), Semgrep (30%), Others (30%)
- **Training Examples**: ~300-500 after narrativization
- **Validation Split**: 90/10

### Fine-Tuning Parameters (Colab)

```python
num_epochs = 3
batch_size = 2 (with gradient accumulation = 4)
learning_rate = 5e-5
warmup_steps = 100
fp16 = True  # For T4 GPU efficiency
```

---

## 🎯 Success Metrics

### Short-term (After Fine-tuning)

- [ ] Model generates specific code fixes (not generic advice)
- [ ] Fixes compile/parse without syntax errors
- [ ] Remediation matches vulnerability type
- [ ] WebAuthn-specific issues handled correctly

### Long-term (Research Goals)

- [ ] 80%+ of generated fixes resolve the vulnerability
- [ ] Reduce time-to-fix from hours to minutes
- [ ] Dataset published for research community
- [ ] Contributions to OLMo improvement at AI2

---

## 🤝 Collaboration Points

### For AI2/OLMo Team

- **Dataset**: Rich security remediation dataset from production system
- **Evaluation**: How well can OLMo learn domain-specific fixes?
- **Improvements**: Specific areas where OLMo needs enhancement
- **Benchmarks**: Security-focused evaluation metrics

### For Security Community

- **Automated Remediation**: AI-powered security fix generation
- **Best Practices**: What makes good training data for security AI?
- **Open Dataset**: Shareable security vulnerability→fix pairs

---

## 🚦 Quick Start for New Session

```bash
# 1. Check current status
cd security-ai-analysis
ls -la data/  # Check for existing results

# 2. Run analysis (if needed)
python process_artifacts.py

# 3. Create dataset
python create_narrativized_dataset.py
python prepare_finetuning_dataset.py

# 4. Check GitHub Actions
# Go to: https://github.com/[your-repo]/actions
# Download latest artifact: olmo-finetuning-dataset-*

# 5. Fine-tune in Colab
# Upload to Drive, open notebook, run cells

# 6. Test improved model
# Load fine-tuned model and test on new vulnerabilities
```

---

## 📚 Background Context

### Why This Approach?

Based on successful "health journal" pattern where:

1. Raw data → Narrativized stories → Training data
2. Domain-specific context improves model performance
3. Real examples better than synthetic data

### Why OLMo?

- Open source model from AI2
- Good base performance on code/technical content
- Opportunity to contribute improvements back
- Aligns with FOSS philosophy of the project

### Why Security Remediation?

- Current tools find problems but don't fix them
- Developers need actionable solutions, not just warnings
- Automated fixes can dramatically improve security posture
- WebAuthn security is critical for authentication systems

---

## 📝 Notes for Future Sessions

### Known Issues

- OLMo sometimes generates repetitive text (addressed with repetition_penalty)
- Some fixes are still too generic (needs more training data)
- Container scanning produces many similar vulnerabilities (consider deduplication)

### Optimization Opportunities

- Use larger OLMo model (7B) if resources available
- Implement retrieval-augmented generation (RAG) with fix database
- Add semantic similarity to avoid duplicate training examples
- Create fix validation pipeline using security scanners

### Research Questions

- Can fine-tuned OLMo outperform GPT-4 on domain-specific security fixes?
- What's the minimum training data needed for effective remediation?
- How to balance security education vs. preventing exploit generation?
- Can we create a feedback loop from production fixes to improve model?

---

*Last Updated: Current session*
*Status: Ready for fine-tuning phase*
*Next Milestone: Test fine-tuned model on real vulnerabilities*
