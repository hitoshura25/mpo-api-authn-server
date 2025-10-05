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

# Function to run unit tests (fast <5 seconds)
run_unit_tests() {
    print_status "Running unit tests (fast - <5 seconds)..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # Run unit tests from tests/unit/ directory
    local start_time=$(date +%s)
    python -m pytest tests/unit/ -v --tb=short --durations=3
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $? -eq 0 ]; then
        print_success "Unit tests passed ✓ (${duration}s)"
    else
        print_error "Unit tests failed ✗"
        exit 1
    fi
}

# Function to run integration tests (~15-30 seconds with parallel execution)
run_integration_tests() {
    print_status "Running integration tests (medium speed - ~15-30 seconds with parallel execution)..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # Skip slow tests by default, use parallel execution for speed
    local start_time=$(date +%s)
    python -m pytest tests/integration/ -v --tb=short -m "not slow" -n auto --durations=5
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $? -eq 0 ]; then
        print_success "Integration tests passed ✓ (${duration}s)"
    else
        print_error "Integration tests failed ✗"
        exit 1
    fi
}

# Function to run all tests including slow ones (1-3 minutes with optimizations)
run_all_tests() {
    print_status "Running all tests including slow tests (full suite - optimized to 1-3 minutes)..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    local start_time=$(date +%s)
    # Use parallel execution and show timing for optimization feedback
    python -m pytest tests/ -v --tb=short -n auto --durations=10
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $? -eq 0 ]; then
        print_success "All tests passed ✓ (${duration}s total)"
    else
        print_error "Some tests failed ✗"
        exit 1
    fi
}

# Function to run training tests only (~1 minute with optimizations)
run_training_tests() {
    print_status "Running training tests only (ultra-fast ~1 minute with test configuration)..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    local start_time=$(date +%s)
    # Run only training-marked tests with test mode environment
    OLMO_TEST_MODE=1 python -m pytest tests/ -v --tb=short -m "training" --durations=3
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $? -eq 0 ]; then
        print_success "Training tests passed ✓ (${duration}s)"
    else
        print_error "Training tests failed ✗"
        exit 1
    fi
}

# Function to run upload tests only
run_upload_tests() {
    print_status "Running upload tests only..."

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    local start_time=$(date +%s)
    # Run only upload-marked tests
    python -m pytest tests/ -v --tb=short -m "upload" --durations=3
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $? -eq 0 ]; then
        print_success "Upload tests passed ✓ (${duration}s)"
    else
        print_error "Upload tests failed ✗"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [quick|integration|all|training|upload|help]"
    echo ""
    echo "Test execution modes:"
    echo "  quick       - Run unit tests and fast checks (<10 seconds)"
    echo "  integration - Run integration tests, skip slow tests (~15-30 seconds)"
    echo "  all         - Run complete test suite including slow tests (1-3 minutes)"
    echo "  training    - Run only training-related tests (ultra-fast ~1 minute)"
    echo "  upload      - Run only upload-related tests"
    echo "  help        - Show this help message"
    echo ""
    echo "Performance optimizations:"
    echo "  • Parallel execution with pytest-xdist (-n auto)"
    echo "  • Ultra-fast training tests with test-specific configuration"
    echo "  • Performance timing and slowest test identification"
    echo ""
    echo "Examples:"
    echo "  $0 quick          # Fast feedback during development (unit tests + fixtures)"
    echo "  $0 integration    # Standard CI testing (parallel execution)"
    echo "  $0 training       # Test only training pipeline (ultra-fast)"
    echo "  $0 all            # Complete validation before release"
    echo ""
    echo "Test coverage:"
    echo "  • Unit tests for multi-domain security specialization"
    echo "  • 13 comprehensive integration tests with real security tool outputs"
    echo "  • End-to-end pipeline validation across all 8 phases"
    echo "  • Performance optimized fixture-based testing (4-40x faster)"
    echo "  • Training tests optimized from 40+ minutes to ~1 minute"
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
            print_status "Running comprehensive test suite (optimized to 1-3 minutes)..."
            # Single comprehensive run of all tests - no duplication
            run_all_tests
            print_success "All tests completed successfully!"
            ;;
        "training")
            print_status "Starting training test mode..."
            check_pytest
            check_test_data
            run_training_tests
            print_success "Training tests completed successfully!"
            ;;
        "upload")
            print_status "Starting upload test mode..."
            check_pytest
            check_test_data
            run_upload_tests
            print_success "Upload tests completed successfully!"
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