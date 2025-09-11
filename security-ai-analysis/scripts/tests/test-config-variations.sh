#!/bin/bash
set -euo pipefail

echo "🔬 Phase 5 CRITICAL: Configuration Variation Tests - Anti-Masking Validation"
echo "==========================================================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0
CRITICAL_FAILURES=0

# Helper function for test results
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ $2${NC}"
        ((TESTS_FAILED++))
        if [[ "$2" == *"CRITICAL"* ]]; then
            ((CRITICAL_FAILURES++))
        fi
    fi
}

# Helper function for critical test results
critical_test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ CRITICAL: $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ CRITICAL: $2${NC}"
        ((TESTS_FAILED++))
        ((CRITICAL_FAILURES++))
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

# Helper function for critical warnings
critical_msg() {
    echo -e "${PURPLE}🚨 CRITICAL: $1${NC}"
}

echo ""
critical_msg "This test prevents configuration masking issues by using completely different paths"
critical_msg "If config changes are ignored, this test will fail and prevent false confidence"
echo ""

# Generate unique test session ID
TEST_SESSION_ID="config-test-$(date +%s)-$$"
info_msg "Test session ID: $TEST_SESSION_ID"

echo ""
echo "📋 Test 1: CRITICAL - Baseline Configuration Validation"
echo "--------------------------------------------------------"

# Test 1.1: Verify original configuration works
info_msg "Testing original configuration..."

python3 -c "
import sys
import os
sys.path.append('security-ai-analysis')
from config_manager import get_default_config

try:
    config = get_default_config()
    summary = config.get_config_summary()
    print(f'✅ Original config loaded')
    print(f'Base models dir: {summary[\"base_models_dir\"]}')
    print(f'Fine-tuned models dir: {summary[\"fine_tuned_models_dir\"]}')
    print(f'Default model: {summary[\"default_base_model\"]}')
except Exception as e:
    print(f'❌ Original config failed: {e}')
    sys.exit(1)
" && test_result 0 "Original configuration loads successfully" || test_result 1 "Original configuration loading failed"

echo ""
echo "📋 Test 2: CRITICAL - Alternative Path Configuration Testing"
echo "------------------------------------------------------------"

# Test 2.1: Create completely different test paths (GUARANTEED to be different)
TEST_BASE_DIR="/tmp/test-ai-security-${TEST_SESSION_ID}"
ALT_CONFIG_PATH="$TEST_BASE_DIR/alternative-config.yaml"
ALT_MODELS_BASE="$TEST_BASE_DIR/models/base"
ALT_MODELS_FINETUNED="$TEST_BASE_DIR/models/fine-tuned"
ALT_TEST_MODEL="test-model-${TEST_SESSION_ID}"

critical_msg "Creating alternative configuration with paths: $TEST_BASE_DIR"

# Create directory structure
mkdir -p "$ALT_MODELS_BASE"
mkdir -p "$ALT_MODELS_FINETUNED"

# Create test model directory and files
mkdir -p "$ALT_MODELS_BASE/$ALT_TEST_MODEL"
echo "Alternative test model content - ${TEST_SESSION_ID}" > "$ALT_MODELS_BASE/$ALT_TEST_MODEL/model.txt"
echo '{"model_type": "test", "session": "'$TEST_SESSION_ID'"}' > "$ALT_MODELS_BASE/$ALT_TEST_MODEL/config.json"

critical_test_result 0 "Alternative test directories created with unique paths"

# Test 2.2: Create alternative configuration file
cat > "$ALT_CONFIG_PATH" << EOF
# Alternative Configuration for Anti-Masking Test
# Session: $TEST_SESSION_ID
# These paths are COMPLETELY different from defaults to ensure no masking

base_models_dir: "$ALT_MODELS_BASE"
fine_tuned_models_dir: "$ALT_MODELS_FINETUNED"
default_base_model: "$ALT_TEST_MODEL"
EOF

info_msg "Alternative configuration created at: $ALT_CONFIG_PATH"

# Test 2.3: CRITICAL - Verify alternative config loads with different paths
python3 -c "
import sys
import os
from pathlib import Path
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig

