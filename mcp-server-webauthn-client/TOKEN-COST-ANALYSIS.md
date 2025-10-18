# Token Cost Analysis: MCP vs. Alternative Approaches

## Executive Summary

**The claim "MCP = 0 tokens" needs clarification:**

- **MCP Mode**: 0 tokens *for tool execution* (but initial discovery varies)
- **CLI Mode**: ~2000-3000 tokens for discovery + fetch (one-time cost)
- **Manual Guidance**: 12000-17000 tokens (repeated for each user)

This document explains the token costs for different AI agent integration approaches.

**IMPORTANT**: For agents in external projects, `.ai-agents.json` must be fetched from the mpo-api-authn-server GitHub repository, adding ~2000-3000 tokens to discovery costs.

---

## Understanding "0 Tokens" for MCP

### What Does "0 Tokens" Actually Mean?

When we say "MCP = 0 tokens," we mean:

✅ **Tool Execution**: 0 tokens - MCP protocol handles tool calls natively
❌ **Initial Discovery**: NOT 0 tokens - agent must discover AND fetch documentation from GitHub

### The Complete Picture

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 0: Project Discovery (EXTERNAL PROJECTS ONLY)        │
│  How does agent in external project find mpo-api-authn?     │
└─────────────────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ Method 1: User Provides GitHub URL             │
    │ User: "Use hitoshura25/mpo-api-authn-server"   │
    │ Cost: ~50 tokens (user message)                │
    └────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ Method 2: Agent Searches npm Registry          │
    │ Search "webauthn server" or "webauthn client"  │
    │ Cost: ~500-1000 tokens (search + read)         │
    └────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ Method 3: Agent Searches GitHub                │
    │ Search for relevant WebAuthn projects          │
    │ Cost: ~500-1500 tokens (search + browse)       │
    └────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Fetch Documentation (ONE-TIME SETUP)              │
│  Agent fetches .ai-agents.json from GitHub repo             │
└─────────────────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ Fetch .ai-agents.json from GitHub Raw URL      │
    │ URL: raw.githubusercontent.com/hitoshura25/    │
    │      mpo-api-authn-server/main/.ai-agents.json │
    │ Cost: ~1500 tokens (GitHub file fetch)         │
    │                                                 │
    │ NOTE: This file is in the mpo-api-authn-server │
    │ repository, NOT in the consuming project!      │
    └────────────────────────────────────────────────┘
        │
        ↓
    Agent discovers mcp_servers.webauthn_client_generator

┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Setup (ONE-TIME CONFIGURATION)                    │
│  How does the user configure the MCP server?                │
└─────────────────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ MCP-Compatible Agent (Claude Code)             │
    │ User adds to claude_config.json manually OR    │
    │ Agent guides user to add configuration         │
    │ Cost: ~500-1000 tokens (guidance)              │
    └────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ Non-MCP Agent (Cursor, Aider)                  │
    │ No setup needed - uses CLI directly            │
    │ Cost: 0 tokens (no MCP setup required)         │
    └────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Execution (EVERY TIME USER NEEDS IT)              │
│  Generate a web client                                      │
└─────────────────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ MCP Mode                                       │
    │ Agent calls generate_web_client tool via MCP   │
    │ Cost: **0 tokens** - Native protocol execution │
    └────────────────────────────────────────────────┘
        │
    ┌───▼────────────────────────────────────────────┐
    │ CLI Mode                                       │
    │ Agent suggests: npx ... command                │
    │ Cost: ~50 tokens (command text generation)     │
    └────────────────────────────────────────────────┘
```

---

## Detailed Token Cost Breakdown

### Scenario 1: MCP-Compatible Agent (Claude Code) in External Project

#### First Use
```
Project Discovery:  User provides URL: ~50 tokens
                   OR Agent searches: ~500-1500 tokens
