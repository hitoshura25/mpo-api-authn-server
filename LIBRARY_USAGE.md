# WebAuthn Client Libraries Usage Guide

This guide explains how to use the published WebAuthn client libraries in your projects.

## 🚀 Available Libraries

The WebAuthn server automatically publishes client libraries for multiple platforms through a **consolidated E2E testing and publishing workflow**:

- **Android Library**: Published to GitHub Packages
- **TypeScript/npm Library**: Published to npm registry (main branch) or GitHub Packages (PRs)

## 🔄 Publishing Workflow

### Consolidated Architecture
Client libraries are now published as part of the same workflow that:
1. **Generates** both Android and TypeScript clients from OpenAPI spec
2. **Tests** the clients with full E2E test suite (web + Android emulator testing)
3. **Publishes** libraries only when OpenAPI changes are detected
4. **Validates** the entire pipeline in a single workflow run

### Automatic Triggers
Libraries are automatically published when:
- **OpenAPI specification changes** (in `webauthn-server/src/main/resources/openapi/**`)
- **Client generation configuration changes** (in `webauthn-server/build.gradle.kts`)
- **Workflow configuration changes** (in `.github/workflows/client-e2e-tests.yml`)
- **Force publish** via manual workflow dispatch

## 📱 Android Library Usage

### Installation

Add the GitHub Packages repository and dependency to your `build.gradle`:

```gradle
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

dependencies {
    implementation 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.123'
}
```

### Authentication Setup

Create `gradle.properties` in your project root or `~/.gradle/gradle.properties`:

```properties
# Option 1: New specific property names (preferred)
GitHubPackagesUsername=your-github-username
GitHubPackagesPassword=your-github-personal-access-token

# Option 2: Legacy property names (still supported)
gpr.user=your-github-username
gpr.key=your-github-personal-access-token
```

Or set environment variables:
```bash
# Option 1: New specific environment variables (preferred)
export ANDROID_PUBLISH_USER=your-github-username
export ANDROID_PUBLISH_TOKEN=your-github-personal-access-token

# Option 2: Legacy environment variables (still supported)
export USERNAME=your-github-username
export TOKEN=your-github-personal-access-token
```

### Basic Usage

```kotlin
import com.vmenon.mpo.api.authn.client.api.RegistrationApi
import com.vmenon.mpo.api.authn.client.api.AuthenticationApi
import com.vmenon.mpo.api.authn.client.Configuration
import com.vmenon.mpo.api.authn.client.model.RegistrationRequest

// Configure the API client
val configuration = Configuration().apply {
    host = "your-webauthn-server.com"
    scheme = "https"
}

val registrationApi = RegistrationApi(configuration)
val authenticationApi = AuthenticationApi(configuration)

// Start registration
val registrationRequest = RegistrationRequest().apply {
    username = "user@example.com"
}

registrationApi.startRegistration(registrationRequest) { result ->
    when (result) {
        is ApiResult.Success -> {
            val response = result.data
            // Handle registration start response
            // Parse publicKeyCredentialCreationOptions and use with WebAuthn
        }
        is ApiResult.Error -> {
            // Handle error
        }
    }
}
```

### WebAuthn Integration

The client works seamlessly with Android's WebAuthn/FIDO2 APIs:

```kotlin
import androidx.credentials.CredentialManager
import androidx.credentials.CreatePublicKeyCredentialRequest
import androidx.credentials.GetCredentialRequest
import androidx.credentials.PublicKeyCredential

class WebAuthnHelper(private val context: Context) {
    private val credentialManager = CredentialManager.create(context)
    
    suspend fun performRegistration(username: String) {
        // 1. Start registration with API client
        val startResponse = registrationApi.startRegistration(
            RegistrationRequest().apply { this.username = username }
        )
        
        // 2. Parse the response for WebAuthn
        val publicKeyOptions = JSONObject(startResponse.publicKeyCredentialCreationOptions)
            .getJSONObject("publicKey")
        
        // 3. Create credential request
        val createRequest = CreatePublicKeyCredentialRequest(publicKeyOptions.toString())
        
        // 4. Get credential from system
        val result = credentialManager.createCredential(
            context = context as ComponentActivity,
            request = createRequest
        )
        
        // 5. Complete registration
        val credential = result.credential as PublicKeyCredential
        registrationApi.completeRegistration(
            RegistrationCompleteRequest().apply {
                requestId = startResponse.requestId
                this.credential = credential.authenticationResponseJson
            }
        )
    }
}
```

## 🌐 TypeScript/npm Library Usage

### Installation

```bash
npm install @mpo-webauthn/client
```

### Basic Usage

