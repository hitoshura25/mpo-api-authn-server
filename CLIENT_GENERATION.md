# Client Code Generation for MPO WebAuthn Server

This document explains how to automatically generate client libraries for the MPO WebAuthn authentication server.

## Overview

The server uses OpenAPI 3.0 specifications to automatically generate client libraries in multiple programming languages:

- **TypeScript/JavaScript** - For web applications and Node.js
- **Java** - For Android apps and Spring Boot services
- **Python** - For Django/Flask applications
- **C#** - For .NET applications

## Quick Start

### 1. Generate All Client Libraries

```bash
# Make sure your server is running on localhost:8080
./gradlew run

# In another terminal, generate all clients
./generate-clients.sh
```

### 2. Generate Specific Client

```bash
# TypeScript client only
./gradlew generateTsClient

# Java client only  
./gradlew generateJavaClient

# Python client only
./gradlew generatePythonClient

# C# client only
./gradlew generateCsharpClient
```

### 3. Package for Distribution

```bash
# Generate and package all clients
./generate-clients.sh --package
```

## Generated Client Locations

After generation, client libraries will be available in:

```
build/generated-clients/
├── typescript/          # TypeScript/JavaScript client
├── java/               # Java client
├── python/             # Python client
└── csharp/             # C# client
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
