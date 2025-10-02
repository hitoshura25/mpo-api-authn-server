#!/usr/bin/env python3
"""
Enhanced Dataset Creator for AI Security Enhancement

This module creates enhanced training datasets with code-aware, specific security fixes
to replace generic security advice with actionable code examples.

Classes:
- EnhancedDatasetCreator: Main class for creating enhanced training datasets
- EnhancedTrainingExample: Data class for enhanced training examples
- DatasetCreationResult: Result of dataset creation with metadata

Usage:
    creator = EnhancedDatasetCreator()
    result = creator.create_enhanced_dataset(vulnerabilities)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from vulnerable_code_extractor import VulnerableCodeExtractor, ContextExtractionResult
from multi_approach_fix_generator import MultiApproachFixGenerator, SecurityFix, FixApproach
from url_to_code_mapper import URLToCodeMapper, enhance_vulnerability_with_url_mapping
from fix_quality_assessor import FixQualityAssessor, QualityAssessmentResult
from advanced_data_augmentation import SecurityDataAugmentor, AugmentationConfig


@dataclass
class EnhancedTrainingExample:
    """
    Enhanced training example with code-aware security fixes.
    """
    instruction: str
    response: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Enhanced fields for code-aware training
    vulnerability_context: Optional[Dict[str, Any]] = None
    fix_approaches: List[Dict[str, Any]] = field(default_factory=list)
    code_examples: Dict[str, str] = field(default_factory=dict)


@dataclass
class DatasetCreationResult:
    """
    Result of enhanced dataset creation.
    """
    success: bool
    enhanced_examples: List[EnhancedTrainingExample] = field(default_factory=list)
    original_examples_count: int = 0
    enhanced_examples_count: int = 0
    error_message: Optional[str] = None
    creation_metadata: Dict[str, Any] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)  # Multi-domain enhancement
    categorized_vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)  # Reusable categorized vulnerabilities


# Import categorization from dedicated module


class EnhancedDatasetCreator:
    """
    Creates enhanced training datasets with code-aware security fixes.

    This class processes vulnerability data and generates multiple training
    examples with specific code examples for each vulnerability.
    """

    def __init__(self, output_dir: Optional[Path] = None, project_root: Optional[Path] = None):
        """
        Initialize the enhanced dataset creator.

        Args:
            output_dir: Directory for saving enhanced datasets
            project_root: Project root directory for resolving relative file paths
        """
        # Set project root - default to parent directory if running from security-ai-analysis/
        if project_root is None:
            current_dir = Path.cwd()
            if current_dir.name == "security-ai-analysis":
                project_root = current_dir.parent
            else:
                project_root = current_dir

        self.project_root = project_root
        self.extractor = VulnerableCodeExtractor(project_root=self.project_root)
        self.fix_generator = MultiApproachFixGenerator()
        self.url_mapper = URLToCodeMapper(project_root=self.project_root)  # NEW: URL mapping component
        self.quality_assessor = FixQualityAssessor()  # NEW: Quality Assessment (enabled by default)
        self.data_augmentor = SecurityDataAugmentor()  # NEW: Advanced data augmentation (Phase 2)
        self.output_dir = output_dir or Path("enhanced_datasets/code-aware-training")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Category-specific fix patterns for multi-domain specialization
        self.category_fix_patterns = {
            'container_security': {
                'user_privilege': 'Use non-root user and least privilege principles',
                'base_image': 'Use minimal, security-hardened base images',
                'layer_optimization': 'Minimize attack surface through layer optimization'
            },
            'dependency_vulnerabilities': {
                'version_pinning': 'Pin to secure versions and maintain updates',
                'dependency_scanning': 'Implement continuous dependency monitoring',
                'vulnerability_remediation': 'Apply security patches promptly'
            },
            'web_security': {
                'cors_configuration': 'Implement proper CORS policies',
                'csp_headers': 'Add Content Security Policy headers',
                'input_validation': 'Validate and sanitize all inputs'
            },
            'webauthn_security': {
                'challenge_validation': 'Ensure proper challenge validation',
                'credential_verification': 'Implement robust credential verification',
                'attestation_validation': 'Validate attestation statements'
            },
            'mobile_security': {
                'component_security': 'Secure Android components and intents',
                'permission_management': 'Implement least privilege permissions',
                'data_protection': 'Protect sensitive data storage and transmission'
            },
            'infrastructure_security': {
                'secret_management': 'Use secure secret management practices',
                'access_control': 'Implement proper access controls',
                'configuration_hardening': 'Apply security configuration standards'
            },
            'code_vulnerabilities': {
                'injection_prevention': 'Prevent injection attacks through validation',
                'secure_coding': 'Apply secure coding practices',
                'error_handling': 'Implement secure error handling'
            }
        }

    def _generate_category_specific_fixes(self, category: str, vulnerability: Dict[str, Any],
                                        code_context, fix_patterns: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Generate security fixes specialized for the vulnerability category.

        Args:
            category: Security category (e.g., 'container_security')
            vulnerability: Vulnerability data
            code_context: Extracted code context
            fix_patterns: Category-specific fix patterns

        Returns:
            List of SecurityFix-compatible dictionaries with category-specific implementations
        """
        try:
            category_patterns = self.category_fix_patterns.get(category, {})
            specialized_fixes = []

            for pattern_name, pattern_description in category_patterns.items():
                # Generate category-specific fix based on vulnerability details
                fix_title = f"{category.replace('_', ' ').title()} - {pattern_name.replace('_', ' ').title()}"

                # Create specialized fix content based on category
                if category == 'container_security':
                    fix_content = self._generate_container_security_fix(vulnerability, pattern_name, code_context)
                elif category == 'dependency_vulnerabilities':
                    fix_content = self._generate_dependency_security_fix(vulnerability, pattern_name, code_context)
                elif category == 'web_security':
                    fix_content = self._generate_web_security_fix(vulnerability, pattern_name, code_context)
                elif category == 'webauthn_security':
                    fix_content = self._generate_webauthn_security_fix(vulnerability, pattern_name, code_context)
                elif category == 'mobile_security':
                    fix_content = self._generate_mobile_security_fix(vulnerability, pattern_name, code_context)
                elif category == 'infrastructure_security':
                    fix_content = self._generate_infrastructure_security_fix(vulnerability, pattern_name, code_context)
                else:  # code_vulnerabilities
                    fix_content = self._generate_code_security_fix(vulnerability, pattern_name, code_context)

                specialized_fix = {
                    'title': fix_title,
                    'description': pattern_description,
                    'approach': 'category_specific',
                    'category': category,
                    'pattern': pattern_name,
                    'fixed_code': fix_content.get('code', ''),
                    'validation_steps': fix_content.get('validation', ''),
                    'security_impact': fix_content.get('impact', 'Improved security posture'),
                    'complexity_level': fix_content.get('complexity', 'medium')
                }
                specialized_fixes.append(specialized_fix)

            return specialized_fixes

        except Exception as e:
            self.logger.error(f"❌ Category-specific fix generation failed for {category}: {e}")
            raise RuntimeError(f"Category-specific fix generation failed - this indicates a critical training data creation issue: {e}") from e

    def _generate_container_security_fix(self, vulnerability: Dict[str, Any], pattern: str, code_context) -> Dict[str, Any]:
        """Generate container security specific fixes."""
        file_path = vulnerability.get('file_path', '')

        # Extract image name for context-aware fixes
        image_name = None
        if file_path.startswith('dockerfile://'):
            image_name = file_path.replace('dockerfile://', '')

        if 'dockerfile' in file_path.lower() or file_path.startswith('dockerfile://'):
            if pattern == 'user_privilege':
                code = '''# Add non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup

# Switch to non-root user
USER 1001:1001'''
                if image_name:
                    code = f'''# Fix user privilege vulnerability in {image_name}
# Add non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup

# Switch to non-root user
USER 1001:1001'''
                return {
                    'code': code,
                    'validation': 'Verify container runs as non-root user',
                    'impact': 'Reduces privilege escalation risks',
                    'complexity': 'low'
                }
            elif pattern == 'base_image':
                code = '''# Use minimal, security-hardened base image
FROM alpine:3.18-slim
# Or use distroless images for even better security
# FROM gcr.io/distroless/static-debian11'''
                if image_name:
                    code = f'''# Update base image for {image_name}
# Use minimal, security-hardened base image
FROM alpine:3.18-slim
# Or use distroless images for even better security
# FROM gcr.io/distroless/static-debian11'''
                return {
                    'code': code,
                    'validation': 'Scan base image for vulnerabilities',
                    'impact': 'Reduces attack surface',
                    'complexity': 'low'
                }

        return {'code': '# Container security fix applied', 'validation': 'Manual review required'}

    def _generate_dependency_security_fix(self, vulnerability: Dict[str, Any], pattern: str, code_context) -> Dict[str, Any]:
        """Generate dependency vulnerability specific fixes."""
        if pattern == 'version_pinning':
            return {
                'code': '''# Pin dependencies to secure versions
# Update package.json or requirements.txt with specific versions
# Example: "express": "4.18.2" (instead of "^4.18.0")''',
                'validation': 'Run dependency scan after update',
                'impact': 'Prevents vulnerable dependency updates',
                'complexity': 'low'
            }
        elif pattern == 'dependency_scanning':
            return {
                'code': '''# Add dependency scanning to CI/CD
npm audit --audit-level=moderate
# Or for Python: pip-audit
# Or for Java: mvn dependency:check''',
                'validation': 'Integrate into build pipeline',
                'impact': 'Early vulnerability detection',
                'complexity': 'medium'
            }

        return {'code': '# Dependency security fix applied', 'validation': 'Update to latest secure version'}

    def _generate_web_security_fix(self, vulnerability: Dict[str, Any], pattern: str, code_context) -> Dict[str, Any]:
        """Generate web security specific fixes."""
        if pattern == 'cors_configuration':
            return {
                'code': '''// Configure CORS properly
app.use(cors({
    origin: ['https://yourdomain.com', 'https://trusted-domain.com'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));''',
                'validation': 'Test CORS policy with different origins',
                'impact': 'Prevents unauthorized cross-origin requests',
                'complexity': 'medium'
            }
        elif pattern == 'csp_headers':
            return {
                'code': '''// Add Content Security Policy headers
app.use((req, res, next) => {
    res.setHeader('Content-Security-Policy',
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'");
    next();
});''',
                'validation': 'Test CSP policy with browser dev tools',
                'impact': 'Prevents XSS and injection attacks',
                'complexity': 'medium'
            }

        return {'code': '# Web security fix applied', 'validation': 'Test security headers'}

    def _generate_webauthn_security_fix(self, vulnerability: Dict[str, Any], pattern: str, code_context) -> Dict[str, Any]:
        """Generate WebAuthn security specific fixes."""
        if pattern == 'challenge_validation':
            return {
                'code': '''// Validate challenge properly
if (!storedChallenge || storedChallenge !== receivedChallenge) {
    throw new Error('Challenge validation failed');
}
// Clear challenge after use
delete session.challenge;''',
                'validation': 'Test challenge reuse prevention',
                'impact': 'Prevents replay attacks',
                'complexity': 'medium'
            }
        elif pattern == 'credential_verification':
            return {
                'code': '''// Robust credential verification
const verification = await verifyAuthenticationResponse({
    response: authenticationResponse,
    expectedChallenge: storedChallenge,
    expectedOrigin: process.env.ORIGIN,
    expectedRPID: process.env.RP_ID,
    authenticator: storedAuthenticator
});''',
                'validation': 'Test with various credential types',
                'impact': 'Ensures authentic credential verification',
                'complexity': 'high'
            }

        return {'code': '# WebAuthn security fix applied', 'validation': 'Test with WebAuthn flows'}

    def _generate_mobile_security_fix(self, vulnerability: Dict[str, Any], pattern: str, code_context) -> Dict[str, Any]:
        """Generate mobile security specific fixes."""
        if pattern == 'component_security':
            return {
                'code': '''<!-- Secure Android component -->
<activity
    android:name=".MainActivity"
    android:exported="false"
    android:launchMode="singleTask">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>''',
                'validation': 'Review component exposure in manifest',
                'impact': 'Prevents unauthorized component access',
                'complexity': 'medium'
            }
        elif pattern == 'permission_management':
            return {
                'code': '''// Request minimal permissions
<uses-permission android:name="android.permission.INTERNET" />
<!-- Remove unnecessary permissions -->
<!-- <uses-permission android:name="android.permission.READ_CONTACTS" /> -->''',
                'validation': 'Audit required vs granted permissions',
                'impact': 'Reduces privacy and security risks',
                'complexity': 'low'
            }

        return {'code': '# Mobile security fix applied', 'validation': 'Test on Android device'}

    def _generate_infrastructure_security_fix(self, vulnerability: Dict[str, Any], pattern: str, code_context) -> Dict[str, Any]:
        """Generate infrastructure security specific fixes."""
        if pattern == 'secret_management':
            return {
                'code': '''# Use environment variables for secrets
# Remove hardcoded secrets
# const apiKey = process.env.API_KEY; // Instead of hardcoded value
#
# Or use dedicated secret management
# const secret = await secretManager.getSecret('api-key');''',
                'validation': 'Scan for remaining hardcoded secrets',
                'impact': 'Prevents secret exposure',
                'complexity': 'medium'
            }
        elif pattern == 'access_control':
            return {
                'code': '''# Implement proper access controls
# AWS IAM policy example
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": "arn:aws:s3:::specific-bucket/*",
            "Condition": {
                "IpAddress": {
                    "aws:SourceIp": "203.0.113.0/24"
                }
            }
        }
    ]
}''',
                'validation': 'Test access controls with different roles',
                'impact': 'Enforces least privilege access',
                'complexity': 'high'
            }

        return {'code': '# Infrastructure security fix applied', 'validation': 'Review configuration'}

    def _generate_code_security_fix(self, vulnerability: Dict[str, Any], pattern: str, code_context) -> Dict[str, Any]:
        """Generate code vulnerability specific fixes."""
        if pattern == 'injection_prevention':
            return {
                'code': '''// Use parameterized queries to prevent SQL injection
const query = 'SELECT * FROM users WHERE id = ?';
const result = await db.execute(query, [userId]);

// Or for command injection prevention
const { execSync } = require('child_process');
const sanitizedInput = input.replace(/[;&|`$()\\]/g, '');
execSync(`safe-command ${sanitizedInput}`);''',
                'validation': 'Test with injection payloads',
                'impact': 'Prevents injection attacks',
                'complexity': 'medium'
            }
        elif pattern == 'secure_coding':
            return {
                'code': '''// Apply secure coding practices
// Input validation
if (!input || typeof input !== 'string' || input.length > 100) {
    throw new Error('Invalid input');
}

// Output encoding
const sanitized = encodeHTML(userInput);
response.send(`<div>${sanitized}</div>`);''',
                'validation': 'Code review and security testing',
                'impact': 'Improves overall code security',
                'complexity': 'medium'
            }

        return {'code': '# Code security fix applied', 'validation': 'Security code review required'}

    def create_enhanced_dataset(self, vulnerabilities: List[Dict[str, Any]],
                              dataset_name: Optional[str] = None,
                              enable_augmentation: bool = True) -> DatasetCreationResult:
        """
        Create enhanced dataset from pre-categorized vulnerability data.

        Args:
            vulnerabilities: List of vulnerability data with security_category field
            dataset_name: Name for the dataset (auto-generated if None)
            enable_augmentation: Whether to apply Phase 2 advanced data augmentation (default: True)

        Returns:
            DatasetCreationResult with enhanced training examples

        Raises:
            ValueError: If vulnerabilities are missing security_category or have 'unknown' categories
        """
        try:
            self.logger.info(f"🚀 Creating enhanced dataset from {len(vulnerabilities)} vulnerabilities")

            # ✅ FAIL-FAST: Validate all vulnerabilities have security_category
            missing_category_count = 0
            unknown_category_count = 0
            category_counts = {}  # Track category distribution

            for vuln in vulnerabilities:
                vuln_id = vuln.get('id', vuln.get('vulnerability_id', 'unknown'))

                # Check for missing security_category field
                if 'security_category' not in vuln:
                    missing_category_count += 1
                    self.logger.error(f"❌ Vulnerability {vuln_id} missing 'security_category' field")
                    continue

                category = vuln['security_category']

                # Check for 'unknown' category (indicates categorization failure)
                if category == 'unknown':
                    unknown_category_count += 1
                    self.logger.error(f"❌ Vulnerability {vuln_id} has 'unknown' security_category")
                    continue

                category_counts[category] = category_counts.get(category, 0) + 1

            # ✅ FAIL-FAST: Stop if any vulnerabilities lack proper categorization
            if missing_category_count > 0:
                raise ValueError(f"❌ {missing_category_count} vulnerabilities missing 'security_category' field. "
                               f"Enhanced dataset creation requires pre-categorized input. "
                               f"Run categorization in Phase 2C first.")

            if unknown_category_count > 0:
                raise ValueError(f"❌ {unknown_category_count} vulnerabilities have 'unknown' security_category. "
                               f"This indicates categorization failures that must be fixed in Phase 2C. "
                               f"Cannot proceed with enhanced dataset creation.")

            self.logger.info(f"✅ All {len(vulnerabilities)} vulnerabilities have valid security categories")
            self.logger.info(f"📊 Category distribution: {category_counts}")

            enhanced_examples = []
            processed_count = 0
            failed_count = 0

            for vuln in vulnerabilities:
                try:
                    # NEW: Try URL-to-code mapping for URL-based vulnerabilities
                    url_mapped = enhance_vulnerability_with_url_mapping(vuln, self.url_mapper)

                    # Get pre-assigned category (no categorization logic here)
                    category = vuln['security_category']

                    # Extract code context (now works for URL-mapped vulnerabilities too)
                    extraction_result = self.extractor.extract_vulnerability_context(vuln)

                    if not extraction_result.success:
                        # Only log warnings for unexpected failures, not dependency/infrastructure scanners
                        if "Dependency/infrastructure scanner" not in extraction_result.error_message:
                            self.logger.warning(f"⚠️ Failed to extract context for {vuln.get('id', 'unknown')}: {extraction_result.error_message}")
                        failed_count += 1
                        continue

                    # Generate multiple fix approaches
                    fix_result = self.fix_generator.generate_fixes(vuln, extraction_result.code_context)

                    if not fix_result.success:
                        self.logger.warning(f"⚠️ Failed to generate fixes for {vuln.get('id', 'unknown')}: {fix_result.error_message}")
                        failed_count += 1
                        continue

                    # Generate category-specific fixes based on security domain
                    category_specific_fixes = self._generate_category_specific_fixes(
                        category, vuln, extraction_result.code_context, self.category_fix_patterns.get(category, {})
                    )

                    if category_specific_fixes:
                        self.logger.debug(f"🎯 Generated {len(category_specific_fixes)} category-specific fixes for {category}")

                    # Combine standard fixes with category-specific fixes
                    all_fixes = [fix.__dict__ for fix in fix_result.fixes] + category_specific_fixes

                    # NEW: Quality Assessment - Filter high-quality fixes (enabled by default)
                    generated_fixes = all_fixes
                    original_code = extraction_result.code_context.vulnerable_code if extraction_result.code_context else None

                    high_quality_fixes = self.quality_assessor.filter_high_quality_fixes(
                        vuln, generated_fixes, original_code
                    )

                    if not high_quality_fixes:
                        self.logger.warning(f"⚠️ No high-quality fixes generated for {vuln.get('id', 'unknown')} "
                                           f"(generated {len(generated_fixes)} fixes, none passed quality threshold)")
                        failed_count += 1
                        continue

                    self.logger.info(f"✅ Quality assessment: {len(high_quality_fixes)}/{len(generated_fixes)} fixes "
                                   f"passed validation for {vuln.get('id', vuln.get('vulnerability_id', 'unknown'))}")

                    # Create enhanced training examples (one per high-quality fix approach)
                    vuln_examples = self._create_training_examples_for_vulnerability_with_quality(
                        vuln, extraction_result, high_quality_fixes
                    )

                    enhanced_examples.extend(vuln_examples)
                    processed_count += 1

                    if processed_count % 10 == 0:
                        self.logger.info(f"📊 Processed {processed_count} vulnerabilities, generated {len(enhanced_examples)} enhanced examples")

                except Exception as e:
                    self.logger.error(f"❌ Error processing vulnerability {vuln.get('id', 'unknown')}: {e}")
                    raise

            # Create dataset name if not provided
            if not dataset_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dataset_name = f"enhanced_security_dataset_{timestamp}"

            # Apply Phase 2 advanced data augmentation if enabled
            final_examples = enhanced_examples
            augmentation_metadata = {}

            if enable_augmentation and enhanced_examples:
                self.logger.info(f"🚀 Phase 2: Applying advanced data augmentation to {len(enhanced_examples)} examples...")

                # Convert EnhancedTrainingExample to ChatML format for augmentation
                chatml_examples = []
                for example in enhanced_examples:
                    chatml_example = {
                        'messages': [
                            {'role': 'user', 'content': example.instruction},
                            {'role': 'assistant', 'content': example.response}
                        ],
                        'metadata': {
                            'vulnerability_id': example.metadata.get('vulnerability_id', 'unknown'),
                            'original_example': True
                        }
                    }
                    chatml_examples.append(chatml_example)

                # Apply advanced data augmentation
                augmented_chatml = self.data_augmentor.augment_training_data(chatml_examples)

                # Convert back to EnhancedTrainingExample format
                final_examples = []
                original_count = 0
                augmented_count = 0

                for aug_example in augmented_chatml:
                    # Extract messages
                    messages = aug_example.get('messages', [])
                    user_msg = next((m for m in messages if m.get('role') == 'user'), {})
                    assistant_msg = next((m for m in messages if m.get('role') == 'assistant'), {})

                    instruction = user_msg.get('content', '')
                    response = assistant_msg.get('content', '')

                    # Create EnhancedTrainingExample
                    metadata = aug_example.get('metadata', {})
                    is_original = metadata.get('original_example', False)

                    enhanced_example = EnhancedTrainingExample(
                        instruction=instruction,
                        response=response,
                        metadata=metadata
                    )

                    final_examples.append(enhanced_example)

                    if is_original:
                        original_count += 1
                    else:
                        augmented_count += 1

                augmentation_ratio = len(final_examples) / len(enhanced_examples)
                augmentation_metadata = {
                    'augmentation_enabled': True,
                    'original_examples': original_count,
                    'augmented_examples': augmented_count,
                    'total_examples': len(final_examples),
                    'augmentation_ratio': augmentation_ratio
                }

                self.logger.info(f"✅ Phase 2 augmentation complete: {len(enhanced_examples)} → {len(final_examples)} ({augmentation_ratio:.1f}x)")
            else:
                augmentation_metadata = {'augmentation_enabled': False}
                self.logger.info(f"⏭️ Phase 2 augmentation skipped (disabled)")

            # Log category distribution for multi-domain analysis
            self.logger.info(f"🎯 Multi-domain categorization: {dict(category_counts)}")
            self.logger.info(f"✅ Enhanced dataset creation completed: {len(final_examples)} examples from {processed_count} vulnerabilities")

            return DatasetCreationResult(
                success=True,
                enhanced_examples=final_examples,
                original_examples_count=len(vulnerabilities),
                enhanced_examples_count=len(final_examples),
                category_distribution=category_counts,
                creation_metadata={
                    'dataset_name': dataset_name,
                    'vulnerabilities_processed': processed_count,
                    'vulnerabilities_failed': failed_count,
                    'original_count': len(vulnerabilities),
                    'enhanced_count': len(final_examples),
                    'enhancement_ratio': len(final_examples) / len(vulnerabilities) if vulnerabilities else 0,
                    'created_at': datetime.now().isoformat(),
                    'phase2_augmentation': augmentation_metadata,
                    'multi_domain_categorization': {
                        'total_categories': len(category_counts),
                        'category_distribution': category_counts
                    }
                }
            )

        except Exception as e:
            self.logger.error(f"Dataset creation failed: {e}")
            raise

    def _create_training_examples_for_vulnerability(self,
                                                  vulnerability: Dict[str, Any],
                                                  extraction_result: ContextExtractionResult,
                                                  fix_result) -> List[EnhancedTrainingExample]:
        """Create multiple training examples for a single vulnerability."""

        examples = []
        code_context = extraction_result.code_context

        # Handle both source code and infrastructure vulnerabilities
        if code_context:
            # Source code vulnerability - has code context
            vulnerability_context = {
                'id': vulnerability.get('id', 'unknown'),
                'severity': vulnerability.get('extra', {}).get('severity', 'unknown'),
                'file_path': code_context.file_path,
                'line': code_context.vulnerability_line,
                'language': code_context.language,
                'function': code_context.function_name,
                'class': code_context.class_name,
                'message': vulnerability.get('extra', {}).get('message', '')
            }
        else:
            # Infrastructure vulnerability - no code context available
            vulnerability_context = {
                'id': vulnerability.get('id', 'unknown'),
                'severity': vulnerability.get('extra', {}).get('severity', 'unknown'),
                'file_path': vulnerability.get('file_path', vulnerability.get('path', 'unknown')),
                'line': vulnerability.get('start', {}).get('line', 1),
                'language': 'infrastructure',
                'function': None,
                'class': None,
                'message': vulnerability.get('extra', {}).get('message', ''),
                'infrastructure_type': extraction_result.extraction_metadata.get('extraction_type', 'infrastructure'),
                'original_path': extraction_result.extraction_metadata.get('original_path', '')
            }

        # Create one training example per fix approach
        for fix in fix_result.fixes:
            example = self._create_single_training_example(
                vulnerability, vulnerability_context, code_context, fix
            )
            examples.append(example)

        # Also create a comprehensive example with all approaches
        if len(fix_result.fixes) > 1:
            comprehensive_example = self._create_comprehensive_training_example(
                vulnerability, vulnerability_context, code_context, fix_result.fixes
            )
            examples.append(comprehensive_example)

        return examples

    def _create_training_examples_for_vulnerability_with_quality(self,
                                                               vulnerability: Dict[str, Any],
                                                               extraction_result: ContextExtractionResult,
                                                               high_quality_fixes: List[Tuple[Dict[str, Any], QualityAssessmentResult]]) -> List[EnhancedTrainingExample]:
        """Create training examples for quality-assessed fixes."""

        examples = []
        code_context = extraction_result.code_context

        # Handle both source code and infrastructure vulnerabilities
        if code_context:
            # Source code vulnerability - has code context
            vulnerability_context = {
                'id': vulnerability.get('id', 'unknown'),
                'severity': vulnerability.get('extra', {}).get('severity', 'unknown'),
                'file_path': code_context.file_path,
                'line': code_context.vulnerability_line,
                'type': vulnerability.get('extra', {}).get('metadata', {}).get('category', 'security'),
                'language': code_context.language,
                'function': code_context.function_name,
                'class': code_context.class_name,
                'message': vulnerability.get('extra', {}).get('message', 'Security vulnerability detected')
            }
        else:
            # Infrastructure vulnerability - no code context
            vulnerability_context = {
                'id': vulnerability.get('id', 'unknown'),
                'severity': vulnerability.get('extra', {}).get('severity', 'unknown'),
                'file_path': vulnerability.get('path', 'unknown'),
                'line': vulnerability.get('start', {}).get('line', 0),
                'type': vulnerability.get('extra', {}).get('metadata', {}).get('category', 'infrastructure'),
                'language': 'text',
                'function': None,
                'class': None,
                'message': vulnerability.get('extra', {}).get('message', 'Infrastructure security issue detected')
            }

        # Create training examples for each high-quality fix
        for fix_data, quality_assessment in high_quality_fixes:
            # Convert fix_data dict back to SecurityFix-like object for compatibility
            class QualityFixWrapper:
                def __init__(self, data, quality):
                    self.__dict__.update(data)
                    self.quality_assessment = quality

            quality_fix = QualityFixWrapper(fix_data, quality_assessment)

            # Create enhanced training example with quality metadata
            example = self._create_single_training_example_with_quality(
                vulnerability, vulnerability_context, code_context, quality_fix
            )
            examples.append(example)

        # Also create a comprehensive example combining all high-quality fixes
        if len(high_quality_fixes) > 1:
            fixes_only = [fix_data for fix_data, _ in high_quality_fixes]
            comprehensive_example = self._create_comprehensive_training_example_with_quality(
                vulnerability, vulnerability_context, code_context, high_quality_fixes
            )
            examples.append(comprehensive_example)

        return examples

    def _create_single_training_example_with_quality(self,
                                                   vulnerability: Dict[str, Any],
                                                   vulnerability_context: Dict[str, Any],
                                                   code_context,
                                                   quality_fix) -> EnhancedTrainingExample:
        """Create a single training example with quality assessment metadata."""

        # Create instruction with quality context
        instruction = self._create_enhanced_instruction_with_quality(
            vulnerability_context, code_context, quality_fix
        )

        # Create response with quality validation details
        response = self._create_enhanced_response_with_quality(
            vulnerability_context, code_context, quality_fix
        )

        # Enhanced metadata including quality assessment
        metadata = {
            'vulnerability_id': vulnerability_context['id'],
            'severity': vulnerability_context['severity'],
            'fix_approach': getattr(quality_fix, 'approach', 'unknown'),
            'created_at': datetime.now().isoformat(),
            'enhanced_dataset': True,
            'quality_assessed': True,  # NEW: Quality assessment marker
            'quality_score': quality_fix.quality_assessment.overall_score,
            'quality_details': {
                'syntax_valid': quality_fix.quality_assessment.syntax_valid,
                'security_improved': quality_fix.quality_assessment.security_improved,
                'validation_passed': quality_fix.quality_assessment.validation_passed,
                'code_quality_score': quality_fix.quality_assessment.code_quality_score
            },
            # Multi-domain categorization
            'security_category': vulnerability.get('security_category', 'unknown'),
            'category_confidence': vulnerability.get('category_confidence', 0.0)
        }

        # Code examples for training
        code_examples = {}
        if code_context:
            code_examples['original'] = code_context.vulnerable_code
            code_examples['fixed'] = getattr(quality_fix, 'fixed_code', '')

        return EnhancedTrainingExample(
            instruction=instruction,
            response=response,
            metadata=metadata,
            vulnerability_context=vulnerability_context,
            fix_approaches=[quality_fix.__dict__],
            code_examples=code_examples
        )

    def _create_enhanced_instruction_with_quality(self, vulnerability_context: Dict[str, Any],
                                                code_context, quality_fix) -> str:
        """Create an enhanced instruction highlighting quality aspects."""

        base_instruction = self._create_enhanced_instruction(vulnerability_context, code_context,
                                                           getattr(quality_fix, 'approach', None))

        # Add quality context to instruction
        quality_note = f"\n\nNote: Provide a high-quality, validated security fix " \
                      f"(target quality score: ≥{quality_fix.quality_assessment.assessment_details.get('assessment_threshold', 0.7)})."

        return base_instruction + quality_note

    def _create_enhanced_response_with_quality(self, vulnerability_context: Dict[str, Any],
                                             code_context, quality_fix) -> str:
        """Create an enhanced response with quality validation details."""

        base_response = self._create_enhanced_response(vulnerability_context, code_context, quality_fix)

        # Add quality assessment details
        quality_details = f"""

## Quality Assessment ✅
- **Overall Score**: {quality_fix.quality_assessment.overall_score:.2f}/1.0
- **Syntax Valid**: {'✅' if quality_fix.quality_assessment.syntax_valid else '❌'}
- **Security Improved**: {'✅' if quality_fix.quality_assessment.security_improved else '❌'}
- **Code Quality**: {quality_fix.quality_assessment.code_quality_score:.2f}/1.0
- **Validation Status**: {'✅ PASSED' if quality_fix.quality_assessment.validation_passed else '❌ FAILED'}

**Quality Recommendations**:
{chr(10).join(f'- {rec}' for rec in quality_fix.quality_assessment.recommendations)}
"""

        return base_response + quality_details

    def _create_comprehensive_training_example_with_quality(self,
                                                          vulnerability: Dict[str, Any],
                                                          vulnerability_context: Dict[str, Any],
                                                          code_context,
                                                          high_quality_fixes: List[Tuple[Dict[str, Any], QualityAssessmentResult]]) -> EnhancedTrainingExample:
        """Create a comprehensive example combining all high-quality fixes."""

        fixes_data = [fix_data for fix_data, _ in high_quality_fixes]
        assessments = [assessment for _, assessment in high_quality_fixes]

        # Calculate aggregate quality metrics
        avg_quality_score = sum(a.overall_score for a in assessments) / len(assessments)
        all_syntax_valid = all(a.syntax_valid for a in assessments)
        any_security_improved = any(a.security_improved for a in assessments)

        instruction = f"""Analyze this security vulnerability and provide multiple high-quality fix approaches:

**Vulnerability**: {vulnerability_context['id']} ({vulnerability_context['severity']})
**File**: {vulnerability_context['file_path']}:{vulnerability_context['line']}
**Type**: {vulnerability_context['type']}

Multiple validated fix approaches are needed with quality scores ≥0.7."""

        # Combine all high-quality fix responses
        combined_response = f"""# Multiple High-Quality Security Fix Approaches

## Vulnerability Analysis
**ID**: {vulnerability_context['id']}
**Location**: {vulnerability_context['file_path']}:{vulnerability_context['line']}
**Severity**: {vulnerability_context['severity']}

## Validated Fix Approaches ({len(high_quality_fixes)} quality-assessed solutions)

"""

        for i, (fix_data, assessment) in enumerate(high_quality_fixes, 1):
            combined_response += f"""### Approach {i}: {fix_data.get('title', 'Security Fix')}
**Quality Score**: {assessment.overall_score:.2f}/1.0 ✅

{fix_data.get('description', 'High-quality security fix')}

**Implementation**:
```{vulnerability_context.get('language', '')}
{fix_data.get('fixed_code', '')}
```

**Validation**: {fix_data.get('validation_steps', 'Quality validated')}

---

"""

        # Aggregate metadata
        metadata = {
            'vulnerability_id': vulnerability_context['id'],
            'severity': vulnerability_context['severity'],
            'fix_approach': 'comprehensive_quality_assessed',
            'created_at': datetime.now().isoformat(),
            'enhanced_dataset': True,
            'phase_4_quality_assessed': True,
            'comprehensive_example': True,
            'quality_summary': {
                'total_fixes': len(high_quality_fixes),
                'average_quality_score': avg_quality_score,
                'all_syntax_valid': all_syntax_valid,
                'security_improvements': any_security_improved
            },
            # Multi-domain categorization
            'security_category': vulnerability.get('security_category', 'unknown'),
            'category_confidence': vulnerability.get('category_confidence', 0.0)
        }

        return EnhancedTrainingExample(
            instruction=instruction,
            response=combined_response,
            metadata=metadata,
            vulnerability_context=vulnerability_context,
            fix_approaches=fixes_data,
            code_examples={}
        )

    def _create_single_training_example(self,
                                      vulnerability: Dict[str, Any],
                                      vulnerability_context: Dict[str, Any],
                                      code_context,
                                      fix: SecurityFix) -> EnhancedTrainingExample:
        """Create a training example for a single fix approach."""

        # Create enhanced instruction
        instruction = self._create_enhanced_instruction(vulnerability_context, code_context, fix.approach)

        # Create enhanced response with specific code examples
        response = self._create_enhanced_response(vulnerability_context, code_context, fix)

        # Prepare metadata
        metadata = {
            'vulnerability_id': vulnerability_context['id'],
            'fix_approach': fix.approach.value,
            'language': vulnerability_context['language'],  # Use vulnerability_context since code_context might be None
            'complexity_level': fix.complexity_level,
            'security_impact': fix.security_impact,
            'created_at': datetime.now().isoformat(),
            'enhancement_type': 'single_approach'
        }

        # Add URL mapping metadata if available
        if vulnerability.get('endpoint_metadata'):
            metadata['endpoint_metadata'] = vulnerability['endpoint_metadata']
            metadata['url_mapped'] = True
            metadata['url'] = vulnerability.get('url')

        # Add file path and line number for code context
        metadata['file_path'] = vulnerability_context.get('file_path')
        metadata['line_number'] = vulnerability_context.get('line')

        return EnhancedTrainingExample(
            instruction=instruction,
            response=response,
            metadata=metadata,
            vulnerability_context=vulnerability_context,
            fix_approaches=[{
                'approach': fix.approach.value,
                'title': fix.title,
                'complexity': fix.complexity_level,
                'security_impact': fix.security_impact
            }],
            code_examples={
                'vulnerable_code': fix.vulnerable_code,
                'fixed_code': fix.fixed_code,
                'context': code_context.get_full_context(line_padding=3) if code_context else 'No source code context (infrastructure vulnerability)'
            }
        )

    def _create_comprehensive_training_example(self,
                                             vulnerability: Dict[str, Any],
                                             vulnerability_context: Dict[str, Any],
                                             code_context,
                                             fixes: List[SecurityFix]) -> EnhancedTrainingExample:
        """Create a comprehensive training example with multiple fix approaches."""

        if code_context:
            # Source code vulnerability instruction
            instruction = f"""Analyze this security vulnerability and provide multiple remediation approaches with specific code examples:

Vulnerability: {vulnerability_context['id']}
File: {vulnerability_context['file_path']}
Line: {vulnerability_context['line']}
Language: {vulnerability_context['language']}
Function: {vulnerability_context['function'] or 'N/A'}
Class: {vulnerability_context['class'] or 'N/A'}

Vulnerable Code:
```{vulnerability_context['language']}
{code_context.vulnerable_code}
```

Context:
{code_context.get_full_context(line_padding=2)}

Provide multiple specific fix approaches with actual code examples."""
        else:
            # Infrastructure vulnerability instruction
            instruction = f"""Analyze this infrastructure security vulnerability and provide multiple remediation approaches:

Vulnerability: {vulnerability_context['id']}
Component: {vulnerability_context['file_path']}
Infrastructure Type: {vulnerability_context.get('infrastructure_type', 'unknown')}
Original Path: {vulnerability_context.get('original_path', 'N/A')}

Provide multiple specific remediation approaches with configuration examples and deployment guidance."""

        # Create comprehensive response
        response = self._create_comprehensive_response(vulnerability_context, code_context, fixes)

        # Prepare metadata
        metadata = {
            'vulnerability_id': vulnerability_context['id'],
            'fix_approaches': [fix.approach.value for fix in fixes],
            'language': vulnerability_context['language'],  # Use vulnerability_context since code_context might be None
            'approaches_count': len(fixes),
            'created_at': datetime.now().isoformat(),
            'enhancement_type': 'multi_approach'
        }

        # Add URL mapping metadata if available
        if vulnerability.get('endpoint_metadata'):
            metadata['endpoint_metadata'] = vulnerability['endpoint_metadata']
            metadata['url_mapped'] = True
            metadata['url'] = vulnerability.get('url')

        # Add file path and line number for code context
        metadata['file_path'] = vulnerability_context.get('file_path')
        metadata['line_number'] = vulnerability_context.get('line')

        return EnhancedTrainingExample(
            instruction=instruction,
            response=response,
            metadata=metadata,
            vulnerability_context=vulnerability_context,
            fix_approaches=[{
                'approach': fix.approach.value,
                'title': fix.title,
                'complexity': fix.complexity_level,
                'security_impact': fix.security_impact
            } for fix in fixes],
            code_examples={
                'vulnerable_code': code_context.vulnerable_code if code_context else 'No source code (infrastructure vulnerability)',
                'context': code_context.get_full_context(line_padding=3) if code_context else 'No source code context (infrastructure vulnerability)',
                **{f'fix_{i+1}_{fix.approach.value}': fix.fixed_code for i, fix in enumerate(fixes)}
            }
        )

    def _create_enhanced_instruction(self, vulnerability_context: Dict[str, Any],
                                   code_context, approach: FixApproach) -> str:
        """Create an enhanced instruction with code context."""

        approach_descriptions = {
            FixApproach.INPUT_VALIDATION: "input validation and sanitization",
            FixApproach.OUTPUT_SANITIZATION: "output encoding and sanitization",
            FixApproach.DATABASE_SOLUTION: "database-level security controls",
            FixApproach.IN_MEMORY_SOLUTION: "secure in-memory data handling",
            FixApproach.CACHE_SOLUTION: "secure caching mechanisms",
            FixApproach.MICROSERVICE_SOLUTION: "microservice architecture security"
        }

        # Handle both enum and string approach values
        if hasattr(approach, 'value'):
            fallback_desc = f"{approach.value.replace('_', ' ')} approach"
        else:
            fallback_desc = f"{str(approach).replace('_', ' ')} approach"
        approach_desc = approach_descriptions.get(approach, fallback_desc)

        if code_context:
            # Source code vulnerability
            return f"""Analyze this {vulnerability_context['language']} security vulnerability and provide a specific fix using {approach_desc}:

Vulnerability: {vulnerability_context['id']}
File: {vulnerability_context['file_path']} (line {vulnerability_context['line']})
Function: {vulnerability_context['function'] or 'N/A'}
Class: {vulnerability_context['class'] or 'N/A'}

Vulnerable Code:
```{vulnerability_context['language']}
{code_context.vulnerable_code}
```

Provide a specific code fix with detailed explanation."""
        else:
            # Infrastructure vulnerability
            return f"""Analyze this infrastructure security vulnerability and provide specific remediation guidance using {approach_desc}:

Vulnerability: {vulnerability_context['id']}
Component: {vulnerability_context['file_path']}
Infrastructure Type: {vulnerability_context.get('infrastructure_type', 'unknown')}
Original Path: {vulnerability_context.get('original_path', 'N/A')}

Provide specific configuration and deployment recommendations to address this vulnerability."""

    def _create_enhanced_response(self, vulnerability_context: Dict[str, Any],
                                code_context, fix: SecurityFix) -> str:
        """Create an enhanced response with specific code examples."""

        if code_context:
            # Source code vulnerability response
            return f"""# {fix.title}

## Vulnerability Analysis
**ID**: {vulnerability_context['id']}
**File**: {vulnerability_context['file_path']} (line {vulnerability_context['line']})
**Language**: {vulnerability_context['language']}
**Function**: {vulnerability_context['function'] or 'N/A'}
**Class**: {vulnerability_context['class'] or 'N/A'}
**Severity**: {vulnerability_context['severity']}

## Problem Description
{vulnerability_context['message']}

## Vulnerable Code
```{vulnerability_context['language']}
{getattr(fix, 'vulnerable_code', 'No vulnerable code provided')}
```

## Fixed Code
```{vulnerability_context['language']}
{getattr(fix, 'fixed_code', 'No fixed code provided')}
```

## Fix Explanation
{getattr(fix, 'explanation', 'No explanation provided')}

## Benefits
{chr(10).join(f'• {benefit}' for benefit in getattr(fix, 'benefits', []))}

## Implementation Notes
{chr(10).join(f'• {note}' for note in getattr(fix, 'implementation_notes', []))}

## Trade-offs
{chr(10).join(f'• {tradeoff}' for tradeoff in getattr(fix, 'trade_offs', []))}

## Security Impact
**Level**: {getattr(fix, 'security_impact', 'Not specified')}
**Complexity**: {getattr(fix, 'complexity_level', 'Not specified')}

## Code Context
```{vulnerability_context['language']}
{code_context.get_full_context(line_padding=2)}
```"""
        else:
            # Infrastructure vulnerability response
            return f"""# {fix.title}

## Infrastructure Vulnerability Analysis
**ID**: {vulnerability_context['id']}
**Component**: {vulnerability_context['file_path']}
**Infrastructure Type**: {vulnerability_context.get('infrastructure_type', 'unknown')}
**Original Path**: {vulnerability_context.get('original_path', 'N/A')}
**Severity**: {vulnerability_context['severity']}

## Problem Description
{vulnerability_context['message']}

## Current Configuration Issues
{getattr(fix, 'vulnerable_code', 'No vulnerable code provided')}

## Recommended Configuration
{getattr(fix, 'fixed_code', 'No fixed code provided')}

## Remediation Guidance
{getattr(fix, 'explanation', 'No explanation provided')}

## Security Benefits
{chr(10).join(f'• {benefit}' for benefit in getattr(fix, 'benefits', []))}

## Implementation Steps
{chr(10).join(f'• {note}' for note in getattr(fix, 'implementation_notes', []))}

## Considerations
{chr(10).join(f'• {tradeoff}' for tradeoff in getattr(fix, 'trade_offs', []))}

## Risk Reduction
**Level**: {getattr(fix, 'security_impact', 'Not specified')}
**Complexity**: {getattr(fix, 'complexity_level', 'Not specified')}

## Infrastructure Context
Component: {vulnerability_context.get('original_path', vulnerability_context['file_path'])}
Type: {vulnerability_context.get('infrastructure_type', 'Infrastructure vulnerability')}"""

    def _create_comprehensive_response(self, vulnerability_context: Dict[str, Any],
                                     code_context, fixes: List[SecurityFix]) -> str:
        """Create a comprehensive response with multiple fix approaches."""

        if code_context:
            # Source code vulnerability response
            response = f"""# Multiple Security Fix Approaches

## Vulnerability Analysis
**ID**: {vulnerability_context['id']}
**File**: {vulnerability_context['file_path']} (line {vulnerability_context['line']})
**Language**: {vulnerability_context['language']}
**Function**: {vulnerability_context['function'] or 'N/A'}
**Class**: {vulnerability_context['class'] or 'N/A'}
**Severity**: {vulnerability_context['severity']}

## Problem Description
{vulnerability_context['message']}

## Vulnerable Code
```{vulnerability_context['language']}
{code_context.vulnerable_code}
```

## Fix Approaches

"""
        else:
            # Infrastructure vulnerability response
            response = f"""# Multiple Infrastructure Security Fix Approaches

## Infrastructure Vulnerability Analysis
**ID**: {vulnerability_context['id']}
**Component**: {vulnerability_context['file_path']}
**Infrastructure Type**: {vulnerability_context.get('infrastructure_type', 'unknown')}
**Original Path**: {vulnerability_context.get('original_path', 'N/A')}
**Severity**: {vulnerability_context['severity']}

## Problem Description
{vulnerability_context['message']}

## Infrastructure Configuration Issues
Current configuration has security vulnerabilities that need to be addressed through proper configuration management and security hardening.

## Remediation Approaches

"""

        for i, fix in enumerate(fixes, 1):
            response += f"""### Approach {i}: {fix.title}

**Complexity**: {fix.complexity_level} | **Security Impact**: {fix.security_impact}

#### Fixed Code
```{vulnerability_context['language']}
{fix.fixed_code}
```

#### Explanation
{fix.explanation}

#### Benefits
{chr(10).join(f'• {benefit}' for benefit in fix.benefits)}

#### Trade-offs
{chr(10).join(f'• {tradeoff}' for tradeoff in fix.trade_offs)}

---

"""

        response += f"""## Recommendation
Choose the approach that best fits your architecture and security requirements. For this {vulnerability_context['language']} {'codebase' if code_context else 'infrastructure'}, consider:

1. **Quick Fix**: {fixes[0].title} (complexity: {fixes[0].complexity_level})
2. **Comprehensive**: {fixes[-1].title if len(fixes) > 1 else fixes[0].title}
"""

        if code_context:
            response += f"""
## Code Context
```{vulnerability_context['language']}
{code_context.get_full_context(line_padding=3)}
```"""
        else:
            response += f"""
## Infrastructure Context
Component: {vulnerability_context.get('original_path', vulnerability_context['file_path'])}
Type: {vulnerability_context.get('infrastructure_type', 'Infrastructure component')}
Remediation Focus: Configuration and deployment security"""

        return response

    def save_enhanced_dataset(self, result: DatasetCreationResult,
                            format: str = 'jsonl') -> Optional[Path]:
        """
        Save enhanced dataset to file.

        Args:
            result: Dataset creation result
            format: Output format ('jsonl' or 'json')

        Returns:
            Path to saved file or None if failed
        """
        if not result.success:
            self.logger.error("Cannot save failed dataset creation result")
            return None

        try:
            dataset_name = result.creation_metadata.get('dataset_name', 'enhanced_dataset')

            if format == 'jsonl':
                output_file = self.output_dir / f"{dataset_name}.jsonl"

                with open(output_file, 'w', encoding='utf-8') as f:
                    for example in result.enhanced_examples:
                        # Convert to simple dict for JSONL format
                        jsonl_example = {
                            'instruction': example.instruction,
                            'response': example.response,
                            'metadata': example.metadata
                        }
                        f.write(json.dumps(jsonl_example, ensure_ascii=False, cls=EnumJSONEncoder) + '\n')

            elif format == 'json':
                output_file = self.output_dir / f"{dataset_name}.json"

                dataset_dict = {
                    'metadata': result.creation_metadata,
                    'examples': [
                        {
                            'instruction': example.instruction,
                            'response': example.response,
                            'metadata': example.metadata,
                            'vulnerability_context': example.vulnerability_context,
                            'fix_approaches': serialize_fix_approaches(example.fix_approaches),
                            'code_examples': example.code_examples
                        }
                        for example in result.enhanced_examples
                    ]
                }

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(dataset_dict, f, ensure_ascii=False, indent=2, cls=EnumJSONEncoder)

            else:
                raise ValueError(f"Unsupported format: {format}")

            self.logger.info(f"✅ Enhanced dataset saved to: {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"Failed to save enhanced dataset: {e}")
            raise


class EnumJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Enum objects by converting them to their string values."""

    def default(self, obj):
        if isinstance(obj, FixApproach):
            return obj.value
        return super().default(obj)


def serialize_fix_approaches(fix_approaches):
    """Convert FixApproach enum objects to their string values for JSON serialization."""
    if isinstance(fix_approaches, list):
        return [approach.value if isinstance(approach, FixApproach) else approach
                for approach in fix_approaches]
    elif isinstance(fix_approaches, FixApproach):
        return fix_approaches.value
    return fix_approaches
