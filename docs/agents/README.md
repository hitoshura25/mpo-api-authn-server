# Claude Code Agents

This project uses specialized Claude Code agents located in `.claude/agents/`. These agents provide domain-specific expertise for various development tasks.

## Available Agents

- **[android-integration-agent.md](../../.claude/agents/android-integration-agent.md)** - Android-specific issues and testing
- **[api-contract-validator-agent.md](../../.claude/agents/api-contract-validator-agent.md)** - Contract compliance validation  
- **[client-generation-agent.md](../../.claude/agents/client-generation-agent.md)** - API client regeneration and updates
- **[code-quality-modernization.md](../../.claude/agents/code-quality-modernization.md)** - Code quality improvements and modernization
- **[cross-platform-testing-agent.md](../../.claude/agents/cross-platform-testing-agent.md)** - Multi-platform test coordination
- **[documentation-synchronization.md](../../.claude/agents/documentation-synchronization.md)** - Documentation consistency and updates
- **[multi-module-refactoring.md](../../.claude/agents/multi-module-refactoring.md)** - Complex refactoring across modules
- **[openapi-sync-agent.md](../../.claude/agents/openapi-sync-agent.md)** - API specification synchronization
- **[webauthn-security-analysis.md](../../.claude/agents/webauthn-security-analysis.md)** - WebAuthn security vulnerability analysis

## Usage

These agents are automatically discovered by Claude Code and should not be moved from their current location. They provide specialized workflows for complex development tasks that require domain expertise.

## Agent Guidelines

- Agents in `.claude/agents/` are essential for Claude Code functionality
- Do not modify, move, or delete agent files
- Each agent handles specific cross-cutting concerns in the codebase
- Use subagents for complex multi-file operations as recommended in CLAUDE.md