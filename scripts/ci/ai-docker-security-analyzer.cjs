#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Try to import AI SDKs with cross-platform fetch helpers, fall back if not available
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

/**
 * 3-Tier AI Docker Security Analyzer
 * 
 * Advanced Docker security scan analysis using a sophisticated 3-tier AI system:
 * - Tier 1: Anthropic Claude (Primary) - Comprehensive Docker security analysis
 * - Tier 2: Google Gemini (Fallback) - Docker-focused vulnerability assessment 
 * - Tier 3: Template Analysis (Final Fallback) - Pattern-based Docker security checks
 *
 * TIER MODES:
 *   Default Mode: Multi-provider analysis (Anthropic → Gemini → Template)
 *   GEMINI_ONLY_MODE: Skip Anthropic, use Gemini with Docker container focus
 *   TEMPLATE_ONLY_MODE: Skip all AI, use template-based Docker security patterns
 *
 * USAGE:
 *   node ai-docker-security-analyzer.cjs
 *   (Uses scan results from environment variables or files)
 * 
 * ENVIRONMENT VARIABLES:
 *   - SCAN_RESULTS - JSON string with scan results (fallback)
 *   - CRITICAL_VULN_COUNT - Number of critical vulnerabilities
 *   - ANTHROPIC_API_KEY - API key for Anthropic AI analysis (primary, optional)
 *   - GEMINI_API_KEY - API key for Google Gemini AI analysis (fallback, optional)
 *   - GEMINI_ONLY_MODE - Set to "true" to skip Anthropic and use Gemini-only Docker focus
 *   - TEMPLATE_ONLY_MODE - Set to "true" to skip all AI and use template analysis
 *   - VULNERABILITY_DB_PATH - Path to vulnerability database JSON
 * 
 * INPUT FILES:
 *   - docker-security-scan-results.json - Primary scan results file
 * 
 * OUTPUT FILES:
 *   - ai-security-analysis.json - AI analysis results with tier metadata
 * 
 * OUTPUTS:
 *   - GitHub Actions output variables for workflow decisions
 *   - Structured JSON analysis for security team review
 *   - Analysis tier metadata and AI provider information
 *
 * EXIT CODES:
 *   0 - Analysis completed successfully
 *   1 - Analysis failed (fallback analysis provided)
 */
class AIDockerSecurityAnalyzer {
    constructor() {
        // Detect analysis mode from environment variables
        this.geminiOnlyMode = process.env.GEMINI_ONLY_MODE === 'true';
        this.templateOnlyMode = process.env.TEMPLATE_ONLY_MODE === 'true';
        
        // Initialize AI clients based on mode
        this.anthropic = null;
        this.gemini = null;
        this.geminiModel = null;
        
        if (this.templateOnlyMode) {
            console.log('📋 Template-Only Mode: Skipping all AI initialization');
        } else if (this.geminiOnlyMode) {
            console.log('🔷 Gemini-Only Mode: Initializing Gemini for Docker-focused analysis');
            // Only initialize Gemini in Gemini-only mode
            if (GoogleGenerativeAI && process.env.GEMINI_API_KEY) {
                this.gemini = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
                this.geminiModel = this.gemini.getGenerativeModel({ model: 'gemini-1.5-pro' });
            } else {
                console.warn('⚠️ Gemini-Only Mode requested but Gemini not available');
            }
        } else {
            console.log('🤖 Standard Mode: Initializing all available AI providers');
            // Initialize Anthropic client if available
            this.anthropic = Anthropic && process.env.ANTHROPIC_API_KEY ? new Anthropic({
                apiKey: process.env.ANTHROPIC_API_KEY
            }) : null;
            
            // Initialize Gemini client if available
            this.gemini = GoogleGenerativeAI && process.env.GEMINI_API_KEY ? new GoogleGenerativeAI(process.env.GEMINI_API_KEY) : null;
            this.geminiModel = this.gemini ? this.gemini.getGenerativeModel({ model: 'gemini-1.5-pro' }) : null;
        }
        
        this.maxRetries = 3;
        this.retryDelay = 2000;
        this.scanResults = this.loadScanResults();
        
        // Log available providers and mode
        const availableProviders = [];
        if (this.anthropic) availableProviders.push('Anthropic');
        if (this.geminiModel) availableProviders.push('Gemini');
        if (availableProviders.length === 0) availableProviders.push('Template');
        
        let modeDescription = 'Standard';
        if (this.templateOnlyMode) modeDescription = 'Template-Only (Tier 3)';
        else if (this.geminiOnlyMode) modeDescription = 'Gemini-Only (Tier 2)';
        
        console.log('🐳 3-Tier AI Docker Security Analyzer initialized');
        console.log(`🔧 Analysis Mode: ${modeDescription}`);
        console.log(`🔧 AI Providers available: ${availableProviders.join(', ')}`);
        console.log(`📂 Scan Results Loaded: ${this.scanResults.scans ? 'Yes' : 'No'}`);
    }

    loadScanResults() {
        try {
            if (fs.existsSync('docker-security-scan-results.json')) {
                console.log('📂 Loading scan results from docker-security-scan-results.json');
                return JSON.parse(fs.readFileSync('docker-security-scan-results.json', 'utf8'));
            }
            
            if (process.env.SCAN_RESULTS) {
                console.log('📂 Loading scan results from SCAN_RESULTS environment variable');
                return JSON.parse(process.env.SCAN_RESULTS);
            }
            
            console.warn('⚠️ No scan results found in file or environment variable');
            return { scans: [] };
        } catch (error) {
            console.warn('⚠️ Could not load scan results:', error.message);
            return { scans: [] };
        }
    }

