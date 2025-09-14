# Complete Pattern Verification Protocol - Comprehensive Guide

This document contains detailed examples and comprehensive guidance for pattern verification across all codebase contexts, extracted from CLAUDE.md for reference.

## Universal Pattern Verification Checklist

**When reusing existing patterns in ANY codebase context, ALWAYS verify ALL implementation details match existing usage, not just architectural concepts.**

**THE FUNDAMENTAL PROBLEM**: Assuming architectural understanding equals implementation accuracy across ALL code generation contexts.

### BEFORE implementing any code that reuses existing patterns:

**Step 1: 📋 Identify Reference Implementations**:
```bash
# Find ALL existing implementations of the pattern across the codebase
grep -r "pattern-keyword" .github/workflows/ src/ scripts/ *.gradle *.yml *.json
find . -name "*.kt" -o -name "*.ts" -o -name "*.yml" | xargs grep "pattern"
```

**Step 2: 🔍 Extract Complete Implementation Details**:
- **Command syntax**: Exact commands, spaces, hyphens, flags, ordering
- **Parameter patterns**: Order, format, quoting style, escaping
- **File paths**: Relative vs absolute, naming conventions, directory structure
- **Environment variables**: Names, formats, scoping, default values
- **Error handling**: Patterns for failures, cleanup, exit codes, conditions
- **Code conventions**: Indentation, spacing, variable naming, function signatures
- **Configuration syntax**: Key names, nesting, data types, comment styles

**Step 3: ✅ Verify Against Multiple Examples**:
- **Find 2-3 existing uses** of the same pattern in different contexts
- **Compare syntax consistency** across all examples
- **Identify project-specific conventions** vs language/tool standards
- **Note context-specific variations** (test vs production, different modules)

**Step 4: 🧪 Implementation Verification Pattern**:
```bash
# Extract exact syntax from existing implementations
grep -A5 -B5 "target-pattern" existing-file

# Verify your new implementation matches EXACTLY
diff <(grep "your-pattern" existing-file) <(grep "your-pattern" new-file)

# For complex patterns, extract full context blocks
sed -n '/start-pattern/,/end-pattern/p' reference-file
```

## Pattern Verification Examples by Context

### ✅ CORRECT Process Examples:

#### GitHub Actions:
```bash
grep -r "docker.*compose" .github/workflows/
# Found: docker compose (space, not hyphen) → Use exactly
```

#### Kotlin/Gradle Code:
```bash
grep -r "implementation.*webauthn" *.gradle.kts
# Found: implementation("com.yubico:webauthn-server-core:2.6.0") → Match format
```

#### Script Patterns:
```bash
grep -r "set -euo pipefail" scripts/
# Found: set -euo pipefail (specific flags) → Use same flags
```

#### Configuration Files:
```bash
grep -A3 "environment:" docker-compose*.yml
# Found: specific indentation and key patterns → Match exactly
```

#### Application Code:
```bash
grep -r "class.*Test" src/
# Found: class SomeTest : BaseIntegrationTest() → Follow naming pattern
```

## Common Pattern Verification Failures Across All Contexts

### Command/Script Syntax:
- `docker-compose` vs `docker compose`, `npm run` vs `npx`, flag ordering
- `./gradlew` vs `gradle`, relative vs absolute script paths
- Shell options: `set -e` vs `set -euo pipefail`

### Code Conventions:
- Function naming: `camelCase` vs `snake_case`, prefix patterns
- Import statements: relative vs absolute, ordering, grouping
- Error handling: `try-catch` vs `Result<T>`, exception types

### Configuration Syntax:
- YAML indentation (2 vs 4 spaces), key naming (`snake_case` vs `kebab-case`)
- JSON formatting, comment styles, environment variable patterns
- Build file conventions: dependency declarations, plugin application

### File Organization:
- Directory structure: `src/main/kotlin` vs `src/kotlin`
- Test file naming: `*Test.kt` vs `*Tests.kt` vs `Test*.kt`
- Resource file locations and naming patterns

## Context-Specific Verification Commands

```bash
# Workflow/CI Patterns
grep -r "docker.*compose\|npm.*run\|gradle.*build" .github/workflows/

# Application Code Patterns
grep -r "class.*\|fun.*\|val.*" src/main/kotlin/ src/test/kotlin/

# Script Patterns  
grep -r "set.*\|if.*then\|function.*" scripts/

# Configuration Patterns
grep -r "environment:\|ports:\|version:" *.yml *.yaml
grep -r "implementation\|testImplementation" *.gradle.kts

# Build/Dependency Patterns
grep -r "plugins.*\|dependencies.*\|repositories.*" build.gradle.kts */build.gradle.kts
```

## Critical Real-World Examples

### August 2025 - Docker Compose Commands
Used `docker-compose` instead of `docker compose`
- **Root Cause**: Understood Docker Compose architecture but didn't verify command syntax
- **Pattern**: Good architectural grasp, missed implementation details

### Previous - Gradle Dependencies
Wrong dependency syntax format
- **Root Cause**: Assumed standard Gradle syntax instead of checking project patterns
- **Pattern**: External knowledge applied without local verification

### Previous - Test File Naming
Inconsistent test class naming conventions
- **Root Cause**: Used general conventions instead of project-specific patterns
- **Pattern**: Generic best practices overrode local consistency

## UNIVERSAL ENFORCEMENT RULE

**Every reused pattern must show `grep`/`find` evidence of existing usage before implementation, regardless of context (workflows, code, configs, scripts, documentation).**

## Integration with Existing Tools

- **IDE Search**: Use project-wide search before implementing patterns
- **Git History**: `git log --grep="pattern"` to understand pattern evolution  
- **Code Review**: Verify pattern consistency in review process
- **Linting**: Configure linters to enforce discovered patterns

## Why This Matters Universally

- **Consistency**: Maintains codebase coherence across all contexts
- **Maintainability**: Reduces cognitive load for developers
- **Reliability**: Prevents subtle bugs from syntax/convention mismatches
- **Quality**: Ensures new code follows established, proven patterns

## Advanced Pattern Analysis Techniques

### Multi-Context Pattern Discovery
```bash
# Cross-reference patterns across different file types
for pattern in "test" "build" "deploy"; do
  echo "=== Pattern: $pattern ==="
  grep -r "$pattern" --include="*.kt" --include="*.yml" --include="*.gradle.kts" .
done
```

### Pattern Evolution Tracking
```bash
# Track how patterns have evolved over time
git log --grep="docker" --oneline | head -10
git log -p --grep="compose" -- "*.yml" | head -50
```

### Cross-Platform Pattern Validation
```bash
# Ensure patterns work across different environments
grep -r "platform\|os\|arch" .github/workflows/
grep -r "java\|kotlin\|node" build.gradle.kts */build.gradle.kts
```

### Pattern Consistency Audit
```bash
# Audit for inconsistent pattern usage
# Example: Check for mixed dependency declaration styles
grep -r "implementation(" . | grep -v "implementation(\"" | head -5
grep -r "testImplementation" . | wc -l
```

This comprehensive approach ensures all patterns are verified against actual codebase usage rather than assumptions or external knowledge.