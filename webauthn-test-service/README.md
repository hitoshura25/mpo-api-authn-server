# WebAuthn Test Service

A standalone HTTP service for generating WebAuthn test credentials across multiple platforms (Android, iOS, Unity, Unreal Engine, Web).

## Purpose

This service provides realistic WebAuthn credentials for testing client applications without requiring actual authenticators or complex cryptographic implementations in each client platform.

## Security Note

⚠️ **This service is for testing only** - it generates predictable credentials using known test keys. Never use in production environments.

## Endpoints

### Health Check
```
GET /health
```

### Generate Registration Credential
```
POST /test/generate-registration-credential
Content-Type: application/json

{
  "challenge": "base64url-encoded-challenge",
  "rpId": "localhost",
  "origin": "https://localhost",
  "username": "test-user",
  "displayName": "Test User"
}
```

**Response:**
```json
{
  "credential": "{...webauthn-credential-json...}",
  "keyPairId": "uuid-for-linking-auth",
  "credentialId": "base64url-credential-id"
}
```

### Generate Authentication Credential
```
POST /test/generate-authentication-credential
Content-Type: application/json

{
  "challenge": "base64url-encoded-challenge",
  "credentialId": "base64url-credential-id",
  "keyPairId": "uuid-from-registration",
  "rpId": "localhost",
  "origin": "https://localhost"
}
```

### Clear Test Data
```
POST /test/clear
```

## Usage

### Local Development
```bash
./gradlew run
```

### Docker
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# Stop
docker-compose down
```

### Client Integration Examples

**Android (Kotlin):**
```kotlin
// Generate registration credential
val request = TestRegistrationRequest(
    challenge = challengeFromServer,
    rpId = "localhost",
    origin = "https://localhost"
)

val response = httpClient.post("http://localhost:8081/test/generate-registration-credential") {
    contentType(ContentType.Application.Json)
    setBody(request)
}
```

**iOS (Swift):**
```swift
// Generate registration credential
let request = [
    "challenge": challengeFromServer,
    "rpId": "localhost",
    "origin": "https://localhost"
]

// Use URLSession or Alamofire to POST to http://localhost:8081/test/generate-registration-credential
```

**Unity (C#):**
```csharp
// Generate registration credential
var request = new {
    challenge = challengeFromServer,
    rpId = "localhost", 
    origin = "https://localhost"
};

// Use UnityWebRequest to POST to http://localhost:8081/test/generate-registration-credential
```

## Architecture

- **Port:** 8081 (separate from main WebAuthn server on 8080)
- **Framework:** Ktor with Jackson serialization
- **Crypto:** Yubico WebAuthn library + BouncyCastle
- **Storage:** In-memory (keypairs cleared on restart)

## Development

```bash
# Build
./gradlew build

# Test
./gradlew test

# Create shadow JAR
./gradlew shadowJar
```

## Integration with Main WebAuthn Server

This service is designed to run alongside your main WebAuthn server. Clients can:

1. Call main server to start registration/authentication (get challenge)
2. Call test service to generate realistic credential 
3. Call main server to complete registration/authentication

This keeps test utilities completely separate from production code while providing realistic test data.