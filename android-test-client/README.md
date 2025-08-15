# Android WebAuthn Test Client

This is an Android E2E test client for the MPO WebAuthn authentication server. It consumes the published Android client library to demonstrate WebAuthn registration and authentication flows using real published packages.

## Features

- **WebAuthn Registration**: Register new users with FIDO2/WebAuthn credentials
- **WebAuthn Authentication**: Authenticate existing users using biometric/security key
- **Real-time Logging**: View detailed logs of the authentication process
- **Error Handling**: Comprehensive error handling and user feedback
- **Published API Client**: Uses published Android client library for type-safe API communication

## Prerequisites

- Android Studio Arctic Fox or later
- Android SDK API level 26+ (Android 8.0)
- Device or emulator with biometric capability (for real WebAuthn)
- MPO WebAuthn server running (see main project README)

## Setup

### 1. Published Client Library Architecture

The Android test client consumes the published Android client library from GitHub Packages:

```gradle
repositories {
    maven {
        url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
        credentials {
            username = System.getenv("GITHUB_ACTOR")
            password = System.getenv("GITHUB_TOKEN")
        }
    }
}

dependencies {
    implementation 'io.github.hitoshura25:mpo-webauthn-android-client:X.X.X'
}
```

**E2E Testing with Staging Packages**:
- **PR Testing**: Uses staging packages (e.g., `pr-123.456`) for validation
- **Production**: Uses production packages from main branch
- **Version Resolution**: Automatically managed by GitHub Actions workflows

### 2. Open in Android Studio

1. Open Android Studio
2. Select "Open an existing Android Studio project"
3. Navigate to `android-test-client` directory
4. Click "OK"

### 3. Development Workflow

```bash
# Standard Android development
./gradlew build

# Run E2E tests with published client
./gradlew connectedAndroidTest

# Clean build
./gradlew clean build

# Local client library development (if needed)
cd ../android-client-library && ./gradlew publishToMavenLocal
```

## Configuration

### Server URL Configuration

The app is configured to connect to different server URLs based on build type:

- **Debug**: `http://10.0.2.2:8080` (Android emulator localhost)
- **Release**: `https://your-production-server.com` (configure as needed)

To change the server URL, modify the `buildConfigField` in `app/build.gradle`:

```gradle
buildTypes {
    debug {
        buildConfigField "String", "SERVER_URL", "\"http://your-server:8080\""
    }
}
```

### Emulator Setup

If using Android Emulator:
1. Start your WebAuthn server on localhost:8080
2. The emulator uses `10.0.2.2` to access the host machine's localhost
3. Make sure the server allows CORS for the Android app origin

## Usage

### Basic Flow

1. **Launch the App**: Install and run the app on device/emulator
2. **Registration**: 
   - Enter a username and display name
   - Tap "Register with WebAuthn"
   - Follow the biometric prompts (if using real WebAuthn)
3. **Authentication**:
   - Enter the registered username
   - Tap "Authenticate with WebAuthn"
   - Follow the biometric prompts
4. **View Logs**: Monitor the process in the logs section

### Mock vs Real WebAuthn

The current implementation includes mock credential creation for testing without actual biometric hardware. To enable real WebAuthn:

1. Remove the mock credential creation in `WebAuthnViewModel`
2. Implement proper FIDO2 API integration using the task results
3. Handle the WebAuthn intents properly

## Project Structure

```
android-test-client/
├── app/
│   ├── src/main/java/com/vmenon/mpo/authn/testclient/
│   │   ├── MainActivity.kt              # Main UI activity
│   │   └── WebAuthnViewModel.kt         # Business logic and API calls
│   ├── src/androidTest/                 # Instrumentation tests
│   └── src/test/                        # Unit tests
├── build.gradle.kts                     # Project configuration with published dependency
└── settings.gradle.kts                  # Repository configuration for GitHub Packages
```

**Published Client Library Structure**:
```
../android-client-library/               # Dedicated client library submodule
├── src/main/java/                       # Generated API client source
├── build.gradle.kts                     # Publishing configuration
└── README.md                            # Client library documentation
```

## Dependencies

### Core Android
- AndroidX Core, AppCompat, Material Design
- ViewBinding and ViewModel architecture
- Biometric library for fingerprint/face authentication

### WebAuthn/FIDO2
- Google Play Services FIDO library
- FIDO2 API client for WebAuthn operations

### API Client
- OkHttp for HTTP communication  
- Gson for JSON serialization
- Published Android client library from GitHub Packages

## Testing

### Run Unit Tests

```bash
./gradlew test
```

### Run Instrumentation Tests

```bash
./gradlew connectedAndroidTest
```

### Test Cases

The project includes tests for:
- Registration flow with valid credentials
- Authentication flow for existing users
- Server health check
- Error handling (invalid usernames, non-existent users)
- Mock credential creation

## Real WebAuthn Integration

To implement real WebAuthn instead of mocks:

### 1. Update Registration Flow

```kotlin
// In WebAuthnViewModel.registerUser()
val task = fido2ApiClient.getRegisterIntent(publicKeyCredentialCreationOptions)
task.addOnSuccessListener { intent ->
    // Launch intent for result
    activity.startActivityForResult(intent, REGISTER_REQUEST_CODE)
}
```

### 2. Handle WebAuthn Results

```kotlin
// In MainActivity.onActivityResult()
when (requestCode) {
    REGISTER_REQUEST_CODE -> {
        val credential = AuthenticatorAttestationResponse.deserializeFromBytes(
            data.getByteArrayExtra(Fido2ApiClient.KEY_RESPONSE_EXTRA)
        )
        // Process the real credential
    }
}
```

### 3. Update Authentication Flow

```kotlin
// Similar pattern for authentication
val task = fido2ApiClient.getSignIntent(publicKeyCredentialRequestOptions)
// Handle the assertion response
```

## Security Considerations

- **Network Security**: Uses cleartext traffic for development only
- **Credential Storage**: Generated client handles secure credential transmission
- **Biometric Data**: Processed entirely on-device by Android system
- **API Security**: Follows WebAuthn security best practices from server

## Troubleshooting

### Common Issues

1. **Server Connection Failed**
   - Check server is running on correct port
   - Verify emulator can reach host (use `10.0.2.2` for localhost)
   - Check CORS configuration on server

2. **Build Errors**
   - Check client library dependency is accessible: verify GitHub Packages authentication
   - Clean and rebuild: `./gradlew clean build`
   - Check if client version exists in GitHub Packages

3. **WebAuthn Errors**
   - Check device has biometric capability
   - Ensure user has enrolled biometrics
   - Verify app permissions for biometric access

### Debug Logging

Enable verbose logging in `WebAuthnViewModel` by modifying the log level:

```kotlin
private fun addLog(message: String) {
    Log.d("WebAuthnTest", message)  // Add Android logging
    // ... existing code
}
```

## Future Improvements

- **Real FIDO2 Integration**: Replace mock credentials with actual FIDO2 API
- **Credential Management**: Add credential listing and deletion features  
- **Advanced UI**: Material Design improvements and better UX flows
- **Error Recovery**: Better error handling and retry mechanisms
- **Offline Support**: Handle network failures gracefully
- **Security Enhancements**: Certificate pinning, request signing

## Related Documentation

- [Main Project README](../README.md)
- [Client Library Publishing](../docs/development/client-library-publishing.md)
- [WebAuthn Security Analysis](../docs/security/webauthn-analysis.md)
- [Android WebAuthn Guide](https://developers.google.com/identity/fido)
- [FIDO2 API Reference](https://developers.google.com/android/reference/com/google/android/gms/fido/fido2/api/common/package-summary)