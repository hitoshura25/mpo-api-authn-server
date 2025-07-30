# Coding Standards

This document outlines the coding standards and conventions used in this project to ensure consistency, maintainability, and readability across all codebases.

## Import Standards

### ✅ Use Explicit Imports

**Always use explicit imports instead of wildcard imports** to improve code clarity and avoid naming conflicts.

### ✅ Remove Unused Imports

**Remove all unused imports** to keep code clean and avoid unnecessary dependencies.

#### ❌ Bad - Wildcard Imports
```kotlin
import com.vmenon.mpo.api.authn.client.model.*
import java.security.*
import io.ktor.server.application.*
```

#### ❌ Bad - Unused Imports
```kotlin
import io.ktor.server.application.Application
import io.ktor.server.application.install  // ← Unused import
import io.ktor.server.application.call
import java.io.Closeable  // ← Unused import

class MyService {
    fun configureApp(app: Application) {
        app.call.respond("Hello")  // install and Closeable never used
    }
}
```

#### ✅ Good - Explicit Imports Only What's Used
```kotlin
import com.vmenon.mpo.api.authn.client.model.RegistrationRequest
import com.vmenon.mpo.api.authn.client.model.RegistrationCompleteRequest
import com.vmenon.mpo.api.authn.client.model.AuthenticationRequest
import java.security.KeyPair
import java.security.SecureRandom
import java.security.Signature
import io.ktor.server.application.Application
import io.ktor.server.application.call

class MyService {
    fun configureApp(app: Application) {
        app.call.respond("Hello")  // All imports are used
    }
}
```

### Import Organization

Group imports logically with blank lines between groups:

```kotlin
// Standard library imports
import java.util.UUID
import java.security.KeyPair

// Third-party library imports  
import com.fasterxml.jackson.databind.ObjectMapper
import io.ktor.server.application.Application

// Project-specific imports
import com.vmenon.mpo.api.authn.client.model.RegistrationRequest
import com.vmenon.webauthn.testlib.WebAuthnTestAuthenticator
```

## Gradle Build Standards

### Version Management

**All dependency versions must be referenced via variables** to ensure consistency and ease of maintenance.

#### ✅ Good - Version Variables
```kotlin
// Version constants at the top of build.gradle.kts
val androidxCoreVersion = "1.12.0"
val lifecycleVersion = "2.7.0"
val webauthnVersion = "2.6.0"
val okhttpVersion = "4.12.0"

dependencies {
    implementation("androidx.core:core-ktx:$androidxCoreVersion")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:$lifecycleVersion")
    implementation("com.yubico:webauthn-server-core:$webauthnVersion")
    implementation("com.squareup.okhttp3:okhttp:$okhttpVersion")
}
```

#### ❌ Bad - Hardcoded Versions
```kotlin
dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")
    implementation("com.yubico:webauthn-server-core:2.6.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
```

### Dependency Organization

Dependencies must be organized in the following order:

1. **Non-test dependencies first** (logically grouped with descriptive comments)
2. **Test dependencies second** with specific order:
   - `testImplementation` (unit tests)
   - `androidTestImplementation` (instrumentation tests)

#### Example Structure
```kotlin
dependencies {
    // Android Core Libraries
    implementation("androidx.core:core-ktx:$androidxCoreVersion")
    implementation("androidx.appcompat:appcompat:$androidxAppCompatVersion")
    
    // WebAuthn/FIDO2 Support
    implementation("androidx.biometric:biometric:$biometricVersion")
    implementation("com.google.android.gms:play-services-fido:$playServicesFidoVersion")
    
    // JSON Processing
    implementation("com.google.code.gson:gson:$gsonVersion")
    
    // Unit Testing
    testImplementation("junit:junit:$junitVersion")
    testImplementation("org.mockito:mockito-core:$mockitoVersion")
    
    // Instrumentation Testing
    androidTestImplementation("androidx.test.ext:junit:$androidxTestJunitVersion")
    androidTestImplementation("androidx.test.espresso:espresso-core:$espressoVersion")
}
```

