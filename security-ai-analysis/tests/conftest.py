"""
Shared fixtures and configuration for security AI analysis tests
"""
import pytest
import tempfile
import shutil
import os
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up isolated test environment with directory overrides for all tests.
    This ensures complete test isolation from production directories.
    """
    # Create session-wide temporary directory for all tests
    session_temp_dir = Path(tempfile.mkdtemp(prefix="security_ai_test_session_"))

    # Store original environment variables
    original_env_vars = {}
    test_env_vars = {
        'OLMO_WORKSPACE_DIR': str(session_temp_dir / "test_workspace"),
        'OLMO_KNOWLEDGE_BASE_DIR': str(session_temp_dir / "test_kb"),
        'OLMO_FINE_TUNED_MODELS_DIR': str(session_temp_dir / "test_models"),
        'OLMO_MAX_EPOCHS': '1',
        'OLMO_SAVE_STEPS': '3',
        'OLMO_EVAL_STEPS': '2',
        'OLMO_LEARNING_RATE': '2e-4',
        'OLMO_BATCH_SIZE': '1',
        'OLMO_MAX_STAGE1_ITERS': '0',  # No maximum = use calculated value (30)
        'OLMO_MAX_STAGE2_ITERS': '0',   # No maximum = use calculated value (48)
        # Test-friendly validation thresholds (fixture data regression testing)
        'OLMO_STAGE1_VALIDATION_THRESHOLD': '0.2',
        'OLMO_STAGE2_VALIDATION_THRESHOLD': '0.2',
        'OLMO_SEQUENTIAL_VALIDATION_THRESHOLD': '0.15',
        # Multi-domain configuration for testing (always enabled)
        'OLMO_MULTI_DOMAIN_OVERALL_THRESHOLD': '0.75',
        'OLMO_MULTI_DOMAIN_CATEGORY_MIN': '0.40',
        'OLMO_MULTI_DOMAIN_HIGH_THRESHOLD': '0.75',
        'OLMO_MULTI_DOMAIN_MEDIUM_THRESHOLD': '0.60'
    }

    # Set test environment variables and store originals
    for key, value in test_env_vars.items():
        original_env_vars[key] = os.environ.get(key)
        os.environ[key] = value

    yield session_temp_dir

    # Cleanup: restore original environment variables
    for key, original_value in original_env_vars.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

    # Cleanup: remove session temporary directory
    if session_temp_dir.exists():
        shutil.rmtree(session_temp_dir)


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


@pytest.fixture
def mock_training_run_manager():
    """Create TrainingRunManager that uses isolated test directory instead of production paths"""
    import sys
    from pathlib import Path

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config_manager import OLMoSecurityConfig
    from training_run_manager import TrainingRunManager

    # Create config that will use test environment variables
    config = OLMoSecurityConfig()

    # Create training run manager with test-isolated paths
    training_run_manager = TrainingRunManager(config)

    # Ensure training runs directory exists in test environment
    training_run_manager.training_runs_dir.mkdir(parents=True, exist_ok=True)

    return training_run_manager


@pytest.fixture
def create_mock_model_files():
    """Helper function to create realistic model files for testing"""
    import json
    import struct

    def create_files(directory: Path):
        """Create realistic model files in the given directory"""
        directory.mkdir(parents=True, exist_ok=True)

        # Create config.json
        model_config = {
            "model_type": "OLMoForCausalLM",
            "vocab_size": 50304,
            "hidden_size": 2048,
            "intermediate_size": 5504,
            "num_hidden_layers": 16,
            "num_attention_heads": 16,
            "max_position_embeddings": 2048,
            "architectures": ["OLMoForCausalLM"]
        }
        (directory / "config.json").write_text(json.dumps(model_config, indent=2))

        # Create tokenizer.json
        tokenizer_config = {
            "version": "1.0",
            "tokenizer": {
                "type": "ByteLevelBPETokenizer",
                "vocab_size": 50304
            },
            "decoder": {
                "type": "ByteLevelDecoder"
            }
        }
        (directory / "tokenizer.json").write_text(json.dumps(tokenizer_config, indent=2))

        # Create mock safetensors file (minimal but valid)
        tensors_metadata = {
            "lm_head.weight": {
                "dtype": "F32",
                "shape": [50304, 2048],
                "data_offsets": [0, 411041792]
            }
        }

        # Create header and minimal tensor data
        header_json = json.dumps(tensors_metadata).encode('utf-8')
        header_length = len(header_json)

        # Create some dummy tensor data (smaller than real model but valid format)
        tensor_data = b'\x00' * 1024  # 1KB of zero data

        # Write safetensors format: 8 bytes length + header + tensor data
        with open(directory / "model.safetensors", 'wb') as f:
            f.write(struct.pack('<Q', header_length))
            f.write(header_json)
            f.write(tensor_data)

        # Create README.md (required for model validation)
        readme_content = """---
