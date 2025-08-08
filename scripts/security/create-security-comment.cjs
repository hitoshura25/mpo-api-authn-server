#!/usr/bin/env node

// Use native fetch if available (Node.js 18+), otherwise use https module
async function githubFetch(url, options) {
    if (typeof fetch !== 'undefined') {
        return fetch(url, options);
    }
    
    // Fallback for older Node.js versions
    const https = require('https');
    const { URL } = require('url');
    
    return new Promise((resolve, reject) => {
        const parsedUrl = new URL(url);
        const requestOptions = {
            hostname: parsedUrl.hostname,
            path: parsedUrl.pathname + parsedUrl.search,
            method: options.method || 'GET',
            headers: options.headers || {}
        };
        
        const req = https.request(requestOptions, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                const response = {
                    ok: res.statusCode >= 200 && res.statusCode < 300,
                    status: res.statusCode,
                    text: async () => data,
                    json: async () => JSON.parse(data)
                };
                resolve(response);
            });
        });
        
        req.on('error', reject);
        if (options.body) req.write(options.body);
        req.end();
    });
}

/**
 * Security PR Comment Generator
 *
 * This script creates comprehensive security review comments for pull requests
 * based on AI-powered security analysis results. It formats vulnerability findings,
 * recommendations, and test suggestions into a structured GitHub comment.
 *
 * USAGE:
 *   node create-security-comment.js
 *   (Requires security analysis artifacts and environment variables)
 *
 * INPUTS:
 *   - security-analysis-results.json - AI analysis results file
 *   - security-test-implementations.json - Generated test implementations file
 *   - Environment variables from GitHub Actions workflow
 *
 * ENVIRONMENT VARIABLES:
 *   - SECURITY_SCORE - Numerical security score (0-10)
 *   - VULNERABILITIES_COUNT - Number of vulnerabilities found
 *   - REQUIRES_REVIEW - Boolean indicating if security review is required
 *   - RISK_LEVEL - Risk level assessment (HIGH/MEDIUM/LOW/MINIMAL)
 *   - GITHUB_TOKEN - GitHub API token (provided by GitHub Actions)
 *
 * OUTPUTS:
 *   - Creates a GitHub comment on the pull request
 *   - Returns exit code 0 on success, 1 on failure
 *
 * COMMENT STRUCTURE:
 *   - Security status header with risk assessment
 *   - Detailed vulnerability findings with CWE references
 *   - Actionable security recommendations
 *   - Generated test implementations (collapsible)
 *   - Security patterns analysis (good/missing/anti-patterns)
 *   - Security checklist for reviewers
 *   - Links to security resources
 */

const fs = require('fs');

/**
 * Main security comment generator class
 */
class SecurityCommentGenerator {
    constructor() {
        this.securityScore = parseFloat(process.env.SECURITY_SCORE || '0');
        this.vulnerabilitiesCount = parseInt(process.env.VULNERABILITIES_COUNT || '0');
        this.requiresReview = process.env.REQUIRES_REVIEW === 'true';
        this.riskLevel = process.env.RISK_LEVEL || 'UNKNOWN';
        
        this.analysisResults = {};
        this.testResults = {};
        
        this.loadAnalysisFiles();
    }

    /**
     * Load analysis result files with error handling
     */
    loadAnalysisFiles() {
        console.log('📂 Loading security analysis files...');
        
        try {
            if (fs.existsSync('security-analysis-results.json')) {
                this.analysisResults = JSON.parse(fs.readFileSync('security-analysis-results.json', 'utf8'));
                console.log('✅ Loaded security analysis results');
            } else {
                console.warn('⚠️ security-analysis-results.json not found');
            }
            
            if (fs.existsSync('security-test-implementations.json')) {
                this.testResults = JSON.parse(fs.readFileSync('security-test-implementations.json', 'utf8'));
                console.log('✅ Loaded test implementations');
            } else {
                console.warn('⚠️ security-test-implementations.json not found');
            }
        } catch (error) {
            console.error('❌ Error loading analysis files:', error.message);
            // Continue with empty results - the comment will reflect missing data
        }
    }

