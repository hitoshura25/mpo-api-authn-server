# MCP Web Client Generator - Implementation Plan

**Status**: In Progress
**Created**: 2025-10-17
**Owner**: Vinayak Menon

## Overview

Create a focused Model Context Protocol (MCP) server that helps AI agents in other projects generate WebAuthn web clients. The other project already has docker-compose with webauthn-server running - they just need to create a web client that connects to it.

## Background

### What is MCP?

Model Context Protocol (MCP) is a standard protocol that allows AI agents to interact with external tools and services. MCP servers expose tools that AI agents can discover and use automatically.

**User Experience Flow**:
```
User (in Project B) → Claude/AI Agent → MCP Client → MCP Server → Returns Generated Files
```

### Why MCP Instead of Just .ai-agents.json?

**Static JSON Approach** (Current):
- ❌ Fixed information, no interaction
- ❌ AI must interpret and generate code manually
- ❌ No validation or troubleshooting
- ❌ User must create all files themselves

**Interactive MCP Server** (This Implementation):
- ✅ Dynamic conversation flow
- ✅ Generates actual working files
- ✅ Framework-specific code (React/Vue/Vanilla)
- ✅ Customizable to user's needs
- ✅ Preserves critical integration patterns automatically

## Scope (Narrow Focus)

### What We're Building
Single MCP tool: `generate_web_client` - Generates a complete web client that connects to an existing webauthn-server instance in docker-compose.

### What We're NOT Building (Out of Scope)
- ❌ Docker-compose generation (user already has this)
- ❌ Server setup wizard
- ❌ Multi-step interactive wizard
- ❌ Validation tools
- ❌ Troubleshooting tools

These can be added later if needed. Initial focus: **web client generation only**.

## Technical Architecture

### MCP Server Package Structure

```
mcp-server-webauthn-client/
├── package.json                    # MCP server package
├── tsconfig.json                   # TypeScript configuration
├── src/
│   ├── index.ts                   # Main MCP server implementation
│   ├── templates/                 # Code generation templates
│   │   ├── vanilla/               # Vanilla TypeScript templates
│   │   │   ├── package.json.hbs
│   │   │   ├── webauthn-client.ts.hbs
│   │   │   ├── types.ts.hbs
│   │   │   ├── server.ts.hbs
│   │   │   ├── index.html.hbs
│   │   │   ├── webpack.config.js.hbs
│   │   │   └── tsconfig.json.hbs
│   │   ├── react/                 # Future: React templates
│   │   └── vue/                   # Future: Vue templates
│   └── lib/
│       └── generator.ts           # File generation logic
└── README.md                       # MCP server documentation
```

### Generated Web Client Structure

When AI agent calls the MCP tool, it generates this structure in the user's project:

```
{project_path}/
├── package.json                    # With all required dependencies
├── tsconfig.json                   # TypeScript configuration
├── webpack.config.js               # Build configuration
├── src/
│   ├── webauthn-client.ts         # Complete WebAuthn integration
│   ├── types.ts                   # TypeScript type definitions
│   └── server.ts                  # Express dev server
├── public/
│   └── index.html                 # Test UI
└── README.md                       # Usage instructions
```

## MCP Tool Definition

### Tool: `generate_web_client`

**Description**: Generate a complete WebAuthn web client that connects to an existing webauthn-server instance

**Input Schema**:
```json
{
  "name": "generate_web_client",
  "description": "Generate a complete WebAuthn web client using the @vmenon25/mpo-webauthn-client npm library",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_path": {
        "type": "string",
        "description": "Where to create the web client directory (e.g., './web-client')",
        "default": "./web-client"
      },
      "framework": {
        "type": "string",
        "enum": ["vanilla", "react", "vue"],
        "description": "Web framework to use",
        "default": "vanilla"
      },
      "server_url": {
        "type": "string",
        "description": "URL of the webauthn-server instance",
        "default": "http://localhost:8080"
      },
      "client_port": {
        "type": "number",
        "description": "Port for the web client dev server",
        "default": 8082
      }
    },
    "required": ["project_path"]
  }
}
```

**Output**:
Returns status message and list of generated files:
```json
{
  "success": true,
  "message": "Web client generated successfully!",
  "files_created": [
    "./web-client/package.json",
    "./web-client/src/webauthn-client.ts",
    "./web-client/src/types.ts",
    "./web-client/src/server.ts",
    "./web-client/public/index.html",
    "./web-client/webpack.config.js",
    "./web-client/tsconfig.json",
    "./web-client/README.md"
  ],
  "next_steps": [
    "cd web-client",
    "npm install",
    "npm run build",
    "npm start",
    "Open http://localhost:8082"
  ]
}
```

## Critical WebAuthn Integration Patterns

