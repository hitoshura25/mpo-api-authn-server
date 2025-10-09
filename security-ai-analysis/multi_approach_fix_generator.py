#!/usr/bin/env python3
"""
Multi-Approach Fix Generator for AI Security Enhancement

This module generates multiple fix approaches for security vulnerabilities
to create diverse training data for the enhanced AI model.

Classes:
- FixApproach: Enumeration of different fix strategies
- SecurityFix: Data class representing a generated security fix
- MultiApproachFixGenerator: Main class for generating varied security fixes
- FixGenerationResult: Result of fix generation with metadata

Usage:
    generator = MultiApproachFixGenerator()
    fixes = generator.generate_fixes(vulnerability, code_context)
"""

import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass, field

from vulnerable_code_extractor import CodeContext, VulnerableCodeExtractor


class FixApproach(Enum):
    """Different approaches for fixing security vulnerabilities."""
    
    # Basic approaches
    INPUT_VALIDATION = "input_validation"
    OUTPUT_SANITIZATION = "output_sanitization"
    ERROR_HANDLING = "error_handling"
    ACCESS_CONTROL = "access_control"
    
    # Architectural approaches
    IN_MEMORY_SOLUTION = "in_memory_solution"
    DATABASE_SOLUTION = "database_solution"
    CACHE_SOLUTION = "cache_solution"
    MICROSERVICE_SOLUTION = "microservice_solution"
    
    # Framework-specific approaches
    FRAMEWORK_SECURITY = "framework_security"
    LIBRARY_REPLACEMENT = "library_replacement"
    CONFIGURATION_CHANGE = "configuration_change"
    
    # Advanced approaches
    DEFENSIVE_PROGRAMMING = "defensive_programming"
    FAIL_SAFE_DESIGN = "fail_safe_design"
    PRINCIPLE_OF_LEAST_PRIVILEGE = "principle_of_least_privilege"


@dataclass
class SecurityFix:
    """
    Represents a generated security fix with code examples.
    """
    approach: FixApproach
    title: str
    description: str
    
    # Code examples
    vulnerable_code: str
    fixed_code: str
    
    # Additional context
    explanation: str
    benefits: List[str] = field(default_factory=list)
    trade_offs: List[str] = field(default_factory=list)
    implementation_notes: List[str] = field(default_factory=list)
    
    # Metadata
    language: Optional[str] = None
    framework: Optional[str] = None
    complexity_level: str = "medium"  # low, medium, high
    security_impact: str = "medium"   # low, medium, high, critical


@dataclass
class FixGenerationResult:
    """
    Result of security fix generation.
    """
    success: bool
    fixes: List[SecurityFix] = field(default_factory=list)
    error_message: Optional[str] = None
    generation_metadata: Dict[str, Any] = field(default_factory=dict)


