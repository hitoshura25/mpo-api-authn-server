# WebAuthn Client Generator - MCP Server

A Model Context Protocol (MCP) server that helps AI agents automatically generate complete WebAuthn web clients for testing authentication.

## Overview

This MCP server provides AI agents with the ability to generate fully-functional WebAuthn web clients that connect to webauthn-server instances.

## What Gets Generated

When you use this tool, you get a **complete, zero-trust WebAuthn stack**:

- ✅ **Envoy Gateway** - Entry point with JWT authentication for protected routes
- ✅ **WebAuthn Server** - FIDO2/Passkey authentication + JWT issuer
- ✅ **JWKS Endpoint** (`/.well-known/jwks.json`) - Public key distribution for JWT verification
- ✅ **Example Service** - Python FastAPI demo showing JWT-protected endpoints
- ✅ **PostgreSQL 15** - Credential storage with auto-schema initialization
- ✅ **Redis 7** - Session management
- ✅ **Jaeger** - Distributed tracing (optional)
- ✅ **Docker Compose** - Complete orchestration with secrets management
- ✅ **Playwright E2E Tests** - Automated testing with Chromium virtual authenticator
- ✅ **TypeScript Web Client** - Complete build toolchain and dev server

**Key Feature**: All services communicate through Envoy Gateway using JWT authentication verified via the JWKS endpoint, demonstrating a zero-trust architecture.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Generated Stack                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Web Client (TypeScript)                                         │
│  └─ http://localhost:8082                                        │
│         │                                                         │
│         │ WebAuthn Registration/Authentication                   │
│         ▼                                                         │
│  ┌────────────────────────────────────────┐                      │
│  │    Envoy Gateway (port 8000)           │                      │
│  │  ┌──────────────────────────────────┐  │                      │
│  │  │ Public Routes (no JWT required)   │  │                      │
│  │  │  ✓ /register/*                    │  │                      │
│  │  │  ✓ /authenticate/*                │  │                      │
│  │  │  ✓ /.well-known/jwks.json         │  │                      │
│  │  │  ✓ /health                        │  │                      │
│  │  └──────────────────────────────────┘  │                      │
│  │  ┌──────────────────────────────────┐  │                      │
│  │  │ Protected Routes (JWT required)   │  │                      │
│  │  │  ✓ /api/* → JWT verification via  │  │                      │
│  │  │    JWKS endpoint                  │  │                      │
│  │  └──────────────────────────────────┘  │                      │
│  └─────┬──────────────┬─────────────────┘                        │
│        │              │                                           │
│        │              │ mTLS (Phase 2)                           │
│        ▼              ▼                                           │
│  ┌──────────┐   ┌─────────────────┐                             │
│  │ WebAuthn │   │ Example Service │                             │
│  │  Server  │   │  (Python/FastAPI)│                            │
│  │ :8080    │   │   :9000         │                             │
│  │          │   │                  │                             │
│  │ • Issues │   │ • Validates JWT  │                             │
│  │   JWTs   │   │ • Protected      │                             │
│  │ • JWKS   │   │   /api/example/* │                             │
│  │   endpoint│   │   endpoints      │                             │
│  └────┬─────┘   └─────────────────┘                             │
│       │                                                           │
│       ├─ PostgreSQL 15 (credentials)                             │
│       ├─ Redis 7 (sessions)                                      │
│       └─ Jaeger (distributed tracing)                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

JWT Authentication Flow:
1. User authenticates via WebAuthn → Server issues JWT
2. Client includes JWT in Authorization header for /api/* requests
3. Envoy Gateway fetches public key from /.well-known/jwks.json
4. Envoy verifies JWT signature using JWKS before forwarding request
5. Protected service receives verified request with JWT
```

## What is MCP?

Model Context Protocol (MCP) is a standard protocol that allows AI agents like Claude to interact with external tools and services. MCP servers expose tools that AI agents can discover and use automatically to help users accomplish tasks.

## Features

### Single Focused Tool: `generate_web_client`

Generates a complete web client with:

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

#### Discovery File for Non-MCP Agents

**For coding agents without native MCP support** (Cursor, Aider, Windsurf, etc.), this tool can be discovered via the project's `.ai-agents.json` file:

**Discovery URL**: https://raw.githubusercontent.com/hitoshura25/mpo-api-authn-server/main/.ai-agents.json

**How Non-MCP Agents Discover This Tool:**

1. **Agent reads `.ai-agents.json`** from the project root (~1500 tokens one-time cost)
2. **Finds `mcp_servers.webauthn_client_generator` section** with complete usage documentation
3. **Suggests CLI command** to user based on their requirements
4. **User runs command** - tool executes locally (0 additional tokens)

**Example Discovery Flow:**

```
User: "I need to test my WebAuthn server with a web client"

Agent (internal):
1. Reads .ai-agents.json from project
2. Finds webauthn-client-generator tool
3. Extracts CLI usage examples

Agent (response):
"I found a WebAuthn client generator tool. Run this command to generate a complete test client:

npx -y @vmenon25/mcp-server-webauthn-client --path ./web-client

This will generate:
• Complete TypeScript web client
• Docker stack (Envoy Gateway + WebAuthn Server + PostgreSQL + Redis)
• E2E Playwright tests
• Zero-trust architecture with JWT authentication

After generation:
1. cd web-client/docker && docker compose up -d
2. cd .. && npm install && npm run build && npm start
3. npm test  # Run E2E tests
4. Open http://localhost:8082
```

**What's in `.ai-agents.json`:**
- Complete tool description and usage examples
- All CLI options with defaults
- Critical integration patterns (JSON parsing, credential serialization)
- Docker compose configuration examples
- Common pitfalls and solutions
- Token cost analysis

**Benefits for Non-MCP Agents:**
- ✅ **Low token cost**: ~1500 tokens vs. 4500-10000 for manual guidance
- ✅ **Accurate instructions**: Based on official documentation
- ✅ **Complete examples**: Working CLI commands ready to use
- ✅ **No manual configuration**: Single command generates everything

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

## Zero-Trust Architecture Explained

The generated stack implements a **zero-trust architecture** using industry-standard patterns:

### 1. Envoy Gateway as Entry Point

**All traffic flows through Envoy Gateway** - no direct access to backend services:
- **Public Routes** (no authentication required):
  - `/register/*` - WebAuthn registration endpoints
  - `/authenticate/*` - WebAuthn authentication endpoints
  - `/.well-known/jwks.json` - Public key distribution (JWKS)
  - `/health` - Health check endpoint

- **Protected Routes** (JWT authentication required):
  - `/api/*` - All application endpoints require valid JWT

### 2. JWKS Endpoint for JWT Verification

The **JWKS (JSON Web Key Set) endpoint** (`/.well-known/jwks.json`) provides public keys for JWT verification:

```json
{
  "keys": [{
    "kty": "RSA",
    "use": "sig",
    "kid": "unique-key-id",
    "alg": "RS256",
    "n": "base64url-encoded-modulus",
    "e": "base64url-encoded-exponent"
  }]
}
```

**How Envoy uses JWKS:**
1. Envoy Gateway fetches JWKS on startup and caches for 5 minutes
2. When request comes to `/api/*`, Envoy extracts JWT from Authorization header
3. Envoy verifies JWT signature using public key from JWKS
4. If valid, request forwards to backend service; if invalid, returns 401 Unauthorized

**Benefits:**
- ✅ JWT verification happens at gateway (zero-trust perimeter)
- ✅ Backend services receive only verified requests
- ✅ Key rotation supported via JWKS updates
- ✅ No shared secrets between services

### 3. Example Service - Protected Endpoint Demo

The **Example Service** (Python FastAPI) demonstrates a protected microservice:

```python
# Located at: web-client/example-service/main.py

@app.get("/api/example/data")
async def get_data():
    # This endpoint is protected by Envoy Gateway
    # JWT has already been verified before request reaches here
    return {"message": "Protected data", "timestamp": "..."}
```

**Key Points:**
- Runs on port 9000 (not directly accessible from outside)
- All requests come through Envoy Gateway
- JWT already verified by Envoy (zero-trust model)
- Service can extract user info from JWT claims

**How to add your own protected services:**
1. Add service definition to `docker/docker-compose.yml`
2. Add route to `docker/envoy-gateway.yaml` under protected routes
3. Service receives only authenticated requests

### 4. mTLS Between Services (Phase 2)

The stack includes **mTLS (mutual TLS) configuration** between Envoy Gateway and backend services:

```yaml
# envoy-gateway.yaml
transport_socket:
  name: envoy.transport_sockets.tls
  typed_config:
    common_tls_context:
      tls_certificates:  # Gateway's client cert
      validation_context:  # Validates service certs
```

**Benefits:**
- ✅ Encrypted communication between services
- ✅ Mutual authentication (both sides verify identity)
- ✅ Protection against man-in-the-middle attacks
- ✅ Zero-trust within the service mesh

### Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│ Zero-Trust Perimeter                                         │
│                                                               │
│  Envoy Gateway                                               │
│  ├─ Public Routes → WebAuthn Server (no JWT)                │
│  ├─ JWKS Endpoint → Public key distribution                  │
│  └─ Protected Routes → JWT verification + mTLS               │
│                                                               │
│  Backend Services (not directly accessible)                  │
│  ├─ WebAuthn Server (issues JWTs)                           │
│  ├─ Example Service (validates via gateway)                  │
│  ├─ PostgreSQL (credentials)                                 │
│  └─ Redis (sessions)                                         │
└─────────────────────────────────────────────────────────────┘

Security Principles:
• Never trust, always verify (even internal traffic)
• JWT verification at perimeter (Envoy Gateway)
• Public key cryptography (JWKS) for verification
• mTLS for inter-service communication
• Secrets management via Docker secrets
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

# 2. ⚠️ CRITICAL: Start Docker stack FIRST (before running client)
cd web-client/docker
docker compose up -d

# This starts the complete zero-trust stack:
#   - Envoy Gateway (port 8000) - Entry point with JWT verification
#   - WebAuthn Server (port 8080) - FIDO2 auth + JWT issuer
#   - Example Service (port 9000) - Protected endpoints demo
#   - PostgreSQL 15 (port 5432) - Credential storage
#   - Redis 7 (port 6379) - Session management
#   - Jaeger (port 16686) - Distributed tracing UI
#
# Database schema auto-initializes from init-db.sql
# Docker secrets (passwords) are auto-generated and gitignored

# Wait for services to be healthy (check with: docker compose ps)

# 3. Install and build client
cd ..
npm install
npm run build

# 4. Start client server (in background)
npm start &
# Client runs on port 8082 (configurable via --forward-port)
# Connects to Envoy Gateway at http://localhost:8000

# 5. Run E2E tests to validate complete stack
npm test
# Tests full flow:
#   ✓ WebAuthn Registration through Envoy Gateway
#   ✓ WebAuthn Authentication + JWT issuance
#   ✓ Protected endpoint access (/api/*) with JWT
#   ✓ Public endpoint access (no JWT required)
#   ✓ JWKS endpoint functionality
# Uses Chromium virtual authenticator (no real device needed)

# 6. If tests pass ✅, stack is ready for use
# Open http://localhost:8082 to use interactively
# View Jaeger traces at http://localhost:16686
# Check Envoy admin at http://localhost:9901
```

### Important: Docker Stack Must Run First

**Why this order matters:**
1. **WebAuthn Server must be running** - Client needs authentication endpoints
2. **Envoy Gateway must be running** - All requests route through gateway
3. **JWKS endpoint must be available** - JWT verification depends on it
4. **Database must initialize** - Schema creation happens on first startup

**Common mistake**: Running `npm start` before `docker compose up -d` will result in "Connection refused" errors.

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

### Connection Refused Errors

**Issue**: `ECONNREFUSED` when accessing `http://localhost:8000` or WebAuthn endpoints

**Root Cause**: Docker stack not running or services not healthy

**Solution**:
```bash
# 1. Check if Docker stack is running
cd web-client/docker
docker compose ps

# 2. If services are not running, start them
docker compose up -d

# 3. Wait for services to be healthy (look for "healthy" status)
docker compose ps

# 4. Check service logs if issues persist
docker compose logs webauthn-server
docker compose logs envoy-gateway
```

**Prevention**: Always run `docker compose up -d` BEFORE `npm start`

### Port Already in Use

**Issue**: `EADDRINUSE` or "port already allocated" errors

**Common Ports in Conflict**:
- 5432 (PostgreSQL)
- 6379 (Redis)
- 8000 (Envoy Gateway)
- 8082 (Client dev server)
- 16686 (Jaeger UI)

**Solution**: Use custom ports when generating client:
```bash
npx -y @vmenon25/mcp-server-webauthn-client \
  --postgres-host-port 5433 \
  --redis-host-port 6380 \
  --gateway-host-port 8001 \
  --forward-port 3000 \
  --jaeger-ui-port 16687
```

**Quick Fix**: Kill process using the port:
```bash
# Find process on port 8000
lsof -ti:8000 | xargs kill -9
```

### JWT Verification Failed (401 Unauthorized on /api/*)

**Issue**: Protected endpoints return `401 Unauthorized` even with JWT

**Root Causes**:
1. **JWKS endpoint not accessible** - Envoy can't fetch public key
2. **JWT not included** - Missing `Authorization: Bearer <token>` header
3. **JWT expired** - Token lifetime is 15 minutes
4. **JWKS cache stale** - Envoy cached old key (5-minute cache)

**Solutions**:

**Check JWKS endpoint**:
```bash
curl http://localhost:8000/.well-known/jwks.json

# Should return JSON with keys array:
# {"keys":[{"kty":"RSA","use":"sig","kid":"...","alg":"RS256","n":"...","e":"..."}]}
```

**Verify JWT is included**:
```javascript
// Correct: Include JWT in Authorization header
fetch('http://localhost:8000/api/example/data', {
  headers: {
    'Authorization': `Bearer ${jwtToken}`
  }
})
```

**Check Envoy logs**:
```bash
docker compose -f docker/docker-compose.yml logs envoy-gateway | grep -i jwt
```

**Restart Envoy** to clear JWKS cache:
```bash
cd docker && docker compose restart envoy-gateway
```

### E2E Tests Failing

**Issue**: Playwright tests fail with various errors

**Common Causes & Solutions**:

1. **Docker stack not running**:
   ```bash
   cd docker && docker compose up -d
   ```

2. **Client server not running**:
   ```bash
   # Playwright global-setup.js starts it automatically
   # If manual testing, ensure: npm start
   ```

3. **Services not healthy**:
   ```bash
   docker compose ps  # All should show "healthy" or "running"
   ```

4. **Database not initialized**:
   ```bash
   # Check if schema exists
   docker compose exec postgres psql -U webauthn_user -d webauthn -c "\dt"

   # If empty, restart postgres (schema initializes on first start)
   docker compose restart postgres
   ```

### Database Connection Errors

**Issue**: `Connection refused` or `authentication failed` for PostgreSQL

**Root Causes**:
1. PostgreSQL not healthy
2. Wrong password in environment
3. Database schema not initialized

**Solutions**:

**Check PostgreSQL health**:
```bash
docker compose ps postgres  # Should be "healthy"
docker compose logs postgres  # Check for errors
```

**Verify password**:
```bash
# Password is in docker/secrets/postgres_password
cat docker/secrets/postgres_password

# Verify it matches docker-compose.yml configuration
```

**Manual schema initialization** (if auto-init failed):
```bash
docker compose exec postgres psql -U webauthn_user -d webauthn -f /docker-entrypoint-initdb.d/V1__Create_webauthn_tables.sql
```

### Jaeger Tracing Not Working

**Issue**: No traces visible in Jaeger UI (`http://localhost:16686`)

**Root Causes**:
1. Jaeger not running
2. Services not configured for tracing
3. Wrong OTLP endpoint

**Solutions**:

**Check Jaeger status**:
```bash
docker compose ps jaeger
docker compose logs jaeger
```

**Verify trace configuration** in docker-compose.yml:
```yaml
environment:
  MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT: "http://jaeger:4317"
```

**Check if traces are being sent**:
```bash
# Generate some traffic
curl http://localhost:8000/health

# Check Jaeger UI
open http://localhost:16686
# Select "webauthn-server" service and click "Find Traces"
```

### Example Service Not Accessible

**Issue**: `/api/example/*` endpoints return 503 Service Unavailable

**Root Causes**:
1. Example service container not running
2. Port misconfiguration
3. Envoy route misconfigured

**Solutions**:

**Check service status**:
```bash
docker compose ps example-service
docker compose logs example-service
```

**Test direct access** (from within Docker network):
```bash
docker compose exec envoy-gateway wget -O- http://example-service:9000/api/example/data
```

**Check Envoy routing**:
```bash
# Envoy admin interface
curl http://localhost:9901/config_dump | jq '.configs[] | select(.["@type"] | contains("RouteConfiguration"))'
```

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
