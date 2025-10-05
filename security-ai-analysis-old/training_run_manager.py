#!/usr/bin/env python3
"""
Training Run Manager - Structured Model Output Architecture

Implements manifest-driven training run management to replace timestamp-based
discovery with explicit contracts and artifact type validation.

Based on: docs/improvements/in-progress/structured-model-output-architecture.md
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TYPE_CHECKING
from datetime import datetime
from dataclasses import dataclass, asdict

if TYPE_CHECKING:
    from config_manager import OLMoSecurityConfig

logger = logging.getLogger(__name__)


@dataclass
class StageMetadata:
    """Metadata for a training stage - pure path contract without status tracking"""
    adapters_path: str
    training_data_path: str

    # Stage-specific optional fields
    final_model_path: Optional[str] = None
    merged_model_path: Optional[str] = None
    training_data_paths: Optional[Dict[str, str]] = None


@dataclass
class RunManifest:
    """Training run manifest schema"""
    version: str = "1.0"
    run_metadata: Dict[str, Any] = None
    stage1: Optional[StageMetadata] = None
    stage2: Optional[StageMetadata] = None
    validation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "version": self.version,
            "run_metadata": self.run_metadata or {},
        }

        if self.stage1:
            result["stage1"] = asdict(self.stage1)
        if self.stage2:
            result["stage2"] = asdict(self.stage2)
        if self.validation:
            result["validation"] = self.validation

        return result


class TrainingRun:
    """Single training run with manifest-based artifact management"""

    def __init__(self, run_dir: Path):
        """Initialize training run from directory path"""
        self.run_dir = run_dir
        self.manifest_path = run_dir / "run-manifest.json"
        self._manifest: Optional[RunManifest] = None

        logger.info(f"🔧 Initializing TrainingRun: {run_dir}")

    @property
    def manifest(self) -> RunManifest:
        """Load and cache run manifest"""
        if self._manifest is None:
            self._manifest = self._load_manifest()
        return self._manifest

    def _load_manifest(self) -> RunManifest:
        """Load manifest from JSON file"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Run manifest not found: {self.manifest_path}")

        try:
            with open(self.manifest_path, 'r') as f:
                manifest_data = json.load(f)

            logger.info(f"📋 Loaded manifest for run: {manifest_data.get('run_metadata', {}).get('run_id', 'unknown')}")

            # Convert to dataclass structure
            manifest = RunManifest()
            manifest.version = manifest_data.get("version", "1.0")
            manifest.run_metadata = manifest_data.get("run_metadata", {})
            manifest.validation = manifest_data.get("validation")

            # Load stage metadata
            if "stage1" in manifest_data:
                stage1_data = manifest_data["stage1"]
                manifest.stage1 = StageMetadata(**stage1_data)

            if "stage2" in manifest_data:
                stage2_data = manifest_data["stage2"]
                manifest.stage2 = StageMetadata(**stage2_data)

            return manifest

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            raise ValueError(f"Invalid manifest format in {self.manifest_path}: {e}")

    def save_manifest(self) -> None:
        """Save manifest to JSON file"""
        if self._manifest is None:
            raise RuntimeError("No manifest to save - call create_manifest() first")

        # Ensure run directory exists
        self.run_dir.mkdir(parents=True, exist_ok=True)

        with open(self.manifest_path, 'w') as f:
            json.dump(self._manifest.to_dict(), f, indent=2)

        logger.info(f"💾 Saved manifest: {self.manifest_path}")

    @property
    def run_id(self) -> str:
        """Get run ID from manifest"""
        return self.manifest.run_metadata.get("run_id", "unknown")


    # Stage 1 properties
    @property
    def stage1_adapters_path(self) -> Path:
        """Get validated Stage 1 LoRA adapters path"""
        if not self.manifest.stage1:
            raise ValueError("Stage 1 not found in manifest")

        adapters_path = self.run_dir / self.manifest.stage1.adapters_path

        # Validate LoRA adapter structure
        if not self._validate_lora_adapters(adapters_path):
            raise ValueError(f"Invalid LoRA adapter structure: {adapters_path}")

        return adapters_path

    @property
    def stage1_merged_model_path(self) -> Path:
        """Get validated Stage 1 merged model path"""
        if not self.manifest.stage1 or not self.manifest.stage1.merged_model_path:
            raise ValueError("Stage 1 merged model not found in manifest")

        model_path = self.run_dir / self.manifest.stage1.merged_model_path

        # Validate full model structure
        if not self._validate_full_model(model_path):
            raise ValueError(f"Invalid full model structure: {model_path}")

        return model_path

    @property
    def stage1_training_data_path(self) -> Path:
        """Get Stage 1 training dataset path"""
        if not self.manifest.stage1:
            raise ValueError("Stage 1 not found in manifest")

        return self.run_dir / self.manifest.stage1.training_data_path

    # Stage 2 properties
    @property
    def stage2_final_model_path(self) -> Path:
        """Get validated Stage 2 complete model path"""
        if not self.manifest.stage2 or not self.manifest.stage2.final_model_path:
            raise ValueError("Stage 2 final model not found in manifest")

        model_path = self.run_dir / self.manifest.stage2.final_model_path

        # Validate full model structure
        if not self._validate_full_model(model_path):
            raise ValueError(f"Invalid full model structure: {model_path}")

        return model_path

    @property
    def stage2_adapters_path(self) -> Path:
        """Get validated Stage 2 LoRA adapters path"""
        if not self.manifest.stage2:
            raise ValueError("Stage 2 not found in manifest")

        adapters_path = self.run_dir / self.manifest.stage2.adapters_path

        # Validate LoRA adapter structure
        if not self._validate_lora_adapters(adapters_path):
            raise ValueError(f"Invalid LoRA adapter structure: {adapters_path}")

        return adapters_path

    def get_stage1_training_data(self) -> Path:
        """Get Stage 1 training dataset for mixing in Stage 2"""
        return self.stage1_training_data_path

    def get_stage2_training_data(self, dataset_type: str = "mixed") -> Path:
        """Get Stage 2 training dataset"""
        if not self.manifest.stage2 or not self.manifest.stage2.training_data_paths:
            raise ValueError("Stage 2 training data not found in manifest")

        if dataset_type not in self.manifest.stage2.training_data_paths:
            available = list(self.manifest.stage2.training_data_paths.keys())
            raise ValueError(f"Stage 2 dataset type '{dataset_type}' not found. Available: {available}")

        return self.run_dir / self.manifest.stage2.training_data_paths[dataset_type]

    # Validation methods
    def _validate_lora_adapters(self, adapter_path: Path) -> bool:
        """Validate LoRA adapter directory structure"""
        if not adapter_path.exists():
            logger.warning(f"LoRA adapter path does not exist: {adapter_path}")
            return False

        required_files = ['adapters.safetensors', 'adapter_config.json']
        for file in required_files:
            file_path = adapter_path / file
            if not file_path.exists() or file_path.stat().st_size == 0:
                logger.warning(f"Missing or empty LoRA file: {file_path}")
                return False

        logger.debug(f"✅ LoRA adapter validation passed: {adapter_path}")
        return True

    def _validate_full_model(self, model_path: Path) -> bool:
        """Validate full model directory structure"""
        if not model_path.exists():
            logger.warning(f"Model path does not exist: {model_path}")
            return False

        required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
        for file in required_files:
            file_path = model_path / file
            if not file_path.exists() or file_path.stat().st_size == 0:
                logger.warning(f"Missing or empty model file: {file_path}")
                return False

        logger.debug(f"✅ Full model validation passed: {model_path}")
        return True



