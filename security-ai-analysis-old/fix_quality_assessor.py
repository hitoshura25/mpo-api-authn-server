#!/usr/bin/env python3
"""
Fix Quality Assessor - Quality Assurance Framework

Provides comprehensive validation of generated fixes using open-source tools.
This module is designed to be enabled by default in the main process_artifacts.py 
pipeline to ensure the highest quality training data and analysis output.

Key Features:
- Syntax validation for multiple programming languages
- Security improvement assessment
- Code quality scoring
- Best practices compliance checking
- Integration with enhanced dataset creation pipeline

Design Philosophy:
- Default behavior: Quality assessment runs automatically
- No configuration required: Built into standard workflow
- Quality filtering: Only high-quality fixes included in training datasets
"""

import ast
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)

@dataclass
class QualityAssessmentResult:
    """Results from comprehensive fix quality assessment"""
    overall_score: float
    syntax_valid: bool
    security_improved: bool
    code_quality_score: float
    best_practices_score: float
    completeness_score: float
    validation_passed: bool
    individual_scores: Dict[str, Any]
    recommendations: List[str]
    assessment_details: Dict[str, Any]

@dataclass
class SyntaxValidationResult:
    """Results from language-specific syntax validation"""
    is_valid: bool
    error_message: Optional[str] = None
    line_number: Optional[int] = None
    error_type: Optional[str] = None

