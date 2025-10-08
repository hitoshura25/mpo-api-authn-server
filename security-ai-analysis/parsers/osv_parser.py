"""
Parse OSV Scanner dependency scan outputs
OSV Scanner format documented at: https://github.com/google/osv-scanner
"""
import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

def _parse_osv_json(filepath: str) -> List[Dict]:
    """
    Parse OSV Scanner JSON output

    Expected structure from OSV Scanner:
    {
        "results": [
            {
                "source": {
                    "path": "...",
                    "type": "lockfile"
                },
                "packages": [
                    {
                        "package": {
                            "name": "...",
                            "version": "...",
                            "ecosystem": "..."
                        },
                        "vulnerabilities": [
                            {
                                "id": "...",
                                "summary": "...",
                                "severity": [...]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    """
    # Graceful handling for optional tool execution
    if not Path(filepath).exists():
        logger.info(f"ℹ️ OSV Scanner file not found: {filepath}")
        logger.info("This is acceptable - OSV dependency scanning may not have been run")
        return []

    # Fail fast on corrupted existing files
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        vulnerabilities = []
        for result in data.get('results', []):
            source_path = result.get('source', {}).get('path', 'Unknown')
            source_type = result.get('source', {}).get('type', 'Unknown')
            
            for package in result.get('packages', []):
                pkg_info = package.get('package', {})
                pkg_name = pkg_info.get('name', 'Unknown')
                pkg_version = pkg_info.get('version', 'Unknown')
                ecosystem = pkg_info.get('ecosystem', 'Unknown')
                
                for vuln in package.get('vulnerabilities', []):
                    # Extract severity if available
                    severity = 'Unknown'
                    if 'severity' in vuln and vuln['severity']:
                        severity_info = vuln['severity'][0] if isinstance(vuln['severity'], list) else vuln['severity']
                        if isinstance(severity_info, dict):
                            severity = severity_info.get('score', 'Unknown')
                        else:
                            severity = str(severity_info)

                    # Extract fixed versions from affected ranges
                    fixed_versions = []
                    for affected in vuln.get('affected', []):
                        for range_obj in affected.get('ranges', []):
                            for event in range_obj.get('events', []):
                                if 'fixed' in event:
                                    fixed_versions.append(event['fixed'])

                    # Create vulnerability dict with all necessary data
                    vuln_dict = {
                        'tool': 'osv-scanner',
                        'id': vuln.get('id', 'Unknown'),
                        'summary': vuln.get('summary', 'No summary'),
                        'details': vuln.get('details', ''),
                        'severity': severity,
                        'package_name': pkg_name,
                        'package_version': pkg_version,
                        'ecosystem': ecosystem,
                        'source_path': source_path,
                        'source_type': source_type,
                        'path': source_path,  # Map source_path to path field for enhanced dataset creation
                        'start': {'line': 1},  # Minimal start field for enhanced dataset compatibility
                        'affected': vuln.get('affected', [])  # Include full affected data for fix generation
                    }

                    # Add fixed_version field if available (for simplified access)
                    if fixed_versions:
                        vuln_dict['fixed_version'] = ', '.join(fixed_versions)

                    vulnerabilities.append(vuln_dict)
        
        return vulnerabilities
    except Exception as e:
        logger.error(f"❌ CRITICAL: Corrupted OSV Scanner data in {filepath}: {e}")
        logger.error("🔍 File exists but is corrupted - indicates OSV Scanner tool malfunction requiring investigation")
        raise RuntimeError(f"Corrupted OSV Scanner data requires investigation: {e}") from e


def _code_context_to_dict(code_context) -> Dict:
    """Convert CodeContext dataclass to dict for JSON serialization."""
    return {
        'file_path': code_context.file_path,
        'language': code_context.language,
        'file_extension': code_context.file_extension,
        'vulnerability_line': code_context.vulnerability_line,
        'vulnerability_column': code_context.vulnerability_column,
        'vulnerable_code': code_context.vulnerable_code,
        'before_lines': code_context.before_lines,
        'after_lines': code_context.after_lines,
        'function_name': code_context.function_name,
        'function_context': code_context.function_context,
        'function_start_line': code_context.function_start_line,
        'function_end_line': code_context.function_end_line,
        'class_name': code_context.class_name,
        'class_context': code_context.class_context,
        'class_start_line': code_context.class_start_line,
        'extraction_type': getattr(code_context, 'extraction_type', 'code'),
        'extraction_success': True
    }


