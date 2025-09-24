#!/bin/bash
# Test runner for Security AI Analysis with speed tiers
# Supports different test execution modes for fast feedback

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if pytest is available
check_pytest() {
    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    if ! command -v pytest &> /dev/null; then
        print_error "pytest not found. Please install pytest in your environment."
        print_status "Suggestion: source venv/bin/activate && python -m pip install pytest"
        exit 1
    fi
}

# Function to check test data
check_test_data() {
    print_status "Checking test data integrity..."

    test_data_dir="tests/fixtures/controlled_test_data"

    if [ ! -d "$test_data_dir" ]; then
        print_error "Test data directory not found: $test_data_dir"
        exit 1
    fi

    required_files=(
        "semgrep.sarif"
        "trivy-results.sarif"
        "checkov-results.sarif"
        "osv-results.json"
        "zap-report.json"
        "README.md"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$test_data_dir/$file" ]; then
            print_error "Required test file missing: $test_data_dir/$file"
            exit 1
        fi
    done

    print_success "Test data integrity check passed"
}

# Function to run unit tests (~2 seconds)
run_unit_tests() {
    print_status "Running unit tests (fast - ~2 seconds)..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    python -m pytest tests/unit/ -v --tb=short

    if [ $? -eq 0 ]; then
        print_success "Unit tests passed ✓"
    else
        print_error "Unit tests failed ✗"
        exit 1
    fi
}

# Function to run integration tests (~30 seconds)
run_integration_tests() {
    print_status "Running integration tests (medium speed - ~30 seconds)..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # Skip slow tests by default
    python -m pytest tests/integration/ -v --tb=short -m "not slow"

    if [ $? -eq 0 ]; then
        print_success "Integration tests passed ✓"
    else
        print_error "Integration tests failed ✗"
        exit 1
    fi
}

# Function to run all tests including slow ones (minutes)
run_all_tests() {
    print_status "Running all tests including slow tests (full suite - may take minutes)..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    python -m pytest tests/ -v --tb=short

    if [ $? -eq 0 ]; then
        print_success "All tests passed ✓"
    else
        print_error "Some tests failed ✗"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [quick|integration|all|help]"
    echo ""
    echo "Test execution modes:"
    echo "  quick       - Run unit tests only (~2 seconds)"
    echo "  integration - Run unit + integration tests, skip slow tests (~30 seconds)"
    echo "  all         - Run complete test suite including slow tests (minutes)"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 quick          # Fast feedback during development"
    echo "  $0 integration    # Standard CI testing"
    echo "  $0 all            # Complete validation before release"
    echo ""
    echo "Test data summary:"
    echo "  • 8 controlled vulnerabilities across 5 security tools"
    echo "  • Exact assertion testing for regression detection"
    echo "  • Fast execution with predictable results"
}

# Main execution logic
main() {
    local mode="${1:-integration}"  # Default to integration mode

    case "$mode" in
        "quick")
            print_status "Starting quick test mode..."
            check_pytest
            check_test_data
            run_unit_tests
            print_success "Quick tests completed successfully!"
            ;;
        "integration")
            print_status "Starting integration test mode..."
            check_pytest
            check_test_data
            run_integration_tests
            print_success "Integration tests completed successfully!"
            ;;
        "all")
            print_status "Starting full test suite..."
            check_pytest
            check_test_data
            run_unit_tests
            run_integration_tests
            print_warning "Running slow tests - this may take several minutes..."
            # Note: run_all_tests runs all tests including unit+integration+slow, so there's some duplication
            # but that's acceptable for a comprehensive test run
            run_all_tests
            print_success "All tests completed successfully!"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown mode: $mode"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Trap Ctrl+C and cleanup
trap 'print_warning "Tests interrupted by user"; exit 130' INT

# Run main function with all arguments
main "$@"