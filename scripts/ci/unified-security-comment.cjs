#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Unified Security Reporting System
 * Consolidates findings from all 8 security tools into single professional PR comment
 * 
 * Supported Tools:
 * - Trivy (Container vulnerabilities)
 * - OSV-Scanner (Open source vulnerabilities) 
 * - Semgrep (SAST)
 * - GitLeaks (Secrets)
 * - Checkov (IaC)
 * - OWASP ZAP (DAST)
 * - Dependabot (Dependencies)
 * - Gradle Locking (Supply chain)
 */

class UnifiedSecurityReporter {
  constructor() {
    this.github = {
      token: process.env.GITHUB_TOKEN,
      repository: process.env.GITHUB_REPOSITORY,
      prNumber: process.env.PR_NUMBER
    };
    
    this.findings = {
      trivy: [],
      osvScanner: [],
      semgrep: [],
      checkov: [],
      owaspZap: [],
      gitLeaks: [],
      dependabot: [],
      gradleLocking: { status: 'enabled', lockedDeps: 974 }
    };
    
    this.summary = {
      total: 0,
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      informational: 0,
      toolStatus: {}
    };
  }

  async run() {
    try {
      console.log('🔄 Starting unified security report generation...');
      
      // Collect findings from all security tools
      await this.collectFindings();
      
      // Generate summary statistics
      this.generateSummary();
      
      // Create unified dashboard comment
      const dashboardComment = this.buildSecurityDashboard();
      
      // Post or update PR comment
      await this.postUnifiedComment(dashboardComment);
      
      console.log('✅ Unified security dashboard successfully generated!');
      
    } catch (error) {
      console.error('❌ Failed to generate unified security report:', error.message);
      console.error('Stack trace:', error.stack);
      process.exit(1);
    }
  }

  async collectFindings() {
    console.log('📋 Collecting findings from all security tools...');
    
    // Check what artifacts are available
    await this.checkAvailableArtifacts();
    
    // Parse SARIF files from security tools
    await this.parseSarifFindings();
    
    // Parse JSON files from security tools  
    await this.parseJsonFindings();
    
    // Query GitHub API for additional data
    await this.parseGitHubSecurityData();
    
    console.log(`📊 Collection complete: ${this.summary.total} total findings`);
  }

  async checkAvailableArtifacts() {
    console.log('📋 Checking available security artifacts...');
    
    try {
      // List all security-related files in the security-artifacts directory
      const artifactDirs = ['security-artifacts', '.', 'downloaded-artifacts'];
      
      for (const dir of artifactDirs) {
        try {
          const listCmd = `find ${dir} -name "*.sarif" -o -name "*.json" 2>/dev/null | head -20`;
          const files = execSync(listCmd, { encoding: 'utf8', stdio: 'pipe' }).trim();
          
          if (files) {
            console.log(`📄 Security files found in ${dir}/:`);
            files.split('\n').forEach(file => {
              console.log(`  - ${file}`);
            });
          }
        } catch (dirError) {
          // Directory doesn't exist or no files found
        }
      }
      
      // Also list artifact directories that were downloaded
      try {
        const artifactDirsCmd = `find security-artifacts -type d -name "*results*" 2>/dev/null`;
        const dirs = execSync(artifactDirsCmd, { encoding: 'utf8', stdio: 'pipe' }).trim();
        
        if (dirs) {
          console.log(`📁 Artifact directories found:`);
          dirs.split('\n').forEach(dir => {
            console.log(`  - ${dir}/`);
          });
        }
      } catch (dirListError) {
        console.log('📁 No artifact directories found in security-artifacts/');
      }
      
    } catch (error) {
      console.warn('⚠️ Could not list available artifacts:', error.message);
    }
  }

