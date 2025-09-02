"""
Improved OLMo Security Analyzer with better prompting for security tasks
Optimized for OLMo-1B's capabilities
"""
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from typing import Dict, List
import json


class OLMoSecurityAnalyzer:
    def __init__(self, model_name: str = "allenai/OLMo-1B"):
        """
        Initialize OLMo with optimized settings for security analysis
        """
        print(f"Loading {model_name} with security-optimized configuration...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True
        )
        
        # Set pad token if not set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        print("✅ OLMo model loaded and optimized for security analysis")
    
    def analyze_vulnerability(self, vulnerability: Dict) -> str:
        """
        Generate analysis with improved prompting for OLMo
        """
        # More structured prompt that works better with OLMo
        # Using a format that helps OLMo understand the task better
        
        severity = vulnerability.get('severity', 'UNKNOWN')
        tool = vulnerability.get('tool', 'security-scan')
        vuln_id = vulnerability.get('id', 'UNKNOWN')
        description = vulnerability.get('description', vulnerability.get('message', 'No description'))
        
        # Simplified, direct prompt that OLMo handles better
        prompt = f"""Vulnerability: {vuln_id}
Severity: {severity}
Tool: {tool}
Issue: {description}

Security Analysis:
1. Impact: This vulnerability could"""
        
        # Tokenize with proper settings for OLMo
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256,  # Shorter context for better focus
            padding=False,
            return_token_type_ids=False  # OLMo doesn't use token_type_ids
        )
        
        # Move to device if available
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Generate with settings optimized for security analysis
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=150,  # Focused response length
                min_new_tokens=50,   # Ensure meaningful response
                temperature=0.3,     # Lower temperature for more focused output
                do_sample=True,
                top_p=0.9,          # Slightly lower for consistency
                repetition_penalty=1.2,  # Reduce repetition
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode and extract generated part
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the generated analysis
        if "Security Analysis:" in full_response:
            analysis = full_response.split("Security Analysis:")[1].strip()
        else:
            analysis = full_response[len(prompt):].strip()
        
        # Format the analysis for better readability
        formatted_analysis = self._format_analysis(analysis, vulnerability)
        
        return formatted_analysis
    
    def _format_analysis(self, raw_analysis: str, vulnerability: Dict) -> Dict:
        """
        Structure the OLMo output into a formatted response
        """
        # Parse the raw analysis and structure it
        lines = raw_analysis.split('\n')
        
        analysis = {
            "vulnerability_id": vulnerability.get('id', 'UNKNOWN'),
            "severity": vulnerability.get('severity', 'UNKNOWN'),
            "tool": vulnerability.get('tool', 'unknown'),
            "raw_analysis": raw_analysis,
            "structured_analysis": {
                "impact": "",
                "remediation": "",
                "prevention": ""
            }
        }
        
        # Try to extract structured information
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers
            if any(key in line.lower() for key in ['impact:', 'risk:', 'consequence:']):
                current_section = 'impact'
                # Extract content after the colon
                if ':' in line:
                    content = line.split(':', 1)[1].strip()
                    if content:
                        analysis['structured_analysis']['impact'] = content
            elif any(key in line.lower() for key in ['fix:', 'remediation:', 'solution:', 'update']):
                current_section = 'remediation'
                if ':' in line:
                    content = line.split(':', 1)[1].strip()
                    if content:
                        analysis['structured_analysis']['remediation'] = content
            elif any(key in line.lower() for key in ['prevent:', 'avoid:', 'best practice']):
                current_section = 'prevention'
                if ':' in line:
                    content = line.split(':', 1)[1].strip()
                    if content:
                        analysis['structured_analysis']['prevention'] = content
            elif current_section:
                # Continue adding to current section
                analysis['structured_analysis'][current_section] += " " + line
        
        # Clean up the structured sections
        for key in analysis['structured_analysis']:
            analysis['structured_analysis'][key] = analysis['structured_analysis'][key].strip()
            
            # If a section is empty, try to extract from raw analysis
            if not analysis['structured_analysis'][key] and raw_analysis:
                if key == 'impact':
                    analysis['structured_analysis'][key] = "Security impact requires further investigation"
                elif key == 'remediation':
                    if 'update' in raw_analysis.lower() or 'patch' in raw_analysis.lower():
                        analysis['structured_analysis'][key] = "Apply security updates as recommended"
                    else:
                        analysis['structured_analysis'][key] = "Review and apply security best practices"
                elif key == 'prevention':
                    analysis['structured_analysis'][key] = "Implement security monitoring and regular updates"
        
        return analysis
    
    def batch_analyze(self, vulnerabilities: List[Dict], max_items: int = 10) -> List[Dict]:
        """
        Analyze multiple vulnerabilities with progress tracking
        """
        results = []
        
        # Limit to max_items for performance
        items_to_process = vulnerabilities[:max_items]
        
        print(f"\n🔍 Analyzing {len(items_to_process)} vulnerabilities with OLMo...")
        print("-" * 50)
        
        for i, vuln in enumerate(items_to_process, 1):
            print(f"[{i}/{len(items_to_process)}] Analyzing {vuln.get('id', 'unknown')}...", end=" ")
            
            try:
                analysis = self.analyze_vulnerability(vuln)
                results.append({
                    'vulnerability': vuln,
                    'analysis': analysis,
                    'status': 'success'
                })
                print("✅")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                results.append({
                    'vulnerability': vuln,
                    'analysis': {'error': str(e)},
                    'status': 'error'
                })
        
        print("-" * 50)
        print(f"✅ Analysis complete: {len(results)} items processed\n")
        
        return results
    
    def generate_summary_report(self, analysis_results: List[Dict]) -> Dict:
        """
        Generate a summary report of all analyses
        """
        summary = {
            "total_analyzed": len(analysis_results),
            "successful": sum(1 for r in analysis_results if r['status'] == 'success'),
            "failed": sum(1 for r in analysis_results if r['status'] == 'error'),
            "by_severity": {},
            "by_tool": {},
            "key_findings": []
        }
        
        for result in analysis_results:
            if result['status'] == 'success':
                vuln = result['vulnerability']
                severity = vuln.get('severity', 'UNKNOWN')
                tool = vuln.get('tool', 'unknown')
                
                # Count by severity
                summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
                
                # Count by tool
                summary['by_tool'][tool] = summary['by_tool'].get(tool, 0) + 1
                
                # Extract key findings for HIGH/CRITICAL severities
                if severity in ['HIGH', 'CRITICAL', 'ERROR']:
                    summary['key_findings'].append({
                        'id': vuln.get('id'),
                        'severity': severity,
                        'impact': result['analysis'].get('structured_analysis', {}).get('impact', 'N/A')
                    })
        
        return summary


def test_improved_analyzer():
    """
    Test function to validate the improved analyzer
    """
    print("🧪 Testing Improved OLMo Security Analyzer...")
    
    # Sample vulnerability for testing
    test_vuln = {
        'tool': 'checkov',
        'id': 'CKV2_GHA_1',
        'severity': 'HIGH',
        'description': 'Ensure top-level permissions are not set to write-all in GitHub Actions workflows',
        'file_path': '.github/workflows/test.yml'
    }
    
    # Initialize analyzer
    analyzer = ImprovedOLMoSecurityAnalyzer()
    
    # Test single analysis
    print("\n📝 Testing single vulnerability analysis...")
    result = analyzer.analyze_vulnerability(test_vuln)
    print(json.dumps(result, indent=2))
    
    # Test batch analysis
    print("\n📊 Testing batch analysis...")
    test_vulns = [test_vuln] * 3  # Test with 3 items
    results = analyzer.batch_analyze(test_vulns, max_items=3)
    
    # Generate summary
    summary = analyzer.generate_summary_report(results)
    print("\n📈 Summary Report:")
    print(json.dumps(summary, indent=2))
    
    return results


if __name__ == "__main__":
    test_improved_analyzer()
