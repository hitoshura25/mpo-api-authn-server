#!/usr/bin/env python3
"""
Unit tests for multi-domain security specialization functionality.

Tests the vulnerability categorization, enhanced dataset creation with multi-domain awareness,
and sequential fine-tuner category-aware validation.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Import the classes we're testing
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from enhanced_dataset_creator import EnhancedDatasetCreator
from vulnerability_categorizer import VulnerabilityCategorizor
from sequential_fine_tuner import SequentialFineTuner
from config_manager import OLMoSecurityConfig


class TestVulnerabilityCategorizor:
    """Test vulnerability categorization by security domain."""

    def setup_method(self):
        """Set up test fixtures."""
        self.categorizer = VulnerabilityCategorizor()

    def test_categorize_container_vulnerability(self):
        """Test categorization of container security vulnerabilities."""
        vuln = {
            'tool': 'trivy',
            'description': 'dockerfile uses root user',
            'file_path': '/path/to/Dockerfile',
            'severity': 'high'
        }

        category, confidence = self.categorizer.categorize_vulnerability(vuln)

        assert category == 'container_security'
        assert confidence > 0.6

    def test_categorize_dependency_vulnerability(self):
        """Test categorization of dependency vulnerabilities."""
        vuln = {
            'tool': 'osv-scanner',
            'description': 'vulnerable package version detected',
            'file_path': '/path/to/package.json',
            'severity': 'medium'
        }

        category, confidence = self.categorizer.categorize_vulnerability(vuln)

        assert category == 'dependency_vulnerabilities'
        assert confidence > 0.6

    def test_categorize_web_security_vulnerability(self):
        """Test categorization of web security vulnerabilities."""
        vuln = {
            'tool': 'zap',
            'description': 'missing cors headers detected',
            'file_path': '/path/to/server.js',
            'severity': 'medium'
        }

        category, confidence = self.categorizer.categorize_vulnerability(vuln)

        assert category == 'web_security'
        assert confidence >= 0.6

    def test_categorize_webauthn_vulnerability(self):
        """Test categorization of WebAuthn-specific vulnerabilities."""
        vuln = {
            'tool': 'semgrep',
            'description': 'webauthn challenge validation missing',
            'file_path': '/path/to/webauthn.js',
            'severity': 'high'
        }

        category, confidence = self.categorizer.categorize_vulnerability(vuln)

        assert category == 'webauthn_security'
        assert confidence > 0.6

    def test_categorize_mobile_security_vulnerability(self):
        """Test categorization of mobile security vulnerabilities."""
        vuln = {
            'tool': 'mobsf',
            'description': 'android exported activity without permission',
            'file_path': '/path/to/AndroidManifest.xml',
            'severity': 'high'
        }

        category, confidence = self.categorizer.categorize_vulnerability(vuln)

        assert category == 'mobile_security'
        assert confidence > 0.6

    def test_categorize_infrastructure_vulnerability(self):
        """Test categorization of infrastructure security vulnerabilities."""
        vuln = {
            'tool': 'gitleaks',
            'description': 'api key detected in source code',
            'file_path': '/path/to/config.js',
            'severity': 'critical'
        }

        category, confidence = self.categorizer.categorize_vulnerability(vuln)

        assert category == 'infrastructure_security'
        assert confidence >= 0.6

    def test_fail_fast_unknown_tool(self):
        """Test that unknown tools trigger fail-fast behavior."""
        vuln = {
            'tool': 'unknown',
            'description': 'some random vulnerability',
            'file_path': '/path/to/file.txt',
            'severity': 'low'
        }

        with pytest.raises(ValueError) as exc_info:
            self.categorizer.categorize_vulnerability(vuln)

        # Validate the error message contains expected content
        error_message = str(exc_info.value)
        assert "Unknown security tool 'unknown'" in error_message
        assert "Supported tools:" in error_message

class TestEnhancedDatasetCreatorMultiDomain:
    """Test enhanced dataset creator with multi-domain features."""

    def setup_method(self):
        """Set up test fixtures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = Path(temp_dir)
            self.creator = EnhancedDatasetCreator(
                output_dir=self.temp_dir / "datasets",
                project_root=self.temp_dir
            )

    def test_create_dataset_with_pre_categorized_vulnerabilities(self):
        """Test that dataset creation works with pre-categorized vulnerabilities."""
        # Create test vulnerabilities with security_category already assigned (as would come from Phase 2C)
        vulnerabilities = [
            {
                'id': 'test-container-1',
                'tool': 'trivy',
                'description': 'dockerfile security issue',
                'file_path': 'Dockerfile',
                'severity': 'high',
                'message': 'Container security vulnerability',
                'security_category': 'container_security',
                'category_confidence': 0.9
            },
            {
                'id': 'test-web-1',
                'tool': 'zap',
                'description': 'cors misconfiguration',
                'file_path': 'server.js',
                'severity': 'medium',
                'message': 'Web security vulnerability',
                'security_category': 'web_security',
                'category_confidence': 0.8
            },
            {
                'id': 'test-webauthn-1',
                'tool': 'semgrep',
                'description': 'webauthn challenge issue',
                'file_path': 'webauthn.js',
                'severity': 'high',
                'message': 'WebAuthn security vulnerability',
                'security_category': 'webauthn_security',
                'category_confidence': 0.85
            }
        ]

        with patch.object(self.creator.extractor, 'extract_vulnerability_context') as mock_extract:
            # Mock extraction to return no code context (simulating dependency/infrastructure vulnerabilities)
            mock_extract.return_value = Mock(success=False, error_message="Dependency/infrastructure scanner - no code context needed")

            with patch.object(self.creator.fix_generator, 'generate_fixes') as mock_generate:
                # Mock fix generation
                mock_generate.return_value = Mock(success=False, error_message="No fixes generated")

                result = self.creator.create_enhanced_dataset(vulnerabilities)

                # Verify that pre-categorized vulnerabilities were accepted
                assert hasattr(result, 'category_distribution')

                # Should preserve the pre-assigned categories
                categories = result.category_distribution
                assert 'container_security' in categories
                assert 'web_security' in categories
                assert 'webauthn_security' in categories

                # Verify vulnerabilities retain their pre-assigned categories
                assert vulnerabilities[0]['security_category'] == 'container_security'
                assert vulnerabilities[1]['security_category'] == 'web_security'
                assert vulnerabilities[2]['security_category'] == 'webauthn_security'

    def test_fail_fast_missing_security_category(self):
        """Test that EnhancedDatasetCreator fails fast when vulnerabilities lack security_category."""
        vulnerabilities = [
            {
                'id': 'missing-category-1',
                'tool': 'trivy',
                'description': 'vulnerability without security_category',
                'file_path': 'Dockerfile',
                'severity': 'high'
                # Missing: security_category field
            }
        ]

        with pytest.raises(ValueError) as exc_info:
            self.creator.create_enhanced_dataset(vulnerabilities)

        error_message = str(exc_info.value)
        assert "missing 'security_category' field" in error_message
        assert "Enhanced dataset creation requires pre-categorized input" in error_message
        assert "Run categorization in Phase 2C first" in error_message

    def test_fail_fast_unknown_security_category(self):
        """Test that EnhancedDatasetCreator fails fast when vulnerabilities have 'unknown' category."""
        vulnerabilities = [
            {
                'id': 'unknown-category-1',
                'tool': 'semgrep',
                'description': 'vulnerability with unknown category',
                'file_path': 'src/code.js',
                'severity': 'medium',
                'security_category': 'unknown'  # This should trigger fail-fast
            }
        ]

        with pytest.raises(ValueError) as exc_info:
            self.creator.create_enhanced_dataset(vulnerabilities)

        error_message = str(exc_info.value)
        assert "have 'unknown' security_category" in error_message
        assert "categorization failures that must be fixed in Phase 2C" in error_message
        assert "Cannot proceed with enhanced dataset creation" in error_message

    def test_category_specific_fix_generation(self):
        """Test that category-specific fixes are generated."""
        # Test container security fix generation
        container_fixes = self.creator._generate_category_specific_fixes(
            'container_security',
            {'file_path': 'Dockerfile', 'tool': 'trivy'},
            None,
            {}
        )

        assert len(container_fixes) > 0
        assert any('dockerfile' in fix['fixed_code'].lower() or 'user' in fix['fixed_code'].lower()
                  for fix in container_fixes)

        # Test web security fix generation
        web_fixes = self.creator._generate_category_specific_fixes(
            'web_security',
            {'file_path': 'server.js', 'tool': 'zap'},
            None,
            {}
        )

        assert len(web_fixes) > 0
        assert any('cors' in fix['fixed_code'].lower() or 'csp' in fix['fixed_code'].lower()
                  for fix in web_fixes)