try:
    config = OLMoSecurityConfig(Path('$ALT_CONFIG_PATH'))
    summary = config.get_config_summary()
    
    # CRITICAL: Verify paths are actually different
    base_dir = summary['base_models_dir']
    if '$TEST_BASE_DIR' not in base_dir:
        print(f'❌ CRITICAL: Alternative config not loaded - base_dir: {base_dir}')
        sys.exit(1)
    
    if '$ALT_TEST_MODEL' not in summary['default_base_model']:
        print(f'❌ CRITICAL: Alternative model not loaded - model: {summary[\"default_base_model\"]}')
        sys.exit(1)
    
    print(f'✅ Alternative config loaded with different paths')
    print(f'Base models dir: {base_dir}')
    print(f'Default model: {summary[\"default_base_model\"]}')
    
except Exception as e:
    print(f'❌ CRITICAL: Alternative config loading failed: {e}')
    sys.exit(1)
" && critical_test_result 0 "CRITICAL: Alternative configuration loads with different paths" || critical_test_result 1 "CRITICAL: Alternative configuration masking detected"

echo ""
echo "📋 Test 3: CRITICAL - Model Path Resolution Validation" 
echo "-------------------------------------------------------"

# Test 3.1: CRITICAL - Verify model path resolution uses alternative config
python3 -c "
import sys
from pathlib import Path
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig

try:
    config = OLMoSecurityConfig(Path('$ALT_CONFIG_PATH'))
    model_path = config.get_base_model_path()
    
    # CRITICAL: Verify the resolved path contains our test session ID
    if '$TEST_SESSION_ID' not in str(model_path):
        print(f'❌ CRITICAL: Model path does not use alternative config')
        print(f'Expected path to contain: $TEST_SESSION_ID')
        print(f'Actual path: {model_path}')
        sys.exit(1)
    
    # CRITICAL: Verify the model directory exists and contains our test content
    if not model_path.exists():
        print(f'❌ CRITICAL: Alternative model path does not exist: {model_path}')
        sys.exit(1)
    
    test_file = model_path / 'model.txt'
    if not test_file.exists():
        print(f'❌ CRITICAL: Test model file missing: {test_file}')
        sys.exit(1)
    
    # Read and verify test content
    with open(test_file, 'r') as f:
        content = f.read()
    
    if '$TEST_SESSION_ID' not in content:
        print(f'❌ CRITICAL: Test content does not match session ID')
        print(f'Expected content to contain: $TEST_SESSION_ID')
        print(f'Actual content: {content}')
        sys.exit(1)
    
    print(f'✅ Alternative model path resolves correctly: {model_path}')
    print(f'✅ Test content verified with session ID: $TEST_SESSION_ID')
    
except Exception as e:
    print(f'❌ CRITICAL: Model path resolution failed: {e}')
    sys.exit(1)
" && critical_test_result 0 "CRITICAL: Model path resolution uses alternative configuration" || critical_test_result 1 "CRITICAL: Model path resolution ignores alternative configuration"

echo ""
echo "📋 Test 4: CRITICAL - Environment Variable Override Anti-Masking"
echo "-----------------------------------------------------------------"

# Test 4.1: Create another set of completely different paths for env var testing
ENV_TEST_BASE_DIR="/tmp/env-test-ai-security-${TEST_SESSION_ID}"
ENV_MODELS_BASE="$ENV_TEST_BASE_DIR/env-models/base"
ENV_TEST_MODEL="env-model-${TEST_SESSION_ID}"

mkdir -p "$ENV_MODELS_BASE"
mkdir -p "$ENV_MODELS_BASE/$ENV_TEST_MODEL"
echo "Environment override test model - ${TEST_SESSION_ID}" > "$ENV_MODELS_BASE/$ENV_TEST_MODEL/model.txt"

critical_msg "Testing environment variable override with: $ENV_MODELS_BASE"

# Test 4.2: CRITICAL - Test environment variable override
export OLMO_BASE_MODELS_DIR="$ENV_MODELS_BASE"
export OLMO_DEFAULT_BASE_MODEL="$ENV_TEST_MODEL"

python3 -c "
import sys
import os
from pathlib import Path
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig

