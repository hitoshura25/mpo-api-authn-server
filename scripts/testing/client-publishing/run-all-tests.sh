#!/bin/bash
# Master test runner for client publishing testing suite
set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/common-functions.sh"

# Test runner metadata
TEST_RUNNER_NAME="Client Publishing Testing Suite"
VERSION="1.0.0"

# Global test tracking
TOTAL_TEST_SCRIPTS=0
PASSED_TEST_SCRIPTS=0
FAILED_TEST_SCRIPTS=0
SKIPPED_TEST_SCRIPTS=0

# Configuration
VERBOSE=false
DEBUG=false
CATEGORY=""
DRY_RUN=false
PARALLEL=false
MAX_PARALLEL_JOBS=4

# Test categories and their scripts
get_category_scripts() {
    local category="$1"
    case "$category" in
        "config-validation")
            echo "test-config-syntax.sh test-config-structure.sh test-config-completeness.sh test-config-environments.sh"
            ;;
        "workflow-syntax")
            echo "test-workflow-syntax.sh test-input-output-mapping.sh"
            ;;
        "gradle-simulation")
            echo "test-android-template.sh test-gradle-dry-run.sh test-property-mapping.sh"
            ;;
        "environment-selection")
            echo "test-config-loading.sh test-environment-isolation.sh test-dynamic-queries.sh"
            ;;
        "integration")
            echo "test-full-workflow.sh test-cross-platform.sh test-error-scenarios.sh"
            ;;
        *)
            echo ""
            ;;
    esac
}

get_all_categories() {
    echo "config-validation workflow-syntax gradle-simulation environment-selection integration"
}

# Helper functions
show_usage() {
    cat << EOF
${TEST_RUNNER_NAME} v${VERSION}

USAGE:
    $0 [OPTIONS] [CATEGORY]

DESCRIPTION:
    Comprehensive testing suite for the configuration-driven client library 
    publishing system. Validates configuration, workflows, templates, and 
    integration scenarios without actual publishing.

OPTIONS:
    -h, --help              Show this help message and exit
    -v, --verbose           Enable verbose output
    -d, --debug             Enable debug output
    -n, --dry-run           Show what would be tested without running tests
    -p, --parallel          Run tests in parallel (experimental)
    -j, --jobs NUM          Maximum parallel jobs (default: $MAX_PARALLEL_JOBS)
    -c, --category CAT      Run only tests from specific category
    -l, --list-categories   List available test categories
    -s, --summary-only      Show only final summary (quiet mode)

CATEGORIES:
    config-validation       Configuration file validation tests
    workflow-syntax         GitHub Actions workflow syntax tests  
    gradle-simulation       Android template and Gradle tests
    environment-selection   Environment-specific configuration tests
    integration            End-to-end integration simulation tests

EXAMPLES:
    $0                                    # Run all tests
    $0 --verbose                          # Run with verbose output
    $0 --category config-validation       # Run only config tests
    $0 --dry-run                         # Show what would run
    $0 --parallel --jobs 8               # Run with 8 parallel jobs

EXIT CODES:
    0    All tests passed
    1    Some tests failed
    2    Invalid arguments or setup error
    3    Required tools missing
EOF
}

list_categories() {
    echo "Available test categories:"
    echo ""
    for category in $(get_all_categories); do
        echo "  $category:"
        for script in $(get_category_scripts "$category"); do
            echo "    - $script"
        done
        echo ""
    done
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--debug)
                DEBUG=true
                export DEBUG=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -p|--parallel)
                PARALLEL=true
                shift
                ;;
            -j|--jobs)
                if [[ -n "${2:-}" && "$2" =~ ^[0-9]+$ ]]; then
                    MAX_PARALLEL_JOBS="$2"
                    shift 2
                else
                    log_error "Invalid number of jobs: ${2:-}"
                    exit 2
                fi
                ;;
            -c|--category)
                if [[ -n "${2:-}" ]]; then
                    CATEGORY="$2"
                    shift 2
                else
                    log_error "Category argument required"
                    exit 2
                fi
                ;;
            -l|--list-categories)
                list_categories
                exit 0
                ;;
            -s|--summary-only)
                VERBOSE=false
                export QUIET=true
                shift
                ;;
            -*)
                log_error "Unknown option: $1"
                show_usage
                exit 2
                ;;
            *)
                # Positional argument - treat as category
                if [[ -z "$CATEGORY" ]]; then
                    CATEGORY="$1"
                else
                    log_error "Multiple categories specified: $CATEGORY and $1"
                    exit 2
                fi
                shift
                ;;
        esac
    done
}