class TestSequentialFineTunerMultiDomain:
    """Test sequential fine-tuner with multi-domain awareness."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock config (multi-domain always enabled)
        self.mock_config = Mock()
        self.mock_config.multi_domain = Mock()
        self.mock_config.multi_domain.target_categories = [
            'webauthn_security', 'web_security', 'code_vulnerabilities'
        ]
        self.mock_config.multi_domain.category_weights = {
            'webauthn_security': 1.5,
            'web_security': 1.2,
            'code_vulnerabilities': 1.0
        }

        # Mock other required config attributes
        self.mock_config.validation = Mock()
        self.mock_config.validation.stage2_threshold = 0.7

        # Mock fine_tuning config attributes
        self.mock_config.fine_tuning = Mock()
        self.mock_config.fine_tuning.learning_rate = 5e-6
        self.mock_config.fine_tuning.batch_size = 1
        self.mock_config.fine_tuning.save_steps = 200
        self.mock_config.fine_tuning.max_stage1_iters = 800
        self.mock_config.fine_tuning.max_stage2_iters = 1200

    def test_multi_domain_initialization(self):
        """Test that multi-domain configuration is properly loaded (always enabled)."""
        fine_tuner = SequentialFineTuner(
            config=self.mock_config,
            enable_cf_prevention=False
        )

        assert 'webauthn_security' in fine_tuner.target_categories
        assert fine_tuner.category_weights['webauthn_security'] == 1.5

    def test_category_specialization_scoring(self):
        """Test category-specific specialization scoring."""
        fine_tuner = SequentialFineTuner(
            config=self.mock_config,
            enable_cf_prevention=False
        )

        # Mock validation samples with category information
        validation_samples = [
            {
                'security_category': 'webauthn_security',
                'syntax_correctness': 0.8,
                'security_pattern_application': 0.9,
                'implementation_guidance': 0.7,
                'response': 'webauthn credential validation fix'
            },
            {
                'security_category': 'web_security',
                'syntax_correctness': 0.7,
                'security_pattern_application': 0.8,
                'implementation_guidance': 0.6,
                'response': 'cors configuration security fix'
            }
        ]

        category_scores = fine_tuner._calculate_category_specialization_scores(validation_samples)

        assert 'webauthn_security' in category_scores
        assert 'web_security' in category_scores

        # WebAuthn should have higher score due to weight
        assert category_scores['webauthn_security'] > category_scores['web_security']

    def test_multi_domain_validation_prompt_creation(self):
        """Test creation of category-specific validation prompts."""
        fine_tuner = SequentialFineTuner(
            config=self.mock_config,
            enable_cf_prevention=False
        )

        vulnerability = {
            'vulnerability_id': 'test-1',
            'description': 'test vulnerability',
            'severity': 'high'
        }

        prompt = fine_tuner._create_multi_domain_validation_prompt(vulnerability, 'webauthn_security')

        assert 'webauthn security specialist' in prompt.lower()
        assert 'webauthn_security' in prompt
        assert 'test-1' in prompt

    def test_determine_specialization_level(self):
        """Test specialization level determination based on scores."""
        fine_tuner = SequentialFineTuner(
            config=self.mock_config,
            enable_cf_prevention=False
        )

        assert fine_tuner._determine_specialization_level(0.80) == "High Specialization"
        assert fine_tuner._determine_specialization_level(0.65) == "Medium Specialization"
        assert fine_tuner._determine_specialization_level(0.45) == "Low Specialization"
        assert fine_tuner._determine_specialization_level(0.30) == "Minimal Specialization"


class TestMultiDomainConfigManager:
    """Test multi-domain configuration management."""

    def test_multi_domain_config_loading(self):
        """Test that multi-domain configuration loads properly."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