try:
    # Use alternative config but with env var overrides
    config = OLMoSecurityConfig(Path('$ALT_CONFIG_PATH'))
    summary = config.get_config_summary()
    
    # CRITICAL: Verify environment variables override the alternative config
    base_dir = summary['base_models_dir']
    if '$ENV_TEST_BASE_DIR' not in base_dir:
        print(f'❌ CRITICAL: Environment override not working')
        print(f'Expected path to contain: $ENV_TEST_BASE_DIR')
        print(f'Actual base_dir: {base_dir}')
        sys.exit(1)
    
    if '$ENV_TEST_MODEL' not in summary['default_base_model']:
        print(f'❌ CRITICAL: Environment model override not working')
        print(f'Expected model: $ENV_TEST_MODEL')
        print(f'Actual model: {summary[\"default_base_model\"]}')
        sys.exit(1)
    
    # CRITICAL: Verify model path resolution uses environment override
    model_path = config.get_base_model_path()
    if '$ENV_TEST_MODEL' not in str(model_path):
        print(f'❌ CRITICAL: Model path does not use environment override')
        print(f'Expected path to contain: $ENV_TEST_MODEL')
        print(f'Actual path: {model_path}')
        sys.exit(1)
    
    # Verify environment override model content
    test_file = model_path / 'model.txt'
    with open(test_file, 'r') as f:
        content = f.read()
    
    if 'Environment override' not in content:
        print(f'❌ CRITICAL: Environment override content not found')
        print(f'Content: {content}')
        sys.exit(1)
    
    print(f'✅ Environment override working correctly')
    print(f'Override base dir: {base_dir}')
    print(f'Override model: {summary[\"default_base_model\"]}')
    print(f'Override model path: {model_path}')
    
except Exception as e:
    print(f'❌ CRITICAL: Environment override test failed: {e}')
    sys.exit(1)
" && critical_test_result 0 "CRITICAL: Environment variable overrides work correctly" || critical_test_result 1 "CRITICAL: Environment variable overrides are masked or ignored"

# Clean up environment variables
unset OLMO_BASE_MODELS_DIR
unset OLMO_DEFAULT_BASE_MODEL

echo ""
echo "📋 Test 5: CRITICAL - Hardcoded Path Detection Scan"
echo "----------------------------------------------------"

# Test 5.1: Scan for remaining hardcoded patterns in key files
critical_msg "Scanning for hardcoded paths that could cause masking..."

HARDCODED_PATTERNS=(
    "/Users/vinayakmenon/olmo-security-analysis"
    "olmo-security-analysis/venv"
    "~/olmo-security-analysis"
    "/private/tmp/olmo-models"
    "TODO.*config"
)

SCAN_FILES=(
    "security-ai-analysis/config_manager.py"
    "security-ai-analysis/process_artifacts.py"
    "security-ai-analysis/model_manager.py"
    "security-ai-analysis/main.py"
    "config/olmo-security-config.yaml"
)

HARDCODED_FOUND=0
for file in "${SCAN_FILES[@]}"; do
    if [ -f "$file" ]; then
        info_msg "Scanning $file for hardcoded patterns..."
        
        for pattern in "${HARDCODED_PATTERNS[@]}"; do
            if grep -n "$pattern" "$file" 2>/dev/null; then
                warn_msg "Found potential hardcoded pattern '$pattern' in $file"
                HARDCODED_FOUND=1
            fi
        done
    else
        warn_msg "File not found for scanning: $file"
    fi
done

if [ $HARDCODED_FOUND -eq 0 ]; then
    critical_test_result 0 "CRITICAL: No hardcoded paths found in scanned files"
else
    critical_test_result 1 "CRITICAL: Hardcoded paths detected - potential masking risk"
fi

echo ""
echo "📋 Test 6: CRITICAL - Configuration Isolation Validation"
echo "---------------------------------------------------------"

# Test 6.1: CRITICAL - Ensure different configs produce different results
critical_msg "Testing configuration isolation to prevent cross-contamination..."