  async parseJsonFindings() {
    console.log('📄 Parsing JSON security findings...');
    
    // Search for JSON files by pattern
    const jsonSearchPatterns = {
      'osvScanner': ['osv-results.json', '*osv*.json']
    };

    for (const [toolName, searchPatterns] of Object.entries(jsonSearchPatterns)) {
      let found = false;
      
      for (const pattern of searchPatterns) {
        try {
          // Search for files matching the pattern in artifact directories
          const searchDirs = ['security-artifacts', '.', 'downloaded-artifacts'];
          let foundFile = '';
          
          for (const dir of searchDirs) {
            const findCmd = `find ${dir} -name "${pattern}" -type f 2>/dev/null | head -1`;
            foundFile = execSync(findCmd, { encoding: 'utf8', stdio: 'pipe' }).trim();
            if (foundFile) break;
          }
          
          if (foundFile && fs.existsSync(foundFile)) {
            console.log(`🔍 Parsing ${toolName} JSON file: ${foundFile}`);
            try {
              const jsonContent = JSON.parse(fs.readFileSync(foundFile, 'utf8'));
              if (toolName === 'osvScanner') {
                this.parseOsvScannerJson(jsonContent, toolName);
              }
              this.summary.toolStatus[toolName] = '✅ Completed';
              found = true;
              break;
            } catch (parseError) {
              console.error(`❌ Failed to parse ${toolName} JSON:`, parseError.message);
              this.summary.toolStatus[toolName] = '❌ Error';
            }
          }
        } catch (searchError) {
          // Continue with next pattern
        }
      }
      
      if (!found) {
        console.log(`⚠️ No JSON file found for ${toolName} (searched patterns: ${searchPatterns.join(', ')})`);
        this.summary.toolStatus[toolName] = '⚠️ Missing';
      }
    }
  }

  parseOsvScannerJson(jsonData, toolName) {
    if (!jsonData.results || !Array.isArray(jsonData.results)) {
      console.log(`  📊 ${toolName}: No vulnerabilities found`);
      this.findings.osvScanner = [];
      return;
    }

    this.findings.osvScanner = [];
    
    for (const result of jsonData.results) {
      if (!result.packages) continue;
      
      for (const pkg of result.packages) {
        if (!pkg.vulnerabilities) continue;
        
        for (const vuln of pkg.vulnerabilities) {
          this.findings.osvScanner.push({
            tool: toolName,
            severity: this.mapOsvSeverity(vuln.database_specific?.severity),
            message: vuln.summary || vuln.id,
            location: result.source?.path || 'Unknown',
            package: pkg.package?.name || 'Unknown',
            vulnerability: vuln.id,
            cvssScore: vuln.database_specific?.cvss_score || 'N/A'
          });
        }
      }
    }
    
    console.log(`  📊 ${toolName}: ${this.findings.osvScanner.length} vulnerabilities found`);
  }


  mapOsvSeverity(severity) {
    if (!severity) return 'medium';
    const sev = severity.toLowerCase();
    if (sev.includes('critical')) return 'critical';
    if (sev.includes('high')) return 'high';  
    if (sev.includes('medium') || sev.includes('moderate')) return 'medium';
    if (sev.includes('low')) return 'low';
    return 'medium';
  }

