# Publishing Workflow Fixes V2 (Historical)

**Note**: The separate workflows described in this document have been **consolidated** into a single `client-e2e-tests.yml` workflow for improved efficiency and maintainability.

## 🚨 Issues Resolved (Historical Context)

### 1. Android Publishing - Gradle Properties Error
**Error**: `The following Gradle properties are missing for 'GitHubPackages' credentials: GitHubPackagesUsername, GitHubPackagesPassword`

**Root Cause**: Environment variables were set but not passed as Gradle properties to the build command.

**Fix**: Explicitly pass Gradle properties in the workflow:
```bash
./gradlew client-library:assembleRelease client-library:publish \
  -PGitHubPackagesUsername="${ANDROID_PUBLISH_USER}" \
  -PGitHubPackagesPassword="${ANDROID_PUBLISH_TOKEN}" \
  -PclientVersion="${CLIENT_VERSION}" \
  --info
```

### 2. npm Publishing - GitHub Packages Permissions Error  
**Error**: `Permission installation not allowed to Create organization package`

**Root Cause**: Missing `packages: write` permission and incorrect package scoping for GitHub Packages.

**Fixes Applied**:
1. **Added proper permissions**:
```yaml
permissions:
  contents: read
  packages: write
  pull-requests: write
  id-token: write
```

2. **Fixed package scoping**:
   - **PRs**: `@hitoshura25/mpo-webauthn-client` (scoped to repository owner)
   - **Main**: `@vmenon25/mpo-webauthn-client` (public npm)

3. **Added proper publishConfig**:
   - **PRs**: `"registry": "https://npm.pkg.github.com"`
   - **Main**: `"access": "public"`

## ✅ Changes Made

### Android Workflow (consolidated into `.github/workflows/client-e2e-tests.yml`)

1. **Added workflow-level permissions**:
```yaml
permissions:
  contents: read
  packages: write
  pull-requests: write
  id-token: write
```

2. **Updated build command with explicit Gradle properties**:
```bash
./gradlew client-library:assembleRelease client-library:publish \
  -PGitHubPackagesUsername="${ANDROID_PUBLISH_USER}" \
  -PGitHubPackagesPassword="${ANDROID_PUBLISH_TOKEN}" \
  -PclientVersion="${CLIENT_VERSION}" \
  --info
```

3. **Enhanced PR comment with proper credential setup**:
   - Shows both environment variable and Gradle property options
   - Includes complete repository configuration

### npm Workflow (consolidated into `.github/workflows/client-e2e-tests.yml`)

1. **Added workflow-level permissions** (same as Android)

2. **Simplified package.json generation**:
   - Single conditional block for PR vs main branch 
   - Proper publishConfig for each target registry
   - Correct package scoping for GitHub Packages

3. **Fixed package naming**:
   - **PR packages**: `@{repository_owner}/mpo-webauthn-client`
   - **Production packages**: `@vmenon25/mpo-webauthn-client`

4. **Updated secret reference**:
   - Changed from generic `NPM_TOKEN` to specific `NPM_PUBLISH_TOKEN`

### Android Client Library (`android-test-client/client-library/build.gradle.kts`)

**Already had correct configuration** with fallback order:
```kotlin
credentials {
    username = project.findProperty("GitHubPackagesUsername") as String? 
        ?: project.findProperty("gpr.user") as String? 
        ?: System.getenv("ANDROID_PUBLISH_USER")
    password = project.findProperty("GitHubPackagesPassword") as String? 
        ?: project.findProperty("gpr.key") as String? 
        ?: System.getenv("ANDROID_PUBLISH_TOKEN")
}
```

## 🧪 Testing Verification

### Android Build Test
```bash
cd android-test-client 
./gradlew client-library:assembleRelease \
  -PGitHubPackagesUsername=test \
  -PGitHubPackagesPassword=test \
  -PclientVersion=1.0.0-test \
  --dry-run
```
**Result**: ✅ `BUILD SUCCESSFUL` - Properties are now recognized

### Workflow Permissions
Both workflows now have:
- ✅ `contents: read` - For repository access
- ✅ `packages: write` - For GitHub Packages publishing
- ✅ `pull-requests: write` - For PR comments  
- ✅ `id-token: write` - For OIDC authentication

## 📋 Required Repository Configuration

### GitHub Secrets
1. **`GITHUB_TOKEN`** - ✅ Automatically provided by GitHub Actions
2. **`NPM_PUBLISH_TOKEN`** - ⚠️ **Required**: npm registry token for main branch publishing

### Repository Settings
1. **Actions > General > Workflow permissions**: 
   - ✅ Set to "Read and write permissions"
   - ✅ "Allow GitHub Actions to create and approve pull requests" enabled

2. **GitHub Packages**:
   - ✅ Should be automatically enabled for the repository
   - ✅ Packages will be visible under repository "Packages" tab

## 🔍 Publishing Flow

### Pull Request Publishing
1. **Triggers**: PR opened/updated with OpenAPI changes
2. **Android**: Publishes to GitHub Packages as `1.0.0-pr.42.123` (with enhanced regex validation)
3. **npm**: Publishes to GitHub Packages as `@hitoshura25/mpo-webauthn-client@1.0.0-pr.42.123`
4. **Comments**: Bot adds installation instructions to PR

### Main Branch Publishing  
1. **Triggers**: Push to main branch with OpenAPI changes
2. **Android**: Publishes to GitHub Packages as `1.0.26`, `1.0.27` (3-part with enhanced validation)
3. **npm**: Publishes to public npm as `@vmenon25/mpo-webauthn-client@1.0.26`, `@vmenon25/mpo-webauthn-client@1.0.27`
4. **Releases**: Creates GitHub releases for production versions

## 🎯 Next Steps

1. **Add `NPM_PUBLISH_TOKEN` secret** to repository settings
2. **Test PR publishing** by creating a PR with OpenAPI changes
3. **Verify packages** appear in GitHub Packages section
4. **Test main branch publishing** after merging PR

## 📊 Expected Outcomes

### PR Publishing Test
- ✅ Android client publishes without credential errors
- ✅ npm client publishes to GitHub Packages without permission errors
- ✅ PR receives bot comments with installation instructions
- ✅ Packages visible under repository Packages tab

### Main Branch Publishing
- ✅ Android client publishes to GitHub Packages  
- ✅ npm client publishes to public npm registry
- ✅ GitHub releases created with installation instructions
- ✅ Production packages available for external use

All publishing credential and permission issues should now be resolved!