"""
Shared fixtures and configuration for security AI analysis tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing path to controlled test data directory"""
    return Path(__file__).parent / "fixtures" / "controlled_test_data"


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


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take minutes to run)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark slow tests"""
    for item in items:
        if "fine_tuning" in item.name or "model_upload" in item.name:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def ensure_test_data_exists(test_data_dir):
    """Ensure test data directory and files exist before running any test"""
    assert test_data_dir.exists(), f"Test data directory not found: {test_data_dir}"

    required_files = [
        "semgrep.sarif",
        "trivy-results.sarif",
        "checkov-results.sarif",
        "osv-results.json",
        "zap-report.json",
        "README.md"
    ]

    for filename in required_files:
        file_path = test_data_dir / filename
        assert file_path.exists(), f"Required test file missing: {file_path}"


# Expected vulnerability counts for validation
EXPECTED_VULNERABILITY_COUNTS = {
    "semgrep": 3,
    "trivy": 2,
    "checkov": 1,
    "osv-scanner": 1,
    "zap": 1,
    "total": 8
}


@pytest.fixture
def expected_counts():
    """Fixture providing expected vulnerability counts for assertions"""
    return EXPECTED_VULNERABILITY_COUNTS.copy()


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


@pytest.fixture
def parser_functions():
    """Fixture providing all parser functions for testing"""
    import sys
    from pathlib import Path

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from parsers.semgrep_parser import parse_semgrep_sarif
    from parsers.trivy_parser import parse_trivy_json
    from parsers.checkov_parser import parse_checkov_json
    from parsers.osv_parser import parse_osv_json
    from parsers.zap_parser import parse_zap_json

    return {
        "semgrep": parse_semgrep_sarif,
        "trivy": parse_trivy_json,
        "checkov": parse_checkov_json,
        "osv": parse_osv_json,
        "zap": parse_zap_json
    }