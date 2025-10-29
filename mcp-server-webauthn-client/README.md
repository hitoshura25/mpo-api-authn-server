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

1. **MCP Mode** - For MCP-compatible AI agents (Claude Code, Continue.dev, Cline)
2. **CLI Mode** - For non-MCP agents (Cursor, Aider, Windsurf) or direct usage

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
You: "Please create a webauthn stack using the webauthn-client-generator MCP server."

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

#### Direct MCP Tool Call

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

**JWT Key Rotation Configuration (Advanced):**

The generated WebAuthn stack includes automatic JWT signing key rotation for enhanced security. These parameters control the rotation behavior:

- `--jwt-rotation-enabled <true|false>` - Enable automatic key rotation (default: `true`)
- `--jwt-rotation-interval-days <days>` - Days between key rotations (default: `180` = 6 months)
- `--jwt-rotation-interval-seconds <seconds>` - Override rotation interval in seconds for testing (optional)
- `--jwt-grace-period-minutes <minutes>` - Grace period before retiring old key (default: `60` = 1 hour)
- `--jwt-retention-minutes <minutes>` - How long to keep retired keys for verification (default: `60` = 1 hour)
- `--jwks-cache-duration-seconds <seconds>` - JWKS endpoint cache duration (default: `300` = 5 minutes)

**Production Example** (6-month rotation with 1-hour grace period):
```bash
npx -y @vmenon25/mcp-server-webauthn-client \
  --jwt-rotation-interval-days 180 \
  --jwt-grace-period-minutes 60 \
  --jwt-retention-minutes 60
```

**Testing Example** (accelerated 30-second rotation for E2E tests):
```bash
npx -y @vmenon25/mcp-server-webauthn-client \
  --jwt-rotation-interval-seconds 30 \
  --jwt-grace-period-minutes 0.25 \
  --jwt-retention-minutes 0.5 \
  --jwks-cache-duration-seconds 10
```

**How It Works:**
1. Server automatically rotates JWT signing keys every 180 days (or custom interval)
2. New JWTs are signed with the new key after rotation
3. Old JWTs remain valid for 60 minutes (grace period) to prevent disruption
4. Retired keys are kept for 60 minutes (retention period) then automatically cleaned up
5. JWKS endpoint (`/.well-known/jwks.json`) serves all active keys with 5-minute cache

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
User: "I need a complete WebAuthn authentication stack for testing passkeys"

Agent (internal):
1. Reads .ai-agents.json from project
2. Finds webauthn-client-generator tool
3. Extracts CLI usage examples

Agent (response):
"I found a WebAuthn stack generator tool. Run this command to generate a complete authentication infrastructure:

npx -y @vmenon25/mcp-server-webauthn-client --path ./web-client

This will generate:
• Complete zero-trust architecture with Envoy Gateway
• WebAuthn Server Docker image (hitoshura25/webauthn-server)
• PostgreSQL + Redis + Jaeger infrastructure
• TypeScript web client with complete build toolchain
• E2E Playwright tests with virtual authenticator
• JWT authentication with JWKS endpoint

After generation:
1. cd web-client/docker && docker compose up -d  # Start infrastructure
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

**Benefits for Non-MCP Agents:**
- ✅ **Accurate instructions**: Based on official documentation
- ✅ **Complete examples**: Working CLI commands ready to use
- ✅ **No manual configuration**: Single command generates everything


## What is MCP?