validate_category() {
    if [[ -n "$CATEGORY" ]]; then
        local valid_categories=$(get_all_categories)
        if [[ ! " $valid_categories " =~ " $CATEGORY " ]]; then
            log_error "Invalid category: $CATEGORY"
            log_info "Available categories: $valid_categories"
            exit 2
        fi
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("yq" "jq")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install missing tools:"
        for tool in "${missing_tools[@]}"; do
            case "$tool" in
                "yq")
                    log_info "  yq: brew install yq"
                    ;;
                "jq")
                    log_info "  jq: brew install jq"
                    ;;
            esac
        done
        exit 3
    fi
    
    # Check optional tools
    local optional_tools=("actionlint")
    for tool in "${optional_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_warning "Optional tool not available: $tool"
            case "$tool" in
                "actionlint")
                    log_info "  Install with: brew install actionlint (for workflow syntax validation)"
                    ;;
            esac
        fi
    done
    
    # Check project structure
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        log_error "Are you running from the project root?"
        exit 2
    fi
    
    if [[ ! -d "$WORKFLOWS_DIR" ]]; then
        log_error "Workflows directory not found: $WORKFLOWS_DIR"
        exit 2
    fi
    
    log_success "Prerequisites check passed"
}

run_test_script() {
    local category="$1"
    local script_name="$2"
    local script_path="${SCRIPT_DIR}/${category}/${script_name}"
    
    if [[ ! -f "$script_path" ]]; then
        log_error "Test script not found: $script_path"
        return 1
    fi
    
    if [[ ! -x "$script_path" ]]; then
        log_error "Test script not executable: $script_path"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would run: $script_path"
        return 0
    fi
    
    log_info "Running: ${category}/${script_name}"
    
    local start_time
    start_time=$(date +%s)
    
    local test_result=0
    if [[ "$VERBOSE" == "true" ]]; then
        "$script_path" || test_result=$?
    else
        "$script_path" >/dev/null 2>&1 || test_result=$?
    fi
    
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ $test_result -eq 0 ]]; then
        log_success "✅ ${script_name} PASSED (${duration}s)"
        ((PASSED_TEST_SCRIPTS++))
    else
        log_error "❌ ${script_name} FAILED (${duration}s)"
        ((FAILED_TEST_SCRIPTS++))
    fi
    
    ((TOTAL_TEST_SCRIPTS++))
    return $test_result
}

run_category_tests() {
    local category="$1"
    local category_scripts=$(get_category_scripts "$category")
    
    log_info "Running $category tests..."
    
    local category_start_time
    category_start_time=$(date +%s)
    
    local category_failures=0
    
    if [[ "$PARALLEL" == "true" ]]; then
        log_info "Running tests in parallel (max $MAX_PARALLEL_JOBS jobs)"
        
        # Create array of background job PIDs
        local pids=()
        local active_jobs=0
        
        for script_name in $category_scripts; do
            # Wait if we've reached max parallel jobs
            while [[ $active_jobs -ge $MAX_PARALLEL_JOBS ]]; do
                # Check for completed jobs
                for i in "${!pids[@]}"; do
                    if ! kill -0 "${pids[i]}" 2>/dev/null; then
                        wait "${pids[i]}"
                        local job_result=$?
                        if [[ $job_result -ne 0 ]]; then
                            ((category_failures++))
                        fi
                        unset "pids[i]"
                        ((active_jobs--))
                    fi
                done
                sleep 0.1
            done
            
            # Start new job in background
            (run_test_script "$category" "$script_name") &
            pids+=($!)
            ((active_jobs++))
        done
        
        # Wait for all remaining jobs
        for pid in "${pids[@]}"; do
            if [[ -n "$pid" ]]; then
                wait "$pid"
                local job_result=$?
                if [[ $job_result -ne 0 ]]; then
                    ((category_failures++))
                fi
            fi
        done
    else
        # Sequential execution
        for script_name in $category_scripts; do
            if ! run_test_script "$category" "$script_name"; then
                ((category_failures++))
            fi
        done
    fi
    
    local category_end_time
    category_end_time=$(date +%s)
    local category_duration=$((category_end_time - category_start_time))
    
    if [[ $category_failures -eq 0 ]]; then
        log_success "✅ $category category completed successfully (${category_duration}s)"
    else
        log_error "❌ $category category completed with $category_failures failures (${category_duration}s)"
    fi
    
    return $category_failures
}

