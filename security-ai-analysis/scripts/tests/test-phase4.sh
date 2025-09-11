#!/bin/bash
set -euo pipefail

echo "🧪 Phase 4 Validation Tests - Documentation & .gitignore Updates"
echo "=================================================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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

echo ""
echo "📋 Test 1: .gitignore File Validation"
echo "--------------------------------------"

# Test 1.1: .gitignore exists
if [ -f "security-ai-analysis/.gitignore" ]; then
    test_result 0 ".gitignore file exists"
else
    test_result 1 ".gitignore file missing"
fi

# Test 1.2: .gitignore contains sharing philosophy comments
if grep -q "Sharing Philosophy" security-ai-analysis/.gitignore; then
    test_result 0 ".gitignore contains sharing philosophy comments"
else
    test_result 1 ".gitignore missing sharing philosophy comments"
fi

# Test 1.3: .gitignore includes required directories
REQUIRED_GITIGNORE_PATTERNS=("venv/" "data/" "results/" "__pycache__/" "*.pyc")
for pattern in "${REQUIRED_GITIGNORE_PATTERNS[@]}"; do
    if grep -q "$pattern" security-ai-analysis/.gitignore; then
        test_result 0 ".gitignore includes pattern: $pattern"
    else
        test_result 1 ".gitignore missing pattern: $pattern"
    fi
done

# Test 1.4: .gitignore explains why directories are ignored
if grep -q "project-specific" security-ai-analysis/.gitignore; then
    test_result 0 ".gitignore explains project-specific rationale"
else
    test_result 1 ".gitignore missing project-specific explanation"
fi

echo ""
echo "📋 Test 2: Documentation Updates Validation"
echo "--------------------------------------------"

# Test 2.1: README.md updated with new paths
if grep -q "~/shared-olmo-models/" security-ai-analysis/README.md; then
    test_result 0 "README.md references new shared model paths"
else
    test_result 1 "README.md missing shared model path references"
fi

# Test 2.2: README.md no longer contains hardcoded paths
HARDCODED_PATTERNS=("/Users/vinayakmenon/olmo-security-analysis" "olmo-security-analysis/venv")
HARDCODED_FOUND=0
for pattern in "${HARDCODED_PATTERNS[@]}"; do
    if grep -q "$pattern" security-ai-analysis/README.md; then
        echo -e "${YELLOW}⚠️  Found hardcoded path in README.md: $pattern${NC}"
        HARDCODED_FOUND=1
    fi
done

if [ $HARDCODED_FOUND -eq 0 ]; then
    test_result 0 "README.md contains no hardcoded paths"
else
    test_result 1 "README.md still contains hardcoded paths"
fi

# Test 2.3: README.md includes portable setup instructions
if grep -q "security-ai-analysis/scripts/setup.py" security-ai-analysis/README.md; then
    test_result 0 "README.md includes portable setup instructions"
else
    test_result 1 "README.md missing portable setup instructions"
fi

# Test 2.4: README.md includes sharing philosophy
if grep -q "Sharing Philosophy\|What Gets Shared" security-ai-analysis/README.md; then
    test_result 0 "README.md includes sharing philosophy"
else
    test_result 1 "README.md missing sharing philosophy"
fi

echo ""
echo "📋 Test 3: Getting Started Guide Validation"
echo "--------------------------------------------"

# Test 3.1: Getting started guide exists
if [ -f "security-ai-analysis/docs/GETTING_STARTED.md" ]; then
    test_result 0 "GETTING_STARTED.md exists"
else
    test_result 1 "GETTING_STARTED.md missing"
fi

# Test 3.2: Guide includes setup instructions
if grep -q "python3 security-ai-analysis/scripts/setup.py" security-ai-analysis/docs/GETTING_STARTED.md; then
    test_result 0 "Getting started guide includes correct setup command"
else
    test_result 1 "Getting started guide missing setup command"
fi

# Test 3.3: Guide includes architecture explanation
if grep -q "Sharing Philosophy\|Directory Structure" security-ai-analysis/docs/GETTING_STARTED.md; then
    test_result 0 "Getting started guide includes architecture explanation"
else
    test_result 1 "Getting started guide missing architecture explanation"
fi

# Test 3.4: Guide includes usage examples
if grep -q "Usage Examples\|process_artifacts.py" security-ai-analysis/docs/GETTING_STARTED.md; then
    test_result 0 "Getting started guide includes usage examples"
else
    test_result 1 "Getting started guide missing usage examples"
fi

# Test 3.5: Guide includes troubleshooting
if grep -q "Troubleshooting\|Common Issues" security-ai-analysis/docs/GETTING_STARTED.md; then
    test_result 0 "Getting started guide includes troubleshooting section"
else
    test_result 1 "Getting started guide missing troubleshooting section"
