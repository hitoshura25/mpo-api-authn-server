# Client Code Generation for MPO WebAuthn Server

This document explains how to automatically generate client libraries for the MPO WebAuthn authentication server.

## Overview

The server uses OpenAPI 3.0 specifications to automatically generate client libraries in multiple programming languages:

- **TypeScript/JavaScript** - For web applications and Node.js
- **Java** - For Android apps and Spring Boot services
- **Python** - For Django/Flask applications
- **C#** - For .NET applications

## Quick Start

### 1. Generate Android Client (Currently Available)

```bash
# Make sure your server is running on localhost:8080
./gradlew :webauthn-server:run

# In another terminal, generate Android client
./gradlew :webauthn-server:copyGeneratedClientToLibrary
```

### 2. Generate Other Clients (Future Implementation)

```bash
# TypeScript client (when implemented)
./gradlew :webauthn-server:generateTsClient

# Java client (when implemented)
./gradlew :webauthn-server:generateJavaClient

# Python client (when implemented)
./gradlew :webauthn-server:generatePythonClient

# C# client (when implemented)
./gradlew :webauthn-server:generateCsharpClient
```

### 3. Package for Distribution (Future Implementation)

```bash
# Generate and package all clients (when implemented)
./gradlew :webauthn-server:generateAllClients
```

## Generated Client Locations

After generation, client libraries will be available in:

```
webauthn-server/build/generated-clients/
├── android/            # Android-specific Java client (currently implemented)
├── typescript/         # TypeScript/JavaScript client (future)
├── java/               # Java client (future)  
├── python/             # Python client (future)
└── csharp/             # C# client (future)
```

**Android Client Integration:**
The Android client is automatically copied to:
```
android-test-client/client-library/src/main/java/
```

## Client Publishing

### Build and Publish All Clients (Future Implementation)

```bash
# Generate, build, and prepare all clients for publishing (when implemented)
./gradlew :webauthn-server:prepareClientPublishing
```

This will:
1. Generate all client libraries
2. Build them (compile, test, package)
3. Publish Java/Android clients to local Maven
4. Package TypeScript/Python/C# clients for distribution
5. Create distribution artifacts in `build/client-distributions/`

### Individual Client Management

```bash
# Generate specific client
./gradlew generateAndroidClient
./gradlew generateTsClient

# Build and publish individual clients
cd build/generated-clients/android
./gradlew build publishToMavenLocal

cd build/generated-clients/typescript  
npm install && npm run build && npm pack
```

### Publishing to Remote Repositories

After running `./gradlew prepareClientPublishing`, you can publish to remote repositories:

#### Maven Central (Java/Android)
```bash
cd build/generated-clients/java
# Configure Maven credentials in ~/.m2/settings.xml
./gradlew publish

cd ../android
./gradlew publish
```

#### NPM Registry (TypeScript)
```bash
cd build/generated-clients/typescript
npm login
npm publish
```

#### PyPI (Python)
```bash
cd build/generated-clients/python
pip install twine
python setup.py sdist bdist_wheel
twine upload dist/*
```

#### NuGet Gallery (C#)
```bash
cd build/generated-clients/csharp
dotnet pack
dotnet nuget push *.nupkg --api-key YOUR_API_KEY --source https://api.nuget.org/v3/index.json
```

### Using Published Clients

Once published, consumers can use the clients directly:

#### Android Project
```gradle
dependencies {
    implementation 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0'
}
```

#### NPM Project
```bash
npm install mpo-webauthn-client
```

#### Python Project
```bash
pip install mpo-webauthn-client
```

## Using the Generated Clients

### TypeScript/JavaScript Example

```typescript
import { DefaultApi, Configuration } from 'mpo-webauthn-client';

const config = new Configuration({
    basePath: 'http://localhost:8080'
});

const api = new DefaultApi(config);

// Start registration
const registrationResponse = await api.startRegistration({
    registrationRequest: {
        username: 'john.doe',
        displayName: 'John Doe'
    }
});

// Use with WebAuthn API
const credential = await navigator.credentials.create({
    publicKey: registrationResponse.data.publicKeyCredentialCreationOptions
});

// Complete registration
const result = await api.completeRegistration({
    registrationCompleteRequest: {
        requestId: registrationResponse.data.requestId,
        publicKeyCredential: credential
    }
});
```

### Java Example

```java
import com.vmenon.mpo.api.authn.client.DefaultApi;
import com.vmenon.mpo.api.authn.client.model.*;
import com.vmenon.mpo.api.authn.client.ApiClient;

// Create API client
ApiClient apiClient = new ApiClient();
apiClient.

        setBasePath("http://localhost:8080");

        DefaultApi api = new DefaultApi(apiClient);

        // Start registration
        RegistrationRequest request = new RegistrationRequest()
                .username("john.doe")
                .displayName("John Doe");

        RegistrationResponse response = api.startRegistration(request);

        // Complete registration (after WebAuthn interaction)
        RegistrationCompleteRequest completeRequest = new RegistrationCompleteRequest()
                .requestId(response.getRequestId())
                .publicKeyCredential(credential); // From WebAuthn

        RegistrationCompleteResponse result = api.completeRegistration(completeRequest);
```

