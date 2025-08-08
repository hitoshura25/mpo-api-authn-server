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
 * Security Labels Manager
 *
 * This script automatically adds appropriate security-related labels to pull requests
 * based on AI-powered security analysis results. It categorizes PRs by risk level,
 * component changes, and review requirements.
 *
 * USAGE:
 *   node add-security-labels.js
 *   (Uses environment variables from GitHub Actions workflow)
 *
 * ENVIRONMENT VARIABLES:
 *   - SECURITY_SCORE - Numerical security score (0-10)
 *   - RISK_LEVEL - Risk level assessment (HIGH/MEDIUM/LOW/MINIMAL)
 *   - REQUIRES_SECURITY_REVIEW - Boolean indicating if security review is required
 *   - HAS_AUTH_CHANGES - Boolean indicating authentication flow changes
 *   - HAS_DEPENDENCY_CHANGES - Boolean indicating dependency changes
 *   - GITHUB_TOKEN - GitHub API token (provided by GitHub Actions)
 *
 * LABELS APPLIED:
 *   - security-analysis (always applied for security PRs)
 *   - security:high-risk, security:medium-risk, security:low-risk (based on risk/score)
 *   - security-review-required (if manual review needed)
 *   - authentication (if auth flows changed)
 *   - dependencies (if dependencies changed)
 *
 * OUTPUTS:
 *   - Adds labels to the pull request
 *   - Returns exit code 0 on success, 1 on failure
 */

/**
 * Security label manager class
 */
class SecurityLabelManager {
    constructor() {
        this.securityScore = parseFloat(process.env.SECURITY_SCORE || '0');
        this.riskLevel = process.env.RISK_LEVEL || 'MINIMAL';
        this.requiresReview = process.env.REQUIRES_SECURITY_REVIEW === 'true';
        this.hasAuthChanges = process.env.HAS_AUTH_CHANGES === 'true';
        this.hasDependencyChanges = process.env.HAS_DEPENDENCY_CHANGES === 'true';
        
        console.log('🏷️ Security Label Manager initialized:');
        console.log(`  Security Score: ${this.securityScore}`);
        console.log(`  Risk Level: ${this.riskLevel}`);
        console.log(`  Requires Review: ${this.requiresReview}`);
        console.log(`  Auth Changes: ${this.hasAuthChanges}`);
        console.log(`  Dependency Changes: ${this.hasDependencyChanges}`);
    }

    /**
     * Determine appropriate security labels based on analysis results
     */
    determineLabels() {
        console.log('📊 Determining appropriate security labels...');
        
        const labels = [];
        
        // Always add base security analysis label
        labels.push('security-analysis');
        
        // Add risk level labels based on both risk level and score
        this.addRiskLabels(labels);
        
        // Add review requirement label
        if (this.requiresReview) {
            labels.push('security-review-required');
            console.log('✅ Added security-review-required label');
        }
        
        // Add component-specific labels
        this.addComponentLabels(labels);
        
        console.log(`🎯 Final label set: ${labels.join(', ')}`);
        return labels;
    }

    /**
     * Add risk-based labels
     */
    addRiskLabels(labels) {
        // Determine risk based on both explicit risk level and security score
        let effectiveRisk = this.riskLevel;
        
        // Override risk level based on security score if score indicates higher risk
        if (this.securityScore >= 8.0 && effectiveRisk !== 'HIGH') {
            effectiveRisk = 'HIGH';
            console.log(`⬆️ Upgraded risk from ${this.riskLevel} to HIGH based on security score`);
        } else if (this.securityScore >= 6.0 && effectiveRisk === 'LOW') {
            effectiveRisk = 'MEDIUM';
            console.log(`⬆️ Upgraded risk from ${this.riskLevel} to MEDIUM based on security score`);
        }
        
        // Add appropriate risk label
        switch (effectiveRisk) {
            case 'HIGH':
                labels.push('security:high-risk');
                console.log('🚨 Added security:high-risk label');
                break;
            case 'MEDIUM':
                labels.push('security:medium-risk');
                console.log('⚠️ Added security:medium-risk label');
                break;
            case 'LOW':
                labels.push('security:low-risk');
                console.log('🔍 Added security:low-risk label');
                break;
            default:
                console.log('ℹ️ No risk label added for MINIMAL risk level');
        }
    }

