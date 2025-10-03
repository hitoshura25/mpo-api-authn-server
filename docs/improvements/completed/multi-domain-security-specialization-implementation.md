# Multi-Domain Security Specialization Implementation Plan

**Status**: In Progress
**Priority**: High
**Timeline**: 4 weeks
**Dependencies**: Current sequential fine-tuning infrastructure

## Executive Summary

This plan enhances the existing security AI model from WebAuthn-specific specialization to comprehensive multi-domain security remediation. The current model achieves 0.62 Stage 2 score (medium specialization) with 67% quality pass rate. Through multi-domain specialization, we target 0.75+ Stage 2 score (high specialization) with 85%+ quality pass rate.

### Problem Analysis

**Current Limitations**:
- Model trained primarily on WebAuthn patterns (1 of 7 security domains)
- Generic fix generation lacks domain-specific expertise
- Poor remediation quality for non-WebAuthn vulnerabilities
- Missed opportunity for comprehensive security coverage

**Opportunity**: Vulnerability data contains 7 distinct security domains:
1. **Container Security** (Trivy) - Docker/infrastructure vulnerabilities
2. **Dependency Vulnerabilities** (OSV Scanner) - Package security issues
3. **Web Application Security** (ZAP) - CORS, CSP, authentication
4. **Code Vulnerabilities** (Semgrep) - Injection attacks, insecure patterns
5. **WebAuthn Security** (Semgrep custom rules) - Current strength
6. **Mobile Security** (Android analysis) - Component security, permissions
7. **Infrastructure Security** (Checkov, GitLeaks) - IaC, secrets management

## Technical Architecture Integration

### Current Process Flow Analysis

The existing 6-phase `process_artifacts.py` architecture provides excellent integration points:

```
Phase 1: Parsing → Extract vulnerabilities from security tools
Phase 2A: Core Analysis → AI analysis without RAG
Phase 2B: RAG Enhancement → Knowledge base enhancement
Phase 2C: Analysis Summary → Generate summaries
Phase 3: Narrativization → Create rich narratives
Phase 4: Datasets → **PRIMARY INTEGRATION POINT** (lines 804-950)
Phase 5: Training → Sequential fine-tuning (ENHANCEMENT POINT)
Phase 6: Upload → HuggingFace uploads
```

### Key Integration Points

#### **1. Phase 4: Datasets Creation (Primary)**
**File**: `process_artifacts.py` lines 844-895
**Current**: Uses `enhanced_dataset_creator.py` for code-aware training data
**Enhancement**: Add multi-domain categorization and specialized training examples

#### **2. Phase 5: Sequential Training (Secondary)**
**File**: `sequential_fine_tuner.py` validation methods
**Current**: Generic Stage 2 validation scoring
**Enhancement**: Category-aware validation with domain-specific scoring

#### **3. Enhanced Dataset Creator (Core)**
**File**: `enhanced_dataset_creator.py`
**Current**: Code-aware security fixes, quality assessment, data augmentation
**Enhancement**: Add vulnerability categorization and domain-specific example generation

## Implementation Phases

### Phase 1: Category Detection System (Week 1)

#### **1.1 Vulnerability Categorization Algorithm**

**Objective**: Automatically categorize vulnerabilities by security domain using tool origin and content analysis.

**Implementation**: Add to `enhanced_dataset_creator.py`

```python
class VulnerabilityCategorizor:
    """Categorizes vulnerabilities by security domain for specialized training."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Tool-to-category mapping
        self.tool_category_map = {
            'trivy': 'container_security',
            'osv-scanner': 'dependency_vulnerabilities',
            'zap': 'web_security',
            'checkov': 'infrastructure_security',
            'gitleaks': 'infrastructure_security',
            'semgrep': 'code_vulnerabilities'  # Default, refined by content
        }

        # Content-based categorization patterns
        self.content_patterns = {
            'webauthn_security': [
                'webauthn', 'fido', 'credential', 'attestation',
                'authenticator', 'assertion', 'challenge'
            ],
            'mobile_security': [
                'android', 'exported_activity', 'permission',
                'manifest', '.kt', 'androidx'
            ],
            'container_security': [
                'dockerfile', 'docker', 'container', 'alpine',
                'base image', 'user privileges'
            ],
            'web_security': [
                'cors', 'csp', 'xss', 'csrf', 'origin',
                'access-control', 'same-origin'
            ],
            'dependency_vulnerabilities': [
                'package.json', 'gradle', 'maven', 'npm',
                'version', 'cve-', 'dependency'
            ]
        }

    def categorize_vulnerabilities(self, vulnerabilities: List[Dict]) -> Dict[str, List]:
        """
        Categorize vulnerabilities by security domain.

        Args:
            vulnerabilities: List of vulnerability dictionaries

        Returns:
            Dictionary mapping category names to vulnerability lists
        """
        categories = {
            'container_security': [],
            'dependency_vulnerabilities': [],
            'web_security': [],
            'code_vulnerabilities': [],
            'webauthn_security': [],
            'mobile_security': [],
            'infrastructure_security': []
        }

        for vuln in vulnerabilities:
            category = self._detect_vulnerability_category(vuln)
            categories[category].append(vuln)

            # Add category metadata to vulnerability
            vuln['detected_category'] = category

        # Log categorization results
        for category, vulns in categories.items():
            if vulns:
                self.logger.info(f"📊 {category}: {len(vulns)} vulnerabilities")

        return {k: v for k, v in categories.items() if v}  # Remove empty categories

    def _detect_vulnerability_category(self, vulnerability: Dict) -> str:
        """
        Detect vulnerability category using tool origin and content analysis.

        Args:
            vulnerability: Vulnerability dictionary

        Returns:
            Category string
        """
        tool = vulnerability.get('tool', '').lower()
        description = str(vulnerability.get('description', '')).lower()
        file_path = str(vulnerability.get('file_path', '')).lower()
        alert_name = str(vulnerability.get('alert', '')).lower()
        check_id = str(vulnerability.get('check_id', '')).lower()

        # Combine all text for content analysis
        combined_text = f"{description} {file_path} {alert_name} {check_id}"

        # Primary: Tool-based categorization
        base_category = self.tool_category_map.get(tool, 'code_vulnerabilities')

        # Secondary: Content-based refinement
        if tool == 'semgrep':
            # Semgrep needs content-based subcategorization
            for category, patterns in self.content_patterns.items():
                if any(pattern in combined_text for pattern in patterns):
                    return category
            return 'code_vulnerabilities'  # Default for semgrep

        # Content-based override for specific patterns
        for category, patterns in self.content_patterns.items():
            pattern_matches = sum(1 for pattern in patterns if pattern in combined_text)
            if pattern_matches >= 2:  # Require multiple pattern matches for override
                return category

        return base_category
```

#### **1.2 Integration with Enhanced Dataset Creator**

**File**: `enhanced_dataset_creator.py` - Modify constructor and main methods

```python
class EnhancedDatasetCreator:
    """Enhanced with multi-domain security specialization capability."""

    def __init__(self, output_dir: Optional[Path] = None, project_root: Optional[Path] = None,
                 enable_multi_domain: bool = False):
        """
        Initialize enhanced dataset creator with optional multi-domain support.

        Args:
            output_dir: Directory for saving enhanced datasets
            project_root: Project root directory for resolving relative file paths
            enable_multi_domain: Enable multi-domain categorization and specialization
        """
        # Existing initialization (unchanged)
        if project_root is None:
            current_dir = Path.cwd()
            if current_dir.name == "security-ai-analysis":
                project_root = current_dir.parent
            else:
                project_root = current_dir

        self.project_root = project_root
        self.extractor = VulnerableCodeExtractor(project_root=self.project_root)
        self.fix_generator = MultiApproachFixGenerator()
        self.url_mapper = URLToCodeMapper(project_root=self.project_root)
        self.quality_assessor = FixQualityAssessor()
        self.data_augmentor = SecurityDataAugmentor()
        self.output_dir = output_dir or Path("enhanced_datasets/code-aware-training")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # NEW: Multi-domain components
        self.enable_multi_domain = enable_multi_domain
        self.categorizer = VulnerabilityCategorizor() if enable_multi_domain else None

        # Setup logging
        self.logger = logging.getLogger(__name__)

        if enable_multi_domain:
            self.logger.info("🌐 Multi-domain security specialization enabled")

    def create_enhanced_dataset(self, vulnerabilities: List[Dict[str, Any]],
                              dataset_name: Optional[str] = None,
                              enable_augmentation: bool = True,
                              target_categories: Optional[List[str]] = None) -> DatasetCreationResult:
        """
        Create enhanced dataset with optional multi-domain categorization.

        Args:
            vulnerabilities: List of vulnerability data
            dataset_name: Optional name for the dataset
            enable_augmentation: Whether to enable data augmentation
            target_categories: Optional list of categories to focus on (multi-domain only)

        Returns:
            DatasetCreationResult with enhanced examples
        """
        if self.enable_multi_domain and self.categorizer:
            return self._create_multi_domain_dataset(
                vulnerabilities, dataset_name, enable_augmentation, target_categories
            )
        else:
            # Use existing implementation for backward compatibility
            return self._create_standard_dataset(vulnerabilities, dataset_name, enable_augmentation)

    def _create_multi_domain_dataset(self, vulnerabilities: List[Dict[str, Any]],
                                   dataset_name: Optional[str] = None,
                                   enable_augmentation: bool = True,
                                   target_categories: Optional[List[str]] = None) -> DatasetCreationResult:
        """
        Create multi-domain enhanced dataset with category-specific specialization.

        Args:
            vulnerabilities: List of vulnerability data
            dataset_name: Optional name for the dataset
            enable_augmentation: Whether to enable data augmentation
            target_categories: Optional list of categories to focus on

        Returns:
            DatasetCreationResult with multi-domain enhanced examples
        """
        self.logger.info(f"🌐 Creating multi-domain enhanced dataset from {len(vulnerabilities)} vulnerabilities")

        # Step 1: Categorize vulnerabilities
        categorized_vulns = self.categorizer.categorize_vulnerabilities(vulnerabilities)

        # Step 2: Filter by target categories if specified
        if target_categories:
            categorized_vulns = {
                cat: vulns for cat, vulns in categorized_vulns.items()
                if cat in target_categories
            }
            self.logger.info(f"🎯 Focusing on categories: {list(categorized_vulns.keys())}")

        # Step 3: Generate category-specific enhanced examples
        all_enhanced_examples = []
        category_metadata = {}

        for category, vulns in categorized_vulns.items():
            self.logger.info(f"📦 Processing {category}: {len(vulns)} vulnerabilities")

            category_examples = self._create_category_specific_examples(category, vulns)
            all_enhanced_examples.extend(category_examples)
            category_metadata[category] = {
                'vulnerability_count': len(vulns),
                'enhanced_examples_count': len(category_examples),
                'enhancement_ratio': len(category_examples) / len(vulns) if vulns else 0
            }

        # Step 4: Apply augmentation if enabled
        if enable_augmentation and self.data_augmentor:
            self.logger.info("🔄 Applying multi-domain data augmentation...")
            augmented_examples = []

            for example in all_enhanced_examples:
                # Apply category-aware augmentation
                category = example.metadata.get('detected_category', 'unknown')
                augmentation_config = self._get_category_augmentation_config(category)

                augmented = self.data_augmentor.augment_training_example(
                    example, config=augmentation_config
                )
                augmented_examples.extend(augmented)

            all_enhanced_examples.extend(augmented_examples)

        # Step 5: Create result with comprehensive metadata
        creation_metadata = {
            'multi_domain': True,
            'categories_processed': list(categorized_vulns.keys()),
            'category_breakdown': category_metadata,
            'total_original_vulnerabilities': len(vulnerabilities),
            'total_enhanced_examples': len(all_enhanced_examples),
            'overall_enhancement_ratio': len(all_enhanced_examples) / len(vulnerabilities) if vulnerabilities else 0,
            'augmentation_enabled': enable_augmentation,
            'dataset_name': dataset_name,
            'creation_timestamp': datetime.now().isoformat()
        }

        self.logger.info(f"✅ Multi-domain dataset creation completed:")
        self.logger.info(f"   📊 {len(vulnerabilities)} → {len(all_enhanced_examples)} examples")
        self.logger.info(f"   🎯 Categories: {list(categorized_vulns.keys())}")
        self.logger.info(f"   📈 Enhancement ratio: {creation_metadata['overall_enhancement_ratio']:.1f}x")

        return DatasetCreationResult(
            success=True,
            enhanced_examples=all_enhanced_examples,
            original_examples_count=len(vulnerabilities),
            enhanced_examples_count=len(all_enhanced_examples),
            creation_metadata=creation_metadata
        )
```

