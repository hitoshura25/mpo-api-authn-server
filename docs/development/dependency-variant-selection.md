# Dependency Variant Selection for Server Projects

## Overview

When developing server applications in this project, it's critical to ensure you're using appropriate dependency variants. Gradle's conflict resolution can sometimes select Android-optimized variants even for server projects, leading to suboptimal performance.

## Problem: Android Variants in Server Projects

### Root Cause
Multiple dependencies may request different variants of the same library:
- **Yubico WebAuthn**: Uses version ranges `[24.1.1,33)`
- **Swagger Libraries**: May request specific Android variants  
- **JSON Schema Libraries**: Often request older Android variants
- **Gradle Resolution**: Selects highest version, which may be Android variant

### Example Issue
```kotlin
// These dependencies create a conflict:
implementation("com.yubico:webauthn-server-core:2.6.0")        // guava:[24.1.1,33)
implementation("io.swagger:swagger-core:1.6.10")               // guava:31.1-android
implementation("io.swagger.codegen.v3:swagger-codegen:3.0.41") // guava:31.0.1-jre

// Result: Gradle selects 31.1-android (wrong for servers!)
```

## Solution: Explicit Variant Constraints

### Implementation Pattern
Add dependency constraints to `build.gradle.kts`:

```kotlin
dependencies {
    constraints {
        implementation("com.google.guava:guava:31.1-jre") {
            because(
                "Pin Guava JRE version for server environment, avoiding version ranges and Android variants"
            )
        }
    }
    
    // Your normal dependencies...
}
```

### Detection Commands

**Check Current Selection:**
```bash
./gradlew :webauthn-server:dependencyInsight --dependency=com.google.guava:guava --configuration=runtimeClasspath
```

**Find Android Variants (should be empty for server projects):**
```bash
./gradlew :webauthn-server:dependencies --configuration=runtimeClasspath | grep android
```

**Validate Configuration Cache Works:**
```bash
./gradlew :webauthn-server:shadowJar --configuration-cache
./gradlew :webauthn-server:shadowJar --configuration-cache  # Should show "Reusing configuration cache."
```

## Benefits of JRE Variants

### Performance
- **JRE variants**: Optimized for standard JVM server environments
- **Android variants**: Optimized for Android's constrained runtime environment

### Compatibility  
- **Better framework integration**: Works optimally with Ktor, Spring, etc.
- **Server-specific optimizations**: Memory management, threading, class loading

### Build Performance
- **Configuration Cache Stability**: Pinned versions prevent cache invalidation
- **Predictable Resolution**: No unexpected variant switches during builds

## Project-Specific Rules

### Server Projects (Use JRE variants)
- `webauthn-server/` - Main WebAuthn server
- `webauthn-test-credentials-service/` - Test credentials service

### Client Projects (May use Android variants)
- `android-test-client/` - Android E2E test client
- `android-client-library/` - Android client library

### Shared Libraries (Use JRE variants)
- `webauthn-test-lib/` - Shared test utilities

## Historical Context

This guidance was added in August 2025 after discovering that Gradle was selecting `com.google.guava:guava:31.1-android` for the webauthn-server project due to conflict resolution, despite the project being a pure server application.

The issue was causing:
1. **Suboptimal performance** - Android-optimized runtime behavior in server environment  
2. **Configuration cache instability** - Version ranges were causing cache invalidation
3. **Unexpected dependency selection** - Android variants selected without explicit intent

## Validation Checklist

When adding new dependencies to server projects:

- [ ] Run dependency insight to check for Android variants
- [ ] Add constraints for any Android variants found in server projects
- [ ] Test configuration cache functionality
- [ ] Document any new variant selection constraints
- [ ] Verify no performance regression in CI/CD builds

## Related Documentation

- [Gradle Configuration Cache Compatibility](./gradle-configuration-cache-compatibility.md)
- [Server Development Best Practices](../CLAUDE.md#server-development-best-practices)
- [Dependency Management Patterns](./README.md)