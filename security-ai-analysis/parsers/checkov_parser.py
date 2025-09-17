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
            # Extract file path if available from Checkov data
            file_path = check.get('file_path', check.get('resource', 'Unknown'))
            
            # Checkov scans infrastructure files like .tf, .yml, .json
            # If file_path doesn't look like a file, treat it as a resource identifier
            if '.' not in file_path.split('/')[-1]:  # No file extension
                file_path = f"infrastructure/{file_path}"
            
            # Extract line number if available 
            file_line_range = check.get('file_line_range', [1, 1])
            line_number = file_line_range[0] if isinstance(file_line_range, list) and file_line_range else 1
            
            issues.append({
                'tool': 'checkov',
                'id': check.get('check_id', 'Unknown'),
                'path': file_path,  # File being scanned or resource identifier
                'start': {'line': line_number},  # Line number from Checkov if available
                'resource': check.get('resource', 'Unknown'),
                'description': check.get('description', 'No description'),
                'guideline': check.get('guideline', 'No guideline')
            })
        
        return issues
    except Exception as e:
        print(f"Error parsing Checkov JSON: {e}")
        return []