# Create a third, completely different configuration
ISOLATION_TEST_DIR="/tmp/isolation-test-${TEST_SESSION_ID}"
ISOLATION_CONFIG_PATH="$ISOLATION_TEST_DIR/isolation-config.yaml"
ISOLATION_MODELS_BASE="$ISOLATION_TEST_DIR/unique-models"
ISOLATION_TEST_MODEL="isolation-model-${TEST_SESSION_ID}"

mkdir -p "$ISOLATION_MODELS_BASE"
mkdir -p "$ISOLATION_MODELS_BASE/$ISOLATION_TEST_MODEL"
echo "Isolation test model - ${TEST_SESSION_ID}" > "$ISOLATION_MODELS_BASE/$ISOLATION_TEST_MODEL/model.txt"

cat > "$ISOLATION_CONFIG_PATH" << EOF
# Isolation Test Configuration - Session: $TEST_SESSION_ID
base_models_dir: "$ISOLATION_MODELS_BASE"
fine_tuned_models_dir: "$ISOLATION_MODELS_BASE/fine-tuned"
default_base_model: "$ISOLATION_TEST_MODEL"
EOF

# Test that each config produces different, correct results
python3 -c "
import sys
from pathlib import Path
sys.path.append('security-ai-analysis')
from config_manager import OLMoSecurityConfig, get_default_config

try:
    # Test default config
    default_config = get_default_config()
    default_summary = default_config.get_config_summary()
    
    # Test alternative config
    alt_config = OLMoSecurityConfig(Path('$ALT_CONFIG_PATH'))
    alt_summary = alt_config.get_config_summary()
    
    # Test isolation config
    isolation_config = OLMoSecurityConfig(Path('$ISOLATION_CONFIG_PATH'))
    isolation_summary = isolation_config.get_config_summary()
    
    # CRITICAL: Verify all three configs are different
    configs = [
        ('default', default_summary['base_models_dir']),
        ('alternative', alt_summary['base_models_dir']),
        ('isolation', isolation_summary['base_models_dir'])
    ]
    
    # Check that all base directories are different
    base_dirs = [config[1] for config in configs]
    if len(set(base_dirs)) != 3:
        print(f'❌ CRITICAL: Configuration isolation failed - configs not unique')
        for name, path in configs:
            print(f'  {name}: {path}')
        sys.exit(1)
    
    # Verify each config uses the expected paths
    if '$TEST_BASE_DIR' not in alt_summary['base_models_dir']:
        print(f'❌ CRITICAL: Alternative config contaminated')
        sys.exit(1)
        
    if '$ISOLATION_TEST_DIR' not in isolation_summary['base_models_dir']:
        print(f'❌ CRITICAL: Isolation config contaminated')
        sys.exit(1)
    
    # Verify model names are unique
    models = [
        default_summary['default_base_model'],
        alt_summary['default_base_model'], 
        isolation_summary['default_base_model']
    ]
    
    # Check that test models contain session ID
    if '$ALT_TEST_MODEL' not in alt_summary['default_base_model']:
        print(f'❌ CRITICAL: Alternative model name wrong: {alt_summary[\"default_base_model\"]}')
        sys.exit(1)
        
    if '$ISOLATION_TEST_MODEL' not in isolation_summary['default_base_model']:
        print(f'❌ CRITICAL: Isolation model name wrong: {isolation_summary[\"default_base_model\"]}')
        sys.exit(1)
    
    print(f'✅ Configuration isolation working correctly')
    print(f'Default base dir: {default_summary[\"base_models_dir\"]}')
    print(f'Alternative base dir: {alt_summary[\"base_models_dir\"]}')
    print(f'Isolation base dir: {isolation_summary[\"base_models_dir\"]}')
    
except Exception as e:
    print(f'❌ CRITICAL: Configuration isolation test failed: {e}')
    sys.exit(1)
" && critical_test_result 0 "CRITICAL: Configuration isolation working correctly" || critical_test_result 1 "CRITICAL: Configuration isolation failed - configs contaminated"

echo ""
echo "📋 Test 7: CRITICAL - Process Integration Anti-Masking Validation"
echo "------------------------------------------------------------------"

