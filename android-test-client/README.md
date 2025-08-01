# Android WebAuthn Test Client

This is an Android test client for the MPO WebAuthn authentication server. It uses the OpenAPI-generated client library to demonstrate WebAuthn registration and authentication flows on Android.

## Features

- **WebAuthn Registration**: Register new users with FIDO2/WebAuthn credentials
- **WebAuthn Authentication**: Authenticate existing users using biometric/security key
- **Real-time Logging**: View detailed logs of the authentication process
- **Error Handling**: Comprehensive error handling and user feedback
- **Generated API Client**: Uses OpenAPI-generated client for type-safe API communication

## Prerequisites

- Android Studio Arctic Fox or later
- Android SDK API level 26+ (Android 8.0)
- Device or emulator with biometric capability (for real WebAuthn)
- MPO WebAuthn server running (see main project README)

## Setup

### 1. Build with Generated Client

The Android test client uses the OpenAPI-generated client as a Maven dependency. Use the provided build script:

```bash
# From android-test-client directory - builds client first, then app
./build-with-client.sh
```

This script:
1. Generates the Android API client from OpenAPI spec
2. Builds and publishes it to local Maven repository  
3. Builds the Android test client with the dependency

### 2. Open in Android Studio

1. Open Android Studio
2. Select "Open an existing Android Studio project"
3. Navigate to `android-test-client` directory
4. Click "OK"

### 3. Development Workflow

```bash
# When API changes - rebuild everything
./build-with-client.sh

# For app-only changes - faster build
./gradlew build

# Clean build
./gradlew clean build
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
├── generated-client/                    # OpenAPI-generated client
└── build.gradle                         # Project configuration
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
- OpenAPI-generated client library

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
   - Ensure generated client exists: `./gradlew generateAndroidClient`
   - Clean and rebuild: `./gradlew clean build`

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
- [Client Generation Guide](../CLIENT_GENERATION.md)
- [WebAuthn Security Analysis](../WEBAUTHN_SECURITY_ANALYSIS.md)
- [Android WebAuthn Guide](https://developers.google.com/identity/fido)
- [FIDO2 API Reference](https://developers.google.com/android/reference/com/google/android/gms/fido/fido2/api/common/package-summary)