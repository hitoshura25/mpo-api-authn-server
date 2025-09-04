# Security AI Analysis System

## Overview

Analyzes security scan results from WebAuthn server using OLMo language model.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test OLMo is accessible
python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; print('OLMo ready')"
```

## Usage

```bash
# Test with sample data
python main.py \
  --scan-file data/sample_scans/sample_trivy.json \
  --scan-type trivy \
  --output test_analysis.json

# Analyze Checkov scan  
python main.py \
  --scan-file data/sample_scans/sample_checkov.json \
  --scan-type checkov \
  --output checkov_analysis.json

# Use with your real scan outputs
python main.py \
  --scan-file /path/to/your/trivy_results.json \
  --scan-type trivy \
  --output webauthn_analysis.json
```

## Project Structure

- `parsers/` - Security tool output parsers
- `analysis/` - OLMo analysis logic
- `data/sample_scans/` - Sample scan outputs for testing
- `evaluation/` - Response quality metrics (future)

## Supported Security Tools

- ✅ Trivy (container scanning)
- ✅ Checkov (IaC scanning)
- 🚧 Semgrep (SAST) - planned
- 🚧 OWASP ZAP (DAST) - planned
- 🚧 OSV-Scanner (dependency scanning) - planned

## Notes

- Requires ~4GB RAM for OLMo-1B model
- GPU recommended but not required
- First run downloads model (~2GB)
- Analysis limited to 5 vulnerabilities by default for testing

## Troubleshooting

**If OLMo doesn't load:**
- Try smaller model: allenai/OLMo-1B instead of OLMo-7B
- Check GPU memory if using CUDA
- Use CPU mode by removing device_map="auto"

**If parsing fails:**
- Check actual JSON structure of your scan files
- Print raw JSON to see real format
- Adjust parser to match actual structure