#### **1.3 Category-Specific Example Generation**

```python
def _create_category_specific_examples(self, category: str, vulnerabilities: List[Dict]) -> List[EnhancedTrainingExample]:
    """
    Create enhanced training examples specialized for a specific security category.

    Args:
        category: Security category (e.g., 'container_security', 'web_security')
        vulnerabilities: List of vulnerabilities in this category

    Returns:
        List of enhanced training examples with category-specific patterns
    """
    category_examples = []

    # Get category-specific prompt templates and fix patterns
    prompt_template = self._get_category_prompt_template(category)
    fix_patterns = self._get_category_fix_patterns(category)

    for vuln in vulnerabilities:
        try:
            # Extract code context (existing functionality)
            context_result = self.extractor.extract_vulnerability_context(vuln)

            if context_result.success and context_result.code_context:
                # Generate category-specific fixes
                category_fixes = self._generate_category_specific_fixes(
                    category, vuln, context_result.code_context, fix_patterns
                )

                # Create enhanced examples with category specialization
                for fix in category_fixes:
                    instruction = prompt_template.format(
                        vulnerability=vuln,
                        category=category,
                        context=context_result.code_context
                    )

                    enhanced_example = EnhancedTrainingExample(
                        instruction=instruction,
                        response=fix.implementation,
                        metadata={
                            'vulnerability_id': vuln.get('id', 'unknown'),
                            'detected_category': category,
                            'fix_approach': fix.approach.value,
                            'quality_score': fix.quality_score,
                            'framework': fix.framework,
                            'security_pattern': fix.security_pattern
                        },
                        vulnerability_context=vuln,
                        fix_approaches=[fix.to_dict()],
                        code_examples={
                            'vulnerable': context_result.code_context.vulnerable_code,
                            'fixed': fix.implementation
                        }
                    )

                    category_examples.append(enhanced_example)

        except Exception as e:
            self.logger.error(f"Failed to create category example for {vuln.get('id', 'unknown')}: {e}")
            continue

    return category_examples

def _get_category_prompt_template(self, category: str) -> str:
    """Get category-specific instruction prompt template."""

    templates = {
        'container_security': """Analyze this container security vulnerability and provide a comprehensive Dockerfile fix:

Vulnerability: {vulnerability[description]}
Container: {vulnerability[file_path]}
Security Issue: {vulnerability[alert]}

Provide a complete, secure Dockerfile implementation that addresses this vulnerability.
Focus on:
- Base image security and version pinning
- User privileges and non-root execution
- Layer optimization and security scanning
- Runtime security configurations
- Health checks and monitoring setup

Include specific remediation steps and security best practices.""",

        'dependency_vulnerabilities': """Analyze this dependency vulnerability and provide specific package management fixes:

Vulnerability: {vulnerability[description]}
Package: {vulnerability[package_name]}
Current Version: {vulnerability[current_version]}
CVE: {vulnerability[cve_id]}

Provide complete package.json/build.gradle fixes that address this vulnerability.
Focus on:
- Specific version updates with security patches
- Dependency override configurations
- Alternative package recommendations if applicable
- Security audit integration
- Version pinning strategies

Include verification steps and testing recommendations.""",

        'web_security': """Analyze this web application security vulnerability and provide framework-specific fixes:

Vulnerability: {vulnerability[description]}
Endpoint: {vulnerability[uri]}
Security Issue: {vulnerability[alert]}
Framework: {vulnerability[framework]}

Provide complete security configuration code that addresses this vulnerability.
Focus on:
- CORS/CSP policy configuration
- Authentication and authorization patterns
- Input validation and sanitization
- Security headers implementation
- Session management security

Include framework-specific implementation and testing approaches.""",

        'code_vulnerabilities': """Analyze this code security vulnerability and provide secure implementation patterns:

Vulnerability: {vulnerability[description]}
Location: {vulnerability[file_path]}:{vulnerability[line]}
Security Issue: {vulnerability[check_id]}
Language: {vulnerability[language]}

Provide secure code implementation that eliminates this vulnerability.
Focus on:
- Input validation and sanitization
- Output encoding and escaping
- Secure API usage patterns
- Error handling and logging security
- Language-specific security patterns

Include code examples and security validation methods.""",

        'webauthn_security': """Analyze this WebAuthn security vulnerability and provide FIDO2-compliant fixes:

Vulnerability: {vulnerability[description]}
Component: {vulnerability[component]}
Security Issue: {vulnerability[alert]}

Provide complete WebAuthn implementation that addresses this vulnerability.
Focus on:
- Credential validation and verification
- Challenge generation and validation
- Attestation and assertion security
- Origin and domain validation
- FIDO2 compliance requirements

Include implementation examples and security testing approaches.""",

        'mobile_security': """Analyze this mobile security vulnerability and provide Android-specific fixes:

Vulnerability: {vulnerability[description]}
Component: {vulnerability[component]}
Security Issue: {vulnerability[alert]}
Android API: {vulnerability[api_level]}

Provide secure Android implementation that addresses this vulnerability.
Focus on:
- Permission model and declarations
- Component export security
- Intent handling and validation
- Data protection and encryption
- Runtime security checks

Include AndroidManifest.xml configurations and code examples.""",

        'infrastructure_security': """Analyze this infrastructure security issue and provide configuration fixes:

Vulnerability: {vulnerability[description]}
Resource: {vulnerability[resource]}
Security Issue: {vulnerability[check_id]}
Infrastructure Type: {vulnerability[resource_type]}

Provide secure infrastructure configuration that addresses this vulnerability.
Focus on:
- IAM policies and permission models
- Network security and isolation
- Encryption and key management
- Monitoring and logging configuration
- Compliance and governance

Include Terraform/CloudFormation examples and security validation."""
    }

    return templates.get(category, templates['code_vulnerabilities'])  # Default fallback

def _get_category_fix_patterns(self, category: str) -> Dict[str, List[str]]:
    """Get category-specific fix patterns and security practices."""

    patterns = {
        'container_security': {
            'base_image_security': [
                'Use specific version tags instead of latest',
                'Use minimal base images (alpine, distroless)',
                'Implement multi-stage builds',
                'Add security scanning in CI/CD'
            ],
            'user_privileges': [
                'Create non-root user',
                'Set USER instruction before EXPOSE',
                'Use proper file ownership with COPY --chown',
                'Implement least privilege principle'
            ],
            'runtime_security': [
                'Add health checks',
                'Set resource limits',
                'Configure security contexts',
                'Implement proper signal handling'
            ]
        },

        'dependency_vulnerabilities': {
            'version_management': [
                'Pin to specific patched versions',
                'Use package-lock.json or gradle.lockfile',
                'Implement dependency override strategies',
                'Add security audit automation'
            ],
            'alternative_packages': [
                'Research alternative implementations',
                'Evaluate package maintenance status',
                'Consider feature parity analysis',
                'Implement gradual migration strategies'
            ]
        },

        'web_security': {
            'cors_security': [
                'Explicit origin whitelisting',
                'Credential-aware CORS configuration',
                'Method and header restrictions',
                'Preflight request handling'
            ],
            'csp_implementation': [
                'Strict CSP policy definition',
                'Nonce-based script execution',
                'Report-only mode for testing',
                'Regular policy review and updates'
            ]
        },

        'code_vulnerabilities': {
            'input_validation': [
                'Whitelist-based validation',
                'Type-safe parameter binding',
                'Regular expression validation',
                'Input length and format limits'
            ],
            'output_encoding': [
                'Context-aware encoding',
                'Framework-specific escaping',
                'Content type validation',
                'Encoding consistency checks'
            ]
        }
    }

    return patterns.get(category, {})
```

#### **1.4 Testing and Validation**

**Create test file**: `tests/test_vulnerability_categorization.py`

