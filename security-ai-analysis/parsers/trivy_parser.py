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
            # Extract target information (container image, file path, etc.)
            target = result.get('Target', 'Unknown')
            result_type = result.get('Type', 'Unknown')
            
            for vuln in result.get('Vulnerabilities', []):
                # For Trivy, vulnerabilities are dependency-related, not source code
                # Use the target as the path and provide synthetic line information
                path = target
                
                # If target looks like a dependency file, use it directly
                # Otherwise, create a descriptive path
                if not any(ext in target.lower() for ext in ['.json', '.lock', '.yml', '.yaml', '.toml']):
                    # For container images, create a synthetic dependency path
                    path = f"{target}/dependencies"
                
                vulnerabilities.append({
                    'tool': 'trivy',
                    'id': vuln.get('VulnerabilityID', 'Unknown'),
                    'path': path,  # Target being scanned (image, file, etc.)
                    'start': {'line': 1},  # Dependencies don't have line numbers, use 1
                    'severity': vuln.get('Severity', 'Unknown'),
                    'description': vuln.get('Description', 'No description'),
                    'package': vuln.get('PkgName', 'Unknown'),
                    'fixed_version': vuln.get('FixedVersion', 'Not specified'),
                    'target': target,  # Keep original target info
                    'type': result_type  # Container, filesystem, etc.
                })
        
        return vulnerabilities
    except Exception as e:
        print(f"Error parsing Trivy JSON: {e}")
        return []