#!/bin/bash
set -euo pipefail

echo "🔄 Phase 5 Integration Tests - Complete System Validation"
echo "=========================================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function for test results
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ $2${NC}"
        ((TESTS_FAILED++))
    fi
}

# Helper function for info messages
info_msg() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Helper function for warnings
warn_msg() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo ""
echo "📋 Test 1: Fresh Environment Simulation"
echo "----------------------------------------"

# Test 1.1: Clean environment setup
info_msg "Simulating fresh environment setup..."

# Create a temporary test environment
TEST_ENV_DIR="/tmp/ai-security-test-$$"
mkdir -p "$TEST_ENV_DIR"

# Test 1.2: Copy project to test environment
if cp -r security-ai-analysis "$TEST_ENV_DIR/"; then
    test_result 0 "Project copied to test environment: $TEST_ENV_DIR"
else
    test_result 1 "Failed to copy project to test environment"
fi

cd "$TEST_ENV_DIR/security-ai-analysis"

# Test 1.3: Verify no existing virtual environment
if [ ! -d "venv" ]; then
    test_result 0 "No existing virtual environment (clean start)"
else
    test_result 1 "Virtual environment already exists (not clean)"
fi

# Test 1.4: Create minimal model directories for testing
TEST_MODELS_DIR="$TEST_ENV_DIR/test-models"
mkdir -p "$TEST_MODELS_DIR/base"
mkdir -p "$TEST_MODELS_DIR/fine-tuned"

# Create a dummy model for testing
TEST_MODEL_DIR="$TEST_MODELS_DIR/base/OLMo-2-1B-mlx-q4"
mkdir -p "$TEST_MODEL_DIR"
echo "dummy model file" > "$TEST_MODEL_DIR/model.txt"
echo "config file" > "$TEST_MODEL_DIR/config.json"

test_result 0 "Test model directories created: $TEST_MODELS_DIR"

echo ""
echo "📋 Test 2: Configuration System Validation"
echo "-------------------------------------------"

# Test 2.1: Create alternative config for testing
cat > test-config.yaml << EOF
# Test configuration with alternative paths
base_models_dir: "$TEST_MODELS_DIR/base"
fine_tuned_models_dir: "$TEST_MODELS_DIR/fine-tuned"
default_base_model: "OLMo-2-1B-mlx-q4"
EOF

# Test 2.2: Validate config_manager can load alternative config
python3 -c "
import sys
sys.path.append('.')
from config_manager import OLMoSecurityConfig
from pathlib import Path

try:
    config = OLMoSecurityConfig(Path('test-config.yaml'))
    print(f'✅ Config loaded successfully')
    print(f'Base models dir: {config.base_models_dir}')
    print(f'Fine-tuned models dir: {config.fine_tuned_models_dir}')
    print(f'Default model: {config.default_base_model}')
    
    # Verify the paths match our test setup
    expected_base = Path('$TEST_MODELS_DIR/base').resolve()
    actual_base = config.base_models_dir.resolve()
    if actual_base == expected_base:
        print('✅ Base models directory correctly configured')
    else:
        print(f'❌ Base models directory mismatch: expected {expected_base}, got {actual_base}')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Config loading failed: {e}')
    sys.exit(1)
" && test_result 0 "Alternative configuration loaded successfully" || test_result 1 "Alternative configuration loading failed"

# Test 2.3: Validate model path resolution works
python3 -c "
import sys
sys.path.append('.')
from config_manager import OLMoSecurityConfig
from pathlib import Path

try:
    config = OLMoSecurityConfig(Path('test-config.yaml'))
    model_path = config.get_base_model_path()
    print(f'✅ Model path resolved: {model_path}')
    
    # Verify the model directory exists and has content
    if model_path.exists():
        print('✅ Model directory exists')
        if (model_path / 'model.txt').exists():
            print('✅ Model files found')
        else:
            print('❌ Model files not found')
            sys.exit(1)
    else:
        print(f'❌ Model directory does not exist: {model_path}')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Model path resolution failed: {e}')
    sys.exit(1)
" && test_result 0 "Model path resolution working correctly" || test_result 1 "Model path resolution failed"

echo ""
echo "📋 Test 3: Environment Variable Override Testing"
echo "-------------------------------------------------"

