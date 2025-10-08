
import json
import logging
from typing import List, Dict

from vulnerable_code_extractor import VulnerableCodeExtractor
from multi_approach_fix_generator import MultiApproachFixGenerator

logger = logging.getLogger(__name__)

def parse_semgrep_json(filepath: str) -> List[Dict]:
    """
    Parse Semgrep JSON output files.
    """
    try:
        with open(filepath) as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {filepath}")
        return []

    findings = []
    code_extractor = VulnerableCodeExtractor()
    fix_generator = MultiApproachFixGenerator()

    for result in data.get('results', []):
        # Extract vulnerability info and add tool field for proper routing
        # VulnerableCodeExtractor will handle path resolution intelligently
        extraction_result = code_extractor.extract_vulnerability_context(vulnerability={
            'file_path': result.get('path'),  # Let extractor resolve the path
            'path': result.get('path'),
            'start': result.get('start'),
            'tool': 'semgrep'  # Add tool field for routing
        })

        code_context_dict = None
        if extraction_result.success and extraction_result.code_context:
            code_context_dict = {
                'file_path': extraction_result.code_context.file_path,
                'language': extraction_result.code_context.language,
                'file_extension': extraction_result.code_context.file_extension,
                'vulnerability_line': extraction_result.code_context.vulnerability_line,
                'vulnerability_column': extraction_result.code_context.vulnerability_column,
                'vulnerable_code': extraction_result.code_context.vulnerable_code,
                'before_lines': extraction_result.code_context.before_lines,
                'after_lines': extraction_result.code_context.after_lines,
                'function_name': extraction_result.code_context.function_name,
                'function_context': extraction_result.code_context.function_context,
                'function_start_line': extraction_result.code_context.function_start_line,
                'function_end_line': extraction_result.code_context.function_end_line,
                'class_name': extraction_result.code_context.class_name,
                'class_context': extraction_result.code_context.class_context,
                'class_start_line': extraction_result.code_context.class_start_line,
                'extraction_type': getattr(extraction_result.code_context, 'extraction_type', 'code'),
                'extraction_success': True
            }

        # Add tool field to result for proper routing in MultiApproachFixGenerator
        result_with_tool = {
            **result,
            'tool': 'semgrep',
            'check_id': result.get('check_id'),  # Ensure check_id is preserved
            'extra': result.get('extra', {})
        }

        fix_result = fix_generator.generate_fixes(result_with_tool, extraction_result.code_context)

        fix_object = None
        if fix_result.success and fix_result.fixes:
            primary_fix = fix_result.fixes[0]
            fix_object = {
                "confidence": fix_result.generation_metadata.get('confidence', 0.7),
                "description": primary_fix.description,
                "fixed_code": primary_fix.fixed_code,
                "explanation": primary_fix.explanation,
                "alternatives": [
                    {
                        "description": alt_fix.description,
                        "fixed_code": alt_fix.fixed_code,
                        "explanation": alt_fix.explanation
                    }
                    for alt_fix in fix_result.fixes[1:]
                ]
            }

        finding = {
            'tool': 'semgrep',
            'id': result.get('check_id'),
            'file_path': result.get('path'),
            'path': result.get('path'),
            'start': result.get('start'),
            'end': result.get('end'),
            'message': result.get('extra', {}).get('message'),
            'severity': result.get('extra', {}).get('severity'),
            'code_context': code_context_dict,
            'fix': fix_object,
            'cwe': result.get('extra', {}).get('metadata', {}).get('cwe'),
            'owasp': result.get('extra', {}).get('metadata', {}).get('owasp'),
            'confidence': result.get('extra', {}).get('metadata', {}).get('confidence'),
            'likelihood': result.get('extra', {}).get('metadata', {}).get('likelihood'),
            'impact': result.get('extra', {}).get('metadata', {}).get('impact'),
            'technology': result.get('extra', {}).get('metadata', {}).get('technology'),
            'references': result.get('extra', {}).get('metadata', {}).get('references'),
            'tool_name': 'Semgrep',
            'tool_version': data.get('version'),
            'security_category': 'code_vulnerability',
            'category_confidence': 0.7,
            'fix_complexity': 'high',
        }
        findings.append(finding)

    return findings