```python
#!/usr/bin/env python3
"""
Test suite for vulnerability categorization functionality.
"""

import pytest
from pathlib import Path
import json
from enhanced_dataset_creator import VulnerabilityCategorizor

class TestVulnerabilityCategorizor:
    """Test cases for vulnerability categorization."""

    @pytest.fixture
    def categorizer(self):
        """Create categorizer instance for testing."""
        return VulnerabilityCategorizor()

    @pytest.fixture
    def sample_vulnerabilities(self):
        """Sample vulnerability data for testing."""
        return [
            # Container security (Trivy)
            {
                'tool': 'trivy',
                'description': 'Alpine base image vulnerability',
                'file_path': 'Dockerfile',
                'severity': 'HIGH'
            },
            # Dependency vulnerability (OSV Scanner)
            {
                'tool': 'osv-scanner',
                'description': 'Jackson core stack overflow vulnerability',
                'package_name': 'jackson-core',
                'cve_id': 'CVE-2025-52999'
            },
            # Web security (ZAP)
            {
                'tool': 'zap',
                'alert': 'CORS Misconfiguration',
                'uri': 'http://localhost:8080',
                'description': 'CORS policy allows malicious origins'
            },
            # WebAuthn security (Semgrep)
            {
                'tool': 'semgrep',
                'check_id': 'webauthn-credential-validation-bypass',
                'description': 'WebAuthn credential validation should not be bypassed',
                'file_path': 'WebAuthnViewModel.kt'
            },
            # Mobile security (Semgrep)
            {
                'tool': 'semgrep',
                'check_id': 'exported_activity',
                'description': 'Application exports an activity without proper validation',
                'file_path': 'AndroidManifest.xml'
            },
            # Code vulnerability (Semgrep)
            {
                'tool': 'semgrep',
                'check_id': 'detect-child-process',
                'description': 'Command injection vulnerability in child_process',
                'file_path': 'unified-security-comment.cjs'
            }
        ]

    def test_container_security_detection(self, categorizer, sample_vulnerabilities):
        """Test container security vulnerability detection."""
        trivy_vuln = sample_vulnerabilities[0]
        category = categorizer._detect_vulnerability_category(trivy_vuln)
        assert category == 'container_security'

    def test_dependency_vulnerability_detection(self, categorizer, sample_vulnerabilities):
        """Test dependency vulnerability detection."""
        osv_vuln = sample_vulnerabilities[1]
        category = categorizer._detect_vulnerability_category(osv_vuln)
        assert category == 'dependency_vulnerabilities'

    def test_web_security_detection(self, categorizer, sample_vulnerabilities):
        """Test web security vulnerability detection."""
        zap_vuln = sample_vulnerabilities[2]
        category = categorizer._detect_vulnerability_category(zap_vuln)
        assert category == 'web_security'

    def test_webauthn_security_detection(self, categorizer, sample_vulnerabilities):
        """Test WebAuthn security vulnerability detection."""
        webauthn_vuln = sample_vulnerabilities[3]
        category = categorizer._detect_vulnerability_category(webauthn_vuln)
        assert category == 'webauthn_security'

    def test_mobile_security_detection(self, categorizer, sample_vulnerabilities):
        """Test mobile security vulnerability detection."""
        mobile_vuln = sample_vulnerabilities[4]
        category = categorizer._detect_vulnerability_category(mobile_vuln)
        assert category == 'mobile_security'

    def test_code_vulnerability_detection(self, categorizer, sample_vulnerabilities):
        """Test code vulnerability detection."""
        code_vuln = sample_vulnerabilities[5]
        category = categorizer._detect_vulnerability_category(code_vuln)
        assert category == 'code_vulnerabilities'

    def test_categorize_vulnerabilities_integration(self, categorizer, sample_vulnerabilities):
        """Test complete vulnerability categorization."""
        categorized = categorizer.categorize_vulnerabilities(sample_vulnerabilities)

        # Verify all categories are represented
        expected_categories = {
            'container_security', 'dependency_vulnerabilities', 'web_security',
            'webauthn_security', 'mobile_security', 'code_vulnerabilities'
        }
        assert set(categorized.keys()) == expected_categories

        # Verify each category has the expected vulnerability
        assert len(categorized['container_security']) == 1
        assert len(categorized['dependency_vulnerabilities']) == 1
        assert len(categorized['web_security']) == 1
        assert len(categorized['webauthn_security']) == 1
        assert len(categorized['mobile_security']) == 1
        assert len(categorized['code_vulnerabilities']) == 1

    def test_category_metadata_addition(self, categorizer, sample_vulnerabilities):
        """Test that categorization adds metadata to vulnerabilities."""
        categorized = categorizer.categorize_vulnerabilities(sample_vulnerabilities)

        # Check that all vulnerabilities have category metadata
        for category_vulns in categorized.values():
            for vuln in category_vulns:
                assert 'detected_category' in vuln
                assert vuln['detected_category'] in [
                    'container_security', 'dependency_vulnerabilities', 'web_security',
                    'webauthn_security', 'mobile_security', 'code_vulnerabilities',
                    'infrastructure_security'
                ]

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### Phase 2: Enhanced Dataset Creator Modifications (Week 2)

#### **2.1 Category-Specific Fix Generation**

**File**: `enhanced_dataset_creator.py` - Add specialized fix generation methods

```python
def _generate_category_specific_fixes(self, category: str, vulnerability: Dict,
                                    code_context: CodeContext, fix_patterns: Dict) -> List[SecurityFix]:
    """
    Generate security fixes specialized for the vulnerability category.

    Args:
        category: Security category (e.g., 'container_security')
        vulnerability: Vulnerability data
        code_context: Extracted code context
        fix_patterns: Category-specific fix patterns

    Returns:
        List of SecurityFix objects with category-specific implementations
    """
    category_fixes = []

    # Get category-specific fix generators
    fix_generators = {
        'container_security': self._generate_container_security_fixes,
        'dependency_vulnerabilities': self._generate_dependency_fixes,
        'web_security': self._generate_web_security_fixes,
        'code_vulnerabilities': self._generate_code_security_fixes,
        'webauthn_security': self._generate_webauthn_fixes,
        'mobile_security': self._generate_mobile_security_fixes,
        'infrastructure_security': self._generate_infrastructure_fixes
    }

    generator = fix_generators.get(category, self._generate_generic_fixes)

    try:
        category_fixes = generator(vulnerability, code_context, fix_patterns)
    except Exception as e:
        self.logger.error(f"Category-specific fix generation failed for {category}: {e}")
        # Fallback to generic fix generation
        category_fixes = self._generate_generic_fixes(vulnerability, code_context, fix_patterns)

    return category_fixes

def _generate_container_security_fixes(self, vulnerability: Dict, code_context: CodeContext,
                                     fix_patterns: Dict) -> List[SecurityFix]:
    """Generate container security specific fixes."""
    fixes = []

    # Detect fix type from vulnerability
    if 'dockerfile' in vulnerability.get('file_path', '').lower():
        # Dockerfile security fixes
        if 'base image' in vulnerability.get('description', '').lower():
            fixes.append(self._create_base_image_security_fix(vulnerability, code_context))

        if 'user' in vulnerability.get('description', '').lower() or 'root' in vulnerability.get('description', '').lower():
            fixes.append(self._create_user_privilege_fix(vulnerability, code_context))

        if 'layer' in vulnerability.get('description', '').lower():
            fixes.append(self._create_layer_optimization_fix(vulnerability, code_context))

    elif 'container' in vulnerability.get('description', '').lower():
        # Runtime container fixes
        fixes.append(self._create_runtime_security_fix(vulnerability, code_context))

    return fixes

def _create_base_image_security_fix(self, vulnerability: Dict, code_context: CodeContext) -> SecurityFix:
    """Create base image security fix for containers."""

    # Extract current FROM statement
    vulnerable_code = code_context.vulnerable_code

    # Generate secure base image configuration
    secure_implementation = """# Secure base image configuration
FROM node:18.17.1-alpine AS base  # Use specific patched version

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \\
    adduser -S nodejs -u 1001

# Set working directory with proper ownership
WORKDIR /app
RUN chown nodejs:nodejs /app

# Install dependencies as root, then switch to non-root
COPY package*.json ./
RUN npm ci --only=production && \\
    npm cache clean --force

# Copy application code with proper ownership
COPY --chown=nodejs:nodejs . .

# Switch to non-root user before exposing ports
USER nodejs

# Expose port and add health check
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:3000/health || exit 1

# Set secure runtime environment
ENV NODE_ENV=production
ENV NODE_OPTIONS="--max-old-space-size=512"

CMD ["node", "server.js"]"""

    return SecurityFix(
        approach=FixApproach.SECURE_CONFIGURATION,
        implementation=secure_implementation,
        security_pattern="base_image_hardening",
        framework="Docker",
        quality_score=0.9,
        explanation="Implements secure base image with version pinning, non-root user, proper ownership, health checks, and resource limits.",
        testing_approach="Use docker security scanning tools like Trivy or Snyk to validate the hardened image."
    )

def _generate_dependency_fixes(self, vulnerability: Dict, code_context: CodeContext,
                             fix_patterns: Dict) -> List[SecurityFix]:
    """Generate dependency vulnerability fixes."""
    fixes = []

    package_name = vulnerability.get('package_name', '')
    current_version = vulnerability.get('current_version', '')
    cve_id = vulnerability.get('cve_id', '')

    if 'package.json' in vulnerability.get('file_path', ''):
        fixes.append(self._create_npm_security_fix(vulnerability, code_context))
    elif 'gradle' in vulnerability.get('file_path', '') or '.gradle' in vulnerability.get('file_path', ''):
        fixes.append(self._create_gradle_security_fix(vulnerability, code_context))
    elif 'pom.xml' in vulnerability.get('file_path', ''):
        fixes.append(self._create_maven_security_fix(vulnerability, code_context))

    return fixes

def _create_npm_security_fix(self, vulnerability: Dict, code_context: CodeContext) -> SecurityFix:
    """Create npm package security fix."""

    package_name = vulnerability.get('package_name', 'vulnerable-package')
    secure_version = vulnerability.get('fixed_version', '1.0.0')
    cve_id = vulnerability.get('cve_id', 'CVE-XXXX-XXXX')

    secure_implementation = f"""{{
  "dependencies": {{
    "{package_name}": "^{secure_version}",
    "// Security fix for {cve_id}": "Updated to patched version"
  }},
  "overrides": {{
    "{package_name}": "{secure_version}"
  }},
  "scripts": {{
    "audit": "npm audit",
    "audit-fix": "npm audit fix",
    "security-check": "npm audit --audit-level=moderate"
  }},
  "engines": {{
    "node": ">=18.17.1"
  }}
}}

// package-lock.json validation
// Run: npm ci to ensure exact dependency versions
// Run: npm audit to verify no remaining vulnerabilities

// Security automation in CI/CD:
// - Add npm audit to build pipeline
// - Configure dependency update automation
// - Set up security alert monitoring"""

    return SecurityFix(
        approach=FixApproach.DEPENDENCY_UPDATE,
        implementation=secure_implementation,
        security_pattern="dependency_security_management",
        framework="npm/Node.js",
        quality_score=0.85,
        explanation=f"Updates {package_name} to secure version {secure_version}, adds override configuration, and implements security automation.",
        testing_approach="Run npm audit and verify no HIGH/CRITICAL vulnerabilities remain. Test application functionality with updated dependencies."
    )

def _generate_web_security_fixes(self, vulnerability: Dict, code_context: CodeContext,
                               fix_patterns: Dict) -> List[SecurityFix]:
    """Generate web application security fixes."""
    fixes = []

    alert_type = vulnerability.get('alert', '').lower()

    if 'cors' in alert_type:
        fixes.append(self._create_cors_security_fix(vulnerability, code_context))
    elif 'csp' in alert_type or 'content security policy' in alert_type:
        fixes.append(self._create_csp_security_fix(vulnerability, code_context))
    elif 'xss' in alert_type:
        fixes.append(self._create_xss_protection_fix(vulnerability, code_context))
    elif 'csrf' in alert_type:
        fixes.append(self._create_csrf_protection_fix(vulnerability, code_context))

    return fixes

