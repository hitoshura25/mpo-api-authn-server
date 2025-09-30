"""
Parse Checkov infrastructure scan outputs
Checkov JSON format documented at: https://www.checkov.io/
"""
import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


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
    # Graceful handling for optional tool execution
    if not Path(filepath).exists():
        logger.info(f"ℹ️ Checkov scan file not found: {filepath}")
        logger.info("This is acceptable - Checkov infrastructure scanning may not have been run")
        return []

    # Fail fast on corrupted existing files
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
        logger.error(f"❌ CRITICAL: Corrupted Checkov scan data in {filepath}: {e}")
        logger.error("🔍 File exists but is corrupted - indicates Checkov tool malfunction requiring investigation")
        raise RuntimeError(f"Corrupted Checkov scan data requires investigation: {e}") from e