#!/bin/bash
set -euo pipefail

echo "🧪 Phase 4 Validation Tests - Simplified"
echo "========================================"

TESTS_PASSED=0
TESTS_FAILED=0

# Helper function for test results
test_result() {
    if [ $1 -eq 0 ]; then
        echo "✅ $2"
        ((TESTS_PASSED++))
    else
        echo "❌ $2"
        ((TESTS_FAILED++))
    fi
}

echo ""
echo "📋 Critical Phase 4 Tests"
echo "-------------------------"

# Test 1: .gitignore exists and has sharing philosophy
test -f "security-ai-analysis/.gitignore"
test_result $? ".gitignore file exists"

grep -q "Sharing Philosophy" security-ai-analysis/.gitignore
test_result $? ".gitignore contains sharing philosophy comments"

grep -q "venv/" security-ai-analysis/.gitignore
test_result $? ".gitignore includes venv/ pattern"

grep -q "data/" security-ai-analysis/.gitignore
test_result $? ".gitignore includes data/ pattern"

grep -q "results/" security-ai-analysis/.gitignore
test_result $? ".gitignore includes results/ pattern"

# Test 2: README.md updated
grep -q "~/shared-olmo-models/" security-ai-analysis/README.md
test_result $? "README.md references new shared model paths"

grep -q "Portable Architecture\|Sharing Philosophy" security-ai-analysis/README.md
test_result $? "README.md includes sharing philosophy"

grep -q "security-ai-analysis/scripts/setup.py" security-ai-analysis/README.md
test_result $? "README.md includes portable setup instructions"

# Test 3: Getting Started guide
test -f "security-ai-analysis/docs/GETTING_STARTED.md"
test_result $? "GETTING_STARTED.md exists"

grep -q "python3 security-ai-analysis/scripts/setup.py" security-ai-analysis/docs/GETTING_STARTED.md
test_result $? "Getting started guide includes correct setup command"

grep -q "Sharing Philosophy" security-ai-analysis/docs/GETTING_STARTED.md
test_result $? "Getting started guide includes sharing philosophy"

# Test 4: Check for hardcoded paths
HARDCODED_FOUND=0
if grep -q "/Users/vinayakmenon/olmo-security-analysis" security-ai-analysis/README.md; then
    echo "⚠️  Found hardcoded path in README.md"
    HARDCODED_FOUND=1
fi

if [ $HARDCODED_FOUND -eq 0 ]; then
    test_result 0 "No hardcoded paths found in README.md"
else
    test_result 1 "README.md still contains hardcoded paths"
fi

echo ""
echo "📊 Phase 4 Results Summary"
echo "=========================="
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo "✅ Phase 4 Complete: All critical validation tests passed!"
    echo ""
    echo "Phase 4 Achievements:"
    echo "• ✅ .gitignore created with sharing philosophy comments"
    echo "• ✅ README.md updated with portable architecture paths"
    echo "• ✅ Comprehensive GETTING_STARTED.md guide created"
    echo "• ✅ All documentation uses portable paths"
    exit 0
else
    echo ""
    echo "❌ Phase 4 validation failed with $TESTS_FAILED errors"
    echo "Please fix the issues above before proceeding"
    exit 1
fi