These patterns MUST be preserved in all generated code (from CLAUDE.md and web-test-client/):

### Pattern 1: JSON Parsing
Server responses contain JSON strings that must be parsed before passing to SimpleWebAuthn:

```typescript
// CRITICAL: Parse the JSON string
let publicKeyOptions: any;
if (typeof startResponse.publicKeyCredentialCreationOptions === 'string') {
    publicKeyOptions = JSON.parse(startResponse.publicKeyCredentialCreationOptions);
} else {
    publicKeyOptions = startResponse.publicKeyCredentialCreationOptions;
}
```

### Pattern 2: SimpleWebAuthn Integration
Use SimpleWebAuthn browser library for actual WebAuthn API calls:

```typescript
// Registration
const credential = await window.SimpleWebAuthnBrowser.startRegistration(publicKeyOptions.publicKey);

// Authentication
const assertion = await window.SimpleWebAuthnBrowser.startAuthentication(publicKeyOptions.publicKey);
```

### Pattern 3: Credential Serialization
Credentials must be stringified before sending to server:

```typescript
// CRITICAL: Must stringify credential
const completeRequest: RegistrationCompleteRequest = {
    requestId: startResponse.requestId,
    credential: JSON.stringify(credential)
};
```

### Pattern 4: Error Handling
Proper WebAuthn error handling:

```typescript
catch (error: any) {
    if (error.name === 'InvalidStateError') {
        return { success: false, message: '⚠️ A passkey already exists on this device' };
    } else if (error.name === 'NotAllowedError') {
        return { success: false, message: '❌ Registration was cancelled or timed out' };
    } else if (error.name === 'NotSupportedError') {
        return { success: false, message: '❌ WebAuthn is not supported' };
    }
}
```

## Implementation Steps

### Step 1: Create MCP Server Package

**File**: `mcp-server-webauthn-client/package.json`

```json
{
  "name": "@vmenon25/mcp-server-webauthn-client",
  "version": "1.0.0",
  "description": "MCP server for generating WebAuthn TypeScript web clients",
  "type": "module",
  "main": "dist/index.js",
  "bin": {
    "mcp-server-webauthn-client": "dist/index.js"
  },
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "prepare": "npm run build"
  },
  "keywords": [
    "mcp",
    "webauthn",
    "client-generator",
    "typescript",
    "passkeys"
  ],
  "author": "Vinayak Menon",
  "license": "Apache-2.0",
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.4",
    "handlebars": "^4.7.8"
  },
  "devDependencies": {
    "@types/node": "^22.10.2",
    "typescript": "^5.7.3"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
```

**File**: `mcp-server-webauthn-client/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020"],
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### Step 2: Implement MCP Server

**File**: `mcp-server-webauthn-client/src/index.ts`

```typescript
#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { generateWebClient } from './lib/generator.js';

const server = new Server(
  {
    name: 'webauthn-client-generator',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'generate_web_client',
        description: 'Generate a complete WebAuthn web client using the @vmenon25/mpo-webauthn-client npm library. Connects to existing webauthn-server in docker-compose.',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: "Where to create the web client directory (e.g., './web-client')",
              default: './web-client'
            },
            framework: {
              type: 'string',
              enum: ['vanilla', 'react', 'vue'],
              description: 'Web framework to use',
              default: 'vanilla'
            },
            server_url: {
              type: 'string',
              description: 'URL of the webauthn-server instance',
              default: 'http://localhost:8080'
            },
            client_port: {
              type: 'number',
              description: 'Port for the web client dev server',
              default: 8082
            }
          },
          required: ['project_path'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'generate_web_client':
        return await generateWebClient(args);
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error executing ${name}: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

async function run() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('WebAuthn Client Generator MCP server running on stdio');
}

run().catch(console.error);
```

### Step 3: Implement File Generator

**File**: `mcp-server-webauthn-client/src/lib/generator.ts`

```typescript
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import Handlebars from 'handlebars';

interface GenerateWebClientArgs {
  project_path: string;
  framework?: 'vanilla' | 'react' | 'vue';
  server_url?: string;
  client_port?: number;
}

