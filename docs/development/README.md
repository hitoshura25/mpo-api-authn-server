# Development Documentation Index

This directory contains critical development documentation to ensure code quality, maintainability, and performance across the WebAuthn project.

## 🚨 Critical Development Requirements

### Gradle Configuration Cache Compatibility (MANDATORY)

**ALL custom Gradle task development MUST follow configuration cache compatibility patterns.**

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [Gradle Configuration Cache Compatibility](gradle-configuration-cache-compatibility.md) | **Complete guide** with examples and patterns | Before developing any custom Gradle tasks |
| [Gradle Task Code Review Checklist](gradle-task-code-review-checklist.md) | **Systematic checklist** for reviews | For ALL Gradle task modifications |
| [Gradle Config Cache Quick Fixes](gradle-config-cache-quick-fixes.md) | **Emergency reference** for common issues | When fixing configuration cache violations |

**Automated Validation:**
```bash
# Validate all build files
./scripts/core/validate-gradle-config-cache.sh

# Test specific task
./scripts/core/validate-gradle-config-cache.sh [task-name]
```

### Why Configuration Cache Compatibility Is Critical
- **Performance**: 50-90% build time improvements for all developers
- **Reliability**: Prevents silent failures in template processing and client generation
- **CI/CD Impact**: Violations break publishing workflows and automation
- **Team Productivity**: One developer's violation affects ALL developers' build performance

---

## 📋 Development Standards

### Code Quality Standards
| Document | Purpose |
|----------|---------|
| [Coding Standards](coding-standards.md) | Import organization, dependency management, and enforcement |

### Platform-Specific Guides
| Document | Purpose |
|----------|---------|
| [Android Package Structure](android-package-structure.md) | Android client library organization |
| [Client Library Migration Guide](client-library-migration-guide.md) | Migration between client library architectures |
| [Client Library Staging](client-library-staging.md) | Staging package testing workflows |

### Scripts and Tools
| Document | Purpose |
|----------|---------|
| [Scripts Usage](scripts-usage.md) | Overview of all development scripts |
| [Security Scripts](security-scripts.md) | Security scanning and vulnerability monitoring |

---

## 🔧 Workflow Documentation

### Publishing and CI/CD
| Directory | Purpose |
|-----------|---------|
| [workflows/](workflows/) | GitHub Actions workflow documentation |

---

## 🚀 Quick Start for New Developers

1. **Read CLAUDE.md**: Project overview and development principles
2. **Review Coding Standards**: [coding-standards.md](coding-standards.md)
3. **Before ANY Gradle task development**: Read [gradle-configuration-cache-compatibility.md](gradle-configuration-cache-compatibility.md)
4. **For code reviews**: Use [gradle-task-code-review-checklist.md](gradle-task-code-review-checklist.md)
5. **When stuck**: Check [gradle-config-cache-quick-fixes.md](gradle-config-cache-quick-fixes.md)

---

## 🎯 Common Development Tasks

### Adding New Gradle Tasks
1. **MUST READ FIRST**: [gradle-configuration-cache-compatibility.md](gradle-configuration-cache-compatibility.md)
2. **Follow patterns** from the complete guide
3. **Test with**: `./scripts/core/validate-gradle-config-cache.sh [task-name]`
4. **Code review using**: [gradle-task-code-review-checklist.md](gradle-task-code-review-checklist.md)

### Modifying Client Libraries
1. **Review architecture**: [client-library-migration-guide.md](client-library-migration-guide.md)
2. **Test staging workflow**: [client-library-staging.md](client-library-staging.md)
3. **Validate Gradle tasks**: Configuration cache compatibility

### Working with Security
1. **Security script overview**: [security-scripts.md](security-scripts.md)
2. **Workflow integration**: [workflows/](workflows/)

---

## 🔍 Troubleshooting

### Configuration Cache Issues
- **Quick fixes**: [gradle-config-cache-quick-fixes.md](gradle-config-cache-quick-fixes.md)
- **Error patterns**: See "Common Error Messages → Fixes" section
- **Automated diagnosis**: `./scripts/core/validate-gradle-config-cache.sh`

### Build Issues
- **Coding standards**: [coding-standards.md](coding-standards.md) 
- **Script problems**: [scripts-usage.md](scripts-usage.md)

### Workflow Issues
- **GitHub Actions**: [workflows/](workflows/) directory

---

## 📚 Documentation Maintenance

### When to Update This Documentation
- **New Gradle patterns discovered**: Update compatibility guide
- **New anti-patterns found**: Add to quick fixes and checklist
- **Workflow changes**: Update workflow documentation
- **Tool additions**: Update scripts usage guide

### Documentation Standards
- **All code examples must work**: Test before committing
- **Cross-reference related docs**: Maintain consistency
- **Update automation**: Keep validation scripts current
- **Real-world examples**: Use actual project examples

---

**Remember**: Configuration cache compatibility is not optional. It's a fundamental requirement that affects every developer's productivity and the reliability of our build system.