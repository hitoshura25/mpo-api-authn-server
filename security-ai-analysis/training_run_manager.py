#!/usr/bin/env python3
"""
Training Run Manager - Simplified for Phase 4 Single-Stage Training

Manages structured training run directories with manifest-based artifact tracking.
Handles MLX data format requirements (train.jsonl/valid.jsonl).
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RunManifest:
    """Training run manifest schema for Phase 4"""
    version: str = "1.0"
    run_id: str = ""
    timestamp: str = ""
    base_model: str = ""
    training_params: Dict[str, Any] = None
    adapters_path: str = "./adapters"
    training_data_path: str = "./training-data"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "base_model": self.base_model,
            "training_params": self.training_params or {},
            "adapters_path": self.adapters_path,
            "training_data_path": self.training_data_path
        }


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

            logger.info(f"📋 Loaded manifest for run: {manifest_data.get('run_id', 'unknown')}")

            # Convert to dataclass structure
            manifest = RunManifest(
                version=manifest_data.get("version", "1.0"),
                run_id=manifest_data.get("run_id", ""),
                timestamp=manifest_data.get("timestamp", ""),
                base_model=manifest_data.get("base_model", ""),
                training_params=manifest_data.get("training_params", {}),
                adapters_path=manifest_data.get("adapters_path", "./adapters"),
                training_data_path=manifest_data.get("training_data_path", "./training-data")
            )

            return manifest

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            raise ValueError(f"Invalid manifest format in {self.manifest_path}: {e}")

    def save_manifest(self) -> None:
        """Save manifest to JSON file"""
        if self._manifest is None:
            raise RuntimeError("No manifest to save - create manifest first")

        # Ensure run directory exists
        self.run_dir.mkdir(parents=True, exist_ok=True)

        with open(self.manifest_path, 'w') as f:
            json.dump(self._manifest.to_dict(), f, indent=2)

        logger.info(f"💾 Saved manifest: {self.manifest_path}")

    @property
    def run_id(self) -> str:
        """Get run ID from manifest"""
        return self.manifest.run_id

    @property
    def adapters_path(self) -> Path:
        """Get path to adapter artifacts"""
        return self.run_dir / self.manifest.adapters_path

    @property
    def training_data_path(self) -> Path:
        """Get path to training data directory"""
        return self.run_dir / self.manifest.training_data_path

    def prepare_training_data(self, train_dataset: Path, validation_dataset: Path) -> Path:
        """
        Copy and rename datasets to MLX-required format.

        MLX LoRA expects train.jsonl and valid.jsonl in the training data directory.

        Args:
            train_dataset: Path to original train_dataset.jsonl
            validation_dataset: Path to original validation_dataset.jsonl

        Returns:
            Path to training data directory containing train.jsonl and valid.jsonl
        """
        logger.info("📂 Preparing training data for MLX format...")

        # Create training data directory
        training_data_dir = self.training_data_path
        training_data_dir.mkdir(parents=True, exist_ok=True)

        # Copy and rename to MLX-required names (keep originals pristine)
        train_target = training_data_dir / "train.jsonl"
        valid_target = training_data_dir / "valid.jsonl"

        logger.info(f"   Copying {train_dataset.name} → train.jsonl")
        shutil.copy2(train_dataset, train_target)

        logger.info(f"   Copying {validation_dataset.name} → valid.jsonl")
        shutil.copy2(validation_dataset, valid_target)

        logger.info(f"   ✅ Training data prepared: {training_data_dir}")
        logger.info(f"      - train.jsonl: {train_target.stat().st_size} bytes")
        logger.info(f"      - valid.jsonl: {valid_target.stat().st_size} bytes")

        return training_data_dir


class TrainingRunManager:
    """Manager for training runs with structured output"""

    def __init__(self, config):
        """
        Initialize training run manager with configuration

        Args:
            config: OLMoSecurityConfig instance
        """
        self.config = config
        self.fine_tuned_models_dir = config.fine_tuned_models_dir

        # Ensure fine-tuned models directory exists
        self.fine_tuned_models_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"🏗️ TrainingRunManager initialized: {self.fine_tuned_models_dir}")

    def create_run(self,
                   train_dataset: Path,
                   validation_dataset: Path,
                   run_id: Optional[str] = None,
                   training_params: Optional[Dict[str, Any]] = None) -> TrainingRun:
        """
        Create new training run with structured directory and manifest.

        Args:
            train_dataset: Path to training dataset
            validation_dataset: Path to validation dataset
            run_id: Optional run ID (defaults to timestamp)
            training_params: Optional training parameters to store in manifest

        Returns:
            TrainingRun instance with prepared data directory
        """
        # Generate run ID if not provided
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        run_dir = self.fine_tuned_models_dir / f"webauthn-security-{run_id}"

        if run_dir.exists():
            logger.warning(f"Training run directory already exists: {run_dir}")

        # Create training run instance
        training_run = TrainingRun(run_dir)

        # Create manifest
        manifest = RunManifest(
            run_id=f"webauthn-security-{run_id}",
            timestamp=datetime.now().isoformat(),
            base_model=self.config.default_base_model,
            training_params=training_params or {},
            adapters_path="./adapters",
            training_data_path="./training-data"
        )

        training_run._manifest = manifest
        training_run.save_manifest()

        # Prepare training data (copy and rename to MLX format)
        training_run.prepare_training_data(train_dataset, validation_dataset)

        logger.info(f"🚀 Created new training run: {run_id}")
        logger.info(f"   Directory: {run_dir}")
        logger.info(f"   Training data: {training_run.training_data_path}")
        logger.info(f"   Adapters: {training_run.adapters_path}")

        return training_run

    def get_latest_run(self) -> TrainingRun:
        """Get most recent training run"""
        run_dirs = list(self.fine_tuned_models_dir.glob("webauthn-security-*"))

        if not run_dirs:
            raise FileNotFoundError("No training runs found")

        # Sort by directory name (which includes timestamp)
        run_dirs.sort()
        latest_dir = run_dirs[-1]

        logger.info(f"📋 Found latest run: {latest_dir.name}")
        return TrainingRun(latest_dir)

    def get_run_by_id(self, run_id: str) -> TrainingRun:
        """Get specific run by ID"""
        # Handle both formats: "webauthn-security-ID" and just "ID"
        if not run_id.startswith("webauthn-security-"):
            run_id = f"webauthn-security-{run_id}"

        run_dir = self.fine_tuned_models_dir / run_id

        if not run_dir.exists():
            raise FileNotFoundError(f"Training run not found: {run_id}")

        return TrainingRun(run_dir)
