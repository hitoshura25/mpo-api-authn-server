# WebAuthn Client Generator - MCP Server

A Model Context Protocol (MCP) server that helps AI agents automatically generate complete WebAuthn web clients for testing authentication.

## Overview

This MCP server provides AI agents with the ability to generate fully-functional WebAuthn web clients that connect to existing webauthn-server instances. Perfect for users who already have the server running in docker-compose and need a web client to test registration and authentication flows.

## What is MCP?

Model Context Protocol (MCP) is a standard protocol that allows AI agents like Claude to interact with external tools and services. MCP servers expose tools that AI agents can discover and use automatically to help users accomplish tasks.

## Features

### Single Focused Tool: `generate_web_client`

Generates a complete, production-ready web client with:

- ✅ **TypeScript WebAuthn client** with all critical integration patterns
- ✅ **Express development server** (configurable port)
- ✅ **Complete build toolchain** (Webpack, Babel, TypeScript)
- ✅ **Test UI** with registration and authentication flows
- ✅ **Proper error handling** for WebAuthn-specific errors
- ✅ **Type-safe** implementation using published npm client library

### Critical WebAuthn Patterns Preserved

The generated code automatically includes all critical patterns documented in the main project:

1. **JSON Parsing**: `JSON.parse(startResponse.publicKeyCredentialCreationOptions)`
2. **SimpleWebAuthn Integration**: `await startRegistration(publicKeyOptions.publicKey)`
3. **Credential Serialization**: `JSON.stringify(credential)`
4. **Comprehensive Error Handling**: InvalidStateError, NotAllowedError, NotSupportedError

### Supported Frameworks

- **Vanilla TypeScript** (default) - Currently implemented
- **React** - Planned for future release
- **Vue** - Planned for future release

## Installation

### Local Installation (Development)

```bash
cd mcp-server-webauthn-client
npm install
npm run build
```

### Global Installation (For AI Agent Discovery)

```bash
npm install -g @vmenon25/mcp-server-webauthn-client
```

## Usage

This package can be used in two ways:

1. **MCP Mode** - For MCP-compatible AI agents (Claude Code, Continue.dev, Cline) - **0 token cost**
2. **CLI Mode** - For non-MCP agents (Cursor, Aider, Windsurf) or direct usage - **~1500 token discovery cost**

### CLI Mode (Recommended for Non-MCP Agents)

The easiest way to use the client generator without MCP setup:

```bash
# Basic usage (generates in ./web-client)
npx -y @vmenon25/mcp-server-webauthn-client

# Custom path
npx -y @vmenon25/mcp-server-webauthn-client --path ./auth-client

# Custom server URL and port
npx -y @vmenon25/mcp-server-webauthn-client \
  --server http://localhost:9000 \
  --port 3000

# Production server
npx -y @vmenon25/mcp-server-webauthn-client \
  --server https://auth.example.com

# Show help
npx -y @vmenon25/mcp-server-webauthn-client --help
```

**CLI Options:**
- `-p, --path <path>` - Directory to create web client (default: `./web-client`)
- `-s, --server <url>` - WebAuthn server URL (default: `http://localhost:8080`)
- `-P, --port <port>` - Client dev server port (default: `8082`)
- `-f, --framework <name>` - Framework: `vanilla`|`react`|`vue` (default: `vanilla`)
- `-h, --help` - Show help message

**Token Cost for Non-MCP Agents:**
- Discovery: ~1500 tokens (one-time read of `.ai-agents.json`)
- Execution: 0 tokens (runs locally)
- **Total**: ~1500 tokens vs. 4500-10000 tokens for manual guidance

### MCP Mode (For Claude Code & Compatible Agents)

1. **Add to your project's `claude_config.json`**:

```json
{
  "mcpServers": {
    "webauthn-client-generator": {
      "command": "node",
      "args": ["/absolute/path/to/mcp-server-webauthn-client/dist/index.js"]
    }
  }
}
```

2. **Use naturally in conversation**:

```
You: "I have webauthn-server running on port 8080. Create a web client to test it."

Claude: I'll generate a complete web client for you using the WebAuthn client generator.

[Claude calls the generate_web_client tool]

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
```

### Direct MCP Tool Call

The tool accepts these parameters:

```typescript
{
  project_path: string;      // Where to create web client (e.g., './web-client')
  framework?: string;        // 'vanilla', 'react', or 'vue' (default: 'vanilla')
  server_url?: string;       // WebAuthn server URL (default: 'http://localhost:8080')
  client_port?: number;      // Client dev server port (default: 8082)
}
```

## Generated Web Client Structure

```
web-client/
├── package.json                 # All required dependencies
├── src/
│   ├── index.ts                # Entry point
│   ├── webauthn-client.ts      # Complete WebAuthn integration
│   ├── types.ts                # TypeScript type definitions
│   └── server.ts               # Express development server
├── public/
│   └── index.html              # Test UI
├── webpack.config.js            # Build configuration
├── tsconfig.json                # TypeScript configuration
├── tsconfig.build.json          # Build-specific TypeScript config
└── README.md                    # Usage instructions
```

## Example Scenarios

### Scenario 1: Basic Web Client Generation

**User**: "Generate a web client for my WebAuthn server"

**MCP Tool Call**:
```json
{
  "project_path": "./web-client",
  "framework": "vanilla",
  "server_url": "http://localhost:8080",
  "client_port": 8082
}
```

