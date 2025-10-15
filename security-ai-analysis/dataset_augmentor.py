#!/usr/bin/env python3
"""
Data Augmentation for Security Training Datasets

Implements research-backed augmentation techniques to increase training data
quality and quantity for small security vulnerability datasets.

Research Foundation:
- IEEE 2024: Self-mixup achieves 1.84-4.66% accuracy improvements
- MIT TACL: Token-level augmentations for supervised learning
- Theodo Research: Support set augmentation 48% → 81% accuracy

Techniques:
- Self-mixup: Blend variations of same vulnerability
- Semantic variations: Paraphrase security terminology
- Context blending: Combine similar vulnerability types

Usage:
    from dataset_augmentor import SecurityDataAugmentor

    augmentor = SecurityDataAugmentor(config)
    augmented_data = augmentor.augment_training_data(original_examples)
"""

import logging
import random
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class AugmentationConfig:
    """Configuration for data augmentation."""

    enabled: bool = True
    multiplier: int = 4                      # Target: 4x total examples
    mixup_alpha: float = 0.3                 # Optimal mixing ratio
    semantic_variations: int = 3              # Variations per technique

    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]) -> 'AugmentationConfig':
        """Create from configuration dictionary."""
        aug_config = config_dict.get('augmentation', {})
        return cls(
            enabled=aug_config.get('enabled', True),
            multiplier=aug_config.get('multiplier', 4),
            mixup_alpha=aug_config.get('mixup_alpha', 0.3),
            semantic_variations=aug_config.get('semantic_variations', 3)
        )