```typescript
import { 
    AuthenticationApi, 
    RegistrationApi, 
    Configuration,
    RegistrationRequest 
} from '@mpo-webauthn/client';

// Configure the API client
const configuration = new Configuration({
    basePath: 'https://your-webauthn-server.com'
});

const registrationApi = new RegistrationApi(configuration);
const authenticationApi = new AuthenticationApi(configuration);

// Start registration
const registrationRequest: RegistrationRequest = {
    username: 'user@example.com'
};

try {
    const response = await registrationApi.startRegistration({
        registrationRequest
    });
    
    // Handle the response
    console.log('Registration started:', response);
} catch (error) {
    console.error('Registration failed:', error);
}
```

### WebAuthn Integration with SimpleWebAuthn

The client works perfectly with the SimpleWebAuthn browser library:

```typescript
import { startRegistration, startAuthentication } from '@simplewebauthn/browser';
import { 
    RegistrationApi, 
    AuthenticationApi, 
    Configuration 
} from '@mpo-webauthn/client';

class WebAuthnClient {
    private registrationApi: RegistrationApi;
    private authenticationApi: AuthenticationApi;
    
    constructor(serverUrl: string) {
        const config = new Configuration({ basePath: serverUrl });
        this.registrationApi = new RegistrationApi(config);
        this.authenticationApi = new AuthenticationApi(config);
    }
    
    async performRegistration(username: string) {
        try {
            // 1. Start registration
            const startResponse = await this.registrationApi.startRegistration({
                registrationRequest: { username }
            });
            
            // 2. Parse for SimpleWebAuthn
            const publicKeyOptions = JSON.parse(
                startResponse.publicKeyCredentialCreationOptions
            ).publicKey;
            
            // 3. Get credential from browser
            const credential = await startRegistration(publicKeyOptions);
            
            // 4. Complete registration
            const completeResponse = await this.registrationApi.completeRegistration({
                registrationCompleteRequest: {
                    requestId: startResponse.requestId,
                    credential: JSON.stringify(credential)
                }
            });
            
            return completeResponse;
        } catch (error) {
            console.error('Registration failed:', error);
            throw error;
        }
    }
    
    async performAuthentication(username: string) {
        try {
            // 1. Start authentication
            const startResponse = await this.authenticationApi.startAuthentication({
                authenticationRequest: { username }
            });
            
            // 2. Parse for SimpleWebAuthn
            const publicKeyOptions = JSON.parse(
                startResponse.publicKeyCredentialRequestOptions
            ).publicKey;
            
            // 3. Get assertion from browser
            const assertion = await startAuthentication(publicKeyOptions);
            
            // 4. Complete authentication
            const completeResponse = await this.authenticationApi.completeAuthentication({
                authenticationCompleteRequest: {
                    requestId: startResponse.requestId,
                    credential: JSON.stringify(assertion)
                }
            });
            
            return completeResponse;
        } catch (error) {
            console.error('Authentication failed:', error);
            throw error;
        }
    }
}

// Usage
const client = new WebAuthnClient('https://your-webauthn-server.com');

// Register a new credential
await client.performRegistration('user@example.com');

// Authenticate with existing credential
await client.performAuthentication('user@example.com');
```

### React/Vue.js Integration

```typescript
// React Hook example
import { useState, useCallback } from 'react';
import { WebAuthnClient } from './webauthn-client';

export function useWebAuthn(serverUrl: string) {
    const [client] = useState(() => new WebAuthnClient(serverUrl));
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const register = useCallback(async (username: string) => {
        setLoading(true);
        setError(null);
        
        try {
            const result = await client.performRegistration(username);
            return result;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Registration failed');
            throw err;
        } finally {
            setLoading(false);
        }
    }, [client]);
    
    const authenticate = useCallback(async (username: string) => {
        setLoading(true);
        setError(null);
        
        try {
            const result = await client.performAuthentication(username);
            return result;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Authentication failed');
            throw err;
        } finally {
            setLoading(false);
        }
    }, [client]);
    
    return { register, authenticate, loading, error };
}
```

## 📦 Library Publishing

### Consolidated Publishing Strategy

Both Android and npm libraries are published through the **same consolidated workflow** (`client-e2e-tests.yml`) that:

1. **Generates** clients from OpenAPI specification
2. **Tests** clients with comprehensive E2E testing
3. **Publishes** libraries only when API changes are detected
4. **Creates** GitHub releases for production versions

### Publishing Events

**Main Branch Push**:
- Publishes to **production registries** (GitHub Packages for Android, npm registry for TypeScript)
- Creates **GitHub releases** with full installation documentation
- Uses **production versions** (`1.0.123`)

**Pull Request**:
- Publishes to **staging registries** (GitHub Packages for both Android and npm)
- Uses **pre-release versions** (`1.0.0-pr.42.123`)
- Enables testing of changes before merge