### Python Example

```python
import mpo_webauthn_client
from mpo_webauthn_client.api import default_api
from mpo_webauthn_client.model.registration_request import RegistrationRequest
from mpo_webauthn_client.model.registration_complete_request import RegistrationCompleteRequest

configuration = mpo_webauthn_client.Configuration(
    host="http://localhost:8080"
)

with mpo_webauthn_client.ApiClient(configuration) as api_client:
    api_instance = default_api.DefaultApi(api_client)
    
    # Start registration
    registration_request = RegistrationRequest(
        username="john.doe",
        display_name="John Doe"
    )
    
    response = api_instance.start_registration(registration_request)
    
    # Complete registration (after WebAuthn interaction)
    complete_request = RegistrationCompleteRequest(
        request_id=response.request_id,
        public_key_credential=credential  # From WebAuthn
    )
    
    result = api_instance.complete_registration(complete_request)
```

### C# Example

```csharp
using MpoWebAuthnClient.Api;
using MpoWebAuthnClient.Model;

var api = new DefaultApi("http://localhost:8080");

// Start registration
var request = new RegistrationRequest(
    username: "john.doe",
    displayName: "John Doe"
);

var response = await api.StartRegistrationAsync(request);

// Complete registration (after WebAuthn interaction)
var completeRequest = new RegistrationCompleteRequest(
    requestId: response.RequestId,
    publicKeyCredential: credential // From WebAuthn
);

var result = await api.CompleteRegistrationAsync(completeRequest);
```

## WebAuthn Integration

The generated clients handle the HTTP communication, but you'll still need to integrate with the WebAuthn API in your
client applications:

### Web Browser (JavaScript)

```javascript
// Registration
const registrationOptions = response.data.publicKeyCredentialCreationOptions;
const credential = await navigator.credentials.create({
    publicKey: registrationOptions
});

// Authentication  
const authenticationOptions = response.data.publicKeyCredentialRequestOptions;
const assertion = await navigator.credentials.get({
    publicKey: authenticationOptions
});
```

### Android (Java/Kotlin)

```java
// Use Google's WebAuthn library for Android
// https://developers.google.com/android/reference/com/google/android/gms/fido/fido2/Fido2ApiClient
```

### iOS (Swift)

```swift
// Use AuthenticationServices framework
// https://developer.apple.com/documentation/authenticationservices
```

## API Documentation

Once your server is running, you can access:

- **Swagger UI**: http://localhost:8080/swagger
- **OpenAPI Spec**: http://localhost:8080/openapi

## Customizing Generation

### Modifying Client Configuration

Edit the generation tasks in `build.gradle.kts` to customize client options:

```kotlin
// Example: Customize TypeScript client
tasks.register<org.openapitools.generator.gradle.plugin.tasks.GenerateTask>("generateTsClient") {
    configOptions.set(
        mapOf(
            "npmName" to "my-custom-client-name",
            "supportsES6" to "true",
            "withInterfaces" to "true"
        )
    )
}
```

### Adding New Languages

Add new generation tasks for additional languages:

```kotlin
// Example: Generate Go client
tasks.register<org.openapitools.generator.gradle.plugin.tasks.GenerateTask>("generateGoClient") {
    generatorName.set("go")
    inputSpec.set(openApiSpecFile.absolutePath)
    outputDir.set("${layout.buildDirectory}/generated-clients/go")

    configOptions.set(
        mapOf(
            "packageName" to "webauthn",
            "packageVersion" to project.version.toString()
        )
    )
}
```

## Continuous Integration

Add client generation to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Generate Client Libraries
  run: |
    ./gradlew build
    ./gradlew run &
    sleep 10
    ./generate-clients.sh --package

- name: Upload Client Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: client-libraries
    path: build/client-distributions/
```

## Troubleshooting

### Server Not Running

```bash
# Start the server first
./gradlew run

# Or use Docker
docker-compose up
```

### Generation Fails

```bash
# Check OpenAPI spec is valid
curl http://localhost:8080/openapi

# Check Gradle tasks
./gradlew tasks --group=openapi
```

### Missing Dependencies

```bash
# Install required tools
npm install -g @openapitools/openapi-generator-cli
```

## Security Considerations

- Always use HTTPS in production
- Validate all inputs on the server side
- Implement proper CORS policies
- Use secure credential storage
- Follow WebAuthn best practices

## Support

For issues or questions:

- Check the [OpenAPI Generator documentation](https://openapi-generator.tech/)
- Review the [WebAuthn specification](https://www.w3.org/TR/webauthn-2/)
- Open an issue on the project repository