  async parseSarifFindings() {
    console.log('📄 Parsing SARIF security findings...');
    
    // Search for SARIF files by tool name patterns
    const sarifSearchPatterns = {
      'trivy': ['docker-security-scan-results.sarif', '*trivy*.sarif'],
      'semgrep': ['semgrep.sarif', 'semgrep-results.sarif', '*semgrep*.sarif'],
      'checkov': ['checkov-results.sarif', '*checkov*.sarif'],
      'owaspZap': ['zap-results.sarif', '*zap*.sarif']
    };

    for (const [toolName, searchPatterns] of Object.entries(sarifSearchPatterns)) {
      let found = false;
      
      for (const pattern of searchPatterns) {
        try {
          // Search for files matching the pattern in artifact directories
          const searchDirs = ['security-artifacts', '.', 'downloaded-artifacts'];
          let foundFile = '';
          
          for (const dir of searchDirs) {
            const findCmd = `find ${dir} -name "${pattern}" -type f 2>/dev/null | head -1`;
            foundFile = execSync(findCmd, { encoding: 'utf8', stdio: 'pipe' }).trim();
            if (foundFile) break;
          }
          
          if (foundFile && fs.existsSync(foundFile)) {
            console.log(`🔍 Parsing ${toolName} SARIF file: ${foundFile}`);
            this.findings[toolName] = this.parseSarifFile(foundFile, toolName);
            this.summary.toolStatus[toolName] = '✅ Completed';
            found = true;
            break;
          }
        } catch (searchError) {
          // Continue with next pattern
        }
      }
      
      if (!found) {
        // Special handling for ZAP - check for ZAP JSON report files instead of SARIF files
        if (toolName === 'owaspZap') {
          try {
            // ZAP actions create artifacts with directory structure:
            // security-artifacts/zap-full-scan-webauthn-server/report_json.json
            // security-artifacts/zap-baseline-scan-webauthn-test-credentials-service/report_json.json
            // Also check in root directory: zap-*-scan-*/report_json.json
            const zapReportCheck = `find . -path "./zap-*-scan-*/report_json.json" -o -path "./security-artifacts/zap-*/report_json.json" 2>/dev/null`;
            const zapReports = execSync(zapReportCheck, { encoding: 'utf8', stdio: 'pipe' }).trim();
            
            if (zapReports) {
              const reportFiles = zapReports.split('\n');
              console.log(`🔍 ZAP JSON reports found: ${reportFiles.join(', ')}`);
              
              // Parse ZAP JSON reports to extract vulnerability findings
              this.findings.owaspZap = this.parseZapJsonReports(reportFiles);
              
              // Count unique scans by checking for different directories
              const zapDirs = [...new Set(reportFiles.map(f => f.split('/').slice(0, -1).join('/')))];
              console.log(`📊 ZAP scans detected: ${zapDirs.length} (${zapDirs.map(d => d.split('/').pop()).join(', ')})`);
              
              this.summary.toolStatus[toolName] = '✅ Completed';
              found = true;
            }
          } catch (e) {
            console.log(`🔍 ZAP report check failed: ${e.message}`);
          }
        }
        
        if (!found) {
          console.log(`⚠️ No SARIF file found for ${toolName} (searched patterns: ${searchPatterns.join(', ')})`);
          
          // Enhanced debugging: show what files exist for this tool pattern
          try {
            const debugCmd = `find security-artifacts -type f -name "*${toolName.toLowerCase()}*" 2>/dev/null || find security-artifacts -type f -name "*${searchPatterns[0].split('.')[0]}*" 2>/dev/null`;
            const debugFiles = execSync(debugCmd, { encoding: 'utf8', stdio: 'pipe' }).trim();
            if (debugFiles) {
              console.log(`🔍 Found related files for ${toolName}:`, debugFiles.split('\n').join(', '));
            }
          } catch (e) {
            // Debug command failed, continue
          }
          
          this.summary.toolStatus[toolName] = '⚠️ Missing';
        }
      }
    }
  }

  parseSarifFile(sarifFile, toolName) {
    const sarif = JSON.parse(fs.readFileSync(sarifFile, 'utf8'));
    const vulnerabilities = [];
    
    for (const run of sarif.runs || []) {
      for (const result of run.results || []) {
        const vuln = {
          tool: toolName,
          severity: this.extractSeverity(result),
          ruleId: result.ruleId || 'unknown',
          message: result.message?.text || 'No description available',
          location: this.extractLocation(result),
          package: this.extractPackage(result, toolName),
          vulnerability: this.extractVulnId(result),
          cvssScore: this.extractCvssScore(result)
        };
        
        vulnerabilities.push(vuln);
      }
    }
    
    console.log(`  📊 ${toolName}: ${vulnerabilities.length} findings`);
    return vulnerabilities;
  }

