#!/bin/bash
#
# AI-Powered PR Security Analysis Script
#
# This script performs intelligent security analysis on pull requests using AI
# to detect WebAuthn vulnerabilities, security anti-patterns, and potential attack vectors.
# Supports dual AI providers with automatic fallback: Anthropic (primary) → Gemini (fallback) → Template analysis
#
# USAGE:
#   ./analyze-pr.sh <changed_files_json> <pr_title> <pr_body> <risk_level>
#
# ENVIRONMENT VARIABLES:
#   ANTHROPIC_API_KEY - API key for Anthropic AI analysis (primary, optional)
#   GEMINI_API_KEY - API key for Google Gemini AI analysis (fallback, optional)
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
    
    # Check if AI dependencies are available
    local need_install=false
    if [ ! -d "node_modules/@anthropic-ai/sdk" ] && [ ! -d "../node_modules/@anthropic-ai/sdk" ]; then
        need_install=true
    fi
    if [ ! -d "node_modules/@google/generative-ai" ] && [ ! -d "../node_modules/@google/generative-ai" ]; then
        need_install=true
    fi
    
    if [ "$need_install" = true ]; then
        log "⚠️ Installing AI analysis dependencies..."
        npm install --save-dev \
            @anthropic-ai/sdk \
            @google/generative-ai \
            typescript \
            ts-node \
            @types/node || log "⚠️ Failed to install dependencies, continuing with fallback analysis"
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

// Try to import AI SDKs, fall back if not available
let Anthropic, GoogleGenerativeAI;
try {
  Anthropic = require('@anthropic-ai/sdk').Anthropic;
} catch (error) {
  console.warn('⚠️ Anthropic SDK not available');
  Anthropic = null;
}

try {
  const { GoogleGenerativeAI: GeminiAI } = require('@google/generative-ai');
  GoogleGenerativeAI = GeminiAI;
} catch (error) {
  console.warn('⚠️ Google Generative AI SDK not available');
  GoogleGenerativeAI = null;
}

