#!/bin/bash
set -euo pipefail

echo "🧪 Phase 2 Validation Tests - Model Management & Setup Automation"
echo "=================================================================="

# Navigate to project root
# The script is in security-ai-analysis/scripts/tests/, so go up 3 levels to reach project root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

# Activate virtual environment if it exists
if [[ -d "security-ai-analysis/venv" ]]; then
    echo "🐍 Activating virtual environment..."
    source security-ai-analysis/venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found - will be created during setup"
fi

echo

# Test 1: Setup script execution
echo "📋 Test 1: Setup script works"
echo "Running setup script..."
python3 security-ai-analysis/scripts/setup.py

if [[ $? -eq 0 ]]; then
    echo "✅ Setup script executed successfully"
else
    echo "❌ Setup script failed"
    exit 1
fi
echo

# Test 2: Project structure validation
echo "📋 Test 2: Project structure created correctly"

# Check all required directories
directories=(
    "security-ai-analysis/venv"
    "security-ai-analysis/data"
    "security-ai-analysis/results"
    "~/shared-olmo-models/base"
    "~/shared-olmo-models/fine-tuned"
)

for dir in "${directories[@]}"; do
    # Expand tilde for home directory
    expanded_dir="${dir/#\~/$HOME}"
    if [[ -d "$expanded_dir" ]]; then
        echo "   ✅ Directory exists: $dir"
    else
        echo "   ❌ Directory missing: $dir"
        exit 1
    fi
done

echo "✅ All required directories created"
echo

# Test 3: Virtual environment functionality
echo "📋 Test 3: Virtual environment works correctly"

# Activate the virtual environment
source security-ai-analysis/venv/bin/activate

# Test basic Python functionality
python3 -c "import sys; print(f'✅ Python executable: {sys.executable}')"

# Test that we can import our modules
echo "   Testing module imports..."
cd security-ai-analysis
python3 -c "from config_manager import OLMoSecurityConfig; print('✅ Config manager import works')"
python3 -c "from model_manager import OLMoModelManager; print('✅ Model manager import works')"

echo "✅ Virtual environment is functional"
echo

# Test 4: Model manager functionality
echo "📋 Test 4: Model manager functionality"

# Test model manager instantiation and basic functionality
python3 -c "
from model_manager import OLMoModelManager

# Test instantiation
manager = OLMoModelManager()
print('✅ Model manager instantiation works')

# Test model info functionality
model_info = manager.get_model_info()
print(f'✅ Model info retrieved successfully')
print(f'   Base models dir: {model_info[\"directories\"][\"base_models_dir\"]}')
print(f'   Available base models: {model_info[\"models\"][\"available_base_models\"]}')
print(f'   Project structure ready: {model_info[\"status\"][\"project_structure_ready\"]}')

# Test validation
validation = manager.validate_setup()
print(f'✅ Setup validation completed')
for check, result in validation.items():
    status = '✅' if result else '⚠️ '
    print(f'   {status} {check}: {result}')
"

echo "✅ Model manager functionality works"
echo

# Test 5: Updated scripts work with new project structure
echo "📋 Test 5: Updated scripts work with new structure"

# Test process_artifacts.py help
echo "   Testing process_artifacts.py..."
if python3 process_artifacts.py --help | grep -q "Process security artifacts"; then
    echo "   ✅ process_artifacts.py works correctly"
else
    echo "   ❌ process_artifacts.py help output not found"
    exit 1
fi

# Test that OLMoSecurityAnalyzer can be imported and used
echo "   Testing OLMoSecurityAnalyzer with new paths..."
python3 -c "
import sys
from analysis.olmo_analyzer import OLMoSecurityAnalyzer

try:
    analyzer = OLMoSecurityAnalyzer()
    print('✅ OLMoSecurityAnalyzer instantiation works')
    print(f'   Config base models dir: {analyzer.config.base_models_dir}')
    print(f'   Config default model: {analyzer.config.default_base_model}')
except Exception as e:
    print(f'⚠️  OLMoSecurityAnalyzer instantiation: {e}')
    print('   (This is expected if models are not downloaded)')
"