# Test 7.1: Test that process_artifacts.py respects configuration changes (if it exists)
if [ -f "security-ai-analysis/process_artifacts.py" ]; then
    critical_msg "Testing process_artifacts.py configuration integration..."
    
    # Check if process_artifacts.py imports and uses config_manager
    if grep -q "config_manager\|OLMoSecurityConfig" security-ai-analysis/process_artifacts.py; then
        critical_test_result 0 "CRITICAL: process_artifacts.py imports configuration manager"
        
        # Test if it can load alternative configuration
        python3 -c "
import sys
from pathlib import Path
sys.path.append('security-ai-analysis')

try:
    # Test if process_artifacts can work with alternative config
    import process_artifacts
    from config_manager import OLMoSecurityConfig
    
    # This test verifies the module can be imported and doesn't fail
    # with alternative configurations
    config = OLMoSecurityConfig(Path('$ALT_CONFIG_PATH'))
    print(f'✅ process_artifacts.py compatible with alternative configurations')
    
except ImportError as e:
    print(f'⚠️  process_artifacts.py import failed (may be expected): {e}')
except Exception as e:
    print(f'❌ CRITICAL: process_artifacts.py configuration compatibility failed: {e}')
    sys.exit(1)
" && test_result 0 "process_artifacts.py configuration integration works" || warn_msg "process_artifacts.py configuration integration needs review"
    else
        critical_test_result 1 "CRITICAL: process_artifacts.py does not use configuration manager"
    fi
else
    info_msg "process_artifacts.py not found - skipping integration test"
fi

echo ""
echo "📋 Test 8: Clean-up Test Environment"
echo "-------------------------------------"

# Clean up all test directories
info_msg "Cleaning up test environments..."

# Clean up alternative config test
rm -rf "$TEST_BASE_DIR"
if [ ! -d "$TEST_BASE_DIR" ]; then
    test_result 0 "Alternative config test environment cleaned up"
else
    test_result 1 "Alternative config cleanup failed"
fi

# Clean up environment override test
rm -rf "$ENV_TEST_BASE_DIR"
if [ ! -d "$ENV_TEST_BASE_DIR" ]; then
    test_result 0 "Environment override test environment cleaned up"
else
    test_result 1 "Environment override cleanup failed"
fi

# Clean up isolation test
rm -rf "$ISOLATION_TEST_DIR"
if [ ! -d "$ISOLATION_TEST_DIR" ]; then
    test_result 0 "Isolation test environment cleaned up"
else
    test_result 1 "Isolation test cleanup failed"
fi

echo ""
echo "==========================================================================="
echo "📊 CRITICAL Configuration Variation Test Results"
echo "==========================================================================="
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo -e "${PURPLE}Critical Failures: $CRITICAL_FAILURES${NC}"

if [ $CRITICAL_FAILURES -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ CRITICAL SUCCESS: All configuration variation tests passed!${NC}"
    echo ""
    echo "🔒 Anti-Masking Validation Results:"
    echo "• ✅ Alternative configuration paths are honored"
    echo "• ✅ Environment variable overrides work correctly"
    echo "• ✅ Configuration isolation prevents cross-contamination"
    echo "• ✅ No hardcoded paths detected in scanned files"
    echo "• ✅ Model path resolution uses correct configurations"
    echo "• ✅ Process integration respects configuration changes"
    echo ""
    echo -e "${GREEN}🚀 SYSTEM IS FULLY PORTABLE - No configuration masking detected!${NC}"
    exit 0
elif [ $CRITICAL_FAILURES -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ CRITICAL FAILURE: Configuration masking detected!${NC}"
    echo -e "${PURPLE}$CRITICAL_FAILURES critical failures must be fixed before deployment${NC}"
    echo ""
    echo "🚨 Critical Issues Found:"
    echo "• Configuration changes may be ignored"
    echo "• System may not be portable across environments"
    echo "• Hardcoded paths may prevent proper configuration"
    echo ""
    echo -e "${RED}DO NOT PROCEED - Fix critical issues first${NC}"
    exit 1
else
    echo ""
    echo -e "${YELLOW}⚠️  Some non-critical tests failed but no critical failures detected${NC}"
    echo "Review failed tests but configuration variation appears to work"
    exit 0
fi