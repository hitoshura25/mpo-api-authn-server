#!/usr/bin/env python3
"""
Model Evaluation Script

Evaluates a fine-tuned OLMo model on a held-out test dataset using:
1. Exact Match Accuracy - Character-for-character comparison
2. CodeBLEU - Semantic/structural code similarity (AST, data flow, n-grams)

Usage:
    python evaluate_model.py \
        --model-path /path/to/adapters \
        --test-dataset results/test_dataset.jsonl \
        --output results/evaluation_results.json

Requirements:
    - codebleu package (pip install codebleu)
    - mlx, mlx-lm packages
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import shutil
import sys

# MLX imports
import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

# Config imports
from config_manager import OLMoSecurityConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_test_dataset(test_file: Path) -> List[Dict[str, Any]]:
    """Load test dataset from JSONL file."""
    logger.info(f"Loading test dataset from {test_file}")

    test_cases = []
    with open(test_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    test_case = json.loads(line)
                    test_cases.append(test_case)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON on line {line_num}: {e}")
                    raise

    logger.info(f"Loaded {len(test_cases)} test examples")
    return test_cases


def calculate_exact_match(generated: str, expected: str) -> bool:
    """Calculate exact match (character-for-character equality)."""
    return generated.strip() == expected.strip()


def calculate_codebleu(generated: str, expected: str) -> float:
    """
    Calculate CodeBLEU score for semantic code similarity.

    CodeBLEU combines:
    - n-gram matching (like BLEU)
    - Abstract Syntax Tree (AST) matching
    - Data flow matching

    Returns score between 0.0 and 1.0
    """
    try:
        from codebleu import calc_codebleu

        # CodeBLEU expects lists of references and hypotheses
        result = calc_codebleu(
            [expected],  # References (ground truth)
            [generated],  # Hypotheses (model generated)
            lang="java",  # Default to java/kotlin-like syntax
            weights=(0.25, 0.25, 0.25, 0.25),  # Equal weights for all components
            tokenizer=None  # Use default tokenizer
        )

        return result['codebleu']
    except ImportError:
        logger.error("codebleu package not installed. Install with: pip install codebleu")
        raise
    except Exception as e:
        logger.warning(f"CodeBLEU calculation failed: {e}")
        raise

def extract_messages_and_expected(test_case: Dict[str, Any]) -> tuple[List[Dict[str, str]], str]:
    """
    Extract messages for prompt and expected assistant response from test case.

    Test cases are in ChatML format:
    {
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}  <- This is expected output
        ],
        "metadata": {...}
    }

    Returns:
        Tuple of:
        - List of messages (system + user) for chat template
        - Expected assistant response string
    """
    messages = test_case.get('messages', [])

    if not messages:
        raise ValueError("Test case has no messages")

    # Extract messages for prompt (system + user only)
    prompt_messages = []
    expected_response = None

    for msg in messages:
        role = msg.get('role')
        content = msg.get('content', '')

        if role == 'system' or role == 'user':
            prompt_messages.append({"role": role, "content": content})
        elif role == 'assistant':
            expected_response = content

    if not prompt_messages:
        raise ValueError("Test case missing system/user messages")

    if not expected_response:
        raise ValueError("Test case missing expected assistant response")

    return prompt_messages, expected_response


def evaluate_model(
    model_path: Path,
    test_dataset: Path,
    output_file: Path,
    max_tokens: int = 512,
    temperature: float = 0.0  # Use greedy decoding for deterministic results
) -> Dict[str, Any]:
    """
    Evaluate model on test dataset.

    Args:
        model_path: Path to fine-tuned model adapters
        test_dataset: Path to test_dataset.jsonl
        output_file: Path to save evaluation results
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 = greedy/deterministic)

    Returns:
        Dictionary with evaluation metrics and detailed results
    """
    logger.info("=" * 60)
    logger.info("🔬 Model Evaluation")
    logger.info("=" * 60)
    logger.info(f"Model: {model_path}")
    logger.info(f"Test dataset: {test_dataset}")
    logger.info(f"Max tokens: {max_tokens}")
    logger.info(f"Temperature: {temperature}")

    # Load test dataset
    test_cases = load_test_dataset(test_dataset)

    if not test_cases:
        raise ValueError("No test cases found in dataset")

    # Load base model with LoRA adapters applied
    config = OLMoSecurityConfig()
    base_model_path = config.get_base_model_path()

    logger.info(f"Loading base model: {base_model_path}")
    logger.info(f"Applying LoRA adapters from: {model_path}")
    try:
        model, tokenizer = load(
            path_or_hf_repo=str(base_model_path),
            adapter_path=str(model_path)
        )
        logger.info("✅ Model loaded successfully with adapters applied")
    except Exception as e:
        logger.error(f"Failed to load model with adapters: {e}")
        raise

    # Evaluation results
    results = {
        'model_path': str(model_path),
        'test_dataset': str(test_dataset),
        'total_examples': len(test_cases),
        'exact_matches': 0,
        'codebleu_scores': [],
        'detailed_results': []
    }

    debug_file_path = output_file.parent / "model_evaluation"
    if debug_file_path.exists():
        shutil.rmtree(debug_file_path)

    # Evaluate each test case
    logger.info(f"\nEvaluating {len(test_cases)} test examples...")

    for idx, test_case in enumerate(test_cases, 1):
        try:
            # Extract messages and expected output
            prompt_messages, expected_response = extract_messages_and_expected(test_case)

            # Generate response from model
            logger.info(f"\n[{idx}/{len(test_cases)}] Generating response...")

            # Apply chat template (CRITICAL: Model was trained with ChatML format)
            formatted_prompt = tokenizer.apply_chat_template(
                prompt_messages,
                tokenize=False,
                add_generation_prompt=True
            )

            # Create sampler with temperature control
            sampler = make_sampler(temp=temperature)

            generated_response = generate(
                model,
                tokenizer,
                prompt=formatted_prompt,  # Use ChatML-formatted prompt
                max_tokens=max_tokens,
                sampler=sampler,
                verbose=False
            )

            debug_file = debug_file_path /  f"test_case_{idx}_debug.txt"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, 'a') as df:
                df.write("=" * 120 + "\n")
                df.write(f"Messages (input):\n{prompt_messages}\n")
                df.write("=" * 120 + "\n")
                df.write(f"Formatted Prompt (ChatML):\n{formatted_prompt}\n")
                df.write("=" * 120 + "\n")
                df.write(f"Expected Response:\n{expected_response}\n")
                df.write("=" * 120 + "\n")
                df.write(f"Generated Response:\n{generated_response}\n")

            # Calculate metrics
            exact_match = calculate_exact_match(generated_response, expected_response)
            codebleu_score = calculate_codebleu(generated_response, expected_response)

            if exact_match:
                results['exact_matches'] += 1

            results['codebleu_scores'].append(codebleu_score)

            # Store detailed result
            detailed_result = {
                'example_id': idx,
                'tool': test_case.get('metadata', {}).get('tool', 'unknown'),
                'vulnerability_id': test_case.get('metadata', {}).get('vulnerability_id', 'unknown'),
                'security_category': test_case.get('metadata', {}).get('security_category', 'unknown'),
                'exact_match': exact_match,
                'codebleu': codebleu_score,
                'prompt_length': len(formatted_prompt),
                'generated_length': len(generated_response),
                'expected_length': len(expected_response)
            }

            results['detailed_results'].append(detailed_result)

            logger.info(f"   Exact Match: {'✅ YES' if exact_match else '❌ NO'}")
            logger.info(f"   CodeBLEU: {codebleu_score:.4f}")

        except Exception as e:
            logger.error(f"Error evaluating example {idx}: {e}")
            import traceback
            traceback.print_exc()
            raise

    # Calculate aggregate metrics
    exact_match_accuracy = results['exact_matches'] / results['total_examples'] if results['total_examples'] > 0 else 0
    avg_codebleu = sum(results['codebleu_scores']) / len(results['codebleu_scores']) if results['codebleu_scores'] else 0

    results['metrics'] = {
        'exact_match_accuracy': exact_match_accuracy,
        'exact_match_percentage': exact_match_accuracy * 100,
        'avg_codebleu': avg_codebleu,
        'min_codebleu': min(results['codebleu_scores']) if results['codebleu_scores'] else 0,
        'max_codebleu': max(results['codebleu_scores']) if results['codebleu_scores'] else 0
    }

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Examples: {results['total_examples']}")
    logger.info(f"Exact Matches: {results['exact_matches']} ({exact_match_accuracy * 100:.2f}%)")
    logger.info(f"Average CodeBLEU: {avg_codebleu:.4f}")
    logger.info(f"CodeBLEU Range: [{results['metrics']['min_codebleu']:.4f}, {results['metrics']['max_codebleu']:.4f}]")

    # Save results
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n✅ Evaluation complete. Results saved to: {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned model on test dataset")
    parser.add_argument(
        '--model-path',
        type=Path,
        required=True,
        help="Path to fine-tuned model adapters directory"
    )
    parser.add_argument(
        '--test-dataset',
        type=Path,
        required=True,
        help="Path to test_dataset.jsonl file"
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('results/evaluation_results.json'),
        help="Path to save evaluation results JSON file"
    )
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=512,
        help="Maximum tokens to generate per response"
    )
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.0,
        help="Sampling temperature (0.0 = greedy/deterministic)"
    )

    args = parser.parse_args()

    # Validate paths
    if not args.model_path.exists():
        logger.error(f"Model path does not exist: {args.model_path}")
        sys.exit(1)

    if not args.test_dataset.exists():
        logger.error(f"Test dataset does not exist: {args.test_dataset}")
        sys.exit(1)

    # Run evaluation
    try:
        evaluate_model(
            model_path=args.model_path,
            test_dataset=args.test_dataset,
            output_file=args.output,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        )
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
