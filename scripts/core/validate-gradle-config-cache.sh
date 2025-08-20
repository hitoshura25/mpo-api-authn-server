#!/usr/bin/env bash

# Gradle Configuration Cache Compatibility Validation Script
# Validates that custom Gradle tasks follow configuration cache best practices
# 
# Usage: ./scripts/core/validate-gradle-config-cache.sh [task-name]
#        ./scripts/core/validate-gradle-config-cache.sh (validates all tasks)

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to check for configuration cache anti-patterns in build files
check_build_file_patterns() {
    local file="$1"
    local violations=0
    
    log "🔍 Checking build file: $file"
    
    # Check for project API access in doLast blocks
    if grep -n -A 10 -B 2 "doLast\s*{" "$file" | grep -E "(project\.|Task\.project)" > /dev/null 2>&1; then
        error "❌ Found project API access in doLast block in $file"
        echo "   Problematic patterns found:"
        grep -n -A 10 -B 2 "doLast\s*{" "$file" | grep -E "(project\.|Task\.project)" | sed 's/^/     /'
        violations=$((violations + 1))
    fi
    
    # Check for project API access in doFirst blocks
    if grep -n -A 10 -B 2 "doFirst\s*{" "$file" | grep -E "(project\.|Task\.project)" > /dev/null 2>&1; then
        error "❌ Found project API access in doFirst block in $file"
        echo "   Problematic patterns found:"
        grep -n -A 10 -B 2 "doFirst\s*{" "$file" | grep -E "(project\.|Task\.project)" | sed 's/^/     /'
        violations=$((violations + 1))
    fi
    
    # Check for direct file() calls with project properties in execution blocks
    if grep -n -A 10 "do\(Last\|First\)\s*{" "$file" | grep -E "file\([\"']\$\{project\." > /dev/null 2>&1; then
        error "❌ Found file() calls with project properties in execution blocks in $file"
        violations=$((violations + 1))
    fi
    
    # Check for good patterns
    local good_patterns=0
    
    if grep -q "layout\.projectDirectory\|layout\.buildDirectory" "$file"; then
        success "✅ Found layout API usage in $file"
        good_patterns=$((good_patterns + 1))
    fi
    
    if grep -q "inputs\.\|outputs\." "$file"; then
        success "✅ Found inputs/outputs declarations in $file"
        good_patterns=$((good_patterns + 1))
    fi
    
    return $violations
}

# Function to test configuration cache compatibility of a specific task
test_task_config_cache() {
    local task_name="$1"
    local test_passed=0
    
    log "🧪 Testing configuration cache compatibility for task: $task_name"
    
    # Test 1: Clean build with configuration cache
    log "Test 1: Clean build with configuration cache..."
    if ./gradlew clean "$task_name" --configuration-cache --info > "/tmp/gradle-test-1.log" 2>&1; then
        success "✅ Task runs successfully with configuration cache"
        test_passed=$((test_passed + 1))
    else
        error "❌ Task failed with configuration cache enabled"
        echo "Error details:"
        tail -20 "/tmp/gradle-test-1.log" | sed 's/^/   /'
        return 1
    fi
    
    # Test 2: Second run should hit cache or be up-to-date
    log "Test 2: Verifying cache reuse..."
    if ./gradlew "$task_name" --configuration-cache --info > "/tmp/gradle-test-2.log" 2>&1; then
        if grep -q "FROM-CACHE\|UP-TO-DATE" "/tmp/gradle-test-2.log"; then
            success "✅ Task properly uses configuration cache"
            test_passed=$((test_passed + 1))
        else
            warning "⚠️  Task doesn't appear to benefit from caching"
            echo "Consider adding proper inputs/outputs declarations"
        fi
    else
        error "❌ Task failed on second run"
        tail -20 "/tmp/gradle-test-2.log" | sed 's/^/   /'
        return 1
    fi
    
    # Test 3: Check for configuration cache warnings
    log "Test 3: Checking for configuration cache warnings..."
    if ./gradlew "$task_name" --configuration-cache --configuration-cache-problems=warn > "/tmp/gradle-test-3.log" 2>&1; then
        if grep -q "configuration cache entry stored with.*problem" "/tmp/gradle-test-3.log"; then
            error "❌ Configuration cache warnings detected"
            echo "Warnings found:"
            grep "configuration cache\|Task\.project\|execution time" "/tmp/gradle-test-3.log" | sed 's/^/   /'
            return 1
        else
            success "✅ No configuration cache warnings detected"
            test_passed=$((test_passed + 1))
        fi
    else
        error "❌ Task failed with configuration cache problems reporting"
        return 1
    fi
    
    # Clean up test files
    rm -f /tmp/gradle-test-*.log
    
    success "🎉 Task '$task_name' passed all configuration cache compatibility tests ($test_passed/3)"
    return 0
}

