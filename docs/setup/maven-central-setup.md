# Maven Central Publishing Setup

This document explains how to configure Maven Central publishing for the Android client library.

## Required Secrets

For production publishing to Maven Central, the following GitHub repository secrets must be configured:

### Central Portal Credentials
- **`CENTRAL_PORTAL_USERNAME`**: Your Central Portal user token username
- **`CENTRAL_PORTAL_PASSWORD`**: Your Central Portal user token password

### GPG Signing
- **`SIGNING_KEY`**: Your GPG private key in ASCII armored format
- **`SIGNING_PASSWORD`**: The password for your GPG private key

## Setup Process

### 1. Create Central Portal Account
1. Visit [Central Portal](https://central.sonatype.com)
2. Create an account
3. Verify your namespace (`io.github.hitoshura25`) - for GitHub namespaces this is usually automatic

### 2. Generate GPG Key

GPG (GNU Privacy Guard) signing is required by Maven Central to ensure artifact authenticity and integrity. Every artifact (JAR, sources, javadoc) must be cryptographically signed.

#### Why GPG Signing is Required
- **Authenticity**: Proves artifacts come from the verified publisher
- **Integrity**: Ensures artifacts haven't been tampered with during transit
- **Trust**: Maven Central policy requires signatures for all artifacts
- **Security**: Protects consumers from malicious or corrupted packages

#### What Gets Signed
When publishing to Maven Central, these artifacts are automatically signed:
- Main JAR file (compiled classes)
- Sources JAR (source code)
- Javadoc JAR (API documentation)
- POM file (project metadata)

#### GPG Key Generation Process
```bash
# Generate a new GPG key (interactive process)
gpg --gen-key

# Follow the prompts:
# 1. Select RSA and RSA (default)
# 2. Key size: 4096 bits (recommended for security)
# 3. Expiration: 2 years (or your preference)
# 4. Enter your real name and email
# 5. Create a secure passphrase

# List your keys to find the KEY_ID
gpg --list-secret-keys --keyid-format LONG

# Example output:
# sec   rsa4096/ABC123DEF456 2024-01-01 [SC] [expires: 2026-01-01]
#       1234567890ABCDEF1234567890ABCDEF12345678
# uid                 [ultimate] Your Name <your.email@example.com>
# ssb   rsa4096/GHI789JKL012 2024-01-01 [E] [expires: 2026-01-01]

# The KEY_ID is the part after the slash: ABC123DEF456

# Export the private key in ASCII format (for GitHub Secrets)
gpg --armor --export-secret-keys ABC123DEF456

# Export the public key and upload to keyserver (for public verification)
gpg --armor --export ABC123DEF456
gpg --keyserver keyserver.ubuntu.com --send-keys ABC123DEF456
```

#### Gradle Signing Configuration
Our build configuration handles GPG signing automatically:

```kotlin
signing {
    // Only sign if we have the required properties (for production publishing)
    val signingKey = project.findProperty("signingKey") as String? ?: System.getenv("SIGNING_KEY")
    val signingPassword = project.findProperty("signingPassword") as String? ?: System.getenv("SIGNING_PASSWORD")

    if (signingKey != null && signingPassword != null) {
        useInMemoryPgpKeys(signingKey, signingPassword)  // In-memory signing
        sign(publishing.publications["maven"])            // Sign all publication artifacts
    }
}
```

#### How It Works in GitHub Actions
1. **Secret Storage**: Private key stored securely in GitHub repository secrets
2. **In-Memory Loading**: Key loaded into memory during build (never written to disk)
3. **Automatic Signing**: Gradle signing plugin signs each artifact during publish
4. **Verification**: Maven Central verifies signatures against uploaded public key

#### Security Best Practices
- **Strong Passphrase**: Use a complex passphrase for your GPG key
- **Key Expiration**: Set reasonable expiration dates (1-2 years)
- **Secret Rotation**: Regularly rotate keys and update GitHub secrets
- **Backup Strategy**: Securely backup your private key
- **Limited Scope**: Only use signing keys for artifact publishing

#### Troubleshooting Common Issues
- **"No secret key" error**: Ensure `SIGNING_KEY` secret contains the full ASCII armored private key
- **"Bad passphrase" error**: Verify `SIGNING_PASSWORD` matches your GPG key passphrase
- **"Key not found" error**: Check that you're using the correct KEY_ID format
- **Upload failures**: Ensure public key is uploaded to keyserver before first publish

### 3. Generate Central Portal User Token
1. Log in to [Central Portal](https://central.sonatype.com)
2. Go to Account settings
3. Generate a new User Token
4. Save the token username and password

### 4. Configure GitHub Secrets
Add the following secrets to your GitHub repository:
- `CENTRAL_PORTAL_USERNAME`: Your Central Portal user token username
- `CENTRAL_PORTAL_PASSWORD`: Your Central Portal user token password  
- `SIGNING_KEY`: The ASCII armored private key (entire output from export command)
- `SIGNING_PASSWORD`: The passphrase for your GPG key

## Publishing Types

### Staging (GitHub Packages)
- **Registry**: GitHub Packages (`maven.pkg.github.com`)
- **Artifacts**: `mpo-webauthn-android-client-staging`
- **Authentication**: `GITHUB_TOKEN` (automatic)
- **Usage**: Internal testing, PR validation

### Production (Maven Central)
- **Registry**: Maven Central (`ossrh-staging-api.central.sonatype.com`)
- **Artifacts**: `mpo-webauthn-android-client`
- **Authentication**: Central Portal user token + GPG signing
- **Usage**: Public releases

## Gradle Configuration

The Android client library uses **conditional publishing** - only one repository is configured at build time based on the `publishType` property:

```kotlin
repositories {
    // Determine publishing target based on environment/properties (defaults to staging)
    val publishType = project.findProperty("publishType") as String? ?: System.getenv("PUBLISH_TYPE") ?: "staging"
    
    if (publishType == "production") {
        // Maven Central (for production) - New Central Portal Staging API
        maven {
            name = "CentralPortal"
            url = uri("https://ossrh-staging-api.central.sonatype.com/service/local/staging/deploy/maven2/")
            credentials {
                username = project.findProperty("centralPortalUsername") as String? ?: System.getenv("CENTRAL_PORTAL_USERNAME")
                password = project.findProperty("centralPortalPassword") as String? ?: System.getenv("CENTRAL_PORTAL_PASSWORD")
            }
        }
    } else {
        // GitHub Packages (for staging) - default fallback
        maven {
            name = "GitHubPackages"
            url = uri("https://maven.pkg.github.com/hitoshura25/mpo-api-authn-server")
            credentials {
                username = project.findProperty("GitHubPackagesUsername") as String?
                    ?: System.getenv("ANDROID_PUBLISH_USER")
                password = project.findProperty("GitHubPackagesPassword") as String?
                    ?: System.getenv("ANDROID_PUBLISH_TOKEN")
            }
        }
    }
}

// Signing is also conditional (production only)
signing {
    val publishType = project.findProperty("publishType") as String? ?: System.getenv("PUBLISH_TYPE") ?: "staging"
    val signingKey = project.findProperty("signingKey") as String? ?: System.getenv("SIGNING_KEY")
    val signingPassword = project.findProperty("signingPassword") as String? ?: System.getenv("SIGNING_PASSWORD")

    // Only sign for production publishing and if we have the required properties
    if (publishType == "production" && signingKey != null && signingPassword != null) {
        useInMemoryPgpKeys(signingKey, signingPassword)
        sign(publishing.publications["maven"])
    }
}
```

### Benefits of Conditional Publishing
- **Safety**: Prevents accidental publishing to wrong registry
- **Secure Default**: Defaults to staging (GitHub Packages) unless explicitly set to production
- **Efficiency**: No unnecessary signing for staging builds  
- **Clarity**: Must explicitly specify "production" for Maven Central publishing
- **Flexibility**: Same build script supports both staging and production

## Workflow Usage

The publishing is handled by the `publish-android.yml` workflow:

### Staging Publish (GitHub Packages)
```yaml
uses: ./.github/workflows/publish-android.yml
with:
  publish-type: "staging"
  client-version: "1.0.36-pr.42.123"
  # ... other parameters
```

**Command executed**: `./gradlew :android-client-library:publish -PpublishType="staging"`
- Only configures GitHub Packages repository
- No GPG signing (not required for GitHub Packages)
- Uses `GITHUB_TOKEN` for authentication

### Production Publish (Maven Central)
```yaml
uses: ./.github/workflows/publish-android.yml
with:
  publish-type: "production"
  client-version: "1.0.36"
  # ... other parameters
secrets: inherit  # Includes Central Portal and signing secrets
```

**Command executed**: `./gradlew :android-client-library:publish -PpublishType="production"`
- Only configures Maven Central repository
- Automatically enables GPG signing
- Uses Central Portal credentials and signing key

### Local Testing
```bash
# Test staging publish (GitHub Packages) - default behavior
./gradlew :android-client-library:publish -PclientVersion="test-version"
# OR explicitly specify staging
./gradlew :android-client-library:publish -PpublishType="staging" -PclientVersion="test-version"

# Test production publish (Maven Central) - requires explicit flag and secrets
./gradlew :android-client-library:publish -PpublishType="production" -PclientVersion="test-version"
```

### Safety Features
- **Safe Default**: Running `publish` without `publishType` defaults to staging
- **Explicit Production**: Must explicitly set `publishType="production"` for Maven Central
- **No Accidental Production**: Cannot accidentally publish to Maven Central

## Verification

After publishing to Maven Central:
1. Check the [Central Portal](https://central.sonatype.com/publishing)
2. Artifacts will appear in the publishing portal
3. After manual verification and release, they will be available on Maven Central
4. Search for your artifact on [Maven Central Search](https://search.maven.org/)

## Consumer Usage

Once published to Maven Central, consumers can add the dependency:

```kotlin
dependencies {
    implementation("io.github.hitoshura25:mpo-webauthn-android-client:1.0.36")
}
```

No special repository configuration required - Maven Central is included by default.

## Migration from Legacy OSSRH

If you previously set up Maven Central publishing with the legacy OSSRH system:

### Required Changes
1. **Replace OSSRH credentials** with Central Portal user tokens:
   - Remove: `OSSRH_USERNAME` and `OSSRH_PASSWORD` secrets
   - Add: `CENTRAL_PORTAL_USERNAME` and `CENTRAL_PORTAL_PASSWORD` secrets

2. **Update repository URLs** from:
   - Old: `https://s01.oss.sonatype.org/service/local/staging/deploy/maven2/`
   - New: `https://ossrh-staging-api.central.sonatype.com/service/local/staging/deploy/maven2/`

3. **Generate new user token** in Central Portal (OSSRH tokens will result in 401 errors)

### Benefits of Migration
- **Simplified workflow**: No more manual staging repository management
- **Better UI**: Modern Central Portal interface
- **Faster processing**: Improved publishing pipeline
- **Enhanced security**: Token-based authentication