"""
Parse SARIF format security scan outputs
SARIF format documented at: https://sarifweb.azurewebsites.net/
Supports multiple tools: Trivy, Checkov, GitLeaks, Semgrep, etc.
"""
import json
from typing import List, Dict


def parse_sarif_json(filepath: str) -> List[Dict]:
    """
    Parse SARIF JSON output from various security tools
    
    SARIF v2.1.0 structure:
    {
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "...",
                        "rules": [...]
                    }
                },
                "results": [
                    {
                        "ruleId": "...",
                        "message": {"text": "..."},
                        "locations": [...],
                        "level": "..."
                    }
                ]
            }
        ]
    }
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        findings = []
        for run in data.get('runs', []):
            tool_name = run.get('tool', {}).get('driver', {}).get('name', 'Unknown')
            rules = run.get('tool', {}).get('driver', {}).get('rules', [])
            
            # Create rule lookup for additional context
            rule_lookup = {rule.get('id'): rule for rule in rules}
            
            for result in run.get('results', []):
                rule_id = result.get('ruleId', 'Unknown')
                rule_info = rule_lookup.get(rule_id, {})
                
                # Extract location information
                locations = result.get('locations', [])
                file_path = 'Unknown'
                if locations:
                    physical_location = locations[0].get('physicalLocation', {})
                    artifact_location = physical_location.get('artifactLocation', {})
                    file_path = artifact_location.get('uri', 'Unknown')
                
                # Extract severity/level
                level = result.get('level', 'info')
                severity_map = {
                    'error': 'HIGH',
                    'warning': 'MEDIUM', 
                    'note': 'LOW',
                    'info': 'INFO'
                }
                severity = severity_map.get(level, level.upper())
                
                # Get message
                message = result.get('message', {})
                message_text = message.get('text', 'No description')
                
                findings.append({
                    'tool': f'sarif-{tool_name.lower()}',
                    'id': rule_id,
                    'severity': severity,
                    'level': level,
                    'message': message_text,
                    'file_path': file_path,
                    'rule_name': rule_info.get('name', 'Unknown'),
                    'short_description': rule_info.get('shortDescription', {}).get('text', ''),
                    'full_description': rule_info.get('fullDescription', {}).get('text', ''),
                    'help_uri': rule_info.get('helpUri', ''),
                    'tool_name': tool_name
                })
        
        return findings
    except Exception as e:
        print(f"Error parsing SARIF JSON: {e}")
        return []