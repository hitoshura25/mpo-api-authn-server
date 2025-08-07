#!/bin/bash
#
# 3-Tier Security Test Generation Script
#
# This script generates security test implementations for detected vulnerabilities
# using a 3-tier AI system with intelligent mode detection.
# Supports operation modes matching the security analysis workflow:
#   - Standard Mode: Dual AI providers (Anthropic → Gemini → Template)
#   - GEMINI_ONLY_MODE: Skip Anthropic, use Gemini with WebAuthn focus
#   - TEMPLATE_ONLY_MODE: Skip all AI, use template-based test generation
#
# USAGE:
#   ./generate-tests.sh
#   (Requires security-analysis-results.json from previous security analysis)
#
# ENVIRONMENT VARIABLES:
#   ANTHROPIC_API_KEY - API key for Anthropic AI analysis (primary, optional)
#   GEMINI_API_KEY - API key for Google Gemini AI analysis (fallback, optional)
#   GEMINI_ONLY_MODE - Set to "true" to skip Anthropic and use Gemini-only WebAuthn focus
#   TEMPLATE_ONLY_MODE - Set to "true" to skip all AI and use template generation
#
# OUTPUTS:
#   - security-test-implementations.json - Generated test implementations with tier metadata
#
# EXIT CODES:
#   0 - Test generation completed successfully
#   1 - Test generation failed
#

set -euo pipefail

# Mode detection
GEMINI_ONLY_MODE="${GEMINI_ONLY_MODE:-false}"
TEMPLATE_ONLY_MODE="${TEMPLATE_ONLY_MODE:-false}"

# Determine test generation tier
if [ "$TEMPLATE_ONLY_MODE" = "true" ]; then
    TEST_GENERATION_TIER="Tier 3: Template-Based Test Generation"
Elif [ "$GEMINI_ONLY_MODE" = "true" ]; then
    TEST_GENERATION_TIER="Tier 2: Gemini WebAuthn-Focused Test Generation"
else
    TEST_GENERATION_TIER="Standard Mode: Multi-Provider Test Generation"
fi

# Function to log with timestamp and tier info
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$TEST_GENERATION_TIER] - $*"
}

# Function to check if security analysis results exist
check_analysis_results() {
    if [ ! -f "security-analysis-results.json" ]; then
        log "❌ Error: security-analysis-results.json not found"
        log "This script requires previous security analysis results"
        return 1
    fi
    
    local vuln_count
    vuln_count=$(jq '.vulnerabilitiesFound | length' security-analysis-results.json 2>/dev/null || echo 0)
    
    if [ "$vuln_count" -eq 0 ]; then
        log "ℹ️ No vulnerabilities found - no additional tests needed"
        return 2
    fi
    
    log "📊 Found $vuln_count vulnerabilities requiring test generation"
    return 0
}

