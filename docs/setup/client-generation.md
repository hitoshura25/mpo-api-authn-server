# Client Library Architecture for MPO WebAuthn Server

This document explains the implemented **Docker-inspired staging→production workflow** for client library generation, publishing, and consumption.

## Overview

The OpenAPI client library refactor has been **successfully implemented**, replacing the old file-copying approach with a modern package management workflow similar to Docker's staging→production pattern.

## Architecture Summary

### 🏗️ **Implemented Architecture** (Current State)

The project now uses dedicated client library submodules with automated publishing:

```
mpo-api-authn-server/
├── android-client-library/          # Dedicated Android client submodule
│   ├── src/main/java/               # Generated OpenAPI client source
│   ├── build.gradle.kts             # Publishing configuration
│   └── README.md                    # Client documentation
├── typescript-client-library/       # Dedicated TypeScript client submodule
│   ├── src/                         # Generated TypeScript client source
│   ├── package.json                 # npm publishing configuration
│   └── README.md                    # Client documentation
├── android-test-client/             # E2E test client (consumes published Android library)
├── web-test-client/                 # E2E test client (consumes published npm library)
└── .github/workflows/
    ├── client-publish.yml           # Publishing orchestrator
    ├── publish-android.yml          # Android-specific publishing
    └── publish-typescript.yml       # TypeScript-specific publishing
```

### 🔄 **Staging→Production Workflow**

1. **Client Generation**: OpenAPI spec generates client code in submodules
2. **Staging Publishing**: PR changes publish staging packages to GitHub Packages
3. **E2E Validation**: Test clients consume staging packages for validation
4. **Production Publishing**: Main branch merges publish to npm + GitHub Packages
5. **GitHub Releases**: Automated release creation with usage examples

## Published Client Libraries

### Android Library

**Production Package**:

```gradle
repositories {
    maven {
        url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
        credentials {
            username = "YOUR_GITHUB_USERNAME"
            password = "YOUR_GITHUB_TOKEN"
        }
    }
}

dependencies {
    implementation 'io.github.hitoshura25:mpo-webauthn-android-client:1.0.X'
}
```

**Staging Package** (for PR testing):

```gradle
dependencies {
    implementation 'io.github.hitoshura25:mpo-webauthn-android-client-staging:pr-123.456'
}
```

### TypeScript/npm Library

**Production Package**:

```bash
npm install @vmenon25/mpo-webauthn-client
```

**Staging Package** (for PR testing):

```bash
npm install @vmenon25/mpo-webauthn-client-staging@pr-123.456
```

## Automated Publishing Workflows

### Client Publishing Orchestrator

**File**: `.github/workflows/client-publish.yml`

- Coordinates parallel TypeScript and Android publishing
- Supports both staging and production publishing
- Validates inputs and provides comprehensive outputs

### Platform-Specific Workflows

**Android Publishing** (`.github/workflows/publish-android.yml`):

- Generates Android client from OpenAPI spec
- Publishes to GitHub Packages Maven repository
- Handles version conflict detection

**TypeScript Publishing** (`.github/workflows/publish-typescript.yml`):

- Generates TypeScript client from OpenAPI spec
- Publishes to npm (production) or GitHub Packages (staging)
- Builds CommonJS + ESM + TypeScript declarations

## Version Management

Both clients use **unified semantic versioning**:

- **Format**: `{MAJOR}.{MINOR}.{PATCH}` (e.g., `1.0.26`)
- **PR Versions**: `pr-{PR_NUMBER}.{RUN_NUMBER}` (e.g., `pr-123.456`)
- **Script**: `scripts/core/version-manager.sh`
- **Enhanced Validation**: Full npm semver compliance with prerelease support

## E2E Testing Integration

### Test Client Architecture