    /**
     * Determine security status based on score
     */
    getSecurityStatus() {
        if (this.securityScore >= 8.0) {
            return {
                emoji: '🚨',
                color: 'red',
                description: 'High security risk detected'
            };
        } else if (this.securityScore >= 6.0) {
            return {
                emoji: '⚠️',
                color: 'orange',
                description: 'Medium security risk detected'
            };
        } else if (this.securityScore >= 3.0) {
            return {
                emoji: '🔍',
                color: 'yellow',
                description: 'Low security risk detected'
            };
        } else {
            return {
                emoji: '✅',
                color: 'green',
                description: 'No significant security risks detected'
            };
        }
    }

    /**
     * Build vulnerabilities section with detailed findings
     */
    buildVulnerabilitiesSection() {
        if (!this.analysisResults.vulnerabilitiesFound || this.analysisResults.vulnerabilitiesFound.length === 0) {
            return '';
        }

        let section = '### 🔍 Security Issues Found\n\n';
        
        for (const vuln of this.analysisResults.vulnerabilitiesFound) {
            const severityEmoji = {
                'CRITICAL': '🚨',
                'HIGH': '⚠️',
                'MEDIUM': '🔸',
                'LOW': '🔹'
            }[vuln.severity] || '📋';
            
            section += `${severityEmoji} **${vuln.type}** (${vuln.severity})\n`;
            section += `- **Location**: \`${vuln.location}\`\n`;
            section += `- **Description**: ${vuln.description}\n`;
            
            if (vuln.cweId) {
                section += `- **CWE ID**: [${vuln.cweId}](https://cwe.mitre.org/data/definitions/${vuln.cweId.replace('CWE-', '')}.html)\n`;
            }
            
            section += `- **Recommended Fix**: ${vuln.recommendedFix}\n\n`;
        }
        
        return section;
    }

    /**
     * Build recommendations section
     */
    buildRecommendationsSection() {
        if (!this.analysisResults.recommendations || this.analysisResults.recommendations.length === 0) {
            return '';
        }

        let section = '### 💡 Security Recommendations\n\n';
        
        for (const recommendation of this.analysisResults.recommendations) {
            section += `- ${recommendation}\n`;
        }
        
        return section + '\n';
    }

    /**
     * Build test implementations section with collapsible details
     */
    buildTestSection() {
        if (!this.testResults.testImplementations || this.testResults.testImplementations.length === 0) {
            return '';
        }

        let section = '### 🧪 Generated Security Tests\n\n';
        section += `Generated ${this.testResults.summary.generatedTests} security tests for detected vulnerabilities.\n\n`;
        
        if (this.testResults.summary.generatedTests > 0) {
            section += '<details>\n<summary>📋 View Generated Test Implementations</summary>\n\n';
            
            for (const testImpl of this.testResults.testImplementations) {
                if (testImpl.generated) {
                    section += `**Test for ${testImpl.vulnerability.type}**:\n`;
                    section += '```kotlin\n';
                    section += testImpl.testImplementation;
                    section += '\n```\n\n';
                }
            }
            
            section += '</details>\n\n';
        }
        
        return section;
    }

    /**
     * Build security patterns analysis section
     */
    buildPatternsSection() {
        if (!this.analysisResults.securityPatterns) {
            return '';
        }

        let section = '### 🛡️ Security Patterns Analysis\n\n';
        
        if (this.analysisResults.securityPatterns.good && this.analysisResults.securityPatterns.good.length > 0) {
            section += '**✅ Good Security Patterns Found:**\n';
            for (const pattern of this.analysisResults.securityPatterns.good) {
                section += `- ${pattern}\n`;
            }
            section += '\n';
        }
        
        if (this.analysisResults.securityPatterns.missing && this.analysisResults.securityPatterns.missing.length > 0) {
            section += '**⚠️ Missing Security Patterns:**\n';
            for (const pattern of this.analysisResults.securityPatterns.missing) {
                section += `- ${pattern}\n`;
            }
            section += '\n';
        }
        
        if (this.analysisResults.securityPatterns.antipatterns && this.analysisResults.securityPatterns.antipatterns.length > 0) {
            section += '**🚨 Security Anti-patterns Found:**\n';
            for (const pattern of this.analysisResults.securityPatterns.antipatterns) {
                section += `- ${pattern}\n`;
            }
            section += '\n';
        }
        
        return section;
    }

