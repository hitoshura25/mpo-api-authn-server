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
 * Create E2E Test Results Comment
 * 
 * This script replaces the actions/github-script usage in e2e-tests.yml
 * to create comprehensive comments on PRs with E2E test results.
 * 
 * USAGE:
 *   node create-e2e-results-comment.js
 *   (Uses environment variables from GitHub Actions workflow)
 * 
 * ENVIRONMENT VARIABLES:
 *   - PR_NUMBER - Pull request number to comment on
 *   - VALIDATION_RESULT - Result of Docker image validation step
 *   - WEB_E2E_RESULT - Result of web E2E tests
 *   - ANDROID_E2E_RESULT - Result of Android E2E tests
 *   - WEBAUTHN_SERVER_IMAGE - Docker image name for WebAuthn server
 *   - TEST_CREDENTIALS_IMAGE - Docker image name for test credentials service
 *   - GITHUB_TOKEN - GitHub API token
 */

/**
 * E2E Test Results Comment Generator
 */
class E2EResultsCommentGenerator {
    constructor() {
        this.prNumber = process.env.PR_NUMBER;
        this.validationResult = process.env.VALIDATION_RESULT;
        this.webE2eResult = process.env.WEB_E2E_RESULT;
        this.androidE2eResult = process.env.ANDROID_E2E_RESULT;
        this.webauthnServerImage = process.env.WEBAUTHN_SERVER_IMAGE || 'Unknown';
        this.testCredentialsImage = process.env.TEST_CREDENTIALS_IMAGE || 'Unknown';
        
        console.log('🧪 E2E Results Comment Generator initialized:');
        console.log(`  PR Number: ${this.prNumber}`);
        console.log(`  Validation Result: ${this.validationResult}`);
        console.log(`  Web E2E Result: ${this.webE2eResult}`);
        console.log(`  Android E2E Result: ${this.androidE2eResult}`);
        console.log(`  WebAuthn Server Image: ${this.webauthnServerImage}`);
        console.log(`  Test Credentials Image: ${this.testCredentialsImage}`);
    }

    /**
     * Determine test results status
     */
    getResultsStatus() {
        const validationSuccess = this.validationResult === 'success';
        const webE2eSuccess = this.webE2eResult === 'success';
        const androidE2eSuccess = this.androidE2eResult === 'success';
        const webE2eSkipped = this.webE2eResult === 'skipped';
        const androidE2eSkipped = this.androidE2eResult === 'skipped';
        
        return {
            validationSuccess,
            webE2eSuccess,
            androidE2eSuccess,
            webE2eSkipped,
            androidE2eSkipped
        };
    }

    /**
     * Build comprehensive E2E test results comment
     */
    buildCommentBody() {
        const status = this.getResultsStatus();
        let message = `## 🧪 E2E Test Results for PR #${this.prNumber}\n\n`;

        if (!status.validationSuccess) {
            message += this.buildValidationFailureSection(status);
        } else if (status.webE2eSkipped && status.androidE2eSkipped) {
            message += this.buildAllSkippedSection();
        } else {
            message += this.buildDetailedResultsSection(status);
        }

        return message;
    }

    /**
     * Build validation failure section
     */
    buildValidationFailureSection(status) {
        let section = `❌ **Docker Image Validation Failed**\n`;
        section += `- WebAuthn Server: \`${this.webauthnServerImage}\`\n`;
        section += `- Test Credentials: \`${this.testCredentialsImage}\`\n\n`;
        section += `Please check that the Docker build step completed successfully.\n`;
        return section;
    }

    /**
     * Build all tests skipped section
     */
    buildAllSkippedSection() {
        let section = `⏭️ **E2E Tests Skipped**\n`;
        section += `Docker images were not available for testing.\n`;
        return section;
    }

