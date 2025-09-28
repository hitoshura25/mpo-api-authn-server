#!/usr/bin/env python3
"""
Security Narrativizer - Transform raw vulnerabilities into rich training data
This creates detailed narratives from your security findings to train OLMo
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import subprocess


class SecurityNarrativizer:
    """
    Transform raw vulnerabilities into rich, contextual narratives
    Similar to health data narrativization but for security
    """
    
    def __init__(self):
        self.vulnerability_patterns = self.load_vulnerability_patterns()
        self.narratives = []
        
    def load_vulnerability_patterns(self) -> Dict:
        """Load known vulnerability patterns and their fixes"""
        patterns = {
            "CKV2_GHA_1": {
                "name": "GitHub Actions Excessive Permissions",
                "description": "Top-level permissions set to write-all",
                "impact": "Could allow unauthorized repository modifications",
                "fix_pattern": """permissions:
  contents: read
  # Add specific permissions only where needed""",
                "validation": "Checkov scan passes for CKV2_GHA_1"
            },
            "semgrep-rules.webauthn-credential-validation-bypass": {
                "name": "WebAuthn Credential Validation Bypass",
                "description": "Missing or incomplete credential validation",
                "impact": "Could allow authentication bypass",
                "fix_pattern": """// Validate credential properly
if (!credential.response.clientDataJSON) {
    throw new Error('Invalid credential');
}
const clientData = JSON.parse(
    new TextDecoder().decode(credential.response.clientDataJSON)
);
if (clientData.challenge !== expectedChallenge) {
    throw new Error('Challenge mismatch');
}""",
                "validation": "Credential validation includes challenge verification"
            },
            "javascript.lang.security.detect-child-process": {
                "name": "Child Process Execution",
                "description": "Direct execution of child processes",
                "impact": "Could allow command injection",
                "fix_pattern": """// Use spawn with array arguments instead
const { spawn } = require('child_process');
const child = spawn('command', ['arg1', 'arg2'], {
    shell: false  // Disable shell interpretation
});""",
                "validation": "No direct exec() or shell:true usage"
            }
        }
        return patterns
    
    def narrativize_vulnerability(self, vuln: Dict) -> str:
        """Convert a vulnerability into a detailed narrative"""
        
        vuln_id = vuln.get('id', 'UNKNOWN')
        pattern = self.vulnerability_patterns.get(vuln_id, {})
        
        narrative = f"""
=== Security Vulnerability Narrative ===
Date Discovered: {datetime.now().isoformat()}
Tool: {vuln.get('tool', 'security-scanner')}
Vulnerability ID: {vuln_id}
Severity: {vuln.get('severity', 'UNKNOWN')}
File: {vuln.get('file_path', 'unknown')}

CONTEXT:
This vulnerability was found in the WebAuthn authentication server project. 
{pattern.get('name', vuln.get('message', 'Security issue detected'))}

PROBLEM DESCRIPTION:
{pattern.get('description', vuln.get('message', ''))}
The issue is located in {vuln.get('file_path', 'the codebase')}.

SECURITY IMPACT:
{pattern.get('impact', 'This could potentially compromise system security.')}
In the context of a WebAuthn authentication system, this is particularly critical because:
- Authentication systems are high-value targets
- Vulnerabilities could affect all users
- Trust in the authentication mechanism is essential

SPECIFIC FIX REQUIRED:
To remediate this vulnerability, apply the following fix:

{pattern.get('fix_pattern', 'Apply security best practices for this issue type.')}

STEP-BY-STEP REMEDIATION:
1. Locate the file: {vuln.get('file_path', 'affected file')}
2. Find the vulnerable code section
3. Apply the fix pattern shown above
4. Test the changes to ensure functionality is preserved
5. Re-run security scans to validate the fix

VALIDATION:
After applying the fix:
- {pattern.get('validation', 'The security scan should no longer report this issue')}
- Functionality should remain intact
- No new vulnerabilities should be introduced

LEARNING POINTS:
This vulnerability teaches us about:
- The importance of least privilege principles
- Secure coding practices in {self.get_technology_context(vuln)}
- How automated security scanning helps catch issues early
"""
        return narrative
    
    def get_technology_context(self, vuln: Dict) -> str:
        """Determine the technology context from the file path"""
        file_path = vuln.get('file_path', '')
        
        if '.github/workflows' in file_path:
            return "GitHub Actions CI/CD pipelines"
        elif '.js' in file_path or '.ts' in file_path:
            return "JavaScript/TypeScript applications"
        elif '.yml' in file_path or '.yaml' in file_path:
            return "YAML configuration files"
        elif 'docker' in file_path.lower():
            return "Docker containerization"
        else:
            return "modern web applications"
    
    def collect_git_fixes(self, repo_path: str = ".") -> List[Dict]:
        """Collect real security fixes from git history"""
        fixes = []
        
        try:
            # Get commits that mention security or fixes
            result = subprocess.run(
                ["git", "log", "--grep=fix\\|security\\|CVE\\|vulnerability", 
                 "--pretty=format:%H|%s", "-20"],  # Last 20 security-related commits
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if '|' in line:
                        commit_hash, message = line.split('|', 1)
                        
                        # Get the diff for this commit
                        diff_result = subprocess.run(
                            ["git", "diff", f"{commit_hash}^", commit_hash],
                            cwd=repo_path,
                            capture_output=True,
                            text=True
                        )
                        
                        if diff_result.returncode == 0:
                            fixes.append({
                                'commit': commit_hash,
                                'message': message,
                                'diff': diff_result.stdout[:2000]  # Limit diff size
                            })
        except Exception as e:
            print(f"Error collecting git fixes: {e}")
            raise
        
        return fixes
    
    def create_fix_narrative(self, fix: Dict) -> str:
        """Create a narrative from a real git fix"""
        return f"""
=== Real Security Fix Applied ===
Commit: {fix['commit']}
Message: {fix['message']}

WHAT WAS FIXED:
This commit addressed a security concern by modifying the code as shown below.

CODE CHANGES:
```diff
{fix['diff'][:1500]}  # Truncated for readability
```

EXPLANATION:
This fix improved security by making the code more robust against potential vulnerabilities.
The changes follow security best practices and have been tested in production.

LESSONS LEARNED:
- Real fixes often involve multiple small changes
- Security improvements should be tested thoroughly
- Clear commit messages help track security improvements
"""
    
    def process_scan_results(self, results_dir: str = "data/olmo_analysis_results") -> List[str]:
        """Process existing scan results and create narratives"""
        narratives = []
        
        # Load the analysis results
        results_path = Path(results_dir)
        for json_file in results_path.glob("olmo_analysis_results_*.json"):
            print(f"Processing {json_file.name}...")
            
            with open(json_file, 'r') as f:
                results = json.load(f)
            
            for result in results[:20]:  # Process first 20 for training
                if result.get('status') == 'success':
                    vuln = result['vulnerability']
                    narrative = self.narrativize_vulnerability(vuln)
                    narratives.append(narrative)
        
        return narratives
    
    def create_training_pairs(self, narratives: List[str]) -> List[Dict]:
        """Create instruction-following training pairs"""
        training_pairs = []
        
        for narrative in narratives:
            # Extract vulnerability info from narrative
            lines = narrative.split('\n')
            vuln_id = ""
            file_path = ""
            
            for line in lines:
                if 'Vulnerability ID:' in line:
                    vuln_id = line.split(':', 1)[1].strip()
                elif 'File:' in line:
                    file_path = line.split(':', 1)[1].strip()
            
            # Create different types of training examples
            
            # Type 1: Full analysis request
            training_pairs.append({
                "instruction": "Analyze this security vulnerability and provide detailed remediation",
                "input": f"Vulnerability {vuln_id} found in {file_path}",
                "output": narrative
            })
            
            # Type 2: Fix generation request
            fix_section = narrative.split("SPECIFIC FIX REQUIRED:")[1].split("STEP-BY-STEP")[0].strip() if "SPECIFIC FIX REQUIRED:" in narrative else ""
            if fix_section:
                training_pairs.append({
                    "instruction": "Generate a code fix for this vulnerability",
                    "input": f"{vuln_id}: {file_path}",
                    "output": fix_section
                })
            
            # Type 3: Impact analysis request
            impact_section = narrative.split("SECURITY IMPACT:")[1].split("SPECIFIC FIX")[0].strip() if "SECURITY IMPACT:" in narrative else ""
            if impact_section:
                training_pairs.append({
                    "instruction": "Explain the security impact of this vulnerability",
                    "input": f"What is the impact of {vuln_id}?",
                    "output": impact_section
                })
        
        return training_pairs
    
    def save_narratives(self, output_dir: str = "data/narrativized_security"):
        """Save all narratives and training data"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Process scan results
        print("📝 Creating narratives from scan results...")
        scan_narratives = self.process_scan_results()
        
        # Collect git fixes
        print("📚 Collecting real fixes from git history...")
        git_fixes = self.collect_git_fixes("../..")  # Go up to main repo
        fix_narratives = [self.create_fix_narrative(fix) for fix in git_fixes]
        
        # Combine all narratives
        all_narratives = scan_narratives + fix_narratives
        
        # Save narratives as a text journal (like health_journal.txt)
        journal_path = output_path / f"security_journal_{timestamp}.txt"
        with open(journal_path, 'w') as f:
            for narrative in all_narratives:
                f.write(narrative)
                f.write("\n" + "="*80 + "\n")
        print(f"✅ Security journal saved to: {journal_path}")
        
        # Create training pairs
        training_pairs = self.create_training_pairs(scan_narratives)
        
        # Save training pairs as JSONL
        training_path = output_path / f"training_pairs_{timestamp}.jsonl"
        with open(training_path, 'w') as f:
            for pair in training_pairs:
                f.write(json.dumps(pair) + '\n')
        print(f"✅ Training pairs saved to: {training_path}")
        
        # Save as JSON for easy loading
        json_path = output_path / f"training_data_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump({
                "metadata": {
                    "created": timestamp,
                    "narrative_count": len(all_narratives),
                    "training_pair_count": len(training_pairs)
                },
                "narratives": all_narratives[:10],  # Sample for review
                "training_pairs": training_pairs
            }, f, indent=2)
        print(f"✅ Training data saved to: {json_path}")
        
        # Create README
        readme_path = output_path / "README.md"
        with open(readme_path, 'w') as f:
            f.write(f"""# Narrativized Security Dataset

## Overview
This dataset contains rich, contextual narratives created from security vulnerabilities
found in the WebAuthn authentication server project.

## Files
- `security_journal_*.txt` - Full narratives in journal format (for fine-tuning)
- `training_pairs_*.jsonl` - Instruction-following pairs in JSONL format
- `training_data_*.json` - Complete training data with metadata

## Statistics
- Total Narratives: {len(all_narratives)}
- Training Pairs: {len(training_pairs)}
- Git Fixes Collected: {len(git_fixes)}

## Usage
1. Use the journal format for continuous pre-training
2. Use training pairs for instruction fine-tuning
3. Both formats can be used with OLMo fine-tuning scripts

## Next Steps
1. Review the narratives for quality
2. Fine-tune OLMo using this data
3. Test improved model on new vulnerabilities
""")
        
        print(f"\n📊 Summary:")
        print(f"  - Created {len(all_narratives)} narratives")
        print(f"  - Generated {len(training_pairs)} training pairs")
        print(f"  - Collected {len(git_fixes)} git fixes")
        
        return journal_path


def main():
    print("🔒 Security Narrativizer for OLMo Training")
    print("="*60)
    
    narrativizer = SecurityNarrativizer()
    journal_path = narrativizer.save_narratives()
    
    print("\n✅ Narrativization complete!")
    print("\n🚀 Next steps:")
    print("1. Review the generated narratives for quality")
    print("2. Run: python prepare_finetuning_dataset.py")
    print("3. Fine-tune OLMo using the training data")
    
    return journal_path


if __name__ == "__main__":
    main()
