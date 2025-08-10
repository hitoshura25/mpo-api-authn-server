#!/usr/bin/env node

/**
 * Security Scan PR Comment Generator
 * 
 * Parses Docker security scan results and posts a readable comment on the PR
 * highlighting critical vulnerabilities that fail the build.
 */

const fs = require('fs');
const { exec } = require('child_process');
const path = require('path');

// Environment variables
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPOSITORY = process.env.GITHUB_REPOSITORY;
const PR_NUMBER = process.env.PR_NUMBER;
const SCAN_RESULTS_FILE = process.env.SCAN_RESULTS_FILE || 'docker-security-scan-results.json';

if (!GITHUB_TOKEN || !GITHUB_REPOSITORY || !PR_NUMBER) {
    console.error('❌ Missing required environment variables');
    console.error('Required: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER');
    process.exit(1);
}

function loadScanResults() {
    if (!fs.existsSync(SCAN_RESULTS_FILE)) {
        console.error(`❌ Scan results file not found: ${SCAN_RESULTS_FILE}`);
        process.exit(1);
    }

    try {
        const data = fs.readFileSync(SCAN_RESULTS_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error(`❌ Failed to parse scan results: ${error.message}`);
        process.exit(1);
    }
}

function categorizeVulnerabilities(results) {
    const categories = {
        critical: [],
        high: [],
        medium: [],
        low: []
    };

    // Handle Trivy format
    if (results.Results) {
        results.Results.forEach(result => {
            if (result.Vulnerabilities) {
                result.Vulnerabilities.forEach(vuln => {
                    const severity = vuln.Severity.toLowerCase();
                    if (categories[severity]) {
                        categories[severity].push({
                            ...vuln,
                            target: result.Target
                        });
                    }
                });
            }
        });
    }

    return categories;
}

function generateCommentBody(categories, scanPassed) {
    const totalVulns = Object.values(categories).reduce((sum, vulns) => sum + vulns.length, 0);
    
    let comment = `## 🛡️ Docker Security Scan Results\n\n`;
    
    // Overall status
    if (scanPassed) {
        comment += `✅ **Security scan passed** - No critical vulnerabilities found\n\n`;
    } else {
        comment += `❌ **Security scan failed** - Critical vulnerabilities detected\n\n`;
    }

    // Summary
    comment += `### 📊 Vulnerability Summary\n\n`;
    comment += `| Severity | Count |\n`;
    comment += `|----------|-------|\n`;
    comment += `| 🔴 Critical | ${categories.critical.length} |\n`;
    comment += `| 🟠 High | ${categories.high.length} |\n`;
    comment += `| 🟡 Medium | ${categories.medium.length} |\n`;
    comment += `| ⚪ Low | ${categories.low.length} |\n`;
    comment += `| **Total** | **${totalVulns}** |\n\n`;

    // Critical vulnerabilities details (build-failing)
    if (categories.critical.length > 0) {
        comment += `### 🚨 Critical Vulnerabilities (Build Failing)\n\n`;
        comment += `These vulnerabilities must be addressed before the build can pass:\n\n`;
        
        categories.critical.slice(0, 5).forEach((vuln, index) => {
            comment += `#### ${index + 1}. ${vuln.VulnerabilityID || 'Unknown ID'}\n`;
            comment += `- **Package**: ${vuln.PkgName || 'Unknown'} (${vuln.InstalledVersion || 'Unknown version'})\n`;
            comment += `- **Target**: ${vuln.target || 'Unknown target'}\n`;
            comment += `- **Description**: ${vuln.Description || 'No description available'}\n`;
            if (vuln.FixedVersion) {
                comment += `- **Fix**: Update to version ${vuln.FixedVersion}\n`;
            }
            if (vuln.References && vuln.References.length > 0) {
                comment += `- **References**: [${vuln.References[0]}](${vuln.References[0]})\n`;
            }
            comment += `\n`;
        });

        if (categories.critical.length > 5) {
            comment += `<details>\n<summary>Show ${categories.critical.length - 5} more critical vulnerabilities...</summary>\n\n`;
            categories.critical.slice(5).forEach((vuln, index) => {
                comment += `**${index + 6}. ${vuln.VulnerabilityID || 'Unknown ID'}** - ${vuln.PkgName || 'Unknown'}\n`;
            });
            comment += `\n</details>\n\n`;
        }
    }

    // High vulnerabilities summary
    if (categories.high.length > 0) {
        comment += `### 🟠 High Severity Vulnerabilities\n\n`;
        comment += `<details>\n<summary>${categories.high.length} high severity vulnerabilities found (click to expand)</summary>\n\n`;
        categories.high.slice(0, 10).forEach((vuln, index) => {
            comment += `- **${vuln.VulnerabilityID || 'Unknown'}**: ${vuln.PkgName || 'Unknown'} (${vuln.InstalledVersion || 'Unknown'})\n`;
        });
        if (categories.high.length > 10) {
            comment += `- ... and ${categories.high.length - 10} more\n`;
        }
        comment += `\n</details>\n\n`;
    }

    // Recommendations
    comment += `### 💡 Recommendations\n\n`;
    if (categories.critical.length > 0) {
        comment += `1. 🔴 **Critical**: Address critical vulnerabilities immediately - build is blocked\n`;
        comment += `2. 🔧 **Update base images**: Consider updating Docker base images to newer versions\n`;
        comment += `3. 🔍 **Review dependencies**: Check if any application dependencies can be updated\n`;
    } else if (categories.high.length > 0) {
        comment += `1. 🟠 **High Priority**: Consider addressing high-severity vulnerabilities\n`;
        comment += `2. 🔧 **Update base images**: Consider updating Docker base images to newer versions\n`;
    } else {
        comment += `1. ✅ **Good security posture**: No critical or high-severity vulnerabilities found\n`;
        comment += `2. 🔄 **Keep monitoring**: Continue regular security scanning\n`;
    }

    comment += `\n---\n`;
    comment += `🤖 *Generated by automated security scanning*`;

    return comment;
}

function postComment(commentBody) {
    const commentData = {
        body: commentBody
    };

    const curlCommand = `curl -s -X POST \\
        -H "Authorization: token ${GITHUB_TOKEN}" \\
        -H "Accept: application/vnd.github.v3+json" \\
        -H "Content-Type: application/json" \\
        -d '${JSON.stringify(commentData).replace(/'/g, "'\\''")}' \\
        "https://api.github.com/repos/${GITHUB_REPOSITORY}/issues/${PR_NUMBER}/comments"`;

    exec(curlCommand, (error, stdout, stderr) => {
        if (error) {
            console.error(`❌ Failed to post PR comment: ${error.message}`);
            process.exit(1);
        }

        try {
            const response = JSON.parse(stdout);
            if (response.id) {
                console.log(`✅ Security scan comment posted to PR #${PR_NUMBER}`);
                console.log(`🔗 Comment URL: ${response.html_url}`);
            } else {
                console.error(`❌ Failed to post comment: ${stdout}`);
                process.exit(1);
            }
        } catch (parseError) {
            console.error(`❌ Failed to parse GitHub API response: ${parseError.message}`);
            console.error(`Response: ${stdout}`);
            process.exit(1);
        }
    });
}

function main() {
    console.log('🔍 Processing security scan results for PR comment...');
    
    const scanResults = loadScanResults();
    const categories = categorizeVulnerabilities(scanResults);
    
    // Determine if scan passed (no critical vulnerabilities)
    const scanPassed = categories.critical.length === 0;
    
    console.log(`📊 Found vulnerabilities: Critical: ${categories.critical.length}, High: ${categories.high.length}, Medium: ${categories.medium.length}, Low: ${categories.low.length}`);
    
    const commentBody = generateCommentBody(categories, scanPassed);
    
    console.log('📝 Posting security scan results to PR...');
    postComment(commentBody);
}

if (require.main === module) {
    main();
}