base_models_dir: "~/test-models/base"
fine_tuned_models_dir: "~/test-models/fine-tuned"
default_base_model: "OLMo-2-1B-mlx-q4"

fine_tuning:
  workspace_dir: "test-workspace"
  default_output_name: "test-model"
  training:
    learning_rate: 5e-6
    batch_size: 1
    max_epochs: 3
  lora:
    rank: 16
    alpha: 32
    dropout: 0.1
    target_modules: ["q_proj", "k_proj", "v_proj"]
  mlx:
    quantization: "q4"
    memory_efficient: true
    gradient_checkpointing: true
  huggingface:
    upload_enabled: true
    default_repo_prefix: "test"
    private_repos: false

knowledge_base:
  base_dir: "test-kb"
  embeddings_model: "sentence-transformers/all-MiniLM-L6-v2"
  vector_store_type: "faiss"

validation:
  stage1_threshold: 0.7
  stage2_threshold: 0.7
  sequential_threshold: 0.6

multi_domain:
  target_categories:
    - "webauthn_security"
    - "web_security"
    - "code_vulnerabilities"
  category_weights:
    webauthn_security: 1.5
    web_security: 1.2
    code_vulnerabilities: 1.0
  validation:
    overall_threshold: 0.75
    category_minimum: 0.40
    high_specialization: 0.75
    medium_specialization: 0.60
"""
            f.write(config_content)
            config_file = Path(f.name)

        try:
            config = OLMoSecurityConfig(config_file=config_file)

            assert hasattr(config, 'multi_domain')
            assert 'webauthn_security' in config.multi_domain.target_categories
            assert config.multi_domain.category_weights['webauthn_security'] == 1.5
            assert config.multi_domain.validation.overall_threshold == 0.75

        finally:
            config_file.unlink()  # Clean up


if __name__ == '__main__':
    pytest.main([__file__])
