#!/usr/bin/env python3
"""
Sequential Dataset Creator for Phase 3: Sequential Fine-Tuning

This module creates specialized datasets for multi-stage fine-tuning:
- Stage 1: Vulnerability Analysis Specialist
- Stage 2: Code Fix Generation Specialist

The sequential approach builds domain expertise progressively,
with Stage 2 models building upon Stage 1 analysis capabilities.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, NamedTuple
from dataclasses import dataclass, field

from enhanced_dataset_creator import EnhancedDatasetCreator, EnhancedTrainingExample
from vulnerable_code_extractor import VulnerableCodeExtractor
from multi_approach_fix_generator import MultiApproachFixGenerator


@dataclass
class SequentialDatasetResult:
    """Result of sequential dataset creation."""
    success: bool
    stage1_examples: List[EnhancedTrainingExample] = field(default_factory=list)
    stage2_examples: List[EnhancedTrainingExample] = field(default_factory=list)
    stage1_count: int = 0
    stage2_count: int = 0
    processing_errors: List[str] = field(default_factory=list)
    total_processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SequentialDatasetCreator:
    """
    Creates specialized datasets for sequential fine-tuning stages.
    
    Stage 1: Vulnerability Analysis Focus
    - Input: Raw vulnerability data 
    - Output: Detailed analysis, classification, impact assessment
    - Goal: Create vulnerability analysis specialist
    
    Stage 2: Code Fix Generation Focus  
    - Input: Vulnerability + Stage 1 analysis
    - Output: Specific code fixes, implementation details
    - Goal: Create code fix generation specialist
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize sequential dataset creator."""
        self.project_root = project_root or Path.cwd()
        self.code_extractor = VulnerableCodeExtractor()
        self.fix_generator = MultiApproachFixGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Enhanced dataset creator for base functionality
        self.enhanced_creator = EnhancedDatasetCreator(project_root)
    
    def create_sequential_datasets(self, vulnerabilities: List[Dict[str, Any]], 
                                 dataset_name: Optional[str] = None) -> SequentialDatasetResult:
        """
        Create specialized datasets for sequential fine-tuning.
        
        Args:
            vulnerabilities: List of vulnerability data
            dataset_name: Optional name for the datasets
            
        Returns:
            SequentialDatasetResult with Stage 1 and Stage 2 datasets
        """
        start_time = datetime.now()
        processing_errors = []
        
        try:
            if not dataset_name:
                timestamp = start_time.strftime("%Y%m%d_%H%M%S")
                dataset_name = f"sequential_training_{timestamp}"
            
            self.logger.info(f"🎯 Creating sequential datasets: {dataset_name}")
            self.logger.info(f"   Processing {len(vulnerabilities)} vulnerabilities")
            
            # Stage 1: Vulnerability Analysis Dataset
            stage1_examples = self._create_stage1_analysis_dataset(vulnerabilities)
            self.logger.info(f"   Stage 1 examples created: {len(stage1_examples)}")
            
            # Stage 2: Code Fix Generation Dataset
            stage2_examples = self._create_stage2_codefix_dataset(vulnerabilities)
            self.logger.info(f"   Stage 2 examples created: {len(stage2_examples)}")
            
            # Calculate processing time
            total_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = SequentialDatasetResult(
                success=True,
                stage1_examples=stage1_examples,
                stage2_examples=stage2_examples,
                stage1_count=len(stage1_examples),
                stage2_count=len(stage2_examples),
                processing_errors=processing_errors,
                total_processing_time=total_time,
                metadata={
                    'dataset_name': dataset_name,
                    'creation_time': datetime.now().isoformat(),
                    'total_vulnerabilities': len(vulnerabilities),
                    'sequential_enhancement_approach': 'vulnerability_analysis_then_code_fixes'
                }
            )
            
            self.logger.info(f"✅ Sequential datasets created successfully")
            return result
            
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"❌ Sequential dataset creation failed: {e}")
            raise
    
    def _create_stage1_analysis_dataset(self, vulnerabilities: List[Dict[str, Any]]) -> List[EnhancedTrainingExample]:
        """
        Create Stage 1 dataset focusing on vulnerability analysis and classification.
        
        Goal: Train model to become vulnerability analysis specialist
        - Input: Raw vulnerability data
        - Output: Detailed analysis, classification, impact assessment
        """
        stage1_examples = []
        
        for vuln in vulnerabilities:
            try:
                # Extract context for vulnerability
                extraction_result = self.code_extractor.extract_vulnerability_context(vuln)
                
                # Create analysis-focused instruction
                instruction = self._create_stage1_instruction(vuln, extraction_result.code_context)
                
                # Create analysis-focused response
                response = self._create_stage1_response(vuln, extraction_result.code_context)
                
                # Create training example
                example = EnhancedTrainingExample(
                    instruction=instruction,
                    response=response,
                    metadata={
                        'vulnerability_id': vuln.get('id', 'unknown'),
                        'stage': 'analysis',
                        'training_focus': 'vulnerability_classification_and_impact',
                        'code_context_available': extraction_result.code_context is not None,
                        'vulnerability_type': vuln.get('vulnerability_type', 'unknown')
                    }
                )
                
                stage1_examples.append(example)
                
            except Exception as e:
                self.logger.warning(f"Failed to create Stage 1 example for {vuln.get('id', 'unknown')}: {e}")
                raise
        
        return stage1_examples
    
    def _create_stage2_codefix_dataset(self, vulnerabilities: List[Dict[str, Any]]) -> List[EnhancedTrainingExample]:
        """
        Create Stage 2 dataset focusing on code fix generation.
        
        Goal: Train model to become code fix generation specialist
        - Input: Vulnerability + analysis (from Stage 1)
        - Output: Specific code fixes, implementation details
        """
        stage2_examples = []
        
        for vuln in vulnerabilities:
            try:
                # Extract context for vulnerability
                extraction_result = self.code_extractor.extract_vulnerability_context(vuln)
                
                # Only create code fix examples for vulnerabilities with code context
                if extraction_result.code_context is not None:
                    # Generate multiple fix approaches
                    fix_result = self.fix_generator.generate_fixes(vuln, extraction_result.code_context)
                    
                    if fix_result.success and fix_result.fixes:
                        # Create code fix example for each approach
                        for fix in fix_result.fixes:
                            instruction = self._create_stage2_instruction(vuln, extraction_result.code_context, fix)
                            response = self._create_stage2_response(vuln, extraction_result.code_context, fix)
                            
                            example = EnhancedTrainingExample(
                                instruction=instruction,
                                response=response,
                                metadata={
                                    'vulnerability_id': vuln.get('id', 'unknown'),
                                    'stage': 'code_fix',
                                    'training_focus': 'code_fix_generation',
                                    'fix_approach': fix.approach.value,
                                    'language': extraction_result.code_context.language,
                                    'file_path': extraction_result.code_context.file_path
                                }
                            )
                            
                            stage2_examples.append(example)
                else:
                    # For infrastructure vulnerabilities, create configuration fix examples
                    fix_result = self.fix_generator.generate_fixes(vuln, None)
                    
                    if fix_result.success and fix_result.fixes:
                        # Create infrastructure fix example
                        fix = fix_result.fixes[0]  # Use first fix approach
                        instruction = self._create_stage2_infrastructure_instruction(vuln, fix)
                        response = self._create_stage2_infrastructure_response(vuln, fix)
                        
                        example = EnhancedTrainingExample(
                            instruction=instruction,
                            response=response,
                            metadata={
                                'vulnerability_id': vuln.get('id', 'unknown'),
                                'stage': 'infrastructure_fix',
                                'training_focus': 'infrastructure_configuration_fixes',
                                'fix_approach': fix.approach.value,
                                'infrastructure_type': vuln.get('file_path', 'unknown')
                            }
                        )
                        
                        stage2_examples.append(example)
                        
            except Exception as e:
                self.logger.warning(f"Failed to create Stage 2 example for {vuln.get('id', 'unknown')}: {e}")
                raise
        
        return stage2_examples
    
    def _create_stage1_instruction(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Create Stage 1 instruction focused on vulnerability analysis."""
        
        base_info = f"""Analyze this security vulnerability and provide comprehensive analysis:

**Vulnerability ID**: {vulnerability.get('id', 'unknown')}
**Tool**: {vulnerability.get('tool', 'unknown')}
**Severity**: {vulnerability.get('severity', 'unknown')}
**Description**: {vulnerability.get('description', vulnerability.get('message', 'No description'))}"""

        if code_context:
            base_info += f"""
**File**: {code_context.file_path}
**Language**: {code_context.language}"""
            
            if code_context.function_name:
                base_info += f"""
**Function**: {code_context.function_name}"""
            
            if code_context.vulnerable_code:
                base_info += f"""
**Vulnerable Code**:
```{code_context.language}
{code_context.vulnerable_code}
```"""
        else:
            base_info += f"""
**Component**: {vulnerability.get('file_path', 'unknown')}
**Type**: Infrastructure/Configuration vulnerability"""

        base_info += """

Provide detailed analysis including:
1. Vulnerability classification and type
2. Root cause analysis
3. Impact assessment (technical and business)
4. Attack vectors and exploitation scenarios
5. Risk level justification"""

        return base_info
    
    def _create_stage1_response(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Create Stage 1 response focused on vulnerability analysis."""
        
        vuln_id = vulnerability.get('id', 'unknown')
        severity = vulnerability.get('severity', 'unknown')
        
        # Classify vulnerability type
        vuln_type = self._classify_vulnerability_type(vulnerability, code_context)
        
        response = f"""# Vulnerability Analysis Report

## Classification
**Vulnerability Type**: {vuln_type}
**Severity Level**: {severity}
**Confidence**: High

## Root Cause Analysis"""

        if code_context:
            response += f"""
**Technical Root Cause**: {self._analyze_code_root_cause(vulnerability, code_context)}
**Code Location**: {code_context.file_path}"""
            
            if code_context.function_name:
                response += f"""
**Affected Function**: {code_context.function_name}"""
        else:
            response += f"""
**Infrastructure Root Cause**: {self._analyze_infrastructure_root_cause(vulnerability)}
**Affected Component**: {vulnerability.get('file_path', 'unknown')}"""

        response += f"""

## Impact Assessment
**Technical Impact**: {self._assess_technical_impact(vulnerability, code_context)}
**Business Impact**: {self._assess_business_impact(vulnerability, code_context)}
**Exploitability**: {self._assess_exploitability(vulnerability, code_context)}

## Attack Vectors
{self._identify_attack_vectors(vulnerability, code_context)}

## Risk Justification
{self._justify_risk_level(vulnerability, code_context)}"""

        return response
    
    def _create_stage2_instruction(self, vulnerability: Dict[str, Any], code_context: Any, fix: Any) -> str:
        """Create Stage 2 instruction focused on code fix generation."""
        
        instruction = f"""Generate a specific code fix for this vulnerability using {fix.approach.value} approach:

**Vulnerability Analysis**:
- ID: {vulnerability.get('id', 'unknown')}
- Type: {self._classify_vulnerability_type(vulnerability, code_context)}
- Severity: {vulnerability.get('severity', 'unknown')}

**Current Code**:
```{code_context.language}
{code_context.vulnerable_code}
```

**File**: {code_context.file_path}"""

        if code_context.function_name:
            instruction += f"""
**Function**: {code_context.function_name}"""

        instruction += f"""

**Fix Approach**: {fix.approach.value}
**Fix Strategy**: {fix.title}

Provide:
1. Complete fixed code implementation
2. Explanation of security improvements
3. Implementation steps
4. Validation and testing approach"""

        return instruction
    
    def _create_stage2_response(self, vulnerability: Dict[str, Any], code_context: Any, fix: Any) -> str:
        """Create Stage 2 response focused on code fix implementation."""
        
        response = f"""# Code Fix Implementation

## Fixed Code
```{code_context.language}
{fix.fixed_code}
```

## Security Improvements
{fix.explanation}

## Implementation Steps
{self._generate_implementation_steps(fix)}

## Key Changes Made"""

        # Extract key changes from the fix
        if hasattr(fix, 'key_changes'):
            for i, change in enumerate(fix.key_changes, 1):
                response += f"""
{i}. {change}"""
        else:
            response += """
1. Applied security best practices for this vulnerability type
2. Implemented proper input validation and sanitization
3. Added appropriate error handling and logging
4. Enhanced security controls and access restrictions"""

        response += f"""

## Validation Approach
- **Security Testing**: Verify the vulnerability is properly mitigated
- **Functionality Testing**: Ensure existing functionality remains intact
- **Performance Testing**: Confirm no significant performance degradation
- **Code Review**: Have security-aware developers review the changes

## Additional Security Considerations
- Monitor for similar vulnerabilities in other parts of the codebase
- Update security documentation and coding guidelines
- Consider implementing automated security testing for this vulnerability type"""

        return response
    
    def _create_stage2_infrastructure_instruction(self, vulnerability: Dict[str, Any], fix: Any) -> str:
        """Create Stage 2 instruction for infrastructure fixes."""
        
        return f"""Generate infrastructure security configuration fix for this vulnerability:

**Vulnerability Analysis**:
- ID: {vulnerability.get('id', 'unknown')}
- Component: {vulnerability.get('file_path', 'unknown')}
- Severity: {vulnerability.get('severity', 'unknown')}
- Description: {vulnerability.get('description', vulnerability.get('message', 'No description'))}

**Fix Approach**: {fix.approach.value}

Provide:
1. Secure configuration changes
2. Implementation instructions
3. Security validation steps
4. Deployment considerations"""
    
    def _create_stage2_infrastructure_response(self, vulnerability: Dict[str, Any], fix: Any) -> str:
        """Create Stage 2 response for infrastructure fixes."""
        
        return f"""# Infrastructure Security Fix

## Secure Configuration
{fix.fixed_code}

## Implementation Instructions
{self._generate_implementation_steps(fix)}

## Security Improvements
{fix.explanation}

## Validation Steps
1. **Configuration Validation**: Verify secure settings are properly applied
2. **Security Scanning**: Re-scan to confirm vulnerability is resolved
3. **Functional Testing**: Ensure services continue to operate correctly
4. **Monitoring Setup**: Implement monitoring for configuration drift

## Deployment Considerations
- Apply changes during maintenance window if service restart required
- Test in staging environment before production deployment
- Document configuration changes for audit trail
- Update infrastructure-as-code templates if applicable"""
    
    # Helper methods for analysis
    def _classify_vulnerability_type(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Classify vulnerability type based on available information."""
        vuln_id = vulnerability.get('id', '').lower()
        message = vulnerability.get('message', '').lower()
        
        if 'sql' in vuln_id or 'sql' in message:
            return 'SQL Injection'
        elif 'xss' in vuln_id or 'xss' in message:
            return 'Cross-Site Scripting (XSS)'
        elif 'csrf' in vuln_id or 'csrf' in message:
            return 'Cross-Site Request Forgery (CSRF)'
        elif 'auth' in vuln_id or 'auth' in message:
            return 'Authentication Bypass'
        elif 'permission' in vuln_id or 'permission' in message:
            return 'Permission/Authorization Issue'
        elif code_context is None:
            return 'Infrastructure/Configuration Vulnerability'
        else:
            return 'Security Misconfiguration'
    
    def _generate_implementation_steps(self, fix: Any) -> str:
        """Generate implementation steps from SecurityFix object."""
        
        # Generate steps based on fix approach and details
        steps = []
        
        # Step 1: Review the vulnerability
        steps.append("**Review Vulnerability**: Understand the security issue and its potential impact")
        
        # Step 2: Backup/prepare
        steps.append("**Backup Current Code**: Create backup or branch before making changes")
        
        # Step 3: Implement fix based on approach
        if hasattr(fix, 'approach'):
            approach_name = fix.approach.value if hasattr(fix.approach, 'value') else str(fix.approach)
            if 'input_validation' in approach_name.lower():
                steps.append("**Add Input Validation**: Implement proper input sanitization and validation")
            elif 'database' in approach_name.lower():
                steps.append("**Update Database Logic**: Implement secure database access patterns")
            elif 'authentication' in approach_name.lower():
                steps.append("**Enhance Authentication**: Strengthen authentication and authorization controls")
            else:
                steps.append(f"**Implement {approach_name} Fix**: Apply the specific security improvement")
        else:
            steps.append("**Apply Security Fix**: Implement the recommended security improvement")
        
        # Step 4: Test
        steps.append("**Test Implementation**: Verify the fix works correctly and doesn't break functionality")
        
        # Step 5: Security validation
        steps.append("**Security Validation**: Confirm the vulnerability is resolved through security testing")
        
        # Step 6: Deploy
        steps.append("**Deploy Safely**: Deploy changes using proper deployment procedures")
        
        # Format as numbered list
        formatted_steps = []
        for i, step in enumerate(steps, 1):
            formatted_steps.append(f"{i}. {step}")
        
        return "\n".join(formatted_steps)
    
    def _analyze_code_root_cause(self, vulnerability: Dict[str, Any], code_context: Any) -> str:
        """Analyze root cause for code vulnerabilities."""
        return f"Insecure coding practice in {code_context.language} implementation lacking proper security controls"
    
    def _analyze_infrastructure_root_cause(self, vulnerability: Dict[str, Any]) -> str:
        """Analyze root cause for infrastructure vulnerabilities."""
        return f"Insecure configuration in {vulnerability.get('file_path', 'unknown')} component"
    
    def _assess_technical_impact(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Assess technical impact of vulnerability."""
        severity = vulnerability.get('severity', 'unknown').upper()
        if severity in ['CRITICAL', 'HIGH']:
            return "High - Could lead to system compromise, data breach, or service disruption"
        elif severity == 'MEDIUM':
            return "Medium - Could allow unauthorized access or data manipulation"
        else:
            return "Low - Limited impact on system security or functionality"
    
    def _assess_business_impact(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Assess business impact of vulnerability."""
        severity = vulnerability.get('severity', 'unknown').upper()
        if severity in ['CRITICAL', 'HIGH']:
            return "High - Potential for data loss, compliance violations, or reputation damage"
        elif severity == 'MEDIUM':
            return "Medium - Risk of operational disruption or customer trust issues"
        else:
            return "Low - Minimal business risk with proper monitoring"
    
    def _assess_exploitability(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Assess how easily vulnerability can be exploited."""
        if code_context:
            return "Medium to High - Code-level vulnerabilities can be exploited with appropriate tooling"
        else:
            return "Low to Medium - Infrastructure vulnerabilities require system access"
    
    def _identify_attack_vectors(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Identify potential attack vectors."""
        if code_context:
            return """1. **Direct Code Exploitation**: Malicious input crafted to exploit the vulnerable code path
2. **Automated Scanning**: Vulnerability scanners identifying and exploiting the weakness
3. **Social Engineering**: Tricking users into triggering the vulnerable code"""
        else:
            return """1. **Configuration Exploitation**: Direct exploitation of misconfigured services
2. **Privilege Escalation**: Using misconfiguration to gain elevated access
3. **Lateral Movement**: Leveraging vulnerability to access other systems"""
    
    def _justify_risk_level(self, vulnerability: Dict[str, Any], code_context: Optional[Any]) -> str:
        """Justify the assigned risk level."""
        severity = vulnerability.get('severity', 'unknown').upper()
        return f"Risk level {severity} justified by combination of impact severity, exploitability, and business context"
    
    def save_sequential_datasets(self, result: SequentialDatasetResult, output_dir: Path) -> Dict[str, Path]:
        """
        Save sequential datasets to files.
        
        Returns:
            Dictionary mapping stage names to file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        dataset_name = result.metadata.get('dataset_name', 'sequential_training')
        
        # Save Stage 1 dataset
        stage1_file = output_dir / f"{dataset_name}_stage1_analysis.jsonl"
        stage1_data = [
            {
                "instruction": example.instruction,
                "response": example.response,
                "metadata": example.metadata
            }
            for example in result.stage1_examples
        ]
        
        with open(stage1_file, 'w') as f:
            for item in stage1_data:
                f.write(json.dumps(item) + '\n')
        
        # Save Stage 2 dataset
        stage2_file = output_dir / f"{dataset_name}_stage2_codefix.jsonl"
        stage2_data = [
            {
                "instruction": example.instruction,
                "response": example.response,
                "metadata": example.metadata
            }
            for example in result.stage2_examples
        ]
        
        with open(stage2_file, 'w') as f:
            for item in stage2_data:
                f.write(json.dumps(item) + '\n')
        
        # Save metadata
        metadata_file = output_dir / f"{dataset_name}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(result.metadata, f, indent=2)
        
        self.logger.info(f"✅ Sequential datasets saved:")
        self.logger.info(f"   Stage 1: {stage1_file}")
        self.logger.info(f"   Stage 2: {stage2_file}")
        self.logger.info(f"   Metadata: {metadata_file}")
        
        return {
            'stage1': stage1_file,
            'stage2': stage2_file,
            'metadata': metadata_file
        }

    def save_sequential_datasets_to_structured_paths(self, result: SequentialDatasetResult,
                                                   stage1_data_dir: Path,
                                                   stage2_data_dir: Path) -> Dict[str, Path]:
        """
        Save sequential datasets directly to structured training run directories.

        This method writes datasets directly to the correct structured locations,
        eliminating the need for copying from temporary directories.

        Args:
            result: SequentialDatasetResult to save
            stage1_data_dir: Directory for Stage 1 training data
            stage2_data_dir: Directory for Stage 2 training data

        Returns:
            Dictionary mapping stage names to saved file paths
        """
        # Ensure directories exist
        stage1_data_dir.mkdir(parents=True, exist_ok=True)
        stage2_data_dir.mkdir(parents=True, exist_ok=True)

        dataset_name = result.metadata.get('dataset_name', 'sequential_training')

        # Save Stage 1 dataset using manifest-defined filename
        stage1_file = stage1_data_dir / "analysis-dataset.jsonl"
        stage1_data = [
            {
                "instruction": example.instruction,
                "response": example.response,
                "metadata": example.metadata
            }
            for example in result.stage1_examples
        ]

        with open(stage1_file, 'w') as f:
            for item in stage1_data:
                f.write(json.dumps(item) + '\n')

        # Save Stage 2 dataset using manifest-defined filename
        stage2_file = stage2_data_dir / "codefix-dataset.jsonl"
        stage2_data = [
            {
                "instruction": example.instruction,
                "response": example.response,
                "metadata": example.metadata
            }
            for example in result.stage2_examples
        ]

        with open(stage2_file, 'w') as f:
            for item in stage2_data:
                f.write(json.dumps(item) + '\n')

        # Save metadata to Stage 1 directory (primary metadata location)
        metadata_file = stage1_data_dir / f"{dataset_name}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(result.metadata, f, indent=2)

        self.logger.info(f"✅ Sequential datasets saved to structured paths:")
        self.logger.info(f"   Stage 1: {stage1_file}")
        self.logger.info(f"   Stage 2: {stage2_file}")
        self.logger.info(f"   Metadata: {metadata_file}")

        return {
            'stage1': stage1_file,
            'stage2': stage2_file,
            'metadata': metadata_file
        }


def create_sequential_datasets_from_vulnerabilities(vulnerabilities: List[Dict[str, Any]], 
                                                   output_dir: Path,
                                                   dataset_name: Optional[str] = None) -> SequentialDatasetResult:
    """
    Convenience function to create sequential datasets from vulnerabilities.
    
    Args:
        vulnerabilities: List of vulnerability data
        output_dir: Directory to save datasets
        dataset_name: Optional name for datasets
        
    Returns:
        SequentialDatasetResult with creation results
    """
    creator = SequentialDatasetCreator()
    result = creator.create_sequential_datasets(vulnerabilities, dataset_name)
    
    if result.success:
        creator.save_sequential_datasets(result, output_dir)
    
    return result