class TrainingRunManager:
    """Manager for training runs with structured output"""

    def __init__(self, config: 'OLMoSecurityConfig'):
        """Initialize training run manager with configuration"""
        self.config = config
        self.training_runs_dir = config.get_training_runs_dir()

        # Ensure training runs directory exists
        self.training_runs_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"🏗️ TrainingRunManager initialized: {self.training_runs_dir}")

    def create_run(self, run_id: str, base_model: str = "OLMo-2-1B-mlx-q4") -> TrainingRun:
        """Create new training run with complete manifest containing all predefined paths"""
        run_dir = self.training_runs_dir / f"webauthn-security-{run_id}"

        if run_dir.exists():
            logger.warning(f"Training run directory already exists: {run_dir}")

        # Create training run instance (but don't create directories yet - lazy creation)
        training_run = TrainingRun(run_dir)

        # Generate complete manifest with all predefined paths
        manifest = RunManifest()
        manifest.run_metadata = {
            "run_id": f"webauthn-security-{run_id}",
            "timestamp": datetime.now().isoformat(),
            "base_model": base_model,
            "training_type": "sequential_fine_tuning"
        }

        # Define all Stage 1 paths
        manifest.stage1 = StageMetadata(
            adapters_path="./stage1/adapters",
            merged_model_path="./stage1/merged-model",
            training_data_path="./stage1/training-data/analysis-dataset.jsonl"
        )

        # Define all Stage 2 paths
        manifest.stage2 = StageMetadata(
            adapters_path="./stage2/adapters",
            final_model_path="./stage2/final-model",
            training_data_path="./stage2/training-data/codefix-dataset.jsonl",
            training_data_paths={
                "codefix_dataset": "./stage2/training-data/codefix-dataset.jsonl",
                "mixed_dataset": "./stage2/training-data/mixed-dataset.jsonl"
            }
        )

        training_run._manifest = manifest
        training_run.save_manifest()

        logger.info(f"🚀 Created new training run with complete path manifest: {run_id}")
        return training_run

    def get_latest_run(self) -> TrainingRun:
        """Get most recent run with Stage 2 final model (indicating completion)"""
        completed_runs = []

        for run_dir in self.training_runs_dir.glob("webauthn-security-*"):
            if not run_dir.is_dir():
                continue

            try:
                training_run = TrainingRun(run_dir)
                # Check if Stage 2 final model exists (indicates completed training)
                if training_run.manifest.stage2 and training_run.manifest.stage2.final_model_path:
                    stage2_final_path = training_run.run_dir / training_run.manifest.stage2.final_model_path
                    if (stage2_final_path / "model.safetensors").exists():
                        timestamp_str = training_run.manifest.run_metadata.get("timestamp", "")
                        completed_runs.append((timestamp_str, training_run))
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Skipping invalid run directory {run_dir}: {e}")
                continue

        if not completed_runs:
            raise FileNotFoundError("No completed training runs found")

        # Sort by timestamp and return latest
        completed_runs.sort(key=lambda x: x[0])
        latest_run = completed_runs[-1][1]

        logger.info(f"📋 Found latest completed run: {latest_run.run_id}")
        return latest_run

    def get_run_by_id(self, run_id: str) -> TrainingRun:
        """Get specific run by ID"""
        # Handle both formats: "webauthn-security-ID" and just "ID"
        if not run_id.startswith("webauthn-security-"):
            run_id = f"webauthn-security-{run_id}"

        run_dir = self.training_runs_dir / run_id

        if not run_dir.exists():
            raise FileNotFoundError(f"Training run not found: {run_id}")

        return TrainingRun(run_dir)

    def list_runs(self, status_filter: Optional[str] = None) -> List[TrainingRun]:
        """List all training runs, optionally filtered by status"""
        runs = []

        for run_dir in self.training_runs_dir.glob("webauthn-security-*"):
            if not run_dir.is_dir():
                continue

            try:
                training_run = TrainingRun(run_dir)
                if status_filter is None or training_run.status == status_filter:
                    runs.append(training_run)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Skipping invalid run directory {run_dir}: {e}")
                continue

        # Sort by timestamp
        runs.sort(key=lambda r: r.manifest.run_metadata.get("timestamp", ""))

        logger.info(f"📋 Found {len(runs)} training runs (filter: {status_filter})")
        return runs

    def cleanup_failed_runs(self) -> int:
        """Remove failed or incomplete training runs"""
        failed_runs = self.list_runs(status_filter="failed")
        incomplete_runs = self.list_runs(status_filter="in_progress")

        cleanup_count = 0
        for run in failed_runs + incomplete_runs:
            try:
                import shutil
                shutil.rmtree(run.run_dir)
                cleanup_count += 1
                logger.info(f"🗑️ Cleaned up run: {run.run_id}")
            except Exception as e:
                logger.warning(f"Failed to clean up {run.run_id}: {e}")

        logger.info(f"🧹 Cleaned up {cleanup_count} failed/incomplete runs")
        return cleanup_count