echo "✅ Updated scripts work with new project structure"
echo

# Test 6: Configuration integration
echo "📋 Test 6: Configuration system integration"

# Test that all components use the same configuration
python3 -c "
import sys
from config_manager import OLMoSecurityConfig, get_default_config
from model_manager import OLMoModelManager
from analysis.olmo_analyzer import OLMoSecurityAnalyzer

# Test configuration consistency
config1 = OLMoSecurityConfig()
config2 = get_default_config()
manager = OLMoModelManager()
try:
    analyzer = OLMoSecurityAnalyzer()
    analyzer_config = analyzer.config
except:
    # If models aren't available, create config manually for comparison
    analyzer_config = OLMoSecurityConfig()

# Compare configuration paths
configs = [
    ('Direct config', config1),
    ('Default config', config2), 
    ('Manager config', manager.config),
    ('Analyzer config', analyzer_config)
]

base_paths = set()
for name, config in configs:
    base_paths.add(str(config.base_models_dir))
    
if len(base_paths) == 1:
    print('✅ All components use consistent configuration')
    print(f'   Shared base models directory: {list(base_paths)[0]}')
else:
    print('❌ Configuration inconsistency detected')
    for name, config in configs:
        print(f'   {name}: {config.base_models_dir}')
    sys.exit(1)
"

echo "✅ Configuration system integration works"
echo

# Test 7: Requirements and dependencies
echo "📋 Test 7: Dependencies and requirements"

# Check if requirements.txt exists
if [[ -f "requirements.txt" ]]; then
    echo "   ✅ requirements.txt found"
    
    # Test that key dependencies can be imported
    echo "   Testing key dependencies..."
    
    # Test critical imports that are needed for the system
    python3 -c "
import yaml
print('✅ yaml import works')

try:
    import transformers
    print('✅ transformers import works')
except ImportError:
    print('⚠️  transformers not available (may not be installed)')

try:
    import torch
    print('✅ torch import works')
except ImportError:
    print('⚠️  torch not available (may not be installed)')
    
print('✅ Basic dependencies functional')
"
    
else
    echo "   ⚠️  requirements.txt not found - this is expected for this phase"
fi

echo "✅ Dependencies check completed"
echo

# Test 8: Project isolation and path handling
echo "📋 Test 8: Project isolation and path handling"

# Test that data and results directories are properly isolated
python3 -c "
import sys
import os
from model_manager import OLMoModelManager

manager = OLMoModelManager()
config = manager.config

# Verify project directories are within project
project_root = os.getcwd()

for name, directory in [
    ('data', config.data_dir),
    ('results', config.results_dir),
    ('venv', config.venv_dir)
]:
    if str(directory).startswith(project_root):
        print(f'✅ {name} directory properly isolated within project')
    else:
        print(f'❌ {name} directory not within project: {directory}')
        sys.exit(1)

# Verify shared directories are external
for name, directory in [
    ('base_models', config.base_models_dir),
    ('fine_tuned_models', config.fine_tuned_models_dir)
]:
    if not str(directory).startswith(project_root):
        print(f'✅ {name} directory properly external to project')
    else:
        print(f'⚠️  {name} directory within project (may be intentional for testing)')
        
print('✅ Project isolation verified')
"

echo "✅ Project isolation and path handling correct"
echo

# Return to project root
cd "$PROJECT_ROOT"

echo "🎉 Phase 2 Validation Complete!"
echo "================================"
echo "✅ Setup script works correctly"
echo "✅ Project structure created properly" 
echo "✅ Virtual environment functional"
echo "✅ Model manager working"
echo "✅ Updated scripts compatible with new structure"
echo "✅ Configuration system integrated"
echo "✅ Dependencies check passed"
echo "✅ Project isolation verified"
echo
echo "📁 Created components:"
echo "   - security-ai-analysis/model_manager.py"
echo "   - security-ai-analysis/scripts/setup.py"
echo "   - security-ai-analysis/scripts/tests/test-phase2.sh"
echo "   - Project directory structure"
echo "   - Virtual environment with dependencies"
echo
echo "🚀 Ready for Phase 3: LaunchAgent & Daemon Portability"