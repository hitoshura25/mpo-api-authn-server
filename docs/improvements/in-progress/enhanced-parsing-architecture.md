# Enhanced Parsing Architecture - Training-Ready Vulnerability Data

**Status**: In Progress
**Created**: 2025-10-07
**Priority**: High

**Related Documents**:
- [OSV Parser Plan](./osv-json-parser-implementation-plan.md)
- [Trivy Parser Plan](./trivy-sarif-parser-implementation-plan.md)
- [Semgrep Parser Plan](./semgrep-parser-implementation-plan.md)
- [ZAP Parser Plan](./zap-json-parser-implementation-plan.md)
- [Checkov Parser Plan](./checkov-sarif-parser-implementation-plan.md)
- [GitLeaks Parser Plan](./gitleaks-sarif-parser-implementation-plan.md)

---

## Executive Summary

**Problem**: Current pipeline has 3 phases (Parsing → Categorization → AI Analysis) where AI analysis generates generic, low-value text using expensive LLM calls for data we already have in tool outputs.

**Solution**: Consolidate to 2 phases where **parsing phase generates complete training-ready data** with tool-native fixes, eliminating AI dependency and producing higher-quality training data.

**Key Changes**:
- ✅ Parsers call `MultiApproachFixGenerator` as universal fix generator
- ✅ Simplified data format focused on training needs
- ✅ Single `confidence` field based on tool (no quality_score)
- ✅ Include alternatives array and full code context
- ✅ No filtering during parsing (include all vulnerabilities)

---

## Architecture Overview

### Current Pipeline (BEFORE)
```
Phase 1: Parsing
├── Input: data/security_artifacts/**
├── Output: parsed_vulnerabilities.json
└── Issues: Missing fixes, no code context

Phase 2: Categorization
├── Input: parsed_vulnerabilities.json
├── Output: categorized_vulnerabilities.json
└── Issues: Still no fixes

Phase 3: AI Analysis + Narrative
├── Input: categorized_vulnerabilities.json
├── Process: Expensive LLM calls for generic text
├── Output: narrativized_analyses.json
└── Issues: "Impact: requires investigation" (useless)
```

### New Pipeline (AFTER)
```
Phase 1: Enhanced Parsing (NEW)
├── Input: data/security_artifacts/**
├── Process:
│   ├── Parse tool-specific formats
│   ├── Categorize security domain
│   ├── Extract code context (VulnerableCodeExtractor)
│   ├── Map URLs to code (URLToCodeMapper for ZAP)
│   └── Generate fixes (MultiApproachFixGenerator)
├── Output: enriched_vulnerabilities.json
└── Contains: EVERYTHING needed for training

Phase 2: Dataset Creation
├── Input: enriched_vulnerabilities.json
├── Process:
│   ├── Convert to ChatML format
│   ├── Filter by confidence threshold (if desired)
│   ├── Split train/validation (80/20)
│   └── Balance security categories
├── Output: train.jsonl, validation.jsonl
└── Ready for MLX fine-tuning
```

---

## Unified Vulnerability Data Format

### Complete Schema

**Design Principles**:
1. **Training-Focused**: Only include data needed for model to learn self-healing
2. **Minimal**: Remove verbose nested structures
3. **Flexible**: Include alternatives and full code context for future use
4. **No Filtering**: Capture all data, filter later if needed

