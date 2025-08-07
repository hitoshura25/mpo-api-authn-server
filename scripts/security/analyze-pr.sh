#!/bin/bash
#
# AI-Powered PR Security Analysis Script
#
# This script performs intelligent security analysis on pull requests using AI
# to detect WebAuthn vulnerabilities, security anti-patterns, and potential attack vectors.
#
# USAGE:
#   ./analyze-pr.sh <changed_files_json> <pr_title> <pr_body> <risk_level>
#
# ENVIRONMENT VARIABLES:
#   ANTHROPIC_API_KEY - API key for AI analysis (optional, falls back to standard analysis)
#   PR_NUMBER - Pull request number
#   WEBAUTHN_SECURITY_AGENT_PATH - Path to WebAuthn security agent file
#   VULNERABILITY_DB_PATH - Path to vulnerability database JSON
#
# OUTPUTS:
#   - security-analysis-results.json - Complete AI analysis results
#   - GitHub Actions outputs:
#     - security-score: Risk score 0-10
#     - vulnerabilities-found: Count of vulnerabilities
#     - requires-security-review: true/false
#     - recommendations: Semicolon-separated recommendations
#     - analysis-report: Summary report
#
# EXIT CODES:
#   0 - Analysis completed successfully
#   1 - Analysis failed (fallback analysis provided)
#

set -euo pipefail

# Default paths
WEBAUTHN_SECURITY_AGENT_PATH="${WEBAUTHN_SECURITY_AGENT_PATH:-./.claude/agents/webauthn-security-analysis.md}"
VULNERABILITY_DB_PATH="${VULNERABILITY_DB_PATH:-./vulnerability-tracking.json}"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Function to check if required Node.js dependencies are available
check_dependencies() {
    log "📦 Checking Node.js dependencies..."
    
    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        log "❌ Error: npm is not installed"
        return 1
    fi
    
    # Check if @anthropic-ai/sdk is available
    if [ ! -d "node_modules/@anthropic-ai/sdk" ] && [ ! -d "../node_modules/@anthropic-ai/sdk" ]; then
        log "⚠️ Installing AI analysis dependencies..."
        npm install --save-dev \
            @anthropic-ai/sdk \
            typescript \
            ts-node \
            @types/node || log "⚠️ Failed to install dependencies, continuing with standard analysis"
    fi
    
    log "✅ Dependencies checked"
}

# Function to load security context
load_security_context() {
    local agent_loaded=false
    local vuln_db_loaded=false
    
    log "📚 Loading security analysis context..."
    
    # Load WebAuthn Security Analysis Agent
    if [ -f "$WEBAUTHN_SECURITY_AGENT_PATH" ]; then
        log "✅ WebAuthn Security Agent loaded from $WEBAUTHN_SECURITY_AGENT_PATH"
        agent_loaded=true
    else
        log "⚠️ WebAuthn Security Agent not found at $WEBAUTHN_SECURITY_AGENT_PATH"
    fi
    
    # Load vulnerability tracking database
    if [ -f "$VULNERABILITY_DB_PATH" ]; then
        local vuln_count
        vuln_count=$(jq '.vulnerabilities | length' "$VULNERABILITY_DB_PATH" 2>/dev/null || echo 0)
        log "✅ Vulnerability database loaded with $vuln_count known vulnerabilities"
        vuln_db_loaded=true
    else
        log "⚠️ Vulnerability database not found at $VULNERABILITY_DB_PATH"
    fi
    
    # Set GitHub Actions outputs for context loading
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
        echo "agent-loaded=$agent_loaded" >> "$GITHUB_OUTPUT"
        echo "vuln-db-loaded=$vuln_db_loaded" >> "$GITHUB_OUTPUT"
    fi
}