fi

echo ""
echo "📋 Test 4: Documentation Path Consistency"
echo "------------------------------------------"

# Test 4.1: All documentation uses consistent paths
DOCS_FILES=("security-ai-analysis/README.md" "security-ai-analysis/docs/GETTING_STARTED.md")
INCONSISTENT_PATHS=0

for doc_file in "${DOCS_FILES[@]}"; do
    if [ -f "$doc_file" ]; then
        # Check for inconsistent virtual environment paths
        if grep -q "olmo-security-analysis/venv" "$doc_file"; then
            echo -e "${YELLOW}⚠️  Found old venv path in $doc_file${NC}"
            INCONSISTENT_PATHS=1
        fi
        
        # Check for old hardcoded model paths
        if grep -q "/Users/vinayakmenon/olmo-security-analysis/models" "$doc_file"; then
            echo -e "${YELLOW}⚠️  Found old hardcoded model path in $doc_file${NC}"
            INCONSISTENT_PATHS=1
        fi
    fi
done

if [ $INCONSISTENT_PATHS -eq 0 ]; then
    test_result 0 "All documentation uses consistent portable paths"
else
    test_result 1 "Documentation contains inconsistent paths"
fi

echo ""
echo "📋 Test 5: .gitignore Functionality Test"
echo "-----------------------------------------"

# Test 5.1: Create test files that should be ignored
mkdir -p security-ai-analysis/test_ignore_check/data
mkdir -p security-ai-analysis/test_ignore_check/results
mkdir -p security-ai-analysis/test_ignore_check/venv

# Create test files
touch security-ai-analysis/test_ignore_check/data/test.json
touch security-ai-analysis/test_ignore_check/results/test.json
touch security-ai-analysis/test_ignore_check/venv/test.py
touch security-ai-analysis/test_ignore_check/test.pyc

# Test git status (requires being in git repo)
cd security-ai-analysis/test_ignore_check
GIT_STATUS_OUTPUT=$(git status --porcelain 2>/dev/null || echo "not_in_git_repo")

if [ "$GIT_STATUS_OUTPUT" = "not_in_git_repo" ]; then
    echo -e "${YELLOW}⚠️  Not in git repository - skipping git ignore test${NC}"
    test_result 0 "Git ignore test skipped (not in repo)"
else
    # Check that ignored files don't appear in git status
    IGNORED_FILES_FOUND=0
    if echo "$GIT_STATUS_OUTPUT" | grep -q "data/\|results/\|venv/\|\.pyc"; then
        echo -e "${YELLOW}⚠️  Some files that should be ignored appear in git status${NC}"
        IGNORED_FILES_FOUND=1
    fi
    
    if [ $IGNORED_FILES_FOUND -eq 0 ]; then
        test_result 0 ".gitignore properly excludes test files from git"
    else
        test_result 1 ".gitignore not properly excluding files"
    fi
fi

# Cleanup test files
cd ../..
rm -rf security-ai-analysis/test_ignore_check

echo ""
echo "📋 Test 6: Documentation Completeness"
echo "--------------------------------------"

# Test 6.1: Check for required sections in README
README_SECTIONS=("Portable Architecture" "Quick Setup" "Configuration" "Shared" "Local")
for section in "${README_SECTIONS[@]}"; do
    if grep -q "$section" security-ai-analysis/README.md; then
        test_result 0 "README.md includes section: $section"
    else
        test_result 1 "README.md missing section: $section"
    fi
done

# Test 6.2: Check for required sections in Getting Started
GETTING_STARTED_SECTIONS=("Quick Setup" "Architecture" "Configuration" "Usage Examples" "Troubleshooting")
for section in "${GETTING_STARTED_SECTIONS[@]}"; do
    if grep -q "$section" security-ai-analysis/docs/GETTING_STARTED.md; then
        test_result 0 "GETTING_STARTED.md includes section: $section"
    else
        test_result 1 "GETTING_STARTED.md missing section: $section"
    fi
done

echo ""
echo "=================================================================="
echo "📊 Phase 4 Validation Results Summary"
echo "=================================================================="
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Phase 4 Complete: All documentation and .gitignore validation tests passed!${NC}"
    echo ""
    echo "📋 Phase 4 Achievements:"
    echo "• ✅ .gitignore created with sharing philosophy comments"
    echo "• ✅ README.md updated with portable architecture paths"
    echo "• ✅ Comprehensive GETTING_STARTED.md guide created"
    echo "• ✅ All documentation uses consistent portable paths"
    echo "• ✅ Documentation completeness validated"
    echo ""
    echo "🚀 Ready for Phase 5: Integration Testing"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Phase 4 validation failed with $TESTS_FAILED errors${NC}"
    echo "Please fix the issues above before proceeding to Phase 5"
    exit 1
fi