```json
{
  // ========================================
  // SECTION 1: Vulnerability Metadata
  // ========================================
  "tool": "osv-scanner",
  "id": "CVE-2024-12798",
  "severity": "MEDIUM",
  "level": "warning",
  "message": "Package: ch.qos.logback:logback-core\nInstalled Version: 1.4.14\nVulnerability CVE-2024-12798\nSeverity: MEDIUM\nFixed Version: 1.5.13, 1.3.15",

  // Tool identifiers
  "rule_name": "OsPackageVulnerability",
  "check_id": "CVE-2024-12798",
  "tool_name": "OSV Scanner",

  // Descriptions
  "short_description": "logback-core: Server-Side Request Forgery (SSRF)",
  "full_description": "Logback's XMLUtil$EntityResolver resolves external XML entities by default, allowing SSRF attacks via malicious XML configuration files...",

  // Standards mappings
  "cwe": ["CWE-918: Server-Side Request Forgery (SSRF)"],
  "owasp": ["A10:2021 - Server-Side Request Forgery"],
  "cvss": "CVSS:4.0/AV:L/AC:L/AT:P/PR:L/UI:P/VC:L/VI:N/VA:L/SC:H/SI:H/SA:H/V:D/U:Clear",

  // References
  "help_uri": "https://nvd.nist.gov/vuln/detail/CVE-2024-12798",
  "references": [
    {"type": "ADVISORY", "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-12798"},
    {"type": "WEB", "url": "https://github.com/qos-ch/logback/commit/5f05041cba"}
  ],

  // ========================================
  // SECTION 2: Location Information
  // ========================================
  "file_path": "webauthn-server/build.gradle.kts",
  "path": "webauthn-server/build.gradle.kts",
  "start": {"line": 42, "col": 5},
  "end": {"line": 42, "col": 65},

  // ========================================
  // SECTION 3: Security Categorization
  // ========================================
  "security_category": "dependency_vulnerabilities",
  "category_confidence": 0.9,

  // ========================================
  // SECTION 4: Code Context
  // ========================================
  "code_context": {
    "file_path": "webauthn-server/build.gradle.kts",
    "language": "gradle",
    "file_extension": ".kts",

    // Vulnerable code location
    "vulnerability_line": 42,
    "vulnerability_column": 5,
    "vulnerable_code": "implementation(\"ch.qos.logback:logback-core:1.4.14\")",

    // Surrounding context
    "before_lines": [
      "dependencies {",
      "    implementation(\"io.ktor:ktor-server-core:2.3.7\")",
      "    implementation(\"com.yubico:webauthn-server-core:2.6.0\")"
    ],
    "after_lines": [
      "    implementation(\"ch.qos.logback:logback-classic:1.4.14\")",
      "    implementation(\"io.ktor:ktor-server-netty:2.3.7\")",
      "}"
    ],

    // Function/class context (for code vulnerabilities)
    "function_name": null,
    "function_context": null,
    "function_start_line": null,
    "function_end_line": null,
    "class_name": null,
    "class_context": null,
    "class_start_line": null,

    // Extraction metadata
    "extraction_type": "dependency_file",
    "extraction_success": true
  },

  // ========================================
  // SECTION 5: Fix Data (MOST IMPORTANT)
  // ========================================
  "fix": {
    // Tool-based confidence (no quality_score)
    "confidence": 1.0,  // OSV/Trivy=1.0, ZAP=0.9, Semgrep/Checkov=0.7

    // Primary fix description
    "description": "Upgrade logback-core from 1.4.14 to 1.5.13 to fix SSRF vulnerability",

    // Fixed code (what the model should generate)
    "fixed_code": "implementation(\"ch.qos.logback:logback-core:1.5.13\")",

    // Explanation of why this fix works
    "explanation": "Version 1.5.13 disables external entity resolution by default in XMLUtil$EntityResolver, preventing SSRF attacks via malicious XML configuration files. The fix is implemented in commit 5f05041cba which replaces the EntityResolver with a secure default configuration.",

    // Dependency-specific fields (when applicable)
    "package": "ch.qos.logback:logback-core",
    "from_version": "1.4.14",
    "to_version": "1.5.13",
    "ecosystem": "Maven",

    // Alternative fixes (for code patterns or multiple version branches)
    "alternatives": [
      {
        "description": "Upgrade to 1.3.15 if on 1.3.x branch",
        "fixed_code": "implementation(\"ch.qos.logback:logback-core:1.3.15\")",
        "explanation": "For projects on the 1.3.x release branch, upgrade to 1.3.15 which includes the same security fix."
      }
    ]
  }
}
```

### Example: Code Pattern Vulnerability (Semgrep)