    /**
     * Build security checklist based on findings
     */
    buildSecurityChecklist() {
        let checklist = '### 🔐 Security Checklist\n\n';
        checklist += 'Before merging this PR:\n\n';
        checklist += '- [ ] Review all identified security issues\n';
        checklist += '- [ ] Implement recommended security fixes\n';
        checklist += '- [ ] Add/update security tests as suggested\n';
        checklist += '- [ ] Run existing security tests: `./gradlew test --tests="*VulnerabilityProtectionTest*"`\n';
        checklist += '- [ ] Verify no sensitive data is exposed in logs or responses\n';
        
        if (this.requiresReview) {
            checklist += '- [ ] **Security team review required**\n';
        }
        
        checklist += '\n';
        return checklist;
    }

    /**
     * Build complete comment body
     */
    buildCommentBody() {
        const status = this.getSecurityStatus();
        const vulnerabilitiesSection = this.buildVulnerabilitiesSection();
        const recommendationsSection = this.buildRecommendationsSection();
        const testSection = this.buildTestSection();
        const patternsSection = this.buildPatternsSection();
        const checklist = this.buildSecurityChecklist();
        
        return `## ${status.emoji} AI-Powered Security Analysis

**Security Risk Level**: \`${this.riskLevel}\`  
**Security Score**: \`${this.securityScore}/10\` ${status.emoji}  
**Vulnerabilities Found**: \`${this.vulnerabilitiesCount}\`  
**Requires Security Review**: \`${this.requiresReview ? 'Yes' : 'No'}\`

${status.description}

${vulnerabilitiesSection}${recommendationsSection}${testSection}${patternsSection}${checklist}### 📚 Security Resources

- [WebAuthn Security Best Practices](/.claude/agents/webauthn-security-analysis.md)
- [Vulnerability Tracking Database](/vulnerability-tracking.json)
- [Existing Security Tests](/webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/security/VulnerabilityProtectionTest.kt)

---

🤖 *This analysis was performed by the AI-Powered Security Analysis system*  
📊 *Analysis completed at ${new Date().toISOString()}*`;
    }

    /**
     * Create the security comment using GitHub API
     */
    async createComment() {
        console.log('💬 Creating comprehensive security comment...');
        
        const commentBody = this.buildCommentBody();
        
        try {
            const prNumber = process.env.PR_NUMBER;
            const owner = process.env.REPOSITORY_OWNER;
            const repo = process.env.REPOSITORY_NAME;
            const token = process.env.GITHUB_TOKEN;
            
            if (!prNumber || !owner || !repo || !token) {
                console.error('❌ Missing required environment variables:');
                console.error(`  PR_NUMBER: ${prNumber || 'missing'}`);
                console.error(`  REPOSITORY_OWNER: ${owner || 'missing'}`);
                console.error(`  REPOSITORY_NAME: ${repo || 'missing'}`);
                console.error(`  GITHUB_TOKEN: ${token ? 'present' : 'missing'}`);
                throw new Error('Missing required environment variables');
            }
            
            // Create comment using GitHub REST API
            const response = await githubFetch(`https://api.github.com/repos/${owner}/${repo}/issues/${prNumber}/comments`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github.v3+json',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    body: commentBody
                })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`GitHub API error: ${response.status} ${errorText}`);
            }
            
            console.log('✅ Security comment created successfully');
        } catch (error) {
            console.error('❌ Failed to create security comment:', error.message);
            throw error;
        }
    }
}

/**
 * Main execution function for GitHub Actions
 */
async function main() {
    console.log('🚀 Security Comment Generator Starting');
    
    try {
        const generator = new SecurityCommentGenerator();
        await generator.createComment();
        console.log('🎉 Security comment generation completed successfully');
    } catch (error) {
        console.error('❌ Security comment generation failed:', error);
        process.exit(1);
    }
}

// Export for GitHub Actions usage
module.exports = { SecurityCommentGenerator, main };

// Run main if called directly
if (require.main === module) {
    main();
}