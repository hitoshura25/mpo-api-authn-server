"""
Parse OSV Scanner dependency scan outputs
OSV Scanner format documented at: https://github.com/google/osv-scanner
"""
import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


def parse_osv_json(filepath: str) -> List[Dict]:
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
                    
                    vulnerabilities.append({
                        'tool': 'osv-scanner',
                        'id': vuln.get('id', 'Unknown'),
                        'summary': vuln.get('summary', 'No summary'),
                        'severity': severity,
                        'package_name': pkg_name,
                        'package_version': pkg_version,
                        'ecosystem': ecosystem,
                        'source_path': source_path,
                        'source_type': source_type,
                        'path': source_path,  # Map source_path to path field for enhanced dataset creation
                        'start': {'line': 1}  # Minimal start field for enhanced dataset compatibility
                    })
        
        return vulnerabilities
    except Exception as e:
        logger.error(f"❌ CRITICAL: Corrupted OSV Scanner data in {filepath}: {e}")
        logger.error("🔍 File exists but is corrupted - indicates OSV Scanner tool malfunction requiring investigation")
        raise RuntimeError(f"Corrupted OSV Scanner data requires investigation: {e}") from e