def _create_cors_security_fix(self, vulnerability: Dict, code_context: CodeContext) -> SecurityFix:
    """Create CORS security configuration fix."""

    # Detect framework from file path or context
    framework = self._detect_web_framework(vulnerability, code_context)

    if framework == 'ktor':
        secure_implementation = """// KTor CORS Security Configuration
install(CORS) {
    // Explicit origin whitelist - NEVER use allowAnyHost()
    allowHost("localhost:3000")
    allowHost("https://yourdomain.com")
    allowHost("https://app.yourdomain.com")

    // Restrict HTTP methods to only what's needed
    allowMethod(HttpMethod.Get)
    allowMethod(HttpMethod.Post)
    allowMethod(HttpMethod.Put)
    allowMethod(HttpMethod.Delete)
    allowMethod(HttpMethod.Options)  // Required for preflight

    // Explicit header whitelist
    allowHeader(HttpHeaders.ContentType)
    allowHeader(HttpHeaders.Authorization)
    allowHeader("X-Requested-With")
    allowHeader("X-CSRF-Token")

    // Credentials handling
    allowCredentials = true

    // Security headers
    maxAgeInSeconds = 3600  // Cache preflight for 1 hour max

    // Additional security configurations
    allowNonSimpleContentTypes = false  // Restrict content types
}

// Additional security middleware
install(DefaultHeaders) {
    header("X-Frame-Options", "DENY")
    header("X-Content-Type-Options", "nosniff")
    header("Referrer-Policy", "strict-origin-when-cross-origin")
    header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
}"""

    elif framework == 'express':
        secure_implementation = """// Express.js CORS Security Configuration
const cors = require('cors');

const corsOptions = {
  // Explicit origin whitelist
  origin: [
    'http://localhost:3000',
    'https://yourdomain.com',
    'https://app.yourdomain.com'
  ],

  // Restrict methods
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],

  // Explicit header whitelist
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'X-CSRF-Token'
  ],

  // Credentials handling
  credentials: true,

  // Preflight cache
  maxAge: 3600,

  // Security options
  optionsSuccessStatus: 200,
  preflightContinue: false
};

app.use(cors(corsOptions));

// Additional security headers
app.use((req, res, next) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  next();
});"""

    else:
        # Generic CORS fix
        secure_implementation = """// Generic CORS Security Configuration
// Configure CORS with explicit origin whitelist
const allowedOrigins = [
  'http://localhost:3000',
  'https://yourdomain.com',
  'https://app.yourdomain.com'
];

// CORS middleware function
function configureCORS(req, res, next) {
  const origin = req.headers.origin;

  // Check if origin is in whitelist
  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }

  // Restrict methods
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');

  // Explicit headers
  res.setHeader('Access-Control-Allow-Headers',
    'Content-Type, Authorization, X-Requested-With, X-CSRF-Token');

  // Credentials
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  // Preflight cache
  res.setHeader('Access-Control-Max-Age', '3600');

  next();
}"""

    return SecurityFix(
        approach=FixApproach.SECURE_CONFIGURATION,
        implementation=secure_implementation,
        security_pattern="cors_security_configuration",
        framework=framework,
        quality_score=0.9,
        explanation="Implements secure CORS configuration with explicit origin whitelist, method restrictions, header controls, and additional security headers.",
        testing_approach="Test with browser developer tools, verify preflight requests, and validate that unauthorized origins are blocked."
    )

def _detect_web_framework(self, vulnerability: Dict, code_context: CodeContext) -> str:
    """Detect web framework from vulnerability context."""
    file_path = vulnerability.get('file_path', '').lower()
    description = vulnerability.get('description', '').lower()

    if '.kt' in file_path or 'ktor' in description:
        return 'ktor'
    elif '.js' in file_path and ('express' in description or 'node' in description):
        return 'express'
    elif '.java' in file_path and 'spring' in description:
        return 'spring'
    elif '.py' in file_path and ('flask' in description or 'django' in description):
        return 'python_web'

    return 'generic'
```

#### **2.2 Data Augmentation Configuration**

```python
def _get_category_augmentation_config(self, category: str) -> AugmentationConfig:
    """Get category-specific data augmentation configuration."""

    base_config = AugmentationConfig(
        enable_semantic_paraphrase=True,
        enable_framework_variation=True,
        enable_severity_variation=True,
        max_augmented_per_example=2
    )

    # Category-specific augmentation settings
    category_configs = {
        'container_security': AugmentationConfig(
            enable_semantic_paraphrase=True,
            enable_framework_variation=True,  # Docker vs Podman vs containerd
            enable_severity_variation=True,
            enable_version_variation=True,    # Different base image versions
            max_augmented_per_example=3,
            framework_variations=['docker', 'podman', 'containerd'],
            version_variations=['alpine', 'ubuntu', 'debian']
        ),

        'dependency_vulnerabilities': AugmentationConfig(
            enable_semantic_paraphrase=True,
            enable_framework_variation=True,  # npm vs yarn vs gradle vs maven
            enable_severity_variation=True,
            enable_version_variation=True,    # Different package versions
            max_augmented_per_example=4,
            framework_variations=['npm', 'yarn', 'gradle', 'maven'],
            package_manager_patterns=True
        ),

        'web_security': AugmentationConfig(
            enable_semantic_paraphrase=True,
            enable_framework_variation=True,  # Different web frameworks
            enable_severity_variation=True,
            max_augmented_per_example=3,
            framework_variations=['ktor', 'express', 'spring', 'flask', 'django'],
            security_pattern_variations=True
        ),

        'webauthn_security': AugmentationConfig(
            enable_semantic_paraphrase=True,
            enable_framework_variation=False,  # WebAuthn is standardized
            enable_severity_variation=True,
            enable_fido2_pattern_variation=True,
            max_augmented_per_example=2
        )
    }

    return category_configs.get(category, base_config)
```

### Phase 3: Sequential Fine-Tuner Enhancement (Week 3)

#### **3.1 Multi-Domain Validation Integration**

**File**: `sequential_fine_tuner.py` - Enhance validation methods

```python
class SequentialFineTuner:
    """Enhanced with multi-domain security specialization."""

    def __init__(self, config: OLMoSecurityConfig, enable_multi_domain: bool = False,
                 target_categories: Optional[List[str]] = None):
        """
        Initialize sequential fine-tuner with optional multi-domain support.

        Args:
            config: OLMo security configuration
            enable_multi_domain: Enable multi-domain specialization
            target_categories: Optional list of categories to focus on
        """
        # Existing initialization (unchanged)
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.base_fine_tuner = OLMoFineTuner(config)

        # NEW: Multi-domain components
        self.enable_multi_domain = enable_multi_domain
        self.target_categories = target_categories or []
        self.multi_domain_validator = MultiDomainValidator() if enable_multi_domain else None

        if enable_multi_domain:
            self.logger.info(f"🌐 Multi-domain sequential fine-tuning enabled")
            if target_categories:
                self.logger.info(f"🎯 Target categories: {target_categories}")

    def _validate_stage2_response(self, vulnerability: Dict[str, Any], response: str) -> Dict[str, Any]:
        """Enhanced Stage 2 validation with optional multi-domain awareness."""

        # Always run base validation for backward compatibility
        base_validation = self._validate_base_stage2_response(vulnerability, response)

        # Add multi-domain validation if enabled
        if self.enable_multi_domain and self.multi_domain_validator:
            category = vulnerability.get('detected_category', 'unknown')

            multi_domain_validation = self.multi_domain_validator.validate_category_specific_fix(
                category, vulnerability, response
            )

            # Combine base and multi-domain scores
            combined_score = self._combine_validation_scores(base_validation, multi_domain_validation)

            # Enhance base validation with multi-domain insights
            base_validation.update({
                'multi_domain_score': multi_domain_validation['category_score'],
                'detected_category': category,
                'category_specialization': multi_domain_validation['specialization_level'],
                'framework_awareness': multi_domain_validation['framework_score'],
                'domain_patterns_detected': multi_domain_validation['patterns_detected'],
                'overall_score': combined_score
            })

        return base_validation

    def _validate_base_stage2_response(self, vulnerability: Dict[str, Any], response: str) -> Dict[str, Any]:
        """Base Stage 2 validation (existing logic, unchanged for compatibility)."""
        response_lower = response.lower()

        # Check for code fix components
        has_code_block = '```' in response or 'def ' in response or 'function' in response
        has_security_improvements = any(term in response_lower for term in ['security', 'validation', 'sanitize'])
        has_implementation = any(term in response_lower for term in ['implementation', 'steps', 'deploy'])
        has_testing = any(term in response_lower for term in ['test', 'verify', 'validate'])

        # Calculate scores
        syntax_correctness = 0.8 if has_code_block else 0.2
        security_pattern_application = 0.9 if has_security_improvements else 0.3
        implementation_completeness = (has_code_block + has_implementation + has_testing) / 3
        code_quality = min(len(response) / 400, 1.0) * 0.6 + (implementation_completeness * 0.4)

        return {
            'vulnerability_id': vulnerability.get('vulnerability_id', vulnerability.get('id', 'unknown')),
            'syntax_correctness': syntax_correctness,
            'security_pattern_application': security_pattern_application,
            'implementation_completeness': implementation_completeness,
            'code_quality': code_quality,
            'response_length': len(response),
            'has_code_block': has_code_block,
            'has_security_improvements': has_security_improvements,
            'has_implementation': has_implementation,
            'has_testing': has_testing,
            'overall_score': (syntax_correctness + security_pattern_application + implementation_completeness + code_quality) / 4
        }

    def _combine_validation_scores(self, base_validation: Dict, multi_domain_validation: Dict) -> float:
        """Combine base validation and multi-domain validation scores."""

        base_score = base_validation['overall_score']
        category_score = multi_domain_validation['category_score']
        framework_score = multi_domain_validation['framework_score']

        # Weighted combination: 50% base + 35% category + 15% framework
        combined_score = (base_score * 0.5) + (category_score * 0.35) + (framework_score * 0.15)

        return min(combined_score, 1.0)  # Cap at 1.0