```json
{
  "tool": "semgrep",
  "id": "webauthn-credential-validation-bypass",
  "severity": "MEDIUM",
  "short_description": "WebAuthn credential validation bypass via debug mode",
  "security_category": "code_vulnerabilities",
  "category_confidence": 0.7,

  "file_path": "android-test-client/app/src/main/java/.../WebAuthnViewModel.kt",
  "start": {"line": 212},

  "code_context": {
    "vulnerable_code": "if (DEBUG_MODE) return authenticateResult(...)",
    "function_name": "authenticateWithWebAuthn",
    "function_context": "fun authenticateWithWebAuthn(challenge: String) {\n    if (DEBUG_MODE) return authenticateResult(...)\n    return performFullValidation(challenge, credential)\n}",
    "language": "kotlin"
  },

  "fix": {
    "confidence": 0.7,
    "description": "Remove debug bypass - never skip security validation",
    "fixed_code": "return performFullValidation(challenge, credential)",
    "explanation": "Debug bypasses compromise security. Authentication validation must always run in production. Remove the conditional entirely to ensure validation always occurs.",

    // Multiple approaches for code patterns
    "alternatives": [
      {
        "description": "Add explicit test mode validation",
        "fixed_code": "if (DEBUG_MODE && validateDebugCredentials()) {\n    logger.warn(\"Using debug authentication\")\n    return performFullValidation(challenge, credential)\n} else {\n    return performFullValidation(challenge, credential)\n}",
        "explanation": "If debug mode is required for testing, add additional validation even in debug mode rather than bypassing entirely."
      },
      {
        "description": "Use compile-time flag instead of runtime check",
        "fixed_code": "// Remove DEBUG_MODE check, use BuildConfig.DEBUG_FEATURES instead\nreturn performFullValidation(challenge, credential)",
        "explanation": "Use compile-time flags (BuildConfig) to strip debug code from production builds entirely."
      }
    ]
  }
}
```

---

## Tool Integration Strategy

### MultiApproachFixGenerator as Universal Fix Generator

**Key Insight**: `MultiApproachFixGenerator` already handles both scenarios:
- **Lines 283-368**: Parses dependency info (Trivy message format)
- **Lines 91-782**: Generates multiple approaches for code patterns

**New Role**: Universal fix generator for ALL tools, with tool-specific methods.

### Integration Pattern

```python
# Parser responsibility: Parse → Call Fix Generator → Return enriched data

def parse_osv_json(file_path: str) -> List[Dict]:
    """Parse OSV JSON and enrich with fixes."""
    vulnerabilities = extract_osv_vulnerabilities(file_path)

    # Initialize helpers
    fix_generator = MultiApproachFixGenerator()
    code_extractor = VulnerableCodeExtractor()
    categorizer = VulnerabilityCategorizor()

    for vuln in vulnerabilities:
        # Step 1: Categorization
        category, confidence = categorizer.categorize_vulnerability(vuln)
        vuln['security_category'] = category
        vuln['category_confidence'] = confidence

        # Step 2: Code context extraction
        extraction_result = code_extractor.extract_vulnerability_context(vuln)
        if extraction_result.success and extraction_result.code_context:
            vuln['code_context'] = dataclass_to_dict(extraction_result.code_context)

        # Step 3: Fix generation (tool-specific logic in MultiApproachFixGenerator)
        fix_result = fix_generator.generate_fixes(vuln, extraction_result.code_context)

        if fix_result.success and fix_result.fixes:
            vuln['fix'] = convert_fix_result_to_format(fix_result)

    return vulnerabilities
```

### Tool-Specific Confidence Scale

```python
# Confidence is tool-based, not calculated
TOOL_CONFIDENCE = {
    'osv-scanner': 1.0,      # Deterministic: Native OSV data with version ranges
    'trivy': 1.0,            # Deterministic: Dependency fixes with clear versions
    'zap': 0.9,              # High: Framework-specific with URL→code mapping
    'semgrep': 0.7,          # Medium: Code patterns (context-dependent)
    'checkov': 0.7,          # Medium: Config patterns with context
    'gitleaks': 0.5,         # Low: Manual secret rotation (case-by-case)
}

def get_confidence(tool: str) -> float:
    """Get confidence score based on tool."""
    for key, conf in TOOL_CONFIDENCE.items():
        if key in tool.lower():
            return conf
    return 0.5  # Generic fallback
```