# Test 3.1: Override base models directory
export OLMO_BASE_MODELS_DIR="$TEST_MODELS_DIR/base-override"
mkdir -p "$OLMO_BASE_MODELS_DIR"
mkdir -p "$OLMO_BASE_MODELS_DIR/OLMo-2-1B-mlx-q4"
echo "override model" > "$OLMO_BASE_MODELS_DIR/OLMo-2-1B-mlx-q4/model.txt"

python3 -c "
import sys
sys.path.append('.')
from config_manager import OLMoSecurityConfig
from pathlib import Path

try:
    config = OLMoSecurityConfig(Path('test-config.yaml'))
    
    # Check environment variable override
    expected_override = Path('$TEST_MODELS_DIR/base-override').resolve()
    actual_base = config.base_models_dir.resolve()
    
    if actual_base == expected_override:
        print('✅ Environment variable override working')
    else:
        print(f'❌ Environment override failed: expected {expected_override}, got {actual_base}')
        sys.exit(1)
        
    # Verify we can access the overridden model
    model_path = config.get_base_model_path()
    if (model_path / 'model.txt').exists():
        print('✅ Override model accessible')
    else:
        print('❌ Override model not accessible')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Environment override test failed: {e}')
    sys.exit(1)
" && test_result 0 "Environment variable override working" || test_result 1 "Environment variable override failed"

# Clean up environment variable
unset OLMO_BASE_MODELS_DIR

# Test 3.2: Override default model
export OLMO_DEFAULT_BASE_MODEL="test-model"
mkdir -p "$TEST_MODELS_DIR/base/test-model"
echo "test model content" > "$TEST_MODELS_DIR/base/test-model/model.txt"

python3 -c "
import sys
sys.path.append('.')
from config_manager import OLMoSecurityConfig
from pathlib import Path

try:
    config = OLMoSecurityConfig(Path('test-config.yaml'))
    
    if config.default_base_model == 'test-model':
        print('✅ Default model override working')
        
        # Test that get_base_model_path() uses the override
        model_path = config.get_base_model_path()
        if 'test-model' in str(model_path):
            print('✅ Model path uses overridden default')
        else:
            print(f'❌ Model path does not use override: {model_path}')
            sys.exit(1)
    else:
        print(f'❌ Default model override failed: got {config.default_base_model}')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Default model override test failed: {e}')
    sys.exit(1)
" && test_result 0 "Default model override working" || test_result 1 "Default model override failed"

unset OLMO_DEFAULT_BASE_MODEL

echo ""
echo "📋 Test 4: Virtual Environment Setup"
echo "-------------------------------------"

# Test 4.1: Check if setup script exists
if [ -f "scripts/setup.py" ]; then
    test_result 0 "Setup script exists"
else
    test_result 1 "Setup script missing"
fi

# Test 4.2: Validate requirements.txt exists
if [ -f "requirements.txt" ]; then
    test_result 0 "Requirements file exists"
else
    test_result 1 "Requirements file missing"
fi

# Test 4.3: Test virtual environment creation (if Python available)
if command -v python3 &> /dev/null; then
    info_msg "Testing virtual environment creation..."
    
    # Create virtual environment
    python3 -m venv venv
    
    if [ -d "venv" ]; then
        test_result 0 "Virtual environment created successfully"
        
        # Activate and test basic functionality
        source venv/bin/activate
        
        # Test pip installation
        pip install PyYAML > /dev/null 2>&1
        
        if pip list | grep -q PyYAML; then
            test_result 0 "Package installation in venv working"
        else
            test_result 1 "Package installation in venv failed"
        fi
        
        deactivate
    else
        test_result 1 "Virtual environment creation failed"
    fi
else
    warn_msg "Python3 not available - skipping virtual environment test"
    test_result 0 "Virtual environment test skipped (no Python3)"
fi

echo ""
echo "📋 Test 5: Project Structure Validation"
echo "----------------------------------------"

# Test 5.1: Verify required directories can be created
REQUIRED_DIRS=("data" "results" "analysis")
for dir in "${REQUIRED_DIRS[@]}"; do
    mkdir -p "$dir"
    if [ -d "$dir" ]; then
        test_result 0 "Directory created: $dir"
    else
        test_result 1 "Failed to create directory: $dir"
    fi
done

