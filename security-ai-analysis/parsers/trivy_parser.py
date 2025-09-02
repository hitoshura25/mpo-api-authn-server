"""
Parse Trivy security scan outputs
Trivy JSON format documented at: https://aquasecurity.github.io/trivy/
"""
import json
from typing import List, Dict


def parse_trivy_json(filepath: str) -> List[Dict]:
    """
    Parse Trivy JSON output into structured format

    Expected Trivy JSON structure:
    {
        "Results": [
            {
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-XXX",
                        "Severity": "HIGH",
                        "Description": "...",
                        "PkgName": "...",
                        "FixedVersion": "..."
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
        for result in data.get('Results', []):
            for vuln in result.get('Vulnerabilities', []):
                vulnerabilities.append({
                    'tool': 'trivy',
                    'id': vuln.get('VulnerabilityID', 'Unknown'),
                    'severity': vuln.get('Severity', 'Unknown'),
                    'description': vuln.get('Description', 'No description'),
                    'package': vuln.get('PkgName', 'Unknown'),
                    'fixed_version': vuln.get('FixedVersion', 'Not specified')
                })
        
        return vulnerabilities
    except Exception as e:
        print(f"Error parsing Trivy JSON: {e}")
        return []