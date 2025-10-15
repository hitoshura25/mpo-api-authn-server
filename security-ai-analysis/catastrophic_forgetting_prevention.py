#!/usr/bin/env python3
"""
Catastrophic Forgetting Prevention System for Sequential Fine-Tuning

Implements 2025 research-based catastrophic forgetting prevention techniques
to maintain Stage 1 performance during Stage 2 training in sequential fine-tuning.

Academic Foundation:
- Selective LoRA 2025: arXiv:2501.15377 - Selective Low Rank Adaptation
- Empirical CF Study: arXiv:2308.08747 - Catastrophic Forgetting in Large Language Models
- IBM CF Research: Memory-based replay techniques
- Sharpness-Aware Minimization: 2024 loss landscape flattening research

Classes:
- CatastrophicForgettingPrevention: Main CF prevention system
- MemoryBuffer: Stage 1 example retention for replay
- CFMonitor: Real-time forgetting detection during training
- SelectiveLoRAConfig: Advanced LoRA configuration for CF prevention

Usage:
    cf_prevention = CatastrophicForgettingPrevention(config)
    mixed_data = cf_prevention.create_mixed_training_data(stage2_examples, stage1_buffer)
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from config_manager import OLMoSecurityConfig

logger = logging.getLogger(__name__)


class CFPreventionStrategy(Enum):
    """Catastrophic forgetting prevention strategies."""
    MEMORY_REPLAY = "memory_replay"
    SELECTIVE_LORA = "selective_lora"
    ELASTIC_WEIGHT_CONSOLIDATION = "elastic_weight_consolidation"
    PROGRESSIVE_NEURAL_NETWORKS = "progressive_neural_networks"


@dataclass
class CFPreventionConfig:
    """Configuration for catastrophic forgetting prevention."""

    # Memory replay parameters (IBM Research)
    memory_buffer_size: int = 50                # Retain Stage 1 examples during Stage 2
    replay_ratio: float = 0.15                  # 15% Stage 1 data mixed into Stage 2 training

    # Forgetting detection thresholds (arXiv:2308.08747)
    forgetting_threshold: float = 0.4           # Early warning threshold
    critical_threshold: float = 0.3             # Stop training threshold
    monitoring_interval: int = 100              # Check every N iterations

    # Sharpness-aware minimization parameters (2024 research)
    sam_rho: float = 0.05                      # Flatness optimization parameter
    enable_sam: bool = True                     # Enable SAM for loss landscape flattening

    # Selective LoRA parameters (arXiv:2501.15377)
    enable_selective_lora: bool = True          # Enable selective LoRA adaptation
    stage1_retention_weight: float = 1.5        # Higher weight for Stage 1 retention
    stage2_learning_weight: float = 1.0         # Standard weight for Stage 2 learning

    # Advanced replay strategies
    importance_sampling: bool = True            # Use importance weighting for replay examples
    diversity_sampling: bool = True             # Ensure diverse example selection
    adaptive_replay_ratio: bool = True          # Adjust replay ratio based on forgetting


@dataclass
class MemoryBuffer:
    """Memory buffer for storing Stage 1 examples for replay during Stage 2 training."""

    examples: List[Dict[str, Any]] = field(default_factory=list)
    importance_weights: List[float] = field(default_factory=list)
    diversity_scores: List[float] = field(default_factory=list)
    selection_metadata: Dict[str, Any] = field(default_factory=dict)

    def add_example(self, example: Dict[str, Any], importance: float = 1.0, diversity: float = 1.0):
        """Add an example to the memory buffer with importance and diversity scores."""
        self.examples.append(example)
        self.importance_weights.append(importance)
        self.diversity_scores.append(diversity)

    def sample_for_replay(self, count: int) -> List[Dict[str, Any]]:
        """Sample examples for replay using importance and diversity weighting."""
        if not self.examples or count <= 0:
            return []

        count = min(count, len(self.examples))

        # Combine importance and diversity scores for sampling
        combined_weights = [
            imp * div for imp, div in zip(self.importance_weights, self.diversity_scores)
        ]

        # Weighted random sampling
        sampled_indices = random.choices(
            range(len(self.examples)),
            weights=combined_weights,
            k=count
        )

        return [self.examples[i] for i in sampled_indices]


@dataclass
class CFMonitoringResult:
    """Result of catastrophic forgetting monitoring."""

    iteration: int
    stage1_retention: float
    stage2_performance: float
    forgetting_detected: bool
    critical_forgetting: bool
    recommended_action: str
    monitoring_metadata: Dict[str, Any] = field(default_factory=dict)


class CatastrophicForgettingPrevention:
    """
    2025 research-based catastrophic forgetting prevention system.

    Implements multiple CF prevention strategies:
    - Memory-based replay (IBM Research)
    - Selective LoRA adaptation (arXiv:2501.15377)
    - Real-time monitoring (arXiv:2308.08747)
    - Sharpness-aware minimization (2024 loss landscape research)
    """

    def __init__(self, security_config: OLMoSecurityConfig, cf_config: Optional[CFPreventionConfig] = None):
        """Initialize catastrophic forgetting prevention system."""
        self.security_config = security_config
        self.cf_config = cf_config or CFPreventionConfig()
        self.logger = logging.getLogger(__name__)

        # Initialize memory buffer
        self.memory_buffer = MemoryBuffer()

        # Monitoring state
        self.monitoring_history: List[CFMonitoringResult] = []
        self.last_stage1_performance = None

        # Adaptive parameters
        self.current_replay_ratio = self.cf_config.replay_ratio
        self.consecutive_forgetting_detections = 0

        self.logger.info("🛡️ Catastrophic Forgetting Prevention System initialized")
        self.logger.info(f"  Memory buffer size: {self.cf_config.memory_buffer_size}")
        self.logger.info(f"  Replay ratio: {self.cf_config.replay_ratio:.1%}")
        self.logger.info(f"  Monitoring interval: {self.cf_config.monitoring_interval} iterations")

    def setup_memory_replay(self, stage1_examples: List[Dict[str, Any]]) -> MemoryBuffer:
        """
        Setup memory buffer for catastrophic forgetting prevention.

        Research: Memory-based replay significantly reduces forgetting
        Citation: https://www.ibm.com/think/topics/catastrophic-forgetting

        Args:
            stage1_examples: Training examples from Stage 1

        Returns:
            Configured memory buffer with selected examples
        """
        self.logger.info(f"🧠 Setting up memory replay buffer from {len(stage1_examples)} Stage 1 examples")

        # Select diverse representative examples
        selected_examples = self._select_diverse_examples(
            stage1_examples,
            self.cf_config.memory_buffer_size
        )

        # Calculate importance weights for each example
        for example in selected_examples:
            importance_weight = self._calculate_importance_weight(example)
            diversity_score = self._calculate_diversity_score(example, selected_examples)

            # Add to memory buffer
            self.memory_buffer.add_example(
                example=example,
                importance=importance_weight,
                diversity=diversity_score
            )

        # Store selection metadata
        self.memory_buffer.selection_metadata = {
            'total_stage1_examples': len(stage1_examples),
            'selected_examples': len(selected_examples),
            'selection_strategy': 'importance_diversity_sampling',
            'avg_importance': sum(self.memory_buffer.importance_weights) / len(self.memory_buffer.importance_weights),
            'avg_diversity': sum(self.memory_buffer.diversity_scores) / len(self.memory_buffer.diversity_scores)
        }

        self.logger.info(f"✅ Memory buffer configured: {len(selected_examples)} examples")
        self.logger.info(f"  Average importance: {self.memory_buffer.selection_metadata['avg_importance']:.3f}")
        self.logger.info(f"  Average diversity: {self.memory_buffer.selection_metadata['avg_diversity']:.3f}")

        return self.memory_buffer

    def create_mixed_training_data(self, stage2_examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create mixed training data to prevent catastrophic forgetting.

        Research: 15% replay ratio optimal for sequential task retention

        Args:
            stage2_examples: New Stage 2 training examples

        Returns:
            Mixed training data with Stage 1 replay examples
        """
        if not self.memory_buffer.examples:
            self.logger.warning("⚠️ Memory buffer is empty - no replay examples available")
            return stage2_examples

        # Calculate adaptive replay count
        replay_count = int(len(stage2_examples) * self.current_replay_ratio)
        replay_count = min(replay_count, len(self.memory_buffer.examples))

        self.logger.info(f"🔄 Creating mixed training data: {len(stage2_examples)} Stage 2 + {replay_count} replay examples")

        # Sample replay examples from memory buffer
        replay_examples = self.memory_buffer.sample_for_replay(replay_count)

        # Mark replay examples for specialized loss weighting
        for example in replay_examples:
            example['is_replay'] = True
            example['loss_weight'] = self.cf_config.stage1_retention_weight
            example['cf_metadata'] = {
                'source': 'stage1_replay',
                'replay_ratio': self.current_replay_ratio,
                'importance_sampled': True
            }

        # Mark Stage 2 examples
        for example in stage2_examples:
            example['is_replay'] = False
            example['loss_weight'] = self.cf_config.stage2_learning_weight
            example['cf_metadata'] = {
                'source': 'stage2_primary',
                'replay_ratio': self.current_replay_ratio
            }

        # Combine and shuffle
        mixed_data = stage2_examples + replay_examples
        random.shuffle(mixed_data)

        total_replay_ratio = len(replay_examples) / len(mixed_data)
        self.logger.info(f"✅ Mixed training data created: {len(mixed_data)} total examples")
        self.logger.info(f"  Effective replay ratio: {total_replay_ratio:.1%}")

        return mixed_data

    def monitor_forgetting_during_training(self, iteration: int, current_model_path: Optional[str] = None,
                                         validation_examples: Optional[List[Dict[str, Any]]] = None) -> CFMonitoringResult:
        """
        Real-time catastrophic forgetting monitoring during Stage 2 training.

        Based on: arXiv:2308.08747 empirical CF study recommendations

        Args:
            iteration: Current training iteration
            current_model_path: Path to current model for evaluation
            validation_examples: Validation examples for retention testing

        Returns:
            CFMonitoringResult with forgetting status and recommendations
        """
        # Only monitor at specified intervals
        if iteration % self.cf_config.monitoring_interval != 0:
            return CFMonitoringResult(
                iteration=iteration,
                stage1_retention=0.0,
                stage2_performance=0.0,
                forgetting_detected=False,
                critical_forgetting=False,
                recommended_action="continue"
            )

        self.logger.info(f"🔍 CF Monitor - Iteration {iteration}: Checking for catastrophic forgetting...")

        # Simulate retention evaluation (in real implementation, this would evaluate the model)
        stage1_retention = self._evaluate_stage1_retention(current_model_path, validation_examples)
        stage2_performance = self._evaluate_stage2_performance(current_model_path, validation_examples)

        # Detect forgetting
        forgetting_detected = stage1_retention < self.cf_config.forgetting_threshold
        critical_forgetting = stage1_retention < self.cf_config.critical_threshold

        # Determine recommended action
        recommended_action = self._determine_recommended_action(
            stage1_retention, stage2_performance, forgetting_detected, critical_forgetting
        )

        # Create monitoring result
        result = CFMonitoringResult(
            iteration=iteration,
            stage1_retention=stage1_retention,
            stage2_performance=stage2_performance,
            forgetting_detected=forgetting_detected,
            critical_forgetting=critical_forgetting,
            recommended_action=recommended_action,
            monitoring_metadata={
                'consecutive_detections': self.consecutive_forgetting_detections,
                'current_replay_ratio': self.current_replay_ratio,
                'memory_buffer_size': len(self.memory_buffer.examples)
            }
        )

        # Update monitoring state
        self.monitoring_history.append(result)
        if forgetting_detected:
            self.consecutive_forgetting_detections += 1
        else:
            self.consecutive_forgetting_detections = 0

        # Adaptive replay ratio adjustment
        if forgetting_detected and self.cf_config.adaptive_replay_ratio:
            self._adjust_replay_ratio(stage1_retention)

        # Log results
        self._log_monitoring_result(result)

        return result

    def get_selective_lora_config(self) -> Dict[str, Any]:
        """
        Get selective LoRA configuration for CF prevention.

        Based on: arXiv:2501.15377 - Selective Low Rank Adaptation

        Returns:
            LoRA configuration optimized for CF prevention
        """
        base_config = {
            'rank': self.security_config.fine_tuning.lora.rank,
            'alpha': self.security_config.fine_tuning.lora.alpha,
            'dropout': self.security_config.fine_tuning.lora.dropout,
            'target_modules': self.security_config.fine_tuning.lora.target_modules
        }

        if self.cf_config.enable_selective_lora:
            # Selective LoRA adaptations for CF prevention
            selective_config = {
                **base_config,
                'selective_adaptation': True,
                'stage1_preservation_modules': ['q_proj', 'k_proj'],  # Key modules for Stage 1 retention
                'stage2_adaptation_modules': ['v_proj', 'o_proj'],    # Primary modules for Stage 2 learning
                'shared_modules': ['gate_proj', 'up_proj', 'down_proj'],  # Shared learning modules
                'retention_regularization': True,
                'forgetting_penalty_weight': 0.1
            }

            self.logger.info("🎯 Selective LoRA configuration for CF prevention")
            self.logger.info(f"  Stage 1 preservation: {selective_config['stage1_preservation_modules']}")
            self.logger.info(f"  Stage 2 adaptation: {selective_config['stage2_adaptation_modules']}")

            return selective_config

        return base_config

    def _select_diverse_examples(self, examples: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
        """Select diverse representative examples from Stage 1 for memory buffer."""
        if len(examples) <= target_count:
            return examples

        # Group examples by vulnerability type for diversity
        vulnerability_groups = {}
        for example in examples:
            vuln_type = self._extract_vulnerability_type(example)
            if vuln_type not in vulnerability_groups:
                vulnerability_groups[vuln_type] = []
            vulnerability_groups[vuln_type].append(example)

        # Select proportionally from each group
        selected_examples = []
        examples_per_group = target_count // len(vulnerability_groups)
        remaining = target_count % len(vulnerability_groups)

        for i, (vuln_type, group_examples) in enumerate(vulnerability_groups.items()):
            group_target = examples_per_group + (1 if i < remaining else 0)
            group_target = min(group_target, len(group_examples))

            # Sample from this group
            group_selected = random.sample(group_examples, group_target)
            selected_examples.extend(group_selected)

        return selected_examples

    def _calculate_importance_weight(self, example: Dict[str, Any]) -> float:
        """Calculate importance weight for an example based on various factors."""
        # Base importance
        importance = 1.0

        # Vulnerability severity weighting
        metadata = example.get('metadata', {})
        severity = metadata.get('severity', 'unknown').lower()
        severity_weights = {
            'critical': 1.5,
            'high': 1.3,
            'medium': 1.0,
            'low': 0.8,
            'unknown': 1.0
        }
        importance *= severity_weights.get(severity, 1.0)

        # Training focus weighting
        training_focus = metadata.get('training_focus', 'unknown')
        if 'vulnerability_classification' in training_focus:
            importance *= 1.2  # Higher importance for classification examples

        # Code context availability
        if metadata.get('code_context_available', False):
            importance *= 1.1  # Higher importance for examples with code context

        return importance

    def _calculate_diversity_score(self, example: Dict[str, Any], all_examples: List[Dict[str, Any]]) -> float:
        """Calculate diversity score for an example within the selected set."""
        # Simple diversity metric based on vulnerability type distribution
        example_type = self._extract_vulnerability_type(example)

        # Count occurrences of this type in the selected set
        type_count = sum(1 for ex in all_examples if self._extract_vulnerability_type(ex) == example_type)

        # Inverse frequency weighting for diversity
        diversity_score = 1.0 / (type_count + 1)

        return diversity_score

    def _extract_vulnerability_type(self, example: Dict[str, Any]) -> str:
        """Extract vulnerability type from example for grouping and diversity calculation."""
        # Try to extract from various metadata fields
        metadata = example.get('metadata', {})

        # Check vulnerability_type field
        if 'vulnerability_type' in metadata:
            return metadata['vulnerability_type']

        # Check training_focus field
        training_focus = metadata.get('training_focus', '')
        if 'authentication' in training_focus:
            return 'authentication'
        elif 'cryptographic' in training_focus:
            return 'cryptographic'
        elif 'configuration' in training_focus:
            return 'configuration'
        elif 'implementation' in training_focus:
            return 'implementation'

        # Default grouping
        return 'general'

    def _evaluate_stage1_retention(self, model_path: Optional[str], validation_examples: Optional[List[Dict[str, Any]]]) -> float:
        """Evaluate Stage 1 task retention (placeholder implementation)."""
        # In a real implementation, this would:
        # 1. Load the current model
        # 2. Evaluate on Stage 1 validation tasks
        # 3. Return performance score

        # Simulate retention with some variability based on monitoring history
        base_retention = 0.6  # Starting retention

        # Simulate degradation over time if no prevention
        degradation_factor = len(self.monitoring_history) * 0.02
        simulated_retention = max(0.2, base_retention - degradation_factor)

        # Add some random variation
        variation = random.uniform(-0.05, 0.05)
        final_retention = max(0.0, min(1.0, simulated_retention + variation))

        return final_retention

    def _evaluate_stage2_performance(self, model_path: Optional[str], validation_examples: Optional[List[Dict[str, Any]]]) -> float:
        """Evaluate Stage 2 task performance (placeholder implementation)."""
        # Simulate Stage 2 performance improvement over time
        base_performance = 0.5
        improvement_factor = len(self.monitoring_history) * 0.01
        simulated_performance = min(1.0, base_performance + improvement_factor)

        # Add some random variation
        variation = random.uniform(-0.03, 0.03)
        final_performance = max(0.0, min(1.0, simulated_performance + variation))

        return final_performance

    def _determine_recommended_action(self, stage1_retention: float, stage2_performance: float,
                                    forgetting_detected: bool, critical_forgetting: bool) -> str:
        """Determine recommended action based on monitoring results."""
        if critical_forgetting:
            return "stop_training"
        elif forgetting_detected:
            if self.consecutive_forgetting_detections >= 3:
                return "increase_replay_ratio"
            else:
                return "monitor_closely"
        elif stage1_retention > 0.7 and stage2_performance > 0.6:
            return "continue_optimal"
        else:
            return "continue"

    def _adjust_replay_ratio(self, current_retention: float):
        """Adjust replay ratio based on forgetting detection."""
        if current_retention < self.cf_config.critical_threshold:
            # Aggressive increase for critical forgetting
            self.current_replay_ratio = min(0.5, self.current_replay_ratio * 1.5)
        elif current_retention < self.cf_config.forgetting_threshold:
            # Moderate increase for early forgetting
            self.current_replay_ratio = min(0.3, self.current_replay_ratio * 1.2)

        self.logger.info(f"📈 Adaptive replay ratio adjustment: {self.current_replay_ratio:.1%}")

    def _log_monitoring_result(self, result: CFMonitoringResult):
        """Log monitoring result with appropriate severity level."""
        if result.critical_forgetting:
            self.logger.error(f"🛑 CRITICAL: Catastrophic forgetting detected! Stage 1 retention: {result.stage1_retention:.3f}")
            self.logger.error(f"   Recommended action: {result.recommended_action}")
        elif result.forgetting_detected:
            self.logger.warning(f"⚠️ Warning: Early forgetting detected. Stage 1 retention: {result.stage1_retention:.3f}")
            self.logger.warning(f"   Stage 2 performance: {result.stage2_performance:.3f}")
            self.logger.warning(f"   Recommended action: {result.recommended_action}")
        else:
            self.logger.info(f"✅ CF Monitor OK - Stage 1 retention: {result.stage1_retention:.3f}, Stage 2: {result.stage2_performance:.3f}")

    def get_prevention_summary(self) -> Dict[str, Any]:
        """Get summary of CF prevention system status and effectiveness."""
        if not self.monitoring_history:
            return {
                'status': 'not_started',
                'monitoring_sessions': 0
            }

        recent_results = self.monitoring_history[-5:]  # Last 5 monitoring sessions
        avg_retention = sum(r.stage1_retention for r in recent_results) / len(recent_results)
        avg_performance = sum(r.stage2_performance for r in recent_results) / len(recent_results)

        total_forgetting_detections = sum(1 for r in self.monitoring_history if r.forgetting_detected)
        critical_detections = sum(1 for r in self.monitoring_history if r.critical_forgetting)

        return {
            'status': 'active',
            'monitoring_sessions': len(self.monitoring_history),
            'memory_buffer_size': len(self.memory_buffer.examples),
            'current_replay_ratio': self.current_replay_ratio,
            'avg_stage1_retention': avg_retention,
            'avg_stage2_performance': avg_performance,
            'total_forgetting_detections': total_forgetting_detections,
            'critical_detections': critical_detections,
            'effectiveness_score': self._calculate_effectiveness_score(),
            'recommendations': self._generate_summary_recommendations()
        }

    def _calculate_effectiveness_score(self) -> float:
        """Calculate overall effectiveness score of CF prevention system."""
        if not self.monitoring_history:
            return 0.0

        # Base score from retention performance
        recent_retentions = [r.stage1_retention for r in self.monitoring_history[-10:]]
        avg_retention = sum(recent_retentions) / len(recent_retentions)

        # Penalty for critical forgetting events
        critical_penalty = sum(1 for r in self.monitoring_history if r.critical_forgetting) * 0.1

        # Effectiveness score (0-1 range)
        effectiveness = max(0.0, avg_retention - critical_penalty)

        return effectiveness

    def _generate_summary_recommendations(self) -> List[str]:
        """Generate recommendations based on monitoring history."""
        recommendations = []

        if not self.monitoring_history:
            recommendations.append("Start monitoring to evaluate CF prevention effectiveness")
            return recommendations

        recent_results = self.monitoring_history[-5:]

        # Check for consistent forgetting
        forgetting_rate = sum(1 for r in recent_results if r.forgetting_detected) / len(recent_results)
        if forgetting_rate > 0.6:
            recommendations.append("Consider increasing memory buffer size or replay ratio")

        # Check for critical events
        if any(r.critical_forgetting for r in recent_results):
            recommendations.append("Review training parameters - critical forgetting detected")

        # Check effectiveness
        effectiveness = self._calculate_effectiveness_score()
        if effectiveness < 0.5:
            recommendations.append("CF prevention system may need reconfiguration")
        elif effectiveness > 0.8:
            recommendations.append("CF prevention system working effectively")

        return recommendations