**Manual Trigger**:
- Force publish via workflow dispatch
- Respects same branch-based registry routing

### Change Detection
Libraries are **only published** when changes are detected in:
- OpenAPI specification files
- Client generation configuration
- Workflow configuration itself

### Versioning

**Unified npm-compatible 3-part versioning** - both Android and npm use identical formats:

- **Production releases**: `1.0.123` (main branch) - unified across platforms
- **PR snapshots**: `1.0.0-pr.42.123` (pull requests) - unchanged, already npm compatible  
- **Manual releases**: `1.0.0` (workflow_dispatch)

**Key Improvements**:
- **Unified Format**: Android and npm clients use identical version numbers
- **npm Compatibility**: All versions are npm semver compliant
- **Simplified Management**: Single version strategy for all platforms

### Publishing Destinations

**Main Branch (Production)**:
- **Android**: GitHub Packages → `com.vmenon.mpo.api.authn:mpo-webauthn-android-client`
- **npm**: Public npm registry → `@mpo-webauthn/client`
- **Docker**: DockerHub → `hitoshura25/webauthn-server`
- **Releases**: GitHub releases with installation documentation

**Pull Requests (Testing)**:
- **Android**: GitHub Packages → same repository, pre-release versions
- **npm**: GitHub Packages npm registry → `@hitoshura25/mpo-webauthn-client`
- **Docker**: Not published (PRs don't push to DockerHub)
- **Releases**: Not created for pre-release versions

### Testing PR Versions

When you create a PR that modifies the OpenAPI spec or client configuration, both libraries will be automatically published as snapshot versions.

**Find PR Versions**:
1. Go to your repository → **Packages** tab
2. Look for packages with version format `1.0.0-pr.{number}.{build}`
3. Click on the package for installation instructions

**Android PR Testing**:
```gradle
dependencies {
    implementation 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0-pr.42.123'
}
```

**npm PR Testing**:
```bash
# Configure npm for GitHub Packages
npm config set @hitoshura25:registry https://npm.pkg.github.com
npm config set //npm.pkg.github.com/:_authToken YOUR_GITHUB_TOKEN

# Install PR version (check Packages tab for exact version)
npm install @hitoshura25/mpo-webauthn-client@1.0.0-pr.42.123
```

### Manual Publishing

Force publish both libraries through the consolidated workflow:

```bash
# Trigger consolidated workflow with force publish
gh workflow run client-e2e-tests.yml

# Or trigger via main branch push workflow (which calls client-e2e-tests.yml)
gh workflow run default-branch-push.yml

# Or trigger via PR workflow (which calls client-e2e-tests.yml)
gh workflow run pull-request.yml
```

**Note**: The consolidated approach means both Android and npm clients are always published together, ensuring API consistency across platforms.

## 🔧 Configuration

### Server Configuration

Ensure your WebAuthn server is configured to accept requests from your client applications:

```yaml
# CORS configuration
cors:
  allowed_origins:
    - "https://your-app.com"
    - "http://localhost:3000"  # For development
  allowed_methods:
    - GET
    - POST
    - OPTIONS
  allowed_headers:
    - Content-Type
    - Authorization
```

### Security Considerations

1. **API Authentication**: Configure API authentication if required
2. **HTTPS Only**: Always use HTTPS in production
3. **Origin Validation**: Ensure proper origin validation in your WebAuthn server
4. **Token Storage**: Store GitHub/npm tokens securely

## 📚 API Reference

### Common Models

**RegistrationRequest**:
```typescript
{
  username: string;
}
```

**RegistrationResponse**:
```typescript
{
  requestId: string;
  publicKeyCredentialCreationOptions: string; // JSON string
}
```

**AuthenticationRequest**:
```typescript
{
  username: string;
}
```

**AuthenticationResponse**:
```typescript
{
  requestId: string;
  publicKeyCredentialRequestOptions: string; // JSON string
}
```

### Error Handling

Both libraries provide structured error responses:

```typescript
interface ErrorResponse {
  error: string;
  message: string;
  timestamp: string;
}
```

## 🛠️ Development

### Testing with Local Server

For development, you can test against a local WebAuthn server:

```typescript
// Point to local development server
const client = new WebAuthnClient('http://localhost:8080');
```

### Browser Compatibility

The TypeScript client supports:
- Chrome 67+
- Firefox 60+
- Safari 14+
- Edge 18+

### Android Compatibility

The Android client supports:
- Android API 26+ (Android 8.0)
- Java 8+
- Kotlin 1.9+

## 🔗 Additional Resources

- [WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [SimpleWebAuthn Documentation](https://simplewebauthn.dev/)
- [Android WebAuthn Guide](https://developer.android.com/training/sign-in/passkeys)
- [Server API Documentation](CLIENT_GENERATION.md)