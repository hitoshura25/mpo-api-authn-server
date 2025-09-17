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
        self.output_dir = output_dir or Path("enhanced_datasets/code-aware-training")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def create_enhanced_dataset(self, vulnerabilities: List[Dict[str, Any]], 
                              dataset_name: Optional[str] = None) -> DatasetCreationResult:
        """
        Create enhanced dataset from vulnerability data.
        
        Args:
            vulnerabilities: List of vulnerability data from security tools
            dataset_name: Name for the dataset (auto-generated if None)
            
        Returns:
            DatasetCreationResult with enhanced training examples
        """
        try:
            self.logger.info(f"🚀 Creating enhanced dataset from {len(vulnerabilities)} vulnerabilities")
            
            enhanced_examples = []
            processed_count = 0
            failed_count = 0
            
            for vuln in vulnerabilities:
                try:
                    # NEW: Try URL-to-code mapping for URL-based vulnerabilities
                    url_mapped = enhance_vulnerability_with_url_mapping(vuln, self.url_mapper)
                    
                    # Extract code context (now works for URL-mapped vulnerabilities too)
                    extraction_result = self.extractor.extract_vulnerability_context(vuln)
                    
                    if not extraction_result.success:
                        # Only log warnings for unexpected failures, not dependency/infrastructure scanners
                        if "Dependency/infrastructure scanner" not in extraction_result.error_message:
                            self.logger.warning(f"⚠️ Failed to extract context for {vuln.get('check_id', 'unknown')}: {extraction_result.error_message}")
                        failed_count += 1
                        continue
                    
                    # Generate multiple fix approaches
                    fix_result = self.fix_generator.generate_fixes(vuln, extraction_result.code_context)
                    
                    if not fix_result.success:
                        self.logger.warning(f"⚠️ Failed to generate fixes for {vuln.get('check_id', 'unknown')}: {fix_result.error_message}")
                        failed_count += 1
                        continue
                    
                    # Create enhanced training examples (one per fix approach)
                    vuln_examples = self._create_training_examples_for_vulnerability(
                        vuln, extraction_result, fix_result
                    )
                    
                    enhanced_examples.extend(vuln_examples)
                    processed_count += 1
                    
                    if processed_count % 10 == 0:
                        self.logger.info(f"📊 Processed {processed_count} vulnerabilities, generated {len(enhanced_examples)} enhanced examples")
                
                except Exception as e:
                    self.logger.error(f"❌ Error processing vulnerability {vuln.get('check_id', 'unknown')}: {e}")
                    failed_count += 1
                    continue
            
            # Create dataset name if not provided
            if not dataset_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dataset_name = f"enhanced_security_dataset_{timestamp}"
            
            self.logger.info(f"✅ Enhanced dataset creation completed: {len(enhanced_examples)} examples from {processed_count} vulnerabilities")
            
            return DatasetCreationResult(
                success=True,
                enhanced_examples=enhanced_examples,
                original_examples_count=len(vulnerabilities),
                enhanced_examples_count=len(enhanced_examples),
                creation_metadata={
                    'dataset_name': dataset_name,
                    'vulnerabilities_processed': processed_count,
                    'vulnerabilities_failed': failed_count,
                    'enhancement_ratio': len(enhanced_examples) / len(vulnerabilities) if vulnerabilities else 0,
                    'created_at': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return DatasetCreationResult(
                success=False,
                error_message=f"Dataset creation failed: {e}"
            )
    
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
                'id': vulnerability.get('check_id', 'unknown'),
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
                'id': vulnerability.get('check_id', 'unknown'),
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
        
        approach_desc = approach_descriptions.get(approach, f"{approach.value.replace('_', ' ')} approach")
        
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
{fix.vulnerable_code}
```

## Fixed Code
```{vulnerability_context['language']}
{fix.fixed_code}
```

## Fix Explanation
{fix.explanation}

## Benefits
{chr(10).join(f'• {benefit}' for benefit in fix.benefits)}

## Implementation Notes
{chr(10).join(f'• {note}' for note in fix.implementation_notes)}

## Trade-offs
{chr(10).join(f'• {tradeoff}' for tradeoff in fix.trade_offs)}

## Security Impact
**Level**: {fix.security_impact}
**Complexity**: {fix.complexity_level}

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
{fix.vulnerable_code}

## Recommended Configuration
{fix.fixed_code}

## Remediation Guidance
{fix.explanation}

## Security Benefits
{chr(10).join(f'• {benefit}' for benefit in fix.benefits)}

## Implementation Steps
{chr(10).join(f'• {note}' for note in fix.implementation_notes)}

## Considerations
{chr(10).join(f'• {tradeoff}' for tradeoff in fix.trade_offs)}

## Risk Reduction
**Level**: {fix.security_impact}
**Complexity**: {fix.complexity_level}

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
                        f.write(json.dumps(jsonl_example, ensure_ascii=False) + '\n')
            
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
                            'fix_approaches': example.fix_approaches,
                            'code_examples': example.code_examples
                        }
                        for example in result.enhanced_examples
                    ]
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(dataset_dict, f, ensure_ascii=False, indent=2)
            
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"✅ Enhanced dataset saved to: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save enhanced dataset: {e}")
            return None
    
    def enhance_existing_dataset(self, existing_dataset_path: Path) -> DatasetCreationResult:
        """
        Enhance an existing training dataset by adding code-aware examples.
        
        Args:
            existing_dataset_path: Path to existing JSONL training dataset
            
        Returns:
            DatasetCreationResult with enhanced examples
        """
        try:
            self.logger.info(f"🔧 Enhancing existing dataset: {existing_dataset_path}")
            
            # Load existing examples
            existing_examples = []
            with open(existing_dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    example = json.loads(line.strip())
                    existing_examples.append(example)
            
            self.logger.info(f"📊 Loaded {len(existing_examples)} existing examples")
            
            # Try to extract vulnerability information from existing examples
            vulnerabilities = []
            for example in existing_examples:
                # Parse vulnerability ID from instruction
                instruction = example.get('instruction', '')
                if 'Vulnerability ID:' in instruction:
                    # Extract basic vulnerability info for enhancement
                    vuln_id = instruction.split('Vulnerability ID:')[1].split('\n')[0].strip()
                    
                    vulnerabilities.append({
                        'check_id': vuln_id,
                        'path': 'unknown',  # Will need to be inferred or provided
                        'start': {'line': 1, 'col': 1},
                        'extra': {
                            'message': example.get('response', '').split('\n')[0],
                            'severity': 'UNKNOWN'
                        }
                    })
            
            if not vulnerabilities:
                return DatasetCreationResult(
                    success=False,
                    error_message="No vulnerability information found in existing dataset"
                )
            
            # Create enhanced dataset
            return self.create_enhanced_dataset(vulnerabilities, 
                                              dataset_name=f"enhanced_{existing_dataset_path.stem}")
            
        except Exception as e:
            return DatasetCreationResult(
                success=False,
                error_message=f"Failed to enhance existing dataset: {e}"
            )


# Convenience functions
def create_enhanced_dataset_from_vulnerabilities(vulnerabilities: List[Dict[str, Any]], 
                                               output_dir: Optional[Path] = None,
                                               dataset_name: Optional[str] = None) -> DatasetCreationResult:
    """
    Convenience function to create enhanced dataset from vulnerabilities.
    
    Args:
        vulnerabilities: List of vulnerability data
        output_dir: Output directory for dataset
        dataset_name: Name for the dataset
        
    Returns:
        DatasetCreationResult
    """
    creator = EnhancedDatasetCreator(output_dir)
    return creator.create_enhanced_dataset(vulnerabilities, dataset_name)


def enhance_existing_training_data(existing_dataset_path: Path,
                                 output_dir: Optional[Path] = None) -> DatasetCreationResult:
    """
    Convenience function to enhance existing training dataset.
    
    Args:
        existing_dataset_path: Path to existing training dataset
        output_dir: Output directory for enhanced dataset
        
    Returns:
        DatasetCreationResult
    """
    creator = EnhancedDatasetCreator(output_dir)
    return creator.enhance_existing_dataset(existing_dataset_path)