### Version Consistency

Related projects should use consistent library versions:

- **WebAuthn Core**: `2.6.0` across all projects
- **BouncyCastle**: `1.78` across all projects  
- **Jackson**: `2.16.1` across all projects
- **JUnit**: Context-appropriate versions (4.13.2 for Android, 5.11.3 for server)

## Build File Organization

### Structure Order
1. **Plugin declarations**
2. **Version constants** (grouped logically)
3. **Project configuration** (group, version, repositories)
4. **Android/Application configuration**
5. **Dependencies** (following dependency organization rules above)
6. **Tasks and additional configuration**

#### Example Template
```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Version constants
val androidxCoreVersion = "1.12.0"
val kotlinVersion = "1.9.23"
// ... other versions

android {
    namespace = "com.example.app"
    compileSdk = 34
    // ... configuration
}

dependencies {
    // Production dependencies
    // ... organized by function
    
    // Test dependencies  
    // ... testImplementation before androidTestImplementation
}
```

## Benefits of These Standards

### 1. **Maintainability**
- Version updates require changing only one location per build file
- Clear import statements prevent confusion about class origins
- No unused imports reduce maintenance overhead
- Consistent structure makes build files easier to navigate

### 2. **Consistency**
- All projects follow the same patterns
- Team members can quickly understand any build file
- Reduces cognitive load when switching between modules

### 3. **Reliability**
- Explicit imports prevent accidental usage of wrong classes
- No unused imports reduces potential for confusion and conflicts
- Version variables ensure compatibility across modules
- Organized dependencies make it easier to spot issues

### 4. **Code Review Efficiency**
- Clear imports make it obvious what dependencies are being introduced
- No unused imports mean every import has a purpose
- Consistent patterns make deviations immediately visible
- Standardized organization reduces review time

## Enforcement

These standards should be:
- ✅ Applied to all new code
- ✅ Verified during code reviews  
- ✅ Used when refactoring existing code
- ✅ Documented for all team members
- ✅ **CRITICAL**: Always test builds after removing imports to verify they weren't actually used

### Important Note on Unused Imports

**Always verify builds pass after removing imports.** Some imports may appear unused but are actually used in:
- DSL blocks (e.g., `routing { get("/path") }` uses `io.ktor.server.routing.get`)
- Extension functions called on receiver objects
- Type casting or interface implementations

**Process**: Remove suspected unused imports → Run build → If it fails, the import was actually needed → Add it back.

## Automated Linting with Detekt

The project uses **Detekt 1.23.7** for automated code quality checking, including style and formatting rules.

### Running Detekt

```bash
# Run detekt on specific module
./gradlew :webauthn-server:detekt
./gradlew :webauthn-test-service:detekt
./gradlew :webauthn-test-lib:detekt

# Run detekt on all modules
./gradlew detekt
```

### Configuration

Detekt is configured via `/detekt.yaml` with:
- **Import ordering** enforcement
- **Code formatting** rules (via ktlint integration)
- **Complexity analysis** with increased method length threshold (120 lines)
- **Style checking** including trailing spaces, newlines, and more

### Current Limitations

**Unused Import Detection**: While Detekt includes unused import rules, they may not detect all cases without type resolution enabled. The most reliable approach remains:

1. **IDE detection** (IntelliJ shows unused imports in gray)
2. **Manual verification** (remove import → run build → check if it fails)
3. **Code review** process to catch unused imports

### Reports

Detekt generates comprehensive reports in multiple formats:
- HTML: `build/reports/detekt/detekt.html`
- Markdown: `build/reports/detekt/detekt.md`
- XML: `build/reports/detekt/detekt.xml`

Following these standards ensures our codebase remains clean, maintainable, and professional as the project grows.