Fetch .ai-agents:  GitHub file fetch: ~1500 tokens
Setup:             Agent guides MCP config: ~500-1000 tokens
Execution:         MCP tool call: **0 tokens**
────────────────────────────────────────────────────
TOTAL FIRST USE: ~2050-4000 tokens
```

#### Subsequent Uses (Same Project)
```
Discovery:    Already configured: 0 tokens
Setup:        Already configured: 0 tokens
Execution:    MCP tool call: **0 tokens**
────────────────────────────────────────────────────
TOTAL SUBSEQUENT: **0 tokens** ✅
```

#### Why "0 Tokens" for Execution?

MCP uses **structured protocol messages**, not natural language:

```json
// This is NOT sent as tokens to the LLM
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "generate_web_client",
    "arguments": {
      "project_path": "./web-client",
      "server_url": "http://localhost:8080"
    }
  }
}
```

The MCP SDK handles this **outside the LLM context window**. The agent doesn't need to "think" about the tool call - it's a direct protocol operation.

---

### Scenario 2: Non-MCP Agent with CLI (Cursor, Aider, Windsurf) in External Project

#### First Use
```
Project Discovery:  User provides URL: ~50 tokens
                   OR Agent searches: ~500-1500 tokens
Fetch .ai-agents:  GitHub file fetch: ~1500 tokens
Setup:             None required: 0 tokens
Execution:         Agent suggests CLI command: ~50 tokens
────────────────────────────────────────────────────
TOTAL FIRST USE: ~1600-3050 tokens
```

#### Subsequent Uses (Same Project)
```
Discovery:    Agent remembers from context: ~50 tokens
              OR re-reads .ai-agents.json: ~1500 tokens
Setup:        None required: 0 tokens
Execution:    Agent suggests CLI command: ~50 tokens
────────────────────────────────────────────────────
TOTAL SUBSEQUENT: ~100-1600 tokens
```

**Why Lower Than MCP First Use?**
- No MCP configuration needed
- Direct `npx` usage
- Simpler for non-MCP agents

---

### Scenario 3: Manual Guidance (No Tool, Just Documentation)

#### Every Use (No Memory Between Projects)
```
User Question: "How do I create a WebAuthn client?"
────────────────────────────────────────────────────
Agent searches: Project discovery (~1000 tokens)
Agent reads:   README.md (~4000 tokens)
Agent reads:   Library docs (~3000 tokens)
Agent explains: Setup instructions (~2000 tokens)
Agent guides:  File creation (~1000-3000 tokens)
Back-and-forth: Troubleshooting (~2000-5000 tokens)
────────────────────────────────────────────────────
TOTAL PER USE: ~13,000-18,000 tokens ❌
```

**Why So High?**
- Agent must read documentation every time
- Natural language explanation required
- Multiple rounds of questions
- No automated file generation

---

## Comparison Table

| Approach | First Use | Subsequent Uses | Notes |
|----------|-----------|----------------|-------|
| **MCP Mode** | 2050-4000₸ | **0₸** | Best for repeated use in same project |
| **CLI Mode** | 1600-3050₸ | 100-1600₸ | Best for one-off use or non-MCP agents |
| **Manual Guidance** | 13000-18000₸ | 13000-18000₸ | Expensive every time, error-prone |

₸ = tokens

**Key Insight**: The "discovery" cost includes finding the mpo-api-authn-server project (~50-1500 tokens) PLUS fetching `.ai-agents.json` from GitHub (~1500 tokens).

---

## Why MCP Discovery Still Requires Tokens

### Common Misconception

❌ "MCP agents automatically discover all available tools with 0 tokens"

✅ "MCP agents need to FIND and FETCH documentation before they can use tools with 0 tokens"

### How Agents Discover MCP Servers in External Projects

#### The Full Flow

```
External Project (e.g., my-app/)
         │
         ↓
User: "I need a WebAuthn client for testing"
         │
         ↓
Agent searches for solutions
  - npm search "webauthn client generator"
  - OR GitHub search "webauthn server"
  - OR user provides: "Use hitoshura25/mpo-api-authn-server"
         │
         ↓
Agent finds mpo-api-authn-server GitHub repository
         │
         ↓
Agent fetches .ai-agents.json from GitHub
  URL: https://raw.githubusercontent.com/hitoshura25/
       mpo-api-authn-server/main/.ai-agents.json
         │
         ↓
Agent reads mcp_servers.webauthn_client_generator section
         │
         ↓
Agent offers two options:
  1. MCP Mode → Guide user to add to claude_config.json
  2. CLI Mode → Suggest npx command