# Function to get all custom tasks from build files
get_custom_tasks() {
    find . -name "*.gradle.kts" -o -name "*.gradle" | \
    xargs grep -l "task.*{" | \
    xargs grep -o "task [a-zA-Z][a-zA-Z0-9]*" | \
    cut -d' ' -f2 | \
    sort -u | \
    grep -v -E "^(build|clean|test|check|assemble)$"
}

# Function to validate all build files
validate_build_files() {
    local total_violations=0
    local files_checked=0
    
    log "🔍 Searching for build files with custom tasks..."
    
    while IFS= read -r -d '' file; do
        if grep -q "doLast\|doFirst" "$file"; then
            files_checked=$((files_checked + 1))
            check_build_file_patterns "$file"
            violations=$?
            total_violations=$((total_violations + violations))
        fi
    done < <(find . -name "*.gradle.kts" -o -name "*.gradle" -print0)
    
    log "📊 Build file validation summary:"
    echo "   Files checked: $files_checked"
    echo "   Total violations: $total_violations"
    
    return $total_violations
}

# Main function
main() {
    local task_name="${1:-}"
    
    echo "🚨 Gradle Configuration Cache Compatibility Validator"
    echo "=================================================="
    
    if [[ -n "$task_name" ]]; then
        # Test specific task
        log "🎯 Testing specific task: $task_name"
        
        if test_task_config_cache "$task_name"; then
            success "🎉 Task '$task_name' is configuration cache compatible!"
            exit 0
        else
            error "💥 Task '$task_name' failed configuration cache compatibility tests"
            exit 1
        fi
    else
        # Validate all build files
        log "🔍 Validating all build files for configuration cache patterns..."
        
        if validate_build_files; then
            success "🎉 All build files passed configuration cache pattern validation!"
            
            # Offer to test discovered custom tasks
            log "🔍 Discovering custom tasks..."
            custom_tasks=$(get_custom_tasks)
            
            if [[ -n "$custom_tasks" ]]; then
                echo "Found custom tasks:"
                echo "$custom_tasks" | sed 's/^/  - /'
                echo
                echo "To test a specific task, run:"
                echo "  $0 <task-name>"
                echo
                echo "To test all custom tasks (may take a while):"
                echo "  for task in \$(./scripts/core/validate-gradle-config-cache.sh | grep '^  - ' | cut -d' ' -f4); do"
                echo "    echo \"Testing \$task...\""
                echo "    $0 \$task || exit 1"
                echo "  done"
            else
                log "No custom tasks with execution blocks found"
            fi
            
            exit 0
        else
            error "💥 Configuration cache pattern violations found!"
            echo
            echo "📚 For help fixing these issues, see:"
            echo "  - docs/development/gradle-configuration-cache-compatibility.md"
            echo "  - docs/development/gradle-config-cache-quick-fixes.md"
            echo "  - docs/development/gradle-task-code-review-checklist.md"
            exit 1
        fi
    fi
}

# Check if we're in the right directory
if [[ ! -f "gradlew" ]]; then
    error "This script must be run from the project root directory (where gradlew is located)"
    exit 1
fi

# Run main function with all arguments
main "$@"