### Context Script Usage Matrix

| Parser | URL Mapper | Code Extractor | Fix Generator | Confidence |
|--------|-----------|----------------|---------------|------------|
| **OSV** | ❌ No | ✅ Yes (optional) | ✅ Yes | 1.0 |
| **Trivy** | ❌ No | ✅ Yes (optional) | ✅ Yes | 1.0 |
| **Semgrep** | ❌ No | ✅ **Required** | ✅ **Required** | 0.7 |
| **ZAP** | ✅ **Required** | ✅ **Required** | ✅ Yes | 0.9 |
| **Checkov** | ❌ No | ✅ Yes | ✅ Yes | 0.7 |
| **GitLeaks** | ❌ No | ❌ No | ❌ No | **DEFER** |

---

## MultiApproachFixGenerator Enhancements

### Tool-Specific Methods

```python
class MultiApproachFixGenerator:
    """Universal fix generator for all security tools."""

    def generate_fixes(self, vulnerability: Dict, code_context: Optional[CodeContext]):
        """
        Universal fix generation - delegates to tool-specific methods.

        Returns FixGenerationResult with tool-appropriate fixes.
        """
        tool = vulnerability.get('tool', '').lower()

        # Delegate to tool-specific methods
        if 'osv' in tool:
            return self._generate_osv_fix(vulnerability, code_context)
        elif 'trivy' in tool:
            return self._generate_trivy_fix(vulnerability, code_context)
        elif 'semgrep' in tool:
            return self._generate_semgrep_fix(vulnerability, code_context)
        elif 'zap' in tool:
            return self._generate_zap_fix(vulnerability, code_context)
        elif 'checkov' in tool:
            return self._generate_checkov_fix(vulnerability, code_context)
        else:
            return self._generate_generic_fix(vulnerability, code_context)

    def _generate_osv_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        OSV-specific: Extract fixed versions from affected ranges.

        OSV provides complex version ranges:
        - Multiple branches (1.3.x → 1.3.15, 1.5.x → 1.5.13)
        - Ecosystem-specific format
        - Rich metadata (CVSS v4, patch commits)
        """
        # Extract fixed versions from affected ranges
        fixed_versions = self._extract_osv_fixed_versions(
            vuln.get('affected', [])
        )

        if not fixed_versions:
            return FixGenerationResult(success=False, error_message="No fixed version available")

        # Primary fix: Latest version
        primary_version = fixed_versions[0]

        fix = SecurityFix(
            approach=FixApproach.LIBRARY_REPLACEMENT,
            title=f"Upgrade {vuln['package_name']} to fix {vuln['id']}",
            description=f"Upgrade from {vuln['package_version']} to {primary_version}",
            vulnerable_code=code_context.vulnerable_code if code_context else '',
            fixed_code=self._generate_dependency_upgrade_code(
                vuln['package_name'],
                primary_version,
                vuln.get('ecosystem')
            ),
            explanation=vuln.get('details', vuln.get('summary', '')),
            benefits=[
                'Eliminates known security vulnerability',
                'Includes security patches',
                'Maintains compatibility with ecosystem'
            ],
            trade_offs=[
                'May require dependency testing',
                'Could introduce breaking changes'
            ],
            implementation_notes=[
                f"Update dependency to version {primary_version}",
                'Run tests to ensure compatibility',
                'Check release notes for breaking changes'
            ],
            language=code_context.language if code_context else 'unknown',
            complexity_level='low',
            security_impact='high'
        )

        # Alternative fixes: Other fixed versions
        alternatives = []
        for alt_version in fixed_versions[1:]:
            alt_fix = SecurityFix(
                approach=FixApproach.LIBRARY_REPLACEMENT,
                title=f"Alternative: Upgrade to {alt_version}",
                description=f"Upgrade from {vuln['package_version']} to {alt_version}",
                vulnerable_code=code_context.vulnerable_code if code_context else '',
                fixed_code=self._generate_dependency_upgrade_code(
                    vuln['package_name'],
                    alt_version,
                    vuln.get('ecosystem')
                ),
                explanation=f"Alternative fix for projects on different release branch",
                benefits=['Same security fix', 'Different version branch'],
                complexity_level='low',
                security_impact='high'
            )
            alternatives.append(alt_fix)

        return FixGenerationResult(
            success=True,
            fixes=[fix] + alternatives,
            generation_metadata={
                'tool': 'osv',
                'confidence': 1.0,
                'fixed_versions': fixed_versions
            }
        )

    def _generate_trivy_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        Trivy-specific: Parse message field for dependency info.

        Uses existing _parse_dependency_info() method (lines 283-325).
        """
        # Use existing dependency parsing method
        dependency_info = self._parse_dependency_info(vuln)

        if not dependency_info:
            return FixGenerationResult(success=False, error_message="Could not parse Trivy message")

        # Generate fix using existing infrastructure method
        return self._generate_infrastructure_fix(
            FixApproach.LIBRARY_REPLACEMENT,
            vuln
        )

    def _generate_semgrep_fix(self, vuln: Dict, code_context: CodeContext) -> FixGenerationResult:
        """
        Semgrep-specific: Multi-approach code pattern fixes.

        Uses existing vulnerability_patterns + language_templates.
        Requires code_context.
        """
        if not code_context:
            return FixGenerationResult(success=False, error_message="Code context required for Semgrep")

        # Use existing pattern-based fix generation
        vuln_type = self._classify_vulnerability(vuln)
        approaches = self._get_fix_approaches(vuln_type, code_context)

        fixes = []
        for approach in approaches:
            fix = self._generate_fix_for_approach(approach, vuln, code_context, vuln_type)
            if fix:
                fixes.append(fix)

        return FixGenerationResult(
            success=True,
            fixes=fixes,
            generation_metadata={
                'tool': 'semgrep',
                'confidence': 0.7,
                'vuln_type': vuln_type,
                'approaches_used': [f.approach.value for f in fixes]
            }
        )

    def _generate_zap_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        ZAP-specific: Framework-specific HTTP security fixes.

        Uses ZAP's solution field + framework detection from code_context.
        """
        if not code_context:
            return FixGenerationResult(success=False, error_message="Code context required for ZAP")

        # Extract ZAP solution
        solution = vuln.get('solution', '').strip()
        if not solution:
            return FixGenerationResult(success=False, error_message="No solution provided by ZAP")

        # Detect framework from code context
        framework = self._detect_framework(code_context.language, code_context.file_path)

        # Generate framework-specific fix code
        fixed_code = self._generate_framework_specific_fix(
            vuln.get('alert', ''),
            solution,
            framework,
            code_context
        )

        fix = SecurityFix(
            approach=FixApproach.FRAMEWORK_SECURITY,
            title=f"Fix {vuln.get('alert', 'HTTP security issue')} in {framework}",
            description=self._strip_html_tags(solution),
            vulnerable_code=code_context.vulnerable_code,
            fixed_code=fixed_code,
            explanation=f"ZAP identified {vuln.get('alert')} vulnerability. Apply framework-specific security configuration.",
            benefits=[
                'Addresses HTTP security misconfiguration',
                'Follows framework best practices',
                'Prevents common web attacks'
            ],
            language=code_context.language,
            framework=framework,
            complexity_level='low',
            security_impact='medium'
        )

        return FixGenerationResult(
            success=True,
            fixes=[fix],
            generation_metadata={
                'tool': 'zap',
                'confidence': 0.9,
                'framework': framework
            }
        )

    def _generate_checkov_fix(self, vuln: Dict, code_context: Optional[CodeContext]) -> FixGenerationResult:
        """
        Checkov-specific: Configuration/IaC security fixes.

        Uses rule knowledge base + YAML context.
        """
        rule_id = vuln.get('check_id', vuln.get('rule_name', ''))

        # Look up rule fix pattern
        fix_pattern = self._get_checkov_fix_pattern(rule_id)

        if not fix_pattern:
            return FixGenerationResult(success=False, error_message=f"No fix pattern for rule {rule_id}")

        fix = SecurityFix(
            approach=FixApproach.CONFIGURATION_CHANGE,
            title=fix_pattern['title'],
            description=fix_pattern['description'],
            vulnerable_code=code_context.vulnerable_code if code_context else '',
            fixed_code=fix_pattern['fixed_code'],
            explanation=fix_pattern['explanation'],
            benefits=fix_pattern.get('benefits', []),
            language=code_context.language if code_context else 'yaml',
            complexity_level='low',
            security_impact='medium'
        )

        return FixGenerationResult(
            success=True,
            fixes=[fix],
            generation_metadata={
                'tool': 'checkov',
                'confidence': 0.7,
                'rule_id': rule_id
            }
        )

    def _extract_osv_fixed_versions(self, affected: List[Dict]) -> List[str]:
        """Extract fixed versions from OSV affected ranges."""
        fixed_versions = []

        for affected_item in affected:
            for range_obj in affected_item.get('ranges', []):
                for event in range_obj.get('events', []):
                    if 'fixed' in event:
                        fixed_versions.append(event['fixed'])

        # Return unique versions, sorted by version number (latest first)
        return sorted(set(fixed_versions), reverse=True)

    def _generate_dependency_upgrade_code(self, package: str, version: str, ecosystem: str) -> str:
        """Generate ecosystem-specific dependency upgrade code."""
        if ecosystem == 'Maven':
            return f'implementation("{package}:{version}")'
        elif ecosystem == 'npm':
            return f'"{package}": "^{version}"'
        elif ecosystem == 'PyPI':
            return f'{package}=={version}'
        else:
            return f'Upgrade {package} to version {version}'

    def _detect_framework(self, language: str, file_path: str) -> str:
        """Detect web framework from code context."""
        if 'kotlin' in language.lower() or '.kt' in file_path:
            return 'Ktor'
        elif 'typescript' in language.lower() or 'javascript' in language.lower():
            return 'Express'
        return 'unknown'

    def _generate_framework_specific_fix(self, alert: str, solution: str, framework: str, code_context: CodeContext) -> str:
        """Generate framework-specific fix code."""
        # Framework-specific code generation logic
        # This can be expanded with templates for different frameworks

        if framework == 'Ktor' and 'CORS' in alert:
            return """install(CORS) {
    allowHost("app.example.com", schemes = listOf("https"))
    allowCredentials = true
}"""
        elif framework == 'Express' and 'CORS' in alert:
            return """app.use(cors({
    origin: 'https://app.example.com',
    credentials: true
}));"""

        return f"// Apply fix based on: {solution}"
```

