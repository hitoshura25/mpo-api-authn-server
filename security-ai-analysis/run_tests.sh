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

# Function to check test data (integration tests use their own fixtures)
check_test_data() {
    print_status "Verifying integration test fixtures..."

    # Integration tests have their own fixture files
    integration_fixtures="tests/fixtures/phase_inputs"

    if [ ! -d "$integration_fixtures" ]; then
        print_error "Integration test fixtures not found: $integration_fixtures"
        exit 1
    fi

    print_success "Integration test fixtures verified"
}

# Function to run unit tests (no unit tests currently - using integration tests only)
run_unit_tests() {
    print_status "No unit tests configured - using comprehensive integration tests instead"
    print_success "Unit test phase skipped ✓"
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
    echo "  quick       - Run fast checks only (fixtures verification)"
    echo "  integration - Run integration tests, skip slow tests (~30 seconds)"
    echo "  all         - Run complete test suite including slow tests (minutes)"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 quick          # Fast feedback during development"
    echo "  $0 integration    # Standard CI testing"
    echo "  $0 all            # Complete validation before release"
    echo ""
    echo "Test coverage:"
    echo "  • 13 comprehensive integration tests with real security tool outputs"
    echo "  • End-to-end pipeline validation across all 8 phases"
    echo "  • Performance optimized fixture-based testing (4-40x faster)"
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