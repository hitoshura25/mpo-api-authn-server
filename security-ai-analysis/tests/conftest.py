"""
Shared fixtures and configuration for security AI analysis tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def sample_artifacts_dir():
    """Fixture providing path to sample security artifacts directory"""
    return Path(__file__).parent / "fixtures" / "sample_security_artifacts"


@pytest.fixture
def temp_output_dir():
    """Fixture providing temporary output directory for each test"""
    temp_dir = Path(tempfile.mkdtemp(prefix="security_ai_test_"))
    yield temp_dir
    # Cleanup after test
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture(scope="session")
def script_path():
    """Fixture providing path to main process_artifacts.py script"""
    return Path(__file__).parent.parent / "process_artifacts.py"


def pytest_collection_modifyitems(config, items):
    """Automatically mark slow and specialized tests"""
    for item in items:
        # Mark training tests
        if ("training_phase" in item.name and "creates_complete_model" in item.name) or "fine_tuning" in item.name:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.training)

        # Mark upload tests
        elif "upload" in item.name:
            item.add_marker(pytest.mark.upload)

        # Mark other potentially slow tests
        elif "model_upload" in item.name or "integration" in item.name:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def ensure_fixtures_exist():
    """Ensure required fixture directories exist before running any test"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    assert fixtures_dir.exists(), f"Fixtures directory not found: {fixtures_dir}"

    # Verify sample artifacts directory exists (used by parsing phase tests)
    sample_artifacts = fixtures_dir / "sample_security_artifacts"
    assert sample_artifacts.exists(), f"Sample artifacts directory not found: {sample_artifacts}"

    # Verify phase inputs directory exists (used by phase-specific tests)
    phase_inputs = fixtures_dir / "phase_inputs"
    assert phase_inputs.exists(), f"Phase inputs directory not found: {phase_inputs}"


# Keep expected total count for integration tests
EXPECTED_TOTAL_VULNERABILITIES = 8


# Common test arguments for process_artifacts.py
FAST_TEST_ARGS = [
    "--skip-fine-tuning",
    "--disable-rag",
    "--disable-sequential-fine-tuning",
    "--skip-model-upload"
]


@pytest.fixture
def fast_test_args():
    """Fixture providing arguments for fast test execution"""
    return FAST_TEST_ARGS.copy()


# Integration test fixtures remain focused on end-to-end testing
# Parser functions are tested through integration tests, not unit tests

# Add pytest ini-style configuration programmatically
def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take minutes to run)"
    )
    config.addinivalue_line(
        "markers", "training: marks tests that perform actual model training"
    )
    config.addinivalue_line(
        "markers", "upload: marks tests that test model upload functionality"
    )

    # Set default timeout for slow tests
    if not config.getoption("--timeout"):
        config.option.timeout = 300  # 5 minutes default timeout