export async function generateWebClient(args: GenerateWebClientArgs) {
  const {
    project_path,
    framework = 'vanilla',
    server_url = 'http://localhost:8080',
    client_port = 8082
  } = args;

  // Validate framework
  if (!['vanilla', 'react', 'vue'].includes(framework)) {
    throw new Error(`Unsupported framework: ${framework}. Use 'vanilla', 'react', or 'vue'.`);
  }

  // Check if directory exists
  if (existsSync(project_path)) {
    throw new Error(`Directory already exists: ${project_path}. Please choose a different path or remove the existing directory.`);
  }

  const files_created: string[] = [];
  const template_dir = join(dirname(new URL(import.meta.url).pathname), '..', 'templates', framework);

  // Template files to generate
  const template_files = [
    { template: 'package.json.hbs', output: 'package.json' },
    { template: 'webauthn-client.ts.hbs', output: 'src/webauthn-client.ts' },
    { template: 'types.ts.hbs', output: 'src/types.ts' },
    { template: 'server.ts.hbs', output: 'src/server.ts' },
    { template: 'index.html.hbs', output: 'public/index.html' },
    { template: 'webpack.config.js.hbs', output: 'webpack.config.js' },
    { template: 'tsconfig.json.hbs', output: 'tsconfig.json' },
    { template: 'README.md.hbs', output: 'README.md' }
  ];

  // Template variables
  const template_vars = {
    server_url,
    client_port
  };

  try {
    // Create project directory structure
    mkdirSync(project_path, { recursive: true });
    mkdirSync(join(project_path, 'src'), { recursive: true });
    mkdirSync(join(project_path, 'public'), { recursive: true });

    // Generate files from templates
    for (const { template, output } of template_files) {
      const template_path = join(template_dir, template);
      const output_path = join(project_path, output);

      // Read template
      const template_content = readFileSync(template_path, 'utf8');

      // Compile and render template
      const compiled_template = Handlebars.compile(template_content);
      const rendered_content = compiled_template(template_vars);

      // Ensure output directory exists
      mkdirSync(dirname(output_path), { recursive: true });

      // Write file
      writeFileSync(output_path, rendered_content, 'utf8');
      files_created.push(output_path);
    }

    return {
      content: [
        {
          type: 'text',
          text: `✅ Web client generated successfully!\n\nFiles created:\n${files_created.map(f => `  - ${f}`).join('\n')}\n\nNext steps:\n1. cd ${project_path}\n2. npm install\n3. npm run build\n4. npm start\n5. Open http://localhost:${client_port}`,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error generating web client: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
}
```

### Step 4: Create Templates

Templates are based on proven patterns from `web-test-client/`. Use Handlebars syntax for variable substitution: `{{server_url}}`, `{{client_port}}`.

**Reference Implementation**: Copy and adapt files from:
- `web-test-client/package.json` → `templates/vanilla/package.json.hbs`
- `web-test-client/src/webauthn-client.ts` → `templates/vanilla/webauthn-client.ts.hbs`
- `web-test-client/src/types.ts` → `templates/vanilla/types.ts.hbs`
- `web-test-client/src/server.ts` → `templates/vanilla/server.ts.hbs`
- `web-test-client/public/index.html` → `templates/vanilla/index.html.hbs`
- `web-test-client/webpack.config.js` → `templates/vanilla/webpack.config.js.hbs`
- `web-test-client/tsconfig.json` → `templates/vanilla/tsconfig.json.hbs`

**Key Changes in Templates**:
1. Replace hardcoded `http://localhost:8080` with `{{server_url}}`
2. Replace hardcoded port `8082` with `{{client_port}}`
3. Preserve all critical WebAuthn patterns (JSON parsing, credential serialization)

### Step 5: Update .ai-agents.json

Add MCP server section to `.ai-agents.json`:

```json
{
  "mcp_servers": {
    "webauthn_client_generator": {
      "package": "@vmenon25/mcp-server-webauthn-client",
      "description": "MCP server for generating WebAuthn web clients that connect to existing webauthn-server instances",
      "installation": "npm install -g @vmenon25/mcp-server-webauthn-client",
      "tools": {
        "generate_web_client": {
          "description": "Generate complete web client with TypeScript, Express server, and WebAuthn integration",
          "frameworks_supported": ["vanilla", "react", "vue"],
          "critical_features": [
            "Preserves JSON parsing patterns for WebAuthn API",
            "Includes SimpleWebAuthn browser library integration",
            "Proper credential serialization",
            "Comprehensive error handling"
          ]
        }
      },
      "example_usage": {
        "user_prompt": "Create a web client to test my webauthn-server",
        "ai_agent_action": "Calls generate_web_client tool with appropriate parameters",
        "result": "Complete working web client generated in user's project"
      }
    }
  }
}
```

## Example AI Agent Conversation

### Scenario: User in Another Project

**User**: "I have webauthn-server running in docker-compose on port 8080. Create a web client to test registration and authentication."

**AI Agent** (Claude):
```
I can help you generate a web client! I'll use the WebAuthn client generator MCP tool.

[Calls: generate_web_client({
  project_path: "./web-client",
  framework: "vanilla",
  server_url: "http://localhost:8080",
  client_port: 8082
})]

✅ Web client generated successfully!

Files created:
  - ./web-client/package.json
  - ./web-client/src/webauthn-client.ts
  - ./web-client/src/types.ts
  - ./web-client/src/server.ts
  - ./web-client/public/index.html
  - ./web-client/webpack.config.js
  - ./web-client/tsconfig.json
  - ./web-client/README.md

Next steps:
1. cd web-client
2. npm install
3. npm run build
4. npm start
5. Open http://localhost:8082

The client uses the published @vmenon25/mpo-webauthn-client library and includes all critical WebAuthn integration patterns.
```

## Testing the MCP Server

### Local Testing During Development

1. **Build the MCP server**:
   ```bash
   cd mcp-server-webauthn-client
   npm install
   npm run build
   ```

2. **Test tool directly** (create test script):
   ```typescript
   // test.ts
   import { generateWebClient } from './dist/lib/generator.js';

   generateWebClient({
     project_path: './test-output',
     framework: 'vanilla',
     server_url: 'http://localhost:8080',
     client_port: 8082
   }).then(result => {
     console.log(result);
   });
   ```

3. **Test with Claude Code**:
   - Add to `claude_config.json`:
   ```json
   {
     "mcpServers": {
       "webauthn-client-generator": {
         "command": "node",
         "args": ["mcp-server-webauthn-client/dist/index.js"],
         "cwd": "/Users/vinayakmenon/mpo-api-authn-server"
       }
     }
   }
   ```
   - Ask Claude Code to test the tool

4. **Verify generated client works**:
   ```bash
   cd test-output
   npm install
   npm run build
   npm start
   # Open http://localhost:8082 and test registration/authentication
   ```

## Publishing Strategy

### Phase 1: Internal Testing
- ✅ Test locally with Claude Code
- ✅ Verify generated clients work correctly
- ✅ Test all framework variants (vanilla, react, vue)

### Phase 2: GitHub Release
- Publish to GitHub repository
- Create release with installation instructions
- Update main project README

### Phase 3: npm Publishing (Optional)
- Publish to npm as `@vmenon25/mcp-server-webauthn-client`
- AI agents can auto-discover via npm registry
- Users can install globally: `npm install -g @vmenon25/mcp-server-webauthn-client`

## Future Enhancements (Out of Scope for V1)

### React Framework Support
- Generate React hooks for WebAuthn (`useWebAuthn`, `useRegistration`, `useAuthentication`)
- React component examples
- Context provider for WebAuthn client

### Vue Framework Support
- Generate Vue composables
- Vue component examples
- Pinia store for WebAuthn state

### Additional Tools
- `validate_client` - Validate generated client configuration
- `test_connection` - Test connection to webauthn-server
- `troubleshoot` - Diagnose common issues (CORS, connection, etc.)

### Advanced Features
- Custom styling options
- UI framework selection (Material-UI, Tailwind, etc.)
- Multiple authentication flows (usernameless, conditional UI)
- Internationalization support

## Success Criteria

### V1 Release Must Have:
- ✅ Working MCP server with `generate_web_client` tool
- ✅ Vanilla TypeScript framework support
- ✅ All critical WebAuthn patterns preserved
- ✅ Generated client successfully connects to webauthn-server
- ✅ Documentation for AI agents in .ai-agents.json
- ✅ README with usage examples
- ✅ Tested with Claude Code

### Nice to Have:
- React framework support
- Vue framework support
- Published to npm
- Additional validation tools

## References

### Existing Implementation Files
- `web-test-client/` - Reference implementation for templates
- `web-test-client/src/webauthn-client.ts` - Critical WebAuthn patterns
- `dev-tools-mcp-server.js` - Example MCP server implementation
- `docs/setup/library-usage.md` - Client library documentation
- `.ai-agents.json` - AI agent configuration

### External Documentation
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [@modelcontextprotocol/sdk](https://www.npmjs.com/package/@modelcontextprotocol/sdk) - MCP SDK documentation
- [SimpleWebAuthn](https://simplewebauthn.dev/) - WebAuthn library documentation
- [WebAuthn Guide](https://webauthn.guide/) - WebAuthn specification

## Implementation Timeline

### Phase 1: MCP Server Setup (Day 1)
- Create package structure
- Implement MCP server with tool definition
- Set up TypeScript build

### Phase 2: Template Creation (Day 2-3)
- Create vanilla TypeScript templates
- Copy and adapt from web-test-client
- Implement Handlebars variable substitution

### Phase 3: Generator Implementation (Day 3-4)
- Implement file generation logic
- Add error handling and validation
- Test file generation

### Phase 4: Testing & Documentation (Day 4-5)
- Test with Claude Code
- Update .ai-agents.json
- Create README and usage examples
- Verify generated client works end-to-end

### Phase 5: Polish & Release (Day 5)
- Code cleanup
- Final testing
- Documentation review
- Initial release

**Total Estimated Time**: 5-7 days