    /**
     * Add component-specific labels
     */
    addComponentLabels(labels) {
        // Add authentication label if auth flows are modified
        if (this.hasAuthChanges) {
            labels.push('authentication');
            console.log('🔐 Added authentication label');
        }
        
        // Add dependencies label if dependencies are modified
        if (this.hasDependencyChanges) {
            labels.push('dependencies');
            console.log('📦 Added dependencies label');
        }
    }

    /**
     * Validate label set for WebAuthn security context
     */
    validateLabels(labels) {
        console.log('✅ Validating label set for WebAuthn security context...');
        
        // Ensure high-risk authentication changes always require review
        if (this.hasAuthChanges && this.securityScore >= 7.0 && !labels.includes('security-review-required')) {
            labels.push('security-review-required');
            console.log('🔒 Added security-review-required for high-risk auth changes');
        }
        
        // Ensure dependency changes with security implications are properly labeled
        if (this.hasDependencyChanges && this.securityScore >= 5.0 && !labels.includes('security:medium-risk')) {
            // Check if we need to upgrade to at least medium risk
            const hasLowRisk = labels.includes('security:low-risk');
            const hasHighRisk = labels.includes('security:high-risk');
            
            if (hasLowRisk && !hasHighRisk) {
                labels.splice(labels.indexOf('security:low-risk'), 1);
                labels.push('security:medium-risk');
                console.log('⬆️ Upgraded to security:medium-risk for dependency changes');
            }
        }
        
        console.log('✅ Label validation completed');
        return labels;
    }

    /**
     * Apply labels to the pull request
     */
    async applyLabels() {
        console.log('🏷️ Applying security labels to pull request...');
        
        const labels = this.determineLabels();
        const validatedLabels = this.validateLabels(labels);
        
        if (validatedLabels.length === 0) {
            console.log('ℹ️ No labels to apply');
            return;
        }
        
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
            
            // Apply labels using GitHub REST API with fetch
            const response = await githubFetch(`https://api.github.com/repos/${owner}/${repo}/issues/${prNumber}/labels`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github.v3+json',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    labels: validatedLabels
                })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`GitHub API error: ${response.status} ${errorText}`);
            }
            
            console.log(`✅ Successfully applied ${validatedLabels.length} labels: ${validatedLabels.join(', ')}`);
            
        } catch (error) {
            console.error('❌ Failed to apply security labels:', error.message);
            throw error;
        }
    }

    /**
     * Generate label summary for logging
     */
    generateLabelSummary() {
        const labels = this.validateLabels(this.determineLabels());
        
        return {
            totalLabels: labels.length,
            riskLabel: labels.find(l => l.startsWith('security:')) || 'none',
            requiresReview: labels.includes('security-review-required'),
            componentLabels: labels.filter(l => ['authentication', 'dependencies'].includes(l)),
            allLabels: labels
        };
    }
}

/**
 * Main execution function for GitHub Actions
 */
async function main() {
    console.log('🚀 Security Label Manager Starting');
    
    try {
        const labelManager = new SecurityLabelManager();
        await labelManager.applyLabels();
        
        // Log summary for debugging
        const summary = labelManager.generateLabelSummary();
        console.log('📊 Label Application Summary:');
        console.log(`  Total Labels: ${summary.totalLabels}`);
        console.log(`  Risk Label: ${summary.riskLabel}`);
        console.log(`  Review Required: ${summary.requiresReview}`);
        console.log(`  Component Labels: ${summary.componentLabels.join(', ') || 'none'}`);
        
        console.log('🎉 Security label application completed successfully');
        
    } catch (error) {
        console.error('❌ Security label application failed:', error);
        process.exit(1);
    }
}

// Export for GitHub Actions usage and testing
module.exports = { SecurityLabelManager, main };

// Run main if called directly
if (require.main === module) {
    main();
}