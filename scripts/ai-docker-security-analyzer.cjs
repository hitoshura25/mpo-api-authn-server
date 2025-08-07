#!/usr/bin/env node

const fs = require('fs');

/**
 * AI-Enhanced Docker Security Analyzer
 * 
 * Analyzes Docker security scan results with AI-powered vulnerability assessment,
 * risk scoring, and actionable recommendations.
 * 
 * USAGE:
 *   node ai-docker-security-analyzer.js
 *   (Uses scan results from environment variables or files)
 * 
 * ENVIRONMENT VARIABLES:
 *   - SCAN_RESULTS - JSON string with scan results (fallback)
 *   - CRITICAL_VULN_COUNT - Number of critical vulnerabilities
 *   - ANTHROPIC_API_KEY - Optional AI API key for enhanced analysis
 * 
 * INPUT FILES:
 *   - docker-security-scan-results.json - Primary scan results file
 * 
 * OUTPUT FILES:
 *   - ai-security-analysis.json - AI analysis results
 * 
 * OUTPUTS:
 *   - GitHub Actions output variables for workflow decisions
 *   - Structured JSON analysis for security team review
 */
class AIDockerSecurityAnalyzer {
    constructor() {
        this.hasAIKey = !!process.env.ANTHROPIC_API_KEY;
        this.scanResults = this.loadScanResults();
        
        console.log('🤖 AI Docker Security Analyzer initialized');
        console.log(`   AI Key Available: ${this.hasAIKey ? 'Yes' : 'No'}`);
        console.log(`   Scan Results Loaded: ${this.scanResults.scans ? 'Yes' : 'No'}`);
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
        console.log('🔍 Analyzing Docker security findings...');

        if (!this.scanResults.scans || this.scanResults.scans.length === 0) {
            console.log('ℹ️ No scan results to analyze');
            return this.createEmptyAnalysis();
        }

        const analysis = {
            timestamp: new Date().toISOString(),
            summary: this.scanResults.summary || {},
            imageAnalysis: [],
            recommendations: [],
            riskAssessment: 'LOW',
            actionRequired: false
        };

        // Analyze each scanned image
        for (const scan of this.scanResults.scans) {
            const imageAnalysis = await this.analyzeImageScan(scan);
            analysis.imageAnalysis.push(imageAnalysis);

            // Update overall risk assessment
            if (imageAnalysis.riskLevel === 'HIGH' || imageAnalysis.riskLevel === 'CRITICAL') {
                analysis.riskAssessment = imageAnalysis.riskLevel;
                analysis.actionRequired = true;
            } else if (imageAnalysis.riskLevel === 'MEDIUM' && analysis.riskAssessment === 'LOW') {
                analysis.riskAssessment = 'MEDIUM';
            }
        }

        // Generate recommendations
        analysis.recommendations = this.generateSecurityRecommendations(analysis);

        // Save analysis results
        fs.writeFileSync('ai-security-analysis.json', JSON.stringify(analysis, null, 2));

        console.log(`📊 AI Security Analysis Summary:`);
        console.log(`   Images analyzed: ${analysis.imageAnalysis.length}`);
        console.log(`   Overall risk: ${analysis.riskAssessment}`);
        console.log(`   Action required: ${analysis.actionRequired}`);
        console.log(`   Recommendations: ${analysis.recommendations.length}`);

        return analysis;
    }

