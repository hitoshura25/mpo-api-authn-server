#!/usr/bin/env python3
"""
MLX-Optimized Fine-Tuning for Security Analysis Models

Simplified trainer for Phase 4 of the security analysis pipeline.
Implements quality-weighted sampling per gemini-refactor-plan.md requirements.
"""

import json
import logging
import subprocess
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os

# Configure tokenizer parallelism
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MLX availability check
try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    logger.warning("⚠️  MLX not available. Fine-tuning requires MLX installation on Apple Silicon.")


class MLXTrainer:
    """Simplified MLX trainer for security analysis models with quality-weighted sampling"""

    def __init__(self, config, output_dir: Path):
        """
        Initialize MLX trainer with configuration.

        Args:
            config: OLMoSecurityConfig instance
            output_dir: Where to save fine-tuned adapter
        """
        if not MLX_AVAILABLE:
            raise RuntimeError("MLX not available. Fine-tuning requires MLX on Apple Silicon.")

        self.config = config
        self.output_dir = output_dir

        # Get training parameters from config
        self.base_model_path = config.get_base_model_path()
        self.learning_rate = config.fine_tuning.learning_rate
        self.batch_size = config.fine_tuning.batch_size
        self.num_iters = config.fine_tuning.max_stage1_iters
        self.quality_weight_multiplier = 2.5  # Fixed for now

        logger.info(f"MLXTrainer initialized:")
        logger.info(f"  Base model: {self.base_model_path}")
        logger.info(f"  Output dir: {output_dir}")
        logger.info(f"  Learning rate: {self.learning_rate}")
        logger.info(f"  Batch size: {self.batch_size}")
        logger.info(f"  Iterations: {self.num_iters}")
        logger.info(f"  Quality weight multiplier: {self.quality_weight_multiplier}x")

    def apply_quality_weighted_sampling(self,
                                       train_dataset: Path,
                                       output_path: Path) -> Dict[str, int]:
        """
        Apply quality-weighted sampling to training dataset.

        High quality examples (from public datasets and generated fixes) are duplicated
        to ensure the model learns preferentially from real fixes.

        Args:
            train_dataset: Path to original train_dataset.jsonl
            output_path: Path to save weighted train_dataset.jsonl

        Returns:
            Statistics about the sampling
        """
        logger.info("📊 Applying quality-weighted sampling...")

        examples = []
        quality_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}

        # Load all examples
        with open(train_dataset, 'r') as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)
                    examples.append(example)

                    # Track quality distribution
                    quality = example.get('metadata', {}).get('quality', 'unknown')
                    quality_counts[quality] = quality_counts.get(quality, 0) + 1

        logger.info(f"   Loaded {len(examples)} examples")
        logger.info(f"   Quality distribution: {quality_counts}")

        # Apply weighted sampling
        weighted_examples = []

        for example in examples:
            quality = example.get('metadata', {}).get('quality', 'unknown')
            source = example.get('metadata', {}).get('source', 'unknown')

            # Always include the example once
            weighted_examples.append(example)

            # Duplicate ONLY original high-quality examples (not augmented)
            # Augmented examples already provide diversity, we want to emphasize real fixes
            if quality == 'high' and source != 'augmented':
                # Add (multiplier - 1) additional copies
                duplicates = int(self.quality_weight_multiplier - 1)
                for _ in range(duplicates):
                    weighted_examples.append(example)

        # Shuffle to mix high/low quality examples
        random.shuffle(weighted_examples)

        # Save weighted dataset
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            for example in weighted_examples:
                f.write(json.dumps(example) + '\n')

        # Count augmented vs original for reporting
        augmented_count = sum(1 for ex in examples if ex.get('metadata', {}).get('source') == 'augmented')
        original_count = len(examples) - augmented_count

        logger.info(f"   ✅ Weighted dataset saved: {output_path}")
        logger.info(f"   Original dataset: {len(examples)} examples ({original_count} original, {augmented_count} augmented)")
        logger.info(f"   Weighted dataset: {len(weighted_examples)} examples")
        logger.info(f"   High-quality boost: {self.quality_weight_multiplier}x (original examples only)")

        return {
            "original_count": len(examples),
            "weighted_count": len(weighted_examples),
            "quality_distribution": quality_counts
        }

    def prepare_mlx_dataset(self,
                           train_dataset: Path,
                           validation_dataset: Path,
                           temp_dir: Path) -> Path:
        """
        Prepare datasets in MLX format with quality-weighted sampling.

        Args:
            train_dataset: Path to train_dataset.jsonl
            validation_dataset: Path to validation_dataset.jsonl
            temp_dir: Temporary directory for MLX-formatted data

        Returns:
            Path to MLX data directory containing train.jsonl and valid.jsonl
        """
        logger.info("🔧 Preparing MLX dataset...")

        mlx_data_dir = temp_dir / "mlx_data"
        mlx_data_dir.mkdir(parents=True, exist_ok=True)

        # Apply quality-weighted sampling to training data
        weighted_train = mlx_data_dir / "train.jsonl"
        sampling_stats = self.apply_quality_weighted_sampling(train_dataset, weighted_train)

        # Copy validation data as-is (no weighting)
        logger.info("📋 Copying validation dataset...")
        with open(validation_dataset, 'r') as fin, open(mlx_data_dir / "valid.jsonl", 'w') as fout:
            validation_count = 0
            for line in fin:
                if line.strip():
                    fout.write(line)
                    validation_count += 1

        logger.info(f"   ✅ Validation dataset: {validation_count} examples")
        logger.info(f"   ✅ MLX data prepared: {mlx_data_dir}")

        return mlx_data_dir

    def run_mlx_training(self, mlx_data_dir: Path) -> Path:
        """
        Execute MLX LoRA fine-tuning.

        Args:
            mlx_data_dir: Directory containing train.jsonl and valid.jsonl

        Returns:
            Path to trained adapter directory
        """
        logger.info("🚀 Starting MLX LoRA fine-tuning...")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Build MLX LoRA command
        command = [
            "python", "-m", "mlx_lm", "lora",
            "--model", str(self.base_model_path),
            "--train",
            "--data", str(mlx_data_dir),
            "--adapter-path", str(self.output_dir),
            "--batch-size", str(self.batch_size),
            "--iters", str(self.num_iters),
            "--learning-rate", str(self.learning_rate),
            "--fine-tune-type", "lora",
            "--optimizer", "adamw"
        ]

        logger.info(f"   Command: {' '.join(command)}")
        logger.info(f"   Base model: {self.base_model_path}")
        logger.info(f"   Training data: {mlx_data_dir}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info(f"   Iterations: {self.num_iters}")
        logger.info(f"   Batch size: {self.batch_size}")
        logger.info(f"   Learning rate: {self.learning_rate}")

        try:
            # Execute MLX training
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )

            # Log training output
            if result.stdout:
                logger.debug(f"Training output:\n{result.stdout}")

            return self.output_dir

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ MLX training failed with exit code {e.returncode}")
            logger.error(f"   stdout: {e.stdout}")
            logger.error(f"   stderr: {e.stderr}")
            raise RuntimeError(f"MLX training failed: {e.stderr}")

    def train(self, training_data_dir: Path) -> Path:
        """
        Complete training workflow with quality-weighted sampling.

        Args:
            training_data_dir: Path to directory containing train.jsonl and valid.jsonl

        Returns:
            Path to trained model artifacts
        """
        logger.info("=" * 60)
        logger.info("🎓 Phase 4: Train Model")
        logger.info("=" * 60)

        # Verify MLX-formatted data files exist
        train_file = training_data_dir / "train.jsonl"
        valid_file = training_data_dir / "valid.jsonl"

        if not train_file.exists():
            raise FileNotFoundError(f"Training file not found: {train_file}")
        if not valid_file.exists():
            raise FileNotFoundError(f"Validation file not found: {valid_file}")

        logger.info(f"Training data directory: {training_data_dir}")
        logger.info(f"  - train.jsonl: {train_file.stat().st_size} bytes")
        logger.info(f"  - valid.jsonl: {valid_file.stat().st_size} bytes")

        # Step 1: Apply quality-weighted sampling to training data
        weighted_train_file = training_data_dir / "train_weighted.jsonl"
        self.apply_quality_weighted_sampling(train_file, weighted_train_file)

        # Rename weighted file to train.jsonl for MLX
        train_file.unlink()  # Remove original
        weighted_train_file.rename(train_file)  # Use weighted version

        # Step 2: Run MLX training
        adapter_path = self.run_mlx_training(training_data_dir)

        # Step 3: Save training metadata
        self._save_training_metadata(adapter_path, training_data_dir)

        logger.info("✅ MLX training completed successfully")
        logger.info(f"   Adapter saved: {self.output_dir}")

        return adapter_path

    def _save_training_metadata(self,
                                adapter_path: Path,
                                training_data_dir: Path):
        """Save training metadata for reproducibility"""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "base_model": str(self.base_model_path),
            "training_data_dir": str(training_data_dir),
            "hyperparameters": {
                "learning_rate": self.learning_rate,
                "batch_size": self.batch_size,
                "num_iters": self.num_iters,
                "quality_weight_multiplier": self.quality_weight_multiplier
            },
            "adapter_path": str(adapter_path)
        }

        metadata_file = adapter_path / "training_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"   Training metadata saved: {metadata_file}")

    # ======================================================================
    # Sequential Fine-Tuning Methods (2-Stage Pipeline)
    # ======================================================================

    def train_stage1(self,
                     training_run,
                     stage1_train_dataset: Path,
                     stage1_validation_dataset: Path) -> Path:
        """
        Train Stage 1: General Security Education on Public Datasets.

        Trains from base model on CrossVul + CVEfixes datasets (~22K examples).
        Uses existing train() method internally.

        Args:
            training_run: TrainingRun instance with stage1 configuration
            stage1_train_dataset: Path to Stage 1 training dataset
            stage1_validation_dataset: Path to Stage 1 validation dataset

        Returns:
            Path to Stage 1 adapter artifacts
        """
        logger.info("=" * 80)
        logger.info("🎓 STAGE 1: General Security Education (Public Datasets)")
        logger.info("=" * 80)

        # Prepare Stage 1 training data in run directory
        training_run.prepare_stage_training_data(
            training_run.stage1_training_data_path,
            stage1_train_dataset,
            stage1_validation_dataset
        )

        # Update output_dir to Stage 1 adapters path
        original_output_dir = self.output_dir
        self.output_dir = training_run.stage1_adapters_path

        # Update iterations from config for Stage 1
        original_iters = self.num_iters
        self.num_iters = self.config.fine_tuning.max_stage1_iters

        try:
            # Run training using existing train() method
            adapter_path = self.train(training_run.stage1_training_data_path)

            logger.info("✅ Stage 1 training completed")
            logger.info(f"   Adapter saved: {adapter_path}")

            return adapter_path

        finally:
            # Restore original settings
            self.output_dir = original_output_dir
            self.num_iters = original_iters

    def train_stage2(self,
                     training_run,
                     stage2_train_dataset: Path,
                     stage2_validation_dataset: Path,
                     stage1_adapter_path: Path) -> Path:
        """
        Train Stage 2: WebAuthn Domain Specialization with Replay.

        Continues training from Stage 1 adapter on WebAuthn-specific data
        mixed with 15% Stage 1 replay to prevent catastrophic forgetting.
        Uses --resume-adapter-file to continue from Stage 1.

        Args:
            training_run: TrainingRun instance with stage2 configuration
            stage2_train_dataset: Path to Stage 2 training dataset (with 15% replay)
            stage2_validation_dataset: Path to Stage 2 validation dataset
            stage1_adapter_path: Path to Stage 1 adapter to resume from

        Returns:
            Path to Stage 2 adapter artifacts
        """
        logger.info("=" * 80)
        logger.info("🎯 STAGE 2: WebAuthn Domain Specialization (15% Replay)")
        logger.info("=" * 80)

        # Prepare Stage 2 training data in run directory
        training_run.prepare_stage_training_data(
            training_run.stage2_training_data_path,
            stage2_train_dataset,
            stage2_validation_dataset
        )

        # Update output_dir to Stage 2 adapters path
        original_output_dir = self.output_dir
        self.output_dir = training_run.stage2_adapters_path

        # Update iterations and learning rate from config for Stage 2
        original_iters = self.num_iters
        original_lr = self.learning_rate

        self.num_iters = self.config.fine_tuning.max_stage2_iters
        self.learning_rate = self.config.fine_tuning.stage2_learning_rate

        try:
            # Run MLX training with adapter resumption
            adapter_path = self.run_mlx_training_with_resume(
                training_run.stage2_training_data_path,
                stage1_adapter_path
            )

            # Save training metadata
            self._save_training_metadata(adapter_path, training_run.stage2_training_data_path)

            logger.info("✅ Stage 2 training completed")
            logger.info(f"   Adapter saved: {adapter_path}")

            return adapter_path

        finally:
            # Restore original settings
            self.output_dir = original_output_dir
            self.num_iters = original_iters
            self.learning_rate = original_lr

    def run_mlx_training_with_resume(self,
                                      mlx_data_dir: Path,
                                      resume_adapter_path: Path) -> Path:
        """
        Execute MLX LoRA fine-tuning with adapter resumption.

        Uses --resume-adapter-file to continue training from a previous adapter,
        enabling Stage 2 to build on Stage 1 knowledge.

        Args:
            mlx_data_dir: Directory containing train.jsonl and valid.jsonl
            resume_adapter_path: Path to adapter to resume from (Stage 1)

        Returns:
            Path to trained adapter directory
        """
        logger.info("🚀 Starting MLX LoRA fine-tuning with adapter resumption...")
        logger.info(f"   Resuming from: {resume_adapter_path}")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Build MLX LoRA command with --resume-adapter-file
        command = [
            "python", "-m", "mlx_lm", "lora",
            "--model", str(self.base_model_path),
            "--train",
            "--data", str(mlx_data_dir),
            "--adapter-path", str(self.output_dir),
            "--resume-adapter-file", str(resume_adapter_path / "adapters.safetensors"),
            "--batch-size", str(self.batch_size),
            "--iters", str(self.num_iters),
            "--learning-rate", str(self.learning_rate),
            "--fine-tune-type", "lora",
            "--optimizer", "adamw"
        ]

        logger.info(f"   Command: {' '.join(command)}")
        logger.info(f"   Base model: {self.base_model_path}")
        logger.info(f"   Training data: {mlx_data_dir}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info(f"   Resume from: {resume_adapter_path}")
        logger.info(f"   Iterations: {self.num_iters}")
        logger.info(f"   Batch size: {self.batch_size}")
        logger.info(f"   Learning rate: {self.learning_rate}")

        try:
            # Execute MLX training
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )

            # Log training output
            if result.stdout:
                logger.debug(f"Training output:\n{result.stdout}")

            return self.output_dir

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ MLX training with resumption failed with exit code {e.returncode}")
            logger.error(f"   stdout: {e.stdout}")
            logger.error(f"   stderr: {e.stderr}")
            raise RuntimeError(f"MLX training with resumption failed: {e.stderr}")


