
import json
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def parse_trivy_sarif(filepath: str) -> List[Dict]:
    """
    Parse Trivy SARIF files and extract dependency vulnerability findings
    with structured package upgrade information.
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
    for run in data.get('runs', []):
        if run.get('tool', {}).get('driver', {}).get('name', '').lower() != 'trivy':
            continue

        rules = {rule['id']: rule for rule in run.get('tool', {}).get('driver', {}).get('rules', [])}

        for result in run.get('results', []):
            rule_id = result.get('ruleId')
            rule = rules.get(rule_id, {})
            
            parsed_message = _parse_trivy_message(result.get('message', {}).get('text', ''))
            if not _should_include_vulnerability(parsed_message):
                continue

            location = result.get('locations', [{}])[0]
            artifact_uri = location.get('physicalLocation', {}).get('artifactLocation', {}).get('uri', '')
            
            finding = {
                'tool': 'trivy',
                'id': rule_id,
                'rule_name': rule.get('name'),
                'severity': _map_severity(result.get('level'), rule.get('properties', {}).get('security-severity')),
                'security_severity': rule.get('properties', {}).get('security-severity'),
                'level': result.get('level'),
                'package_name': parsed_message.get('package_name'),
                'installed_version': parsed_message.get('installed_version'),
                'fixed_version': parsed_message.get('fixed_version'),
                'package_ecosystem': _classify_package_ecosystem(parsed_message.get('package_name', ''), artifact_uri),
                'file_path': artifact_uri,
                'path': artifact_uri,
                'artifact': artifact_uri,
                'start': {'line': 1},
                'message': result.get('message', {}).get('text', ''),
                'short_description': rule.get('shortDescription', {}).get('text'),
                'full_description': rule.get('fullDescription', {}).get('text'),
                'fix': _generate_fix_object(parsed_message, _classify_package_ecosystem(parsed_message.get('package_name', ''), artifact_uri)),
                'help_uri': rule.get('helpUri'),
                'cve_link': parsed_message.get('link'),
                'tool_name': 'Trivy',
                'tool_version': run.get('tool', {}).get('driver', {}).get('version'),
                'security_category': 'dependency_security',
                'category_confidence': 1.0,
                'fix_complexity': 'low',
                'tags': rule.get('properties', {}).get('tags', []),
            }
            findings.append(finding)
            
    return findings

def _parse_trivy_message(message_text: str) -> Dict[str, str]:
    fields = {}
    for line in message_text.split('\n'):
        line = line.strip()
        if line.startswith('Package:'):
            fields['package_name'] = line.replace('Package:', '').strip()
        elif line.startswith('Installed Version:'):
            fields['installed_version'] = line.replace('Installed Version:', '').strip()
        elif line.startswith('Vulnerability'):
            parts = line.split()
            if len(parts) >= 2:
                fields['cve_id'] = parts[1]
        elif line.startswith('Severity:'):
            fields['severity'] = line.replace('Severity:', '').strip()
        elif line.startswith('Fixed Version:'):
            fixed_ver = line.replace('Fixed Version:', '').strip()
            if '[' in fixed_ver:
                fixed_ver = fixed_ver.split('[')[0].strip()
            fields['fixed_version'] = fixed_ver.rstrip(',').strip()
        elif line.startswith('Link:'):
            match = re.search(r'\(([^)]+)\)', line)
            if match:
                fields['link'] = match.group(1)
    return fields

def _should_include_vulnerability(parsed_fields: Dict) -> bool:
    fixed_version = parsed_fields.get('fixed_version', '').strip()
    package_name = parsed_fields.get('package_name', '').strip()
    return bool(package_name and fixed_version)

def _classify_package_ecosystem(package_name: str, artifact_uri: str) -> str:
    if ':' in package_name:
        return 'maven'
    if '/' in package_name or package_name.startswith('@'):
        return 'npm'
    if artifact_uri.endswith('requirements.txt') or 'site-packages' in artifact_uri:
        return 'pip'
    if 'dockerfile://' in artifact_uri or artifact_uri.endswith('.tar'):
        if 'alpine' in artifact_uri.lower():
            return 'os_apk'
        return 'os_apt'
    return 'unknown'

def _generate_fix_object(fields: Dict, ecosystem: str) -> Dict:
    package = fields.get('package_name')
    installed = fields.get('installed_version')
    fixed_versions = fields.get('fixed_version', '').split(',')
    primary_fixed_version = fixed_versions[0].strip() if fixed_versions else None

    if not primary_fixed_version:
        return None

    description = f"Upgrade {package} from {installed} to {primary_fixed_version} to fix security vulnerability"
    fixed_code = _generate_dependency_upgrade_code(package, primary_fixed_version, ecosystem)
    explanation = f"The currently installed version {installed} of {package} is vulnerable. Upgrading to version {primary_fixed_version} will resolve the issue."
    
    alternatives = []
    if len(fixed_versions) > 1:
        for alt_version in fixed_versions[1:]:
            alt_version = alt_version.strip()
            alternatives.append({
                "description": f"Upgrade to {alt_version} if on a different release branch",
                "fixed_code": _generate_dependency_upgrade_code(package, alt_version, ecosystem),
                "explanation": f"For projects on a different release branch, upgrade to {alt_version} which also includes the security fix."
            })

    return {
        "confidence": 1.0,
        "description": description,
        "fixed_code": fixed_code,
        "explanation": explanation,
        "package": package,
        "from_version": installed,
        "to_version": primary_fixed_version,
        "ecosystem": ecosystem,
        "alternatives": alternatives
    }

def _generate_dependency_upgrade_code(package: str, version: str, ecosystem: str) -> str:
    if ecosystem == 'maven':
        return f'implementation("{package}:{version}")'
    elif ecosystem == 'npm':
        return f'"{package}": "^{version}"'
    elif ecosystem == 'pip':
        return f'{package}=={version}'
    else:
        return f'Upgrade {package} to version {version}'

def _map_severity(level: str, security_severity: Optional[str]) -> str:
    if security_severity:
        try:
            score = float(security_severity)
            if score >= 9.0:
                return 'CRITICAL'
            elif score >= 7.0:
                return 'HIGH'
            elif score >= 4.0:
                return 'MEDIUM'
            else:
                return 'LOW'
        except (ValueError, TypeError):
            pass
    level_map = {'error': 'HIGH', 'warning': 'MEDIUM', 'note': 'LOW', 'info': 'INFO'}
    return level_map.get(level, 'UNKNOWN')