    async analyzeSecurityFindings() {
        console.log('🔍 Analyzing Docker security findings with 3-tier AI system...');

        if (!this.scanResults.scans || this.scanResults.scans.length === 0) {
            console.log('ℹ️ No scan results to analyze');
            return this.createEmptyAnalysis();
        }

        try {
            // Handle Template-Only Mode (Tier 3)
            if (this.templateOnlyMode) {
                console.log('📋 Template-Only Mode: Using template-based Docker security analysis');
                return this.createTemplateAnalysis();
            }

            // Load security context
            const vulnerabilityDB = this.loadVulnerabilityDatabase();
            const dockerSecurityContext = this.buildDockerSecurityContext();

            // Prepare scan summary for AI analysis
            const scanSummary = this.prepareScanSummaryForAI();

            // Token optimization: Skip AI for minimal risk scans (except in Gemini-only mode)
            if (!this.geminiOnlyMode && this.isMinimalRiskScan()) {
                console.log('💡 Minimal risk scan detected - using optimized template analysis');
                const optimizedResults = this.createTemplateAnalysis();
                optimizedResults.analysisMetadata = {
                    aiProvider: 'Template (optimized for minimal risk)',
                    timestamp: new Date().toISOString(),
                    analysisType: 'optimized-template',
                    reason: 'Minimal risk scan - AI analysis skipped for cost optimization',
                    tier: 'Tier 3 (Optimized)'
                };
                return optimizedResults;
            }

            // Build AI prompt based on analysis mode
            const prompt = this.geminiOnlyMode
                ? this.buildDockerFocusedPrompt(vulnerabilityDB, dockerSecurityContext, scanSummary)
                : this.buildDockerSecurityPrompt(vulnerabilityDB, dockerSecurityContext, scanSummary);

            // Log token estimate for cost tracking
            const estimatedTokens = Math.ceil(prompt.length / 4); // Rough token estimate
            console.log(`💰 Estimated tokens: ~${estimatedTokens} (${(estimatedTokens * 0.000015).toFixed(4)} USD for Claude Opus 4.1)`);

            const { analysis, provider } = await this.performAIAnalysis(prompt);
            const results = this.parseAIAnalysisResults(analysis);

            // Enhance results with traditional analysis
            this.enhanceWithTraditionalAnalysis(results);

            // Add metadata about which provider was used and analysis tier
            results.analysisMetadata = {
                aiProvider: provider,
                timestamp: new Date().toISOString(),
                analysisType: 'ai-powered',
                estimatedTokens: estimatedTokens,
                tier: this.geminiOnlyMode ? 'Tier 2 (Gemini Docker-Focused)' : 'Tier 1 (Multi-Provider)',
                mode: this.geminiOnlyMode ? 'gemini-only' : 'standard'
            };

            console.log(`📊 Analysis completed using: ${provider}`);
            console.log(`📊 Docker Security Analysis Summary:`);
            console.log(`   Images analyzed: ${results.imageAnalysis?.length || 0}`);
            console.log(`   Overall risk: ${results.riskAssessment}`);
            console.log(`   Action required: ${results.actionRequired}`);
            console.log(`   Recommendations: ${results.recommendations?.length || 0}`);

            // Save analysis results
            fs.writeFileSync('ai-security-analysis.json', JSON.stringify(results, null, 2));

            return results;

        } catch (error) {
            console.error('❌ AI Docker analysis failed:', error.message);
            const fallbackResults = this.createTemplateAnalysis();

            // Add metadata about fallback analysis
            fallbackResults.analysisMetadata = {
                aiProvider: 'None (Template-based analysis)',
                timestamp: new Date().toISOString(),
                analysisType: 'template-fallback',
                reason: error.message,
                tier: 'Tier 3 (Fallback)',
                mode: this.templateOnlyMode ? 'template-only' : 'fallback'
            };

            console.log('📊 Analysis completed using: Template-based fallback');
            console.log(`📊 Docker Security Analysis Summary:`);
            console.log(`   Images analyzed: ${fallbackResults.imageAnalysis?.length || 0}`);
            console.log(`   Overall risk: ${fallbackResults.riskAssessment}`);
            console.log(`   Action required: ${fallbackResults.actionRequired}`);
            console.log(`   Recommendations: ${fallbackResults.recommendations?.length || 0}`);

            // Save fallback analysis results
            fs.writeFileSync('ai-security-analysis.json', JSON.stringify(fallbackResults, null, 2));

            return fallbackResults;
        }
    }