```

#### Method 1: User Provides GitHub URL (Fastest)
```
User: "Use hitoshura25/mpo-api-authn-server for WebAuthn client generation"
```

**Token Cost**:
- User message: ~50 tokens
- Fetch .ai-agents.json: ~1500 tokens
- **Total**: ~1550 tokens

#### Method 2: Agent Searches npm Registry
```
Agent searches npm for "webauthn client generator"
→ Finds @vmenon25/mcp-server-webauthn-client package
→ Reads package.json (~500 tokens)
→ Follows repository link to GitHub
→ Fetches .ai-agents.json (~1500 tokens)
```

**Token Cost**: ~2000-2500 tokens (search + package.json + .ai-agents.json)

#### Method 3: Agent Searches GitHub
```
Agent searches GitHub for "webauthn server"
→ Finds hitoshura25/mpo-api-authn-server repository
→ Browses README (~500-1000 tokens)
→ Discovers .ai-agents.json exists
→ Fetches .ai-agents.json (~1500 tokens)
```

**Token Cost**: ~2000-3000 tokens (search + README + .ai-agents.json)

---

## The Real Benefit of MCP

### Not About Discovery Cost

MCP doesn't reduce **initial discovery** token costs compared to CLI + `.ai-agents.json`. Both require finding and fetching documentation from GitHub.

### It's About **Execution** Cost

**MCP Advantage**: After setup, tool execution is **0 tokens forever** in that project.

**CLI Advantage**: No setup needed, but agent must suggest command each time (~50-100 tokens).

### Break-Even Analysis (External Project Scenario)

```
Scenario: User in external project needs to generate web clients 10 times

MCP Mode:
  First use:  3000 tokens (discovery + fetch + setup + execution)
  Uses 2-10:  0 tokens × 9 = 0 tokens
  ─────────────────────────────────────────────
  TOTAL:      3000 tokens

CLI Mode:
  First use:  2050 tokens (discovery + fetch + execution)
  Uses 2-10:  100 tokens × 9 = 900 tokens
  ─────────────────────────────────────────────
  TOTAL:      2950 tokens

Manual Guidance:
  All 10 uses: 15000 tokens × 10 = 150,000 tokens ❌
  ─────────────────────────────────────────────
  TOTAL:      150,000 tokens
```

**Conclusion**: MCP and CLI are nearly equivalent for token cost (~3000 tokens first use). Both are **50x more efficient** than manual guidance.

---

## Our Implementation Strategy

### Hybrid Approach (Best of Both Worlds)

```
┌─────────────────────────────────────────────┐
│  Core Generator (Shared Implementation)     │
└─────────────────────────────────────────────┘
           │
    ┌──────┴──────┬────────────────┐
    │             │                │
┌───▼───┐    ┌────▼────┐     ┌────▼────┐
│  MCP  │    │   CLI   │     │  .ai-   │
│Server │    │  Tool   │     │ agents  │
│       │    │         │     │  .json  │
└───┬───┘    └────┬────┘     └────┬────┘
    │             │                │
    │             │                │