class SecurityDataAugmentor:
    """
    Security-focused data augmentation for small training datasets.

    Implements 2024-2025 research techniques optimized for security
    vulnerability analysis with limited examples.
    """

    def __init__(self, config: Optional[AugmentationConfig] = None):
        """Initialize the security data augmentor."""
        self.config = config or AugmentationConfig()
        self.logger = logging.getLogger(__name__)

        # Security terminology semantic patterns
        self.semantic_patterns = {
            'paraphrase': [
                ('vulnerability', 'security flaw'),
                ('exploit', 'attack vector'),
                ('mitigation', 'remediation'),
                ('validation', 'verification'),
                ('configuration', 'setup'),
                ('fix', 'remediation'),
                ('issue', 'problem'),
                ('secure', 'safe'),
                ('implement', 'apply'),
                ('code', 'implementation')
            ],
            'technical_detail': [
                ('high severity', 'critical impact potential'),
                ('input validation', 'user input sanitization'),
                ('authentication', 'identity verification'),
                ('authorization', 'access control'),
                ('encryption', 'cryptographic protection'),
                ('dependency', 'package'),
                ('version', 'release'),
                ('update', 'upgrade'),
                ('patch', 'fix'),
                ('vulnerable', 'exposed to attack')
            ],
            'severity_perspective': [
                ('potential impact', 'security risk level'),
                ('attack vector', 'exploitation method'),
                ('remediation steps', 'security implementation'),
                ('vulnerable component', 'affected system'),
                ('security control', 'protective measure'),
                ('threat', 'security risk'),
                ('weakness', 'vulnerability'),
                ('defense', 'protection'),
                ('exposure', 'attack surface'),
                ('risk', 'threat level')
            ]
        }

    def augment_training_data(self, training_examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply comprehensive data augmentation to training examples.

        Args:
            training_examples: Original training examples in ChatML format

        Returns:
            Augmented training examples (target: 3x original count)
        """
        if not self.config.enabled:
            self.logger.info("⏭️  Data augmentation disabled")
            return []

        original_count = len(training_examples)
        target_count = original_count * (self.config.multiplier - 1)  # -1 because originals already added

        self.logger.info(f"🎨 Starting data augmentation: {original_count} → target {target_count} new examples")

        augmented_examples = []

        # Phase 1: Semantic variations (most diverse)
        self.logger.info("📝 Phase 1: Generating semantic variations...")
        semantic_examples = self._apply_semantic_variations(training_examples)
        augmented_examples.extend(semantic_examples)

        # Phase 2: Self-mixup augmentation
        self.logger.info("🔄 Phase 2: Applying self-mixup augmentation...")
        mixup_examples = self._apply_self_mixup(training_examples)
        augmented_examples.extend(mixup_examples)

        # Phase 3: Context blending (if needed to reach target)
        remaining = target_count - len(augmented_examples)
        if remaining > 0:
            self.logger.info(f"🎯 Phase 3: Context blending ({remaining} examples needed)...")
            blended_examples = self._apply_context_blending(training_examples, remaining)
            augmented_examples.extend(blended_examples)

        # Quality filtering and deduplication
        final_examples = self._ensure_quality_and_diversity(augmented_examples, training_examples)

        augmentation_ratio = (original_count + len(final_examples)) / original_count
        self.logger.info(f"✅ Augmentation complete: {original_count} → +{len(final_examples)} augmented ({augmentation_ratio:.1f}x total)")

        return final_examples

    def _apply_semantic_variations(self, examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate semantic variations by paraphrasing security terminology."""
        augmented = []

        for example in examples:
            # Generate TWO variations of each type per example (2x increase)
            for variation_type in ['paraphrase', 'technical_detail', 'severity_perspective']:
                for _ in range(2):  # Create 2 variants of each type
                    try:
                        varied = self._create_semantic_variant(example, variation_type)
                        if varied:
                            augmented.append(varied)
                    except Exception as e:
                        self.logger.warning(f"Failed to create semantic variation: {e}")
                        continue

        self.logger.info(f"   ✅ Generated {len(augmented)} semantic variations")
        return augmented

    def _apply_self_mixup(self, examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply self-mixup augmentation to create blended variants."""
        augmented = []

        for example in examples:
            # Create mixup variant with configured alpha
            try:
                mixed = self._create_mixup_variant(example, self.config.mixup_alpha)
                if mixed:
                    augmented.append(mixed)
            except Exception as e:
                self.logger.warning(f"Failed to create mixup variant: {e}")
                continue

        self.logger.info(f"   ✅ Generated {len(augmented)} self-mixup variants")
        return augmented

    def _apply_context_blending(self, examples: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
        """Blend contexts from similar vulnerability types."""
        # Group by tool/category
        grouped = self._group_by_category(examples)

        augmented = []
        attempts = 0
        max_attempts = target_count * 2  # Prevent infinite loop

        while len(augmented) < target_count and attempts < max_attempts:
            attempts += 1

            # Pick random category with multiple examples
            categories_with_multiple = [cat for cat, exs in grouped.items() if len(exs) >= 2]
            if not categories_with_multiple:
                break

            category = random.choice(categories_with_multiple)
            category_examples = grouped[category]

            # Blend two random examples
            ex1, ex2 = random.sample(category_examples, 2)
            try:
                blended = self._blend_two_examples(ex1, ex2)
                if blended:
                    augmented.append(blended)
            except Exception as e:
                self.logger.warning(f"Failed to blend examples: {e}")
                continue

        self.logger.info(f"   ✅ Generated {len(augmented)} context-blended variants")
        return augmented

    def _create_semantic_variant(self, example: Dict[str, Any], variation_type: str) -> Optional[Dict[str, Any]]:
        """Create semantic variation of an example."""
        messages = example.get('messages', [])
        if not messages:
            return None

        # Apply semantic patterns to user and assistant messages
        varied_messages = []
        for msg in messages:
            content = msg.get('content', '')
            role = msg.get('role')

            # Don't modify system message
            if role == 'system':
                varied_messages.append(msg)
            else:
                varied_content = self._apply_semantic_patterns(content, variation_type)
                varied_messages.append({**msg, 'content': varied_content})

        # Create varied example with updated metadata
        metadata = example.get('metadata', {}).copy()
        metadata['augmentation_type'] = f'semantic_{variation_type}'
        metadata['source'] = 'augmented'

        return {
            'messages': varied_messages,
            'metadata': metadata
        }

    def _create_mixup_variant(self, example: Dict[str, Any], mix_ratio: float) -> Optional[Dict[str, Any]]:
        """Create self-mixup variant by varying instruction phrasing."""
        messages = example.get('messages', [])
        if not messages:
            return None

        # Apply subtle variations to user prompt
        mixed_messages = []
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content', '')

            if role == 'user':
                # Add variation to user prompt structure
                mixed_content = self._vary_prompt_structure(content)
                mixed_messages.append({**msg, 'content': mixed_content})
            else:
                mixed_messages.append(msg)

        # Create mixed example
        metadata = example.get('metadata', {}).copy()
        metadata['augmentation_type'] = 'self_mixup'
        metadata['mix_ratio'] = mix_ratio
        metadata['source'] = 'augmented'

        return {
            'messages': mixed_messages,
            'metadata': metadata
        }

    def _blend_two_examples(self, ex1: Dict[str, Any], ex2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Blend two examples from same category."""
        # Extract user prompts
        user1 = self._extract_user_message(ex1)
        user2 = self._extract_user_message(ex2)

        if not user1 or not user2:
            return None

        # Create blended prompt (first 2 lines from each)
        lines1 = user1.split('\n')[:2]
        lines2 = user2.split('\n')[:2]

        blended_prompt = f"{lines1[0]}\n{lines2[0]}\n\nAnalyze these related security issues and provide comprehensive remediation."

        # Use assistant response from first example
        messages = ex1.get('messages', []).copy()
        for i, msg in enumerate(messages):
            if msg.get('role') == 'user':
                messages[i] = {**msg, 'content': blended_prompt}
                break

        # Create blended example
        metadata = ex1.get('metadata', {}).copy()
        metadata['augmentation_type'] = 'context_blending'
        metadata['source'] = 'augmented'

        return {
            'messages': messages,
            'metadata': metadata
        }

    def _apply_semantic_patterns(self, content: str, pattern_type: str) -> str:
        """Apply semantic patterns to vary content while preserving meaning."""
        if pattern_type not in self.semantic_patterns:
            return content

        patterns = self.semantic_patterns[pattern_type]
        varied_content = content

        # Apply random subset of patterns (30-50% of available patterns)
        num_patterns = max(1, int(len(patterns) * random.uniform(0.3, 0.5)))
        applied_patterns = random.sample(patterns, num_patterns)

        for original, replacement in applied_patterns:
            # Case-insensitive replacement with word boundaries
            pattern = re.compile(r'\b' + re.escape(original) + r'\b', re.IGNORECASE)

            # Only replace first occurrence to maintain some original terminology
            varied_content = pattern.sub(replacement, varied_content, count=1)

        return varied_content

    def _vary_prompt_structure(self, prompt: str) -> str:
        """Add subtle variations to prompt structure."""
        # Alternate prompt introductions
        introductions = [
            "Fix the following security vulnerability:",
            "Address this security issue:",
            "Remediate the following vulnerability:",
            "Resolve this security problem:",
            "Fix the following security issue:"
        ]

        # Replace first line if it matches known pattern
        lines = prompt.split('\n')
        if lines and any(intro in lines[0] for intro in ["Fix the following", "Address this"]):
            lines[0] = random.choice(introductions)

        return '\n'.join(lines)

    def _extract_user_message(self, example: Dict[str, Any]) -> Optional[str]:
        """Extract user message content from example."""
        messages = example.get('messages', [])
        for msg in messages:
            if msg.get('role') == 'user':
                return msg.get('content', '')
        return None

    def _group_by_category(self, examples: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group examples by security category or tool."""
        grouped = {}

        for example in examples:
            metadata = example.get('metadata', {})

            # Group by tool or security_category
            category = metadata.get('tool', metadata.get('security_category', 'general'))

            if category not in grouped:
                grouped[category] = []

            grouped[category].append(example)

        return grouped

    def _ensure_quality_and_diversity(
        self,
        augmented: List[Dict[str, Any]],
        originals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ensure quality and remove near-duplicates."""
        # Combine for deduplication check
        all_examples = originals + augmented

        # Remove duplicates based on content similarity
        unique_augmented = []
        seen_hashes = set()

        # First, add all original hashes to seen set
        for example in originals:
            content_hash = self._create_content_hash(example)
            seen_hashes.add(content_hash)

        # Then filter augmented examples
        for example in augmented:
            content_hash = self._create_content_hash(example)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_augmented.append(example)

        removed = len(augmented) - len(unique_augmented)
        if removed > 0:
            self.logger.info(f"   🧹 Quality filtering: removed {removed} duplicates")

        return unique_augmented

    def _create_content_hash(self, example: Dict[str, Any]) -> int:
        """Create simple hash of example content for deduplication."""
        messages = example.get('messages', [])
        content_parts = []

        for msg in messages:
            role = msg.get('role', '')
            # Use first 150 chars for hash (captures key differences)
            content = msg.get('content', '')[:150]
            content_parts.append(f"{role}:{content}")

        return hash('|'.join(content_parts))