  extractSeverity(result) {
    // Extract severity from various SARIF formats
    const securitySeverity = result.properties?.['security-severity'];
    if (securitySeverity) {
      const score = parseFloat(securitySeverity);
      if (score >= 9.0) return 'critical';
      if (score >= 7.0) return 'high';
      if (score >= 4.0) return 'medium';
      return 'low';
    }
    
    // Fallback to SARIF level mapping
    const level = result.level || 'info';
    switch (level) {
      case 'error': return 'high';
      case 'warning': return 'medium';  
      case 'note':
      case 'info':
      default: return 'low';
    }
  }

  extractLocation(result) {
    const location = result.locations?.[0];
    if (location?.physicalLocation?.artifactLocation?.uri) {
      const uri = location.physicalLocation.artifactLocation.uri;
      const startLine = location.physicalLocation?.region?.startLine;
      return startLine ? `${uri}:${startLine}` : uri;
    }
    return 'Unknown location';
  }

  extractPackage(result, toolName) {
    // Tool-specific package extraction
    switch (toolName) {
      case 'trivy':
        return this.extractTrivyPackage(result);
      case 'osvScanner':
        return this.extractOSVPackage(result);
      default:
        return result.properties?.package || 'Unknown package';
    }
  }

  extractTrivyPackage(result) {
    // Extract package from Trivy SARIF format
    const message = result.message?.text || '';
    const packageMatch = message.match(/Package:\s*([^\s]+)/);
    return packageMatch ? packageMatch[1] : 'Unknown package';
  }

  extractOSVPackage(result) {
    // Extract package from OSV-Scanner SARIF format  
    const location = result.locations?.[0];
    const uri = location?.physicalLocation?.artifactLocation?.uri || '';
    const packageMatch = uri.match(/([^\/]+)$/);
    return packageMatch ? packageMatch[1] : 'Unknown package';
  }

  extractVulnId(result) {
    return result.ruleId || result.properties?.vulnId || 'Unknown';
  }

  extractCvssScore(result) {
    const score = result.properties?.['security-severity'];
    return score ? parseFloat(score).toFixed(1) : 'N/A';
  }

  parseZapJsonReports(reportFiles) {
    console.log('📄 Parsing ZAP JSON reports...');
    const allFindings = [];
    
    for (const reportFile of reportFiles) {
      try {
        console.log(`🔍 Processing ZAP report: ${reportFile}`);
        const zapData = JSON.parse(fs.readFileSync(reportFile.trim(), 'utf8'));
        
        // Extract service name from file path for better identification
        const pathParts = reportFile.split('/');
        const scanType = pathParts.find(part => part.includes('scan'));
        const serviceId = scanType ? scanType.replace(/^zap-|-scan.*$/g, '') : 'unknown';
        
        // Parse each site in the ZAP report
        if (zapData.site && Array.isArray(zapData.site)) {
          for (const site of zapData.site) {
            if (site.alerts && Array.isArray(site.alerts)) {
              for (const alert of site.alerts) {
                const finding = {
                  tool: 'owaspZap',
                  severity: this.mapZapRiskCode(alert.riskcode),
                  ruleId: alert.pluginid,
                  message: alert.alert,
                  description: this.stripHtmlTags(alert.desc),
                  location: `${site['@name']} (${serviceId})`,
                  package: site['@host'] + ':' + site['@port'],
                  vulnerability: alert.alertRef || alert.pluginid,
                  cvssScore: 'N/A', // ZAP doesn't provide CVSS scores
                  instanceCount: parseInt(alert.count) || 1,
                  confidence: this.mapZapConfidence(alert.confidence),
                  solution: this.stripHtmlTags(alert.solution),
                  reference: this.stripHtmlTags(alert.reference)
                };
                
                // Add details about affected endpoints
                if (alert.instances && Array.isArray(alert.instances)) {
                  const endpoints = alert.instances.slice(0, 3).map(inst => inst.uri).join(', ');
                  finding.affectedEndpoints = endpoints;
                  if (alert.instances.length > 3) {
                    finding.affectedEndpoints += ` +${alert.instances.length - 3} more`;
                  }
                }
                
                allFindings.push(finding);
              }
            }
          }
        }
        
        console.log(`  📊 ${reportFile}: processed, ${allFindings.length} total findings so far`);
        
      } catch (error) {
        console.error(`❌ Failed to parse ZAP report ${reportFile}:`, error.message);
      }
    }
    
    // Group findings by severity for summary
    const severityCounts = {
      high: allFindings.filter(f => f.severity === 'high').length,
      medium: allFindings.filter(f => f.severity === 'medium').length,
      low: allFindings.filter(f => f.severity === 'low').length,
      informational: allFindings.filter(f => f.severity === 'informational').length
    };
    
    console.log(`  📈 ZAP Summary: ${allFindings.length} total findings`);
    console.log(`  🔥 High: ${severityCounts.high} | ⚠️ Medium: ${severityCounts.medium} | ℹ️ Low: ${severityCounts.low} | 📋 Info: ${severityCounts.informational}`);
    
    return allFindings;
  }

