"""
Shared fixtures and configuration for security AI analysis tests
"""
import pytest
import tempfile
import shutil
import os
from pathlib import Path

session_temp_dir=Path(__file__).parent / "security_ai_test_session"

@pytest.fixture(scope="session")
def setup_temp_dir():
    # Create session-wide temporary directory for all tests
    #session_temp_dir = Path(tempfile.mkdtemp(prefix="security_ai_test_session_"))
    # Cleanup: remove session temporary directory
    if session_temp_dir.exists():
        shutil.rmtree(session_temp_dir)
    session_temp_dir.mkdir(parents=True, exist_ok=True)
    yield session_temp_dir

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Set up isolated test environment with directory overrides for all tests.
    This ensures complete test isolation from production directories.
    """
    test_env_vars = {
        'OLMO_WORKSPACE_DIR': str(session_temp_dir / "test_workspace"),
        'OLMO_KNOWLEDGE_BASE_DIR': str(session_temp_dir / "test_kb"),
        'OLMO_FINE_TUNED_MODELS_DIR': str(session_temp_dir / "test_models")
    }

    # Set test environment variables and store originals
    for key, value in test_env_vars.items():    
        monkeypatch.setenv(key, value)