    async analyzeImageScan(scan) {
        console.log(`🔍 Analyzing security scan for image: ${scan.image || 'Unknown'}`);
        
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

        console.log(`   Risk Level: ${analysis.riskLevel}`);
        console.log(`   Vulnerabilities: ${analysis.vulnerabilities.critical}C, ${analysis.vulnerabilities.high}H, ${analysis.vulnerabilities.medium}M, ${analysis.vulnerabilities.low}L`);
        console.log(`   Security Issues: ${analysis.securityIssues.length}`);

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

    generateSecurityRecommendations(analysis) {
        console.log('💡 Generating security recommendations...');
        const recommendations = [];

        // Vulnerability recommendations
        const totalCritical = analysis.imageAnalysis.reduce((sum, img) => sum + img.vulnerabilities.critical, 0);
        const totalHigh = analysis.imageAnalysis.reduce((sum, img) => sum + img.vulnerabilities.high, 0);

        if (totalCritical > 0) {
            recommendations.push({
                priority: 'URGENT',
                category: 'Vulnerabilities',
                action: `Address ${totalCritical} critical vulnerabilities before publishing to DockerHub`,
                details: 'Critical vulnerabilities pose immediate security risk'
            });
        }

        if (totalHigh > 0) {
            recommendations.push({
                priority: 'HIGH',
                category: 'Vulnerabilities',
                action: `Review and patch ${totalHigh} high-severity vulnerabilities`,
                details: 'High-severity vulnerabilities should be addressed promptly'
            });
        }

        // Secret recommendations
        const secretIssues = analysis.imageAnalysis.flatMap(img =>
            img.securityIssues.filter(issue => issue.type === 'secret')
        );

        if (secretIssues.length > 0) {
            recommendations.push({
                priority: 'URGENT',
                category: 'Secrets',
                action: `Remove ${secretIssues.length} potential secrets from Docker images`,
                details: 'Secrets in images pose significant security risk'
            });
        }

        // Configuration recommendations
        const configIssues = analysis.imageAnalysis.flatMap(img =>
            img.securityIssues.filter(issue => issue.type === 'misconfiguration')
        );

        if (configIssues.length > 0) {
            recommendations.push({
                priority: 'MEDIUM',
                category: 'Configuration',
                action: `Fix ${configIssues.length} security configuration issues`,
                details: 'Misconfigurations can lead to security vulnerabilities'
            });
        }

        console.log(`   Generated ${recommendations.length} recommendations`);
        return recommendations;
    }

    createEmptyAnalysis() {
        return {
            timestamp: new Date().toISOString(),
            summary: { message: 'No scan results available' },
            imageAnalysis: [],
            recommendations: [],
            riskAssessment: 'UNKNOWN',
            actionRequired: false
        };
    }

    /**
     * Output results for GitHub Actions
     */
    outputGitHubActions(analysis) {
        console.log('📤 Setting GitHub Actions outputs...');
        
        // Use the newer format for setting outputs
        if (process.env.GITHUB_OUTPUT) {
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `risk-assessment=${analysis.riskAssessment}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `action-required=${analysis.actionRequired}\n`);
            fs.appendFileSync(process.env.GITHUB_OUTPUT, `recommendations=${analysis.recommendations.length}\n`);
        } else {
            // Fallback to legacy format (deprecated but still works)
            console.log(`::set-output name=risk-assessment::${analysis.riskAssessment}`);
            console.log(`::set-output name=action-required::${analysis.actionRequired}`);
            console.log(`::set-output name=recommendations::${analysis.recommendations.length}`);
        }
        
        console.log(`   Risk Assessment: ${analysis.riskAssessment}`);
        console.log(`   Action Required: ${analysis.actionRequired}`);
        console.log(`   Recommendations: ${analysis.recommendations.length}`);
    }
}

/**
 * Main execution function for GitHub Actions
 */
async function main() {
    console.log('🚀 AI Docker Security Analyzer Starting');
    
    try {
        const analyzer = new AIDockerSecurityAnalyzer();
        const analysis = await analyzer.analyzeSecurityFindings();
        
        // Output for GitHub Actions
        analyzer.outputGitHubActions(analysis);
        
        console.log('✅ AI security analysis completed successfully');
        console.log(`📋 Analysis saved to: ai-security-analysis.json`);
        
    } catch (error) {
        console.error('❌ AI security analysis failed:', error.message);
        console.error('Stack trace:', error.stack);
        process.exit(1);
    }
}

// Export for testing
module.exports = { AIDockerSecurityAnalyzer, main };

// Run main if called directly
if (require.main === module) {
    main();
}