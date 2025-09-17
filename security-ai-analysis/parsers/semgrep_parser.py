"""
Parse Semgrep SAST scan outputs
Semgrep JSON format documented at: https://semgrep.dev/docs/cli-reference/
"""
import json
from typing import List, Dict


def parse_semgrep_json(filepath: str) -> List[Dict]:
    """
    Parse Semgrep JSON output
    
    Expected structure from Semgrep docs:
    {
        "results": [
            {
                "check_id": "...",
                "path": "...",
                "extra": {
                    "message": "...",
                    "severity": "..."
                }
            }
        ]
    }
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        findings = []
        for result in data.get('results', []):
            extra = result.get('extra', {})
            metadata = extra.get('metadata', {})
            
            findings.append({
                'tool': 'semgrep',
                'id': result.get('check_id', 'Unknown'),
                'path': result.get('path', 'Unknown'),
                'start': result.get('start', {}),  # Preserve start location for enhanced dataset creation
                'message': extra.get('message', 'No message'),
                'severity': extra.get('severity', 'Unknown'),
                'cwe': metadata.get('cwe', []),
                'owasp': metadata.get('owasp', []),
                'technology': metadata.get('technology', []),
                'category': metadata.get('category', 'Unknown')
            })
        
        return findings
    except Exception as e:
        print(f"Error parsing Semgrep JSON: {e}")
        return []