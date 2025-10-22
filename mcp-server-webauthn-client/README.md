# WebAuthn Client Generator - MCP Server

A Model Context Protocol (MCP) server that helps AI agents automatically generate complete WebAuthn web clients for testing authentication.

## Overview

This MCP server provides AI agents with the ability to generate fully-functional WebAuthn web clients that connect to webauthn-server instances.

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
- ✅ **Complete Docker stack** (PostgreSQL + Redis + WebAuthn Server)
- ✅ **Secure password generation** using crypto.randomBytes
- ✅ **Docker Compose secrets** (no hardcoded credentials)
- ✅ **Playwright E2E tests** with Chromium virtual authenticator
- ✅ **Auto-initialized database** schema on first startup

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
npm install  # Automatically builds dist/ via prepare script
```

**Note**: The `dist/` directory is automatically built during `npm install` via the `prepare` script in `package.json`. For manual builds:
```bash
npm run build  # Build once
npm run dev    # Watch mode
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

# Custom server URL and forward port
npx -y @vmenon25/mcp-server-webauthn-client \
  --server http://localhost:9000 \
  --forward-port 3000

# Production server with custom relying party
npx -y @vmenon25/mcp-server-webauthn-client \
  --server https://auth.example.com

# Avoid port conflicts with existing infrastructure
npx -y @vmenon25/mcp-server-webauthn-client \
  --postgres-host-port 5433 \
  --redis-host-port 6380 \
  --gateway-host-port 8001

# Show help (lists all available options)
npx -y @vmenon25/mcp-server-webauthn-client --help
```

**CLI Options:**

**Core Options:**
- `-p, --path <path>` - Directory to create web client (default: `./web-client`)
- `-s, --server <url>` - Envoy Gateway URL (default: `http://localhost:8000`)
- `-P, --forward-port <port>` - Client dev server port (default: `8082`)
- `-f, --framework <name>` - Framework: `vanilla`|`react`|`vue` (default: `vanilla`)
- `-h, --help` - Show help message with all options

**Infrastructure Port Customization:**
- `--postgres-host-port <port>` - PostgreSQL host port (default: `5432`)
- `--redis-host-port <port>` - Redis host port (default: `6379`)
- `--gateway-host-port <port>` - Envoy Gateway host port (default: `8000`)
- `--gateway-admin-port <port>` - Envoy admin host port (default: `9901`)