run_all_tests() {
    local overall_start_time
    overall_start_time=$(date +%s)
    
    local total_failures=0
    
    if [[ -n "$CATEGORY" ]]; then
        # Run specific category
        log_info "Running tests for category: $CATEGORY"
        if ! run_category_tests "$CATEGORY"; then
            total_failures=1
        fi
    else
        # Run all categories
        log_info "Running all test categories..."
        
        local categories_to_run=()
        
        # Define execution order (dependencies first)
        local execution_order=("config-validation" "workflow-syntax" "gradle-simulation" "environment-selection" "integration")
        
        for category in "${execution_order[@]}"; do
            local valid_categories=$(get_all_categories)
            if [[ " $valid_categories " =~ " $category " ]]; then
                categories_to_run+=("$category")
            fi
        done
        
        # Add any remaining categories not in execution order
        for category in $(get_all_categories); do
            if [[ ! " ${execution_order[*]} " =~ " ${category} " ]]; then
                categories_to_run+=("$category")
            fi
        done
        
        for category in "${categories_to_run[@]}"; do
            if ! run_category_tests "$category"; then
                total_failures=1
            fi
            echo ""  # Add spacing between categories
        done
    fi
    
    local overall_end_time
    overall_end_time=$(date +%s)
    local overall_duration=$((overall_end_time - overall_start_time))
    
    # Final summary
    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_info "                    TEST EXECUTION SUMMARY"
    log_info "═══════════════════════════════════════════════════════════════"
    log_info "Total test scripts: $TOTAL_TEST_SCRIPTS"
    log_success "Passed: $PASSED_TEST_SCRIPTS"
    
    if [[ $FAILED_TEST_SCRIPTS -gt 0 ]]; then
        log_error "Failed: $FAILED_TEST_SCRIPTS"
    else
        log_info "Failed: $FAILED_TEST_SCRIPTS"
    fi
    
    if [[ $SKIPPED_TEST_SCRIPTS -gt 0 ]]; then
        log_warning "Skipped: $SKIPPED_TEST_SCRIPTS"
    else
        log_info "Skipped: $SKIPPED_TEST_SCRIPTS"
    fi
    
    log_info "Total execution time: ${overall_duration}s"
    
    if [[ "$PARALLEL" == "true" ]]; then
        log_info "Execution mode: Parallel (max $MAX_PARALLEL_JOBS jobs)"
    else
        log_info "Execution mode: Sequential"
    fi
    
    echo ""
    
    if [[ $total_failures -eq 0 ]]; then
        log_success "🎉 All tests passed successfully!"
        return 0
    else
        log_error "💥 Some tests failed. See details above."
        return 1
    fi
}

show_dry_run_summary() {
    log_info "DRY RUN - Tests that would be executed:"
    echo ""
    
    if [[ -n "$CATEGORY" ]]; then
        log_info "Category: $CATEGORY"
        for script_name in $(get_category_scripts "$CATEGORY"); do
            log_info "  - ${CATEGORY}/${script_name}"
        done
    else
        for category in $(get_all_categories); do
            log_info "Category: $category"
            for script_name in $(get_category_scripts "$category"); do
                log_info "  - ${category}/${script_name}"
            done
            echo ""
        done
    fi
    
    log_info "Execution mode: $([ "$PARALLEL" == "true" ] && echo "Parallel (max $MAX_PARALLEL_JOBS jobs)" || echo "Sequential")"
    log_info "Verbose: $VERBOSE"
    log_info "Debug: $DEBUG"
}

# Main execution
main() {
    # Initialize test environment
    if ! init_test_environment; then
        log_error "Failed to initialize test environment"
        exit 2
    fi
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Validate arguments
    validate_category
    
    # Show header
    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_info "    ${TEST_RUNNER_NAME} v${VERSION}"
    log_info "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Handle dry run
    if [[ "$DRY_RUN" == "true" ]]; then
        show_dry_run_summary
        exit 0
    fi
    
    # Run tests
    local test_result=0
    run_all_tests || test_result=$?
    
    # Cleanup
    cleanup_temp_files
    
    exit $test_result
}

# Trap for cleanup on exit
trap 'cleanup_temp_files' EXIT

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi