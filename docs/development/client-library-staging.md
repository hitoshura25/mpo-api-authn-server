# Client Library Staging Configuration

This document describes the staging → production pattern for client library publishing, following the Docker-inspired approach outlined in `docs/improvements/completed/openapi-client-refactor.md`.

## Version Patterns

### Staging Versions (PR Testing)
- **Pattern**: `{NEXT_VERSION}-pr.{PR_NUMBER}.{RUN_NUMBER}`
- **Example**: `1.0.36-pr.123.456` (next version would be 1.0.36, PR #123, GitHub run #456)
- **Logic**: Based on latest release tag + 1, then adds PR suffix
- **Usage**: E2E testing of client libraries before main merge
- **Registry**: GitHub Packages only

### Production Versions (Main Branch)
- **Pattern**: `{MAJOR}.{MINOR}.{PATCH}` (semantic versioning)
- **Example**: `1.0.36` (follows the next build number sequence)
- **Logic**: Based on latest release tag + 1 for continuous versioning
- **Usage**: Published after successful E2E tests
- **Registry**: npm (TypeScript) + GitHub Packages (Android)

## Package Names

### TypeScript Packages
```yaml
# Staging (GitHub Packages)
Package: @hitoshura25/mpo-webauthn-client-staging
Version: 1.0.36-pr.123.456
Registry: https://npm.pkg.github.com

# Production (npm)
Package: @vmenon25/mpo-webauthn-client
Version: 1.0.36
Registry: https://registry.npmjs.org
```

### Android Packages
```yaml
# Staging (GitHub Packages)
GroupId: io.github.hitoshura25
ArtifactId: mpo-webauthn-android-client-staging
Version: 1.0.36-pr.123.456
Repository: https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server

# Production (GitHub Packages)
GroupId: io.github.hitoshura25
ArtifactId: mpo-webauthn-android-client
Version: 1.0.36
Repository: https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server
```

## Authentication Setup

### Required Secrets
```yaml
# GitHub repository secrets
GITHUB_TOKEN: # Already exists - for GitHub Packages
NPM_TOKEN:    # Required for npm publishing (production)

# Environment variables for local testing
ANDROID_PUBLISH_USER: ${GITHUB_ACTOR}
ANDROID_PUBLISH_TOKEN: ${GITHUB_TOKEN}
```

### GitHub Packages Permissions
The workflow requires these permissions:
```yaml
permissions:
  contents: read    # Read repository files
  packages: write   # Publish to GitHub Packages
  id-token: write   # Generate attestations
```

## Workflow Integration

### Staging Workflow (PR Testing)
```yaml
# Call from PR workflows
- name: Publish staging client libraries
  uses: ./.github/workflows/client-publish.yml
  with:
    publish-type: "staging"
    client-version: "pr-${{ github.event.pull_request.number }}.${{ github.run_number }}"
    pr-number: ${{ github.event.pull_request.number }}
```

### Production Workflow (Main Branch)
```yaml
# Call from main branch post-processing
- name: Publish production client libraries
  uses: ./.github/workflows/client-publish.yml
  with:
    publish-type: "production"
    client-version: "1.0.32"  # From version-manager.sh
```

## Test Client Configuration

### Web Test Client (.npmrc)
```ini
# For staging packages (PR testing)
@vmenon25:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}

# For production packages (after refactor)
registry=https://registry.npmjs.org
```

### Android Test Client (repositories)
```kotlin
repositories {
    maven {
        name = "GitHubPackages"
        url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
        credentials {
            username = project.findProperty("gpr.user") ?: System.getenv("USERNAME")
            password = project.findProperty("gpr.key") ?: System.getenv("TOKEN")
        }
    }
}
```

## Implementation Status

### Phase 1: Foundation Setup ✅
- [x] Created `client-publish.yml` callable workflow
- [x] Added staging vs production package name logic
- [x] Configured GitHub Packages authentication
- [x] Added Android client publishing task to webauthn-server
- [x] Created version pattern documentation
- [x] Added authentication verification script
- [x] Created test workflow for manual validation

### Phase 2: Client Publishing Workflow ✅
- [x] Basic workflow structure
- [x] Staging package name configuration
- [x] Production package name configuration
- [x] Authentication setup documentation
- [x] Fix Android artifact ID configuration in build.gradle.kts
- [x] Test staging client generation (staging package names verified)
- [x] Test production client generation (production package names verified)
- [ ] Test staging package publishing (requires GITHUB_TOKEN)
- [ ] Test production package publishing (requires NPM_TOKEN)
- [ ] Validate end-to-end workflow with actual publishing

### Phase 3: Test Client Migration ✅
- [x] Update web-test-client to use published packages
- [x] Update android-test-client to use published packages  
- [x] Remove file copying logic (commented out legacy tasks)
- [x] Create integration test script for published packages
- [x] Update npm and Maven repository configurations

### Phase 4: Workflow Integration (Planned)
- [ ] Update E2E test workflows
- [ ] Update main branch publishing
- [ ] Remove legacy client generation

### Phase 5: Cleanup (Planned)
- [ ] Remove legacy Gradle tasks
- [ ] Update documentation
- [ ] Clean up generated directories

## Verified Functionality

### ✅ Client Generation Tests Passed
```bash
# Staging configuration verified:
./gradlew generateTsClient generateAndroidClient \
  -PclientVersion=pr-999.123 \
  -PnpmName=@vmenon25/mpo-webauthn-client-staging \
  -PandroidArtifactId=mpo-webauthn-android-client-staging

# Results:
# TypeScript: @vmenon25/mpo-webauthn-client-staging@pr-999.123
# Android: com.vmenon.mpo.api.authn:mpo-webauthn-android-client-staging:pr-999.123

# Production configuration verified:
./gradlew generateTsClient generateAndroidClient \
  -PclientVersion=1.0.32 \
  -PnpmName=@vmenon25/mpo-webauthn-client \
  -PandroidArtifactId=mpo-webauthn-android-client

# Results:
# TypeScript: @vmenon25/mpo-webauthn-client@1.0.32
# Android: com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.32
```

### ✅ Authentication Setup Verification
```bash
# Authentication verification script created and tested:
./scripts/setup/verify-client-publishing-auth.sh

# Status: Ready for testing (requires tokens)
# - GITHUB_TOKEN needed for staging publishing
# - NPM_TOKEN needed for production publishing  
```

### ✅ Workflow Configuration Complete
- `client-publish.yml` callable workflow created with staging/production logic
- `test-client-publish.yml` manual test workflow created
- Package naming patterns implemented and verified
- Version patterns (pr-X.Y vs semantic) working correctly

### ✅ Test Client Migration Complete  
- Web-test-client now imports from `@vmenon25/mpo-webauthn-client` 
- Android-test-client now uses `com.vmenon.mpo.api.authn:mpo-webauthn-android-client` from GitHub Packages
- Legacy file copying tasks commented out in `build.gradle.kts`
- `.npmrc` configured for GitHub Packages scoped package resolution
- Android `settings.gradle` configured with GitHub Packages Maven repository
- Integration test script created: `scripts/test-published-package-integration.sh`

## Testing Instructions

### Local Testing
```bash
# Test client generation
./gradlew generateTsClient generateAndroidClient

# Test staging client publishing manually (for development/debugging)
gh workflow run test-client-publish.yml -f test-type=staging -f pr-number=999

# Note: Published package integration is automatically tested by production E2E workflows

# Test staging publish (requires authentication)
./gradlew :webauthn-server:publishAndroidClient \
  -PclientVersion="test-1.0" \
  -PandroidArtifactId="mpo-webauthn-android-client-staging" \
  -PGitHubPackagesUsername="${GITHUB_ACTOR}" \
  -PGitHubPackagesPassword="${GITHUB_TOKEN}"
```

### CI Testing
```bash
# Trigger client-publish workflow manually
gh workflow run client-publish.yml \
  -f publish-type=staging \
  -f client-version=test-1.0 \
  -f pr-number=123
```

## Troubleshooting

### Common Issues
1. **Authentication failures**: Check GITHUB_TOKEN permissions
2. **Package name conflicts**: Ensure staging vs production names are correct
3. **Version conflicts**: Use unique versions for each test

### Debug Commands
```bash
# Check generated clients
ls -la build/generated-clients/

# Verify package.json updates
cat build/generated-clients/typescript/package.json | jq '.name, .version'

# Test npm authentication
npm whoami --registry=https://npm.pkg.github.com
```