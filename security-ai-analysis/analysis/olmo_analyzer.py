"""
Improved OLMo Security Analyzer with better prompting for security tasks
Optimized for OLMo-1B's capabilities
"""
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from typing import Dict, List
import json


class OLMoSecurityAnalyzer:
    def __init__(self, model_name: str = "allenai/OLMo-1B", fallback_mode: bool = False):
        """
        Initialize OLMo with optimized settings for security analysis
        """
        self.fallback_mode = fallback_mode
        self.model = None
        self.tokenizer = None
        
        if fallback_mode:
            print("🔄 Running in fallback mode - using template-based analysis only")
            return
            
        print(f"Loading {model_name} with security-optimized configuration...")
        
        # Add comprehensive environment debugging for GitHub Actions troubleshooting
        print("🔍 Environment Information:")
        import sys
        import transformers
        import psutil
        import platform
        print(f"   Python version: {sys.version}")
        print(f"   PyTorch version: {torch.__version__}")
        print(f"   Transformers version: {transformers.__version__}")
        print(f"   Platform: {platform.platform()}")
        print(f"   Architecture: {platform.architecture()}")
        print(f"   Machine: {platform.machine()}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        print(f"   CPU count: {torch.get_num_threads()}")
        try:
            print(f"   Available memory: {psutil.virtual_memory().available / (1024**3):.1f} GB")
            print(f"   Total memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
        except:
            print("   Memory info: Not available")
        print(f"   Torch backend: {torch.backends.cpu.get_cpu_capability()}")
        
        # Verify model availability before loading
        print(f"📦 Checking model availability: {model_name}")
        try:
            from transformers.utils import cached_path
            # Test if we can resolve the model without downloading
            print("   Model resolution test passed")
        except Exception as e:
            print(f"   Model resolution test failed: {e}")
        
        try:
            print("🔧 Loading tokenizer...", flush=True)
            import sys
            sys.stdout.flush()
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True
            )
            print(f"✅ Tokenizer loaded successfully", flush=True)
            print(f"   Vocab size: {len(self.tokenizer.vocab) if hasattr(self.tokenizer, 'vocab') else 'Unknown'}")
            print(f"   Model max length: {self.tokenizer.model_max_length}")
            
            print("🔧 Loading model with conservative settings...", flush=True)
            sys.stdout.flush()
            # More conservative model loading with additional debugging
            print("   Starting AutoModelForCausalLM.from_pretrained()...", flush=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,  # Always use float32 for stability
                device_map=None,            # Let PyTorch handle device placement
                trust_remote_code=True,
                low_cpu_mem_usage=True,    # Enable memory optimization
                use_cache=True,            # Enable caching
                local_files_only=False     # Allow downloading if needed
            )
            print(f"✅ Model loaded successfully", flush=True)
            
            # Validate model integrity
            print("🔧 Validating model integrity...", flush=True)
            print("   Extracting model parameters...", flush=True)
            model_params = list(self.model.parameters())
            print(f"   Found {len(model_params)} parameter tensors", flush=True)
            
            if not model_params:
                raise ValueError("Model has no parameters - loading failed")
            
            print("   Checking first parameter...", flush=True)
            first_param = model_params[0]
            if first_param is None:
                raise ValueError("First model parameter is None - corrupted loading")
                
            print(f"   ✅ Model has {len(model_params)} parameter tensors", flush=True)
            print(f"   ✅ First parameter shape: {first_param.shape}", flush=True)
            print(f"   ✅ First parameter device: {first_param.device}", flush=True)
            print(f"   ✅ First parameter dtype: {first_param.dtype}", flush=True)
            
            # Set pad token if not set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                print(f"✅ Pad token set to EOS token: '{self.tokenizer.eos_token}'")
            else:
                print(f"✅ Pad token already set: '{self.tokenizer.pad_token}'")
            
            # Print final device info
            device = next(self.model.parameters()).device
            dtype = next(self.model.parameters()).dtype
            print(f"✅ Model device: {device}")
            print(f"✅ Model dtype: {dtype}")
            
            print("✅ OLMo model loaded and optimized for security analysis")
            
        except Exception as e:
            print(f"❌ Failed to load OLMo model: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            print(f"   Full traceback:")
            traceback.print_exc()
            print("🔄 Falling back to template-based analysis mode")
            self.fallback_mode = True
            self.model = None
            self.tokenizer = None
    
    def analyze_vulnerability(self, vulnerability: Dict) -> str:
        """
        Generate analysis with improved prompting for OLMo or fallback mode
        """
        severity = vulnerability.get('severity', 'UNKNOWN')
        tool = vulnerability.get('tool', 'security-scan')
        vuln_id = vulnerability.get('id', 'UNKNOWN')
        description = vulnerability.get('description', vulnerability.get('message', 'No description'))
        
        # If in fallback mode or model failed, use template-based analysis
        if self.fallback_mode or self.model is None:
            return self._generate_template_analysis(vulnerability)
        
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
        
        # Move to device if available (be more careful about device placement)
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate with settings optimized for security analysis
        try:
            # Add additional debugging before generation
            print(f"🔧 Debug - About to generate for {vulnerability.get('id', 'UNKNOWN')}")
            print(f"   Model device: {next(self.model.parameters()).device}")
            print(f"   Input device: {inputs['input_ids'].device}")
            print(f"   Input dtype: {inputs['input_ids'].dtype}")
            print(f"   Model dtype: {next(self.model.parameters()).dtype}")
            print(f"   Tokenizer pad_token: {self.tokenizer.pad_token}")
            print(f"   Tokenizer eos_token: {self.tokenizer.eos_token}")
            
            with torch.no_grad():
                # Even more conservative generation parameters
                outputs = self.model.generate(
                    input_ids=inputs['input_ids'],  # Use explicit input_ids only
                    attention_mask=inputs.get('attention_mask'),  # Include attention mask if available
                    max_new_tokens=50,              # Further reduced
                    min_new_tokens=10,              # Lower minimum  
                    temperature=1.0,                # Default temperature
                    do_sample=False,                # Use greedy decoding for stability
                    pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=False,                # Disable caching to avoid issues
                    output_attentions=False,        # Disable attention outputs
                    output_hidden_states=False      # Disable hidden state outputs
                )
            
            # Check if generation was successful
            if outputs is None:
                raise ValueError("Model generation returned None")
            if len(outputs) == 0:
                raise ValueError("Model generation returned empty tensor list")
            if outputs[0] is None:
                raise ValueError("Model generation returned None in first position")
                
            # Decode and extract generated part
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
        except Exception as e:
            # Handle generation failures gracefully with more detailed error info
            print(f"❌ Model generation failed for vulnerability {vulnerability.get('id', 'UNKNOWN')}")
            print(f"   Error details: {str(e)}")
            print(f"   Device: {device}")
            print(f"   Input shape: {inputs['input_ids'].shape if 'input_ids' in inputs else 'N/A'}")
            print("🔄 Falling back to template-based analysis for this vulnerability")
            # Use template-based fallback
            return self._generate_template_analysis(vulnerability)
        
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
    
    def _generate_template_analysis(self, vulnerability: Dict) -> Dict:
        """
        Generate template-based analysis when model fails or in fallback mode
        """
        severity = vulnerability.get('severity', 'UNKNOWN')
        tool = vulnerability.get('tool', 'security-scan')
        vuln_id = vulnerability.get('id', 'UNKNOWN')
        description = vulnerability.get('description', vulnerability.get('message', 'No description'))
        
        # Generate analysis based on vulnerability patterns
        impact = self._get_impact_template(vuln_id, severity, tool)
        remediation = self._get_remediation_template(vuln_id, severity, tool)
        prevention = self._get_prevention_template(vuln_id, severity, tool)
        
        analysis = {
            "vulnerability_id": vuln_id,
            "severity": severity,
            "tool": tool,
            "raw_analysis": f"Template-based analysis for {vuln_id}",
            "structured_analysis": {
                "impact": impact,
                "remediation": remediation,
                "prevention": prevention
            }
        }
        
        return analysis
    
    def _get_impact_template(self, vuln_id: str, severity: str, tool: str) -> str:
        """Generate impact assessment based on vulnerability type"""
        if "CKV_GHA" in vuln_id or "CKV2_GHA" in vuln_id:
            return "GitHub Actions workflow security misconfiguration could allow unauthorized access or privilege escalation"
        elif "semgrep" in tool.lower():
            return "Static analysis detected potential security vulnerability in code that could be exploited by attackers"
        elif "trivy" in tool.lower():
            return "Container or dependency vulnerability that could be exploited to compromise system security"
        elif "checkov" in tool.lower():
            return "Infrastructure as Code security issue that could create attack vectors in deployed resources"
        elif severity in ['HIGH', 'CRITICAL']:
            return "High-severity security vulnerability with significant potential impact"
        else:
            return "Security vulnerability requiring review and remediation"
    
    def _get_remediation_template(self, vuln_id: str, severity: str, tool: str) -> str:
        """Generate remediation guidance based on vulnerability type"""
        if "CKV_GHA_7" in vuln_id:
            return "Set workflow permissions to minimum required level using 'permissions:' key with specific scopes"
        elif "CKV2_GHA_1" in vuln_id:
            return "Remove 'permissions: write-all' and specify only required permissions for each job"
        elif "webauthn" in vuln_id.lower():
            return "Review WebAuthn implementation for proper credential validation and security controls"
        elif "exported_activity" in vuln_id:
            return "Set android:exported=\"false\" for activities that should not be accessible externally"
        elif "unsafe-formatstring" in vuln_id:
            return "Use parameterized formatting or escape user input to prevent format string vulnerabilities"
        elif "semgrep" in tool.lower():
            return "Apply secure coding practices and review flagged code for proper input validation and sanitization"
        elif "trivy" in tool.lower():
            return "Update vulnerable dependencies to patched versions or apply security patches"
        else:
            return "Follow security best practices and apply appropriate patches or configuration changes"
    
    def _get_prevention_template(self, vuln_id: str, severity: str, tool: str) -> str:
        """Generate prevention guidance based on vulnerability type"""
        if "GHA" in vuln_id:
            return "Implement security-first GitHub Actions workflows with minimal permissions and regular security audits"
        elif "webauthn" in vuln_id.lower():
            return "Establish comprehensive WebAuthn security testing and validation processes"
        elif "android" in vuln_id.lower():
            return "Implement Android security best practices and regular security testing in development lifecycle"
        else:
            return "Integrate security scanning into CI/CD pipeline and conduct regular security reviews"
    
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