- **android-test-client/**: Consumes published Android library for E2E testing
- **web-test-client/**: Consumes published npm library for E2E testing
- **E2E Workflow**: `.github/workflows/e2e-tests.yml` orchestrates cross-platform testing

### Testing Flow

1. **Staging Packages**: Published to GitHub Packages during PR validation
2. **Package Consumption**: Test clients update dependencies to staging versions
3. **E2E Validation**: Comprehensive WebAuthn flow testing with real packages
4. **Production Publishing**: Only occurs after successful E2E validation

## Local Development

### Client Library Development

```bash
# Work with Android client library
cd android-client-library
./gradlew build test
./gradlew publishToMavenLocal

# Work with TypeScript client library
cd typescript-client-library
npm install
npm run build
npm test
```

### Generate and Update Clients

```bash
# Generate clients and copy to submodules
./gradlew generateAndroidClient copyAndroidClientToSubmodule
./gradlew generateTsClient copyTsClientToSubmodule

# Build and test client libraries
cd android-client-library && ./gradlew test
cd typescript-client-library && npm test
```

### Test Client Development

```bash
# Android E2E test client
cd android-test-client
./gradlew build
./gradlew connectedAndroidTest

# Web E2E test client
cd web-test-client
npm install
npm run build
npm test
```

## Usage Examples

### Android Integration

```java
import io.github.hitoshura25.webauthn.client.api.*;
import io.github.hitoshura25.webauthn.client.model.*;

// Create API client
Configuration config = new Configuration();
config.

        setBasePath("https://your-webauthn-server.com");

        RegistrationApi registrationApi = new RegistrationApi(config);

        // Start registration
        RegistrationRequest request = new RegistrationRequest()
                .username("john.doe")
                .displayName("John Doe");

        RegistrationResponse response = registrationApi.startRegistration(request);
```

### TypeScript Integration

```typescript
import { 
  AuthenticationApi, 
  RegistrationApi,
  Configuration 
} from '@vmenon25/mpo-webauthn-client';

// Configure API client
const config = new Configuration({
  basePath: 'https://your-webauthn-server.com'
});

const registrationApi = new RegistrationApi(config);

// Start registration
const response = await registrationApi.startRegistration({
  registrationRequest: {
    username: 'john.doe',
    displayName: 'John Doe'
  }
});
```

## Configuration Management

### Centralized Package Configuration

All package names and versions are centrally managed in workflow environment variables:

```yaml
# .github/workflows/client-publish.yml
env:
  NPM_PACKAGE_NAME: "mpo-webauthn-client"
  ANDROID_GROUP_ID: "io.github.hitoshura25"
  ANDROID_ARTIFACT_BASE_ID: "mpo-webauthn-android-client"
```

### Environment-Specific Configuration

- **Development**: Use published packages or local Maven/npm repositories
- **Staging**: Use GitHub Packages with staging package names
- **Production**: Use npm registry and GitHub Packages with production names

## Security Considerations

- **GitHub Packages Authentication**: Uses GITHUB_TOKEN for package access
- **npm Publishing**: Uses NPM_TOKEN secret for production publishing
- **Version Validation**: Enhanced regex validation prevents malformed versions
- **Package Signing**: npm packages include provenance attestations

## Benefits Achieved

✅ **Eliminated File Copying**: No more manual copying between generated and test clients  
✅ **Standard Package Management**: Uses npm and Maven repositories properly  
✅ **PR Testing**: Client changes validated before main branch merge  
✅ **Parallel Publishing**: Android and TypeScript clients published independently  
✅ **Production Validation**: E2E tests ensure published packages work correctly  
✅ **Automated Releases**: GitHub releases created automatically with usage examples

## Migration from Old Approach

The previous file-copying approach has been completely replaced:

### Old Approach (Removed)

- ❌ Generated clients copied to `generated-client/` directories
- ❌ Manual file copying between build output and test clients
- ❌ Complex Gradle tasks for file management
- ❌ No staging/testing of published packages

### New Approach (Implemented)

- ✅ Dedicated client library submodules
- ✅ Standard npm and Maven publishing workflows
- ✅ Staging→production validation pipeline
- ✅ Automated package management

## Troubleshooting

### Common Issues

1. **Package Not Found**
    - Verify GitHub Packages authentication is configured
    - Check if package version exists in the registry
    - Ensure repository configuration includes GitHub Packages

2. **Version Conflicts**
    - Client publishing workflows detect existing versions
    - Staging packages use unique PR-based versions
    - Production versions follow semantic versioning

3. **Build Failures**
    - Check client library submodules are up to date
    - Verify OpenAPI specification is valid
    - Review publishing workflow logs for specific errors

### Debug Commands

```bash
# Check package availability
npm view @vmenon25/mpo-webauthn-client

# Verify GitHub Packages access
gh api user/packages

# Test local client generation
./gradlew generateAndroidClient generateTsClient
```

## Support

For issues related to client libraries:

- **Client Library Issues**: Check submodule documentation (`android-client-library/README.md`, `typescript-client-library/README.md`)
- **Publishing Issues**: Review workflow logs in `.github/workflows/`
- **E2E Testing**: See test client documentation (`android-test-client/README.md`, `web-test-client/README.md`)
- **OpenAPI Changes**: Ensure server specification is updated first

## Related Documentation

- [Main Project README](../../README.md) - Full project overview
- [Android Test Client](../../android-test-client/README.md) - E2E testing with Android
- [Web Test Client](../../web-test-client/README.md) - E2E testing with TypeScript
- [Client Library Publishing](../development/client-library-publishing.md) - Workflow details
- [OpenAPI Refactor Plan](../OPENAPI_CLIENT_REFACTOR_PLAN.md) - Historical implementation plan
