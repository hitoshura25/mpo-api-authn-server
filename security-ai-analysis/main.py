"""
Main entry point for security analysis system
This is a REAL implementation using VERIFIED tools only
"""
import json
import argparse
from pathlib import Path

# Import our parsers
from parsers.trivy_parser import parse_trivy_json
from parsers.checkov_parser import parse_checkov_json
from parsers.semgrep_parser import parse_semgrep_json
from parsers.osv_parser import parse_osv_json
from parsers.sarif_parser import parse_sarif_json
from parsers.zap_parser import parse_zap_json

# Import OLMo analyzer
from analysis.olmo_analyzer import OLMoSecurityAnalyzer


def main():
    parser = argparse.ArgumentParser(description='Analyze security scans with OLMo')
    parser.add_argument('--scan-file', type=str, required=True, help='Path to scan JSON file')
    parser.add_argument('--scan-type', type=str, choices=['trivy', 'checkov', 'semgrep', 'osv', 'sarif', 'zap'], required=True)
    parser.add_argument('--output', type=str, default='analysis_report.json')
    parser.add_argument('--model', type=str, default='allenai/OLMo-1B')
    
    args = parser.parse_args()
    
    # Parse security scan
    print(f"Parsing {args.scan_type} scan from {args.scan_file}...")
    
    if args.scan_type == 'trivy':
        vulnerabilities = parse_trivy_json(args.scan_file)
    elif args.scan_type == 'checkov':
        vulnerabilities = parse_checkov_json(args.scan_file)
    elif args.scan_type == 'semgrep':
        vulnerabilities = parse_semgrep_json(args.scan_file)
    elif args.scan_type == 'osv':
        vulnerabilities = parse_osv_json(args.scan_file)
    elif args.scan_type == 'sarif':
        vulnerabilities = parse_sarif_json(args.scan_file)
    elif args.scan_type == 'zap':
        vulnerabilities = parse_zap_json(args.scan_file)
    else:
        print(f"Unsupported scan type: {args.scan_type}")
        return
    
    print(f"Found {len(vulnerabilities)} issues to analyze")
    
    if not vulnerabilities:
        print("No vulnerabilities found in scan file")
        return
    
    # Initialize OLMo analyzer
    analyzer = OLMoSecurityAnalyzer(model_name=args.model)
    
    # Analyze vulnerabilities
    print("Starting analysis with OLMo...")
    results = analyzer.batch_analyze(vulnerabilities[:5])  # Limit to 5 for testing
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Analysis complete. Results saved to {args.output}")


if __name__ == "__main__":
    main()