#!/bin/bash
set -euo pipefail

echo "🧪 Phase 1 Validation Tests - AI Security Portability Implementation"
echo "====================================================================="
echo

# Set up test environment - find the mpo-api-authn-server root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$SCRIPT_DIR"
while [ ! -f "$PROJECT_ROOT/security-ai-analysis/config_manager.py" ] && [ "$PROJECT_ROOT" != "/" ]; do
    PROJECT_ROOT=$(cd "$PROJECT_ROOT/.." && pwd)
done

if [ ! -f "$PROJECT_ROOT/security-ai-analysis/config_manager.py" ]; then
    echo "❌ Could not find project root with config_manager.py"
    exit 1
fi

cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -f "security-ai-analysis/venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment..."
    source security-ai-analysis/venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found, using system Python"
fi
echo

# Test 1: Configuration manager loads without errors
echo "📋 Test 1: Configuration manager loads without errors"
python3 -c "
import sys
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig
config = OLMoSecurityConfig()
print('✅ Config loads successfully')
print(f'   Base models dir: {config.base_models_dir}')
print(f'   Fine-tuned models dir: {config.fine_tuned_models_dir}')
print(f'   Default model: {config.default_base_model}')
"
echo

# Test 2: Configuration summary works
echo "📋 Test 2: Configuration summary functionality"
python3 -c "
import sys
import json
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig
config = OLMoSecurityConfig()
summary = config.get_config_summary()
print('✅ Configuration summary works')
print(json.dumps(summary, indent=2))
"
echo

# Test 3: Model path detection works (allows FileNotFoundError for fresh setup)
echo "📋 Test 3: Model path detection functionality"
python3 -c "
import sys
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig
config = OLMoSecurityConfig()
try:
    path = config.get_base_model_path()
    print(f'✅ Default model found at: {path}')
except FileNotFoundError as e:
    print(f'⚠️  Default model not found (expected for fresh setup): {e}')
    print('✅ Model path detection works correctly (fail-fast behavior)')
"
echo

# Test 4: Updated olmo_analyzer.py can be imported and instantiated
echo "📋 Test 4: Updated olmo_analyzer.py loads with configuration"
python3 -c "
import sys
sys.path.append('security-ai-analysis')
from analysis.olmo_analyzer import OLMoSecurityAnalyzer
print('✅ Updated OLMoSecurityAnalyzer can be imported')
# Test configuration loading (should work if model is available)
analyzer = OLMoSecurityAnalyzer()
print('✅ OLMoSecurityAnalyzer can be instantiated with configuration')
print(f'   Config base models dir: {analyzer.config.base_models_dir}')
print(f'   Config default model: {analyzer.config.default_base_model}')
"
echo

# Test 5: Updated process_artifacts.py can be imported and shows help
echo "📋 Test 5: Updated process_artifacts.py works with configuration"
cd security-ai-analysis
python3 process_artifacts.py --help | head -10 | grep -E "(Process|usage|model)" && echo "✅ Process script works with configured model paths"
cd "$PROJECT_ROOT"
echo

# Test 6: No hardcoded paths remain in updated files
echo "📋 Test 6: Validate no hardcoded paths remain in updated files"
HARDCODED_FOUND=false

echo "   Checking analysis/olmo_analyzer.py..."
if grep -q "olmo-security-analysis\|/Users/vinayakmenon/olmo-security-analysis" security-ai-analysis/analysis/olmo_analyzer.py; then
    echo "❌ Hardcoded paths still exist in olmo_analyzer.py"
    grep -n "olmo-security-analysis\|/Users/vinayakmenon/olmo-security-analysis" security-ai-analysis/analysis/olmo_analyzer.py || true
    HARDCODED_FOUND=true
else
    echo "   ✅ No hardcoded paths found in olmo_analyzer.py"
fi

echo "   Checking process_artifacts.py..."
if grep -q "olmo-security-analysis\|/Users/vinayakmenon/olmo-security-analysis" security-ai-analysis/process_artifacts.py; then
    echo "❌ Hardcoded paths still exist in process_artifacts.py"
    grep -n "olmo-security-analysis\|/Users/vinayakmenon/olmo-security-analysis" security-ai-analysis/process_artifacts.py || true
    HARDCODED_FOUND=true
else
    echo "   ✅ No hardcoded paths found in process_artifacts.py"
fi

if [ "$HARDCODED_FOUND" = true ]; then
    echo "❌ Test 6 FAILED: Hardcoded paths still exist"
    exit 1
else
    echo "✅ Test 6 PASSED: No hardcoded paths found in updated files"
fi
echo

# Test 7: Configuration file structure validation
echo "📋 Test 7: Configuration file structure validation"
python3 -c "
import yaml
from pathlib import Path

config_file = Path('config/olmo-security-config.yaml')
if not config_file.exists():
    raise FileNotFoundError(f'Config file not found: {config_file}')

with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

required_keys = ['base_models_dir', 'fine_tuned_models_dir', 'default_base_model']
for key in required_keys:
    if key not in config:
        raise KeyError(f'Required key missing from config: {key}')

print('✅ Configuration file structure is valid')
print(f'   Keys present: {list(config.keys())}')
"
echo

# Test 8: Environment variable override functionality
echo "📋 Test 8: Environment variable override functionality"
export OLMO_BASE_MODELS_DIR="/tmp/test-base-models"
export OLMO_DEFAULT_BASE_MODEL="test-model-variant"
python3 -c "
import sys
import os
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig
config = OLMoSecurityConfig()
expected_base = os.environ.get('OLMO_BASE_MODELS_DIR')
expected_model = os.environ.get('OLMO_DEFAULT_BASE_MODEL')
if str(config.base_models_dir) != expected_base:
    raise AssertionError(f'Environment override failed: expected {expected_base}, got {config.base_models_dir}')
if config.default_base_model != expected_model:
    raise AssertionError(f'Environment override failed: expected {expected_model}, got {config.default_base_model}')
print('✅ Environment variable overrides work correctly')
print(f'   Base models dir: {config.base_models_dir}')
print(f'   Default model: {config.default_base_model}')
"
unset OLMO_BASE_MODELS_DIR OLMO_DEFAULT_BASE_MODEL
echo

echo "🎉 Phase 1 Validation Complete!"
echo "================================"
echo "✅ Configuration system implemented and working"
echo "✅ Hardcoded paths replaced with configurable paths"
echo "✅ Environment variable overrides functional"
echo "✅ Fail-fast configuration behavior working"
echo "✅ Updated components load and work correctly"
echo
echo "📁 Created files:"
echo "   - security-ai-analysis/config_manager.py"
echo "   - config/olmo-security-config.yaml"
echo "   - Updated: security-ai-analysis/analysis/olmo_analyzer.py"
echo "   - Updated: security-ai-analysis/process_artifacts.py"
echo
echo "🚀 Ready for Phase 2: Model Management & Setup Automation"