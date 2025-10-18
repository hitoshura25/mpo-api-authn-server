# MCP Server Publishing Guide

This document explains how the MCP server is automatically published to npm when changes are made.

## Automated Publishing Workflow

The MCP server is automatically published to npm via GitHub Actions when changes are pushed to the `main` branch.

### Workflow: `.github/workflows/publish-mcp-server.yml`

**Trigger**: Automatically runs when:
- Code is pushed to `main` branch
- Files in `mcp-server-webauthn-client/**` are modified

**What it does**:
1. **Auto-increment version**: Reads existing `mcp-server-v*` git tags and increments patch version
2. **Update package.json**: Sets new version in package.json
3. **Build TypeScript**: Compiles MCP server and CLI tool
4. **Validate outputs**: Ensures all required entry points exist
5. **Publish to npm**: Publishes `@vmenon25/mcp-server-webauthn-client` with public access
6. **Create git tag**: Creates and pushes `mcp-server-v{version}` tag
7. **Create GitHub release**: Creates release with installation instructions

## Versioning Strategy

### Format
- **Git tags**: `mcp-server-v{major}.{minor}.{patch}` (e.g., `mcp-server-v1.0.5`)
- **npm version**: `{major}.{minor}.{patch}` (e.g., `1.0.5`)

### Independent Versioning
The MCP server uses **independent versioning** from other client libraries:
- `mcp-server-v*` - MCP server package versions
- `npm-client-v*` - TypeScript client library versions (separate)
- `android-client-v*` - Android client library versions (separate)

### Auto-Increment Logic
1. Find highest existing `mcp-server-v*` tag (e.g., `mcp-server-v1.0.4`)
2. Extract patch number (e.g., `4`)
3. Increment patch (e.g., `5`)
4. Create new version (e.g., `1.0.5`)
5. Create new tag (e.g., `mcp-server-v1.0.5`)

## Manual Publishing (Not Recommended)

If you need to publish manually for testing:

```bash
cd mcp-server-webauthn-client

# Update version in package.json
npm version 1.0.X --no-git-tag-version

# Build
npm install
npm run build

# Publish (requires NPM_PUBLISH_TOKEN)
npm publish --access public
```

**Note**: Manual publishing should be avoided. Use the automated workflow for consistency.

## First-Time Setup

The workflow requires the `NPM_PUBLISH_TOKEN` secret to be configured in GitHub repository settings.

### Verifying Secret Configuration
1. Go to repository Settings → Secrets and variables → Actions
2. Verify `NPM_PUBLISH_TOKEN` secret exists
3. Secret should contain npm publish token with public package publishing permissions

## Workflow Execution

### Successful Publish
When the workflow succeeds:
- ✅ New version published to npm: `@vmenon25/mcp-server-webauthn-client@{version}`
- ✅ Git tag created: `mcp-server-v{version}`
- ✅ GitHub release created with installation instructions
- ✅ Package available via `npx -y @vmenon25/mcp-server-webauthn-client`

### Viewing Results
- **npm package**: https://www.npmjs.com/package/@vmenon25/mcp-server-webauthn-client
- **GitHub releases**: https://github.com/hitoshura25/mpo-api-authn-server/releases
- **Workflow runs**: https://github.com/hitoshura25/mpo-api-authn-server/actions/workflows/publish-mcp-server.yml

## Testing Changes Before Publishing

To test changes locally before pushing to `main`:

```bash
cd mcp-server-webauthn-client

# Build TypeScript
npm install
npm run build

# Test CLI mode
npx . --path /tmp/test-client --server http://localhost:8080

# Test MCP mode (create test configuration)
# Add to test project's claude_config.json:
{
  "mcpServers": {
    "webauthn-test": {
      "command": "node",
      "args": ["/absolute/path/to/mcp-server-webauthn-client/dist/index.js"]
    }
  }
}
```

## Package Information

### Published Package
- **Name**: `@vmenon25/mcp-server-webauthn-client`
- **Registry**: npm (https://registry.npmjs.org)
- **Access**: Public
- **License**: Apache-2.0

### Entry Points
- **CLI**: `dist/cli.js` (executable via `npx`)
- **MCP Server**: `dist/index.js` (stdio transport for MCP protocol)

### Installation Methods

#### Global (For AI Agents)
```bash
npm install -g @vmenon25/mcp-server-webauthn-client
```

#### npx (One-time execution)
```bash
npx -y @vmenon25/mcp-server-webauthn-client
```

#### MCP Configuration
```json
{
  "mcpServers": {
    "webauthn-client-generator": {
      "command": "npx",
      "args": ["-y", "@vmenon25/mcp-server-webauthn-client"]
    }
  }
}
```

## Troubleshooting

### Workflow Fails: "Authentication failed"
- **Cause**: NPM_PUBLISH_TOKEN secret is missing or invalid
- **Solution**: Verify secret exists in repository settings and contains valid npm token

### Workflow Fails: "Version already exists"
This shouldn't happen with auto-increment logic, but if it does:
- **Cause**: Git tag exists but npm package wasn't published
- **Solution**: Manually increment version or delete conflicting tag

### Build Fails: Entry points not found
- **Cause**: TypeScript compilation failed
- **Solution**: Check TypeScript errors in workflow logs, fix source code issues

## Next Steps After Publishing

After the MCP server is published to npm:

1. **Test in external project**:
   - Create new project
   - Add MCP configuration to `claude_config.json`
   - Ask Claude Code to generate web client

2. **Update documentation**:
   - Verify README.md examples work with published version
   - Update any hardcoded version numbers in docs

3. **Announce release**:
   - GitHub release automatically created
   - Share npm package link with users

## Related Documentation

- [README.md](README.md) - Main MCP server documentation
- [TOKEN-COST-ANALYSIS.md](TOKEN-COST-ANALYSIS.md) - Token cost analysis for different usage modes
- [HYBRID-INTEGRATION-STRATEGIES.md](HYBRID-INTEGRATION-STRATEGIES.md) - Multi-language integration strategies
- [.github/workflows/publish-mcp-server.yml](../.github/workflows/publish-mcp-server.yml) - Publishing workflow source code
