"""
Parse OWASP ZAP scan outputs
ZAP JSON format documented at: https://www.zaproxy.org/docs/desktop/ui/reports/
"""
import json
import logging
import re
from pathlib import Path
from typing import List, Dict

from multi_approach_fix_generator import MultiApproachFixGenerator

logger = logging.getLogger(__name__)


def _strip_html_tags(html_text: str) -> str:
    """
    Remove HTML tags from ZAP descriptions/solutions.

    ZAP returns descriptions and solutions with HTML formatting.
    This function strips the HTML tags for clean text.
    """
    if not html_text:
        return ""

    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', html_text)

    # Decode common HTML entities
    clean = clean.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    clean = clean.replace('&quot;', '"').replace('&#x27;', "'")

    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()

    return clean


def parse_zap_json(filepath: str) -> List[Dict]:
    """
    Parse OWASP ZAP JSON report output

    Expected ZAP JSON structure:
    {
        "@programName": "ZAP",
        "@version": "...",
        "site": [
            {
                "@name": "...",
                "@host": "...",
                "@port": "...",
                "alerts": [
                    {
                        "pluginid": "...",
                        "alert": "...",
                        "riskcode": "...",
                        "confidence": "...",
                        "riskdesc": "...",
                        "desc": "...",
                        "instances": [...]
                    }
                ]
            }
        ]
    }
    """
    # Graceful handling for optional tool execution
    if not Path(filepath).exists():
        logger.info(f"ℹ️ ZAP scan file not found: {filepath}")
        logger.info("This is acceptable - ZAP web application scanning may not have been run")
        return []

    # Fail fast on corrupted existing files
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        findings = []
        zap_version = data.get('@version', 'Unknown')
        fix_generator = MultiApproachFixGenerator()

        # Risk mapping
        risk_map = {
            '0': 'INFO',
            '1': 'LOW',
            '2': 'MEDIUM',
            '3': 'HIGH'
        }

        for site in data.get('site', []):
            site_name = site.get('@name', 'Unknown')
            site_host = site.get('@host', 'Unknown')
            site_port = site.get('@port', 'Unknown')

            for alert in site.get('alerts', []):
                risk_code = str(alert.get('riskcode', '0'))
                severity = risk_map.get(risk_code, 'UNKNOWN')

                # Count instances
                instances = alert.get('instances', [])
                instance_count = len(instances)

                # Extract first instance details if available
                first_instance = instances[0] if instances else {}
                uri = first_instance.get('uri', site_name)
                method = first_instance.get('method', 'Unknown')

                # Strip HTML from description and solution
                clean_description = _strip_html_tags(alert.get('desc', 'No description'))
                clean_solution = _strip_html_tags(alert.get('solution', 'No solution provided'))
                clean_reference = _strip_html_tags(alert.get('reference', ''))

                # Build vulnerability dict with tool field for routing
                vulnerability = {
                    'tool': 'zap',
                    'id': alert.get('pluginid', 'Unknown'),
                    'alert_ref': alert.get('alertRef', 'Unknown'),
                    'alert': alert.get('alert', 'Unknown'),
                    'name': alert.get('alert', 'Unknown'),
                    'severity': severity,
                    'risk_code': risk_code,
                    'confidence': alert.get('confidence', 'Unknown'),
                    'risk_desc': alert.get('riskdesc', 'Unknown'),
                    'description': clean_description,
                    'message': clean_description,  # Alias for compatibility
                    'solution': clean_solution,
                    'reference': clean_reference,
                    'cwe': alert.get('cweid', ''),
                    'wasc': alert.get('wascid', ''),
                    'site_host': site_host,
                    'site_port': site_port,
                    'uri': uri,
                    'url': uri,
                    'method': method,
                    'instances': instances,
                    'instance_count': instance_count,
                    'path': uri,  # For compatibility
                    'start': {'line': 1},  # Minimal start field
                }

                # Generate fix using MultiApproachFixGenerator
                # Note: ZAP findings are HTTP-level, so no code context available
                fix_result = fix_generator.generate_fixes(vulnerability, code_context=None)

                fix_object = None
                if fix_result.success and fix_result.fixes:
                    primary_fix = fix_result.fixes[0]
                    fix_object = {
                        "confidence": fix_result.generation_metadata.get('confidence', 0.9),
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
                    'tool': 'zap',
                    'id': alert.get('pluginid', 'Unknown'),
                    'alert_ref': alert.get('alertRef', 'Unknown'),
                    'alert': alert.get('alert', 'Unknown'),
                    'name': alert.get('alert', 'Unknown'),
                    'severity': severity,
                    'risk_code': risk_code,
                    'confidence': alert.get('confidence', 'Unknown'),
                    'risk_desc': alert.get('riskdesc', 'Unknown'),
                    'message': clean_description,
                    'description': clean_description,
                    'solution': clean_solution,
                    'reference': clean_reference,
                    'cwe': alert.get('cweid', ''),
                    'wasc': alert.get('wascid', ''),
                    'site_host': site_host,
                    'site_port': site_port,
                    'uri': uri,
                    'url': uri,
                    'method': method,
                    'instances': instances,
                    'instance_count': instance_count,
                    'path': uri,
                    'start': {'line': 1},
                    'code_context': None,  # ZAP is HTTP-level, no source code context
                    'fix': fix_object,
                    'tool_name': 'ZAP',
                    'tool_version': zap_version,
                    'security_category': 'web_security',
                    'category_confidence': 0.9,
                    'fix_complexity': 'low',  # HTTP header configuration is typically simple
                }
                findings.append(finding)

        return findings
    except Exception as e:
        logger.error(f"❌ CRITICAL: Corrupted ZAP scan data in {filepath}: {e}")
        logger.error("🔍 File exists but is corrupted - indicates ZAP tool malfunction requiring investigation")
        raise RuntimeError(f"Corrupted ZAP scan data requires investigation: {e}") from e