---

## Implementation Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Create master architecture document (this document)
- [ ] Update all parser implementation plans
- [ ] Review and approve unified data format

### Phase 2: Parser Enhancements (Priority Order)

**Week 1-2: High-Value Dependency Parsers**
1. **OSV Parser** (2-3 days)
   - Add `_generate_osv_fix()` to MultiApproachFixGenerator
   - Implement `_extract_osv_fixed_versions()`
   - Test with 46 OSV vulnerabilities
   - Expected: 46 high-quality dependency fixes

2. **Trivy Parser** (1-2 days)
   - Fix regex bug (markdown link capture)
   - Update to use existing `_parse_dependency_info()`
   - Filter empty fixed versions
   - Expected: 13 high-quality Java dependency fixes

**Week 3-4: Code Pattern Parsers**
3. **Semgrep Parser** (3-4 days)
   - Integrate VulnerableCodeExtractor
   - Add `_generate_semgrep_fix()` using existing patterns
   - Test with 107 Semgrep findings
   - Expected: 70+ code pattern fixes with alternatives

4. **ZAP Parser** (2-3 days)
   - Integrate URLToCodeMapper → VulnerableCodeExtractor
   - Add `_generate_zap_fix()` with framework detection
   - Generate Ktor/Express-specific fixes
   - Expected: 9 HTTP security fixes with code context