def main():
    """CLI entry point for standalone testing"""
    import argparse

    parser = argparse.ArgumentParser(description="MLX Trainer for Security Analysis Models")
    parser.add_argument("--base-model", type=Path, required=True,
                       help="Path to base OLMo model")
    parser.add_argument("--train-dataset", type=Path, required=True,
                       help="Path to train_dataset.jsonl")
    parser.add_argument("--validation-dataset", type=Path, required=True,
                       help="Path to validation_dataset.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True,
                       help="Output directory for trained adapter")
    parser.add_argument("--learning-rate", type=float, default=1e-5,
                       help="Learning rate (default: 1e-5)")
    parser.add_argument("--batch-size", type=int, default=4,
                       help="Batch size (default: 4)")
    parser.add_argument("--iters", type=int, default=1000,
                       help="Number of training iterations (default: 1000)")
    parser.add_argument("--quality-weight", type=float, default=2.5,
                       help="Quality weight multiplier for high-quality examples (default: 2.5)")

    args = parser.parse_args()

    # Initialize trainer
    trainer = MLXTrainer(
        base_model_path=args.base_model,
        output_dir=args.output_dir,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        num_iters=args.iters,
        quality_weight_multiplier=args.quality_weight
    )

    # Run training
    adapter_path = trainer.train(args.train_dataset, args.validation_dataset)

    print(f"\n✅ Training complete! Adapter saved to: {adapter_path}")


if __name__ == "__main__":
    main()