def validate_training_run_structure(run_dir: Path) -> Dict[str, Any]:
    """Standalone validation function for training run structure"""
    try:
        training_run = TrainingRun(run_dir)

        result = {
            "valid": True,
            "run_id": training_run.run_id,
            "status": training_run.status,
            "checks": {
                "manifest_exists": True,
                "manifest_valid": True,
                "stage1_present": training_run.manifest.stage1 is not None,
                "stage2_present": training_run.manifest.stage2 is not None
            },
            "errors": []
        }

        # Validate stage artifacts if present
        if training_run.manifest.stage1:
            try:
                training_run.stage1_adapters_path
                result["checks"]["stage1_adapters_valid"] = True
            except ValueError as e:
                result["checks"]["stage1_adapters_valid"] = False
                result["errors"].append(f"Stage 1 adapters: {e}")

        if training_run.manifest.stage2:
            try:
                training_run.stage2_final_model_path
                result["checks"]["stage2_model_valid"] = True
            except ValueError as e:
                result["checks"]["stage2_model_valid"] = False
                result["errors"].append(f"Stage 2 model: {e}")

        # Overall validation
        result["valid"] = len(result["errors"]) == 0

        return result

    except Exception as e:
        return {
            "valid": False,
            "run_id": "unknown",
            "status": "error",
            "checks": {"manifest_exists": False},
            "errors": [str(e)]
        }