**Week 5: Configuration Parsers**
5. **Checkov Parser** (2 days)
   - Integrate VulnerableCodeExtractor for YAML context
   - Add `_generate_checkov_fix()` with rule knowledge base
   - Expected: 10 workflow security fixes

6. **GitLeaks Parser** (0 days - DEFER)
   - Update plan to document deferral
   - No implementation (0 secrets found)

### Phase 3: Dataset Generation (Week 6)
- Implement ChatML conversion for each tool type
- Implement confidence-based filtering (if desired)
- Implement train/validation split
- Test complete pipeline end-to-end

### Phase 4: Model Training (Week 7-8)
- Fine-tune OLMo-2-1B with new dataset
- Evaluate fix generation quality
- Compare vs. baseline

---

## Success Metrics

### Data Quality
- **Dependency Fixes**: Target 100% have fixed versions (OSV/Trivy)
- **Code Pattern Fixes**: Target 70%+ have multiple approaches (Semgrep)
- **HTTP Security Fixes**: Target 90%+ have framework-specific code (ZAP)

### Pipeline Efficiency
- **AI API Calls**: Target = 0 (currently: 1 per vulnerability)
- **Processing Time**: Target < 5 minutes (currently: 20+ with AI)
- **Pipeline Phases**: Target = 2 (currently: 3)

