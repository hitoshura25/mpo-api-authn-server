#!/bin/bash
set -euo pipefail

echo "🧪 Phase 3 Simple Validation Tests"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"

# Test 1: Configuration import
echo "Test 1: Configuration import"
/Users/vinayakmenon/mpo-api-authn-server/security-ai-analysis/venv/bin/python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/security-ai-analysis')

from config_manager import OLMoSecurityConfig
config = OLMoSecurityConfig()
print(f'✅ Config loaded: {config.default_base_model}')
"

# Test 2: Daemon import
echo "Test 2: Daemon import"
/Users/vinayakmenon/mpo-api-authn-server/security-ai-analysis/venv/bin/python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/security-ai-analysis')
sys.path.append('$PROJECT_ROOT/local-analysis')

from security_artifact_daemon import SecurityArtifactDaemon
daemon = SecurityArtifactDaemon()
print(f'✅ Daemon created with data_dir: {daemon.data_dir}')
print(f'✅ Analysis dir: {daemon.analysis_dir}')
"

# Test 3: Template exists
echo "Test 3: Template exists"
if [[ -f "$PROJECT_ROOT/security-ai-analysis/templates/daemon.plist.template" ]]; then
    echo "✅ LaunchAgent template exists"
else
    echo "❌ LaunchAgent template missing"
fi

echo "✅ Simple tests completed"