"""
Parse SARIF format security scan outputs
SARIF format documented at: https://sarifweb.azurewebsites.net/
Supports multiple tools: Trivy, Checkov, GitLeaks, Semgrep, etc.
"""
import json
from typing import List, Dict


def _normalize_file_path(raw_path: str, tool_name: str = "Unknown") -> str:
    """
    Normalize file paths from SARIF data for enhanced dataset creation.
    
    Keep ALL vulnerability data - no filtering. Apply minimal normalization for consistency:
    - Fix GitHub workflow paths (add missing dot prefix)
    - Normalize CI environment paths to relative paths
    - Extract project-relative paths from absolute paths
    - Keep all Docker images, URLs, JARs, etc. - they represent legitimate security concerns
    """
    if not raw_path or raw_path == 'Unknown':
        return 'Unknown'
    
    # Handle CI environment absolute paths with /home/runner/work/
    if '/home/runner/work/' in raw_path:
        # Extract relative path from CI environment
        parts = raw_path.split('/home/runner/work/')
        if len(parts) > 1:
            # Remove the project name part and get relative path
            remaining = parts[1]
            path_parts = remaining.split('/')
            if len(path_parts) > 2:  # project/project/actual-path
                extracted_path = '/'.join(path_parts[2:])
                # Apply additional normalization to extracted path
                return _normalize_file_path(extracted_path, tool_name)
    
    # Handle paths that start with CI environment artifacts (missing leading slash)
    if raw_path.startswith('home/runner/work/'):
        # Extract relative path from CI environment
        path_parts = raw_path.split('/')
        if len(path_parts) > 5:  # home/runner/work/project/project/actual-path
            extracted_path = '/'.join(path_parts[5:])
            # Apply additional normalization to extracted path
            return _normalize_file_path(extracted_path, tool_name)
    
    # Fix GitHub workflow paths (add missing dot)
    if raw_path.startswith('github/workflows/'):
        raw_path = '.' + raw_path
    
    # Handle other absolute paths - try to make relative
    if raw_path.startswith('/Users/') and 'mpo-api-authn-server' in raw_path:
        # Extract path relative to project root
        parts = raw_path.split('mpo-api-authn-server/')
        if len(parts) > 1:
            raw_path = parts[1]
    
    return raw_path


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
                
                # Extract location information with line numbers
                locations = result.get('locations', [])
                file_path = 'Unknown'
                start_line = 1
                if locations:
                    physical_location = locations[0].get('physicalLocation', {})
                    artifact_location = physical_location.get('artifactLocation', {})
                    raw_path = artifact_location.get('uri', 'Unknown')
                    
                    # Normalize file paths for enhanced dataset creation
                    file_path = _normalize_file_path(raw_path, tool_name)
                    
                    # Extract line number from region if available
                    region = physical_location.get('region', {})
                    start_line = region.get('startLine', 1)
                
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
                    'tool_name': tool_name,
                    'path': file_path,  # Map file_path to path field for enhanced dataset creation
                    'start': {'line': start_line}  # Extract actual line number from SARIF region
                })
        
        return findings
    except Exception as e:
        print(f"Error parsing SARIF JSON: {e}")
        return []