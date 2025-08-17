# Cleanup Script Configuration Update Summary

## Changes Made

Updated `scripts/docker/cleanup-staging-packages.sh` to use configurable values instead of hardcoded ones, integrating with the existing central configuration system in `config/publishing-config.yml`.

## Addressed GitHub Copilot Feedback

✅ **Hardcoded scope 'vmenon25'** → Now loaded from `packages.typescript.scope` with `TYPESCRIPT_SCOPE` override
✅ **Hardcoded package name 'mpo-webauthn-client-staging'** → Now constructed from `packages.typescript.basePackageName` + `naming.staging.npmSuffix` with overrides
✅ **Hardcoded Maven package name** → Now constructed from `packages.android.groupId` + `packages.android.baseArtifactId` + `naming.staging.androidSuffix` with overrides  
✅ **Hardcoded Docker package names** → Now configurable via environment variables with defaults

## New Configuration Loading

### Central Configuration Integration
- Loads configuration from `config/publishing-config.yml` using `yq`
- Supports environment variable overrides for all values
- Validates configuration completeness with detailed error messages
- Maintains backward compatibility with environment-only configuration

### Configuration Variables Loaded
- `ANDROID_GROUP_ID` (from `packages.android.groupId`)
- `ANDROID_BASE_ARTIFACT_ID` (from `packages.android.baseArtifactId`)
- `TYPESCRIPT_SCOPE` (from `packages.typescript.scope`)
- `TYPESCRIPT_BASE_PACKAGE_NAME` (from `packages.typescript.basePackageName`)
- `ANDROID_STAGING_SUFFIX` (from `naming.staging.androidSuffix`)
- `NPM_STAGING_SUFFIX` (from `naming.staging.npmSuffix`)
- `AUTHOR_ID` (from `metadata.author.id`)

### Docker Image Configuration
- `DOCKER_WEBAUTHN_IMAGE_NAME` (environment variable, default: "webauthn-server")
- `DOCKER_TEST_CREDENTIALS_IMAGE_NAME` (environment variable, default: "webauthn-test-credentials-service")

### Package Name Construction
- **Android Staging Package**: `${ANDROID_GROUP_ID}.${ANDROID_BASE_ARTIFACT_ID}${ANDROID_STAGING_SUFFIX}`
- **npm Staging Package**: `${TYPESCRIPT_BASE_PACKAGE_NAME}${NPM_STAGING_SUFFIX}`
- **npm Scope Clean**: `${TYPESCRIPT_SCOPE}` (with @ prefix removed for URL encoding)

## Updated Workflow Integration

Modified `.github/workflows/main-ci-cd.yml` to pass Docker image name environment variables:
```yaml
env:
  DOCKER_WEBAUTHN_IMAGE_NAME: "webauthn-server"
  DOCKER_TEST_CREDENTIALS_IMAGE_NAME: "webauthn-test-credentials-service"
```

## Error Handling & Validation

- **Configuration File Missing**: Script fails with clear error message
- **yq Not Available**: Script fails with dependency error  
- **Invalid Configuration Values**: Script validates all required fields and reports specific missing values
- **Environment Override Support**: All configuration values can be overridden via environment variables
- **Preserve Override**: Emergency preserve functionality works before configuration loading

## Benefits Achieved

1. **Single Source of Truth**: All package names controlled from central configuration
2. **Maintainability**: No need to update multiple files when changing package names/scopes
3. **Flexibility**: Environment variable overrides for CI/testing scenarios
4. **Consistency**: Same configuration system used by publishing workflows
5. **Validation**: Comprehensive error checking with specific failure messages
6. **Backward Compatibility**: Existing functionality preserved with environment-only configuration

## Testing Results

✅ Configuration loading from YAML file works correctly
✅ Environment variable overrides function properly
✅ Constructed package names match expected format
✅ Script syntax validation passes
✅ Emergency preserve override works with any configuration state
✅ All hardcoded values successfully eliminated

## Configuration Example

Current values loaded from `config/publishing-config.yml`:
- Android Staging Package: `io.github.hitoshura25.mpo-webauthn-android-client-staging`
- npm Staging Package: `mpo-webauthn-client-staging`
- npm Scope: `vmenon25` (cleaned from `@vmenon25`)
- Docker Images: `webauthn-server`, `webauthn-test-credentials-service`