```

#### **3.2 Multi-Domain Validator Implementation**

**File**: `multi_domain_validator.py` (NEW FILE)

```python
#!/usr/bin/env python3
"""
Multi-Domain Security Validator

Provides category-specific validation for security fixes across different domains.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class SecurityDomain(Enum):
    """Security domain enumeration."""
    CONTAINER_SECURITY = "container_security"
    DEPENDENCY_VULNERABILITIES = "dependency_vulnerabilities"
    WEB_SECURITY = "web_security"
    CODE_VULNERABILITIES = "code_vulnerabilities"
    WEBAUTHN_SECURITY = "webauthn_security"
    MOBILE_SECURITY = "mobile_security"
    INFRASTRUCTURE_SECURITY = "infrastructure_security"


@dataclass
class DomainValidationResult:
    """Result of domain-specific validation."""
    category_score: float
    framework_score: float
    specialization_level: str
    patterns_detected: List[str]
    quality_indicators: Dict[str, bool]
    recommendations: List[str]


class MultiDomainValidator:
    """Validates security fixes with domain-specific expertise."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Domain-specific pattern libraries
        self.domain_patterns = self._initialize_domain_patterns()
        self.framework_patterns = self._initialize_framework_patterns()
        self.quality_indicators = self._initialize_quality_indicators()

    def validate_category_specific_fix(self, category: str, vulnerability: Dict,
                                     response: str) -> DomainValidationResult:
        """
        Validate security fix with category-specific expertise.

        Args:
            category: Security category
            vulnerability: Vulnerability data
            response: Generated fix response

        Returns:
            DomainValidationResult with category-specific scores
        """
        try:
            domain = SecurityDomain(category)
        except ValueError:
            domain = SecurityDomain.CODE_VULNERABILITIES  # Default fallback

        # Get domain-specific validator
        validators = {
            SecurityDomain.CONTAINER_SECURITY: self._validate_container_security,
            SecurityDomain.DEPENDENCY_VULNERABILITIES: self._validate_dependency_fix,
            SecurityDomain.WEB_SECURITY: self._validate_web_security,
            SecurityDomain.CODE_VULNERABILITIES: self._validate_code_security,
            SecurityDomain.WEBAUTHN_SECURITY: self._validate_webauthn_security,
            SecurityDomain.MOBILE_SECURITY: self._validate_mobile_security,
            SecurityDomain.INFRASTRUCTURE_SECURITY: self._validate_infrastructure_security
        }

        validator = validators[domain]
        return validator(vulnerability, response)

    def _validate_container_security(self, vulnerability: Dict, response: str) -> DomainValidationResult:
        """Validate container security fixes."""
        response_lower = response.lower()
        patterns_detected = []
        quality_indicators = {}

        # Check for container security patterns
        container_patterns = self.domain_patterns[SecurityDomain.CONTAINER_SECURITY]

        # Base image security
        if any(pattern in response_lower for pattern in container_patterns['base_image']):
            patterns_detected.append('base_image_security')
            quality_indicators['uses_specific_versions'] = any(
                re.search(r'\d+\.\d+\.\d+', response) for pattern in ['alpine', 'ubuntu', 'node']
            )

        # User privilege management
        if any(pattern in response_lower for pattern in container_patterns['user_privileges']):
            patterns_detected.append('user_privilege_management')
            quality_indicators['creates_nonroot_user'] = 'user' in response_lower and 'root' not in response_lower

        # Runtime security
        if any(pattern in response_lower for pattern in container_patterns['runtime_security']):
            patterns_detected.append('runtime_security')
            quality_indicators['has_health_checks'] = 'healthcheck' in response_lower

        # Layer optimization
        if any(pattern in response_lower for pattern in container_patterns['layer_optimization']):
            patterns_detected.append('layer_optimization')
            quality_indicators['uses_multistage'] = 'as base' in response_lower or 'as builder' in response_lower

        # Calculate category score
        category_score = len(patterns_detected) / 4.0  # 4 main container security areas

        # Framework awareness (Docker-specific)
        framework_score = self._calculate_framework_score('docker', response)

        # Determine specialization level
        if category_score >= 0.8:
            specialization_level = 'high'
        elif category_score >= 0.5:
            specialization_level = 'medium'
        else:
            specialization_level = 'low'

        recommendations = self._generate_container_recommendations(quality_indicators)

        return DomainValidationResult(
            category_score=category_score,
            framework_score=framework_score,
            specialization_level=specialization_level,
            patterns_detected=patterns_detected,
            quality_indicators=quality_indicators,
            recommendations=recommendations
        )

    def _validate_dependency_fix(self, vulnerability: Dict, response: str) -> DomainValidationResult:
        """Validate dependency vulnerability fixes."""
        response_lower = response.lower()
        patterns_detected = []
        quality_indicators = {}

        # Check for dependency management patterns
        dep_patterns = self.domain_patterns[SecurityDomain.DEPENDENCY_VULNERABILITIES]

        # Version management
        if any(pattern in response_lower for pattern in dep_patterns['version_management']):
            patterns_detected.append('version_management')
            quality_indicators['specifies_exact_version'] = re.search(r'"[\w-]+"\s*:\s*"[\d\.]+', response) is not None

        # Package override
        if any(pattern in response_lower for pattern in dep_patterns['override_strategies']):
            patterns_detected.append('override_strategies')
            quality_indicators['uses_override'] = 'override' in response_lower or 'resolution' in response_lower

        # Security automation
        if any(pattern in response_lower for pattern in dep_patterns['security_automation']):
            patterns_detected.append('security_automation')
            quality_indicators['includes_audit'] = 'audit' in response_lower

        # Alternative suggestions
        if any(pattern in response_lower for pattern in dep_patterns['alternatives']):
            patterns_detected.append('alternative_packages')
            quality_indicators['suggests_alternatives'] = 'alternative' in response_lower

        # Calculate scores
        category_score = len(patterns_detected) / 4.0

        # Framework awareness (package manager specific)
        framework = self._detect_package_manager(vulnerability, response)
        framework_score = self._calculate_framework_score(framework, response)

        # Specialization level
        if category_score >= 0.75:
            specialization_level = 'high'
        elif category_score >= 0.5:
            specialization_level = 'medium'
        else:
            specialization_level = 'low'

        recommendations = self._generate_dependency_recommendations(quality_indicators)

        return DomainValidationResult(
            category_score=category_score,
            framework_score=framework_score,
            specialization_level=specialization_level,
            patterns_detected=patterns_detected,
            quality_indicators=quality_indicators,
            recommendations=recommendations
        )

    def _validate_web_security(self, vulnerability: Dict, response: str) -> DomainValidationResult:
        """Validate web application security fixes."""
        response_lower = response.lower()
        patterns_detected = []
        quality_indicators = {}

        # Check for web security patterns
        web_patterns = self.domain_patterns[SecurityDomain.WEB_SECURITY]

        # CORS security
        if any(pattern in response_lower for pattern in web_patterns['cors_security']):
            patterns_detected.append('cors_security')
            quality_indicators['explicit_origins'] = 'allowhost' in response_lower or 'origin:' in response_lower
            quality_indicators['no_wildcard'] = '*' not in response or 'allowanyhost' not in response_lower

        # CSP implementation
        if any(pattern in response_lower for pattern in web_patterns['csp_security']):
            patterns_detected.append('csp_security')
            quality_indicators['strict_csp'] = "'strict-dynamic'" in response or "'nonce-" in response

        # Authentication security
        if any(pattern in response_lower for pattern in web_patterns['auth_security']):
            patterns_detected.append('auth_security')
            quality_indicators['proper_session'] = 'session' in response_lower and 'secure' in response_lower

        # Input validation
        if any(pattern in response_lower for pattern in web_patterns['input_validation']):
            patterns_detected.append('input_validation')
            quality_indicators['validation_library'] = any(lib in response_lower for lib in ['joi', 'yup', 'zod'])

        # Calculate scores
        category_score = len(patterns_detected) / 4.0

        # Framework awareness
        framework = self._detect_web_framework(vulnerability, response)
        framework_score = self._calculate_framework_score(framework, response)

        # Specialization level
        if category_score >= 0.8:
            specialization_level = 'high'
        elif category_score >= 0.6:
            specialization_level = 'medium'
        else:
            specialization_level = 'low'

        recommendations = self._generate_web_security_recommendations(quality_indicators)

        return DomainValidationResult(
            category_score=category_score,
            framework_score=framework_score,
            specialization_level=specialization_level,
            patterns_detected=patterns_detected,
            quality_indicators=quality_indicators,
            recommendations=recommendations
        )

    def _initialize_domain_patterns(self) -> Dict[SecurityDomain, Dict[str, List[str]]]:
        """Initialize domain-specific security patterns."""
        return {
            SecurityDomain.CONTAINER_SECURITY: {
                'base_image': ['from', 'alpine', 'version', 'tag', 'digest'],
                'user_privileges': ['user', 'adduser', 'addgroup', 'chown', 'chmod'],
                'runtime_security': ['healthcheck', 'expose', 'env', 'workdir'],
                'layer_optimization': ['multi-stage', 'as base', 'as builder', 'copy --from']
            },

            SecurityDomain.DEPENDENCY_VULNERABILITIES: {
                'version_management': ['version', 'lockfile', 'exact', 'pin', 'upgrade'],
                'override_strategies': ['override', 'resolution', 'force', 'resolutions'],
                'security_automation': ['audit', 'security', 'vulnerability', 'scan'],
                'alternatives': ['alternative', 'replace', 'migrate', 'substitute']
            },

            SecurityDomain.WEB_SECURITY: {
                'cors_security': ['cors', 'origin', 'allowhost', 'allowcredentials', 'preflight'],
                'csp_security': ['content-security-policy', 'csp', 'nonce', 'strict-dynamic'],
                'auth_security': ['authentication', 'authorization', 'session', 'token', 'jwt'],
                'input_validation': ['validation', 'sanitize', 'escape', 'whitelist', 'regex']
            },

            SecurityDomain.CODE_VULNERABILITIES: {
                'input_validation': ['validate', 'sanitize', 'whitelist', 'regex', 'type'],
                'output_encoding': ['encode', 'escape', 'html', 'url', 'json'],
                'injection_prevention': ['prepared', 'parameterized', 'query', 'statement'],
                'error_handling': ['try', 'catch', 'error', 'exception', 'log']
            },

            SecurityDomain.WEBAUTHN_SECURITY: {
                'credential_validation': ['credential', 'validate', 'verify', 'assertion'],
                'challenge_management': ['challenge', 'random', 'expire', 'timeout'],
                'attestation_security': ['attestation', 'trusted', 'origin', 'rp'],
                'fido2_compliance': ['fido2', 'webauthn', 'authenticator', 'public-key']
            },

            SecurityDomain.MOBILE_SECURITY: {
                'permission_management': ['permission', 'uses-permission', 'exported', 'android'],
                'component_security': ['activity', 'service', 'receiver', 'provider'],
                'data_protection': ['encrypt', 'keystore', 'shared-preferences', 'database'],
                'runtime_security': ['runtime', 'permission', 'check', 'request']
            },

            SecurityDomain.INFRASTRUCTURE_SECURITY: {
                'iam_security': ['iam', 'policy', 'role', 'permission', 'access'],
                'network_security': ['vpc', 'security-group', 'network', 'firewall'],
                'encryption': ['encrypt', 'kms', 'key', 'cipher', 'tls'],
                'monitoring': ['log', 'monitor', 'audit', 'cloudtrail', 'alert']
            }
        }

    def _initialize_framework_patterns(self) -> Dict[str, List[str]]:
        """Initialize framework-specific patterns."""
        return {
            'docker': ['from', 'run', 'copy', 'workdir', 'expose', 'cmd', 'healthcheck'],
            'npm': ['package.json', 'npm', 'dependencies', 'devdependencies', 'scripts'],
            'gradle': ['build.gradle', 'dependencies', 'implementation', 'testImplementation'],
            'maven': ['pom.xml', 'dependency', 'groupid', 'artifactid', 'version'],
            'ktor': ['install', 'cors', 'routing', 'authentication', 'httpmethod'],
            'express': ['app.use', 'cors', 'middleware', 'router', 'req', 'res'],
            'spring': ['@controller', '@service', '@repository', 'spring', 'boot'],
            'android': ['androidmanifest', 'activity', 'permission', 'intent-filter']
        }

    def _calculate_framework_score(self, framework: str, response: str) -> float:
        """Calculate framework-awareness score."""
        if framework not in self.framework_patterns:
            return 0.5  # Neutral score for unknown frameworks

        response_lower = response.lower()
        framework_patterns = self.framework_patterns[framework]

        matches = sum(1 for pattern in framework_patterns if pattern in response_lower)
        score = min(matches / len(framework_patterns), 1.0)

        return score

    def _detect_package_manager(self, vulnerability: Dict, response: str) -> str:
        """Detect package manager from vulnerability and response."""
        file_path = vulnerability.get('file_path', '').lower()
        response_lower = response.lower()

        if 'package.json' in file_path or 'npm' in response_lower:
            return 'npm'
        elif 'build.gradle' in file_path or 'gradle' in response_lower:
            return 'gradle'
        elif 'pom.xml' in file_path or 'maven' in response_lower:
            return 'maven'
        elif 'yarn' in response_lower:
            return 'yarn'

        return 'generic'

    def _detect_web_framework(self, vulnerability: Dict, response: str) -> str:
        """Detect web framework from vulnerability and response."""
        file_path = vulnerability.get('file_path', '').lower()
        response_lower = response.lower()

        if '.kt' in file_path or 'ktor' in response_lower:
            return 'ktor'
        elif 'express' in response_lower or 'app.use' in response_lower:
            return 'express'
        elif 'spring' in response_lower or '@controller' in response_lower:
            return 'spring'
        elif 'flask' in response_lower or 'django' in response_lower:
            return 'python_web'

        return 'generic'

    def _generate_container_recommendations(self, quality_indicators: Dict[str, bool]) -> List[str]:
        """Generate container security recommendations."""
        recommendations = []

        if not quality_indicators.get('uses_specific_versions'):
            recommendations.append("Use specific version tags instead of 'latest' for better security")

        if not quality_indicators.get('creates_nonroot_user'):
            recommendations.append("Create and use non-root user for container execution")

        if not quality_indicators.get('has_health_checks'):
            recommendations.append("Add HEALTHCHECK instruction for container monitoring")

        if not quality_indicators.get('uses_multistage'):
            recommendations.append("Consider multi-stage builds to reduce final image size")

        return recommendations

    def _generate_dependency_recommendations(self, quality_indicators: Dict[str, bool]) -> List[str]:
        """Generate dependency security recommendations."""
        recommendations = []

        if not quality_indicators.get('specifies_exact_version'):
            recommendations.append("Pin to exact versions for security patches")

        if not quality_indicators.get('uses_override'):
            recommendations.append("Use dependency overrides to force secure versions")

        if not quality_indicators.get('includes_audit'):
            recommendations.append("Add security audit automation to CI/CD pipeline")

        if not quality_indicators.get('suggests_alternatives'):
            recommendations.append("Consider alternative packages if current one is unmaintained")

        return recommendations

    def _generate_web_security_recommendations(self, quality_indicators: Dict[str, bool]) -> List[str]:
        """Generate web security recommendations."""
        recommendations = []

        if not quality_indicators.get('explicit_origins'):
            recommendations.append("Use explicit origin whitelist instead of wildcards")

        if not quality_indicators.get('no_wildcard'):
            recommendations.append("Avoid wildcard (*) in CORS configurations")

        if not quality_indicators.get('strict_csp'):
            recommendations.append("Implement strict Content Security Policy with nonces")

        if not quality_indicators.get('proper_session'):
            recommendations.append("Use secure session configuration with proper flags")

        return recommendations