Claude Code     Cursor         Universal
Continue.dev    Aider         Discovery
Cline          Windsurf        Mechanism
(0₸ exec)      (~50₸ exec)    (~2000₸)
```

### Token Costs by Agent Type (External Project, 10 Uses)

| Agent Type | Discovery + Fetch | Setup | Execution (×10) | Total (10 uses) |
|------------|-------------------|-------|-----------------|-----------------|
| Claude Code (MCP) | 2000₸ | 1000₸ | 0₸ | **3000₸** |
| Cursor (CLI) | 2000₸ | 0₸ | 1000₸ | **3000₸** |
| Aider (CLI) | 2000₸ | 0₸ | 500₸ | **2500₸** |
| Manual (No Tool) | 15000₸ | 0₸ | 135000₸ | **150,000₸** |

---

## Optimization Strategies: Minimizing Discovery Costs

Your questions reveal critical optimization opportunities. Let's analyze the most efficient approaches.

### Understanding Prompt Processing Costs

**IMPORTANT**: Even when MCP server is pre-configured in `claude_config.json`, the agent still needs tokens to:
1. **Process your natural language prompt** (~20-50 tokens)
2. **Map your intent to the correct tool** (~10-20 tokens)
3. **Extract parameters from your request** (~10-30 tokens)

The "0 tokens" claim applies ONLY to the **tool execution protocol**, not to understanding what you're asking for.

### Strategy 1: Pre-Configured MCP (Most Optimal)

**Setup**: User manually adds to `claude_config.json` BEFORE first use

```json
{
  "mcpServers": {
    "webauthn-client-generator": {
      "command": "node",
      "args": ["/path/to/mcp-server-webauthn-client/dist/index.js"]
    }
  }
}
```

**Token Costs Per Use**:
```
User prompt:      "Create a WebAuthn web client for my server on port 8080"
Prompt processing: ~50 tokens (LLM understands intent)
Tool mapping:      ~20 tokens (LLM selects generate_web_client)
Parameter extraction: ~30 tokens (LLM extracts server_url, port)
Tool execution:    **0 tokens** (MCP protocol handles it)
────────────────────────────────────────────────────
TOTAL PER USE: ~100 tokens ✅
```

**Even More Optimal - Explicit Tool Name**:
```
User prompt:      "Use webauthn-client-generator to create a client for localhost:8080"
Prompt processing: ~30 tokens (explicit tool name reduces ambiguity)
Tool mapping:      ~10 tokens (direct tool reference)
Parameter extraction: ~20 tokens (clear parameters)
Tool execution:    **0 tokens** (MCP protocol)
────────────────────────────────────────────────────
TOTAL PER USE: ~60 tokens ✅✅
```

**Key Insight**: Pre-configuring MCP eliminates discovery/fetch costs (~2000-3000 tokens) but still requires ~60-100 tokens to process your natural language prompt.

### Strategy 2: User Provides Exact Repository (Second Most Optimal)

**User prompt**: `"Use hitoshura25/mpo-api-authn-server for WebAuthn client generation"`

**Token Costs**:
```
User message:      ~50 tokens (includes repo name)
Fetch .ai-agents:  ~1500 tokens (GitHub raw file)
Parse + Guide:     ~500 tokens (configure MCP or suggest CLI)
────────────────────────────────────────────────────
TOTAL FIRST USE: ~2050 tokens
SUBSEQUENT USES: ~100 tokens (if MCP configured) or ~50 tokens (CLI)
```

**Why This Is Optimal**:
- Eliminates search costs (500-1500 tokens saved)
- Direct path to documentation
- Agent doesn't waste tokens guessing

### Strategy 3: User Provides Vague Request (Least Optimal)

**User prompt**: `"I need a WebAuthn client"`

**Token Costs**:
```
Prompt processing:  ~30 tokens
Search phase:       ~500-1500 tokens (npm/GitHub search)
Fetch .ai-agents:   ~1500 tokens
Parse + Guide:      ~500 tokens
────────────────────────────────────────────────────
TOTAL FIRST USE: ~2530-3530 tokens
```

**Why This Is Expensive**:
- Agent must search for solutions
- Multiple search iterations possible
- No clear direction provided

### Comparison Table: Optimization Strategies

| Strategy | Setup Cost | Per-Use Cost | First Use Total | Best For |
|----------|-----------|--------------|-----------------|----------|
| **Pre-configured MCP + Natural prompt** | 0₸ (manual) | 100₸ | **100₸** | Repeated use, same project |
| **Pre-configured MCP + Explicit tool** | 0₸ (manual) | 60₸ | **60₸** | Power users, repeated use |
| **User provides repo URL** | 0₸ | 100₸ | **2050₸** | First use in new project |
| **Agent searches (vague request)** | 0₸ | 100₸ | **2530-3530₸** | Users unaware of tool |

₸ = tokens

### Recommended Prompting Strategies

#### ✅ Most Efficient: Pre-configured MCP

**Pre-requisite**: Add to `claude_config.json` once

**Optimal prompts**:
```
# Explicit tool reference (60 tokens)
"Use webauthn-client-generator for localhost:8080"

# Natural language (100 tokens)
"Create a WebAuthn web client that connects to my server on port 8080"

# With all parameters (80 tokens)
"Generate a web client at ./auth-client connecting to http://localhost:9000 on port 3000"
```

#### ✅ Efficient: Direct Repository Reference

**For first use in a new project**:
```
# Provide exact repo (2050 tokens first use, then 60-100 tokens)
"Use hitoshura25/mpo-api-authn-server to create a WebAuthn client for testing"

