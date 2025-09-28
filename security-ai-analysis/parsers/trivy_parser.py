"""
Parse Trivy security scan outputs
Trivy JSON format documented at: https://aquasecurity.github.io/trivy/
"""
import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


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
    # Graceful handling for optional tool execution
    if not Path(filepath).exists():
        logger.info(f"ℹ️ Trivy scan file not found: {filepath}")
        logger.info("This is acceptable - Trivy container/dependency scanning may not have been run")
        return []

    # Fail fast on corrupted existing files
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
        logger.error(f"❌ CRITICAL: Corrupted Trivy scan data in {filepath}: {e}")
        logger.error("🔍 File exists but is corrupted - indicates Trivy tool malfunction requiring investigation")
        raise RuntimeError(f"Corrupted Trivy scan data requires investigation: {e}") from e