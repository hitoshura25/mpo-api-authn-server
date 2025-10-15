# Docker Hub MCP Integration Guide

This document explains how AI agents with Docker Hub MCP servers can discover and integrate the MPO WebAuthn Server.

## Overview

The MPO WebAuthn Server Docker image includes comprehensive **OCI image labels** that Docker Hub MCP servers can read to provide AI agents with complete integration information.

## For AI Agents with Docker Hub MCP

If you have a Docker Hub MCP server configured, you can discover all configuration details with a single query:

```
Get Docker image details for hitoshura25/webauthn-server
```

or

```
Inspect Docker image hitoshura25/webauthn-server:latest and show me the labels
```

## What's Available in Image Labels

### 1. Standard OCI Annotations

Following the [OCI Image Spec](https://github.com/opencontainers/image-spec/blob/main/annotations.md):

- `org.opencontainers.image.title` - "MPO WebAuthn Server"
- `org.opencontainers.image.description` - Full project description
- `org.opencontainers.image.version` - Current version
- `org.opencontainers.image.authors` - Author information
- `org.opencontainers.image.url` - Project homepage
- `org.opencontainers.image.documentation` - README URL
- `org.opencontainers.image.source` - GitHub repository
- `org.opencontainers.image.licenses` - Apache-2.0

### 2. AI Agent Discovery Labels

**Critical breadcrumbs pointing to complete configuration:**

- `com.mpo.ai-agents.config.url` - Direct link to `.ai-agents.json`
- `com.mpo.ai-agents.config.format` - Configuration format (json)
- `com.mpo.ai-agents.quick-start` - Quick start guide URL

**Best practice:** AI agents should use these labels to fetch the complete `.ai-agents.json` file rather than relying solely on labels (labels have size limitations).

### 3. Environment Variable Labels

All required and optional environment variables with:
- Variable names
- Default values
- Required/optional status
- Sensitive data markers
- Descriptions

**Categories:**
- `com.mpo.env.database.*` - PostgreSQL configuration (5 variables)
- `com.mpo.env.redis.*` - Redis configuration (3 variables)
- `com.mpo.env.app.*` - Application configuration (2 variables)

### 4. Dependency Labels

Required and optional service dependencies:

- `com.mpo.dependencies.postgres.image` - "postgres:15-alpine"
- `com.mpo.dependencies.postgres.required` - "true"
- `com.mpo.dependencies.redis.image` - "redis:7-alpine"
- `com.mpo.dependencies.redis.required` - "true"
- `com.mpo.dependencies.jaeger.image` - "jaegertracing/all-in-one:1.53"
- `com.mpo.dependencies.jaeger.required` - "false"

### 5. Port Exposure Labels

- `com.mpo.ports.http` - "8080"
- `com.mpo.ports.http.description` - "Main HTTP API endpoint"

### 6. Security Feature Labels

- `com.mpo.security.webauthn.version` - "2.0"
- `com.mpo.security.features` - CSV list of security features implemented

## How to Use with Docker Hub MCP

### Step 1: Inspect Image (via MCP)

```
Use Docker Hub MCP to get metadata for hitoshura25/webauthn-server
```

### Step 2: Extract AI Agent Config URL

Look for the label:
```
com.mpo.ai-agents.config.url=https://raw.githubusercontent.com/hitoshura25/mpo-api-authn-server/main/.ai-agents.json
```

### Step 3: Fetch Complete Configuration

```
Fetch the URL from com.mpo.ai-agents.config.url and use it to generate docker-compose.yml
```

## Verification (Manual)

You can manually inspect these labels using Docker CLI:

```bash
# Pull the image
docker pull hitoshura25/webauthn-server:latest

# Inspect all labels
docker inspect hitoshura25/webauthn-server:latest | jq '.[0].Config.Labels'

# Get specific label
docker inspect hitoshura25/webauthn-server:latest | jq -r '.[0].Config.Labels["com.mpo.ai-agents.config.url"]'
```

Expected output for config URL:
```
https://raw.githubusercontent.com/hitoshura25/mpo-api-authn-server/main/.ai-agents.json
```

## Label Namespace Convention

This project uses the `com.mpo.*` namespace for custom labels:

- `com.mpo.ai-agents.*` - AI agent discovery and configuration
- `com.mpo.env.*` - Environment variable documentation
- `com.mpo.dependencies.*` - Service dependency information
- `com.mpo.ports.*` - Port exposure documentation
- `com.mpo.security.*` - Security features and compliance

## Advantages of OCI Labels + .ai-agents.json Approach

### Combined Benefits

1. **Discovery via Docker Hub MCP**: AI agents can find the image and get basic info
2. **Complete Configuration via .ai-agents.json**: Labels point to detailed JSON file
3. **No Size Limitations**: JSON file contains full docker-compose templates and comprehensive docs
4. **Version Controlled**: .ai-agents.json is in the repository, labels are in the image
5. **Universal Access**: Works with or without Docker Hub MCP

### Why Not Labels Alone?

Docker labels have practical size limitations (~1KB per label, ~10KB total). Complex configurations like:
- Full docker-compose.yml templates
- Comprehensive environment variable schemas
- Health check configurations
- Security considerations

...are better served by the `.ai-agents.json` file (no size limit, ~15KB for complete config).

## Workflow Comparison

### With Docker Hub MCP (Optimal)
```
1. AI Agent: "Inspect hitoshura25/webauthn-server via Docker Hub MCP"
   → Returns all labels (1 MCP call)
2. AI Agent: Extracts com.mpo.ai-agents.config.url from labels
3. AI Agent: Fetches .ai-agents.json from URL (1 HTTP call)
4. AI Agent: Generates complete docker-compose.yml
   Total: 1 MCP call + 1 HTTP call
```

### Without Docker Hub MCP (Fallback)
```
1. AI Agent: Reads README.md (1 HTTP call)
2. AI Agent: Finds .ai-agents.json reference
3. AI Agent: Fetches .ai-agents.json (1 HTTP call)
4. AI Agent: Generates complete docker-compose.yml
   Total: 2 HTTP calls
```

Both paths lead to the same comprehensive `.ai-agents.json` configuration file.

## For Developers: Adding Labels to Your Dockerfile

See the reference implementation in `/webauthn-server/Dockerfile` (lines 17-75).

**Key principles:**
1. Use standard OCI annotations for basic metadata
2. Add custom namespace labels for project-specific data
3. **Always include breadcrumb labels** pointing to complete configuration files
4. Keep label values concise (use URLs to point to detailed docs)
5. Document sensitive variables with `.sensitive="true"` labels

## Related Documentation

- **Complete Configuration**: [`.ai-agents.json`](../../.ai-agents.json)
- **Integration Guide**: [README - For AI Agents](../../README.md#-for-ai-agents--developers)
- **Docker Setup**: [docker-compose.yml](../../webauthn-server/docker-compose.yml)
- **OCI Image Spec**: https://github.com/opencontainers/image-spec/blob/main/annotations.md

## Updates and Maintenance

When updating Docker configuration:

1. Update `.ai-agents.json` with new environment variables or dependencies
2. Update Dockerfile labels to reflect changes
3. Ensure label URLs remain valid
4. Test label extraction: `docker inspect <image> | jq '.[0].Config.Labels'`
5. Rebuild and push image to Docker Hub for labels to be available

Labels are embedded at **build time** and become part of the image manifest on Docker Hub.