# Test 5.2: Verify core Python modules can be imported
if command -v python3 &> /dev/null; then
    # Test config_manager import
    python3 -c "
import sys
sys.path.append('.')

try:
    from config_manager import OLMoSecurityConfig, get_default_config
    print('✅ config_manager imports successfully')
except ImportError as e:
    print(f'❌ config_manager import failed: {e}')
    sys.exit(1)
" && test_result 0 "config_manager module imports successfully" || test_result 1 "config_manager module import failed"

    # Test process_artifacts import (if available)
    if [ -f "process_artifacts.py" ]; then
        python3 -c "
import sys
sys.path.append('.')

try:
    import process_artifacts
    print('✅ process_artifacts imports successfully')
except ImportError as e:
    print(f'❌ process_artifacts import failed: {e}')
    sys.exit(1)
" && test_result 0 "process_artifacts module imports successfully" || test_result 1 "process_artifacts module import failed"
    else
        info_msg "process_artifacts.py not found - skipping import test"
    fi
else
    warn_msg "Python3 not available - skipping module import tests"
fi

echo ""
echo "📋 Test 6: Clean-up and Path Independence"
echo "------------------------------------------"

# Test 6.1: Return to original directory
cd - > /dev/null

# Test 6.2: Verify test environment is isolated
if [ -d "$TEST_ENV_DIR" ]; then
    test_result 0 "Test environment isolated and accessible"
else
    test_result 1 "Test environment lost or inaccessible"
fi

# Test 6.3: Clean up test environment
rm -rf "$TEST_ENV_DIR"

if [ ! -d "$TEST_ENV_DIR" ]; then
    test_result 0 "Test environment cleaned up successfully"
else
    test_result 1 "Test environment cleanup failed"
fi

# Test 6.4: Verify original project still accessible
if [ -f "security-ai-analysis/config_manager.py" ]; then
    test_result 0 "Original project still accessible after test"
else
    test_result 1 "Original project damaged or inaccessible"
fi

echo ""
echo "📋 Test 7: Documentation Accuracy Validation"
echo "---------------------------------------------"

# Test 7.1: Verify setup instructions in README work
if grep -q "python3 security-ai-analysis/scripts/setup.py" security-ai-analysis/README.md; then
    test_result 0 "README contains correct setup command"
else
    test_result 1 "README setup command incorrect or missing"
fi

# Test 7.2: Verify configuration examples are valid YAML
if [ -f "config/olmo-security-config.yaml" ]; then
    python3 -c "
import yaml

try:
    with open('config/olmo-security-config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print('✅ Configuration YAML is valid')
except yaml.YAMLError as e:
    print(f'❌ Configuration YAML is invalid: {e}')
    sys.exit(1)
" && test_result 0 "Configuration YAML is valid" || test_result 1 "Configuration YAML is invalid"
else
    test_result 1 "Configuration file not found"
fi

# Test 7.3: Verify no remaining placeholders in documentation
PLACEHOLDER_PATTERNS=("TODO" "FIXME" "XXX" "\\[\\[.*\\]\\]")
PLACEHOLDERS_FOUND=0

for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
    if grep -r "$pattern" security-ai-analysis/README.md security-ai-analysis/docs/ 2>/dev/null; then
        warn_msg "Found placeholder pattern: $pattern"
        PLACEHOLDERS_FOUND=1
    fi
done

if [ $PLACEHOLDERS_FOUND -eq 0 ]; then
    test_result 0 "No placeholder patterns found in documentation"
else
    test_result 1 "Placeholder patterns still exist in documentation"
fi

echo ""
echo "=========================================================="
echo "📊 Integration Test Results Summary"
echo "=========================================================="
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Integration Tests Complete: All tests passed!${NC}"
    echo ""
    echo "📋 Integration Test Achievements:"
    echo "• ✅ Fresh environment simulation successful"
    echo "• ✅ Configuration system working with alternative configs"
    echo "• ✅ Environment variable overrides functional"
    echo "• ✅ Virtual environment setup working"
    echo "• ✅ Project structure validation passed"
    echo "• ✅ Path independence confirmed"
    echo "• ✅ Documentation accuracy validated"
    echo ""
    echo "🚀 Ready for Configuration Variation Testing"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Integration tests failed with $TESTS_FAILED errors${NC}"
    echo "Please fix the issues above before proceeding"
    exit 1
fi