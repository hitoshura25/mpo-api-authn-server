"""
Parse Checkov SARIF output files
Checkov is an Infrastructure-as-Code (IaC) security scanner
"""
import json
import logging
from typing import List, Dict

from vulnerable_code_extractor import VulnerableCodeExtractor
from multi_approach_fix_generator import MultiApproachFixGenerator

logger = logging.getLogger(__name__)

def _build_rule_lookup(rules: List[Dict]) -> Dict[str, Dict]:
    """
    Build a lookup dictionary of rule ID to rule metadata.

    Args:
        rules: List of rule objects from tool.driver.rules

    Returns:
        Dictionary mapping rule ID to rule metadata
    """
    rule_lookup = {}
    for rule in rules:
        rule_id = rule.get('id', '')
        if rule_id:
            rule_lookup[rule_id] = {
                'name': rule.get('name', ''),
                'shortDescription': rule.get('shortDescription', {}).get('text', ''),
                'fullDescription': rule.get('fullDescription', {}).get('text', ''),
                'help': rule.get('help', {}).get('text', ''),
                'level': rule.get('defaultConfiguration', {}).get('level', 'warning')
            }
    return rule_lookup


def _map_severity(level: str) -> str:
    """
    Map SARIF level to standard severity.

    Args:
        level: SARIF level (error/warning/note/info)

    Returns:
        Standard severity string
    """
    severity_map = {
        'error': 'HIGH',
        'warning': 'MEDIUM',
        'note': 'LOW',
        'none': 'INFO'
    }
    return severity_map.get(level.lower(), 'MEDIUM')


def _infer_config_type(file_path: str) -> str:
    """
    Infer the configuration type from file path.

    Args:
        file_path: Path to the configuration file

    Returns:
        Configuration type (github_actions, dockerfile, kubernetes, terraform, etc.)
    """
    file_path_lower = file_path.lower()

    if '.github/workflows' in file_path_lower:
        return 'github_actions'
    elif 'dockerfile' in file_path_lower or file_path_lower.endswith('.dockerfile'):
        return 'dockerfile'
    elif file_path_lower.endswith(('.yaml', '.yml')) and 'k8s' in file_path_lower:
        return 'kubernetes'
    elif file_path_lower.endswith('.tf'):
        return 'terraform'
    elif file_path_lower.endswith(('.yaml', '.yml')):
        return 'yaml_config'
    else:
        return 'config'


def parse_checkov_sarif(filepath: str) -> List[Dict]:
    """
    Parse Checkov SARIF output and extract configuration security findings.

    Args:
        filepath: Path to the Checkov SARIF file

    Returns:
        List of vulnerability dictionaries in unified format
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

    # Extract tool information
    runs = data.get('runs', [])
    if not runs:
        logger.warning(f"No runs found in Checkov SARIF file: {filepath}")
        return []

    run = runs[0]
    tool_info = run.get('tool', {}).get('driver', {})
    tool_name = tool_info.get('name', 'Checkov')
    tool_version = tool_info.get('version', 'Unknown')

    # Validate it's Checkov output
    if tool_name != 'Checkov':
        logger.warning(f"Expected Checkov output, got {tool_name}")
        return []

    # Build rule lookup for metadata
    rules = tool_info.get('rules', [])
    rule_lookup = _build_rule_lookup(rules)

    # Process results
    results = run.get('results', [])

    for result in results:
        rule_id = result.get('ruleId', 'Unknown')
        level = result.get('level', 'warning')
        message = result.get('message', {}).get('text', 'No message provided')

        # Get rule metadata
        rule_info = rule_lookup.get(rule_id, {})
        rule_name = rule_info.get('name', message)
        help_text = rule_info.get('help', '')

        # Extract location information
        locations = result.get('locations', [])
        if not locations:
            continue

        location = locations[0]
        physical_location = location.get('physicalLocation', {})
        artifact_location = physical_location.get('artifactLocation', {})
        region = physical_location.get('region', {})

        file_path = artifact_location.get('uri', 'Unknown')
        start_line = region.get('startLine', 1)
        end_line = region.get('endLine', start_line)

        # Infer config type from file path
        config_type = _infer_config_type(file_path)

        # Extract code context using VulnerableCodeExtractor
        extraction_result = code_extractor.extract_vulnerability_context(vulnerability={
            'file_path': file_path,
            'path': file_path,
            'start': {'line': start_line},
            'end': {'line': end_line},
            'tool': 'checkov'
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
                'extraction_type': getattr(extraction_result.code_context, 'extraction_type', 'code'),
                'extraction_success': True
            }

        # Build vulnerability dict with tool field for routing
        vulnerability = {
            'tool': 'checkov',
            'id': rule_id,
            'rule_name': rule_name,
            'message': message,
            'severity': _map_severity(level),
            'level': level,
            'file_path': file_path,
            'path': file_path,
            'start': {'line': start_line},
            'end': {'line': end_line},
            'short_description': rule_info.get('shortDescription', message),
            'full_description': rule_info.get('fullDescription', message),
            'help_text': help_text,
            'config_type': config_type,
        }

        # Generate fix using MultiApproachFixGenerator
        fix_result = fix_generator.generate_fixes(vulnerability, extraction_result.code_context if extraction_result.success else None)

        fix_object = None
        if fix_result.success and fix_result.fixes:
            primary_fix = fix_result.fixes[0]
            fix_object = {
                "confidence": fix_result.generation_metadata.get('confidence', 0.8),
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
            'tool': 'checkov',
            'id': rule_id,
            'rule_name': rule_name,
            'message': message,
            'severity': _map_severity(level),
            'level': level,
            'file_path': file_path,
            'path': file_path,
            'start': {'line': start_line},
            'end': {'line': end_line},
            'short_description': rule_info.get('shortDescription', message),
            'full_description': rule_info.get('fullDescription', message),
            'help_text': help_text,
            'code_context': code_context_dict,
            'fix': fix_object,
            'tool_name': tool_name,
            'tool_version': tool_version,
            'security_category': 'configuration_security',
            'category_confidence': 0.9,
            'config_type': config_type,
            'fix_complexity': 'low',  # Config changes are typically straightforward
        }
        findings.append(finding)

    return findings