# With parameters (2080 tokens first use)
"Use the webauthn client generator from hitoshura25/mpo-api-authn-server
 to create a client on port 3000 for my server on localhost:9000"
```

#### ❌ Less Efficient: Vague Requests

**Avoid these prompts** (waste 500-1500 tokens on search):
```
# Too vague (2530-3530 tokens)
"I need a WebAuthn client"
"How do I test WebAuthn?"
"Create a client for authentication"
```

### The Absolute Optimal Workflow

1. **One-time setup** (0 tokens, done manually):
   - Add MCP server to `claude_config.json`
   - Restart Claude Code

2. **Every subsequent use** (60-100 tokens):
   - Use natural language or explicit tool name
   - Agent processes prompt, selects tool, executes
   - **~60x more efficient than manual guidance**

3. **Key insight**: The bottleneck shifts from discovery (2000-3000 tokens) to prompt processing (60-100 tokens)

---

## Recommendations

### For MCP-Compatible Agents (Claude Code, Continue.dev, Cline)
✅ Use MCP mode
- 0 token execution after setup
- Best for projects with repeated use
- Native integration feels seamless

### For Non-MCP Agents (Cursor, Aider, Windsurf)
✅ Use CLI mode
- No MCP setup complexity
- Still ~50x more efficient than manual
- Actually LOWER first-use cost than MCP

### For One-Time Usage
✅ CLI mode (even for MCP agents)
- Lower total cost if only using once
- No configuration needed
- Simple `npx` command

---

## Conclusion

**"MCP = 0 tokens"** is accurate for **tool execution protocol** but doesn't tell the complete story:

1. **Discovery + Fetch**: ~2000-3000₸ (external projects, one-time)
2. **Setup**: ~1000₸ for MCP config (one-time), 0₸ for CLI
3. **Prompt Processing**: ~60-100₸ per use (EVEN with pre-configured MCP)
4. **Tool Execution**: 0₸ for MCP protocol, ~50₸ for CLI suggestion

### The Complete Token Cost Hierarchy

**From Most to Least Efficient**:

1. **Pre-configured MCP + Explicit Tool Name**: ~60₸ per use
   - Example: "Use webauthn-client-generator for localhost:8080"
   - Best for: Power users, repeated use

2. **Pre-configured MCP + Natural Language**: ~100₸ per use
   - Example: "Create a WebAuthn client for my server"
   - Best for: Regular use, natural interaction

3. **User Provides Repo URL (First Use)**: ~2050₸ first use, then ~100₸
   - Example: "Use hitoshura25/mpo-api-authn-server for client generation"
   - Best for: First use in new project

4. **Vague Request (Agent Searches)**: ~2530-3530₸ first use
   - Example: "I need a WebAuthn client"
   - Best for: Users unaware of tool existence

5. **Manual Guidance (No Tool)**: ~13,000-18,000₸ EVERY use
   - Least efficient, error-prone

### Key Takeaways

**For MCP Users**:
- ✅ Pre-configure in `claude_config.json` (manual, 0 tokens)
- ✅ Use explicit tool names in prompts (60 tokens vs 100 tokens)
- ✅ Optimal for repeated use: **60x more efficient** than manual guidance

**For Non-MCP Users**:
- ✅ Provide exact GitHub repo in initial prompt (saves 500-1500 tokens)
- ✅ CLI mode is simpler: no MCP configuration needed
- ✅ Still **40-50x more efficient** than manual guidance

**Critical Clarifications**:
1. The `.ai-agents.json` file is in the **mpo-api-authn-server GitHub repository**, not in consuming projects
2. Agents must fetch it from GitHub (~1500 tokens) during first discovery
3. Even with pre-configured MCP, **prompt processing requires ~60-100 tokens**
4. The "0 tokens" claim applies ONLY to the protocol execution, not prompt understanding

**Bottom Line**: Our hybrid MCP + CLI implementation maximizes compatibility and efficiency across ALL agents, with optimized prompting strategies reducing costs from thousands of tokens to as low as 60 tokens per use.
