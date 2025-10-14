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
class SequentialStageManifest:
    """Sequential stage manifest for Stage 1 and Stage 2"""
    adapters_path: str = ""
    training_data_path: str = ""
    evaluation_results_path: str = ""
    training_params: Dict[str, Any] = None
    dataset_stats: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "adapters_path": self.adapters_path,
            "training_data_path": self.training_data_path,
            "evaluation_results_path": self.evaluation_results_path,
            "training_params": self.training_params or {},
            "dataset_stats": self.dataset_stats or {},
        }


@dataclass
class RunManifest:
    """Training run manifest schema v2.0 for sequential fine-tuning"""
    version: str = "2.0"
    run_id: str = ""
    timestamp: str = ""
    base_model: str = ""
    pipeline_type: str = "sequential"
    stage1: Optional[SequentialStageManifest] = None
    stage2: Optional[SequentialStageManifest] = None
    final_model_path: str = "./final-model"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        manifest_dict = {
            "version": self.version,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "base_model": self.base_model,
            "pipeline_type": self.pipeline_type,
            "final_model_path": self.final_model_path,
        }

        # Add stage manifests if present
        if self.stage1:
            manifest_dict["stage1"] = self.stage1.to_dict()
        if self.stage2:
            manifest_dict["stage2"] = self.stage2.to_dict()

        return manifest_dict


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
        """Load manifest from JSON file (v2.0 format only)"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Run manifest not found: {self.manifest_path}")

        try:
            with open(self.manifest_path, 'r') as f:
                manifest_data = json.load(f)

            logger.info(f"📋 Loaded manifest for run: {manifest_data.get('run_id', 'unknown')}")

            # Load v2.0 manifest with sequential stages
            stage1_data = manifest_data.get("stage1")
            stage2_data = manifest_data.get("stage2")

            stage1 = None
            if stage1_data:
                stage1 = SequentialStageManifest(
                    adapters_path=stage1_data.get("adapters_path", ""),
                    training_data_path=stage1_data.get("training_data_path", ""),
                    evaluation_results_path=stage1_data.get("evaluation_results_path", ""),
                    training_params=stage1_data.get("training_params", {}),
                    dataset_stats=stage1_data.get("dataset_stats", {}),
                )

            stage2 = None
            if stage2_data:
                stage2 = SequentialStageManifest(
                    adapters_path=stage2_data.get("adapters_path", ""),
                    training_data_path=stage2_data.get("training_data_path", ""),
                    evaluation_results_path=stage2_data.get("evaluation_results_path", ""),
                    training_params=stage2_data.get("training_params", {}),
                    dataset_stats=stage2_data.get("dataset_stats", {}),
                )

            manifest = RunManifest(
                version=manifest_data.get("version", "2.0"),
                run_id=manifest_data.get("run_id", ""),
                timestamp=manifest_data.get("timestamp", ""),
                base_model=manifest_data.get("base_model", ""),
                pipeline_type=manifest_data.get("pipeline_type", "sequential"),
                stage1=stage1,
                stage2=stage2,
                final_model_path=manifest_data.get("final_model_path", "./final-model"),
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
    def stage1_adapters_path(self) -> Path:
        """Get path to Stage 1 adapter artifacts"""
        if not self.manifest.stage1:
            raise ValueError("Stage 1 not configured in manifest")
        return self.run_dir / self.manifest.stage1.adapters_path

    @property
    def stage1_training_data_path(self) -> Path:
        """Get path to Stage 1 training data directory"""
        if not self.manifest.stage1:
            raise ValueError("Stage 1 not configured in manifest")
        return self.run_dir / self.manifest.stage1.training_data_path

    @property
    def stage1_evaluation_path(self) -> Path:
        """Get path to Stage 1 evaluation results"""
        if not self.manifest.stage1:
            raise ValueError("Stage 1 not configured in manifest")
        return self.run_dir / self.manifest.stage1.evaluation_results_path

    @property
    def stage2_adapters_path(self) -> Path:
        """Get path to Stage 2 adapter artifacts"""
        if not self.manifest.stage2:
            raise ValueError("Stage 2 not configured in manifest")
        return self.run_dir / self.manifest.stage2.adapters_path

    @property
    def stage2_training_data_path(self) -> Path:
        """Get path to Stage 2 training data directory"""
        if not self.manifest.stage2:
            raise ValueError("Stage 2 not configured in manifest")
        return self.run_dir / self.manifest.stage2.training_data_path

    @property
    def stage2_evaluation_path(self) -> Path:
        """Get path to Stage 2 evaluation results"""
        if not self.manifest.stage2:
            raise ValueError("Stage 2 not configured in manifest")
        return self.run_dir / self.manifest.stage2.evaluation_results_path

    @property
    def final_model_path(self) -> Path:
        """Get path to final merged model"""
        return self.run_dir / self.manifest.final_model_path

    def prepare_stage_training_data(
        self,
        stage_training_data_path: Path,
        train_dataset: Path,
        validation_dataset: Path
    ) -> Path:
        """
        Copy and rename datasets to MLX-required format for a specific stage.

        MLX LoRA expects train.jsonl and valid.jsonl in the training data directory.

        Args:
            stage_training_data_path: Path to stage's training data directory
            train_dataset: Path to original train_dataset.jsonl
            validation_dataset: Path to original validation_dataset.jsonl

        Returns:
            Path to training data directory containing train.jsonl and valid.jsonl
        """
        logger.info(f"📂 Preparing stage training data: {stage_training_data_path}")

        # Create training data directory
        stage_training_data_path.mkdir(parents=True, exist_ok=True)

        # Copy and rename to MLX-required names
        train_target = stage_training_data_path / "train.jsonl"
        valid_target = stage_training_data_path / "valid.jsonl"

        logger.info(f"   Copying {train_dataset.name} → train.jsonl")
        shutil.copy2(train_dataset, train_target)

        logger.info(f"   Copying {validation_dataset.name} → valid.jsonl")
        shutil.copy2(validation_dataset, valid_target)

        logger.info(f"   ✅ Training data prepared: {stage_training_data_path}")
        logger.info(f"      - train.jsonl: {train_target.stat().st_size} bytes")
        logger.info(f"      - valid.jsonl: {valid_target.stat().st_size} bytes")

        return stage_training_data_path


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

    def create_sequential_run(self, run_id: Optional[str] = None) -> TrainingRun:
        """
        Create new sequential training run with stage1/stage2 directory structure.

        Creates directory structure:
        webauthn-security-sequential-YYYYMMDD_HHMMSS/
        ├── run-manifest.json (v2.0)
        ├── stage1/
        │   ├── adapters/
        │   ├── training-data/
        │   └── evaluation/
        ├── stage2/
        │   ├── adapters/
        │   ├── training-data/
        │   └── evaluation/
        └── final-model/

        Args:
            run_id: Optional run ID (defaults to timestamp)

        Returns:
            TrainingRun instance with sequential structure
        """
        # Generate run ID if not provided
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        run_dir = self.fine_tuned_models_dir / f"webauthn-security-sequential-{run_id}"

        if run_dir.exists():
            logger.warning(f"Training run directory already exists: {run_dir}")

        # Create training run instance
        training_run = TrainingRun(run_dir)

        # Create v2.0 manifest with stage1 and stage2
        stage1_manifest = SequentialStageManifest(
            adapters_path="./stage1/adapters",
            training_data_path="./stage1/training-data",
            evaluation_results_path="./stage1/evaluation",
            training_params={},
            dataset_stats={},
        )

        stage2_manifest = SequentialStageManifest(
            adapters_path="./stage2/adapters",
            training_data_path="./stage2/training-data",
            evaluation_results_path="./stage2/evaluation",
            training_params={},
            dataset_stats={},
        )

        manifest = RunManifest(
            version="2.0",
            run_id=f"webauthn-security-sequential-{run_id}",
            timestamp=datetime.now().isoformat(),
            base_model=self.config.default_base_model,
            pipeline_type="sequential",
            stage1=stage1_manifest,
            stage2=stage2_manifest,
            final_model_path="./final-model",
        )

        training_run._manifest = manifest
        training_run.save_manifest()

        # Create stage directories
        training_run.stage1_adapters_path.mkdir(parents=True, exist_ok=True)
        training_run.stage1_training_data_path.mkdir(parents=True, exist_ok=True)
        training_run.stage1_evaluation_path.mkdir(parents=True, exist_ok=True)

        training_run.stage2_adapters_path.mkdir(parents=True, exist_ok=True)
        training_run.stage2_training_data_path.mkdir(parents=True, exist_ok=True)
        training_run.stage2_evaluation_path.mkdir(parents=True, exist_ok=True)

        training_run.final_model_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"🚀 Created new sequential training run: {run_id}")
        logger.info(f"   Directory: {run_dir}")
        logger.info(f"   Stage 1: {training_run.stage1_training_data_path}")
        logger.info(f"   Stage 2: {training_run.stage2_training_data_path}")
        logger.info(f"   Final model: {training_run.final_model_path}")

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

    def evaluate(self, training_run: TrainingRun, test_dataset: Path, stage: int = 1) -> Dict[str, Any]:
        """
        Evaluate the trained model and save results to run directory.

        Creates {run_dir}/stageN/evaluation/ with:
        - evaluation_results.json (metrics, detailed results)
        - model_evaluation/ (debug files per test case)

        Args:
            training_run: TrainingRun instance with trained adapters
            test_dataset: Path to test dataset JSONL file
            stage: Stage number (1 or 2) for sequential training runs

        Returns:
            Dictionary with evaluation results and metrics
        """
        from evaluate_model import evaluate_model

        # Determine adapter path based on stage
        if stage == 1:
            adapter_path = training_run.stage1_adapters_path
            eval_dir = training_run.stage1_evaluation_path
        elif stage == 2:
            adapter_path = training_run.stage2_adapters_path
            eval_dir = training_run.stage2_evaluation_path
        else:
            raise ValueError(f"Invalid stage: {stage}. Must be 1 or 2.")

        # Create evaluation directory in training run
        eval_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"🔬 Evaluating Stage {stage} model...")
        logger.info(f"   Adapter path: {adapter_path}")
        logger.info(f"   Evaluation output: {eval_dir}")

        # Run evaluation with output in training run directory
        results = evaluate_model(
            model_path=adapter_path,
            test_dataset=test_dataset,
            output_file=eval_dir / "evaluation_results.json"
        )

        logger.info(f"✅ Stage {stage} evaluation complete. Results saved to: {eval_dir}")

        return results
