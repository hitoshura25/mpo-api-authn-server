#!/bin/bash
# Run script for processing security artifacts with OLMo

echo "🚀 WebAuthn Security Analysis with OLMo"
echo "========================================"

# Activate virtual environment
if [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Check if artifacts directory exists
ARTIFACTS_DIR="data/security_artifacts"

if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo ""
    echo "📦 Please place your downloaded GitHub Actions artifacts in:"
    echo "   $ARTIFACTS_DIR"
    echo ""
    echo "You can download them from:"
    echo "https://github.com/hitoshura25/mpo-api-authn-server/actions"
    echo ""
    echo "Or use GitHub CLI:"
    echo "gh run list --repo hitoshura25/mpo-api-authn-server"
    echo "gh run download <RUN_ID> -D $ARTIFACTS_DIR"
    echo ""
    mkdir -p "$ARTIFACTS_DIR"
    exit 1
fi

# Process the artifacts
echo ""
echo "🔍 Processing security artifacts..."
python process_artifacts.py "$ARTIFACTS_DIR"

echo ""
echo "✅ Done! Check data/olmo_analysis_results/ for results"
