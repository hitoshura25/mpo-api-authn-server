"""
Shared fixtures and configuration for security AI analysis tests
"""
import pytest
import shutil
from pathlib import Path

session_temp_dir=Path(__file__).parent / "security_ai_test_session"
workspace_dir = session_temp_dir / "test_workspace"
kb_dir = session_temp_dir / "test_kb"
models_dir = session_temp_dir / "test_models"
upload_staging_dir = session_temp_dir / "test_upload_staging"

@pytest.fixture(scope="session",autouse=True)
def setup_temp_dir():
    # Create session-wide temporary directory for all tests
    # Cleanup: remove session temporary directory
    if session_temp_dir.exists():
        shutil.rmtree(session_temp_dir)
    session_temp_dir.mkdir(parents=True, exist_ok=True)
    yield

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Set up isolated test environment with directory overrides for all tests.
    This ensures complete test isolation from production directories.
    """
    test_env_vars = {
        'OLMO_WORKSPACE_DIR': str(workspace_dir),
        'OLMO_KNOWLEDGE_BASE_DIR': str(kb_dir),
        'OLMO_FINE_TUNED_MODELS_DIR': str(models_dir),
        'OLMO_UPLOAD_STAGING_DIR': str(upload_staging_dir),
    }

    # Set test environment variables and store originals
    for key, value in test_env_vars.items():    
        monkeypatch.setenv(key, value)

    yield

@pytest.fixture
def test_models_dir():
    """Fixture to provide the test models directory path"""
    return models_dir

@pytest.fixture
def test_upload_staging_dir():
    """Fixture to provide the test upload staging directory path"""
    return upload_staging_dir