language: en
tags:
- fine-tuned
- security-analysis
- test-model
library_name: transformers
pipeline_tag: text-generation
---

# Test Model

This is a test model created for validation testing.

## Model Details

- **Base Model**: OLMo-2-1B
- **Purpose**: Testing security analysis pipeline
- **Training**: Mock training for test validation

## Usage

This model is for testing purposes only.

## Performance

Test model with minimal functionality for validation testing.

## Training Data

Mock training data for testing validation pipeline.
"""
        (directory / "README.md").write_text(readme_content)

    return create_files


@pytest.fixture
def create_mock_lora_files():
    """Helper function to create realistic LoRA adapter files for testing"""
    import json
    import struct

    def create_files(directory: Path):
        """Create realistic LoRA adapter files in the given directory"""
        directory.mkdir(parents=True, exist_ok=True)

        # Create adapter_config.json
        adapter_config = {
            "base_model_name_or_path": "allenai/OLMo-2-1B",
            "peft_type": "LORA",
            "task_type": "CAUSAL_LM",
            "r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "adapter_name": "default"
        }
        (directory / "adapter_config.json").write_text(json.dumps(adapter_config, indent=2))

        # Create mock adapters.safetensors
        adapter_tensors = {
            "base_model.model.layers.0.self_attn.q_proj.lora_A.weight": {
                "dtype": "F32",
                "shape": [16, 2048],
                "data_offsets": [0, 131072]
            },
            "base_model.model.layers.0.self_attn.q_proj.lora_B.weight": {
                "dtype": "F32",
                "shape": [2048, 16],
                "data_offsets": [131072, 262144]
            }
        }

        header_json = json.dumps(adapter_tensors).encode('utf-8')
        header_length = len(header_json)
        tensor_data = b'\x00' * 512  # Small amount of adapter data

        with open(directory / "adapters.safetensors", 'wb') as f:
            f.write(struct.pack('<Q', header_length))
            f.write(header_json)
            f.write(tensor_data)

    return create_files


@pytest.fixture
def completed_training_run(mock_training_run_manager, create_mock_model_files, create_mock_lora_files):
    """Create a completed training run with proper manifest and all required artifacts"""
    import json
    from datetime import datetime

    # Create a training run with a test timestamp
    run_id = "20250929_120000_test"
    training_run = mock_training_run_manager.create_run(run_id, base_model="OLMo-2-1B-mlx-q4")

    # Create Stage 1 artifacts (LoRA adapters)
    stage1_adapters_dir = training_run.run_dir / "stage1" / "adapters"
    create_mock_lora_files(stage1_adapters_dir)

    # Create Stage 1 merged model
    stage1_merged_dir = training_run.run_dir / "stage1" / "merged-model"
    create_mock_model_files(stage1_merged_dir)

    # Create Stage 2 artifacts (final complete model)
    stage2_final_dir = training_run.run_dir / "stage2" / "final-model"
    create_mock_model_files(stage2_final_dir)

    # Create Stage 2 adapters
    stage2_adapters_dir = training_run.run_dir / "stage2" / "adapters"
    create_mock_lora_files(stage2_adapters_dir)

    # Create training data files
    stage1_data_dir = training_run.run_dir / "stage1" / "training-data"
    stage1_data_dir.mkdir(parents=True, exist_ok=True)
    (stage1_data_dir / "analysis-dataset.jsonl").write_text('{"text": "test analysis data"}\n')

    stage2_data_dir = training_run.run_dir / "stage2" / "training-data"
    stage2_data_dir.mkdir(parents=True, exist_ok=True)
    (stage2_data_dir / "codefix-dataset.jsonl").write_text('{"text": "test codefix data"}\n')
    (stage2_data_dir / "mixed-dataset.jsonl").write_text('{"text": "test mixed data"}\n')

    # Update manifest with proper paths (using only valid StageMetadata fields)
    from training_run_manager import StageMetadata

    stage1_metadata = StageMetadata(
        adapters_path="./stage1/adapters",
        merged_model_path="./stage1/merged-model",
        training_data_path="./stage1/training-data/analysis-dataset.jsonl"
    )

    stage2_metadata = StageMetadata(
        adapters_path="./stage2/adapters",
        final_model_path="./stage2/final-model",
        training_data_path="./stage2/training-data/codefix-dataset.jsonl",
        training_data_paths={
            "codefix_dataset": "./stage2/training-data/codefix-dataset.jsonl",
            "mixed_dataset": "./stage2/training-data/mixed-dataset.jsonl"
        }
    )

    # Update the manifest
    training_run.manifest.stage1 = stage1_metadata
    training_run.manifest.stage2 = stage2_metadata
    training_run.manifest.run_metadata.update({
        "status": "completed",
        "total_duration_seconds": 300.0,
        "training_end": datetime.now().isoformat()
    })

    # Save the updated manifest
    training_run.save_manifest()

    return training_run
