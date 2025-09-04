"""
Parse Checkov infrastructure scan outputs
Checkov JSON format documented at: https://www.checkov.io/
"""
import json
from typing import List, Dict


def parse_checkov_json(filepath: str) -> List[Dict]:
    """
    Parse Checkov JSON output
    
    Expected structure based on Checkov documentation:
    {
        "results": {
            "failed_checks": [
                {
                    "check_id": "...",
                    "resource": "...",
                    "description": "...",
                    "guideline": "..."
                }
            ]
        }
    }
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        issues = []
        results = data.get('results', {})
        for check in results.get('failed_checks', []):
            issues.append({
                'tool': 'checkov',
                'id': check.get('check_id', 'Unknown'),
                'resource': check.get('resource', 'Unknown'),
                'description': check.get('description', 'No description'),
                'guideline': check.get('guideline', 'No guideline')
            })
        
        return issues
    except Exception as e:
        print(f"Error parsing Checkov JSON: {e}")
        return []