```

### Phase 4: Integration & Configuration (Week 4)

#### **4.1 Command Line Interface Integration**

**File**: `process_artifacts.py` - Add multi-domain command line arguments

```python
def main():
    """Main entry point with multi-domain security enhancement support."""

    # Initialize configuration for default model path
    config = OLMoSecurityConfig()

    # Get default model path from configuration, with fallback
    try:
        default_model = str(config.get_base_model_path())
    except FileNotFoundError:
        default_model = None
        print(f"⚠️  Default model not found at {config.base_models_dir}/{config.default_base_model}")
        print("🔄 Will use fallback mode if no model specified")

    parser = argparse.ArgumentParser(
        description="Process security artifacts with OLMo analysis - Enhanced Multi-Domain Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Existing arguments (unchanged)
    parser.add_argument("--artifacts-dir", type=Path, default="data/security_artifacts",
                       help="Directory for security artifacts (default: data/security_artifacts)")
    parser.add_argument("--output-dir", type=Path, default="results",
                       help="Output directory for analysis results (default: results)")
    parser.add_argument("--model-name", type=str, default=default_model,
                       help="OLMo-2-1B model to use for analysis (defaults to configured model)")

    # NEW: Multi-domain enhancement arguments
    multi_domain_group = parser.add_argument_group('Multi-Domain Security Enhancement')
    multi_domain_group.add_argument("--enable-multi-domain", action="store_true",
                                   help="Enable multi-domain security specialization")
    multi_domain_group.add_argument("--target-categories", type=str,
                                   help="Comma-separated list of security categories to focus on. "
                                        "Options: container_security, dependency_vulnerabilities, "
                                        "web_security, code_vulnerabilities, webauthn_security, "
                                        "mobile_security, infrastructure_security")
    multi_domain_group.add_argument("--category-weights", type=str,
                                   help="JSON string of category weights for training balance "
                                        "(e.g., '{\"web_security\": 1.5, \"container_security\": 1.2}')")
    multi_domain_group.add_argument("--multi-domain-config", type=Path,
                                   help="Path to multi-domain configuration YAML file")

    # Existing arguments continue...
    args = parser.parse_args()

    # Parse multi-domain arguments
    if args.enable_multi_domain:
        print("🌐 Multi-domain security specialization enabled")

        # Parse target categories
        if args.target_categories:
            target_categories = [cat.strip() for cat in args.target_categories.split(',')]
            print(f"🎯 Target categories: {target_categories}")
        else:
            target_categories = None
            print("📊 Processing all detected categories")

        # Parse category weights
        category_weights = {}
        if args.category_weights:
            try:
                category_weights = json.loads(args.category_weights)
                print(f"⚖️ Category weights: {category_weights}")
            except json.JSONDecodeError as e:
                print(f"⚠️ Invalid category weights JSON: {e}")
                category_weights = {}

        # Store multi-domain settings in args for later use
        args.multi_domain_enabled = True
        args.parsed_target_categories = target_categories
        args.parsed_category_weights = category_weights
    else:
        args.multi_domain_enabled = False
        args.parsed_target_categories = None
        args.parsed_category_weights = {}

    # Continue with existing main logic...
```

#### **4.2 Integration with Datasets Phase**

**File**: `process_artifacts.py` - Update datasets_phase function

```python
def datasets_phase(narrativized_file: Path, vulnerabilities_file: Path, output_dir: str, args) -> Tuple[List, Path, Path]:
    """
    Phase 4: Prepare training and validation datasets with enhanced code-aware examples
    Enhanced with multi-domain specialization capability.
    """
    output_path = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"🔄 Loading narrativized results: {narrativized_file}")
    with open(narrativized_file, 'r') as f:
        narrativized_results = json.load(f)

    print(f"📚 Preparing fine-tuning dataset from {len(narrativized_results)} narratives...")

    # **Standard Training Pairs (Original - unchanged)**
    training_pairs = []

    for item in narrativized_results:
        # Create training pair
        vulnerability_info = f"Vulnerability ID: {item['vulnerability_id']}"

        training_pair = {
            'instruction': f"Analyze this security vulnerability and provide remediation guidance:\\n\\n{vulnerability_info}",
            'response': item['narrative'],
            'metadata': {
                'vulnerability_id': item['vulnerability_id'],
                'created_at': timestamp
            }
        }

        training_pairs.append(training_pair)

    # **Enhanced Training Pairs (Code-Aware with Multi-Domain)**
    print(f"🚀 Creating enhanced code-aware training dataset...")
    try:
        from enhanced_dataset_creator import EnhancedDatasetCreator, EnumJSONEncoder

        # Load raw vulnerability data for enhanced dataset creator
        print(f"🔄 Loading raw vulnerability data: {vulnerabilities_file}")
        with open(vulnerabilities_file, 'r') as f:
            raw_vulnerability_data = json.load(f)

        # Extract successful vulnerability objects for enhancement
        raw_vulnerabilities = []
        for item in raw_vulnerability_data:
            if item.get('status') == 'success' and 'vulnerability' in item:
                raw_vulnerabilities.append(item['vulnerability'])

        print(f"📊 Loaded {len(raw_vulnerabilities)} raw vulnerabilities for enhancement")

        # Get dataset name for enhanced creation
        dataset_name = f"webauthn-security-vulnerabilities-{timestamp}"

        # NEW: Initialize enhanced dataset creator with multi-domain support
        creator = EnhancedDatasetCreator(
            enable_multi_domain=getattr(args, 'multi_domain_enabled', False)
        )

        # NEW: Pass multi-domain parameters if enabled
        if getattr(args, 'multi_domain_enabled', False):
            print("🌐 Multi-domain enhanced dataset creation enabled")
            enhanced_result = creator.create_enhanced_dataset(
                raw_vulnerabilities,
                dataset_name=dataset_name,
                target_categories=getattr(args, 'parsed_target_categories', None)
            )
        else:
            # Use standard enhanced dataset creation
            enhanced_result = creator.create_enhanced_dataset(
                raw_vulnerabilities,
                dataset_name=dataset_name
            )

        if enhanced_result.success:
            print(f"✅ Enhanced dataset creation successful!")

            # NEW: Log multi-domain statistics if available
            if enhanced_result.creation_metadata.get('multi_domain'):
                print(f"🌐 Multi-domain enhancement statistics:")
                category_breakdown = enhanced_result.creation_metadata.get('category_breakdown', {})
                for category, stats in category_breakdown.items():
                    print(f"   📦 {category}: {stats['vulnerability_count']} vulns → "
                          f"{stats['enhanced_examples_count']} examples "
                          f"({stats['enhancement_ratio']:.1f}x)")
            else:
                print(f"  📊 Original examples: {enhanced_result.creation_metadata.get('original_count', 0)}")
                print(f"  🚀 Enhanced examples: {enhanced_result.creation_metadata.get('enhanced_count', 0)}")
                print(f"  🎯 Enhancement ratio: {enhanced_result.creation_metadata.get('enhancement_ratio', 0):.1f}x")

            # Convert enhanced examples to training pairs format (unchanged)
            enhanced_training_pairs = []
            for example in enhanced_result.enhanced_examples:
                enhanced_training_pairs.append({
                    'instruction': example.instruction,
                    'response': example.response,
                    'metadata': example.metadata
                })

            # Combine with standard training pairs for comprehensive dataset
            combined_training_pairs = training_pairs + enhanced_training_pairs
            print(f"🔗 Combined dataset: {len(training_pairs)} standard + {len(enhanced_training_pairs)} enhanced = {len(combined_training_pairs)} total")

            # Use combined dataset for training
            training_pairs = combined_training_pairs

        else:
            print(f"⚠️ Enhanced dataset creation failed: {enhanced_result.error_message}")

    except ImportError as e:
        print(f"⚠️ Enhanced dataset creator not available: {e}")
        print(f"   Continuing with standard narrativized dataset only...")

    # Continue with existing logic (unchanged)...
