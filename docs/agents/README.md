# Claude Code Agents

This project uses specialized Claude Code agents located in `.claude/agents/`. These agents provide domain-specific expertise for various development tasks.

## Available Agents

- **[android-integration-agent.md](../../.claude/agents/android-integration-agent.md)** - Android-specific client integration, testing, and debugging issues
- **[api-contract-validator-agent.md](../../.claude/agents/api-contract-validator-agent.md)** - OpenAPI contract compliance validation and consistency checking  
- **[client-generation-agent.md](../../.claude/agents/client-generation-agent.md)** - Multi-platform client regeneration and dependency management
- **[code-quality-modernization.md](../../.claude/agents/code-quality-modernization.md)** - Code quality improvements, Kotlin modernization, and Detekt fixes
- **[cross-platform-testing-agent.md](../../.claude/agents/cross-platform-testing-agent.md)** - Cross-platform test orchestration and E2E validation
- **[multi-module-refactoring.md](../../.claude/agents/multi-module-refactoring.md)** - Large-scale structural changes across the multi-module project
- **[openapi-sync-agent.md](../../.claude/agents/openapi-sync-agent.md)** - OpenAPI specification drift detection and synchronization
- **[security-vulnerability-analyst.md](../../.claude/agents/security-vulnerability-analyst.md)** - Comprehensive security analysis, vulnerability identification, and threat modeling

## Agent Specializations

### **Platform-Specific Agents**
- **android-integration-agent**: Android build system, emulator setup, WebAuthn client integration, UI testing
- **client-generation-agent**: OpenAPI client regeneration, dependency management, multi-platform publishing

### **Quality & Architecture Agents**
- **code-quality-modernization**: Functional programming patterns, Kotlin best practices, Detekt violations
- **multi-module-refactoring**: Cross-module coordination, renaming operations, architectural improvements
- **api-contract-validator-agent**: Server-client contract validation, endpoint coverage analysis

### **Testing & Integration Agents**
- **cross-platform-testing-agent**: E2E test coordination, multi-platform validation, integration failure diagnosis
- **openapi-sync-agent**: Specification drift detection, response structure analysis, client contract validation

### **Security Agents**
- **security-vulnerability-analyst**: Threat modeling, vulnerability assessment, security remediation strategies

## When to Use Subagents

**Always consider subagents for:**
- ✅ Multi-file changes (>2 files)
- ✅ Systematic refactoring patterns
- ✅ Cross-cutting concerns (renaming, imports)
- ✅ Complex searches requiring multiple rounds
- ✅ Performance optimization tasks
- ✅ Documentation updates across multiple files

**Performance Benefits:**
- 80-95% reduction in tool calls for complex tasks
- Faster completion through specialized expertise
- Better quality through systematic approaches

## Usage Guidelines

### **Automatic Discovery**
These agents are automatically discovered by Claude Code and should not be moved from their current location in `.claude/agents/`.

### **Best Practices**
- **Don't modify agent files** - They're essential for Claude Code functionality
- **Use specific agents** for domain-specific tasks rather than general-purpose
- **Delegate complex work** - When in doubt, use a subagent for multi-step operations
- **Follow CLAUDE.md guidance** - See critical reminders about proactive subagent usage

### **Agent Selection Guide**
```
Task Type → Recommended Agent
├── Android issues → android-integration-agent
├── Client publishing → client-generation-agent  
├── Code quality → code-quality-modernization
├── Large refactors → multi-module-refactoring
├── API validation → api-contract-validator-agent
├── E2E testing → cross-platform-testing-agent
├── OpenAPI sync → openapi-sync-agent
└── Security analysis → security-vulnerability-analyst
```