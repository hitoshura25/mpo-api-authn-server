"""
Parse OSV Scanner dependency scan outputs
OSV Scanner format documented at: https://github.com/google/osv-scanner
"""
import json
from typing import List, Dict


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
        print(f"Error parsing OSV Scanner JSON: {e}")
        return []