# Function to create the security test generator Node.js script
create_test_generator() {
    log "🧪 Creating security test generator..."
    
    cat > security-test-generator.cjs << 'EOF'
const fs = require('fs');

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

class SecurityTestGenerator {
  constructor() {
    // Detect test generation mode from environment variables
    this.geminiOnlyMode = process.env.GEMINI_ONLY_MODE === 'true';
    this.templateOnlyMode = process.env.TEMPLATE_ONLY_MODE === 'true';
    
    // Initialize AI clients based on mode
    this.anthropic = null;
    this.gemini = null;
    this.geminiModel = null;
    
    if (this.templateOnlyMode) {
      console.log('📋 Template-Only Mode: Skipping all AI initialization for test generation');
    } else if (this.geminiOnlyMode) {
      console.log('🔷 Gemini-Only Mode: Initializing Gemini for WebAuthn-focused test generation');
      // Only initialize Gemini in Gemini-only mode
      if (GoogleGenerativeAI && process.env.GEMINI_API_KEY) {
        this.gemini = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
        this.geminiModel = this.gemini.getGenerativeModel({ model: 'gemini-1.5-pro' });
      } else {
        console.warn('⚠️ Gemini-Only Mode requested but Gemini not available for test generation');
      }
    } else {
      console.log('🤖 Standard Mode: Initializing all available AI providers for test generation');
      // Initialize Anthropic client if available
      this.anthropic = Anthropic && process.env.ANTHROPIC_API_KEY ? new Anthropic({
        apiKey: process.env.ANTHROPIC_API_KEY
      }) : null;
      
      // Initialize Gemini client if available
      this.gemini = GoogleGenerativeAI && process.env.GEMINI_API_KEY ? new GoogleGenerativeAI(process.env.GEMINI_API_KEY) : null;
      this.geminiModel = this.gemini ? this.gemini.getGenerativeModel({ model: 'gemini-1.5-pro' }) : null;
    }
    
    // Log available providers and mode
    const availableProviders = [];
    if (this.anthropic) availableProviders.push('Anthropic');
    if (this.geminiModel) availableProviders.push('Gemini');
    if (availableProviders.length === 0) availableProviders.push('Template');
    
    let modeDescription = 'Standard';
    if (this.templateOnlyMode) modeDescription = 'Template-Only (Tier 3)';
    else if (this.geminiOnlyMode) modeDescription = 'Gemini-Only (Tier 2)';
    
    console.log(`🔧 Test Generation Mode: ${modeDescription}`);
    console.log(`🔧 AI Providers available: ${availableProviders.join(', ')}`);
  }

  async generateSecurityTests(analysisResults) {
    const vulnerabilities = analysisResults.vulnerabilitiesFound || [];
    const testRecommendations = analysisResults.testRecommendations || [];
    
    if (vulnerabilities.length === 0) {
      console.log('ℹ️ No vulnerabilities found - no additional tests needed');
      return [];
    }
    
    console.log(`🧪 Generating tests for ${vulnerabilities.length} vulnerabilities...`);
    
    const existingTests = this.loadExistingSecurityTests();
    const testImplementations = [];
    
    for (const vuln of vulnerabilities) {
      const testImpl = await this.generateTestForVulnerability(vuln, existingTests);
      testImplementations.push(testImpl);
    }
    
    return testImplementations;
  }

  loadExistingSecurityTests() {
    try {
      const testFile = './webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/security/VulnerabilityProtectionTest.kt';
      return fs.readFileSync(testFile, 'utf8');
    } catch (error) {
      console.warn('⚠️ Could not load existing security tests:', error.message);
      return '';
    }
  }

  async generateTestForVulnerability(vulnerability, existingTests) {
    // Handle Template-Only Mode (Tier 3)
    if (this.templateOnlyMode) {
      console.log(`📋 Template-Only Mode: Generating template for ${vulnerability.type}`);
      return this.generateTestTemplate(vulnerability);
    }
    
    // Handle modes with no AI providers available
    if (!this.anthropic && !this.geminiModel) {
      console.log(`⚠️ No AI providers available, using template for ${vulnerability.type}`);
      return this.generateTestTemplate(vulnerability);
    }

    // Build prompt based on mode
    const prompt = this.geminiOnlyMode 
      ? this.buildWebAuthnTestPrompt(vulnerability, existingTests)
      : this.buildTestGenerationPrompt(vulnerability, existingTests);

    // Try AI generation with provider fallback
    try {
      const result = await this.performAITestGeneration(prompt, vulnerability);
      const provider = result.includes('// Generated by Anthropic') ? 'Anthropic' : 'Gemini';
      const tier = this.geminiOnlyMode ? 'Tier 2 (Gemini WebAuthn-Focused)' : 
                   provider === 'Anthropic' ? 'Tier 1/Standard (Anthropic)' : 'Standard/Fallback (Gemini)';
      
      return {
        vulnerability: vulnerability,
        testImplementation: result,
        generated: true,
        provider: provider,
        tier: tier,
        mode: this.geminiOnlyMode ? 'gemini-only' : 'standard'
      };
    } catch (error) {
      console.error(`❌ AI test generation failed for ${vulnerability.type}:`, error.message);
      return this.generateTestTemplate(vulnerability);
    }
  }

  buildTestGenerationPrompt(vulnerability, existingTests) {
    return `Generate a complete Kotlin test method for this security vulnerability in a WebAuthn authentication server:

VULNERABILITY:
- Type: ${vulnerability.type}
- Severity: ${vulnerability.severity}
- Location: ${vulnerability.location}
- Description: ${vulnerability.description}
- CWE ID: ${vulnerability.cweId || 'N/A'}
- Recommended Fix: ${vulnerability.recommendedFix}

EXISTING TEST CONTEXT:
${existingTests.substring(0, 5000)}

REQUIREMENTS:
1. Generate a complete, runnable Kotlin test method
2. Follow the existing test patterns and structure
3. Use WebAuthnTestHelpers and testStorageModule where appropriate
4. Include proper assertions that verify protection against the vulnerability
5. Add meaningful DisplayName annotation
6. Include comments explaining the vulnerability and protection mechanism

TEST TEMPLATE STRUCTURE:
@Test
@DisplayName("Should protect against [vulnerability type]")
fun \`test protection against [vulnerability name]\`() = testApplication {
    // Test implementation here
}

Focus on creating practical, executable tests that verify security protections are in place.`;
  }

  buildWebAuthnTestPrompt(vulnerability, existingTests) {
    // Specialized prompt for Gemini-only mode with WebAuthn focus
    return `Generate a complete Kotlin test method for this WebAuthn-specific security vulnerability:

🎯 WEBAUTHN VULNERABILITY (Tier 2 Analysis):
- Type: ${vulnerability.type}
- Severity: ${vulnerability.severity}
- Location: ${vulnerability.location}
- Description: ${vulnerability.description}
- WebAuthn Specific: ${vulnerability.webauthnSpecific || 'true'}
- Recommended Fix: ${vulnerability.recommendedFix}

📚 EXISTING WEBAUTHN TEST CONTEXT:
${existingTests.substring(0, 4000)}

🔒 WEBAUTHN-FOCUSED REQUIREMENTS:
1. Generate a complete, executable Kotlin test method targeting WebAuthn vulnerabilities
2. Focus on WebAuthn-specific attack patterns (PoisonSeed, username enumeration, etc.)
3. Use WebAuthnTestHelpers for credential creation and validation
4. Include testStorageModule for proper test isolation
5. Verify WebAuthn ceremony integrity and security boundaries
6. Test both positive (attack blocked) and negative (legitimate flow works) cases
7. Add detailed comments explaining the WebAuthn vulnerability context

🧪 WEBAUTHN TEST TEMPLATE:
@Test
@DisplayName("Should protect against ${vulnerability.type} in WebAuthn flow")
fun \`test webauthn protection against [specific attack]\`() = testApplication {
    application {
        testStorageModule()
    }
    
    // WebAuthn-specific test implementation
    // Focus on: credential validation, origin checks, challenge verification
}

💡 FOCUS: Assume general security (SQL injection, XSS) is handled elsewhere.
EMPHASIZE: WebAuthn protocol security, FIDO2 compliance, and authentication ceremony protection.`;
  }

  async performAITestGeneration(prompt, vulnerability) {
    // Handle Gemini-Only Mode (Tier 2)
    if (this.geminiOnlyMode) {
      if (this.geminiModel) {
        try {
          console.log(`🔷 Gemini-Only Mode: Generating WebAuthn test for ${vulnerability.type}...`);
          return await this.performGeminiTestGeneration(prompt);
        } catch (error) {
          console.warn(`❌ Gemini-only test generation failed: ${error.message}`);
          throw error;
        }
      } else {
        throw new Error('Gemini-only mode requested but Gemini not available');
      }
    }
    
    // Standard Mode: Try Anthropic first (primary provider)
    if (this.anthropic) {
      try {
        console.log(`🚀 Generating test for ${vulnerability.type} with Anthropic (primary)...`);
        return await this.performAnthropicTestGeneration(prompt);
      } catch (error) {
        console.warn(`🔄 Anthropic test generation failed: ${error.message}`);
        if (this.isRateLimitOrBudgetError(error)) {
          console.log('💸 Anthropic budget/rate limit exceeded, trying Gemini...');
        }
      }
    }
    
    // Fallback to Gemini (secondary provider)
    if (this.geminiModel) {
      try {
        console.log(`🔄 Generating test for ${vulnerability.type} with Gemini (fallback)...`);
        return await this.performGeminiTestGeneration(prompt);
      } catch (error) {
        console.warn(`❌ Gemini test generation failed: ${error.message}`);
      }
    }
    
    // All AI providers failed
    throw new Error('All AI providers failed for test generation');
  }

  async performAnthropicTestGeneration(prompt) {
    const response = await this.anthropic.messages.create({
      model: 'claude-opus-4-1-20250805',
      max_tokens: 2000,
      temperature: 0.2,
      messages: [{
        role: 'user',
        content: prompt
      }]
    });

    console.log('✅ Anthropic test generation completed successfully');
    return `// Generated by Anthropic\n${response.content[0].text}`;
  }

  async performGeminiTestGeneration(prompt) {
    const geminiPrompt = `${prompt}

IMPORTANT: Provide only the Kotlin test method code, with no additional explanations or markdown formatting.`;
    
    const result = await this.geminiModel.generateContent(geminiPrompt);
    const response = await result.response;
    
    console.log('✅ Gemini test generation completed successfully');
    return `// Generated by Gemini\n${response.text()}`;
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

  generateTestTemplate(vulnerability) {
    const testName = vulnerability.type.toLowerCase().replace(/[^a-z0-9]/g, '_');
    const testImplementation = `@Test
@DisplayName("Should protect against ${vulnerability.type}")
fun \`test protection against ${testName}\`() = testApplication {
    // TODO: Implement test for ${vulnerability.type}
    // Vulnerability: ${vulnerability.description}
    // Location: ${vulnerability.location}
    // Severity: ${vulnerability.severity}
    // 
    // Recommended fix: ${vulnerability.recommendedFix}
    // 
    // This test should verify that the system properly protects against:
    // ${vulnerability.description}
    
    application {
        testStorageModule()
    }
    
    // Add test implementation here
    // Example structure:
    // 1. Set up test conditions that would trigger the vulnerability
    // 2. Make request that attempts to exploit the vulnerability  
    // 3. Assert that the system properly rejects/handles the attack
    // 4. Verify no sensitive information is leaked
    
    fail("Test implementation required for ${vulnerability.type}")
}`;

    const availableProviders = [];
    if (this.anthropic) availableProviders.push('Anthropic');
    if (this.geminiModel) availableProviders.push('Gemini');
    
    const availableProviders = [];
    if (this.anthropic) availableProviders.push('Anthropic');
    if (this.geminiModel) availableProviders.push('Gemini');
    
    const errorMessage = this.templateOnlyMode 
      ? 'Template-Only Mode (Tier 3) - no AI providers used by design'
      : availableProviders.length === 0 
        ? 'No AI providers configured - template provided'
        : `AI providers failed (${availableProviders.join(', ')}) - template provided`;
    
    const tier = this.templateOnlyMode ? 'Tier 3 (Template-Only)' : 'Tier 3 (Fallback)';

    return {
      vulnerability: vulnerability,
      testImplementation: testImplementation,
      generated: false,
      template: true,
      error: errorMessage,
      providersAttempted: availableProviders,
      tier: tier,
      mode: this.templateOnlyMode ? 'template-only' : 'fallback'
    };
  }
}

// Main execution
async function main() {
  const generator = new SecurityTestGenerator();
  
  // Load analysis results
  const analysisResults = JSON.parse(fs.readFileSync('security-analysis-results.json', 'utf8'));
  
  // Generate test implementations
  const testImplementations = await generator.generateSecurityTests(analysisResults);
  
  // Determine which tier was used for test generation
  const tierUsed = process.env.TEMPLATE_ONLY_MODE === 'true' ? 'Tier 3 (Template-Only)' :
                   process.env.GEMINI_ONLY_MODE === 'true' ? 'Tier 2 (Gemini WebAuthn-Focused)' :
                   'Standard Multi-Provider';
  
  // Write test implementations to file with tier metadata
  const testReport = {
    timestamp: new Date().toISOString(),
    tierUsed: tierUsed,
    mode: process.env.TEMPLATE_ONLY_MODE === 'true' ? 'template-only' :
           process.env.GEMINI_ONLY_MODE === 'true' ? 'gemini-only' : 'standard',
    vulnerabilityCount: analysisResults.vulnerabilitiesFound.length,
    testImplementations: testImplementations,
    summary: {
      totalTests: testImplementations.length,
      generatedTests: testImplementations.filter(t => t.generated).length,
      templateTests: testImplementations.filter(t => t.template).length,
      failedGenerations: testImplementations.filter(t => t.error && !t.template).length,
      tierBreakdown: {
        tier1: testImplementations.filter(t => t.provider === 'Anthropic').length,
        tier2: testImplementations.filter(t => t.provider === 'Gemini').length,
        tier3: testImplementations.filter(t => t.template).length
      }
    }
  };
  
  fs.writeFileSync('security-test-implementations.json', JSON.stringify(testReport, null, 2));
  
  console.log('📋 Test Generation Summary:');
  console.log(`🎯 Tier Used: ${testReport.tierUsed}`);
  console.log(`🔧 Mode: ${testReport.mode}`);
  console.log(`📊 Total vulnerabilities: ${testReport.vulnerabilityCount}`);
  console.log(`🧪 Tests generated: ${testReport.summary.generatedTests}`);
  console.log(`📋 Template tests: ${testReport.summary.templateTests}`);
  console.log(`❌ Generation failures: ${testReport.summary.failedGenerations}`);
  console.log(`🏷️ Tier breakdown: T1=${testReport.summary.tierBreakdown.tier1}, T2=${testReport.summary.tierBreakdown.tier2}, T3=${testReport.summary.tierBreakdown.tier3}`);
}

main().catch(error => {
  console.error('❌ Test generation failed:', error);
  process.exit(1);
});
EOF
}

# Function to run the test generator
run_test_generator() {
    log "🧪 Running security test generator..."
    
    # Create the test generator script
    create_test_generator
    
    # Install AI dependencies if not already available
    local need_install=false
    if ! npm list @anthropic-ai/sdk &>/dev/null; then
        need_install=true
    fi
    if ! npm list @google/generative-ai &>/dev/null; then
        need_install=true
    fi
    
    if [ "$need_install" = true ]; then
        log "📦 Installing AI dependencies..."
        npm install @anthropic-ai/sdk @google/generative-ai || log "⚠️ Failed to install AI SDKs, using templates"
    fi
    
    # Run test generator
    if node security-test-generator.cjs; then
        log "✅ Security test generation completed successfully"
        return 0
    else
        log "❌ Security test generation failed"
        return 1
    fi
}

# Main execution
main() {
    log "🚀 Security Test Generation Script Starting"
    
    # Check if analysis results exist
    local analysis_status
    if check_analysis_results; then
        analysis_status=$?
    else
        analysis_status=$?
    fi
    
    case $analysis_status in
        0)
            # Vulnerabilities found, proceed with test generation
            run_test_generator
            ;;
        2)
            # No vulnerabilities found, create empty report
            log "📝 Creating empty test report..."
            cat > security-test-implementations.json << EOF
{
  "timestamp": "$(date -Iseconds)",
  "tierUsed": "$TEST_GENERATION_TIER",
  "mode": "${TEMPLATE_ONLY_MODE:+template-only}${GEMINI_ONLY_MODE:+gemini-only}${TEMPLATE_ONLY_MODE:+${GEMINI_ONLY_MODE:+}}${TEMPLATE_ONLY_MODE:-${GEMINI_ONLY_MODE:-standard}}",
  "vulnerabilityCount": 0,
  "testImplementations": [],
  "summary": {
    "totalTests": 0,
    "generatedTests": 0,
    "templateTests": 0,
    "failedGenerations": 0,
    "tierBreakdown": {
      "tier1": 0,
      "tier2": 0,
      "tier3": 0
    }
  },
  "message": "No vulnerabilities found - no tests generated"
}
EOF
            log "✅ Empty test report created"
            ;;
        *)
            # Error occurred
            exit 1
            ;;
    esac
}

# Trap errors for better debugging
trap 'log "❌ Script failed at line $LINENO"' ERR

# Run main function
main