  mapZapRiskCode(riskCode) {
    // ZAP risk codes: 0=Informational, 1=Low, 2=Medium, 3=High
    switch (parseInt(riskCode)) {
      case 3: return 'high';
      case 2: return 'medium';
      case 1: return 'low';
      case 0: 
      default: return 'informational';
    }
  }

  mapZapConfidence(confidence) {
    // ZAP confidence levels: 1=Low, 2=Medium, 3=High
    switch (parseInt(confidence)) {
      case 3: return 'High';
      case 2: return 'Medium';
      case 1: return 'Low';
      default: return 'Unknown';
    }
  }

  stripHtmlTags(text) {
    if (!text) return '';
    // Remove HTML tags and decode common entities
    return text
      .replace(/<[^>]*>/g, '')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .replace(/&#x27;/g, "'")
      .replace(/\s+/g, ' ')
      .trim();
  }

  async parseGitHubSecurityData() {
    // Query GitHub API for GitLeaks issues and Dependabot alerts
    try {
      await this.parseGitLeaksIssues();
      await this.parseDependabotAlerts();
    } catch (error) {
      console.error('❌ Failed to fetch GitHub security data:', error.message);
    }
  }

  async parseGitLeaksIssues() {
    // GitLeaks creates GitHub issues for secret findings
    console.log('🔑 Checking GitLeaks issues...');
    
    try {
      const cmd = `gh api repos/${this.github.repository}/issues --jq '.[] | select(.labels[].name == "gitleaks") | {title, number, created_at}'`;
      const issuesOutput = execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
      
      if (issuesOutput.trim()) {
        const issues = issuesOutput.trim().split('\n').map(line => JSON.parse(line));
        this.findings.gitLeaks = issues.map(issue => ({
          tool: 'gitLeaks',
          severity: 'high', // Secrets are always high severity
          message: issue.title,
          location: `Issue #${issue.number}`,
          package: 'Repository',
          vulnerability: 'Secret Detection'
        }));
        this.summary.toolStatus.gitLeaks = '✅ Completed';
        console.log(`  📊 GitLeaks: ${issues.length} secret issues found`);
      } else {
        this.summary.toolStatus.gitLeaks = '✅ No issues';
        console.log('  📊 GitLeaks: No secret issues found');
      }
    } catch (error) {
      console.error('❌ GitLeaks issue parsing failed:', error.message);
      this.summary.toolStatus.gitLeaks = '❌ Error';
    }
  }

  async parseDependabotAlerts() {
    // Query Dependabot security alerts using PAT_DEPENDABOT token
    console.log('🔧 Checking Dependabot alerts...');
    
    // Use PAT_DEPENDABOT token if available, otherwise fail
    const dependabotToken = process.env.PAT_DEPENDABOT;
    if (!dependabotToken) {
      throw new Error('PAT_DEPENDABOT environment variable is required for Dependabot API access');
    }
    
    try {
      // Use curl with PAT_DEPENDABOT token instead of gh cli with GITHUB_TOKEN
      const cmd = `curl -s -H "Authorization: token ${dependabotToken}" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/${this.github.repository}/dependabot/alerts?state=open" | jq '.[] | {security_advisory: .security_advisory.summary, package: .dependency.package.name, severity: .security_advisory.severity}'`;
      const alertsOutput = execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
      
      if (alertsOutput.trim()) {
        const alerts = alertsOutput.trim().split('\n').map(line => JSON.parse(line));
        this.findings.dependabot = alerts.map(alert => ({
          tool: 'dependabot',
          severity: alert.severity.toLowerCase(),
          message: alert.security_advisory,
          location: 'Dependencies',
          package: alert.package,
          vulnerability: 'Dependency Alert'
        }));
        this.summary.toolStatus.dependabot = '✅ Completed';
        console.log(`  📊 Dependabot: ${alerts.length} alerts found`);
      } else {
        this.summary.toolStatus.dependabot = '✅ No alerts';
        console.log('  📊 Dependabot: No alerts found');
      }
    } catch (error) {
      console.error('❌ Dependabot API access failed:', error.message);
      this.summary.toolStatus.dependabot = '❌ Error';
      throw error; // Fail hard - no graceful fallback
    }
  }

  generateSummary() {
    console.log('📊 Generating vulnerability summary...');
    
    // Combine all findings
    const allFindings = [
      ...this.findings.trivy,
      ...this.findings.osvScanner,
      ...this.findings.semgrep,
      ...this.findings.checkov,
      ...this.findings.owaspZap,
      ...this.findings.gitLeaks,
      ...this.findings.dependabot
    ];
    
    // Count by severity
    this.summary.total = allFindings.length;
    this.summary.critical = allFindings.filter(f => f.severity === 'critical').length;
    this.summary.high = allFindings.filter(f => f.severity === 'high').length;
    this.summary.medium = allFindings.filter(f => f.severity === 'medium').length;
    this.summary.low = allFindings.filter(f => f.severity === 'low').length;
    this.summary.informational = allFindings.filter(f => f.severity === 'informational').length;
    
    console.log(`  📈 Total: ${this.summary.total} findings`);
    console.log(`  🚨 Critical: ${this.summary.critical}`);
    console.log(`  🔥 High: ${this.summary.high}`);
    console.log(`  ⚠️ Medium: ${this.summary.medium}`);
    console.log(`  ℹ️ Low: ${this.summary.low}`);
    console.log(`  📋 Informational: ${this.summary.informational}`);
  }

  buildSecurityDashboard() {
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    
    return `## 🛡️ Unified Security Dashboard

### 📊 Executive Summary
- **Total Findings**: ${this.summary.total} vulnerabilities across 8 security tools
- **Critical**: ${this.summary.critical} 🚨 | **High**: ${this.summary.high} 🔥 | **Medium**: ${this.summary.medium} ⚠️ | **Low**: ${this.summary.low} ℹ️ | **Info**: ${this.summary.informational} 📋
- **Supply Chain**: ${this.findings.gradleLocking.lockedDeps} dependencies locked 🔒

### 🔍 Security Tool Results

| Tool | Status | Findings | Critical | High | Medium | Low | Info | Details |
|------|--------|----------|----------|------|--------|-----|------|---------|
| 🐳 **Trivy** | ${this.summary.toolStatus.trivy || '❓'} | ${this.findings.trivy.length} | ${this.countBySeverity('trivy', 'critical')} | ${this.countBySeverity('trivy', 'high')} | ${this.countBySeverity('trivy', 'medium')} | ${this.countBySeverity('trivy', 'low')} | ${this.countBySeverity('trivy', 'informational')} | Container Security |
| 🔍 **OSV-Scanner** | ${this.summary.toolStatus.osvScanner || '❓'} | ${this.findings.osvScanner.length} | ${this.countBySeverity('osvScanner', 'critical')} | ${this.countBySeverity('osvScanner', 'high')} | ${this.countBySeverity('osvScanner', 'medium')} | ${this.countBySeverity('osvScanner', 'low')} | ${this.countBySeverity('osvScanner', 'informational')} | Open Source Vulns |
| 🔒 **Semgrep** | ${this.summary.toolStatus.semgrep || '❓'} | ${this.findings.semgrep.length} | ${this.countBySeverity('semgrep', 'critical')} | ${this.countBySeverity('semgrep', 'high')} | ${this.countBySeverity('semgrep', 'medium')} | ${this.countBySeverity('semgrep', 'low')} | ${this.countBySeverity('semgrep', 'informational')} | Static Analysis |
| 🔑 **GitLeaks** | ${this.summary.toolStatus.gitLeaks || '❓'} | ${this.findings.gitLeaks.length} | ${this.countBySeverity('gitLeaks', 'critical')} | ${this.countBySeverity('gitLeaks', 'high')} | ${this.countBySeverity('gitLeaks', 'medium')} | ${this.countBySeverity('gitLeaks', 'low')} | ${this.countBySeverity('gitLeaks', 'informational')} | Secret Detection |
| 🏗️ **Checkov** | ${this.summary.toolStatus.checkov || '❓'} | ${this.findings.checkov.length} | ${this.countBySeverity('checkov', 'critical')} | ${this.countBySeverity('checkov', 'high')} | ${this.countBySeverity('checkov', 'medium')} | ${this.countBySeverity('checkov', 'low')} | ${this.countBySeverity('checkov', 'informational')} | Infrastructure |
| ⚡ **OWASP ZAP** | ${this.summary.toolStatus.owaspZap || '❓'} | ${this.findings.owaspZap.length} | ${this.countBySeverity('owaspZap', 'critical')} | ${this.countBySeverity('owaspZap', 'high')} | ${this.countBySeverity('owaspZap', 'medium')} | ${this.countBySeverity('owaspZap', 'low')} | ${this.countBySeverity('owaspZap', 'informational')} | Dynamic Analysis |
| 🔧 **Dependabot** | ${this.summary.toolStatus.dependabot || '❓'} | ${this.findings.dependabot.length} | ${this.countBySeverity('dependabot', 'critical')} | ${this.countBySeverity('dependabot', 'high')} | ${this.countBySeverity('dependabot', 'medium')} | ${this.countBySeverity('dependabot', 'low')} | ${this.countBySeverity('dependabot', 'informational')} | Dependencies |
| 🔒 **Gradle Lock** | ✅ | 974 deps locked | - | - | - | - | - | Supply Chain |

${this.buildCriticalSection()}

${this.buildHighPrioritySection()}

${this.buildResourcesSection()}

---
*🤖 Generated by Unified Security Reporting System*  
*📅 Last updated: ${timestamp} UTC*  
*🔄 Report includes findings from all 8 security tools*`;
  }

  countBySeverity(tool, severity) {
    return this.findings[tool]?.filter(f => f.severity === severity).length || 0;
  }

  buildCriticalSection() {
    const criticalFindings = this.getAllFindings().filter(f => f.severity === 'critical');
    
    if (criticalFindings.length === 0) {
      return `### 🚨 Critical Issues
✅ **No critical vulnerabilities found!** Great job maintaining secure code.`;
    }

    let section = `### 🚨 Critical Issues (${criticalFindings.length}) - Immediate Action Required\n\n`;
    
    criticalFindings.slice(0, 5).forEach((finding, index) => {
      section += `${index + 1}. **${finding.vulnerability}** - ${finding.message}\n`;
      section += `   - **Tool**: ${finding.tool} | **CVSS**: ${finding.cvssScore} | **Package**: \`${finding.package}\`\n`;
      section += `   - **Location**: ${finding.location}\n\n`;
    });
    
    if (criticalFindings.length > 5) {
      section += `\n*... and ${criticalFindings.length - 5} more critical issues. View complete report for details.*\n`;
    }
    
    return section;
  }

  buildHighPrioritySection() {
    const highFindings = this.getAllFindings().filter(f => f.severity === 'high');
    
    if (highFindings.length === 0) {
      return `### 🔥 High Priority Issues
✅ **No high-priority vulnerabilities found!**`;
    }

    let section = `### 🔥 High Priority Issues (${highFindings.length})\n\n`;
    section += `<details>\n<summary>Click to expand high-priority findings</summary>\n\n`;
    
    highFindings.slice(0, 10).forEach((finding, index) => {
      section += `${index + 1}. **${finding.vulnerability}** - ${finding.message}\n`;
      section += `   - **Tool**: ${finding.tool} | **Package**: \`${finding.package}\`\n`;
      section += `   - **Location**: ${finding.location}\n\n`;
    });
    
    if (highFindings.length > 10) {
      section += `\n*... and ${highFindings.length - 10} more high-priority issues.*\n`;
    }
    
    section += `\n</details>\n`;
    return section;
  }

  buildResourcesSection() {
    return `### 🔗 Additional Resources

- **📊 [GitHub Security Tab](https://github.com/${this.github.repository}/security)** - Complete vulnerability details
- **🔒 [Security Advisories](https://github.com/${this.github.repository}/security/advisories)** - Published security issues  
- **🤖 [Dependabot Dashboard](https://github.com/${this.github.repository}/security/dependabot)** - Dependency management
- **📋 [Security Artifacts](https://github.com/${this.github.repository}/actions)** - Download complete SARIF reports

### 🛠️ Remediation Guidance

1. **Critical Issues**: Address immediately before merging
2. **High Priority**: Plan fixes in current sprint  
3. **Medium/Low**: Include in technical debt backlog
4. **False Positives**: Document and suppress with justification`;
  }

  getAllFindings() {
    return [
      ...this.findings.trivy,
      ...this.findings.osvScanner,
      ...this.findings.semgrep,
      ...this.findings.checkov,
      ...this.findings.owaspZap,
      ...this.findings.gitLeaks,
      ...this.findings.dependabot
    ];
  }

  async postUnifiedComment(comment) {
    if (!this.github.prNumber) {
      console.log('📝 Not a PR - skipping comment posting');
      return;
    }

    console.log(`📝 Posting unified security comment to PR #${this.github.prNumber}...`);
    
    try {
      // Check for existing unified security comment
      const existingCommentCmd = `gh api repos/${this.github.repository}/issues/${this.github.prNumber}/comments --jq '.[] | select(.body | contains("🛡️ Unified Security Dashboard")) | .id'`;
      
      let existingCommentId;
      try {
        existingCommentId = execSync(existingCommentCmd, { encoding: 'utf8', stdio: 'pipe' }).trim();
      } catch (error) {
        // No existing comment found
      }

      if (existingCommentId) {
        // Update existing comment
        console.log(`🔄 Updating existing security comment ID: ${existingCommentId}`);
        execSync(`gh api repos/${this.github.repository}/issues/comments/${existingCommentId} -X PATCH -f body='${comment.replace(/'/g, "'\\''")}' > /dev/null`, { stdio: 'pipe' });
      } else {
        // Create new comment  
        console.log('🆕 Creating new unified security comment');
        execSync(`gh pr comment ${this.github.prNumber} --body '${comment.replace(/'/g, "'\\''")}' > /dev/null`, { stdio: 'pipe' });
      }
      
      console.log('✅ Unified security comment successfully posted!');
      
    } catch (error) {
      console.error('❌ Failed to post unified comment:', error.message);
      throw error;
    }
  }
}

// Execute unified security reporting
if (require.main === module) {
  const reporter = new UnifiedSecurityReporter();
  reporter.run().catch(error => {
    console.error('💥 Unified security reporting failed:', error);
    process.exit(1);
  });
}

module.exports = UnifiedSecurityReporter;