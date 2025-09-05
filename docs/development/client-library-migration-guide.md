# Client Library Migration Guide

## Overview

This guide explains the migration from the legacy file-copying client generation approach to the new Docker-inspired staging → production workflow using GitHub Packages.

## Before vs After

### Legacy Approach (Before)

```bash
# Old workflow (no longer available)
./gradlew :webauthn-server:copyGeneratedClientToLibrary
./gradlew :webauthn-server:copyGeneratedTsClientToWebTestClient

# Manual file copying to test clients
cp -r build/generated-clients/android/* android-test-client/client-library/
cp -r build/generated-clients/typescript/* web-test-client/generated-client/
```

**Problems with legacy approach:**
- Manual file copying prone to errors
- No version management for testing
- Client changes only validated after main merge
- Redundant client generation in multiple workflows
- No proper package management

### New Approach (Current)

```bash
# Production packages (published automatically on main merge)
npm install @vmenon25/mpo-webauthn-client@1.0.32

# Staging packages (published automatically for PRs)
npm install @hitoshura25/mpo-webauthn-client-staging@pr-123.456
```

**Benefits of new approach:**
- Automated publishing via GitHub Actions
- Proper semantic versioning
- PR-specific staging packages for testing
- Docker-inspired staging → production workflow
- Reduced manual overhead

## Migration Steps

### For Development Teams

1. **Stop using legacy commands** (these no longer exist):
   ```bash
   # These commands are deprecated and removed
   ./gradlew :webauthn-server:copyGeneratedClientToLibrary
   ./gradlew :webauthn-server:copyGeneratedTsClientToWebTestClient
   ```

2. **Use published packages** instead:
   ```bash
   # For production applications
   npm install @vmenon25/mpo-webauthn-client
   
   # For testing PR changes
   npm install @hitoshura25/mpo-webauthn-client-staging@pr-{PR_NUMBER}.{RUN_NUMBER}
   ```

3. **Update build scripts** to remove file copying:
   ```json
   {
     "scripts": {
       "update-client": "npm install @vmenon25/mpo-webauthn-client@latest"
     }
   }
   ```

### For CI/CD Workflows

1. **Remove manual client generation** from workflows
2. **Use published packages** in E2E tests
3. **Update authentication** for GitHub Packages access

Example workflow update:
```yaml
# Before (legacy)
- name: Generate client
  run: ./gradlew :webauthn-server:copyGeneratedClientToLibrary

# After (current)
- name: Install staging client
  env:
    NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: npm install @hitoshura25/mpo-webauthn-client-staging@pr-${{ github.event.number }}.${{ github.run_number }}
```

### For Local Development

If you need to generate clients locally for development:

```bash
# Generate TypeScript client (output: build/generated-clients/typescript/)
./gradlew :webauthn-server:generateTsClient

# Generate Android client (output: build/generated-clients/android/)
./gradlew :webauthn-server:generateAndroidClient
```

**Note:** Local generation is only recommended for development. Use published packages for all testing and production use.

## Version Patterns

### Staging Versions (PRs)
- **Format**: `pr-{PR_NUMBER}.{RUN_NUMBER}`
- **Example**: `pr-123.456`
- **Purpose**: Testing client changes before merge
- **Registry**: GitHub Packages only

### Production Versions (Main Branch)
- **Format**: `{MAJOR}.{MINOR}.{PATCH}`
- **Example**: `1.0.32`
- **Purpose**: Stable releases for production use
- **Registry**: npm (TypeScript) + GitHub Packages (Android)

## Authentication Setup

### For GitHub Packages Access

Create `.npmrc` file:
```
@vmenon25:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}
```

Set environment variable:
```bash
export NODE_AUTH_TOKEN=your_github_token
```

### For CI/CD

Use `secrets.GITHUB_TOKEN` for staging packages:
```yaml
env:
  NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Package Registry Locations

### TypeScript Packages
- **Staging**: https://npm.pkg.github.com/@hitoshura25/mpo-webauthn-client-staging
- **Production**: https://registry.npmjs.org/@vmenon25/mpo-webauthn-client

### Android Packages
- **Staging**: https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server (io.github.hitoshura25:mpo-webauthn-android-client-staging)
- **Production**: https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server (io.github.hitoshura25:mpo-webauthn-android-client)

## Troubleshooting

### Common Issues

1. **Authentication failures**:
   ```bash
   # Verify GitHub token has packages:read permission
   npm whoami --registry=https://npm.pkg.github.com
   ```

2. **Package not found**:
   ```bash
   # Check if package exists for specific PR
   npm view @hitoshura25/mpo-webauthn-client-staging@pr-123.456
   ```

3. **Version conflicts**:
   ```bash
   # Clear npm cache if seeing stale packages
   npm cache clean --force
   ```

### Getting Help

- Check GitHub Actions logs for publishing status
- Verify package versions at https://github.com/hitoshura25/mpo-api-authn-server/packages
- Review client-library-staging.md for configuration details

## Timeline

- **Legacy approach**: Used until August 2025
- **Migration period**: August 2025 (Phase 1-5 implementation)
- **New approach**: Active since Phase 4 completion
- **Full cleanup**: Completed in Phase 5

This migration improves developer experience, reduces manual errors, and provides proper version management for client libraries.