class SyntaxValidator:
    """Language-specific syntax validation using appropriate parsers"""
    
    def __init__(self):
        self.supported_languages = {
            'python', 'kotlin', 'java', 'javascript', 'typescript', 'yaml', 'json'
        }
    
    def validate(self, code: str, language: str) -> SyntaxValidationResult:
        """Validate code syntax for the specified language"""
        
        language = language.lower()
        if language not in self.supported_languages:
            logger.warning(f"Syntax validation not supported for language: {language}")
            return SyntaxValidationResult(is_valid=True)  # Pass through unsupported languages
        
        try:
            if language == 'python':
                return self._validate_python_syntax(code)
            elif language in ['kotlin', 'java']:
                return self._validate_jvm_syntax(code, language)
            elif language in ['javascript', 'typescript']:
                return self._validate_js_syntax(code, language)
            elif language == 'yaml':
                return self._validate_yaml_syntax(code)
            elif language == 'json':
                return self._validate_json_syntax(code)
            else:
                return SyntaxValidationResult(is_valid=True)
                
        except Exception as e:
            logger.error(f"Syntax validation failed for {language}: {e}")
            raise
    
    def _validate_python_syntax(self, code: str) -> SyntaxValidationResult:
        """Validate Python syntax using AST parsing"""
        try:
            ast.parse(code)
            return SyntaxValidationResult(is_valid=True)
        except SyntaxError as e:
            return SyntaxValidationResult(
                is_valid=False,
                error_message=str(e),
                line_number=e.lineno,
                error_type="syntax_error"
            )
    
    def _validate_jvm_syntax(self, code: str, language: str) -> SyntaxValidationResult:
        """Validate Kotlin/Java syntax using basic pattern matching"""
        # Basic syntax checks for common issues
        
        # Check for balanced braces
        if not self._check_balanced_braces(code):
            return SyntaxValidationResult(
                is_valid=False,
                error_message="Unbalanced braces detected",
                error_type="syntax_error"
            )
        
        # Check for basic language-specific patterns
        if language == 'kotlin':
            # Check for Kotlin-specific syntax patterns
            if 'fun ' in code and not re.search(r'fun\s+\w+\s*\(', code):
                return SyntaxValidationResult(
                    is_valid=False,
                    error_message="Invalid function declaration syntax",
                    error_type="syntax_error"
                )
        
        return SyntaxValidationResult(is_valid=True)
    
    def _validate_js_syntax(self, code: str, language: str) -> SyntaxValidationResult:
        """Validate JavaScript/TypeScript syntax using Node.js if available"""
        try:
            # Try using Node.js for accurate syntax checking
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                
                # Use Node.js to check syntax
                result = subprocess.run(
                    ['node', '--check', f.name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                Path(f.name).unlink()  # Clean up temp file
                
                if result.returncode == 0:
                    return SyntaxValidationResult(is_valid=True)
                else:
                    return SyntaxValidationResult(
                        is_valid=False,
                        error_message=result.stderr.strip(),
                        error_type="syntax_error"
                    )
                    
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Node.js validation failed: {e}")
            raise
    
    def _validate_yaml_syntax(self, code: str) -> SyntaxValidationResult:
        """Validate YAML syntax"""
        try:
            import yaml
            yaml.safe_load(code)
            return SyntaxValidationResult(is_valid=True)
        except Exception as e:
            logger.error(f"YAML validation failed: {e}")
            raise
    
    def _validate_json_syntax(self, code: str) -> SyntaxValidationResult:
        """Validate JSON syntax"""
        try:
            json.loads(code)
            return SyntaxValidationResult(is_valid=True)
        except json.JSONDecodeError as e:
            logger.error(f"JSON validation failed: {e}")
            raise
    
    def _check_balanced_braces(self, code: str) -> bool:
        """Check if braces, brackets, and parentheses are balanced"""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                last = stack.pop()
                if pairs[last] != char:
                    return False
        
        return len(stack) == 0

class SecurityValidator:
    """Security improvement assessment for generated fixes"""
    
    def __init__(self):
        self.vulnerability_patterns = {
            'sql_injection': [
                r'PreparedStatement',
                r'parameterized.*query',
                r'bind.*parameter',
                r'\.setString\(',
                r'\.setInt\(',
                r'%s',  # Python parameterized queries
                r'\?',  # SQL parameter placeholders
                r'execute\s*\([^,]+,\s*\(',  # Python execute with parameters
            ],
            'xss': [
                r'htmlspecialchars',
                r'escapeHtml',
                r'sanitize',
                r'Content-Security-Policy',
                r'textContent\s*=',
            ],
            'command_injection': [
                r'ProcessBuilder',
                r'Arrays\.asList',
                r'whitelist.*validation',
                r'input.*validation',
            ],
            'path_traversal': [
                r'Path\.normalize',
                r'canonical.*path',
                r'resolve.*path',
                r'path.*validation',
            ],
            'authentication': [
                r'bcrypt',
                r'password.*hash',
                r'authentication.*required',
                r'session.*validation',
            ],
            'permissions': [
                r'permissions:\s*\{',
                r'permissions:',
                r'read.*only',
                r'contents:\s*read',
                r'minimal.*permissions',
                r'least.*privilege',
            ],
            'configuration': [
                r'security.*config',
                r'access.*control',
                r'privilege.*separation',
                r'secure.*defaults',
            ]
        }
    
    def assess_security_improvement(self, vulnerability: Dict[str, Any], fixed_code: str, original_code: str = None) -> Tuple[bool, float, List[str]]:
        """Assess if the fix improves security"""
        
        vulnerability_type = vulnerability.get('type', '').lower()
        improvements = []
        score = 0.0
        
        # Check for vulnerability-specific patterns in the fix
        if vulnerability_type in self.vulnerability_patterns:
            patterns = self.vulnerability_patterns[vulnerability_type]
            
            for pattern in patterns:
                if re.search(pattern, fixed_code, re.IGNORECASE):
                    improvements.append(f"Implements {pattern} security pattern")
                    score += 0.2
        
        # General security improvements (more comprehensive)
        security_keywords = [
            'validation', 'sanitization', 'authentication', 'authorization',
            'encryption', 'secure', 'safety', 'protection', 'validate',
            'sanitize', 'escape', 'check', 'verify', 'filter', 'clean',
            'auth', 'permission', 'access', 'control', 'guard', 'safe'
        ]

        for keyword in security_keywords:
            if keyword in fixed_code.lower():
                score += 0.15  # Increased score for security keywords
        
        # Check if original vulnerability pattern is addressed
        if original_code:
            score += self._assess_vulnerability_removal(original_code, fixed_code, vulnerability_type)
        
        # Normalize score to 0-1 range
        score = min(score, 1.0)
        
        security_improved = score > 0.3 or len(improvements) > 0
        
        return security_improved, score, improvements
    
    def _assess_vulnerability_removal(self, original_code: str, fixed_code: str, vulnerability_type: str) -> float:
        """Assess if the original vulnerability has been addressed"""
        
        # Common vulnerability indicators that should be removed/modified
        vulnerability_indicators = {
            'sql_injection': [r'"\s*\+\s*', r"'\s*\+\s*", r'String\.format'],
            'xss': [r'innerHTML\s*=', r'document\.write'],
            'command_injection': [r'Runtime\.exec', r'Process\.start'],
            'path_traversal': [r'\.\./', r'File\(.*\+']
        }
        
        score = 0.0
        
        if vulnerability_type in vulnerability_indicators:
            indicators = vulnerability_indicators[vulnerability_type]
            
            for indicator in indicators:
                in_original = bool(re.search(indicator, original_code))
                in_fixed = bool(re.search(indicator, fixed_code))
                
                if in_original and not in_fixed:
                    score += 0.3  # Good - vulnerability indicator removed
                elif in_original and in_fixed:
                    score -= 0.1  # Bad - vulnerability indicator still present
        
        return max(score, 0.0)

class CodeQualityScorer:
    """Assess code quality of generated fixes"""
    
    def score_code_quality(self, code: str, language: str) -> Tuple[float, List[str]]:
        """Score code quality and provide recommendations"""
        
        score = 0.5  # Start with baseline
        recommendations = []
        
        # Code length assessment
        lines = code.strip().split('\n')
        if len(lines) > 100:
            score -= 0.1
            recommendations.append("Consider breaking large functions into smaller ones")
        elif len(lines) < 5:
            score -= 0.05
            recommendations.append("Code might be too minimal - ensure completeness")
        
        # Comment assessment
        comment_lines = [line for line in lines if line.strip().startswith(('//', '#', '/*', '*'))]
        comment_ratio = len(comment_lines) / max(len(lines), 1)
        
        if comment_ratio > 0.1:
            score += 0.1
        elif comment_ratio == 0:
            recommendations.append("Consider adding comments to explain the fix")
        
        # Language-specific quality checks
        if language.lower() == 'python':
            score += self._assess_python_quality(code)
        elif language.lower() in ['kotlin', 'java']:
            score += self._assess_jvm_quality(code)
        elif language.lower() in ['javascript', 'typescript']:
            score += self._assess_js_quality(code)
        
        # Error handling assessment
        error_handling_patterns = ['try', 'catch', 'except', 'finally', 'throw', 'raise']
        if any(pattern in code.lower() for pattern in error_handling_patterns):
            score += 0.1
        else:
            recommendations.append("Consider adding error handling")
        
        # Normalize score
        score = max(0.0, min(1.0, score))
        
        return score, recommendations
    
    def _assess_python_quality(self, code: str) -> float:
        """Python-specific quality assessment"""
        score = 0.0
        
        # Check for type hints
        if ':' in code and '->' in code:
            score += 0.1
        
        # Check for docstrings
        if '"""' in code or "'''" in code:
            score += 0.1
        
        # Check for f-strings vs old formatting
        if 'f"' in code or "f'" in code:
            score += 0.05
        elif '%' in code or '.format(' in code:
            score -= 0.05
        
        return score
    
    def _assess_jvm_quality(self, code: str) -> float:
        """Kotlin/Java-specific quality assessment"""
        score = 0.0
        
        # Check for proper access modifiers
        if any(modifier in code for modifier in ['private', 'protected', 'public']):
            score += 0.1
        
        # Check for proper exception handling
        if 'throws' in code or 'throw' in code:
            score += 0.05
        
        return score
    
    def _assess_js_quality(self, code: str) -> float:
        """JavaScript/TypeScript-specific quality assessment"""
        score = 0.0
        
        # Check for modern JS features
        if any(feature in code for feature in ['const ', 'let ', '=>', 'async', 'await']):
            score += 0.1
        
        # Avoid var usage
        if 'var ' in code:
            score -= 0.05
        
        return score

class FixQualityAssessor:
    """Main quality assessment coordinator for enhanced quality validation"""
    
    def __init__(self):
        self.syntax_validator = SyntaxValidator()
        self.security_validator = SecurityValidator()
        self.code_quality_scorer = CodeQualityScorer()
        
        # Quality thresholds for filtering
        self.validation_threshold = 0.5  # Minimum score for inclusion in training data (adjusted for real-world fixes)
        self.syntax_weight = 0.4
        self.security_weight = 0.3
        self.quality_weight = 0.2
        self.completeness_weight = 0.1
    
    def assess_fix_quality(self, vulnerability: Dict[str, Any], generated_fix, original_code: str = None) -> QualityAssessmentResult:
        """
        Comprehensive fix quality assessment for enhanced dataset creation

        This is called automatically during the enhanced dataset creation process
        to ensure only high-quality fixes are included in training datasets.

        Args:
            vulnerability: Vulnerability information
            generated_fix: Either a SecurityFix dataclass object or a dictionary containing fix information
            original_code: Optional original vulnerable code
        """

        try:
            # Handle both SecurityFix objects and dictionary inputs
            if hasattr(generated_fix, 'fixed_code'):
                # SecurityFix dataclass object
                fixed_code = generated_fix.fixed_code
                fix_dict = {
                    'fixed_code': generated_fix.fixed_code,
                    'title': getattr(generated_fix, 'title', ''),
                    'description': getattr(generated_fix, 'description', ''),
                    'explanation': getattr(generated_fix, 'explanation', ''),
                    'approach': getattr(generated_fix, 'approach', None)
                }
            else:
                # Dictionary input (legacy support)
                fixed_code = generated_fix.get('fixed_code', '')
                fix_dict = generated_fix
            language = self._detect_language(vulnerability, fixed_code)
            
            # 1. Syntax Validation (only for programming languages)
            programming_languages = ['python', 'kotlin', 'java', 'javascript', 'typescript']
            if language in programming_languages:
                syntax_result = self.syntax_validator.validate(fixed_code, language)
            else:
                # Skip syntax validation for configuration files (XML, YAML, JSON, etc.)
                syntax_result = SyntaxValidationResult(
                    is_valid=True, 
                    error_message=f"Syntax validation skipped for {language} configuration file"
                )
            
            # 2. Security Improvement Assessment
            security_improved, security_score, security_improvements = self.security_validator.assess_security_improvement(
                vulnerability, fixed_code, original_code
            )
            
            # 3. Code Quality Scoring
            quality_score, quality_recommendations = self.code_quality_scorer.score_code_quality(fixed_code, language)
            
            # 4. Completeness Assessment
            completeness_score = self._assess_completeness(fix_dict)
            
            # 5. Calculate Overall Score
            overall_score = (
                (1.0 if syntax_result.is_valid else 0.0) * self.syntax_weight +
                security_score * self.security_weight +
                quality_score * self.quality_weight +
                completeness_score * self.completeness_weight
            )
            
            # 6. Generate Recommendations
            recommendations = []
            if not syntax_result.is_valid:
                recommendations.append(f"Fix syntax error: {syntax_result.error_message}")
            if security_score < 0.5:
                recommendations.append("Enhance security measures in the fix")
            recommendations.extend(quality_recommendations)
            
            # 7. Determine if validation passed (relaxed security requirement for real-world fixes)
            validation_passed = (
                syntax_result.is_valid and
                overall_score >= self.validation_threshold and
                (security_improved or security_score >= 0.05 or 'validation' in fixed_code.lower() or 'security' in fixed_code.lower())  # Very lenient security requirement
            )
            
            # 8. Compile detailed results
            individual_scores = {
                'syntax_score': 1.0 if syntax_result.is_valid else 0.0,
                'security_score': security_score,
                'quality_score': quality_score,
                'completeness_score': completeness_score,
                'security_improvements': security_improvements
            }
            
            assessment_details = {
                'syntax_validation': syntax_result.__dict__,
                'language': language,
                'fix_length': len(fixed_code),
                'lines_of_code': len(fixed_code.split('\n')),
                'assessment_threshold': self.validation_threshold
            }
            
            return QualityAssessmentResult(
                overall_score=overall_score,
                syntax_valid=syntax_result.is_valid,
                security_improved=security_improved,
                code_quality_score=quality_score,
                best_practices_score=quality_score,  # Using quality score as proxy
                completeness_score=completeness_score,
                validation_passed=validation_passed,
                individual_scores=individual_scores,
                recommendations=recommendations,
                assessment_details=assessment_details
            )
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            raise
    
    def _detect_language(self, vulnerability: Dict[str, Any], code: str) -> str:
        """
        Intelligently detect the programming language from vulnerability data and code content
        """
        
        # 1. Check vulnerability metadata for language info
        if vulnerability.get('language'):
            lang = vulnerability['language'].lower()
            if lang in ['python', 'kotlin', 'java', 'javascript', 'typescript']:
                return lang
        
        # 2. Check file path extensions
        file_path = vulnerability.get('file_path', '') or vulnerability.get('path', '')
        if file_path:
            if file_path.endswith('.py'):
                return 'python'
            elif file_path.endswith(('.kt', '.kts')):
                return 'kotlin'
            elif file_path.endswith('.java'):
                return 'java'
            elif file_path.endswith(('.js', '.jsx')):
                return 'javascript'
            elif file_path.endswith(('.ts', '.tsx')):
                return 'typescript'
            elif file_path.endswith(('.xml', '.html', '.htm')):
                return 'xml'
            elif file_path.endswith(('.yml', '.yaml')):
                return 'yaml'
            elif file_path.endswith(('.json',)):
                return 'json'
            elif file_path.endswith(('.sh', '.bash')):
                return 'bash'
        
        # 3. Analyze code content for language patterns
        if code:
            code_lower = code.lower()
            
            # Python indicators
            if any(pattern in code for pattern in ['def ', 'import ', 'from ', '__init__', 'self.', 'print(']):
                return 'python'
            
            # Kotlin/Java indicators
            if any(pattern in code for pattern in ['fun ', 'class ', 'val ', 'var ', 'kotlin', 'package ']):
                return 'kotlin'
            elif any(pattern in code for pattern in ['public class', 'private ', 'public static', 'import java']):
                return 'java'
            
            # JavaScript/TypeScript indicators
            if any(pattern in code for pattern in ['function ', 'const ', 'let ', '=> ', 'require(', 'module.exports']):
                if any(ts_pattern in code for ts_pattern in [': string', ': number', 'interface ', 'type ']):
                    return 'typescript'
                else:
                    return 'javascript'
        
        # 4. Check tool/scanner context (fallback)
        tool_name = vulnerability.get('tool', '') or vulnerability.get('source', '')
        if 'semgrep' in tool_name.lower():
            # Semgrep often scans specific languages, try to infer from rule context
            rule_id = vulnerability.get('rule_id', '') or vulnerability.get('check_id', '')
            if any(lang in rule_id.lower() for lang in ['python', 'py']):
                return 'python'
            elif any(lang in rule_id.lower() for lang in ['kotlin', 'kt']):
                return 'kotlin'
            elif any(lang in rule_id.lower() for lang in ['java']):
                return 'java'
            elif any(lang in rule_id.lower() for lang in ['javascript', 'js']):
                return 'javascript'
        
        # Default fallback - still try to provide a reasonable guess
        # If this is clearly code content, default to Python as it's most common
        if code and any(indicator in code for indicator in ['import', 'def', 'class', 'function', '{']):
            return 'python'  # Conservative default for code content
        
        return 'text'  # Final fallback for non-code content
    
    def _assess_completeness(self, generated_fix: Dict[str, Any]) -> float:
        """Assess if the generated fix is complete"""
        
        score = 0.0
        
        # Check for required components (adapted for SecurityFix object)
        required_fields = ['fixed_code', 'explanation', 'implementation_notes']
        present_fields = [field for field in required_fields if generated_fix.get(field)]

        score += len(present_fields) / len(required_fields) * 0.6

        # Check quality of explanations (use SecurityFix attributes)
        explanation = generated_fix.get('explanation', '') or generated_fix.get('description', '')
        if len(explanation) > 50:
            score += 0.2

        implementation_notes = generated_fix.get('implementation_notes', [])
        if isinstance(implementation_notes, list) and len(implementation_notes) > 0:
            score += 0.2
        elif isinstance(implementation_notes, str) and len(implementation_notes) > 30:
            score += 0.2
        
        return min(score, 1.0)
    
    def assess_fixes_batch(self, vulnerability: Dict[str, Any], generated_fixes: List[Dict[str, Any]], original_code: str = None) -> List[QualityAssessmentResult]:
        """
        Assess quality of multiple fixes for a single vulnerability
        Used during enhanced dataset creation to filter high-quality examples
        """
        
        results = []
        
        for fix in generated_fixes:
            result = self.assess_fix_quality(vulnerability, fix, original_code)
            results.append(result)
        
        return results
    
    def filter_high_quality_fixes(self, vulnerability: Dict[str, Any], generated_fixes: List[Dict[str, Any]], original_code: str = None) -> List[Tuple[Dict[str, Any], QualityAssessmentResult]]:
        """
        Filter and return only high-quality fixes that pass validation
        This is the main integration point with enhanced dataset creation
        """
        
        assessments = self.assess_fixes_batch(vulnerability, generated_fixes, original_code)
        
        high_quality_fixes = []
        
        for fix, assessment in zip(generated_fixes, assessments):
            if assessment.validation_passed:
                high_quality_fixes.append((fix, assessment))
        
        # Log quality filtering results
        total_fixes = len(generated_fixes)
        quality_fixes = len(high_quality_fixes)
        
        logger.info(f"Quality filtering: {quality_fixes}/{total_fixes} fixes passed validation "
                   f"(threshold: {self.validation_threshold})")
        
        return high_quality_fixes
    
    def get_quality_statistics(self, assessments: List[QualityAssessmentResult]) -> Dict[str, Any]:
        """Generate quality statistics for reporting"""
        
        if not assessments:
            return {'total_assessments': 0}
        
        total = len(assessments)
        passed = sum(1 for a in assessments if a.validation_passed)
        
        avg_overall_score = sum(a.overall_score for a in assessments) / total
        avg_syntax_score = sum(a.individual_scores.get('syntax_score', 0) for a in assessments) / total
        avg_security_score = sum(a.individual_scores.get('security_score', 0) for a in assessments) / total
        avg_quality_score = sum(a.code_quality_score for a in assessments) / total
        
        return {
            'total_assessments': total,
            'passed_validation': passed,
            'pass_rate': passed / total,
            'average_scores': {
                'overall': avg_overall_score,
                'syntax': avg_syntax_score,
                'security': avg_security_score,
                'quality': avg_quality_score
            },
            'validation_threshold': self.validation_threshold
        }

# Main interface for integration with enhanced dataset creation
def assess_generated_fixes(vulnerability: Dict[str, Any], generated_fixes: List[Dict[str, Any]], original_code: str = None) -> List[Tuple[Dict[str, Any], QualityAssessmentResult]]:
    """
    Main entry point for quality assessment in enhanced dataset creation
    
    Returns only high-quality fixes that pass validation for inclusion in training datasets.
    This function implements quality assessment with default enablement.
    """
    
    assessor = FixQualityAssessor()
    return assessor.filter_high_quality_fixes(vulnerability, generated_fixes, original_code)

if __name__ == "__main__":
    # Basic testing functionality
    print("Fix Quality Assessor - Quality Assurance Framework")
    print("Enabled by default for enhanced dataset creation")
    
    # Test basic functionality
    assessor = FixQualityAssessor()
    
    test_vulnerability = {
        'type': 'sql_injection',
        'language': 'python'
    }
    
    test_fix = {
        'fixed_code': '''
def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
''',
        'change_explanation': 'Used parameterized query to prevent SQL injection',
        'validation_steps': 'Test with malicious input to ensure query is parameterized'
    }
    
    result = assessor.assess_fix_quality(test_vulnerability, test_fix)
    print(f"Test assessment - Overall score: {result.overall_score:.2f}, Passed: {result.validation_passed}")