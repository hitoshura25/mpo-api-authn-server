# Android Client Package Structure

## Overview

The generated Android client library uses a clear, hierarchical package structure under the `io.github.hitoshura25.webauthn` namespace. The library is built as a separate Gradle submodule (`android-client-library`) for clean separation and direct publishing.

## Package Structure

### Maven Coordinates
```xml
<dependency>
    <groupId>io.github.hitoshura25</groupId>
    <artifactId>mpo-webauthn-android-client</artifactId>
    <version>1.0.X</version>
</dependency>
```

### Gradle Dependency
```kotlin
dependencies {
    implementation("io.github.hitoshura25:mpo-webauthn-android-client:1.0.X")
}
```

### Package Hierarchy

```
io.github.hitoshura25.webauthn.client
├── ApiClient                    // Main API client configuration
├── Configuration               // Client configuration settings
├── ApiException               // Exception handling
│
├── api/                       // API endpoints
│   ├── AuthenticationApi     // Authentication operations
│   ├── RegistrationApi       // Registration operations
│   └── HealthApi            // Health check operations
│
├── model/                    // Data models
│   ├── AuthenticationRequest
│   ├── AuthenticationResponse
│   ├── AuthenticationCompleteRequest
│   ├── AuthenticationCompleteResponse
│   ├── RegistrationRequest
│   ├── RegistrationResponse
│   ├── RegistrationCompleteRequest
│   ├── RegistrationCompleteResponse
│   ├── ErrorResponse
│   └── HealthResponse
│
└── auth/                     // Authentication helpers (if any)
```

## Usage Example

```kotlin
import io.github.hitoshura25.webauthn.client.ApiClient
import io.github.hitoshura25.webauthn.client.Configuration
import io.github.hitoshura25.webauthn.client.api.RegistrationApi
import io.github.hitoshura25.webauthn.client.api.AuthenticationApi
import io.github.hitoshura25.webauthn.client.model.RegistrationRequest
import io.github.hitoshura25.webauthn.client.model.AuthenticationRequest

// Configure the API client
val configuration = Configuration().apply {
    host = "https://your-webauthn-server.com"
}
val apiClient = ApiClient(configuration)

// Create API instances
val registrationApi = RegistrationApi(apiClient)
val authenticationApi = AuthenticationApi(apiClient)

// Use the APIs
val registrationRequest = RegistrationRequest().apply {
    username = "user@example.com"
    displayName = "John Doe"
}

val registrationResponse = registrationApi.startRegistration(registrationRequest)
```

## Benefits of This Structure

1. **Clear Namespace**: `io.github.hitoshura25.webauthn` clearly indicates this is a WebAuthn-related package
2. **Hierarchical Organization**: Logical separation of concerns (api, model, auth)
3. **Maven Central Compatible**: Follows Maven Central naming conventions
4. **Intuitive Imports**: Package names are self-documenting
5. **Collision Avoidance**: Unique namespace prevents conflicts with other libraries

## Version History

- **v1.0.0+**: Uses `io.github.hitoshura25.webauthn.client.*` package structure
- **Pre-v1.0.0**: Used legacy `com.vmenon.mpo.api.authn.client.*` package structure (deprecated)

## Migration Guide

If migrating from the legacy package structure, update your imports:

```kotlin
// Old (deprecated)
import com.vmenon.mpo.api.authn.client.api.RegistrationApi

// New (current)
import io.github.hitoshura25.webauthn.client.api.RegistrationApi
```

The API functionality remains identical - only the package names have changed.