### Scenario 2: Custom Port Configuration

**User**: "Create a web client on port 3000 that connects to my server on port 9000"

**MCP Tool Call**:
```json
{
  "project_path": "./auth-client",
  "server_url": "http://localhost:9000",
  "client_port": 3000
}
```

### Scenario 3: Production Server Integration

**User**: "Generate a web client that connects to my production WebAuthn server at https://auth.example.com"

**MCP Tool Call**:
```json
{
  "project_path": "./production-client",
  "server_url": "https://auth.example.com",
  "client_port": 8082
}
```

## Benefits Over Manual Setup

### For Users
- ⚡ **Zero configuration** - Works immediately after generation
- 🔒 **Best practices** - All critical patterns automatically included
- 📦 **Complete toolchain** - Webpack, TypeScript, Babel pre-configured
- 🎯 **Type-safe** - Full TypeScript support with published client library
- 🚀 **Production-ready** - Express server with proper error handling

### For AI Agents
- 🤖 **Reliable** - Consistent code generation every time
- 📋 **Documented** - Clear tool interface with examples
- 🔄 **Repeatable** - Same inputs always produce same output
- ✅ **Validated** - Generated code follows proven patterns

## Development

### Project Structure

```
mcp-server-webauthn-client/
├── src/
│   ├── index.ts                # Main MCP server
│   ├── lib/
│   │   └── generator.ts        # File generation logic
│   └── templates/
│       └── vanilla/            # Vanilla TypeScript templates
│           ├── package.json.hbs
│           ├── webauthn-client.ts.hbs
│           ├── types.ts.hbs
│           ├── server.ts.hbs
│           ├── index.html.hbs
│           └── ...
├── dist/                       # Compiled output
├── package.json
├── tsconfig.json
└── README.md
```

### Building

```bash
npm run build       # Build once
npm run dev         # Watch mode
```

### Testing

1. **Build the MCP server**:
   ```bash
   npm run build
   ```

2. **Test tool execution** (create `test.ts`):
   ```typescript
   import { generateWebClient } from './dist/lib/generator.js';

   generateWebClient({
     project_path: './test-output',
     framework: 'vanilla',
     server_url: 'http://localhost:8080',
     client_port: 8082
   }).then(result => console.log(result));
   ```

3. **Verify generated client**:
   ```bash
   cd test-output
   npm install
   npm run build
   npm start
   # Open http://localhost:8082
   ```

## Troubleshooting

### MCP Server Not Discovered

**Issue**: Claude Code doesn't see the MCP server

**Solution**:
1. Check `claude_config.json` is in project root
2. Verify absolute path to `dist/index.js`
3. Ensure MCP server is built: `npm run build`
4. Restart Claude Code

### Generation Fails

**Issue**: Tool reports error during generation

**Common Causes**:
- Directory already exists at `project_path`
- Invalid framework name
- Template files missing

**Solution**:
- Choose different `project_path` or remove existing directory
- Use 'vanilla', 'react', or 'vue' for framework
- Rebuild MCP server: `npm run build`

### Generated Client Won't Build

**Issue**: `npm run build` fails in generated client

**Solution**:
1. Ensure all dependencies installed: `npm install`
2. Check Node.js version: `node --version` (need 18+)
3. Verify TypeScript version: `npx tsc --version`
4. Check for port conflicts

## Contributing

This MCP server is part of the [mpo-api-authn-server](https://github.com/hitoshura25/mpo-api-authn-server) project.

### Adding New Framework Support

1. Create new template directory: `src/templates/{framework}/`
2. Copy vanilla templates as starting point
3. Adapt for framework-specific patterns
4. Test generation and client build
5. Update documentation

### Improving Templates

Template files use Handlebars syntax:
- `{{server_url}}` - WebAuthn server URL
- `{{client_port}}` - Client dev server port

Ensure all critical WebAuthn patterns are preserved!

## License

Apache-2.0

## Publishing

The MCP server is automatically published to npm when changes are pushed to the `main` branch. See [PUBLISHING.md](PUBLISHING.md) for details on the automated publishing workflow.

**Published Package**: [@vmenon25/mcp-server-webauthn-client](https://www.npmjs.com/package/@vmenon25/mcp-server-webauthn-client)

## Links

- **Main Project**: [mpo-api-authn-server](https://github.com/hitoshura25/mpo-api-authn-server)
- **Publishing Guide**: [PUBLISHING.md](PUBLISHING.md)
- **Token Cost Analysis**: [TOKEN-COST-ANALYSIS.md](TOKEN-COST-ANALYSIS.md)
- **Multi-Language Integration**: [HYBRID-INTEGRATION-STRATEGIES.md](HYBRID-INTEGRATION-STRATEGIES.md)
- **Implementation Plan**: [docs/improvements/in-progress/mcp-web-client-generator-implementation.md](../docs/improvements/in-progress/mcp-web-client-generator-implementation.md)
- **WebAuthn Client Library**: [@vmenon25/mpo-webauthn-client](https://www.npmjs.com/package/@vmenon25/mpo-webauthn-client)
- **Model Context Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)

## Support

For issues or questions:
- Open an issue in the [main repository](https://github.com/hitoshura25/mpo-api-authn-server/issues)
- Check the [implementation documentation](../docs/improvements/in-progress/mcp-web-client-generator-implementation.md)
- Review the [AI agent configuration](.ai-agents.json) for usage examples