Model Context Protocol (MCP) is a standard protocol that allows AI agents like Claude to interact with external tools and services. MCP servers expose tools that AI agents can discover and use automatically to help users accomplish tasks.

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

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Generated Stack                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Web Client (TypeScript)                                        │
│  └─ http://localhost:8082                                       │
│         │                                                       │
│         │ WebAuthn Registration/Authentication                  │
│         ▼                                                       │
│  ┌────────────────────────────────────────┐                     │
│  │    Envoy Gateway (port 8000)           │                     │
│  │  ┌──────────────────────────────────┐  │                     │
│  │  │ Public Routes (no JWT required)  │  │                     │
│  │  │  ✓ /register/*                   │  │                     │
│  │  │  ✓ /authenticate/*               │  │                     │
│  │  │  ✓ /.well-known/jwks.json        │  │                     │
│  │  │  ✓ /health                       │  │                     │
│  │  └──────────────────────────────────┘  │                     │
│  │  ┌──────────────────────────────────┐  │                     │
│  │  │ Protected Routes (JWT required)  │  │                     │
│  │  │  ✓ /api/* → JWT verification via │  │                     │
│  │  │    JWKS endpoint                 │  │                     │
│  │  └──────────────────────────────────┘  │                     │
│  └─────┬──────────────┬─────────────────┘                       │
│        │              │                                         │
│        │              │ mTLS (Phase 2)                          │
│        ▼              ▼                                         │
│  ┌────────── ┐   ┌───────────────── ┐                           │
│  │ WebAuthn  │   │ Example Service  │                           │
│  │  Server   │   │  (Python/FastAPI)│                           │
│  │ :8080     │   │   :9000          │                           │
│  │           │   │                  │                           │
│  │ • Issues  │   │ • Validates JWT  │                           │
│  │   JWTs    │   │ • Protected      │                           │
│  │ • JWKS    │   │   /api/example/* │                           │
│  │   endpoint│   │   endpoints      │                           │
│  └────┬───── ┘   └───────────────── ┘                           │
│       │                                                         │
│       ├─ PostgreSQL 15 (credentials)                            │
│       ├─ Redis 7 (sessions)                                     │
│       └─ Jaeger (distributed tracing)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

JWT Authentication Flow:
1. User authenticates via WebAuthn → Server issues JWT
2. Client includes JWT in Authorization header for /api/* requests
3. Envoy Gateway fetches public key from /.well-known/jwks.json
4. Envoy verifies JWT signature using JWKS before forwarding request
5. Protected service receives verified request with JWT

Security Principles:
• Never trust, always verify (even internal traffic)
• JWT verification at perimeter (Envoy Gateway)
• Public key cryptography (JWKS) for verification
• mTLS for inter-service communication
• Secrets management via Docker secrets
```

## Troubleshooting

### Connection Refused Errors

**Issue**: `ECONNREFUSED` when accessing `http://localhost:8000` or WebAuthn endpoints

**Solution**:
```bash
# Check if Docker stack is running
cd web-client/docker && docker compose ps

# Start services if not running
docker compose up -d

# Check service logs if issues persist
docker compose logs webauthn-server envoy-gateway
```

**Prevention**: Always run `docker compose up -d` BEFORE `npm start`

### Port Already in Use

**Issue**: `EADDRINUSE` or "port already allocated" errors

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
lsof -ti:8000 | xargs kill -9
```

### JWT Verification Failed (401 Unauthorized)

**Issue**: Protected endpoints return `401 Unauthorized` even with JWT

**Solutions**:

1. **Check JWKS endpoint is accessible**:
   ```bash
   curl http://localhost:8000/.well-known/jwks.json
   ```

2. **Verify JWT is included in Authorization header**:
   ```javascript
   fetch('http://localhost:8000/api/example/data', {
     headers: { 'Authorization': `Bearer ${jwtToken}` }
   })
   ```

3. **Restart Envoy to clear JWKS cache**:
   ```bash
   cd docker && docker compose restart envoy-gateway
   ```

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

## Contributing

Contributions welcome! Please open an issue or pull request on the [GitHub repository](https://github.com/hitoshura25/mpo-api-authn-server).

## License

Apache-2.0

## Links

- **Main Project**: [mpo-api-authn-server](https://github.com/hitoshura25/mpo-api-authn-server)
- **WebAuthn Client Library**: [@vmenon25/mpo-webauthn-client](https://www.npmjs.com/package/@vmenon25/mpo-webauthn-client)
- **Model Context Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)

