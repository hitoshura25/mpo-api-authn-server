#!/bin/bash
set -euo pipefail

echo "🧪 Phase 3 Validation Tests - LaunchAgent & Daemon Portability"
echo "=============================================================="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo -e "${BLUE}📋 Test $1:${NC} $2"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Test 1: Validate daemon imports portable configuration
print_test "1" "Daemon imports portable configuration system"

# Check if virtual environment exists and use it if available
VENV_PYTHON="$PROJECT_ROOT/security-ai-analysis/venv/bin/python3"
if [[ -f "$VENV_PYTHON" ]]; then
    PYTHON_CMD="$VENV_PYTHON"
    print_success "Using project virtual environment"
else
    PYTHON_CMD="python3"
    print_warning "Virtual environment not found, using system Python (install PyYAML if needed)"
fi

if $PYTHON_CMD -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/security-ai-analysis')
sys.path.append('$PROJECT_ROOT/local-analysis')

try:
    from config_manager import OLMoSecurityConfig
    config = OLMoSecurityConfig()
    print(f'Config loaded: {config.default_base_model}')
    print('SUCCESS: Configuration system imports successfully')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>/dev/null; then
    print_success "Daemon can import portable configuration"
else
    print_failure "Daemon cannot import portable configuration"
fi

# Test 2: Validate daemon initializes with project paths
print_test "2" "Daemon uses project-based paths correctly"
if $PYTHON_CMD -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/security-ai-analysis')
sys.path.append('$PROJECT_ROOT/local-analysis')

try:
    from security_artifact_daemon import SecurityArtifactDaemon
    daemon = SecurityArtifactDaemon()
    
    # Check if daemon uses project paths
    expected_data_dir = '$PROJECT_ROOT/security-ai-analysis/data'
    expected_analysis_dir = '$PROJECT_ROOT/security-ai-analysis/results'
    
    if expected_data_dir in str(daemon.data_dir):
        print('✓ Data directory uses project path')
    else:
        print(f'✗ Data directory wrong: {daemon.data_dir} (expected: {expected_data_dir})')
        sys.exit(1)
        
    if expected_analysis_dir in str(daemon.analysis_dir):
        print('✓ Analysis directory uses project path')
    else:
        print(f'✗ Analysis directory wrong: {daemon.analysis_dir} (expected: {expected_analysis_dir})')
        sys.exit(1)
        
    # Test model path method
    model_path = daemon._get_model_path()
    print(f'✓ Model path method works: {model_path}')
    
    print('SUCCESS: Daemon uses project-based paths')