```

#### **4.3 Configuration Management Integration**

**File**: `config_manager.py` - Add multi-domain configuration support

```python
@dataclass
class MultiDomainSection:
    """Multi-domain security specialization configuration."""
    enabled: bool = False
    target_categories: List[str] = field(default_factory=list)
    category_weights: Dict[str, float] = field(default_factory=dict)
    enhancement_ratios: Dict[str, float] = field(default_factory=dict)
    validation_thresholds: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Set default values for multi-domain configuration."""
        if not self.target_categories:
            self.target_categories = [
                'container_security', 'dependency_vulnerabilities', 'web_security',
                'code_vulnerabilities', 'webauthn_security', 'mobile_security',
                'infrastructure_security'
            ]

        if not self.category_weights:
            self.category_weights = {
                'webauthn_security': 1.0,     # Maintain existing strength
                'container_security': 1.2,    # High priority
                'web_security': 1.2,         # High priority
                'code_vulnerabilities': 1.1,  # Medium-high priority
                'dependency_vulnerabilities': 1.0,  # Standard priority
                'mobile_security': 0.9,      # Medium priority
                'infrastructure_security': 0.8  # Lower priority
            }

        if not self.enhancement_ratios:
            self.enhancement_ratios = {
                'webauthn_security': 3.0,     # Keep existing high enhancement
                'container_security': 4.0,    # High enhancement needed
                'web_security': 3.5,         # High enhancement needed
                'code_vulnerabilities': 3.0,  # Standard enhancement
                'dependency_vulnerabilities': 2.5,  # Medium enhancement
                'mobile_security': 2.0,      # Lower enhancement
                'infrastructure_security': 2.0  # Lower enhancement
            }

        if not self.validation_thresholds:
            self.validation_thresholds = {
                'webauthn_security': 0.8,     # High standard (existing)
                'container_security': 0.75,   # High standard
                'web_security': 0.75,        # High standard
                'code_vulnerabilities': 0.7,  # Medium-high standard
                'dependency_vulnerabilities': 0.65,  # Medium standard
                'mobile_security': 0.6,      # Medium standard
                'infrastructure_security': 0.6  # Medium standard
            }

class OLMoSecurityConfig:
    """Enhanced configuration with multi-domain support."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration with optional multi-domain support."""

        # Existing initialization (unchanged)
        if config_file is None:
            config_file = str(Path(__file__).parent / "config" / "olmo_security_config.yaml")

        self.config_file = Path(config_file)
        self.project_root = self._find_project_root()

        # Load configuration
        with open(self.config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        # Initialize sections (existing - unchanged)
        self.base_models_dir = self._resolve_path(config_data['base_models_dir'])
        self.fine_tuned_models_dir = self._resolve_path(
            os.getenv('OLMO_FINE_TUNED_MODELS_DIR', config_data['fine_tuned_models_dir'])
        )
        self.venv_dir = self._resolve_path(config_data['venv_dir'])
        self.data_dir = self._resolve_path(config_data['data_dir'])
        self.results_dir = self._resolve_path(config_data['results_dir'])
        self.default_base_model = os.getenv('OLMO_DEFAULT_BASE_MODEL', config_data['default_base_model'])

        # Load sections
        self.fine_tuning = self._load_fine_tuning_section(config_data, self.project_root)
        self.validation = self._load_validation_section(config_data)

        # NEW: Load multi-domain section
        self.multi_domain = self._load_multi_domain_section(config_data)

    def _load_multi_domain_section(self, config: Dict[str, Any]) -> MultiDomainSection:
        """Load multi-domain configuration section with environment variable overrides."""
        md_config = config.get('multi_domain', {})

        return MultiDomainSection(
            enabled=os.getenv('OLMO_MULTI_DOMAIN_ENABLED', str(md_config.get('enabled', False))).lower() == 'true',
            target_categories=self._parse_env_list('OLMO_TARGET_CATEGORIES', md_config.get('target_categories', [])),
            category_weights=self._parse_env_dict('OLMO_CATEGORY_WEIGHTS', md_config.get('category_weights', {})),
            enhancement_ratios=self._parse_env_dict('OLMO_ENHANCEMENT_RATIOS', md_config.get('enhancement_ratios', {})),
            validation_thresholds=self._parse_env_dict('OLMO_VALIDATION_THRESHOLDS', md_config.get('validation_thresholds', {}))
        )

    def _parse_env_list(self, env_var: str, default: List[str]) -> List[str]:
        """Parse environment variable as comma-separated list."""
        env_value = os.getenv(env_var)
        if env_value:
            return [item.strip() for item in env_value.split(',')]
        return default

    def _parse_env_dict(self, env_var: str, default: Dict[str, float]) -> Dict[str, float]:
        """Parse environment variable as JSON dictionary."""
        env_value = os.getenv(env_var)
        if env_value:
            try:
                return json.loads(env_value)
            except json.JSONDecodeError:
                logging.warning(f"Invalid JSON in {env_var}, using default")
        return default
```

#### **4.4 Configuration File Template**

**File**: `config/olmo_security_config.yaml` - Add multi-domain section

```yaml
# OLMo Security Configuration with Multi-Domain Enhancement Support
# Enhanced configuration for multi-domain security specialization

# Base configuration (unchanged)
base_models_dir: "~/shared-olmo-models/base"
fine_tuned_models_dir: "~/shared-olmo-models/fine-tuned"
venv_dir: "./venv"
data_dir: "./data"
results_dir: "./results"
default_base_model: "OLMo-2-1B-mlx-q4"

# Fine-tuning configuration (existing, unchanged)
fine_tuning:
  workspace_dir: "./fine-tuning"
  training:
    max_epochs: 1
    batch_size: 4
    learning_rate: 1e-4
    save_steps: 100
    eval_steps: 50
    max_stage1_iters: 0  # 0 = use calculated value
    max_stage2_iters: 0  # 0 = use calculated value
  upload:
    enabled: true
    private_repos: false
    default_repo_prefix: "hitoshura25"
    default_output_name: "webauthn-security-model"

# Validation configuration (existing, unchanged)
validation:
  stage1_threshold: 0.7
  stage2_threshold: 0.7
  sequential_threshold: 0.6

# NEW: Multi-domain security specialization configuration
multi_domain:
  # Enable multi-domain specialization
  enabled: false  # Set to true to enable multi-domain features

  # Target security categories to focus on
  # Leave empty to process all detected categories
  target_categories:
    - container_security
    - dependency_vulnerabilities
    - web_security
    - code_vulnerabilities
    - webauthn_security
    - mobile_security
    - infrastructure_security

  # Category-specific weights for training data balance
  # Higher weights = more training examples generated for that category
  category_weights:
    webauthn_security: 1.0      # Maintain existing strength
    container_security: 1.2     # High priority - Docker/container security
    web_security: 1.2          # High priority - CORS, CSP, web app security
    code_vulnerabilities: 1.1   # Medium-high priority - code security patterns
    dependency_vulnerabilities: 1.0  # Standard priority - package security
    mobile_security: 0.9       # Medium priority - Android security
    infrastructure_security: 0.8    # Lower priority - IaC, secrets management

  # Enhancement ratios per category (examples generated per vulnerability)
  enhancement_ratios:
    webauthn_security: 3.0      # Keep existing high enhancement
    container_security: 4.0     # High enhancement - need more Docker expertise
    web_security: 3.5          # High enhancement - need more web security patterns
    code_vulnerabilities: 3.0   # Standard enhancement
    dependency_vulnerabilities: 2.5  # Medium enhancement
    mobile_security: 2.0       # Lower enhancement
    infrastructure_security: 2.0    # Lower enhancement

  # Validation thresholds per category for quality assessment
  validation_thresholds:
    webauthn_security: 0.8      # High standard (existing)
    container_security: 0.75    # High standard - Docker security is critical
    web_security: 0.75         # High standard - web security is critical
    code_vulnerabilities: 0.7   # Medium-high standard
    dependency_vulnerabilities: 0.65  # Medium standard
    mobile_security: 0.6       # Medium standard
    infrastructure_security: 0.6    # Medium standard

  # Advanced multi-domain settings
  advanced:
    # Enable cross-domain knowledge transfer
    enable_cross_domain_transfer: true

    # Category-specific prompt variations
    enable_category_prompts: true

    # Framework-aware fix generation
    enable_framework_awareness: true

    # Multi-stage training configuration
    multi_stage_training:
      enabled: false  # Experimental: 3-stage training instead of 2-stage
      stages:
        stage1_analysis:
          focus: "Multi-domain vulnerability analysis"
          target_score: 0.75
        stage2_generic_fixes:
          focus: "General secure coding patterns"
          target_score: 0.70
        stage3_specialized_fixes:
          focus: "Category-specific advanced patterns"
          target_score: 0.80

# Environment variable overrides:
# OLMO_MULTI_DOMAIN_ENABLED=true
# OLMO_TARGET_CATEGORIES="container_security,web_security,code_vulnerabilities"
# OLMO_CATEGORY_WEIGHTS='{"web_security": 1.5, "container_security": 1.3}'
# OLMO_ENHANCEMENT_RATIOS='{"container_security": 5.0, "web_security": 4.0}'
# OLMO_VALIDATION_THRESHOLDS='{"container_security": 0.8, "web_security": 0.8}'
```

## Testing Strategy

### **Unit Tests**

**File**: `tests/test_multi_domain_integration.py`

```python
#!/usr/bin/env python3
"""
Integration tests for multi-domain security specialization.
"""

import pytest
import json
import tempfile
from pathlib import Path
from enhanced_dataset_creator import EnhancedDatasetCreator, VulnerabilityCategorizor
from multi_domain_validator import MultiDomainValidator
from config_manager import OLMoSecurityConfig

class TestMultiDomainIntegration:
    """Integration tests for multi-domain functionality."""

    @pytest.fixture
    def sample_multi_domain_vulnerabilities(self):
        """Sample vulnerabilities across multiple domains."""
        return [
            # Container security
            {
                'id': 'container-001',
                'tool': 'trivy',
                'description': 'Alpine base image vulnerability in Dockerfile',
                'file_path': 'Dockerfile',
                'severity': 'HIGH'
            },
            # Web security
            {
                'id': 'web-001',
                'tool': 'zap',
                'alert': 'CORS Misconfiguration',
                'uri': 'http://localhost:8080',
                'description': 'CORS policy allows malicious origins'
            },
            # Code vulnerability
            {
                'id': 'code-001',
                'tool': 'semgrep',
                'check_id': 'detect-child-process',
                'description': 'Command injection vulnerability',
                'file_path': 'scripts/build.js'
            },
            # WebAuthn security
            {
                'id': 'webauthn-001',
                'tool': 'semgrep',
                'check_id': 'webauthn-credential-validation-bypass',
                'description': 'WebAuthn credential validation bypass',
                'file_path': 'auth/webauthn.kt'
            }
        ]

    @pytest.fixture
    def temp_output_dir(self):
        """Temporary output directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_multi_domain_categorization(self, sample_multi_domain_vulnerabilities):
        """Test vulnerability categorization across domains."""
        categorizer = VulnerabilityCategorizor()
        categorized = categorizer.categorize_vulnerabilities(sample_multi_domain_vulnerabilities)

        # Verify categories are correctly detected
        assert 'container_security' in categorized
        assert 'web_security' in categorized
        assert 'code_vulnerabilities' in categorized
        assert 'webauthn_security' in categorized

        # Verify vulnerability counts
        assert len(categorized['container_security']) == 1
        assert len(categorized['web_security']) == 1
        assert len(categorized['code_vulnerabilities']) == 1
        assert len(categorized['webauthn_security']) == 1

        # Verify metadata addition
        for category_vulns in categorized.values():
            for vuln in category_vulns:
                assert 'detected_category' in vuln

    def test_multi_domain_dataset_creation(self, sample_multi_domain_vulnerabilities, temp_output_dir):
        """Test multi-domain enhanced dataset creation."""
        creator = EnhancedDatasetCreator(
            output_dir=temp_output_dir,
            enable_multi_domain=True
        )

        result = creator.create_enhanced_dataset(
            sample_multi_domain_vulnerabilities,
            dataset_name="test-multi-domain",
            target_categories=['container_security', 'web_security', 'webauthn_security']
        )

        assert result.success
        assert result.creation_metadata['multi_domain']
        assert len(result.enhanced_examples) > len(sample_multi_domain_vulnerabilities)

        # Verify category breakdown
        category_breakdown = result.creation_metadata['category_breakdown']
        assert 'container_security' in category_breakdown
        assert 'web_security' in category_breakdown
        assert 'webauthn_security' in category_breakdown

    def test_multi_domain_validation(self, sample_multi_domain_vulnerabilities):
        """Test multi-domain validation functionality."""
        validator = MultiDomainValidator()

        # Test container security validation
        container_vuln = next(v for v in sample_multi_domain_vulnerabilities if v['tool'] == 'trivy')
        container_response = """
        FROM node:18.17.1-alpine AS base
        RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
        USER nodejs
        HEALTHCHECK --interval=30s CMD curl -f http://localhost:3000/ || exit 1
        """

        container_result = validator.validate_category_specific_fix(
            'container_security', container_vuln, container_response
        )

        assert container_result.category_score > 0.5
        assert 'base_image_security' in container_result.patterns_detected
        assert container_result.specialization_level in ['medium', 'high']

        # Test web security validation
        web_vuln = next(v for v in sample_multi_domain_vulnerabilities if v['tool'] == 'zap')
        web_response = """
        install(CORS) {
            allowHost("localhost:3000")
            allowHost("https://yourdomain.com")
            allowCredentials = true
            allowMethod(HttpMethod.Get)
            allowMethod(HttpMethod.Post)
        }
        """

        web_result = validator.validate_category_specific_fix(
            'web_security', web_vuln, web_response
        )

        assert web_result.category_score > 0.5
        assert 'cors_security' in web_result.patterns_detected

    def test_configuration_integration(self):
        """Test multi-domain configuration loading."""
        # Test with default configuration
        config = OLMoSecurityConfig()

        # Verify multi-domain section exists
        assert hasattr(config, 'multi_domain')
        assert hasattr(config.multi_domain, 'enabled')
        assert hasattr(config.multi_domain, 'target_categories')
        assert hasattr(config.multi_domain, 'category_weights')

        # Verify default values
        assert isinstance(config.multi_domain.target_categories, list)
        assert isinstance(config.multi_domain.category_weights, dict)
        assert 'webauthn_security' in config.multi_domain.category_weights

    def test_backward_compatibility(self, sample_multi_domain_vulnerabilities, temp_output_dir):
        """Test that multi-domain features don't break existing functionality."""
        # Test with multi-domain disabled
        creator = EnhancedDatasetCreator(
            output_dir=temp_output_dir,
            enable_multi_domain=False
        )

        result = creator.create_enhanced_dataset(
            sample_multi_domain_vulnerabilities,
            dataset_name="test-backward-compatibility"
        )

        assert result.success
        assert not result.creation_metadata.get('multi_domain', False)
        assert len(result.enhanced_examples) > 0

        # Verify existing functionality still works
        for example in result.enhanced_examples:
            assert hasattr(example, 'instruction')
            assert hasattr(example, 'response')
            assert hasattr(example, 'metadata')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### **End-to-End Testing**

**File**: `tests/test_multi_domain_e2e.py`

```python
#!/usr/bin/env python3
"""
End-to-end tests for multi-domain security specialization.
"""

import pytest
import subprocess
import tempfile
import json
from pathlib import Path

class TestMultiDomainE2E:
    """End-to-end tests for complete multi-domain workflow."""

    @pytest.fixture
    def test_artifacts_dir(self):
        """Use existing test artifacts directory."""
        return Path(__file__).parent.parent / "tests" / "fixtures" / "sample_security_artifacts"

    @pytest.fixture
    def temp_output_dir(self):
        """Temporary output directory for E2E testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_multi_domain_datasets_phase(self, test_artifacts_dir, temp_output_dir):
        """Test multi-domain datasets phase integration."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(test_artifacts_dir),
            "--output-dir", str(temp_output_dir),
            "--only-datasets",
            "--enable-multi-domain",
            "--target-categories", "container_security,web_security,code_vulnerabilities"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        assert result.returncode == 0
        assert "Multi-domain security specialization enabled" in result.stdout
        assert "Target categories:" in result.stdout
        assert "Multi-domain enhancement statistics:" in result.stdout or "Enhanced dataset creation successful!" in result.stdout

    def test_multi_domain_full_pipeline(self, test_artifacts_dir, temp_output_dir):
        """Test complete multi-domain pipeline (without actual training)."""
        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(test_artifacts_dir),
            "--output-dir", str(temp_output_dir),
            "--stop-after", "datasets",
            "--enable-multi-domain",
            "--target-categories", "web_security,code_vulnerabilities",
            "--category-weights", '{"web_security": 1.5, "code_vulnerabilities": 1.2}'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        assert result.returncode == 0
        assert "All 4 phases completed successfully" in result.stdout  # parsing, analysis, narrativization, datasets
        assert "Category weights:" in result.stdout

    def test_multi_domain_configuration_override(self, test_artifacts_dir, temp_output_dir):
        """Test multi-domain with environment variable overrides."""
        env = {
            "OLMO_MULTI_DOMAIN_ENABLED": "true",
            "OLMO_TARGET_CATEGORIES": "container_security,dependency_vulnerabilities",
            "OLMO_CATEGORY_WEIGHTS": '{"container_security": 2.0}'
        }

        cmd = [
            "python", "process_artifacts.py",
            "--artifacts-dir", str(test_artifacts_dir),
            "--output-dir", str(temp_output_dir),
            "--only-datasets"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=Path(__file__).parent.parent)

        assert result.returncode == 0
        assert "Multi-domain security specialization enabled" in result.stdout

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

## Usage Examples

### **Basic Multi-Domain Usage**

```bash
# Enable multi-domain for all categories
python process_artifacts.py \
  --artifacts-dir data/security_artifacts \
  --enable-multi-domain

# Focus on specific categories
python process_artifacts.py \
  --artifacts-dir data/security_artifacts \
  --enable-multi-domain \
  --target-categories "container_security,web_security,code_vulnerabilities"

# Custom category weights
python process_artifacts.py \
  --artifacts-dir data/security_artifacts \
  --enable-multi-domain \
  --category-weights '{"web_security": 1.5, "container_security": 1.3, "code_vulnerabilities": 1.1}'
```

### **Environment Variable Configuration**

```bash
# Set environment variables for multi-domain
export OLMO_MULTI_DOMAIN_ENABLED=true
export OLMO_TARGET_CATEGORIES="container_security,web_security"
export OLMO_CATEGORY_WEIGHTS='{"container_security": 1.5, "web_security": 1.2}'

# Run with environment configuration
python process_artifacts.py --artifacts-dir data/security_artifacts
```

### **Development and Testing**

```bash
# Test datasets phase only with multi-domain
python process_artifacts.py \
  --artifacts-dir data/security_artifacts \
  --only-datasets \
  --enable-multi-domain \
  --target-categories "web_security"

# Run validation tests
python -m pytest tests/test_multi_domain_integration.py -v

# Run end-to-end tests
python -m pytest tests/test_multi_domain_e2e.py -v
```

## Expected Outcomes & Success Metrics

### **Quantitative Improvements**

1. **Stage 2 Specialization Score**
   - Current: 0.62 (medium specialization)
   - Target: 0.75+ (high specialization)
   - Measurement: Sequential fine-tuner validation

2. **Quality Pass Rate**
   - Current: 67% fixes pass quality assessment
   - Target: 85% fixes pass quality assessment
   - Measurement: Fix quality assessor results

3. **Domain Coverage**
   - Current: 1 domain (WebAuthn) with high quality
   - Target: 7 domains with medium-high quality
   - Measurement: Category-specific validation scores

4. **Training Data Enhancement**
   - Current: 1,052 enhanced examples (mostly WebAuthn)
   - Target: 3,500+ enhanced examples across domains
   - Measurement: Dataset creation statistics

### **Qualitative Improvements**

1. **Fix Applicability**
   - Framework-specific implementations (KTor, Docker, npm)
   - Copy-paste ready code examples
   - Production-ready security configurations

2. **Security Pattern Recognition**
   - Container hardening patterns
   - CORS/CSP security configurations
   - Dependency management strategies
   - Input validation techniques

3. **Developer Experience**
   - Actionable remediation guidance
   - Reduced research time (hours → minutes)
   - Higher implementation success rate

### **Success Validation**

1. **Automated Testing**
   - Unit tests for categorization accuracy (>95%)
   - Integration tests for dataset creation
   - End-to-end pipeline validation

2. **Manual Quality Assessment**
   - Security expert review of generated fixes
   - Developer usability testing
   - Real-world implementation validation

3. **Performance Benchmarking**
   - Training time impact assessment
   - Model size and inference speed
   - Resource utilization analysis

## Migration & Rollout Strategy

### **Phase 1: Gradual Feature Introduction (Week 1)**
- Deploy categorization and validation components
- Enable multi-domain via feature flag
- Test with limited vulnerability set

### **Phase 2: Enhanced Dataset Testing (Week 2)**
- Generate multi-domain training datasets
- Validate enhanced example quality
- Compare against baseline datasets

### **Phase 3: Training Integration (Week 3)**
- Integrate with sequential fine-tuner
- Test category-aware validation
- Benchmark against existing models

### **Phase 4: Production Deployment (Week 4)**
- Full feature activation
- Performance monitoring
- User feedback collection and analysis

This comprehensive implementation plan provides all necessary details for implementing multi-domain security specialization while maintaining backward compatibility and ensuring robust testing coverage.