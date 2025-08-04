# Publishing Credentials Configuration Fix

## 🔧 Problem Resolved

The Android client publishing was failing with the error:
```
The following Gradle properties are missing for 'GitHubPackages' credentials:
- GitHubPackagesUsername
- GitHubPackagesPassword
```

Additionally, the environment variable names were too generic (`USERNAME`, `TOKEN`) and needed to be more specific.

## ✅ Changes Made

### 1. Android Client Library Configuration

**File**: `android-test-client/client-library/build.gradle.kts`

**Updated credential resolution order:**
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

**Resolution Priority:**
1. **GitHubPackagesUsername/Password** (new specific Gradle properties)
2. **gpr.user/key** (legacy properties - still supported)
3. **ANDROID_PUBLISH_USER/TOKEN** (new specific environment variables)

### 2. GitHub Workflow Updates

**File**: `.github/workflows/client-e2e-tests.yml`

**Updated environment variables:**
```yaml
env:
  ANDROID_PUBLISH_USER: ${{ github.actor }}
  ANDROID_PUBLISH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Note**: Both Android and npm publishing now consolidated into `.github/workflows/client-e2e-tests.yml`

**Updated npm token reference:**
```yaml
env:
  NODE_AUTH_TOKEN: ${{ secrets.NPM_PUBLISH_TOKEN }}
```

### 3. Documentation Updates

**Updated Files:**
- `LIBRARY_USAGE.md` - Added new credential options with examples
- `GITHUB_PACKAGES_SETUP.md` - Updated authentication setup guide
- Android workflow PR comments - Updated with new credential setup

**New Authentication Options:**

**Gradle Properties (Preferred):**
```properties
GitHubPackagesUsername=your-github-username
GitHubPackagesPassword=your-github-token
```

**Environment Variables (CI/Local):**
```bash
export ANDROID_PUBLISH_USER=your-github-username
export ANDROID_PUBLISH_TOKEN=your-github-token
```

**Legacy (Still Supported):**
```properties
gpr.user=your-github-username
gpr.key=your-github-token
```

## 🚀 Benefits

### 1. **Specific Variable Names**
- `ANDROID_PUBLISH_USER/TOKEN` instead of generic `USERNAME/TOKEN`
- `NPM_PUBLISH_TOKEN` instead of generic `NPM_TOKEN`
- Prevents conflicts with other tools/scripts

### 2. **Multiple Authentication Methods**
- Gradle properties (preferred for development)
- Environment variables (preferred for CI)
- Legacy support maintained for existing setups

### 3. **Clear Resolution Order**
- Most specific → least specific
- New properties take precedence
- Fallback to legacy properties
- Final fallback to environment variables

### 4. **Better Error Messages**
- Gradle now properly recognizes `GitHubPackagesUsername/Password`
- Clear credential setup instructions in PR comments

## 🧪 Testing

**Local Test Command:**
```bash
cd android-test-client
ANDROID_PUBLISH_USER=test ANDROID_PUBLISH_TOKEN=test CLIENT_VERSION=1.0.0-test ./gradlew client-library:assembleRelease --dry-run
```

**Result**: ✅ Build successful with new credential configuration

## 📋 Required Secrets

For the GitHub workflows to work, ensure these secrets are set in the repository:

### Required Secrets:
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `NPM_PUBLISH_TOKEN` - npm registry token (for main branch publishing)

### Optional Secrets:
- If using a custom GitHub token instead of `GITHUB_TOKEN`, add it as `ANDROID_PUBLISH_TOKEN`

## 🔄 Migration Guide

### For Existing Users:

**No Action Required** - Legacy `gpr.user/gpr.key` properties still work.

**Recommended Migration:**
```bash
# Old way (still works)
gpr.user=username
gpr.key=token

# New way (preferred)
GitHubPackagesUsername=username
GitHubPackagesPassword=token
```

### For New Users:

Use the new specific property names for better clarity:

**In `gradle.properties`:**
```properties
GitHubPackagesUsername=your-github-username
GitHubPackagesPassword=your-github-token
```

**Or environment variables:**
```bash
export ANDROID_PUBLISH_USER=your-github-username
export ANDROID_PUBLISH_TOKEN=your-github-token
```

## ✅ Status

All credential configuration issues have been resolved:
- ✅ Android publishing credentials fixed
- ✅ Environment variable names made specific
- ✅ Documentation updated
- ✅ PR comments updated with correct setup instructions
- ✅ Backward compatibility maintained
- ✅ Multiple authentication methods supported

The publishing workflows should now work correctly on both main branch and PR publishing.