    /**
     * Build detailed test results section
     */
    buildDetailedResultsSection(status) {
        let section = `### Test Results Summary\n\n`;

        // Web E2E Tests
        if (status.webE2eSkipped) {
            section += `⏭️ **Web E2E Tests**: Skipped (images not available)\n`;
        } else if (status.webE2eSuccess) {
            section += `✅ **Web E2E Tests**: Passed (Playwright)\n`;
        } else {
            section += `❌ **Web E2E Tests**: Failed (Playwright)\n`;
        }

        // Android E2E Tests
        if (status.androidE2eSkipped) {
            section += `⏭️ **Android E2E Tests**: Skipped (images not available)\n`;
        } else if (status.androidE2eSuccess) {
            section += `✅ **Android E2E Tests**: Passed (connectedAndroidTest)\n`;
        } else {
            section += `❌ **Android E2E Tests**: Failed (connectedAndroidTest)\n`;
        }

        section += `\n`;
        section += this.buildOverallStatusSection(status);
        section += this.buildTestArchitectureSection();

        return section;
    }

    /**
     * Build overall status section
     */
    buildOverallStatusSection(status) {
        let section = '';

        // Overall status
        if (status.webE2eSuccess && status.androidE2eSuccess) {
            section += `🎉 **Overall Status: All E2E Tests Passed**\n`;
            section += `- Cross-platform WebAuthn functionality verified\n`;
            section += `- Full API contract validation completed\n`;
            section += `- Both web and Android clients integration tested\n`;
        } else if ((status.webE2eSuccess || status.webE2eSkipped) && 
                   (status.androidE2eSuccess || status.androidE2eSkipped) && 
                   (status.webE2eSuccess || status.androidE2eSuccess)) {
            section += `⚠️ **Overall Status: Partial Success**\n`;
            section += `Some tests passed, but others failed or were skipped.\n`;
        } else {
            section += `❌ **Overall Status: E2E Tests Failed**\n`;
            section += `Integration tests did not pass. Please check the test logs.\n`;
        }

        section += `\n**Images tested:**\n`;
        section += `- WebAuthn Server: \`${this.webauthnServerImage}\`\n`;
        section += `- Test Credentials: \`${this.testCredentialsImage}\`\n`;

        return section;
    }

    /**
     * Build test architecture information section
     */
    buildTestArchitectureSection() {
        let section = `\n**Test Architecture:**\n`;
        section += `- Docker Compose: \`webauthn-server/\` directory with all dependencies\n`;
        section += `- Services: WebAuthn Server (8080), Test Credentials (8081), PostgreSQL, Redis, Jaeger\n`;
        section += `- Tests: Web (Playwright) and Android (connectedAndroidTest) run in parallel\n`;
        
        return section;
    }

    /**
     * Create the E2E results comment using GitHub API
     */
    async createComment() {
        console.log('💬 Creating E2E test results comment...');
        
        const commentBody = this.buildCommentBody();
        
        try {
            const owner = process.env.GITHUB_REPOSITORY_OWNER;
            const repo = process.env.GITHUB_REPOSITORY_NAME;
            const token = process.env.GITHUB_TOKEN;
            
            if (!this.prNumber || !owner || !repo || !token) {
                console.error('❌ Missing required environment variables:');
                console.error(`  PR_NUMBER: ${this.prNumber || 'missing'}`);
                console.error(`  GITHUB_REPOSITORY_OWNER: ${owner || 'missing'}`);
                console.error(`  GITHUB_REPOSITORY_NAME: ${repo || 'missing'}`);
                console.error(`  GITHUB_TOKEN: ${token ? 'present' : 'missing'}`);
                throw new Error('Missing required environment variables');
            }
            
            // Create comment using GitHub REST API
            const response = await githubFetch(`https://api.github.com/repos/${owner}/${repo}/issues/${this.prNumber}/comments`, {
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
            
            console.log(`✅ Posted E2E test results to PR #${this.prNumber}`);
            
        } catch (error) {
            console.error('❌ Failed to create E2E results comment:', error.message);
            throw error;
        }
    }
}

/**
 * Main execution function for GitHub Actions
 */
async function main() {
    console.log('🚀 E2E Results Comment Generator Starting');
    
    try {
        const generator = new E2EResultsCommentGenerator();
        await generator.createComment();
        console.log('🎉 E2E results comment generation completed successfully');
    } catch (error) {
        console.error('❌ E2E results comment generation failed:', error);
        process.exit(1);
    }
}

// Export for GitHub Actions usage and testing
module.exports = { E2EResultsCommentGenerator, main };

// Run main if called directly
if (require.main === module) {
    main();
}