**Jaeger Tracing Port Customization:**
- `--jaeger-ui-port <port>` - Jaeger UI port (default: `16686`)
- `--jaeger-collector-http-port <port>` - Jaeger collector HTTP (default: `14268`)
- `--jaeger-collector-grpc-port <port>` - Jaeger collector gRPC (default: `14250`)
- `--jaeger-otlp-grpc-port <port>` - Jaeger OTLP gRPC (default: `4317`)
- `--jaeger-otlp-http-port <port>` - Jaeger OTLP HTTP (default: `4318`)
- `--jaeger-agent-compact-port <port>` - Jaeger agent compact thrift UDP (default: `6831`)
- `--jaeger-agent-binary-port <port>` - Jaeger agent binary thrift UDP (default: `6832`)
- `--jaeger-agent-config-port <port>` - Jaeger agent config HTTP (default: `5778`)

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
      "command": "npx",
      "args": [
        "-y",
        "@vmenon25/mcp-server-webauthn-client@latest"
      ]
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
  // Required
  project_path: string;                    // Where to create web client (e.g., './web-client')

  // Core Configuration
  framework?: 'vanilla' | 'react' | 'vue'; // Default: 'vanilla'
  server_url?: string;                     // Envoy Gateway URL (default: 'http://localhost:8000')
  forward_port?: number;                   // Client dev server port (default: 8082)

  // WebAuthn Configuration
  relying_party_id?: string;               // WebAuthn RP ID (default: 'localhost')
  relying_party_name?: string;             // WebAuthn RP name (default: 'WebAuthn Demo')

  // Infrastructure Port Customization (to avoid conflicts)
  postgres_host_port?: number;             // PostgreSQL host port (default: 5432)
  redis_host_port?: number;                // Redis host port (default: 6379)
  gateway_host_port?: number;              // Envoy Gateway host port (default: 8000)
  gateway_admin_port?: number;             // Envoy admin host port (default: 9901)

  // Jaeger Tracing Port Customization
  jaeger_ui_port?: number;                 // Jaeger UI port (default: 16686)
  jaeger_collector_http_port?: number;     // Jaeger collector HTTP (default: 14268)
  jaeger_collector_grpc_port?: number;     // Jaeger collector gRPC (default: 14250)
  jaeger_otlp_grpc_port?: number;          // Jaeger OTLP gRPC (default: 4317)
  jaeger_otlp_http_port?: number;          // Jaeger OTLP HTTP (default: 4318)
  jaeger_agent_compact_port?: number;      // Jaeger agent compact thrift UDP (default: 6831)
  jaeger_agent_binary_port?: number;       // Jaeger agent binary thrift UDP (default: 6832)
  jaeger_agent_config_port?: number;       // Jaeger agent config HTTP (default: 5778)
}
```

## Generated Web Client Structure

```
web-client/
├── .gitignore                   # 🆕 Comprehensive gitignore for Node/TypeScript
├── package.json                 # All required dependencies
├── src/
│   ├── index.ts                # Entry point
│   ├── webauthn-client.ts      # Complete WebAuthn integration
│   ├── types.ts                # TypeScript type definitions
│   └── server.ts               # Express development server
├── public/
│   └── index.html              # Test UI
├── docker/                      # 🆕 Complete Docker stack
│   ├── docker-compose.yml      # PostgreSQL + Redis + WebAuthn Server
│   ├── init-db.sql             # Database schema initialization
│   ├── setup-secrets.sh        # Secret verification script
│   └── secrets/                # 🔐 Auto-generated passwords (gitignored)
│       ├── .gitignore          # Prevents accidental commits
│       ├── postgres_password   # Auto-generated 32-char password
│       └── redis_password      # Auto-generated 32-char password
├── tests/                       # 🆕 Playwright E2E tests
│   └── webauthn.spec.js        # Registration + Authentication tests
├── playwright.config.js         # Playwright configuration
├── global-setup.js              # Test setup (starts client server)
├── global-teardown.js           # Test cleanup
├── webpack.config.js            # Build configuration
├── tsconfig.json                # TypeScript configuration
├── tsconfig.build.json          # Build-specific TypeScript config
└── README.md                    # Usage instructions + security docs
```

## Example Scenarios

### Scenario 1: Basic Web Client Generation

**User**: "Generate a web client for my WebAuthn server"

**MCP Tool Call**:
```json
{
  "project_path": "./web-client",
  "framework": "vanilla",
  "server_url": "http://localhost:8000",
  "forward_port": 8082
}
```

### Scenario 2: Custom Port Configuration

**User**: "Create a web client on port 3000 that connects to my server on port 9000"

**MCP Tool Call**:
```json
{
  "project_path": "./auth-client",
  "server_url": "http://localhost:9000",
  "forward_port": 3000
}
```

### Scenario 3: Production Server with Custom Relying Party

**User**: "Generate a web client that connects to my production WebAuthn server at https://auth.example.com with relying party ID 'example.com'"

**MCP Tool Call**:
```json
{
  "project_path": "./production-client",
  "server_url": "https://auth.example.com",
  "forward_port": 8082,
  "relying_party_id": "example.com",
  "relying_party_name": "Example Corp Authentication"
}
```

### Scenario 4: Avoiding Port Conflicts with Existing Services

**User**: "I already have PostgreSQL on 5432 and Redis on 6379. Generate a client that uses different ports."

**MCP Tool Call**:
```json
{
  "project_path": "./web-client",
  "server_url": "http://localhost:8000",
  "forward_port": 8082,
  "postgres_host_port": 5433,
  "redis_host_port": 6380,
  "gateway_host_port": 8001,
  "jaeger_ui_port": 16687
}
```

### Scenario 5: Complete Custom Port Configuration for Isolated Testing

**User**: "Create a completely isolated test environment with no port conflicts"

**MCP Tool Call**:
```json
{
  "project_path": "./isolated-test-client",
  "server_url": "http://localhost:9000",
  "forward_port": 9082,
  "postgres_host_port": 15432,
  "redis_host_port": 16379,
  "gateway_host_port": 9000,
  "gateway_admin_port": 9902,
  "jaeger_ui_port": 26686,
  "jaeger_otlp_grpc_port": 14317,
  "jaeger_otlp_http_port": 14318
}
```

## Complete Workflow (Docker + Tests)

### What Gets Generated

When you call `generate_web_client`, the MCP server:

1. **Creates complete directory structure** with all files
2. **Generates unique secure passwords** using crypto.randomBytes(32)
3. **Writes passwords to docker/secrets/** (auto-gitignored)
4. **Configures docker-compose.yml** to use Docker secrets (no hardcoded passwords)
5. **Sets up Playwright E2E tests** with virtual authenticator

### Recommended Usage Flow for AI Agents

```bash
# 1. Generate the client (MCP does this)
# Creates: web-client/ with docker/, tests/, src/, etc.

# 2. Start Docker stack FIRST (before running client)
cd web-client/docker
docker compose up -d
# This starts: PostgreSQL + Redis + WebAuthn Server
# Database schema auto-initializes from init-db.sql

# 3. Install and build client
cd ..
npm install
npm run build

# 4. Start client server (in background)
npm start &
# Client runs on port 8082

# 5. Run E2E tests to validate setup
npm test
# Tests: Registration + Authentication flows
# Uses Chromium virtual authenticator (no real device needed)

# 6. If tests pass ✅, client is ready
# Open http://localhost:8082 to use interactively
```

### Security Notes for AI Agents

**Docker Secrets Implementation:**
- Passwords are auto-generated using Node.js `crypto.randomBytes(32)`
- Each generated client gets **unique passwords**
- Secrets stored in `docker/secrets/` (gitignored)
- docker-compose.yml uses Docker secrets feature (read-only mounts at `/run/secrets/`)
- **No hardcoded passwords** in any generated files

**Important**: Always run `docker compose up -d` BEFORE running tests or client server.

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

## Security

This MCP server implements comprehensive security controls to prevent path traversal and other file-system attacks. See [SECURITY.md](SECURITY.md) for:
- Path traversal prevention measures
- Attack vectors mitigated
- Security testing procedures
- Vulnerability disclosure policy

## Links

- **Main Project**: [mpo-api-authn-server](https://github.com/hitoshura25/mpo-api-authn-server)
- **Security Documentation**: [SECURITY.md](SECURITY.md)
- **Publishing Guide**: [PUBLISHING.md](PUBLISHING.md)
- **Template Fixes**: [TEMPLATE-FIXES.md](TEMPLATE-FIXES.md)
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