# Function to create the AI security analyzer Node.js script
create_ai_analyzer() {
    local changed_files="$1"
    local pr_title="$2"
    local pr_body="$3"
    local risk_level="$4"
    
    log "🤖 Creating AI security analyzer..."
    
    cat > ai-security-analyzer.cjs << 'EOF'
const fs = require('fs');
const path = require('path');

// Try to import Anthropic SDK, fall back if not available
let Anthropic;
try {
  Anthropic = require('@anthropic-ai/sdk').Anthropic;
} catch (error) {
  console.warn('⚠️ Anthropic SDK not available, using fallback analysis');
  Anthropic = null;
}

class WebAuthnSecurityAnalyzer {
  constructor() {
    this.anthropic = Anthropic ? new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY
    }) : null;
    this.maxRetries = 3;
    this.retryDelay = 2000;
  }

  async analyzeSecurityChanges(changedFiles, prContext) {
    try {
      console.log('🔍 Analyzing security implications of code changes...');
      
      if (!this.anthropic || !process.env.ANTHROPIC_API_KEY) {
        console.log('⚠️ AI analysis not available, using fallback analysis');
        return this.createFallbackAnalysis();
      }
      
      // Load security context
      const securityAgent = this.loadSecurityAgent();
      const vulnerabilityDB = this.loadVulnerabilityDatabase();
      const codeChanges = await this.extractCodeChanges(changedFiles);
      
      const prompt = this.buildSecurityAnalysisPrompt(
        securityAgent, 
        vulnerabilityDB, 
        codeChanges, 
        prContext
      );
      
      const analysis = await this.performAIAnalysis(prompt);
      return this.parseAnalysisResults(analysis);
      
    } catch (error) {
      console.error('❌ AI analysis failed:', error.message);
      return this.createFallbackAnalysis();
    }
  }

  loadSecurityAgent() {
    try {
      const agentPath = process.env.WEBAUTHN_SECURITY_AGENT_PATH || './.claude/agents/webauthn-security-analysis.md';
      return fs.readFileSync(agentPath, 'utf8');
    } catch (error) {
      console.warn('⚠️ Could not load security agent:', error.message);
      return 'Security analysis agent not available';
    }
  }

  loadVulnerabilityDatabase() {
    try {
      const dbPath = process.env.VULNERABILITY_DB_PATH || './vulnerability-tracking.json';
      return JSON.parse(fs.readFileSync(dbPath, 'utf8'));
    } catch (error) {
      console.warn('⚠️ Could not load vulnerability database:', error.message);
      return { vulnerabilities: [] };
    }
  }

  async extractCodeChanges(changedFiles) {
    const codeChanges = {};
    
    for (const file of changedFiles) {
      try {
        if (fs.existsSync(file)) {
          const content = fs.readFileSync(file, 'utf8');
          codeChanges[file] = {
            content: content.substring(0, 10000), // Limit for AI context
            size: content.length,
            extension: path.extname(file)
          };
        }
      } catch (error) {
        console.warn(`⚠️ Could not read file ${file}:`, error.message);
      }
    }
    
    return codeChanges;
  }

  buildSecurityAnalysisPrompt(securityAgent, vulnerabilityDB, codeChanges, prContext) {
    return `You are a WebAuthn security expert analyzing a pull request for potential security vulnerabilities.

SECURITY CONTEXT:
${securityAgent}

KNOWN VULNERABILITIES DATABASE:
${JSON.stringify(vulnerabilityDB.vulnerabilities, null, 2)}

PULL REQUEST CONTEXT:
- Title: ${prContext.title}
- Risk Level: ${prContext.riskLevel}
- Changed Files: ${Object.keys(codeChanges).join(', ')}

CODE CHANGES TO ANALYZE:
${Object.entries(codeChanges).map(([file, data]) => 
  `\n--- ${file} ---\n${data.content}`
).join('\n')}

ANALYSIS REQUIREMENTS:
1. **Vulnerability Detection**: Identify potential security issues using the known vulnerability patterns
2. **WebAuthn-Specific Risks**: Focus on authentication flows, credential handling, origin validation
3. **Information Leakage**: Check for sensitive data exposure in logs, errors, or responses
4. **Attack Vector Analysis**: Assess potential for PoisonSeed, replay, tampering attacks
5. **Defensive Programming**: Verify proper error handling and input validation

RESPONSE FORMAT (JSON):
{
  "securityScore": <0-10 float representing risk level>,
  "vulnerabilitiesFound": [
    {
      "type": "vulnerability type",
      "severity": "LOW|MEDIUM|HIGH|CRITICAL",
      "location": "file:line",
      "description": "detailed vulnerability description",
      "cweId": "CWE-XXX if applicable",
      "recommendedFix": "specific mitigation steps"
    }
  ],
  "recommendations": [
    "specific actionable security recommendations"
  ],
  "requiresSecurityReview": <boolean>,
  "testRecommendations": [
    {
      "testType": "test category",
      "description": "what should be tested",
      "priority": "HIGH|MEDIUM|LOW"
    }
  ],
  "securityPatterns": {
    "good": ["security patterns found"],
    "missing": ["missing security patterns"],
    "antipatterns": ["problematic patterns found"]
  }
}

Focus on practical, actionable analysis specific to WebAuthn authentication security.`;
  }

  async performAIAnalysis(prompt) {
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        console.log(`🤖 AI Analysis attempt ${attempt}/${this.maxRetries}...`);
        
        const message = await this.anthropic.messages.create({
          model: 'claude-3-5-sonnet-20241022',
          max_tokens: 4000,
          temperature: 0.1, // Low temperature for consistent security analysis
          messages: [{
            role: 'user',
            content: prompt
          }]
        });

        return message.content[0].text;
        
      } catch (error) {
        console.warn(`⚠️ AI analysis attempt ${attempt} failed:`, error.message);
        
        if (attempt === this.maxRetries) {
          throw error;
        }
        
        await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempt));
      }
    }
  }

  parseAnalysisResults(analysisText) {
    try {
      // Extract JSON from AI response (may include explanation text)
      const jsonMatch = analysisText.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        throw new Error('No JSON found in AI response');
      }
      
      const analysis = JSON.parse(jsonMatch[0]);
      
      // Validate required fields
      const required = ['securityScore', 'vulnerabilitiesFound', 'recommendations', 'requiresSecurityReview'];
      for (const field of required) {
        if (!(field in analysis)) {
          console.warn(`⚠️ Missing required field: ${field}`);
        }
      }
      
      return analysis;
      
    } catch (error) {
      console.error('❌ Failed to parse AI analysis results:', error.message);
      console.log('Raw AI response:', analysisText);
      return this.createFallbackAnalysis();
    }
  }

  createFallbackAnalysis() {
    return {
      securityScore: 5.0,
      vulnerabilitiesFound: [],
      recommendations: [
        'AI security analysis failed - manual security review recommended',
        'Run existing security tests: ./gradlew test --tests="*VulnerabilityProtectionTest*"',
        'Review changes against WebAuthn security best practices'
      ],
      requiresSecurityReview: true,
      testRecommendations: [
        {
          testType: 'Manual Review',
          description: 'Manual security review required due to AI analysis failure',
          priority: 'HIGH'
        }
      ],
      analysisError: 'AI analysis failed - fallback analysis provided'
    };
  }
}