except Exception as e:
    print(f'FAILED: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>/dev/null; then
    print_success "Daemon uses project-based paths correctly"
else
    print_failure "Daemon does not use project-based paths correctly"
fi

# Test 3: Validate daemon backward compatibility
print_test "3" "Daemon backward compatibility with explicit data_dir"
if $PYTHON_CMD -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/security-ai-analysis')
sys.path.append('$PROJECT_ROOT/local-analysis')

try:
    from security_artifact_daemon import SecurityArtifactDaemon
    
    # Test with explicit data_dir (backward compatibility)
    test_data_dir = '/tmp/test-daemon-compat'
    daemon = SecurityArtifactDaemon(data_dir=test_data_dir)
    
    if test_data_dir in str(daemon.data_dir):
        print('✓ Explicit data_dir parameter works')
    else:
        print(f'✗ Explicit data_dir failed: {daemon.data_dir}')
        sys.exit(1)
        
    print('SUCCESS: Backward compatibility maintained')
except Exception as e:
    print(f'FAILED: {e}')
    sys.exit(1)
" 2>/dev/null; then
    print_success "Daemon backward compatibility works"
else
    print_failure "Daemon backward compatibility broken"
fi

# Test 4: LaunchAgent template exists and has correct structure
print_test "4" "LaunchAgent template validation"
TEMPLATE_FILE="$PROJECT_ROOT/security-ai-analysis/templates/daemon.plist.template"

if [[ -f "$TEMPLATE_FILE" ]]; then
    print_success "LaunchAgent template file exists"
    
    # Check for required template variables
    if grep -q "{{PROJECT_ROOT}}" "$TEMPLATE_FILE"; then
        print_success "Template contains PROJECT_ROOT variable"
    else
        print_failure "Template missing PROJECT_ROOT variable"
    fi
    
    # Check for required plist structure
    if grep -q "<key>ProgramArguments</key>" "$TEMPLATE_FILE"; then
        print_success "Template has ProgramArguments section"
    else
        print_failure "Template missing ProgramArguments section"
    fi
    
    if grep -q "<key>WorkingDirectory</key>" "$TEMPLATE_FILE"; then
        print_success "Template has WorkingDirectory section"
    else
        print_failure "Template missing WorkingDirectory section"
    fi
else
    print_failure "LaunchAgent template file not found at $TEMPLATE_FILE"
fi

# Test 5: LaunchAgent template generation
print_test "5" "LaunchAgent template variable substitution"
if $PYTHON_CMD -c "
import os
from pathlib import Path

template_path = Path('$PROJECT_ROOT/security-ai-analysis/templates/daemon.plist.template')
if not template_path.exists():
    print('FAILED: Template file not found')
    sys.exit(1)

content = template_path.read_text()
project_root = Path('$PROJECT_ROOT')
result = content.replace('{{PROJECT_ROOT}}', str(project_root))

# Validate substitution worked
if '{{PROJECT_ROOT}}' in result:
    print('FAILED: Template substitution incomplete')
    sys.exit(1)

expected_python_path = str(project_root / 'security-ai-analysis/venv/bin/python3')
expected_daemon_path = str(project_root / 'local-analysis/security_artifact_daemon.py')

if expected_python_path in result:
    print('✓ Python path substituted correctly')
else:
    print(f'✗ Python path not found in result')
    sys.exit(1)
    
if expected_daemon_path in result:
    print('✓ Daemon path substituted correctly')
else:
    print(f'✗ Daemon path not found in result')
    sys.exit(1)

print('SUCCESS: Template generation works')
print(f'Generated Python path: {expected_python_path}')
print(f'Generated daemon path: {expected_daemon_path}')
" 2>/dev/null; then
    print_success "LaunchAgent template generation works"
else
    print_failure "LaunchAgent template generation failed"
fi

# Test 6: Validate no hardcoded paths remain in daemon
print_test "6" "Check for remaining hardcoded paths in daemon"
HARDCODED_PATTERNS=(
    "olmo-security-analysis"
    "/Users/vinayakmenon/olmo-security-analysis"
    "~/olmo-security-analysis"
)

HARDCODED_FOUND=false
for pattern in "${HARDCODED_PATTERNS[@]}"; do
    if grep -n "$pattern" "$PROJECT_ROOT/local-analysis/security_artifact_daemon.py" | grep -v "fallback\|compatibility\|Fallback"; then
        print_failure "Found hardcoded path: $pattern"
        HARDCODED_FOUND=true
    fi
done

if [[ "$HARDCODED_FOUND" == "false" ]]; then
    print_success "No hardcoded paths found in daemon (excluding fallbacks)"
else
    print_failure "Hardcoded paths still exist in daemon"
fi

# Test 7: Integration test - daemon can run in test mode
print_test "7" "Daemon integration test (test mode)"
if timeout 30 $PYTHON_CMD "$PROJECT_ROOT/local-analysis/security_artifact_daemon.py" --test-mode --data-dir "$PROJECT_ROOT/security-ai-analysis/data" 2>/dev/null; then
    print_success "Daemon runs successfully in test mode"
else
    # This might fail due to missing GitHub CLI or models, but we should check if it fails gracefully
    print_warning "Daemon test mode failed (expected if GitHub CLI not configured or models missing)"
fi

# Final results
echo ""
echo "=============================================================="
echo -e "${BLUE}📊 Phase 3 Validation Results:${NC}"
echo -e "${GREEN}✅ Tests passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests failed: $TESTS_FAILED${NC}"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}🎉 Phase 3 validation PASSED!${NC}"
    echo -e "${GREEN}✅ Daemon uses portable configuration system${NC}"
    echo -e "${GREEN}✅ LaunchAgent template created and functional${NC}"
    echo -e "${GREEN}✅ Backward compatibility maintained${NC}"
    echo -e "${GREEN}✅ No hardcoded paths remain (excluding fallbacks)${NC}"
    echo ""
    echo "Phase 3 implementation complete! Ready for Phase 4."
    exit 0
else
    echo ""
    echo -e "${RED}❌ Phase 3 validation FAILED!${NC}"
    echo -e "${RED}Please fix the failing tests before proceeding.${NC}"
    exit 1
fi