    analyzeImageScanTraditional(scan) {
        console.log(`🔍 Traditional analysis for image: ${scan.image || 'Unknown'}`);
        
        const analysis = {
            image: scan.image,
            riskLevel: 'LOW',
            vulnerabilities: {
                critical: 0,
                high: 0,
                medium: 0,
                low: 0,
                total: 0
            },
            securityIssues: [],
            recommendations: []
        };

        // Analyze vulnerabilities
        if (scan.scans && scan.scans.vulnerabilities) {
            this.analyzeVulnerabilities(scan.scans.vulnerabilities, analysis);
        }

        // Analyze secrets
        if (scan.scans && scan.scans.secrets) {
            this.analyzeSecrets(scan.scans.secrets, analysis);
        }

        // Analyze configuration
        if (scan.scans && scan.scans.config) {
            this.analyzeConfiguration(scan.scans.config, analysis);
        }

        // Determine overall risk level for image
        if (analysis.vulnerabilities.critical > 0) {
            analysis.riskLevel = 'CRITICAL';
        } else if (analysis.vulnerabilities.high > 5) {
            analysis.riskLevel = 'HIGH';
        } else if (analysis.vulnerabilities.high > 0 || analysis.vulnerabilities.medium > 10) {
            analysis.riskLevel = 'MEDIUM';
        }

        console.log(`   Traditional Risk Level: ${analysis.riskLevel}`);
        console.log(`   Traditional Vulnerabilities: ${analysis.vulnerabilities.critical}C, ${analysis.vulnerabilities.high}H, ${analysis.vulnerabilities.medium}M, ${analysis.vulnerabilities.low}L`);
        console.log(`   Traditional Security Issues: ${analysis.securityIssues.length}`);

        return analysis;
    }

    analyzeVulnerabilities(vulnScan, analysis) {
        if (!vulnScan.Results) {
            console.log('   No vulnerability results found');
            return;
        }

        for (const result of vulnScan.Results) {
            if (!result.Vulnerabilities) continue;

            for (const vuln of result.Vulnerabilities) {
                analysis.vulnerabilities.total++;

                switch (vuln.Severity) {
                    case 'CRITICAL':
                        analysis.vulnerabilities.critical++;
                        analysis.securityIssues.push({
                            type: 'vulnerability',
                            severity: 'CRITICAL',
                            title: vuln.Title || vuln.VulnerabilityID,
                            description: vuln.Description,
                            package: vuln.PkgName,
                            installedVersion: vuln.InstalledVersion,
                            fixedVersion: vuln.FixedVersion
                        });
                        break;
                    case 'HIGH':
                        analysis.vulnerabilities.high++;
                        break;
                    case 'MEDIUM':
                        analysis.vulnerabilities.medium++;
                        break;
                    case 'LOW':
                        analysis.vulnerabilities.low++;
                        break;
                }
            }
        }

        console.log(`   Processed ${analysis.vulnerabilities.total} vulnerabilities from ${vulnScan.Results.length} scan results`);
    }

    analyzeSecrets(secretScan, analysis) {
        if (!secretScan.Results) {
            console.log('   No secret scan results found');
            return;
        }

        let secretCount = 0;
        for (const result of secretScan.Results) {
            if (!result.Secrets) continue;

            for (const secret of result.Secrets) {
                secretCount++;
                analysis.securityIssues.push({
                    type: 'secret',
                    severity: 'HIGH',
                    title: `Potential secret: ${secret.Title}`,
                    description: `Found potential secret in ${result.Target}`,
                    location: result.Target,
                    rule: secret.RuleID
                });
            }
        }

        console.log(`   Found ${secretCount} potential secrets`);
    }