// Main execution
async function main() {
  const analyzer = new WebAuthnSecurityAnalyzer();
  
  const changedFiles = JSON.parse(process.env.CHANGED_FILES || '[]');
  const prContext = {
    title: process.env.PR_TITLE || '',
    riskLevel: process.env.RISK_LEVEL || 'UNKNOWN'
  };
  
  console.log(`🔍 Analyzing ${changedFiles.length} changed files...`);
  console.log('Risk Level:', prContext.riskLevel);
  
  const results = await analyzer.analyzeSecurityChanges(changedFiles, prContext);
  
  console.log('📊 Security Analysis Results:');
  console.log(`Security Score: ${results.securityScore}/10`);
  console.log(`Vulnerabilities Found: ${results.vulnerabilitiesFound.length}`);
  console.log(`Requires Security Review: ${results.requiresSecurityReview}`);
  
  // Write results to files for GitHub Actions
  fs.writeFileSync('security-analysis-results.json', JSON.stringify(results, null, 2));
  
  // Set GitHub Actions outputs
  console.log(`::set-output name=security-score::${results.securityScore}`);
  console.log(`::set-output name=vulnerabilities-found::${results.vulnerabilitiesFound.length}`);
  console.log(`::set-output name=requires-security-review::${results.requiresSecurityReview}`);
  
  const recommendationsText = results.recommendations.join(';');
  console.log(`::set-output name=recommendations::${recommendationsText}`);
  
  const analysisReport = `Security Score: ${results.securityScore}/10\nVulnerabilities: ${results.vulnerabilitiesFound.length}\nReview Required: ${results.requiresSecurityReview}`;
  console.log(`::set-output name=analysis-report::${analysisReport}`);
  
  process.exit(0);
}

// Handle errors gracefully
main().catch(error => {
  console.error('❌ Analysis failed:', error);
  
  // Fallback outputs for GitHub Actions
  console.log('::set-output name=security-score::5.0');
  console.log('::set-output name=vulnerabilities-found::0');
  console.log('::set-output name=requires-security-review::true');
  console.log('::set-output name=recommendations::AI analysis failed - manual review required');
  console.log('::set-output name=analysis-report::AI analysis failed - manual security review required');
  
  process.exit(1);
});
EOF
}

# Function to run the AI security analysis
run_ai_analysis() {
    local changed_files="$1"
    local pr_title="$2"
    local pr_body="$3"
    local risk_level="$4"
    
    log "🤖 Starting AI-powered security analysis..."
    
    # Create the AI analyzer script
    create_ai_analyzer "$changed_files" "$pr_title" "$pr_body" "$risk_level"
    
    # Set environment variables for the Node.js script
    export CHANGED_FILES="$changed_files"
    export PR_TITLE="$pr_title"
    export PR_BODY="$pr_body"
    export RISK_LEVEL="$risk_level"
    
    # Run AI security analysis
    if node ai-security-analyzer.cjs; then
        log "✅ AI security analysis completed successfully"
        return 0
    else
        log "⚠️ AI security analysis failed, fallback analysis provided"
        return 1
    fi
}

# Main execution
main() {
    local changed_files="${1:-[]}"
    local pr_title="${2:-}"
    local pr_body="${3:-}"
    local risk_level="${4:-UNKNOWN}"
    
    log "🚀 PR Security Analysis Script Starting"
    log "PR Title: $pr_title"
    log "Risk Level: $risk_level"
    log "Changed Files Count: $(echo "$changed_files" | jq 'length' 2>/dev/null || echo 'unknown')"
    
    # Check dependencies
    check_dependencies
    
    # Load security context
    load_security_context
    
    # Run AI analysis
    run_ai_analysis "$changed_files" "$pr_title" "$pr_body" "$risk_level"
}

# Trap errors for better debugging
trap 'log "❌ Script failed at line $LINENO"' ERR

# Run main function with all arguments
main "$@"