def _convert_fix_result_to_format(fix_result) -> Dict:
    """Convert FixGenerationResult to unified format."""
    if not fix_result.success or not fix_result.fixes:
        return {
            'confidence': 0.0,
            'description': 'No fix available',
            'fixed_code': '',
            'explanation': '',
            'alternatives': []
        }

    primary_fix = fix_result.fixes[0]
    confidence = fix_result.generation_metadata.get('confidence', 0.5)

    fix_data = {
        'confidence': confidence,
        'description': primary_fix.description,
        'fixed_code': primary_fix.fixed_code,
        'explanation': primary_fix.explanation,
        'alternatives': []
    }

    # Add dependency-specific fields if available
    # Note: SecurityFix doesn't have these attributes, but we can infer from metadata
    if 'ecosystem' in fix_result.generation_metadata:
        # Extract from description (format: "Upgrade PACKAGE from VERSION to VERSION")
        desc = primary_fix.description
        if ' from ' in desc and ' to ' in desc:
            parts = desc.split(' from ')
            if len(parts) == 2:
                package_part = parts[0].replace('Upgrade ', '').strip()
                version_parts = parts[1].split(' to ')
                if len(version_parts) == 2:
                    fix_data['package'] = package_part
                    fix_data['from_version'] = version_parts[0].strip()
                    fix_data['to_version'] = version_parts[1].strip()
                    fix_data['ecosystem'] = fix_result.generation_metadata['ecosystem']

    # Add fixed_versions if available
    if 'fixed_versions' in fix_result.generation_metadata:
        fix_data['available_versions'] = fix_result.generation_metadata['fixed_versions']

    # Add alternatives
    for alt_fix in fix_result.fixes[1:]:
        fix_data['alternatives'].append({
            'description': alt_fix.description,
            'fixed_code': alt_fix.fixed_code,
            'explanation': alt_fix.explanation
        })

    return fix_data

def parse_osv_json_enhanced(filepath: str) -> List[Dict]:
    """
    Parse OSV Scanner JSON with enhanced fix generation and code context.

    This function implements the enhanced parsing architecture:
    1. Parse OSV data
    2. Categorize vulnerabilities
    3. Extract code context (optional for dependencies)
    4. Generate fixes using MultiApproachFixGenerator

    Returns vulnerabilities in unified training-ready format with:
    - security_category and category_confidence
    - code_context (if available)
    - fix with confidence, description, fixed_code, explanation, alternatives
    """
    # Import here to avoid circular dependencies
    from multi_approach_fix_generator import MultiApproachFixGenerator
    from vulnerable_code_extractor import VulnerableCodeExtractor
    from vulnerability_categorizer import VulnerabilityCategorizor

    # Parse base vulnerabilities
    vulnerabilities = _parse_osv_json(filepath)

    if not vulnerabilities:
        return []

    # Initialize helpers
    fix_generator = MultiApproachFixGenerator()
    code_extractor = VulnerableCodeExtractor()
    categorizer = VulnerabilityCategorizor()

    logger.info(f"🔧 Enhanced OSV parsing: Processing {len(vulnerabilities)} vulnerabilities")

    enriched_vulns = []
    for vuln in vulnerabilities:
        try:
            # Step 1: Categorization
            category, confidence = categorizer.categorize_vulnerability(vuln)
            vuln['security_category'] = category
            vuln['category_confidence'] = confidence

            # Step 2: Code context extraction (optional for dependencies)
            extraction_result = code_extractor.extract_vulnerability_context(vuln)
            if extraction_result.success and extraction_result.code_context:
                vuln['code_context'] = _code_context_to_dict(extraction_result.code_context)
            else:
                # For dependencies without code context, create minimal context
                vuln['code_context'] = {
                    'file_path': vuln.get('source_path', 'Unknown'),
                    'language': vuln.get('ecosystem', 'Maven').lower(),
                    'file_extension': '.gradle' if 'gradle' in vuln.get('source_path', '') else '.lock',
                    'vulnerable_code': f"{vuln.get('package_name', 'Unknown')}:{vuln.get('package_version', 'Unknown')}",
                    'extraction_type': 'dependency_file',
                    'extraction_success': False
                }

            # Step 3: Fix generation
            fix_result = fix_generator.generate_fixes(vuln, extraction_result.code_context if extraction_result.success else None)

            if fix_result.success and fix_result.fixes:
                vuln['fix'] = _convert_fix_result_to_format(fix_result)
            else:
                logger.warning(f"⚠️ Fix generation failed for {vuln.get('id', 'Unknown')}: {fix_result.error_message}")
                # Include error in output for debugging
                vuln['fix'] = {
                    'confidence': 0.0,
                    'description': f"Fix generation failed: {fix_result.error_message}",
                    'fixed_code': '',
                    'explanation': '',
                    'alternatives': []
                }

            enriched_vulns.append(vuln)

        except Exception as e:
            logger.error(f"❌ Error processing vulnerability {vuln.get('id', 'Unknown')}: {e}")
            # Include the vulnerability anyway with error marker
            vuln['processing_error'] = str(e)
            enriched_vulns.append(vuln)

    logger.info(f"✅ Enhanced OSV parsing complete: {len(enriched_vulns)} vulnerabilities enriched")
    return enriched_vulns