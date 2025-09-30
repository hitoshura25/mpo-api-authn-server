"""
Parse OWASP ZAP scan outputs
ZAP JSON format documented at: https://www.zaproxy.org/docs/desktop/ui/reports/
"""
import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


def parse_zap_json(filepath: str) -> List[Dict]:
    """
    Parse OWASP ZAP JSON report output

    Expected ZAP JSON structure:
    {
        "@programName": "ZAP",
        "@version": "...",
        "site": [
            {
                "@name": "...",
                "@host": "...",
                "@port": "...",
                "alerts": [
                    {
                        "pluginid": "...",
                        "alert": "...",
                        "riskcode": "...",
                        "confidence": "...",
                        "riskdesc": "...",
                        "desc": "...",
                        "instances": [...]
                    }
                ]
            }
        ]
    }
    """
    # Graceful handling for optional tool execution
    if not Path(filepath).exists():
        logger.info(f"ℹ️ ZAP scan file not found: {filepath}")
        logger.info("This is acceptable - ZAP web application scanning may not have been run")
        return []

    # Fail fast on corrupted existing files
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        findings = []
        zap_version = data.get('@version', 'Unknown')
        
        # Risk mapping
        risk_map = {
            '0': 'INFO',
            '1': 'LOW', 
            '2': 'MEDIUM',
            '3': 'HIGH'
        }
        
        for site in data.get('site', []):
            site_name = site.get('@name', 'Unknown')
            site_host = site.get('@host', 'Unknown')
            site_port = site.get('@port', 'Unknown')
            
            for alert in site.get('alerts', []):
                risk_code = str(alert.get('riskcode', '0'))
                severity = risk_map.get(risk_code, 'UNKNOWN')
                
                # Count instances
                instances = alert.get('instances', [])
                instance_count = len(instances)
                
                # Extract first instance details if available
                first_instance = instances[0] if instances else {}
                uri = first_instance.get('uri', site_name)
                method = first_instance.get('method', 'Unknown')
                
                findings.append({
                    'tool': 'zap',
                    'id': alert.get('pluginid', 'Unknown'),
                    'alert_ref': alert.get('alertRef', 'Unknown'),
                    'name': alert.get('alert', 'Unknown'),
                    'severity': severity,
                    'risk_code': risk_code,
                    'confidence': alert.get('confidence', 'Unknown'),
                    'risk_desc': alert.get('riskdesc', 'Unknown'),
                    'description': alert.get('desc', 'No description'),
                    'solution': alert.get('solution', 'No solution provided'),
                    'reference': alert.get('reference', ''),
                    'site_host': site_host,
                    'site_port': site_port,
                    'uri': uri,
                    'url': uri,  # NEW: Add URL field for URL-to-code mapping
                    'method': method,
                    'instance_count': instance_count,
                    'zap_version': zap_version,
                    'path': uri,  # Map URI to path field for enhanced dataset creation
                    'start': {'line': 1}  # Minimal start field for enhanced dataset compatibility
                })
        
        return findings
    except Exception as e:
        logger.error(f"❌ CRITICAL: Corrupted ZAP scan data in {filepath}: {e}")
        logger.error("🔍 File exists but is corrupted - indicates ZAP tool malfunction requiring investigation")
        raise RuntimeError(f"Corrupted ZAP scan data requires investigation: {e}") from e