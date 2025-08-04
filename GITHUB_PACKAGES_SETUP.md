# GitHub Packages Setup for Android Client Publishing

This document explains how to set up and use the automated GitHub workflow that publishes Android client libraries to GitHub Packages with PR-aware versioning.

## 🔄 Workflow Overview

The workflow automatically:
- **Detects API changes** in OpenAPI specs or build configuration
- **Generates versions** based on branch/PR context
- **Builds and publishes** Android client to GitHub Packages
- **Creates releases** for main branch publications
- **Comments on PRs** with usage instructions
- **Updates test client** dependency automatically

## 📦 Versioning Scheme

### Main Branch (Production)
- **Format**: `1.0.0`, `1.1.0`, `1.2.0`
- **Trigger**: Push to `main` branch
- **Creates**: GitHub Release
- **Example**: `com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0`

### Pull Requests
- **Format**: `1.0.0-pr-123.1`, `1.0.0-pr-123.2`
- **Trigger**: PR opened/updated
- **Creates**: Prerelease package + PR comment
- **Example**: `com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0-pr-123.1`

### Feature Branches
- **Format**: `1.0.0-feature-branch.1`, `1.0.0-develop.2`
- **Trigger**: Push to non-main branches
- **Creates**: Prerelease package
- **Example**: `com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0-develop.15`

## 🚀 Repository Setup

### 1. Enable GitHub Packages

Ensure your repository has GitHub Packages enabled:

1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select **Read and write permissions**
3. Check **Allow GitHub Actions to create and approve pull requests**

### 2. Update Base Version (Optional)

To change the base version, edit `.github/workflows/client-e2e-tests.yml`:

```yaml
env:
  BASE_VERSION: "2.0.0"  # Change this to your desired base version
```

### 3. Configure Repository Secrets (Optional)

The workflow uses `GITHUB_TOKEN` automatically. For additional security, you can create a dedicated token:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add `PACKAGES_TOKEN` with a Personal Access Token that has `write:packages` permission

## 📱 Using Published Packages

### For Android Projects

Add to your `build.gradle`:

```gradle
repositories {
    maven {
        name = "GitHubPackages"
        url = uri("https://maven.pkg.github.com/YOUR_ORG/YOUR_REPO")
        credentials {
            username = project.findProperty("GitHubPackagesUsername") ?: project.findProperty("gpr.user") ?: System.getenv("ANDROID_PUBLISH_USER")
            password = project.findProperty("GitHubPackagesPassword") ?: project.findProperty("gpr.key") ?: System.getenv("ANDROID_PUBLISH_TOKEN")
        }
    }
}

dependencies {
    // Production version
    implementation 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0'
    
    // PR version (for testing)
    implementation 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0-pr-123.1'
}
```

### Authentication Setup

#### Option 1: Environment Variables (Preferred)
```bash
export ANDROID_PUBLISH_USER=your-github-username
export ANDROID_PUBLISH_TOKEN=your-github-token
```

#### Option 2: Gradle Properties (New)
Create `~/.gradle/gradle.properties` or project `gradle.properties`:
```properties
GitHubPackagesUsername=your-github-username
GitHubPackagesPassword=your-github-token
```

#### Option 3: Legacy Gradle Properties (Still Supported)
Create `~/.gradle/gradle.properties` or project `gradle.properties`:
```properties
gpr.user=your-github-username
gpr.key=your-github-token
```

## 🔧 Workflow Triggers

### Automatic Triggers
- **API Changes**: Workflow runs when OpenAPI specs or build config changes
- **PR Updates**: New versions published for each PR synchronization
- **Main Branch**: Production releases created automatically

### Manual Triggers
```bash
# Force publish regardless of changes
gh workflow run client-e2e-tests.yml
```

## 📋 Workflow Jobs

### 1. `detect-changes`
- Analyzes file changes to determine if publishing is needed
- Checks OpenAPI specs, build config, and workflow files
- Outputs decision for downstream jobs

### 2. `generate-version`
- Creates appropriate version number based on context
- Handles main branch, PR, and feature branch scenarios
- Determines if version should be marked as prerelease

### 3. `build-and-publish`
- Generates Android client from OpenAPI spec
- Configures GitHub Packages publishing
- Builds and publishes the library
- Creates GitHub releases for production versions

### 4. `update-android-test-client`
- Automatically updates test client dependency version
- Commits changes back to PR branch
- Ensures test client always uses latest generated client

### 5. `summary`
- Provides workflow execution summary
- Helpful for debugging and monitoring

## 🔍 Monitoring and Debugging

### View Published Packages
- Go to your repository → **Packages** tab
- Find `mpo-webauthn-android-client` package
- View all published versions and download statistics

### Check Workflow Runs
- Go to **Actions** tab in your repository
- Select "Generate and Publish Android Client" workflow
- Review logs for each job

### Common Issues

#### Authentication Errors
```
401 Unauthorized when publishing to GitHub Packages
```
**Solution**: Verify GitHub token has `write:packages` permission

#### Version Conflicts
```
Version already exists
```
**Solution**: This is normal - workflow skips publishing if version exists

#### Build Failures
```
OpenAPI generation failed
```
**Solution**: Check OpenAPI spec syntax and build configuration

## 📚 Integration Examples

### Testing PR Versions

When a PR is created, the bot comments with usage instructions:

```gradle
dependencies {
    // Test the PR version
    implementation 'com.vmenon.mpo.api.authn:mpo-webauthn-android-client:1.0.0-pr-42.1'
}
```

### Gradle Version Catalogs

`gradle/libs.versions.toml`:
```toml
[versions]
webauthn-client = "1.0.0"

[libraries]
webauthn-android = { module = "com.vmenon.mpo.api.authn:mpo-webauthn-android-client", version.ref = "webauthn-client" }
```

### Dependabot Updates

`.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "gradle"
    directory: "/"
    schedule:
      interval: "weekly"
    allow:
      - dependency-name: "com.vmenon.mpo.api.authn:mpo-webauthn-android-client"
```

## 🛡️ Security Considerations

- Packages are published to your organization's GitHub Packages
- Access is controlled by repository permissions
- Tokens are handled securely through GitHub Secrets
- PR versions allow safe testing without affecting production

## 📖 Related Documentation

- [Client Generation Guide](CLIENT_GENERATION.md)
- [Android Test Client README](android-test-client/README.md)
- [GitHub Packages Documentation](https://docs.github.com/en/packages)
- [OpenAPI Generator Documentation](https://openapi-generator.tech/)