class WebAuthnSecurityAnalyzer {
  constructor() {
    // Initialize Anthropic client if available
    this.anthropic = Anthropic && process.env.ANTHROPIC_API_KEY ? new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY
    }) : null;
    
    // Initialize Gemini client if available
    this.gemini = GoogleGenerativeAI && process.env.GEMINI_API_KEY ? new GoogleGenerativeAI(process.env.GEMINI_API_KEY) : null;
    this.geminiModel = this.gemini ? this.gemini.getGenerativeModel({ model: 'gemini-1.5-pro' }) : null;
    
    this.maxRetries = 3;
    this.retryDelay = 2000;
    
    // Log available providers
    const availableProviders = [];
    if (this.anthropic) availableProviders.push('Anthropic');
    if (this.geminiModel) availableProviders.push('Gemini');
    if (availableProviders.length === 0) availableProviders.push('Fallback');
    
    console.log(`🔧 AI Providers available: ${availableProviders.join(', ')}`);
  }

  async analyzeSecurityChanges(changedFiles, prContext) {
    try {
      console.log('🔍 Analyzing security implications of code changes...');
      
      if (!this.anthropic && !this.geminiModel) {
        console.log('⚠️ No AI providers available, using fallback analysis');
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
      
      const { analysis, provider } = await this.performAIAnalysis(prompt);
      const results = this.parseAnalysisResults(analysis);
      
      // Add metadata about which provider was used
      results.analysisMetadata = {
        aiProvider: provider,
        timestamp: new Date().toISOString(),
        analysisType: 'ai-powered'
      };
      
      console.log(`📊 Analysis completed using: ${provider}`);
      return results;
      
    } catch (error) {
      console.error('❌ AI analysis failed:', error.message);
      const fallbackResults = this.createFallbackAnalysis();
      
      // Add metadata about fallback analysis
      fallbackResults.analysisMetadata = {
        aiProvider: 'None (Template-based analysis)',
        timestamp: new Date().toISOString(),
        analysisType: 'template-fallback',
        reason: error.message
      };
      
      console.log('📊 Analysis completed using: Template-based fallback');
      return fallbackResults;
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
    // Try Anthropic first (primary provider)
    if (this.anthropic) {
      try {
        console.log('🚀 Attempting analysis with Anthropic (primary)...');
        const analysis = await this.performAnthropicAnalysis(prompt);
        return { analysis, provider: 'Anthropic Claude Opus 4.1' };
      } catch (error) {
        console.warn('🔄 Anthropic analysis failed:', error.message);
        if (this.isRateLimitOrBudgetError(error)) {
          console.log('💸 Anthropic budget/rate limit exceeded, trying Gemini...');
        }
      }
    }
    
    // Fallback to Gemini (secondary provider)
    if (this.geminiModel) {
      try {
        console.log('🔷 Switching to Gemini (fallback provider)...');
        console.log('🔷 Gemini model: gemini-1.5-pro');
        const analysis = await this.performGeminiAnalysis(prompt);
        console.log('✅ Gemini analysis completed successfully - switching back to main flow');
        return { analysis, provider: 'Google Gemini 1.5 Pro' };
      } catch (error) {
        console.warn('❌ Gemini analysis failed:', error.message);
        console.warn('❌ Both Anthropic and Gemini failed - falling back to template analysis');
      }
    } else {
      console.log('⚠️ Gemini not configured (GEMINI_API_KEY missing) - skipping to template fallback');
    }
    
    // Both AI providers failed
    throw new Error('All AI providers failed, using fallback analysis');
  }

  async performAnthropicAnalysis(prompt) {
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        console.log(`🤖 Anthropic attempt ${attempt}/${this.maxRetries}...`);
        
        const message = await this.anthropic.messages.create({
          model: 'claude-opus-4-1-20250805',
          max_tokens: 4000,
          temperature: 0.1, // Low temperature for consistent security analysis
          messages: [{
            role: 'user',
            content: prompt
          }]
        });

        console.log('✅ Anthropic analysis completed successfully');
        return message.content[0].text;
        
      } catch (error) {
        console.warn(`⚠️ Anthropic attempt ${attempt} failed:`, error.message);
        
        // Don't retry on budget/auth errors
        if (this.isRateLimitOrBudgetError(error)) {
          throw error;
        }
        
        if (attempt === this.maxRetries) {
          throw error;
        }
        
        await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempt));
      }
    }
  }

  async performGeminiAnalysis(prompt) {
    console.log('🔷 Starting Gemini analysis process...');
    console.log(`🔷 Gemini prompt length: ${prompt.length} characters`);
    
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        console.log(`🔷 Gemini analysis attempt ${attempt}/${this.maxRetries}...`);
        
        // Adapt prompt for Gemini format
        const geminiPrompt = this.adaptPromptForGemini(prompt);
        console.log('🔷 Sending request to Gemini 1.5 Pro...');
        
        const result = await this.geminiModel.generateContent(geminiPrompt);
        const response = await result.response;
        const responseText = response.text();
        
        console.log('✅ Gemini response received successfully');
        console.log(`✅ Gemini response length: ${responseText.length} characters`);
        console.log('✅ Gemini analysis completed - parsing results...');
        
        return responseText;
        
      } catch (error) {
        console.warn(`⚠️ Gemini attempt ${attempt} failed:`, error.message);
        
        // Don't retry on quota/auth errors
        if (this.isRateLimitOrBudgetError(error)) {
          throw error;
        }
        
        if (attempt === this.maxRetries) {
          throw error;
        }
        
        await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempt));
      }
    }
  }

  adaptPromptForGemini(prompt) {
    // Gemini works well with the same prompt format, but we can add specific instructions
    return `${prompt}

IMPORTANT: Provide your response as valid JSON only, with no additional text or explanations outside the JSON structure.`;
  }

  isRateLimitOrBudgetError(error) {
    const errorMessage = error.message?.toLowerCase() || '';
    const errorStatus = error.status || error.code || 0;
    
    // Check for common rate limit/budget error indicators
    return (
      errorStatus === 429 || // Rate limit
      errorStatus === 402 || // Payment required
      errorMessage.includes('rate limit') ||
      errorMessage.includes('quota') ||
      errorMessage.includes('budget') ||
      errorMessage.includes('billing') ||
      errorMessage.includes('insufficient credits') ||
      errorMessage.includes('usage limit')
    );
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
    const availableProviders = [];
    if (this.anthropic) availableProviders.push('Anthropic');
    if (this.geminiModel) availableProviders.push('Gemini');
    
    const analysisError = availableProviders.length === 0 
      ? 'No AI providers configured - template analysis provided'
      : `AI providers failed (${availableProviders.join(', ')}) - template analysis provided`;
    
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
      analysisError: analysisError,
      providersAttempted: availableProviders
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
  
  if (results.analysisMetadata) {
    console.log(`🤖 Analysis Provider: ${results.analysisMetadata.aiProvider}`);
    console.log(`📅 Analysis Timestamp: ${results.analysisMetadata.timestamp}`);
    console.log(`🔧 Analysis Type: ${results.analysisMetadata.analysisType}`);
  }
  
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