### Training Data Volume
- **Total Vulnerabilities**: Target >= 200 (OSV 46 + Trivy 13 + Semgrep 70 + ZAP 9 + Checkov 10 + others)
- **High Confidence (1.0)**: Target >= 60 (OSV + Trivy)
- **With Alternatives**: Target >= 70 (Semgrep multi-approach)

---

## Appendix: Data Format Conversion

### From FixGenerationResult to Unified Format

```python
def convert_fix_result_to_format(fix_result: FixGenerationResult) -> Dict:
    """Convert MultiApproachFixGenerator result to unified format."""
    if not fix_result.success or not fix_result.fixes:
        return None

    primary_fix = fix_result.fixes[0]
    confidence = fix_result.generation_metadata.get('confidence', 0.5)

    fix_data = {
        'confidence': confidence,
        'description': primary_fix.description,
        'fixed_code': primary_fix.fixed_code,
        'explanation': primary_fix.explanation,
        'alternatives': []
    }

    # Add dependency-specific fields
    if hasattr(primary_fix, 'package_name'):
        fix_data['package'] = getattr(primary_fix, 'package_name', None)
        fix_data['from_version'] = getattr(primary_fix, 'from_version', None)
        fix_data['to_version'] = getattr(primary_fix, 'to_version', None)
        fix_data['ecosystem'] = getattr(primary_fix, 'ecosystem', None)

    # Add alternatives
    for alt_fix in fix_result.fixes[1:]:
        fix_data['alternatives'].append({
            'description': alt_fix.description,
            'fixed_code': alt_fix.fixed_code,
            'explanation': alt_fix.explanation
        })

    return fix_data

def dataclass_to_dict(code_context: CodeContext) -> Dict:
    """Convert CodeContext dataclass to dict."""
    return {
        'file_path': code_context.file_path,
        'language': code_context.language,
        'file_extension': code_context.file_extension,
        'vulnerability_line': code_context.vulnerability_line,
        'vulnerability_column': code_context.vulnerability_column,
        'vulnerable_code': code_context.vulnerable_code,
        'before_lines': code_context.before_lines,
        'after_lines': code_context.after_lines,
        'function_name': code_context.function_name,
        'function_context': code_context.function_context,
        'function_start_line': code_context.function_start_line,
        'function_end_line': code_context.function_end_line,
        'class_name': code_context.class_name,
        'class_context': code_context.class_context,
        'class_start_line': code_context.class_start_line,
        'extraction_type': getattr(code_context, 'extraction_type', 'code'),
        'extraction_success': True
    }
```

---

**Last Updated**: 2025-10-07
**Status**: Ready for Implementation
**Next Steps**: Update individual parser implementation plans
