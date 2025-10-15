"""
HuggingFace Public Dataset Loader for Sequential Fine-Tuning

Loads CrossVul and CVEfixes datasets from HuggingFace and transforms them
to ChatML format for Stage 1 training (General Security Education).

Datasets:
- hitoshura25/crossvul: 9,313 vulnerability/fix pairs
- hitoshura25/cvefixes: 12,987 CVE fixes (5GB - uses streaming)
"""

import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datasets import load_dataset
import random

logger = logging.getLogger(__name__)


class PublicDatasetLoader:
    """
    Loads public vulnerability datasets from HuggingFace and transforms
    them to ChatML format for training.

    Uses intelligent adaptive loading based on available disk space:
    - >10GB free: Full download with caching (fastest for repeated runs)
    - 3-10GB free: Batched streaming (balanced)
    - <3GB free: Single-item streaming or error
    """

    # Dataset size constants (in GB)
    CROSSVUL_SIZE_GB = 0.234  # 234 MB
    CVEFIXES_SIZE_GB = 5.0    # 5 GB

    # Disk space thresholds (in GB)
    FULL_DOWNLOAD_THRESHOLD_GB = 10.0
    BATCHED_STREAMING_THRESHOLD_GB = 3.0

    # Batched streaming configuration
    BATCH_SIZE = 100

    def __init__(self, config=None):
        """
        Initialize the public dataset loader.

        Args:
            config: Optional OLMoSecurityConfig instance. If not provided, creates default config.
                   Used to ensure token filtering uses the same model ID as training.
        """
        from config_manager import OLMoSecurityConfig

        self.config = config or OLMoSecurityConfig()
        self.crossvul_dataset_name = "hitoshura25/crossvul"
        self.cvefixes_dataset_name = "hitoshura25/cvefixes"

    def _get_available_disk_space_gb(self) -> float:
        """
        Get available disk space in GB for the HuggingFace cache directory.

        Returns:
            Available disk space in GB
        """
        # HuggingFace datasets cache to ~/.cache/huggingface/datasets/
        cache_dir = Path.home() / ".cache" / "huggingface" / "datasets"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Get disk usage statistics
        stat = shutil.disk_usage(cache_dir)
        available_gb = stat.free / (1024 ** 3)

        return available_gb

    def _determine_loading_strategy(self, dataset_size_gb: float, dataset_name: str) -> str:
        """
        Determine optimal loading strategy based on available disk space.

        Args:
            dataset_size_gb: Size of dataset in GB
            dataset_name: Name of dataset (for logging)

        Returns:
            Loading strategy: "full", "batched", or "streaming"
        """
        available_gb = self._get_available_disk_space_gb()

        logger.info(f"📊 Disk space analysis for {dataset_name}:")
        logger.info(f"   Dataset size: {dataset_size_gb:.2f} GB")
        logger.info(f"   Available space: {available_gb:.2f} GB")

        if available_gb >= self.FULL_DOWNLOAD_THRESHOLD_GB:
            logger.info(f"   ✅ Strategy: FULL DOWNLOAD (sufficient space)")
            logger.info(f"   ⚠️  First run will download {dataset_size_gb:.2f} GB and cache to ~/.cache/huggingface/datasets/")
            logger.info(f"   ⚠️  Subsequent runs will use cached version (no download)")
            return "full"

        elif available_gb >= self.BATCHED_STREAMING_THRESHOLD_GB:
            logger.info(f"   ⚙️  Strategy: BATCHED STREAMING (moderate space)")
            logger.info(f"   Batch size: {self.BATCH_SIZE} examples per network request")
            logger.info(f"   Memory usage: ~{self.BATCH_SIZE * 0.5:.1f} MB (vs {dataset_size_gb * 1024:.0f} MB for full download)")
            return "batched"

        else:
            logger.warning(f"   ⚠️  Strategy: SINGLE-ITEM STREAMING (low disk space)")
            logger.warning(f"   This will be slow due to network I/O per example")
            logger.warning(f"   Consider freeing up disk space for better performance")

            if available_gb < dataset_size_gb:
                raise RuntimeError(
                    f"Insufficient disk space for {dataset_name}!\n"
                    f"   Required: {dataset_size_gb:.2f} GB\n"
                    f"   Available: {available_gb:.2f} GB\n"
                    f"   Please free up at least {dataset_size_gb - available_gb:.2f} GB"
                )

            return "streaming"

    def load_crossvul(self, max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load CrossVul dataset from HuggingFace.

        CrossVul contains 9,313 vulnerability/fix pairs across 158 CWE types
        and 21 programming languages.

        Args:
            max_examples: Optional limit on number of examples to load

        Returns:
            List of examples in ChatML format
        """
        logger.info(f"Loading CrossVul dataset from {self.crossvul_dataset_name}")

        try:
            # Load dataset (234MB - small enough to load fully)
            dataset = load_dataset(self.crossvul_dataset_name, split="train")
            logger.info(f"CrossVul dataset size: {len(dataset)} examples downloaded")

            examples = []
            for idx, example in enumerate(dataset):
                if max_examples and idx >= max_examples:
                    break

                logger.debug(f"Processing CrossVul example {idx + 1}/{len(dataset)}")
                chatml_example = self._crossvul_to_chatml(example)
                logger.debug(f"Transformed example created for example {idx + 1}")
                if chatml_example:
                    examples.append(chatml_example)

            logger.info(f"Created {len(examples)} examples from CrossVul")
            return examples

        except Exception as e:
            logger.error(f"Failed to load CrossVul dataset: {e}")
            raise

    def load_cvefixes(self, max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load CVEfixes dataset from HuggingFace with intelligent adaptive loading.

        CVEfixes contains 12,987 CVE fixes (5GB dataset). Loading strategy is
        automatically determined based on available disk space:
        - >10GB free: Full download with caching (fastest)
        - 3-10GB free: Batched streaming (balanced)
        - <3GB free: Single-item streaming (slowest)

        Args:
            max_examples: Optional limit on number of examples to load

        Returns:
            List of examples in ChatML format
        """
        logger.info(f"Loading CVEfixes dataset from {self.cvefixes_dataset_name}")

        # Determine loading strategy based on disk space
        strategy = self._determine_loading_strategy(
            self.CVEFIXES_SIZE_GB,
            "CVEfixes"
        )

        try:
            if strategy == "full":
                return self._load_cvefixes_full(max_examples)
            elif strategy == "batched":
                return self._load_cvefixes_batched(max_examples)
            else:  # streaming
                return self._load_cvefixes_streaming(max_examples)

        except Exception as e:
            logger.error(f"Failed to load CVEfixes dataset: {e}")
            raise

    def _process_cvefixes_examples(
        self,
        dataset_iterator,
        max_examples: Optional[int] = None,
        total_hint: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Common processing logic for CVEfixes examples.

        Handles transformation, filtering, and progress logging for any iterator
        of CVEfixes examples.

        Args:
            dataset_iterator: Iterator yielding CVEfixes examples
            max_examples: Optional limit on number of examples to process
            total_hint: Optional total count for enhanced progress display

        Returns:
            List of transformed ChatML examples
        """
        examples = []
        processed = 0

        for example in dataset_iterator:
            if max_examples and processed >= max_examples:
                break

            logger.debug(f"Processing CVEfixes example {processed + 1}")
            chatml_example = self._cvefixes_to_chatml(example)

            if chatml_example:
                examples.append(chatml_example)

            processed += 1

            # Log progress every 1000 examples
            if processed % 1000 == 0:
                progress_msg = f"Processed {processed}"
                if total_hint:
                    progress_msg += f"/{total_hint}"
                progress_msg += " CVEfixes examples..."
                logger.info(progress_msg)

        logger.info(f"Created {len(examples)} examples from CVEfixes")
        return examples

    def _load_cvefixes_full(self, max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load CVEfixes with full download and caching."""
        logger.info("📥 Downloading CVEfixes dataset (full download mode)...")

        dataset = load_dataset(self.cvefixes_dataset_name, split="train")
        logger.info(f"✅ CVEfixes downloaded: {len(dataset)} examples available")

        total = min(len(dataset), max_examples) if max_examples else len(dataset)
        return self._process_cvefixes_examples(dataset, max_examples, total)

    def _load_cvefixes_batched(self, max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load CVEfixes with batched streaming."""
        logger.info(f"📥 Loading CVEfixes dataset (batched streaming mode, batch_size={self.BATCH_SIZE})...")

        dataset = load_dataset(
            self.cvefixes_dataset_name,
            split="train",
            streaming=True
        )

        # Flatten batches into single iterator
        def batch_iterator():
            for batch in dataset.iter(batch_size=self.BATCH_SIZE):
                yield from batch

        return self._process_cvefixes_examples(batch_iterator(), max_examples)

    def _load_cvefixes_streaming(self, max_examples: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load CVEfixes with single-item streaming (slowest, minimal memory)."""
        logger.info("📥 Loading CVEfixes dataset (single-item streaming mode)...")

        dataset = load_dataset(
            self.cvefixes_dataset_name,
            split="train",
            streaming=True
        )

        return self._process_cvefixes_examples(dataset, max_examples)

    def load_all_public_datasets(self,
                                  max_crossvul: Optional[int] = None,
                                  max_cvefixes: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load both CrossVul and CVEfixes datasets, combine and shuffle.

        This creates the complete Stage 1 training dataset for general
        security education (~22K examples total).

        Args:
            max_crossvul: Optional limit for CrossVul examples
            max_cvefixes: Optional limit for CVEfixes examples

        Returns:
            Combined and shuffled list of examples in ChatML format
        """
        # Show total dataset size upfront
        total_size_gb = self.CROSSVUL_SIZE_GB + self.CVEFIXES_SIZE_GB
        available_gb = self._get_available_disk_space_gb()

        logger.info("=" * 80)
        logger.info("📚 Loading Public Datasets for Stage 1 Training")
        logger.info("=" * 80)
        logger.info(f"Total dataset size: {total_size_gb:.2f} GB")
        logger.info(f"  - CrossVul: {self.CROSSVUL_SIZE_GB:.3f} GB (~9,313 examples)")
        logger.info(f"  - CVEfixes: {self.CVEFIXES_SIZE_GB:.2f} GB (~12,987 examples)")
        logger.info(f"Available disk space: {available_gb:.2f} GB")
        logger.info("=" * 80)

        # Load CrossVul
        crossvul_examples = self.load_crossvul(max_examples=max_crossvul)

        # Load CVEfixes
        cvefixes_examples = self.load_cvefixes(max_examples=max_cvefixes)

        # Combine datasets
        logger.info("Combining CrossVul and CVEfixes datasets")
        all_examples = crossvul_examples + cvefixes_examples

        # Filter long sequences before shuffling
        logger.info("=" * 80)
        logger.info("🔍 Filtering sequences exceeding token limit")
        logger.info("=" * 80)
        filtered_examples, token_filter_stats = self._filter_long_sequences(all_examples)

        # Shuffle to mix sources
        logger.info("Shuffling combined dataset")
        random.shuffle(filtered_examples)

        logger.info(f"✅ Total public dataset examples: {len(filtered_examples)}")
        logger.info(f"   CrossVul: {len(crossvul_examples)}, CVEfixes: {len(cvefixes_examples)}")
        logger.info(f"   Token filtered: {token_filter_stats['filtered_examples']} examples")
        logger.info(f"   Final training set: {len(filtered_examples)} examples")

        return filtered_examples

    def _crossvul_to_chatml(self, example: Dict) -> Optional[Dict[str, Any]]:
        """
        Transform CrossVul record to ChatML format.

        CrossVul schema:
        - vulnerable_code: Code with vulnerability
        - fixed_code: Patched code
        - cwe_id: CWE identifier
        - cwe_name: CWE description
        - language: Programming language
        - vulnerability_description: Description of the issue

        ChatML format:
        {
            "messages": [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ],
            "metadata": {...}
        }

        Args:
            example: Raw CrossVul example

        Returns:
            ChatML formatted example or None if transformation fails
        """
        try:
            vulnerable_code = example.get("vulnerable_code", "").strip()
            fixed_code = example.get("fixed_code", "").strip()
            cwe_id = example.get("cwe_id", "Unknown")
            cwe_name = example.get("cwe_name", "Unknown vulnerability")
            language = example.get("language", "unknown")
            description = example.get("vulnerability_description", "")

            # Skip if essential fields are missing
            if not vulnerable_code or not fixed_code:
                return None

            # System message
            system_message = (
                "You are a security-focused code analysis assistant. "
                "Analyze code for vulnerabilities and provide secure fixes."
            )

            # User message - present the vulnerable code
            user_message = f"Analyze this {language} code for security vulnerabilities:\n\n```{language}\n{vulnerable_code}\n```"

            # Assistant message - provide analysis and fix
            assistant_parts = []

            if description:
                assistant_parts.append(f"Security Issue: {description}")
            else:
                assistant_parts.append(f"Security Issue: {cwe_name} ({cwe_id})")

            assistant_parts.append(f"\nFixed Code:\n```{language}\n{fixed_code}\n```")

            assistant_message = "\n".join(assistant_parts)

            return {
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message}
                ],
                "metadata": {
                    "quality": "high",
                    "source": "crossvul",
                    "cwe_id": cwe_id,
                    "cwe_name": cwe_name,
                    "language": language
                }
            }

        except Exception as e:
            logger.warning(f"Failed to transform CrossVul example: {e}")
            return None

    def _cvefixes_to_chatml(self, example: Dict) -> Optional[Dict[str, Any]]:
        """
        Transform CVEfixes record to ChatML format.

        CVEfixes schema:
        - vulnerable_code: Code with vulnerability
        - fixed_code: Patched code
        - cve_id: CVE identifier
        - cwe_id: CWE identifier (optional)
        - language: Programming language
        - vulnerability_description: Description of the issue

        Args:
            example: Raw CVEfixes example

        Returns:
            ChatML formatted example or None if transformation fails
        """
        try:
            vulnerable_code = example.get("vulnerable_code", "").strip()
            fixed_code = example.get("fixed_code", "").strip()
            cve_id = example.get("cve_id", "Unknown")
            cwe_id = example.get("cwe_id", "Unknown")
            language = example.get("language", "unknown")
            description = example.get("vulnerability_description", "")

            # Skip if essential fields are missing
            if not vulnerable_code or not fixed_code:
                return None

            # System message
            system_message = (
                "You are a security-focused code analysis assistant. "
                "Analyze code for vulnerabilities and provide secure fixes."
            )

            # User message - present the vulnerable code
            user_message = f"Analyze this {language} code for security vulnerabilities:\n\n```{language}\n{vulnerable_code}\n```"

            # Assistant message - provide analysis and fix
            assistant_parts = []

            if description:
                assistant_parts.append(f"Security Issue: {description}")

            # Include CVE/CWE identifiers
            identifiers = []
            if cve_id != "Unknown":
                identifiers.append(cve_id)
            if cwe_id != "Unknown":
                identifiers.append(cwe_id)

            if identifiers:
                if not description:
                    assistant_parts.append(f"Security Issue: {', '.join(identifiers)}")
                else:
                    assistant_parts[0] += f" ({', '.join(identifiers)})"

            assistant_parts.append(f"\nFixed Code:\n```{language}\n{fixed_code}\n```")

            assistant_message = "\n".join(assistant_parts)

            return {
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message}
                ],
                "metadata": {
                    "quality": "high",
                    "source": "cvefixes",
                    "cve_id": cve_id,
                    "cwe_id": cwe_id,
                    "language": language
                }
            }

        except Exception as e:
            logger.warning(f"Failed to transform CVEfixes example: {e}")
            return None

    def _chatml_to_text(self, example: Dict[str, Any]) -> str:
        """
        Convert ChatML format to text for token counting.

        Matches the format that MLX will use during training with ChatML template.

        Args:
            example: ChatML-formatted example

        Returns:
            Text representation matching MLX training format
        """
        messages = example.get("messages", [])
        text_parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            # Format matching ChatML template structure used in training
            text_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")

        return "\n".join(text_parts)

    def _filter_long_sequences(
        self,
        examples: List[Dict[str, Any]],
        max_tokens: int = 2048,
        model_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter out training examples that exceed token limit.

        Uses AutoTokenizer for exact token counting matching MLX training tokenization.
        This prevents MLX truncation warnings during training.

        Args:
            examples: List of ChatML-formatted examples
            max_tokens: Maximum token limit (default 2048 for MLX)
            model_id: HuggingFace model ID for tokenizer. If None, uses config.base_model_hf_id

        Returns:
            Tuple of (filtered_examples, statistics)
        """
        from transformers import AutoTokenizer

        # Use configured model ID if not explicitly provided
        if model_id is None:
            model_id = self.config.base_model_hf_id

        logger.info(f"🔍 Filtering sequences longer than {max_tokens} tokens...")
        logger.info(f"   Using tokenizer: {model_id}")

        # Load tokenizer using pattern from old implementation
        logger.debug(f"Loading tokenizer for model {model_id}...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=True
        )
        logger.debug("Tokenizer loaded successfully.")

        filtered_examples = []
        too_long_examples = []
        token_length_distribution = []
        examples_length = len(examples)

        for idx, example in enumerate(examples):
            logger.debug(f"Generating chatml text for example {idx + 1}/{examples_length}")
            # Convert ChatML messages to text for tokenization
            text = self._chatml_to_text(example)

            # Count tokens using exact same tokenizer as MLX
            logger.debug(f"Encoding example")
            tokens = tokenizer.encode(text, add_special_tokens=True)
            token_count = len(tokens)
            token_length_distribution.append(token_count)

            if token_count <= max_tokens:
                filtered_examples.append(example)
            else:
                too_long_examples.append({
                    "index": idx,
                    "token_count": token_count,
                    "source": example.get("metadata", {}).get("source", "unknown"),
                    "cwe_id": example.get("metadata", {}).get("cwe_id", "unknown")
                })

        # Calculate statistics
        stats = {
            "total_examples": len(examples),
            "kept_examples": len(filtered_examples),
            "filtered_examples": len(too_long_examples),
            "filter_percentage": (len(too_long_examples) / len(examples) * 100) if examples else 0,
            "min_tokens": min(token_length_distribution) if token_length_distribution else 0,
            "max_tokens": max(token_length_distribution) if token_length_distribution else 0,
            "mean_tokens": sum(token_length_distribution) / len(token_length_distribution) if token_length_distribution else 0,
            "filtered_breakdown": too_long_examples[:10]  # Show first 10 filtered examples
        }

        logger.info(f"✅ Token filtering complete:")
        logger.info(f"   Kept: {stats['kept_examples']} examples")
        logger.info(f"   Filtered: {stats['filtered_examples']} examples (>{max_tokens} tokens)")
        logger.info(f"   Filter rate: {stats['filter_percentage']:.2f}%")
        logger.info(f"   Token range: {stats['min_tokens']}-{stats['max_tokens']} tokens")
        logger.info(f"   Mean: {stats['mean_tokens']:.0f} tokens")

        if stats['filtered_examples'] > 0:
            logger.info(f"   Sample filtered examples:")
            for filtered_ex in stats['filtered_breakdown'][:5]:
                logger.info(f"      - Index {filtered_ex['index']}: {filtered_ex['token_count']} tokens "
                           f"(source: {filtered_ex['source']}, cwe: {filtered_ex['cwe_id']})")

        return filtered_examples, stats