    analyzeConfiguration(configScan, analysis) {
        if (!configScan.Results) {
            console.log('   No configuration scan results found');
            return;
        }

        let configIssueCount = 0;
        for (const result of configScan.Results) {
            if (!result.Misconfigurations) continue;

            for (const config of result.Misconfigurations) {
                if (config.Severity === 'HIGH' || config.Severity === 'CRITICAL') {
                    configIssueCount++;
                    analysis.securityIssues.push({
                        type: 'misconfiguration',
                        severity: config.Severity,
                        title: config.Title,
                        description: config.Description,
                        location: result.Target,
                        resolution: config.Resolution
                    });
                }
            }
        }

        console.log(`   Found ${configIssueCount} high/critical configuration issues`);
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

    buildDockerSecurityContext() {
        return {
            containerSecurity: [
                'Docker image vulnerability scanning',
                'Container secrets management',
                'Docker configuration security',
                'Base image security hardening',
                'Runtime security monitoring'
            ],
            commonThreats: [
                'Vulnerable base images and packages',
                'Hardcoded secrets in containers',
                'Insecure container configurations',
                'Privilege escalation attacks',
                'Container escape vulnerabilities'
            ]
        };
    }

    prepareScanSummaryForAI() {
        const scanSummary = {
            totalImages: this.scanResults.scans?.length || 0,
            totalVulns: 0,
            criticalVulns: 0,
            highVulns: 0,
            secretsFound: 0,
            configIssues: 0,
            images: []
        };

        for (const scan of this.scanResults.scans || []) {
            const imageData = {
                image: scan.image,
                vulnerabilities: { critical: 0, high: 0, medium: 0, low: 0 },
                secrets: 0,
                misconfigs: 0,
                criticalDetails: []
            };

            // Count vulnerabilities
            if (scan.scans?.vulnerabilities?.Results) {
                for (const result of scan.scans.vulnerabilities.Results) {
                    if (result.Vulnerabilities) {
                        for (const vuln of result.Vulnerabilities) {
                            imageData.vulnerabilities[vuln.Severity.toLowerCase()]++;
                            scanSummary.totalVulns++;

                            if (vuln.Severity === 'CRITICAL') {
                                scanSummary.criticalVulns++;
                                imageData.criticalDetails.push({
                                    id: vuln.VulnerabilityID,
                                    title: vuln.Title,
                                    package: vuln.PkgName,
                                    version: vuln.InstalledVersion,
                                    fixedVersion: vuln.FixedVersion
                                });
                            } else if (vuln.Severity === 'HIGH') {
                                scanSummary.highVulns++;
                            }
                        }
                    }
                }
            }

            // Count secrets
            if (scan.scans?.secrets?.Results) {
                for (const result of scan.scans.secrets.Results) {
                    if (result.Secrets) {
                        imageData.secrets += result.Secrets.length;
                        scanSummary.secretsFound += result.Secrets.length;
                    }
                }
            }

            // Count misconfigurations
            if (scan.scans?.config?.Results) {
                for (const result of scan.scans.config.Results) {
                    if (result.Misconfigurations) {
                        imageData.misconfigs += result.Misconfigurations.length;
                        scanSummary.configIssues += result.Misconfigurations.length;
                    }
                }
            }

            scanSummary.images.push(imageData);
        }

        return scanSummary;
    }

    isMinimalRiskScan() {
        const scanSummary = this.prepareScanSummaryForAI();
        return scanSummary.criticalVulns === 0 && 
               scanSummary.highVulns <= 2 && 
               scanSummary.secretsFound === 0 &&
               scanSummary.totalImages <= 2;
    }

    buildDockerSecurityPrompt(vulnerabilityDB, dockerContext, scanSummary) {
        const relevantVulns = vulnerabilityDB.vulnerabilities?.slice(0, 3) || [];
        
        return `Docker Container Security Analysis (${scanSummary.totalImages} images scanned)

KEY VULNERABILITIES TO CHECK:
${relevantVulns.map(v => `• ${v.type}: ${v.description?.substring(0, 80)}...`).join('\n')}

DOCKER SECURITY CONTEXT:
• Container Threats: ${dockerContext.commonThreats.join(', ')}
• Security Areas: ${dockerContext.containerSecurity.join(', ')}

SCAN RESULTS SUMMARY:
• Total Images: ${scanSummary.totalImages}
• Critical Vulnerabilities: ${scanSummary.criticalVulns}
• High Vulnerabilities: ${scanSummary.highVulns}
• Secrets Found: ${scanSummary.secretsFound}
• Configuration Issues: ${scanSummary.configIssues}

IMAGE DETAILS:
${scanSummary.images.map(img => 
`--- ${img.image} ---
• Vulnerabilities: ${img.vulnerabilities.critical}C, ${img.vulnerabilities.high}H, ${img.vulnerabilities.medium}M
• Secrets: ${img.secrets}, Misconfigs: ${img.misconfigs}
${img.criticalDetails.length > 0 ? `• Critical Issues: ${img.criticalDetails.map(c => `${c.id} (${c.package})`).join(', ')}` : ''}`
).join('\n\n')}

ANALYZE FOR:
- Container vulnerability risk assessment
- Docker security best practices compliance
- Secret exposure in container layers
- Configuration security issues
- Base image security hardening needs
- Container runtime security risks

JSON RESPONSE:
{
  "securityScore": <0-10>,
  "riskAssessment": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "actionRequired": <boolean>,
  "vulnerabilitiesFound": [{"type":"", "severity":"", "location":"", "description":"", "recommendedFix":""}],
  "recommendations": ["specific Docker security fixes"],
  "dockerSpecificRisks": {"baseImageRisks":[], "secretExposure":[], "configurationIssues":[]},
  "imageAnalysis": [{"image":"", "riskLevel":"", "criticalIssues":[], "recommendations":[]}]
}`;
    }

    buildDockerFocusedPrompt(vulnerabilityDB, dockerContext, scanSummary) {
        const dockerVulns = vulnerabilityDB.vulnerabilities?.filter(v => 
            v.type?.toLowerCase().includes('docker') ||
            v.type?.toLowerCase().includes('container') ||
            v.type?.toLowerCase().includes('image') ||
            v.type?.toLowerCase().includes('secret')
        ).slice(0, 5) || [];

        return `Docker Container Security Analysis - Tier 2 Gemini Focus (${scanSummary.totalImages} images)

🐳 SPECIALIZED DOCKER VULNERABILITY ANALYSIS:
${dockerVulns.map(v => `• ${v.type}: ${v.description?.substring(0, 100)}...`).join('\n')}

🔒 DOCKER SECURITY CONTEXT:
• Container Threats: ${dockerContext.commonThreats.join(', ')}
• Security Focus: ${dockerContext.containerSecurity.join(', ')}

📊 SCAN RESULTS SUMMARY:
• Images Scanned: ${scanSummary.totalImages}
• Critical Container Vulnerabilities: ${scanSummary.criticalVulns}
• High-Risk Container Issues: ${scanSummary.highVulns}
• Container Secrets Exposed: ${scanSummary.secretsFound}
• Docker Configuration Problems: ${scanSummary.configIssues}

🐳 CONTAINER DETAILS:
${scanSummary.images.map(img => 
`--- ${img.image} ---
• Security Issues: ${img.vulnerabilities.critical}C, ${img.vulnerabilities.high}H, ${img.vulnerabilities.medium}M
• Exposed Secrets: ${img.secrets}, Config Issues: ${img.misconfigs}
${img.criticalDetails.length > 0 ? `• Critical Container Vulnerabilities: ${img.criticalDetails.map(c => `${c.id} in ${c.package} ${c.version} (fix: ${c.fixedVersion || 'unavailable'})`).join(', ')}` : ''}`
).join('\n\n')}

🎯 PRIORITY DOCKER SECURITY CHECKS:
- Container image vulnerability exploitation risk
- Docker secrets and credentials exposure
- Container escape and privilege escalation paths
- Base image security hardening gaps
- Container runtime security configurations
- Docker network security isolation
- Container resource limit bypasses
- Docker daemon security configurations

💡 ASSUME general web security handled - FOCUS ON container-specific threats

JSON RESPONSE:
{
  "securityScore": <0-10>,
  "riskAssessment": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "actionRequired": <boolean>,
  "vulnerabilitiesFound": [{"type":"", "severity":"", "location":"", "description":"", "recommendedFix":"", "dockerSpecific": true}],
  "recommendations": ["Docker-specific security fixes"],
  "dockerPatterns": {"secureConfigs":[], "vulnerablePatterns":[], "missingHardening":[]},
  "imageAnalysis": [{"image":"", "riskLevel":"", "dockerRisks":[], "hardeningNeeded":[]}],
  "tierAnalysis": "Tier 2: Docker-focused analysis by Gemini"
}`;
    }

    async performAIAnalysis(prompt) {
        // Try Anthropic first (primary provider)
        if (this.anthropic) {
            try {
                console.log('🚀 Attempting Docker analysis with Anthropic (primary)...');
                const analysis = await this.performAnthropicAnalysis(prompt);
                return { analysis, provider: 'Anthropic Claude Opus 4.1' };
            } catch (error) {
                console.warn('🔄 Anthropic Docker analysis failed:', error.message);
                if (this.isRateLimitOrBudgetError(error)) {
                    console.log('💸 Anthropic budget/rate limit exceeded, trying Gemini...');
                }
            }
        }

        // Fallback to Gemini (secondary provider)
        if (this.geminiModel) {
            try {
                console.log('🔷 Switching to Gemini for Docker analysis (fallback provider)...');
                console.log('🔷 Gemini model: gemini-1.5-pro');
                const analysis = await this.performGeminiAnalysis(prompt);
                console.log('✅ Gemini Docker analysis completed successfully');
                return { analysis, provider: 'Google Gemini 1.5 Pro' };
            } catch (error) {
                console.warn('❌ Gemini Docker analysis failed:', error.message);
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
                console.log(`🤖 Anthropic Docker analysis attempt ${attempt}/${this.maxRetries}...`);

                const message = await this.anthropic.messages.create({
                    model: 'claude-opus-4-1-20250805',
                    max_tokens: 3000, // Increased for Docker analysis details
                    temperature: 0.1, // Low temperature for consistent security analysis
                    messages: [{
                        role: 'user',
                        content: prompt
                    }]
                });

                console.log('✅ Anthropic Docker analysis completed successfully');
                return message.content[0].text;

            } catch (error) {
                console.warn(`⚠️ Anthropic Docker attempt ${attempt} failed:`, error.message);

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
        console.log('🔷 Starting Gemini Docker analysis process...');
        console.log(`🔷 Gemini Docker prompt length: ${prompt.length} characters`);

        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                console.log(`🔷 Gemini Docker analysis attempt ${attempt}/${this.maxRetries}...`);

                // Adapt prompt for Gemini format
                const geminiPrompt = this.adaptPromptForGemini(prompt);
                console.log('🔷 Sending Docker analysis request to Gemini 1.5 Pro...');

                const result = await this.geminiModel.generateContent(geminiPrompt);
                const response = await result.response;
                const responseText = response.text();

                console.log('✅ Gemini Docker response received successfully');
                console.log(`✅ Gemini Docker response length: ${responseText.length} characters`);
                console.log('✅ Gemini Docker analysis completed - parsing results...');

                return responseText;

            } catch (error) {
                console.warn(`⚠️ Gemini Docker attempt ${attempt} failed:`, error.message);

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

    parseAIAnalysisResults(analysisText) {
        try {
            // Extract JSON from AI response (may include explanation text)
            const jsonMatch = analysisText.match(/\{[\s\S]*\}/);
            if (!jsonMatch) {
                throw new Error('No JSON found in AI response');
            }

            const analysis = JSON.parse(jsonMatch[0]);

            // Validate required fields and transform to our expected format
            const results = {
                timestamp: new Date().toISOString(),
                summary: this.scanResults.summary || {},
                imageAnalysis: analysis.imageAnalysis || [],
                recommendations: analysis.recommendations || [],
                riskAssessment: analysis.riskAssessment || 'UNKNOWN',
                actionRequired: analysis.actionRequired || false,
                securityScore: analysis.securityScore || 5.0,
                vulnerabilitiesFound: analysis.vulnerabilitiesFound || [],
                dockerSpecificRisks: analysis.dockerSpecificRisks || {},
                dockerPatterns: analysis.dockerPatterns || {},
                tierAnalysis: analysis.tierAnalysis || 'AI Analysis'
            };

            return results;

        } catch (error) {
            console.error('❌ Failed to parse AI Docker analysis results:', error.message);
            console.log('Raw AI response:', analysisText);
            return this.createFallbackAnalysis();
        }
    }

    enhanceWithTraditionalAnalysis(results) {
        console.log('🔧 Enhancing AI results with traditional Docker analysis...');

        // Ensure we have traditional analysis for each image
        for (const scan of this.scanResults.scans || []) {
            const traditionalAnalysis = this.analyzeImageScanTraditional(scan);
            
            // Find corresponding AI analysis or create new entry
            let imageAnalysis = results.imageAnalysis?.find(img => img.image === scan.image);
            if (!imageAnalysis) {
                imageAnalysis = {
                    image: scan.image,
                    riskLevel: traditionalAnalysis.riskLevel,
                    criticalIssues: [],
                    recommendations: []
                };
                results.imageAnalysis = results.imageAnalysis || [];
                results.imageAnalysis.push(imageAnalysis);
            }

            // Merge traditional vulnerability data
            imageAnalysis.vulnerabilities = traditionalAnalysis.vulnerabilities;
            imageAnalysis.securityIssues = traditionalAnalysis.securityIssues;
            
            // Update overall risk if traditional analysis found higher risk
            if (traditionalAnalysis.riskLevel === 'CRITICAL' || traditionalAnalysis.riskLevel === 'HIGH') {
                results.riskAssessment = traditionalAnalysis.riskLevel;
                results.actionRequired = true;
            }
        }

        // Generate traditional recommendations and merge with AI recommendations
        const traditionalRecommendations = this.generateTraditionalRecommendations(results);
        results.recommendations = [...(results.recommendations || []), ...traditionalRecommendations];

        console.log('✅ Enhanced analysis with traditional Docker security checks');
    }

    generateTraditionalRecommendations(analysis) {
        console.log('💡 Generating traditional Docker security recommendations...');
        const recommendations = [];

        // Vulnerability recommendations
        const totalCritical = analysis.imageAnalysis?.reduce((sum, img) => sum + (img.vulnerabilities?.critical || 0), 0) || 0;
        const totalHigh = analysis.imageAnalysis?.reduce((sum, img) => sum + (img.vulnerabilities?.high || 0), 0) || 0;

        if (totalCritical > 0) {
            recommendations.push({
                priority: 'URGENT',
                category: 'Container Vulnerabilities',
                action: `Address ${totalCritical} critical container vulnerabilities before deployment`,
                details: 'Critical container vulnerabilities pose immediate security risk'
            });
        }

        if (totalHigh > 0) {
            recommendations.push({
                priority: 'HIGH',
                category: 'Container Security',
                action: `Review and patch ${totalHigh} high-severity container vulnerabilities`,
                details: 'High-severity container vulnerabilities should be addressed promptly'
            });
        }

        // Secret recommendations
        const secretIssues = analysis.imageAnalysis?.flatMap(img =>
            img.securityIssues?.filter(issue => issue.type === 'secret') || []
        ) || [];

        if (secretIssues.length > 0) {
            recommendations.push({
                priority: 'URGENT',
                category: 'Container Secrets',
                action: `Remove ${secretIssues.length} potential secrets from Docker images`,
                details: 'Secrets in container images pose significant security risk'
            });
        }

        // Configuration recommendations
        const configIssues = analysis.imageAnalysis?.flatMap(img =>
            img.securityIssues?.filter(issue => issue.type === 'misconfiguration') || []
        ) || [];

        if (configIssues.length > 0) {
            recommendations.push({
                priority: 'MEDIUM',
                category: 'Container Configuration',
                action: `Fix ${configIssues.length} Docker security configuration issues`,
                details: 'Container misconfigurations can lead to security vulnerabilities'
            });
        }

        console.log(`   Generated ${recommendations.length} traditional recommendations`);
        return recommendations;
    }

    createEmptyAnalysis() {
        return {
            timestamp: new Date().toISOString(),
            summary: { message: 'No scan results available' },
            imageAnalysis: [],
            recommendations: [{
                priority: 'HIGH',
                category: 'Scan Results',
                action: 'No Docker scan results found - ensure security scanning is enabled',
                details: 'Unable to perform security analysis without scan results'
            }],
            riskAssessment: 'UNKNOWN',
            actionRequired: true,
            securityScore: 0,
            vulnerabilitiesFound: [],
            analysisMetadata: {
                aiProvider: 'None (No scan data)',
                timestamp: new Date().toISOString(),
                analysisType: 'empty-analysis',
                reason: 'No Docker scan results available',
                tier: 'N/A'
            }
        };
    }

    createTemplateAnalysis() {
        console.log('📋 Creating template-based Docker security analysis...');
        
        const analysis = {
            timestamp: new Date().toISOString(),
            summary: this.scanResults.summary || {},
            imageAnalysis: [],
            recommendations: [],
            riskAssessment: 'LOW',
            actionRequired: false,
            securityScore: 5.0,
            vulnerabilitiesFound: []
        };

        // Analyze each scanned image with template patterns
        for (const scan of this.scanResults.scans || []) {
            const imageAnalysis = this.analyzeImageScanTraditional(scan);
            analysis.imageAnalysis.push(imageAnalysis);

            // Update overall risk assessment
            if (imageAnalysis.riskLevel === 'HIGH' || imageAnalysis.riskLevel === 'CRITICAL') {
                analysis.riskAssessment = imageAnalysis.riskLevel;
                analysis.actionRequired = true;
                analysis.securityScore = imageAnalysis.riskLevel === 'CRITICAL' ? 8.0 : 6.5;
            } else if (imageAnalysis.riskLevel === 'MEDIUM' && analysis.riskAssessment === 'LOW') {
                analysis.riskAssessment = 'MEDIUM';
                analysis.securityScore = 5.5;
            }

            // Convert security issues to vulnerabilities found format
            for (const issue of imageAnalysis.securityIssues) {
                analysis.vulnerabilitiesFound.push({
                    type: issue.type,
                    severity: issue.severity,
                    location: issue.location || issue.package || imageAnalysis.image,
                    description: issue.description,
                    recommendedFix: issue.resolution || 'Review and update container configuration'
                });
            }
        }

        // Generate template recommendations
        analysis.recommendations = this.generateTraditionalRecommendations(analysis);

        // Add Docker-specific template patterns
        analysis.dockerPatterns = this.analyzeDockerSecurityPatterns();
        analysis.templateAnalysis = {
            scanMethod: 'Traditional pattern-based analysis',
            imagesScanned: analysis.imageAnalysis.length,
            totalVulnerabilities: analysis.vulnerabilitiesFound.length,
            riskFactors: analysis.imageAnalysis.map(img => `${img.image}: ${img.riskLevel}`)
        };

        console.log('📋 Template analysis completed');
        console.log(`   Images analyzed: ${analysis.imageAnalysis.length}`);
        console.log(`   Overall risk: ${analysis.riskAssessment}`);
        console.log(`   Action required: ${analysis.actionRequired}`);
        console.log(`   Recommendations: ${analysis.recommendations.length}`);

        return analysis;
    }

    analyzeDockerSecurityPatterns() {
        const patterns = {
            secureConfigs: [],
            vulnerablePatterns: [],
            missingHardening: []
        };

        for (const scan of this.scanResults.scans || []) {
            // Check for secure patterns
            if (scan.scans?.config?.Results) {
                const configResults = scan.scans.config.Results;
                const lowSeverityConfigs = configResults.filter(result => 
                    result.Misconfigurations?.some(config => config.Severity === 'LOW')
                );
                if (lowSeverityConfigs.length === 0) {
                    patterns.secureConfigs.push(`${scan.image}: Good configuration practices`);
                }
            }

            // Check for vulnerable patterns
            if (scan.scans?.vulnerabilities?.Results) {
                const vulnResults = scan.scans.vulnerabilities.Results;
                const criticalVulns = vulnResults.flatMap(result => 
                    result.Vulnerabilities?.filter(v => v.Severity === 'CRITICAL') || []
                );
                if (criticalVulns.length > 0) {
                    patterns.vulnerablePatterns.push(`${scan.image}: ${criticalVulns.length} critical vulnerabilities`);
                }
            }

            // Check for missing hardening
            if (scan.scans?.secrets?.Results && scan.scans.secrets.Results.length > 0) {
                patterns.missingHardening.push(`${scan.image}: Potential secrets exposure`);
            }
        }

        return patterns;
    }

    createFallbackAnalysis() {
        const availableProviders = [];
        if (this.anthropic) availableProviders.push('Anthropic');
        if (this.geminiModel) availableProviders.push('Gemini');

        const analysisError = availableProviders.length === 0
            ? 'No AI providers configured - template Docker analysis provided'
            : `AI providers failed (${availableProviders.join(', ')}) - template Docker analysis provided`;

        const fallbackAnalysis = this.createTemplateAnalysis();
        
        // Add fallback-specific recommendations
        fallbackAnalysis.recommendations.unshift({
            priority: 'HIGH',
            category: 'Analysis Method',
            action: 'AI Docker security analysis failed - manual security review recommended',
            details: 'Review Docker images manually for security vulnerabilities and misconfigurations'
        });

        fallbackAnalysis.analysisError = analysisError;
        fallbackAnalysis.providersAttempted = availableProviders;

        return fallbackAnalysis;
    }

    /**
     * Output results for GitHub Actions with enhanced 3-tier metadata
     */
    outputGitHubActions(analysis) {
        console.log('📤 Setting GitHub Actions outputs with 3-tier metadata...');
        
        const securityScore = analysis.securityScore || 5.0;
        const vulnerabilitiesFound = analysis.vulnerabilitiesFound?.length || 0;
        const requiresSecurityReview = analysis.actionRequired || securityScore >= 6.0;
        const aiProvider = analysis.analysisMetadata?.aiProvider || 'Template Analysis';
        const analysisTier = analysis.analysisMetadata?.tier || 'Unknown Tier';
        
        // Prepare recommendations text
        const recommendationsText = (analysis.recommendations || [])
            .map(rec => typeof rec === 'string' ? rec : rec.action || 'Security review needed')
            .join(';');
        
        // Prepare analysis report
        const analysisReport = [
            `Docker Security Score: ${securityScore}/10`,
            `Vulnerabilities: ${vulnerabilitiesFound}`,
            `Review Required: ${requiresSecurityReview}`,
            `Analysis Provider: ${aiProvider}`,
            `Tier: ${analysisTier}`
        ].join('\n');
        
        // Use the newer format for setting outputs
        if (process.env.GITHUB_OUTPUT) {
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `risk-assessment=${analysis.riskAssessment}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `action-required=${analysis.actionRequired}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `recommendations=${analysis.recommendations?.length || 0}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `security-score=${securityScore}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `vulnerabilities-found=${vulnerabilitiesFound}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `requires-security-review=${requiresSecurityReview}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `ai-provider=${aiProvider}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `analysis-tier=${analysisTier}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `recommendations-text=${recommendationsText.replace(/\n/g, ' ')}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `analysis-report=${analysisReport.replace(/\n/g, ' | ')}\n`);
        } else {
            // Fallback to legacy format (deprecated but still works)
            console.log(`::set-output name=risk-assessment::${analysis.riskAssessment}`);
            console.log(`::set-output name=action-required::${analysis.actionRequired}`);
            console.log(`::set-output name=recommendations::${analysis.recommendations?.length || 0}`);
            console.log(`::set-output name=security-score::${securityScore}`);
            console.log(`::set-output name=vulnerabilities-found::${vulnerabilitiesFound}`);
            console.log(`::set-output name=requires-security-review::${requiresSecurityReview}`);
            console.log(`::set-output name=ai-provider::${aiProvider}`);
            console.log(`::set-output name=analysis-tier::${analysisTier}`);
            console.log(`::set-output name=recommendations-text::${recommendationsText.replace(/\n/g, ' ')}`);
            console.log(`::set-output name=analysis-report::${analysisReport.replace(/\n/g, ' | ')}`);
        }
        
        console.log(`   Risk Assessment: ${analysis.riskAssessment}`);
        console.log(`   Action Required: ${analysis.actionRequired}`);
        console.log(`   Security Score: ${securityScore}/10`);
        console.log(`   Vulnerabilities Found: ${vulnerabilitiesFound}`);
        console.log(`   Recommendations: ${analysis.recommendations?.length || 0}`);
        console.log(`   AI Provider: ${aiProvider}`);
        console.log(`   Analysis Tier: ${analysisTier}`);
    }
}

/**
 * Main execution function for GitHub Actions with 3-tier system
 */
async function main() {
    console.log('🚀 3-Tier AI Docker Security Analyzer Starting');
    
    // Log tier configuration
    const geminiOnly = process.env.GEMINI_ONLY_MODE === 'true';
    const templateOnly = process.env.TEMPLATE_ONLY_MODE === 'true';
    
    if (templateOnly) {
        console.log('📋 Running in Template-Only Mode (Tier 3)');
    } else if (geminiOnly) {
        console.log('🔷 Running in Gemini-Only Mode (Tier 2) - Docker focus');
    } else {
        console.log('🤖 Running in Standard Mode - Multi-provider analysis (Tier 1)');
    }
    
    try {
        const analyzer = new AIDockerSecurityAnalyzer();
        const analysis = await analyzer.analyzeSecurityFindings();
        
        // Output for GitHub Actions
        analyzer.outputGitHubActions(analysis);
        
        console.log('✅ 3-Tier AI Docker security analysis completed successfully');
        console.log(`📋 Analysis saved to: ai-security-analysis.json`);
        
        if (analysis.analysisMetadata) {
            console.log(`🤖 Analysis Provider: ${analysis.analysisMetadata.aiProvider}`);
            console.log(`📅 Analysis Timestamp: ${analysis.analysisMetadata.timestamp}`);
            console.log(`🔧 Analysis Type: ${analysis.analysisMetadata.analysisType}`);
            console.log(`🏷️ Analysis Tier: ${analysis.analysisMetadata.tier}`);
        }
        
        // Exit with success
        process.exit(0);
        
    } catch (error) {
        console.error('❌ 3-Tier AI Docker security analysis failed:', error.message);
        console.error('Stack trace:', error.stack);
        
        // Create emergency fallback analysis
        const emergencyAnalysis = {
            timestamp: new Date().toISOString(),
            summary: { message: 'Emergency fallback analysis due to system failure' },
            imageAnalysis: [],
            recommendations: [{
                priority: 'HIGH',
                category: 'System Error',
                action: 'Docker security analysis system failed - manual review required',
                details: 'Critical system error prevented automated Docker security analysis'
            }],
            riskAssessment: 'UNKNOWN',
            actionRequired: true,
            securityScore: 5.0,
            vulnerabilitiesFound: [],
            analysisMetadata: {
                aiProvider: 'None (Emergency Fallback)',
                timestamp: new Date().toISOString(),
                analysisType: 'emergency-fallback',
                reason: 'System failure: ' + error.message,
                tier: 'Emergency Fallback'
            }
        };
        
        // Save emergency analysis
        fs.writeFileSync('ai-security-analysis.json', JSON.stringify(emergencyAnalysis, null, 2));
        
        // Set emergency GitHub Actions outputs
        if (process.env.GITHUB_OUTPUT) {
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `risk-assessment=UNKNOWN\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `action-required=true\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `recommendations=1\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `security-score=5.0\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `vulnerabilities-found=0\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `requires-security-review=true\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `ai-provider=None (Emergency Fallback)\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `analysis-tier=Emergency Fallback\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `recommendations-text=Docker security analysis system failed - manual review required\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `analysis-report=Docker Security: System Failed | Manual Review Required | Tier: Emergency Fallback\n`);
        } else {
            console.log('::set-output name=risk-assessment::UNKNOWN');
            console.log('::set-output name=action-required::true');
            console.log('::set-output name=recommendations::1');
            console.log('::set-output name=security-score::5.0');
            console.log('::set-output name=vulnerabilities-found::0');
            console.log('::set-output name=requires-security-review::true');
            console.log('::set-output name=ai-provider::None (Emergency Fallback)');
            console.log('::set-output name=analysis-tier::Emergency Fallback');
            console.log('::set-output name=recommendations-text::Docker security analysis system failed - manual review required');
            console.log('::set-output name=analysis-report::Docker Security: System Failed | Manual Review Required | Tier: Emergency Fallback');
        }
        
        process.exit(1);
    }
}

// Export for testing
module.exports = { AIDockerSecurityAnalyzer, main };

// Run main if called directly
if (require.main === module) {
    main();
}