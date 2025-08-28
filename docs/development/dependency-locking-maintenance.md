# Gradle Dependency Locking - Implementation & Maintenance Guide

## Overview

This project implements comprehensive Gradle dependency locking across all 6 modules to enhance supply chain security by ensuring exact dependency versions are used consistently across all builds and environments.

## Implementation Summary

### Modules with Dependency Locking Enabled

1. **Root Project** (`/build.gradle.kts`) - Applies locking to all subprojects
2. **webauthn-server** (`/webauthn-server/build.gradle.kts`) - Main WebAuthn server
3. **webauthn-test-credentials-service** (`/webauthn-test-credentials-service/build.gradle.kts`) - Test credentials service
4. **webauthn-test-lib** (`/webauthn-test-lib/build.gradle.kts`) - Shared test library
5. **android-test-client** (`/android-test-client/build.gradle.kts`) - Android project root
6. **android-client-library** (template: `/android-client-library/build.gradle.kts.template`) - Generated client library

### Configuration Applied

Each module includes this configuration block:
```kotlin
// Dependency locking configuration for supply chain security
// Ensures exact dependency versions are used across builds
dependencyLocking {
    lockAllConfigurations()
}
```

### Generated Lockfiles

The following `gradle.lockfile` files are generated and version-controlled:
- `/webauthn-server/gradle.lockfile`
- `/webauthn-test-credentials-service/gradle.lockfile` 
- `/webauthn-test-lib/gradle.lockfile`
- `/android-test-client/app/gradle.lockfile`

## Security Benefits

1. **Supply Chain Protection**: Prevents dependency confusion and substitution attacks
2. **Reproducible Builds**: Guarantees identical dependency versions across environments
3. **Vulnerability Scanning Enhancement**: Enables OSV-Scanner and Dependabot to scan exact locked versions
4. **Change Detection**: Alerts when dependency versions change unexpectedly

## Maintenance Procedures

### When Adding New Dependencies

When you add new dependencies to any module:

1. **Add the dependency** to the appropriate `build.gradle.kts` file
2. **Update lockfiles** by running:
   ```bash
   ./gradlew dependencies --write-locks
   ```
3. **For specific modules**, target the module:
   ```bash
   ./gradlew :webauthn-server:dependencies --write-locks
   ./gradlew :webauthn-test-lib:dependencies --write-locks
   ./gradlew :webauthn-test-credentials-service:dependencies --write-locks
   ```
4. **For Android modules**:
   ```bash
   cd android-test-client && ./gradlew app:dependencies --write-locks
   ```
5. **Commit the updated lockfiles** with your code changes

### When Updating Existing Dependencies

To update dependency versions:

1. **Update version numbers** in build.gradle.kts files
2. **Regenerate lockfiles**:
   ```bash
   ./gradlew dependencies --write-locks
   ```
3. **Verify build still works**:
   ```bash
   ./gradlew clean build -x test
   ```
4. **Run tests** to ensure compatibility:
   ```bash
   ./gradlew test
   ```
5. **Commit both version changes and lockfile updates**

### Bulk Dependency Updates

For major dependency updates across multiple modules:

1. **Update all version constants** in build.gradle.kts files
2. **Clear existing locks and regenerate**:
   ```bash
   # Remove old lockfiles
   find . -name "gradle.lockfile" -delete
   
   # Regenerate all lockfiles
   ./gradlew dependencies --write-locks
   cd android-test-client && ./gradlew dependencies --write-locks
   ```
3. **Validate all modules build**:
   ```bash
   ./gradlew clean build
   ```
4. **Test thoroughly** before committing

### Resolving Lock Conflicts

If you encounter dependency resolution conflicts:

1. **Review the error message** for conflicting versions
2. **Update dependency constraints** in build.gradle.kts if needed
3. **Regenerate lockfiles**:
   ```bash
   ./gradlew dependencies --write-locks
   ```
4. **For persistent conflicts**, use dependency constraints:
   ```kotlin
   dependencies {
       constraints {
           implementation("com.example:library:exact-version") {
               because("Resolve version conflict with reason")
           }
       }
   }
   ```

### Android Client Library Special Handling

The android-client-library uses a template system:

1. **Template file**: `/android-client-library/build.gradle.kts.template` includes dependency locking
2. **Generated file**: The actual build.gradle.kts is generated from the template
3. **When updating**: Modify the template, then run client generation:
   ```bash
   ./gradlew generateAndroidClient copyAndroidClientToSubmodule
   ```

## Verification Commands

### Check Current Lock Status
```bash
# View current locked versions for a module
./gradlew :webauthn-server:dependencies --configuration=compileClasspath

# Check if lockfiles are up-to-date
./gradlew dependencies --write-locks --dry-run
```

### Validate Locking is Working
```bash
# Build should succeed with existing lockfiles
./gradlew build

# Should fail if lockfiles are missing (after deletion)
rm webauthn-server/gradle.lockfile && ./gradlew :webauthn-server:build
```

### Integration with Security Tools

The locked dependencies enhance security scanning:

1. **OSV-Scanner**: Scans exact versions in lockfiles for known vulnerabilities
2. **Dependabot**: Monitors locked versions for security updates
3. **FOSS Security Tools**: Can analyze precise dependency trees

## CI/CD Integration

Lockfiles work seamlessly with existing CI/CD:

1. **Build Performance**: No impact on build times
2. **Configuration Cache**: Compatible with Gradle configuration cache
3. **Parallel Builds**: Works with parallel module builds
4. **Security Workflows**: Enhances existing security scanning workflows

## Troubleshooting

### Common Issues and Solutions

#### "Could not resolve dependencies" Error
- **Cause**: Lockfile references a version that's no longer available
- **Solution**: Regenerate lockfiles with `--write-locks`

#### Build Works Locally But Fails in CI
- **Cause**: Lockfiles not committed or out of sync
- **Solution**: Ensure all gradle.lockfile files are version-controlled

#### Android Build Issues
- **Cause**: Android project has separate lockfiles
- **Solution**: Generate Android lockfiles from android-test-client directory

#### Dependency Constraints vs Locking Conflicts
- **Cause**: Version constraints conflict with locked versions
- **Solution**: Update constraints first, then regenerate locks

### Performance Considerations

- **First Build**: Slightly slower due to lockfile validation
- **Subsequent Builds**: Same performance as before
- **Memory Usage**: Minimal impact on build memory
- **Cache Compatibility**: Fully compatible with Gradle build cache

## Best Practices

1. **Always commit lockfiles** with dependency changes
2. **Regenerate locks** after major dependency updates
3. **Test thoroughly** after lockfile changes
4. **Document reasons** for version constraints
5. **Regular maintenance**: Update dependencies periodically for security
6. **Monitor security alerts** on locked versions

## Integration with Existing Workflows

This implementation integrates seamlessly with:
- Existing FOSS security implementation
- OpenAPI client generation workflows
- Multi-platform testing pipelines
- Maven Central and GitHub Packages publishing

## Next Steps

1. **Monitor security alerts** on locked dependency versions
2. **Establish regular dependency update schedule**
3. **Configure automated security scanning** of lockfiles
4. **Consider dependency update automation** for security patches

## Related Documentation

- [FOSS Security Implementation](../improvements/in-progress/foss-security-implementation.md)
- [Gradle Configuration Cache Compatibility](gradle-configuration-cache-compatibility.md)
- [Dependency Variant Selection](dependency-variant-selection.md)