class MultiApproachFixGenerator:
    """
    Generates multiple security fix approaches for vulnerabilities.
    
    This class analyzes vulnerability context and generates diverse
    fix strategies with specific code examples for training data.
    """
    
    def __init__(self):
        """Initialize the fix generator."""
        import logging
        self.logger = logging.getLogger(__name__)

        # Common vulnerability patterns and their fix strategies
        self.vulnerability_patterns = {
            'sql_injection': [
                FixApproach.INPUT_VALIDATION,
                FixApproach.DATABASE_SOLUTION,
                FixApproach.FRAMEWORK_SECURITY
            ],
            'xss': [
                FixApproach.INPUT_VALIDATION,
                FixApproach.OUTPUT_SANITIZATION,
                FixApproach.FRAMEWORK_SECURITY
            ],
            'command_injection': [
                FixApproach.INPUT_VALIDATION,
                FixApproach.LIBRARY_REPLACEMENT,
                FixApproach.DEFENSIVE_PROGRAMMING
            ],
            'authentication_bypass': [
                FixApproach.ACCESS_CONTROL,
                FixApproach.FRAMEWORK_SECURITY,
                FixApproach.PRINCIPLE_OF_LEAST_PRIVILEGE
            ],
            'information_disclosure': [
                FixApproach.ERROR_HANDLING,
                FixApproach.ACCESS_CONTROL,
                FixApproach.CONFIGURATION_CHANGE
            ],
            'insecure_configuration': [
                FixApproach.CONFIGURATION_CHANGE,
                FixApproach.FRAMEWORK_SECURITY,
                FixApproach.FAIL_SAFE_DESIGN
            ]
        }
        
        # Language-specific fix templates
        self.language_templates = {
            'python': self._get_python_templates(),
            'kotlin': self._get_kotlin_templates(),
            'java': self._get_java_templates(),
            'javascript': self._get_javascript_templates(),
            'typescript': self._get_typescript_templates()
        }
    
    def generate_fixes(self, vulnerability: Dict[str, Any],
                      code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        Generate multiple fix approaches for a vulnerability.

        Universal fix generation - delegates to tool-specific methods when available.

        Args:
            vulnerability: Vulnerability data from security tools
            code_context: Extracted code context around vulnerability (None for infrastructure vulnerabilities)

        Returns:
            FixGenerationResult with generated fixes
        """
        try:
            # Check for tool-specific fix generation
            tool = vulnerability.get('tool', '').lower()

            # Delegate to tool-specific methods
            if 'osv' in tool:
                return self._generate_osv_fix(vulnerability, code_context)
            elif 'trivy' in tool:
                return self._generate_trivy_fix(vulnerability, code_context)
            elif 'semgrep' in tool:
                return self._generate_semgrep_fix(vulnerability, code_context)
            elif 'zap' in tool:
                return self._generate_zap_fix(vulnerability, code_context)
            elif 'checkov' in tool:
                return self._generate_checkov_fix(vulnerability, code_context)

            # Fall back to generic multi-approach generation
            # Analyze vulnerability type
            vuln_type = self._classify_vulnerability(vulnerability)

            # Get applicable fix approaches
            approaches = self._get_fix_approaches(vuln_type, code_context)

            # Generate fixes for each approach
            fixes = []
            for approach in approaches:
                fix = self._generate_fix_for_approach(
                    approach, vulnerability, code_context, vuln_type
                )
                if fix:
                    fixes.append(fix)

            return FixGenerationResult(
                success=True,
                fixes=fixes,
                generation_metadata={
                    'vulnerability_type': vuln_type,
                    'approaches_attempted': len(approaches),
                    'fixes_generated': len(fixes),
                    'language': code_context.language if code_context else 'infrastructure',
                    'function_context': code_context.function_name is not None if code_context else False,
                    'class_context': code_context.class_name is not None if code_context else False,
                    'infrastructure_vulnerability': code_context is None
                }
            )

        except Exception as e:
            self.logger.error(f"Fix generation failed: {e}")
            raise
    
    def _classify_vulnerability(self, vulnerability: Dict[str, Any]) -> str:
        """Classify vulnerability type from vulnerability data."""
        check_id = vulnerability.get('check_id', '').lower()
        message = vulnerability.get('extra', {}).get('message', '').lower()
        
        # Check for common vulnerability patterns
        if any(term in check_id or term in message for term in ['sql', 'injection', 'query']):
            return 'sql_injection'
        
        if any(term in check_id or term in message for term in ['xss', 'cross-site', 'script']):
            return 'xss'
        
        if any(term in check_id or term in message for term in ['command', 'exec', 'shell']):
            return 'command_injection'
        
        if any(term in check_id or term in message for term in ['auth', 'credential', 'bypass']):
            return 'authentication_bypass'
        
        if any(term in check_id or term in message for term in ['disclosure', 'leak', 'expose']):
            return 'information_disclosure'
        
        if any(term in check_id or term in message for term in ['config', 'setting', 'default']):
            return 'insecure_configuration'
        
        return 'generic_security_issue'
    
    def _get_fix_approaches(self, vuln_type: str, code_context: Optional[CodeContext]) -> List[FixApproach]:
        """Get applicable fix approaches for vulnerability type."""
        # For infrastructure vulnerabilities (no code context), use infrastructure-specific approaches
        if code_context is None:
            return [
                FixApproach.CONFIGURATION_CHANGE,
                FixApproach.ACCESS_CONTROL,
                FixApproach.FRAMEWORK_SECURITY,
                FixApproach.LIBRARY_REPLACEMENT
            ]
        
        # Get base approaches for vulnerability type
        base_approaches = self.vulnerability_patterns.get(vuln_type, [
            FixApproach.INPUT_VALIDATION,
            FixApproach.ERROR_HANDLING,
            FixApproach.DEFENSIVE_PROGRAMMING
        ])
        
        # Add architectural approaches based on context
        architectural_approaches = []
        
        # Add context-specific approaches
        if code_context.function_name:
            architectural_approaches.extend([
                FixApproach.IN_MEMORY_SOLUTION,
                FixApproach.CACHE_SOLUTION
            ])
        
        if code_context.class_name:
            architectural_approaches.extend([
                FixApproach.DATABASE_SOLUTION,
                FixApproach.MICROSERVICE_SOLUTION
            ])
        
        # Combine and limit to 4-5 approaches for diversity
        all_approaches = base_approaches + architectural_approaches
        return all_approaches[:5]
    
    def _generate_fix_for_approach(self, approach: FixApproach, 
                                 vulnerability: Dict[str, Any],
                                 code_context: Optional[CodeContext],
                                 vuln_type: str) -> Optional[SecurityFix]:
        """Generate a specific fix for the given approach."""
        
        # Handle infrastructure vulnerabilities (no code context)
        if code_context is None:
            return self._generate_infrastructure_fix(approach, vulnerability)
        
        language = code_context.language or 'generic'
        templates = self.language_templates.get(language, {})
        
        # Get template for this approach
        template_key = f"{vuln_type}_{approach.value}"
        fallback_key = approach.value
        
        template = templates.get(template_key) or templates.get(fallback_key)
        
        if not template:
            # Generate generic fix
            return self._generate_generic_fix(approach, vulnerability, code_context)
        
        # Apply template to generate fix
        return self._apply_fix_template(template, approach, vulnerability, code_context)

    def _parse_dependency_info(self, vulnerability: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Parse dependency upgrade information from vulnerability message.

        Extracts package name, installed version, and fixed version from the vulnerability
        message field for Trivy/OSV dependency vulnerabilities.

        Args:
            vulnerability: Vulnerability dict with 'message' field

        Returns:
            Dict with 'package', 'installed_version', 'fixed_version' keys, or None if parsing fails
        """
        message = vulnerability.get('message', '')

        if not message:
            return None

        # Parse package name (e.g., "Package: ch.qos.logback:logback-core")
        package_match = re.search(r'Package:\s*([^\n]+)', message)
        if not package_match:
            return None
        package_name = package_match.group(1).strip()

        # Parse installed version (e.g., "Installed Version: 1.4.14")
        installed_match = re.search(r'Installed Version:\s*([^\n]+)', message)
        if not installed_match:
            return None
        installed_version = installed_match.group(1).strip()

        # Parse fixed version (e.g., "Fixed Version: 1.5.13, 1.3.15")
        # CRITICAL BUG FIX: Parse line-by-line to avoid capturing markdown links
        fixed_version = ''
        for line in message.split('\n'):
            if line.startswith('Fixed Version:'):
                fixed_ver = line.replace('Fixed Version:', '').strip()
                # Remove markdown links if present (e.g., "1.5.13\nLink: [CVE-...]")
                if '[' in fixed_ver:
                    fixed_ver = fixed_ver.split('[')[0].strip()
                fixed_version = fixed_ver.rstrip(',').strip()
                break

        # If fixed version is empty, use 'latest'
        if not fixed_version:
            fixed_version = 'latest'

        return {
            'package': package_name,
            'installed_version': installed_version,
            'fixed_version': fixed_version
        }

    def _generate_infrastructure_fix(self, approach: FixApproach,
                                   vulnerability: Dict[str, Any]) -> SecurityFix:
        """Generate infrastructure-specific fixes for vulnerabilities without code context."""

        # Try to parse dependency information for specific upgrade instructions
        dependency_info = self._parse_dependency_info(vulnerability)

        if dependency_info:
            # Generate specific dependency upgrade instruction
            package = dependency_info['package']
            installed_version = dependency_info['installed_version']
            fixed_version = dependency_info['fixed_version']

            # Create specific upgrade instruction
            if fixed_version and fixed_version.lower() != 'latest':
                fixed_instruction = f"Upgrade '{package}' from version '{installed_version}' to version '{fixed_version}' in your dependency management file (build.gradle.kts, pom.xml, package.json, requirements.txt, etc.)."
            else:
                fixed_instruction = f"Upgrade '{package}' from version '{installed_version}' to the latest secure version in your dependency management file (build.gradle.kts, pom.xml, package.json, requirements.txt, etc.)."

            return SecurityFix(
                approach=approach,
                title='Dependency Security Update',
                description=f'Update {package} to fix security vulnerability',
                vulnerable_code=f'Current version: {package} {installed_version}',
                fixed_code=fixed_instruction,
                explanation=f'The installed version {installed_version} of {package} contains a known security vulnerability. Upgrading to {fixed_version} addresses this issue.',
                benefits=[
                    'Eliminates known security vulnerabilities',
                    'Provides security patches and bug fixes',
                    'Maintains compatibility with security standards'
                ],
                trade_offs=['May require dependency compatibility testing', 'Could introduce breaking changes in major version upgrades'],
                implementation_notes=[
                    'Update the dependency version in your build file',
                    'Run tests to ensure compatibility',
                    'Check release notes for any breaking changes'
                ],
                language='infrastructure',
                framework=None,
                complexity_level='low',
                security_impact='high'
            )

        # Fallback to generic templates if parsing fails
        approach_templates = {
            FixApproach.CONFIGURATION_CHANGE: {
                'title': 'Configuration Security Enhancement',
                'description': 'Update configuration to address security vulnerability',
                'vulnerable_config': 'Current insecure configuration',
                'fixed_config': 'Recommended secure configuration',
                'explanation': 'Update the configuration to use secure defaults and remove vulnerable settings.',
                'benefits': [
                    'Eliminates configuration-based security vulnerabilities',
                    'Improves overall system security posture',
                    'Reduces attack surface through secure defaults'
                ],
                'implementation_notes': [
                    'Review all configuration files for similar issues',
                    'Test configuration changes in staging environment',
                    'Document configuration security standards'
                ]
            },
            FixApproach.ACCESS_CONTROL: {
                'title': 'Access Control Implementation',
                'description': 'Implement proper access controls and permissions',
                'vulnerable_config': 'Overly permissive access configuration',
                'fixed_config': 'Restricted access with principle of least privilege',
                'explanation': 'Implement proper access controls to limit exposure and reduce security risks.',
                'benefits': [
                    'Reduces unauthorized access risks',
                    'Implements principle of least privilege',
                    'Improves audit and compliance posture'
                ],
                'implementation_notes': [
                    'Review and update access control policies',
                    'Implement role-based access controls where applicable',
                    'Regular access reviews and cleanup'
                ]
            },
            FixApproach.FRAMEWORK_SECURITY: {
                'title': 'Framework Security Configuration',
                'description': 'Configure framework security settings appropriately',
                'vulnerable_config': 'Default or insecure framework configuration',
                'fixed_config': 'Hardened framework security configuration',
                'explanation': 'Apply security hardening to framework configuration to prevent exploitation.',
                'benefits': [
                    'Leverages framework built-in security features',
                    'Reduces common attack vectors',
                    'Maintains compatibility while improving security'
                ],
                'implementation_notes': [
                    'Follow framework security best practices',
                    'Keep framework versions updated',
                    'Regular security configuration reviews'
                ]
            },
            FixApproach.LIBRARY_REPLACEMENT: {
                'title': 'Secure Library Replacement',
                'description': 'Replace vulnerable library with secure alternative',
                'vulnerable_config': 'Vulnerable library dependency',
                'fixed_config': 'Updated secure library version or alternative',
                'explanation': 'Update or replace vulnerable libraries with secure versions or alternatives.',
                'benefits': [
                    'Eliminates known vulnerabilities',
                    'Improves long-term security maintenance',
                    'May include performance improvements'
                ],
                'implementation_notes': [
                    'Test library replacements thoroughly',
                    'Update dependency management processes',
                    'Monitor for future security updates'
                ]
            }
        }

        template = approach_templates.get(approach, approach_templates[FixApproach.CONFIGURATION_CHANGE])

        return SecurityFix(
            approach=approach,
            title=template['title'],
            description=template['description'],
            vulnerable_code=template['vulnerable_config'],
            fixed_code=template['fixed_config'],
            explanation=template['explanation'],
            benefits=template['benefits'],
            trade_offs=['May require infrastructure changes', 'Could affect system compatibility'],
            implementation_notes=template['implementation_notes'],
            language='infrastructure',
            framework=None,
            complexity_level='medium',
            security_impact='high'
        )
    
    def _generate_generic_fix(self, approach: FixApproach, 
                            vulnerability: Dict[str, Any],
                            code_context: CodeContext) -> SecurityFix:
        """Generate a generic fix when no specific template is available."""
        
        approach_descriptions = {
            FixApproach.INPUT_VALIDATION: {
                'title': 'Input Validation and Sanitization',
                'description': 'Validate and sanitize all user inputs before processing',
                'explanation': 'Add comprehensive input validation to prevent malicious data from being processed.'
            },
            FixApproach.OUTPUT_SANITIZATION: {
                'title': 'Output Encoding and Sanitization', 
                'description': 'Properly encode outputs to prevent injection attacks',
                'explanation': 'Ensure all data sent to output contexts is properly encoded or escaped.'
            },
            FixApproach.ERROR_HANDLING: {
                'title': 'Secure Error Handling',
                'description': 'Implement proper error handling without information disclosure',
                'explanation': 'Replace error messages that could leak sensitive information with generic messages.'
            },
            FixApproach.ACCESS_CONTROL: {
                'title': 'Access Control Implementation',
                'description': 'Add proper authorization checks before sensitive operations',
                'explanation': 'Verify user permissions before allowing access to sensitive functionality.'
            },
            FixApproach.IN_MEMORY_SOLUTION: {
                'title': 'In-Memory Security Solution',
                'description': 'Use in-memory data structures for secure temporary storage',
                'explanation': 'Leverage secure in-memory storage to avoid persistence vulnerabilities.'
            },
            FixApproach.DATABASE_SOLUTION: {
                'title': 'Database-Level Security',
                'description': 'Implement security controls at the database layer',
                'explanation': 'Use parameterized queries and database-level security features.'
            },
            FixApproach.CACHE_SOLUTION: {
                'title': 'Secure Caching Strategy',
                'description': 'Implement secure caching with proper expiration and validation',
                'explanation': 'Use secure caching mechanisms to prevent cache-based attacks.'
            },
            FixApproach.MICROSERVICE_SOLUTION: {
                'title': 'Microservice Architecture Fix',
                'description': 'Isolate security concerns in dedicated microservices',
                'explanation': 'Separate security-sensitive operations into isolated services.'
            }
        }
        
        info = approach_descriptions.get(approach, {
            'title': f'{approach.value.replace("_", " ").title()} Fix',
            'description': f'Apply {approach.value.replace("_", " ")} security measures',
            'explanation': f'Implement security fixes using {approach.value.replace("_", " ")} approach.'
        })
        
        return SecurityFix(
            approach=approach,
            title=info['title'],
            description=info['description'],
            vulnerable_code=code_context.vulnerable_code,
            fixed_code=f"// TODO: Implement {info['title'].lower()}\n{code_context.vulnerable_code}",
            explanation=info['explanation'],
            benefits=[
                "Improves security posture",
                "Reduces attack surface",
                "Follows security best practices"
            ],
            trade_offs=[
                "May require additional development time",
                "Could impact performance slightly"
            ],
            implementation_notes=[
                f"Apply {info['title'].lower()} principles",
                "Test thoroughly after implementation",
                "Consider security review"
            ],
            language=code_context.language,
            complexity_level="medium",
            security_impact="medium"
        )
    
    def _apply_fix_template(self, template: Dict[str, Any], 
                          approach: FixApproach,
                          vulnerability: Dict[str, Any],
                          code_context: CodeContext) -> SecurityFix:
        """Apply a fix template to generate specific code fixes."""
        
        # Extract template components
        title = template.get('title', f'{approach.value.replace("_", " ").title()} Fix')
        description = template.get('description', '')
        explanation = template.get('explanation', '')
        
        # Generate fixed code using template
        fixed_code = self._generate_fixed_code(template, code_context)
        
        return SecurityFix(
            approach=approach,
            title=title,
            description=description,
            vulnerable_code=code_context.vulnerable_code,
            fixed_code=fixed_code,
            explanation=explanation,
            benefits=template.get('benefits', []),
            trade_offs=template.get('trade_offs', []),
            implementation_notes=template.get('implementation_notes', []),
            language=code_context.language,
            framework=template.get('framework'),
            complexity_level=template.get('complexity_level', 'medium'),
            security_impact=template.get('security_impact', 'medium')
        )
    
    def _generate_fixed_code(self, template: Dict[str, Any], 
                           code_context: CodeContext) -> str:
        """Generate fixed code using template patterns."""
        
        vulnerable_code = code_context.vulnerable_code
        
        # Apply template transformations
        transformations = template.get('transformations', [])
        fixed_code = vulnerable_code
        
        for transform in transformations:
            if transform['type'] == 'replace':
                pattern = transform['pattern']
                replacement = transform['replacement']
                fixed_code = re.sub(pattern, replacement, fixed_code)
            elif transform['type'] == 'wrap':
                prefix = transform.get('prefix', '')
                suffix = transform.get('suffix', '')
                fixed_code = f"{prefix}{fixed_code}{suffix}"
            elif transform['type'] == 'prepend':
                fixed_code = f"{transform['code']}\n{fixed_code}"
            elif transform['type'] == 'append':
                fixed_code = f"{fixed_code}\n{transform['code']}"
        
        return fixed_code
    
    def _get_python_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get Python-specific fix templates."""
        return {
            'input_validation': {
                'title': 'Python Input Validation',
                'description': 'Add input validation using Python best practices',
                'explanation': 'Use Python validation libraries and type hints for secure input handling.',
                'transformations': [
                    {
                        'type': 'prepend',
                        'code': 'import re\nfrom typing import Optional\n\ndef validate_input(data: str) -> Optional[str]:\n    if not data or not isinstance(data, str):\n        return None\n    # Add specific validation logic\n    return data.strip()'
                    },
                    {
                        'type': 'wrap',
                        'prefix': 'validated_data = validate_input(',
                        'suffix': ')\nif validated_data is None:\n    raise ValueError("Invalid input")'
                    }
                ],
                'benefits': ['Type safety', 'Clear validation logic', 'Pythonic approach'],
                'complexity_level': 'low',
                'security_impact': 'high'
            },
            'sql_injection_database_solution': {
                'title': 'Python Parameterized Queries',
                'description': 'Use parameterized queries to prevent SQL injection',
                'explanation': 'Replace string concatenation with parameterized queries using Python DB-API.',
                'transformations': [
                    {
                        'type': 'replace',
                        'pattern': r'["\'].*?%s.*?["\']',
                        'replacement': '""'
                    },
                    {
                        'type': 'wrap',
                        'prefix': 'cursor.execute("SELECT * FROM users WHERE id = %s", (',
                        'suffix': ',))'
                    }
                ],
                'benefits': ['Prevents SQL injection', 'Database agnostic', 'Performance benefits'],
                'complexity_level': 'low',
                'security_impact': 'critical'
            }
        }
    
    def _get_kotlin_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get Kotlin-specific fix templates."""
        return {
            'input_validation': {
                'title': 'Kotlin Input Validation',
                'description': 'Use Kotlin null safety and validation for secure input handling',
                'explanation': 'Leverage Kotlin\'s type system and validation libraries for input security.',
                'transformations': [
                    {
                        'type': 'wrap',
                        'prefix': 'require(!',
                        'suffix': '.isNullOrBlank()) { "Input cannot be null or blank" }'
                    }
                ],
                'benefits': ['Null safety', 'Expressive syntax', 'Compile-time checks'],
                'complexity_level': 'low',
                'security_impact': 'medium'
            }
        }
    
    def _get_java_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get Java-specific fix templates."""
        return {
            'input_validation': {
                'title': 'Java Input Validation',
                'description': 'Use Java validation frameworks for secure input handling',
                'explanation': 'Apply Java validation annotations and secure coding practices.',
                'benefits': ['Framework integration', 'Annotation-based', 'Enterprise ready'],
                'complexity_level': 'medium',
                'security_impact': 'high'
            }
        }
    
    def _get_javascript_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get JavaScript-specific fix templates."""
        return {
            'xss_output_sanitization': {
                'title': 'JavaScript XSS Prevention',
                'description': 'Sanitize output to prevent XSS attacks',
                'explanation': 'Use proper encoding and sanitization for web output.',
                'transformations': [
                    {
                        'type': 'wrap',
                        'prefix': 'escapeHtml(',
                        'suffix': ')'
                    }
                ],
                'benefits': ['XSS prevention', 'Client-side security', 'Easy integration'],
                'complexity_level': 'low',
                'security_impact': 'high'
            }
        }
    
    def _get_typescript_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get TypeScript-specific fix templates."""
        return {
            'input_validation': {
                'title': 'TypeScript Type-Safe Validation',
                'description': 'Use TypeScript types and validation for input security',
                'explanation': 'Leverage TypeScript\'s type system for compile-time security.',
                'benefits': ['Type safety', 'Compile-time checks', 'Developer experience'],
                'complexity_level': 'medium',
                'security_impact': 'medium'
            }
        }
    
    def generate_training_examples(self, vulnerabilities: List[Dict[str, Any]],
                                 extractor: VulnerableCodeExtractor) -> List[Dict[str, Any]]:
        """
        Generate training examples for multiple vulnerabilities.
        
        Args:
            vulnerabilities: List of vulnerability data
            extractor: VulnerableCodeExtractor instance
            
        Returns:
            List of training examples with multiple fix approaches
        """
        training_examples = []
        
        for vuln in vulnerabilities:
            # Extract code context
            extraction_result = extractor.extract_vulnerability_context(vuln)
            
            if not extraction_result.success:
                continue
            
            # Generate multiple fixes
            fix_result = self.generate_fixes(vuln, extraction_result.code_context)
            
            if not fix_result.success:
                continue
            
            # Create training example
            training_example = {
                'vulnerability': {
                    'id': vuln.get('check_id', 'unknown'),
                    'message': vuln.get('extra', {}).get('message', ''),
                    'severity': vuln.get('extra', {}).get('severity', 'unknown'),
                    'file_path': vuln.get('path', ''),
                    'line': vuln.get('start', {}).get('line', 0)
                },
                'code_context': {
                    'language': extraction_result.code_context.language,
                    'function': extraction_result.code_context.function_name,
                    'class': extraction_result.code_context.class_name,
                    'vulnerable_code': extraction_result.code_context.vulnerable_code,
                    'context': extraction_result.code_context.get_full_context()
                },
                'fixes': [
                    {
                        'approach': fix.approach.value,
                        'title': fix.title,
                        'description': fix.description,
                        'fixed_code': fix.fixed_code,
                        'explanation': fix.explanation,
                        'benefits': fix.benefits,
                        'complexity': fix.complexity_level,
                        'security_impact': fix.security_impact
                    }
                    for fix in fix_result.fixes
                ]
            }
            
            training_examples.append(training_example)
        
        return training_examples

    # ========================================
    # Tool-Specific Fix Generation Methods
    # ========================================

    def _generate_osv_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        OSV-specific: Extract fixed versions from affected ranges.

        OSV provides complex version ranges:
        - Multiple branches (1.3.x → 1.3.15, 1.5.x → 1.5.13)
        - Ecosystem-specific format
        - Rich metadata (CVSS v4, patch commits)
        """
        # Extract fixed versions from OSV data
        # OSV format has 'vulnerabilities' array with 'affected' field
        fixed_versions = self._extract_osv_fixed_versions(vuln)

        if not fixed_versions:
            return FixGenerationResult(
                success=False,
                error_message="No fixed version available in OSV data"
            )

        # Primary fix: Latest version
        primary_version = fixed_versions[0]
        package_name = vuln.get('package_name')
        current_version = vuln.get('installed_version')
        ecosystem = vuln.get('ecosystem')

        if not package_name:
            raise ValueError("Package name missing in OSV vulnerability data")
        if not current_version:
            raise ValueError("Installed version missing in OSV vulnerability data")
        if not ecosystem:
            raise ValueError("Ecosystem information missing in OSV vulnerability data")

        fix = SecurityFix(
            approach=FixApproach.LIBRARY_REPLACEMENT,
            title=f"Upgrade {package_name} to fix {vuln.get('id', 'vulnerability')}",
            description=f"Upgrade {package_name} from {current_version} to {primary_version}",
            vulnerable_code=code_context.vulnerable_code if code_context else f'{package_name}:{current_version}',
            fixed_code=self._generate_dependency_upgrade_code(
                package_name,
                primary_version,
                ecosystem
            ),
            explanation=vuln.get('summary', f'Security vulnerability fixed in version {primary_version}'),
            benefits=[
                'Eliminates known security vulnerability',
                'Includes security patches from upstream',
                'Maintains compatibility with ecosystem'
            ],
            trade_offs=[
                'May require dependency testing',
                'Could introduce breaking changes if major version upgrade'
            ],
            implementation_notes=[
                f"Update dependency to version {primary_version}",
                'Run tests to ensure compatibility',
                'Check release notes for breaking changes'
            ],
            language=code_context.language if code_context else ecosystem.lower(),
            complexity_level='low',
            security_impact='high'
        )

        # Alternative fixes: Other fixed versions
        alternatives = []
        for alt_version in fixed_versions[1:]:
            alt_fix = SecurityFix(
                approach=FixApproach.LIBRARY_REPLACEMENT,
                title=f"Alternative: Upgrade to {alt_version}",
                description=f"Upgrade {package_name} from {current_version} to {alt_version}",
                vulnerable_code=code_context.vulnerable_code if code_context else f'{package_name}:{current_version}',
                fixed_code=self._generate_dependency_upgrade_code(
                    package_name,
                    alt_version,
                    ecosystem
                ),
                explanation=f"Alternative fix for projects on different release branch ({alt_version} branch)",
                benefits=[
                    'Same security fix as primary version',
                    'May be more compatible with existing dependencies'
                ],
                trade_offs=[
                    'Different version branch may have different features'
                ],
                complexity_level='low',
                security_impact='high'
            )
            alternatives.append(alt_fix)

        return FixGenerationResult(
            success=True,
            fixes=[fix] + alternatives,
            generation_metadata={
                'tool': 'osv',
                'confidence': 1.0,
                'fixed_versions': fixed_versions,
                'ecosystem': ecosystem
            }
        )

    def _generate_trivy_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        Trivy-specific: Parse message field for dependency info.

        Uses existing _parse_dependency_info() method (lines 283-325).
        """
        # Use existing dependency parsing method
        dependency_info = self._parse_dependency_info(vuln)

        if not dependency_info:
            return FixGenerationResult(
                success=False,
                error_message="Could not parse Trivy dependency information from message field"
            )

        # Generate fix using existing infrastructure method
        fix = self._generate_infrastructure_fix(
            FixApproach.LIBRARY_REPLACEMENT,
            vuln
        )

        return FixGenerationResult(
            success=True,
            fixes=[fix],
            generation_metadata={
                'tool': 'trivy',
                'confidence': 1.0
            }
        )

    def _generate_semgrep_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        Semgrep-specific: Multi-approach code pattern fixes.

        Uses existing vulnerability_patterns + language_templates.
        Requires code_context.
        """
        if not code_context:
            return FixGenerationResult(
                success=False,
                error_message="Code context required for Semgrep fix generation"
            )

        # Use existing pattern-based fix generation (fall through to generic)
        vuln_type = self._classify_vulnerability(vuln)
        approaches = self._get_fix_approaches(vuln_type, code_context)

        fixes = []
        for approach in approaches:
            fix = self._generate_fix_for_approach(approach, vuln, code_context, vuln_type)
            if fix:
                fixes.append(fix)

        return FixGenerationResult(
            success=True,
            fixes=fixes,
            generation_metadata={
                'tool': 'semgrep',
                'confidence': 0.7,
                'vuln_type': vuln_type,
                'approaches_used': [f.approach.value for f in fixes]
            }
        )
    def _generate_zap_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        ZAP-specific: HTTP security configuration fixes.

        ZAP findings are HTTP-level and typically don't have code context.
        Uses ZAP's solution field to generate configuration-based fixes.
        """
        # Extract ZAP solution
        solution = vuln.get('solution', '').strip()
        if not solution:
            return FixGenerationResult(
                success=False,
                error_message="No solution provided by ZAP"
            )

        alert_name = vuln.get('alert', 'HTTP security issue')

        # Generate generic HTTP configuration fix based on alert type
        fixed_code = self._generate_http_security_fix(alert_name, solution)

        # Use clean solution (already stripped of HTML in parser)
        clean_solution = solution[:200] + ('...' if len(solution) > 200 else '')

        fix = SecurityFix(
            approach=FixApproach.CONFIGURATION_CHANGE,
            title=f"Fix {alert_name}",
            description=clean_solution,
            vulnerable_code=f"HTTP endpoint: {vuln.get('uri', 'Unknown URL')}",
            fixed_code=fixed_code,
            explanation=f"ZAP identified {alert_name} in HTTP response. {solution}",
            benefits=[
                'Addresses HTTP security misconfiguration',
                'Improves web application security posture',
                'Prevents common web attacks'
            ],
            language='http',
            complexity_level='low',
            security_impact='medium'
        )

        return FixGenerationResult(
            success=True,
            fixes=[fix],
            generation_metadata={
                'tool': 'zap',
                'confidence': 0.9
            }
        )

    def _generate_http_security_fix(self, alert_name: str, solution: str) -> str:
        """
        Generate HTTP security configuration fix based on alert type.

        Maps common ZAP alerts to generic configuration examples.
        """
        alert_lower = alert_name.lower()

        if 'cors' in alert_lower:
            return """// Ktor CORS Configuration
install(CORS) {
    allowHost("yourdomain.com", schemes = listOf("https"))
    allowCredentials = true
    allowMethod(HttpMethod.Get)
    allowMethod(HttpMethod.Post)
}"""
        elif 'x-content-type-options' in alert_lower:
            return """// Ktor Security Headers
install(DefaultHeaders) {
    header("X-Content-Type-Options", "nosniff")
}"""
        elif 'cache' in alert_lower or 'cacheable' in alert_lower:
            return """// Ktor Cache Control
install(CachingHeaders) {
    options { call, _ ->
        when {
            call.request.path().startsWith("/api") ->
                CachingOptions(CacheControl.NoStore(CacheControl.Visibility.Private))
            else -> null
        }
    }
}"""
        elif 'cross-origin-resource-policy' in alert_lower or 'spectre' in alert_lower:
            return """// Ktor Security Headers
install(DefaultHeaders) {
    header("Cross-Origin-Resource-Policy", "same-origin")
}"""
        elif 'sec-fetch' in alert_lower:
            return """// Server-side validation of Sec-Fetch headers
intercept(ApplicationCallPipeline.Call) {
    val fetchDest = call.request.headers["Sec-Fetch-Dest"]
    val fetchMode = call.request.headers["Sec-Fetch-Mode"]
    val fetchSite = call.request.headers["Sec-Fetch-Site"]

    // Validate Sec-Fetch headers for sensitive endpoints
    if (call.request.path().startsWith("/api/") && fetchSite == "cross-site") {
        call.respond(HttpStatusCode.Forbidden)
        finish()
    }
}"""
        else:
            return f"""// HTTP Security Configuration
// {solution}

// Apply appropriate security headers or configuration changes
// based on the specific security requirement."""

    def _generate_checkov_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        Checkov-specific: Configuration/IaC security fixes.

        Uses rule knowledge base + YAML context.
        Falls back to generic fix if no specific pattern available.
        """
        rule_id = vuln.get('id', vuln.get('check_id', vuln.get('rule_name', '')))
        rule_name = vuln.get('rule_name', vuln.get('message', 'Security configuration issue'))
        message = vuln.get('message', rule_name)

        # Look up rule fix pattern
        fix_pattern = self._get_checkov_fix_pattern(rule_id)

        if fix_pattern:
            # Use predefined pattern
            fix = SecurityFix(
                approach=FixApproach.CONFIGURATION_CHANGE,
                title=fix_pattern['title'],
                description=fix_pattern['description'],
                vulnerable_code=code_context.vulnerable_code if code_context else f"Configuration issue in {vuln.get('file_path', 'config file')}",
                fixed_code=fix_pattern['fixed_code'],
                explanation=fix_pattern['explanation'],
                benefits=fix_pattern.get('benefits', []),
                language=code_context.language if code_context else 'yaml',
                complexity_level='low',
                security_impact='medium'
            )
            confidence = 0.8  # High confidence for known patterns
        else:
            # Generate generic fix based on rule message
            fix = SecurityFix(
                approach=FixApproach.CONFIGURATION_CHANGE,
                title=f"Fix {rule_name}",
                description=message[:200] + ('...' if len(message) > 200 else ''),
                vulnerable_code=code_context.vulnerable_code if code_context else f"Configuration in {vuln.get('file_path', 'config file')}",
                fixed_code=f"# Apply fix based on Checkov rule {rule_id}\n# {message}\n\n# Review and update configuration to address the security issue",
                explanation=f"Checkov identified {rule_name}. Review the configuration and apply the recommended changes from Checkov documentation.",
                benefits=[
                    'Improves configuration security',
                    'Follows security best practices',
                    'Reduces attack surface'
                ],
                language=code_context.language if code_context else 'yaml',
                complexity_level='low',
                security_impact='medium'
            )
            confidence = 0.7  # Lower confidence for generic fixes

        return FixGenerationResult(
            success=True,
            fixes=[fix],
            generation_metadata={
                'tool': 'checkov',
                'confidence': confidence,
                'rule_id': rule_id
            }
        )

    def _extract_osv_fixed_versions(self, vuln: Dict) -> List[str]:
        """
        Extract fixed versions from OSV vulnerability data.

        OSV format can have fixed versions in multiple places:
        1. Direct 'fixed_version' field (from our parser)
        2. 'affected' array with ranges/events (full OSV JSON)
        """
        fixed_versions = []

        # Check for direct fixed_version field (from simplified parser output)
        if 'fixed_version' in vuln:
            fixed_version = vuln['fixed_version']
            if fixed_version and fixed_version != 'Unknown':
                # Could be comma-separated list
                if ',' in fixed_version:
                    fixed_versions = [v.strip() for v in fixed_version.split(',')]
                else:
                    fixed_versions = [fixed_version]

        # Check for full OSV format with 'affected' array
        if 'affected' in vuln:
            for affected_item in vuln['affected']:
                for range_obj in affected_item.get('ranges', []):
                    for event in range_obj.get('events', []):
                        if 'fixed' in event:
                            fixed_versions.append(event['fixed'])

        # Remove duplicates and empty strings, sort by version (latest first)
        fixed_versions = [v for v in set(fixed_versions) if v and v.strip()]

        # Simple version sorting (latest first) - this is basic, could be improved with packaging.version
        return sorted(fixed_versions, reverse=True)

    def _generate_dependency_upgrade_code(self, package: str, version: str, ecosystem: str) -> str:
        """Generate ecosystem-specific dependency upgrade code."""
        if ecosystem == 'Maven' or ecosystem == 'maven':
            # Gradle Kotlin DSL format
            return f'implementation("{package}:{version}")'
        elif ecosystem == 'npm' or ecosystem == 'npm':
            # package.json format
            pkg_name = package.split('/')[-1]  # Handle scoped packages
            return f'"{package}": "^{version}"'
        elif ecosystem == 'PyPI' or ecosystem == 'pypi':
            # requirements.txt format
            return f'{package}=={version}'
        elif ecosystem == 'Go':
            # go.mod format
            return f'require {package} v{version}'
        else:
            # Generic format
            return f'{package}:{version}'

    def _detect_framework(self, language: str, file_path: str) -> str:
        """Detect web framework from code context."""
        if not language:
            language = ''
        if not file_path:
            file_path = ''

        language = language.lower()
        file_path = file_path.lower()

        if 'kotlin' in language or '.kt' in file_path or 'ktor' in file_path:
            return 'Ktor'
        elif 'typescript' in language or 'javascript' in language or '.ts' in file_path or '.js' in file_path:
            if 'express' in file_path:
                return 'Express'
            return 'Node.js'
        elif 'python' in language or '.py' in file_path:
            return 'Python'
        elif 'java' in language or '.java' in file_path:
            return 'Spring'
        return 'unknown'

    def _generate_framework_specific_fix(self, alert: str, solution: str, framework: str, code_context: CodeContext) -> str:
        """Generate framework-specific fix code."""
        # Framework-specific code generation logic
        # This can be expanded with templates for different frameworks

        if framework == 'Ktor' and 'CORS' in alert:
            return """install(CORS) {
    allowHost("app.example.com", schemes = listOf("https"))
    allowCredentials = true
}"""
        elif (framework == 'Express' or framework == 'Node.js') and 'CORS' in alert:
            return """app.use(cors({
    origin: 'https://app.example.com',
    credentials: true
}));"""
        elif framework == 'Ktor' and 'Content Security Policy' in alert:
            return """install(DefaultHeaders) {
    header("Content-Security-Policy", "default-src 'self'")
}"""
        elif (framework == 'Express' or framework == 'Node.js') and 'Content Security Policy' in alert:
            return """app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"]
        }
    }
}));"""

        # Generic fix based on solution
        return f"// Apply fix based on: {solution[:100]}..."

    def _get_checkov_fix_pattern(self, rule_id: str) -> Optional[Dict]:
        """
        Get fix pattern for Checkov rule.

        Includes patterns for common GitHub Actions, Docker, and IaC rules.
        """
        patterns = {
            'CKV_GHA_1': {
                'title': 'Add explicit workflow permissions',
                'description': 'Configure explicit permissions instead of inheriting defaults',
                'fixed_code': 'permissions:\n  contents: read\n  pull-requests: write',
                'explanation': 'Explicit permissions follow principle of least privilege',
                'benefits': ['Reduces attack surface', 'Prevents unauthorized access']
            },
            'CKV2_GHA_1': {
                'title': 'Remove write-all from top-level permissions',
                'description': 'Replace write-all with granular permissions',
                'fixed_code': '''permissions:
  contents: read      # For checking out code
  pull-requests: write # For commenting on PRs
  issues: write       # For creating/updating issues
  # Remove: permissions: write-all''',
                'explanation': 'Using write-all grants excessive permissions. Specify only the permissions each job needs.',
                'benefits': [
                    'Follows principle of least privilege',
                    'Reduces risk of unauthorized changes',
                    'Limits blast radius of compromised workflows'
                ]
            },
            'CKV_GHA_7': {
                'title': 'Pin GitHub Actions to commit SHA',
                'description': 'Use commit SHA instead of tag for reproducibility',
                'fixed_code': 'uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1',
                'explanation': 'Pinning to SHA ensures exact version and prevents tag hijacking',
                'benefits': ['Prevents supply chain attacks', 'Ensures reproducibility']
            }
        }

        return patterns.get(rule_id, None)


# Convenience function for quick usage
def generate_security_fixes(vulnerability: Dict[str, Any], 
                          code_context: CodeContext) -> FixGenerationResult:
    """
    Quick function to generate security fixes for a vulnerability.
    
    Args:
        vulnerability: Vulnerability data
        code_context: Code context around vulnerability
        
    Returns:
        Fix generation result
    """
    generator = MultiApproachFixGenerator()
    return generator.generate_fixes(vulnerability, code_context)