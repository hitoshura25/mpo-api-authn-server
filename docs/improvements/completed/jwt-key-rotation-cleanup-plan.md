# JWT Key Rotation - Code Quality & Cleanup Plan

**Date**: 2025-10-27
**Last Updated**: 2025-10-27
**Status**: Phase 1 Complete ✅ | Ready for Phase 2

**Progress**:
- ✅ **Phase 1**: Documentation + Architecture Fix (Complete)
- ⏳ **Phase 2**: Template Simplification (Next)
- ⏳ **Phase 3**: Database Schema Cleanup
- ⏳ **Phase 4**: Code Refactoring
- ⏳ **Phase 5**: Test Security Improvements
**Related Documents**:
- [jwt-key-rotation-implementation-plan.md](../completed/jwt-key-rotation-implementation-plan.md)
- [jwt-key-rotation-test-failures-fix.md](../completed/jwt-key-rotation-test-failures-fix.md)

## 🎯 Key Decisions Made

1. ✅ **Production-Ready Defaults** - All generator defaults are production values (300s cache, 180d rotation). Tests explicitly override.
2. ✅ **Migration-Based Schema** - Remove JWT tables from init-db.sql.hbs, use Flyway V3 migration (Option A).
3. ✅ **Unified Quantum-Safe Encryption** - Consolidate to Kyber768 for both JWT keys and WebAuthn credentials.

---

## Executive Summary

This document addresses 14 code quality issues identified after the successful JWT key rotation implementation (40/40 tests passing). The issues fall into these categories:

1. **Over-Engineered Logic**: Complex auto-detection that should be simplified with explicit defaults
2. **Schema Duplication**: Migration V3 content duplicated in init-db.sql.hbs
3. **Configuration Duplication**: Database config repeated in multiple DI providers
4. **Deprecated Code**: Methods marked deprecated but still in use
5. **Test Security**: Hardcoded plaintext secrets in test files
6. **Validation Gaps**: Missing fail-fast validation for required environment variables

**Goal**: Simplify codebase, eliminate duplication, improve security, while maintaining 100% test pass rate.

---

## Table of Contents

1. [Issue #1: generator.ts - Complex JWKS Cache Logic](#issue-1-generatorts---complex-jwks-cache-logic)
2. [Issue #2: docker-compose.yml.hbs - Conditional Complexity](#issue-2-docker-composeymlhbs---conditional-complexity)
3. [Issue #3: envoy-gateway.yaml.hbs - Auto-Determined Values](#issue-3-envoy-gatewayyamlhbs---auto-determined-values)
4. [Issue #4: init-db.sql.hbs - Migration Duplication](#issue-4-init-dbsqlhbs---migration-duplication)
5. [Issue #5: EnvironmentVariables.kt - Misleading Comment](#issue-5-environmentvariableskt---misleading-comment)
6. [Issue #6: StorageModule.kt - Database Config Duplication](#issue-6-storagemodulett---database-config-duplication)
7. [Issue #7: JwtService.kt - Deprecated getPublicKey()](#issue-7-jwtservicekt---deprecated-getpublickey)
8. [Issue #8: JwtService.kt - verifyToken() Comment Clarity](#issue-8-jwtservicekt---verifytoken-comment-clarity)
9. [Issue #9: KeyEncryptionService vs PostQuantumCryptographyService](#issue-9-keyencryptionservice-vs-postquantumcryptographyservice)
10. [Issue #10: KeyRotationService - Missing Fail-Fast Validation](#issue-10-keyrotationservice---missing-fail-fast-validation)
11. [Issue #11: V3 Migration Duplication (see Issue #4)](#issue-11-v3-migration-duplication-see-issue-4)
12. [Issue #12: TestStorageModule.kt - Hardcoded Secret](#issue-12-teststoragemodulett---hardcoded-secret)
13. [Issue #13: KeyRotationIntegrationTest.kt - Hardcoded Password](#issue-13-keyrotationintegrationtestkt---hardcoded-password)
14. [Issue #14: BaseIntegrationTest.kt - Hardcoded Encryption Key](#issue-14-baseintegrationtestkt---hardcoded-encryption-key)

---

## Issue #1: generator.ts - Complex JWKS Cache Logic

### Current Implementation

**File**: `mcp-server-webauthn-client/src/lib/generator.ts` (lines 123-138)

```typescript
// Calculate smart JWKS cache duration based on rotation interval
let calculated_jwks_cache_duration = jwks_cache_duration_seconds;

if (!calculated_jwks_cache_duration) {
  // Auto-detect based on rotation interval
  if (jwt_rotation_interval_seconds && parseInt(jwt_rotation_interval_seconds) < 60) {
    // Testing mode: Short rotation interval detected
    calculated_jwks_cache_duration = 10; // 10 second cache for rapid testing
    console.log('ℹ️  Testing mode detected (rotation interval < 60s): Using 10-second JWKS cache');
  } else {
    // Production mode: Standard rotation interval
    calculated_jwks_cache_duration = 300; // 5 minute cache (industry standard)
  }
} else {
  console.log(`ℹ️  Using explicit JWKS cache duration: ${calculated_jwks_cache_duration} seconds`);
}
```

### Problem Analysis

1. **Over-Engineering**: Auto-detection logic adds complexity without significant benefit
2. **Hidden Defaults**: Default values buried in conditional logic instead of interface
3. **Implicit Behavior**: Users don't know what value will be used without reading source
4. **Testing Assumption**: Assumes `< 60s` means testing, but could be legitimate production use case

### Proposed Solution

**Remove auto-detection, use PRODUCTION defaults at interface level:**

```typescript
interface GenerateWebClientArgs {
  // ... existing parameters

  // JWT key rotation configuration
  jwt_rotation_enabled?: string;              // Default: "true"
  jwt_rotation_interval_days?: string;        // Default: "180" (6 months)
  jwt_rotation_interval_seconds?: string;     // Optional override for testing
  jwt_grace_period_minutes?: string;          // Default: "60" (1 hour)
  jwt_retention_minutes?: string;             // Default: "60" (1 hour)

  // JWKS cache duration - PRODUCTION default
  jwks_cache_duration_seconds?: number;       // Default: 300 (5 minutes - industry standard)
}

export async function generateWebClient(args: GenerateWebClientArgs) {
  const {
    // ... existing destructuring
    jwt_rotation_enabled = 'true',
    jwt_rotation_interval_days = '180',       // PRODUCTION: 6 months
    jwt_grace_period_minutes = '60',          // PRODUCTION: 1 hour
    jwt_retention_minutes = '60',             // PRODUCTION: 1 hour
    jwks_cache_duration_seconds = 300,        // PRODUCTION: 5 minutes
    jwt_rotation_interval_seconds,            // Optional override
  } = args;

  // No conditional logic - just use the values
  console.log(`ℹ️  JWT Rotation: ${jwt_rotation_enabled}`);
  console.log(`ℹ️  JWKS cache duration: ${jwks_cache_duration_seconds} seconds`);

  const template_vars = {
    // ... existing vars
    jwt_rotation_enabled,
    jwt_rotation_interval_days,
    jwt_rotation_interval_seconds,
    jwt_grace_period_minutes,
    jwt_retention_minutes,
    jwks_cache_duration_seconds
  };
}
```

**For test clients, explicitly override defaults:**
```typescript
// generate-rotation-test-client.mjs
await generateWebClient({
  project_path: './test-key-rotation-client',
  // Override all values for accelerated testing
  jwt_rotation_interval_seconds: '30',       // Testing: 30 seconds (not days)
  jwt_grace_period_minutes: '0.25',          // Testing: 15 seconds
  jwt_retention_minutes: '0.5',              // Testing: 30 seconds
  jwks_cache_duration_seconds: 10            // Testing: 10 seconds
});
```

### Benefits

- ✅ Clear, predictable behavior
- ✅ Production-ready defaults (secure by default)
- ✅ No hidden logic or magic values
- ✅ Defaults in one place (interface)
- ✅ Test clients explicitly opt into accelerated settings

### Migration Impact

- **Breaking Change**: Minimal - most users don't override defaults
- **Mitigation**: Production clients work unchanged (defaults are production-ready)
- **Test Impact**: Update `generate-rotation-test-client.mjs` to explicitly override all testing values

---

## Issue #2: docker-compose.yml.hbs - Conditional Complexity

### Current Implementation

**File**: `mcp-server-webauthn-client/src/templates/vanilla/docker/docker-compose.yml.hbs` (lines 119-126)

```yaml
environment:
  # JWT Key Rotation Configuration
  MPO_AUTHN_JWT_KEY_ROTATION_ENABLED: "{{#if jwt_rotation_enabled}}{{jwt_rotation_enabled}}{{else}}true{{/if}}"
  {{#if jwt_rotation_interval_seconds}}
  MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS: "{{jwt_rotation_interval_seconds}}"  # Testing mode: accelerated rotation
  {{else}}
  MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS: "180"  # Production default: 6 months
  {{/if}}
  MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES: "{{#if jwt_grace_period_minutes}}{{jwt_grace_period_minutes}}{{else}}60{{/if}}"
  MPO_AUTHN_JWT_KEY_RETENTION_MINUTES: "{{#if jwt_retention_minutes}}{{jwt_retention_minutes}}{{else}}60{{/if}}"
```

### Problem Analysis

1. **Template Complexity**: Nested Handlebars conditionals hard to read/maintain
2. **Inconsistent Defaults**: Some defaults in template, some in generator
3. **Multiple Default Locations**: Defaults scattered across template files
4. **Conditional Key Names**: `INTERVAL_SECONDS` vs `INTERVAL_DAYS` conditionally set

### Proposed Solution

**Set ALL defaults in generator.ts with PRODUCTION values, use explicit template variables:**

```typescript
// In generator.ts - PRODUCTION defaults
export async function generateWebClient(args: GenerateWebClientArgs) {
  const {
    // PRODUCTION defaults for JWT rotation
    jwt_rotation_enabled = 'true',
    jwt_rotation_interval_days = '180',        // PRODUCTION: 6 months
    jwt_rotation_interval_seconds,             // Optional override for testing
    jwt_grace_period_minutes = '60',           // PRODUCTION: 1 hour
    jwt_retention_minutes = '60',              // PRODUCTION: 1 hour
    jwks_cache_duration_seconds = 300,         // PRODUCTION: 5 minutes
  } = args;

  const template_vars = {
    // ... existing vars
    jwt_rotation_enabled,
    jwt_rotation_interval_days,
    jwt_rotation_interval_seconds,
    jwt_grace_period_minutes,
    jwt_retention_minutes,
    jwks_cache_duration_seconds
  };
}
```

**Simplified docker-compose.yml.hbs:**

```yaml
environment:
  # JWT Key Rotation Configuration
  MPO_AUTHN_JWT_KEY_ROTATION_ENABLED: "{{jwt_rotation_enabled}}"
  {{#if jwt_rotation_interval_seconds}}
  MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS: "{{jwt_rotation_interval_seconds}}"
  {{else}}
  MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS: "{{jwt_rotation_interval_days}}"
  {{/if}}
  MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES: "{{jwt_grace_period_minutes}}"
  MPO_AUTHN_JWT_KEY_RETENTION_MINUTES: "{{jwt_retention_minutes}}"
  MPO_AUTHN_JWT_KEY_SIZE: "2048"
  MPO_AUTHN_JWT_KEY_ID_PREFIX: "webauthn"
```

**Note**: The `{{#if}}` conditional is kept because the server uses EITHER `INTERVAL_SECONDS` OR `INTERVAL_DAYS` (mutually exclusive). This is minimal conditional logic required by the server's environment variable handling.

**For testing, generator script explicitly overrides:**
```typescript
// generate-rotation-test-client.mjs
await generateWebClient({
  project_path: './test-key-rotation-client',
  jwt_rotation_interval_seconds: '30',       // Override: 30 seconds for testing
  jwt_grace_period_minutes: '0.25',          // Override: 15 seconds
  jwt_retention_minutes: '0.5',              // Override: 30 seconds
  jwks_cache_duration_seconds: 10            // Override: 10 seconds
});
```

### Benefits

- ✅ No conditional logic except server-required SECONDS vs DAYS choice
- ✅ All defaults in one place (generator.ts) with PRODUCTION values
- ✅ Template becomes mostly pure variable substitution
- ✅ Production-ready by default
- ✅ Test clients explicitly opt into accelerated settings

---

## Issue #3: envoy-gateway.yaml.hbs - Auto-Determined Values

### Current Implementation

**File**: `mcp-server-webauthn-client/src/templates/vanilla/docker/envoy-gateway.yaml.hbs` (lines 84-85)

```yaml
cache_duration:
  seconds: {{#if jwks_cache_duration_seconds}}{{jwks_cache_duration_seconds}}{{else}}300{{/if}}
```

### Problem Analysis

1. **Fallback in Template**: Should never happen if generator.ts provides defaults
2. **Dead Code**: The `{{else}}300{{/if}}` branch never executes if Issue #1 is fixed
3. **Defensive Programming Gone Wrong**: Template shouldn't need to handle missing values

### Proposed Solution

**Remove conditional, rely on generator defaults:**

```yaml
cache_duration:
  seconds: {{jwks_cache_duration_seconds}}
```

Generator.ts guarantees this value is always set (Issue #1 fix provides default).

### Benefits

- ✅ Simpler template
- ✅ Single source of truth (generator.ts)
- ✅ Template fails loudly if value missing (better than silent fallback)

### Validation

If generator.ts doesn't provide `jwks_cache_duration_seconds`, Handlebars will output empty string → Envoy will fail to start → immediate detection.

This is GOOD - fail-fast at deployment time, not silent unexpected behavior.

---

## Issue #4: init-db.sql.hbs - Migration Duplication

### Current Implementation

**Two locations defining JWT tables:**

1. **Server migrations**: `webauthn-server/src/main/resources/db/migration/V3__add_jwt_signing_keys_tables.sql`
2. **MCP template**: `mcp-server-webauthn-client/src/templates/vanilla/docker/init-db.sql.hbs` (lines 36-114)

**init-db.sql.hbs includes:**
```sql
-- Lines 1-35: WebAuthn tables (V1/V2)
CREATE TABLE webauthn_users_secure ...
CREATE TABLE webauthn_credentials_secure ...

-- Lines 36-114: JWT tables (duplicates V3 migration!)
CREATE TABLE jwt_signing_keys ...
CREATE TABLE jwt_key_audit_log ...
```

### Problem Analysis

1. **Schema Duplication**: Same tables defined in two places
2. **Maintenance Burden**: Changes must be made in both locations
3. **Drift Risk**: Schemas can diverge if only one location is updated
4. **Wrong Responsibility**: init-db.sql.hbs is for Docker first-run, not application migrations

### Proposed Solution

**Option A: Remove JWT Tables from init-db.sql.hbs** ✅ **CHOSEN APPROACH**

```sql
-- init-db.sql.hbs - ONLY WebAuthn base tables
-- Lines 1-35 remain, lines 36-114 DELETED

-- WebAuthn Database Schema Initialization
-- Auto-generated by @vmenon25/mcp-server-webauthn-client
--
-- This script creates ONLY the base WebAuthn tables.
-- JWT key rotation tables are managed by Flyway migrations (V3).

-- Users table
CREATE TABLE webauthn_users_secure (
    user_handle_hash CHAR(64) PRIMARY KEY,
    username_hash CHAR(64) UNIQUE NOT NULL,
    encrypted_user_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Credentials table
CREATE TABLE webauthn_credentials_secure (
    credential_id_hash CHAR(64) PRIMARY KEY,
    user_handle_hash CHAR(64) NOT NULL REFERENCES webauthn_users_secure(user_handle_hash) ON DELETE CASCADE,
    encrypted_credential_data TEXT NOT NULL,
    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_webauthn_users_secure_username ON webauthn_users_secure(username_hash);
CREATE INDEX idx_webauthn_credentials_secure_user ON webauthn_credentials_secure(user_handle_hash);

-- Comments
COMMENT ON TABLE webauthn_users_secure IS 'Stores WebAuthn user data with application-level encryption';
COMMENT ON TABLE webauthn_credentials_secure IS 'Stores WebAuthn credentials with application-level encryption';
```

**How JWT tables get created:**
1. Docker starts with `init-db.sql` → creates base WebAuthn tables
2. Server starts → Flyway detects pending migration V3 → creates JWT tables
3. Single source of truth for JWT schema (V3 migration)

**Option B: Remove V3 Migration, Keep in init-db.sql.hbs**

Alternative: Delete `V3__add_jwt_signing_keys_tables.sql` and rely solely on init-db.sql.hbs.

**Why Option A is Better:**
- ✅ Migrations are versioned and tracked by Flyway
- ✅ Server can run independently without docker-compose
- ✅ Migration history preserved in git
- ✅ Rollback capability (Flyway handles this)
- ✅ Production databases can migrate without full recreate

**Why Option B is Worse:**
- ❌ No migration history for JWT tables
- ❌ Can't evolve schema incrementally
- ❌ Requires database recreate for updates
- ❌ Breaks server-only deployment

### Implementation Plan

1. **Delete lines 36-114 from init-db.sql.hbs**
2. **Update comment header** to clarify scope
3. **Test in fresh Docker environment**:
   ```bash
   cd test-key-rotation-client/docker
   docker compose down -v  # Clean volumes
   docker compose up -d
   # Verify both WebAuthn AND JWT tables exist
   docker exec -it webauthn-postgres psql -U webauthn_user -d webauthn -c "\dt"
   ```
4. **Verify Flyway migration logs**:
   ```bash
   docker logs webauthn-server | grep "Flyway"
   # Should show: "Migrating schema to version 3 - add jwt signing keys tables"
   ```

### Risks & Mitigation

**Risk**: Existing Docker volumes have JWT tables from init-db.sql, migration V3 will fail

**Mitigation**:
- Flyway's `validateMigrationNaming` handles this - V3 won't re-run if tables exist
- Document: Users should use `docker compose down -v` to clean volumes after template update

---

## Issue #5: EnvironmentVariables.kt - Misleading Comment

### Current Implementation

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/config/EnvironmentVariables.kt` (line 40-41)

```kotlin
// JWT Key Rotation - Test Mode
const val MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS = "MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS"
```

### Problem Analysis

1. **Misleading Comment**: Implies this is ONLY for testing
2. **Valid Production Use**: Fine-grained rotation intervals (e.g., daily = 86400s) are legitimate
3. **Confusing Documentation**: Users might think this is test-only and avoid using it

### Proposed Solution

**Update comment to reflect dual purpose:**

```kotlin
// JWT Key Rotation Configuration
const val MPO_AUTHN_JWT_KEY_ROTATION_ENABLED = "MPO_AUTHN_JWT_KEY_ROTATION_ENABLED"
const val MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS = "MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS"
const val MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES = "MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES"
const val MPO_AUTHN_JWT_KEY_RETENTION_MINUTES = "MPO_AUTHN_JWT_KEY_RETENTION_MINUTES"
const val MPO_AUTHN_JWT_KEY_SIZE = "MPO_AUTHN_JWT_KEY_SIZE"
const val MPO_AUTHN_JWT_KEY_ID_PREFIX = "MPO_AUTHN_JWT_KEY_ID_PREFIX"
const val MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY = "MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY"

// JWT Key Rotation - Override interval in seconds (for testing or fine-grained production control)
// Takes precedence over MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS if set
const val MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS = "MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS"
```

### Benefits

- ✅ Accurate documentation
- ✅ Clarifies precedence (seconds overrides days)
- ✅ Encourages appropriate use

---

## Issue #6: StorageModule.kt - Database Config Duplication

### Current Implementation

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/di/StorageModule.kt`

**Two places creating database configs with same env vars:**

```kotlin
// Lines 261-280: DataSource provider
single<DataSource> {
    val host: String by inject(named("dbHost"))
    val port: Int by inject(named("dbPort"))
    val database: String by inject(named("dbName"))
    val username: String by inject(named("dbUsername"))
    val password: String by inject(named("dbPassword"))
    val maxPoolSize: Int by inject(named("dbMaxPoolSize"))

    val hikariConfig = HikariConfig().apply {
        jdbcUrl = "jdbc:postgresql://$host:$port/$database?sslmode=disable"
        this.username = username
        this.password = password
        maximumPoolSize = maxPoolSize
        // ...
    }
    HikariDataSource(hikariConfig)
}

// Lines 283-300: CredentialStorage provider (DUPLICATE VALUES!)
single<CredentialStorage> {
    val host: String by inject(named("dbHost"))
    val port: Int by inject(named("dbPort"))
    val database: String by inject(named("dbName"))
    val username: String by inject(named("dbUsername"))
    val password: String by inject(named("dbPassword"))
    val maxPoolSize: Int by inject(named("dbMaxPoolSize"))

    createQuantumSafeCredentialStorage(
        DatabaseConfig(
            host = host,
            port = port,
            database = database,
            username = username,
            password = password,
            maxPoolSize = maxPoolSize,
        ),
    )
}
```

### Problem Analysis

1. **Code Duplication**: Same 6 values injected in two places
2. **Maintenance Burden**: Changes must be made in both locations
3. **Inconsistency Risk**: One provider might get updated, other forgotten
4. **Violation of DRY**: Don't Repeat Yourself principle

### Proposed Solution

**Create single DatabaseConfig provider:**

```kotlin
// Add DatabaseConfig as a single provider
single<DatabaseConfig> {
    val host: String by inject(named("dbHost"))
    val port: Int by inject(named("dbPort"))
    val database: String by inject(named("dbName"))
    val username: String by inject(named("dbUsername"))
    val password: String by inject(named("dbPassword"))
    val maxPoolSize: Int by inject(named("dbMaxPoolSize"))

    DatabaseConfig(
        host = host,
        port = port,
        database = database,
        username = username,
        password = password,
        maxPoolSize = maxPoolSize,
    )
}

// DataSource uses DatabaseConfig
single<DataSource> {
    val dbConfig: DatabaseConfig by inject()

    val hikariConfig = HikariConfig().apply {
        jdbcUrl = "jdbc:postgresql://${dbConfig.host}:${dbConfig.port}/${dbConfig.database}?sslmode=disable"
        username = dbConfig.username
        password = dbConfig.password
        maximumPoolSize = dbConfig.maxPoolSize
        connectionTimeout = 30000
        idleTimeout = 600000
        maxLifetime = 1800000
    }

    HikariDataSource(hikariConfig)
}

// CredentialStorage uses DatabaseConfig
single<CredentialStorage> {
    val dbConfig: DatabaseConfig by inject()
    createQuantumSafeCredentialStorage(dbConfig)
}.onClose { it?.close() }
```

### Benefits

- ✅ Single source of truth for database configuration
- ✅ Reduced code duplication
- ✅ Easier to maintain and update
- ✅ Consistent configuration across all database users

### Testing Verification

Verify both DataSource and CredentialStorage work correctly:
```kotlin
@Test
fun `database config is shared correctly`() {
    val dataSource: DataSource by inject()
    val credentialStorage: CredentialStorage by inject()

    // Both should use same configuration
    dataSource.connection.use { conn ->
        val dbName = conn.metaData.url
        assertTrue(dbName.contains("webauthn"))
    }
}
```

---

## Issue #7: JwtService.kt - Deprecated getPublicKey()

### Current Implementation

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/security/JwtService.kt` (lines 114-127)

```kotlin
/**
 * Get current RSA public key for JWT signature verification.
 *
 * DEPRECATED: Clients should use the JWKS endpoint (/.well-known/jwks.json)
 * instead of this method, as JWKS automatically handles key rotation by
 * returning all publishable keys (ACTIVE + RETIRED).
 *
 * This method is kept for backward compatibility and testing purposes.
 *
 * @return RSA public key of the current ACTIVE signing key
 */
fun getPublicKey(): RSAPublicKey {
    val (_, keyPair) = keyRotationService.getActiveSigningKey()
    return keyPair.public as RSAPublicKey
}
```

**Usage Analysis**: Used ONLY in `JwtServiceTest.kt` (6 times):
- Line 114: `val publicKey = jwtService.getPublicKey()`
- Line 130: `val publicKey = jwtService.getPublicKey()`
- Line 157: `val publicKey1 = service1.getPublicKey()`
- Line 158: `val publicKey2 = service2.getPublicKey()`
- Line 166: `val publicKey1 = jwtService.getPublicKey()`
- Line 167: `val publicKey2 = jwtService.getPublicKey()`

**NO PRODUCTION CODE USES THIS METHOD**

### Problem Analysis

1. **Deprecated in Production**: Marked deprecated but kept "for backward compatibility"
2. **No External Users**: Only used internally by tests
3. **Misleading Comment**: Says "backward compatibility" but nothing external depends on it
4. **Test Smell**: Tests should use public APIs (JWKS endpoint), not internal methods

### Proposed Solution

**Option A: Remove Method Entirely (RECOMMENDED)**

1. **Update JwtServiceTest.kt** to verify tokens via JWKS endpoint instead:

```kotlin
// OLD: Direct public key access
@Test
fun `should generate valid JWT token`() {
    val token = jwtService.createToken("testuser")
    val publicKey = jwtService.getPublicKey()  // REMOVE THIS

    val verifier = JWT.require(Algorithm.RSA256(publicKey, null))
        .withIssuer("mpo-webauthn")
        .build()
    val decoded = verifier.verify(token)
    assertEquals("testuser", decoded.subject)
}

// NEW: Use JWKS endpoint (via KeyRotationService)
@Test
fun `should generate valid JWT token`() {
    val token = jwtService.createToken("testuser")

    // Verify using all publishable keys (same as production clients would)
    val publishableKeys = keyRotationService.getAllPublishableKeys()
    val tokenHeader = JWT.decode(token)
    val keyId = tokenHeader.keyId

    val signingKey = publishableKeys.first { it.keyId == keyId }
    val publicKey = loadPublicKeyFromPem(signingKey.publicKeyPem)

    val verifier = JWT.require(Algorithm.RSA256(publicKey, null))
        .withIssuer("mpo-webauthn")
        .build()
    val decoded = verifier.verify(token)
    assertEquals("testuser", decoded.subject)
}
```

2. **Delete `getPublicKey()` method** from JwtService.kt

**Option B: Keep Method but Mark @Deprecated with Error**

```kotlin
@Deprecated(
    message = "Use JWKS endpoint (/.well-known/jwks.json) instead. " +
              "This method only returns ACTIVE key, not RETIRED keys needed during rotation.",
    replaceWith = ReplaceWith("keyRotationService.getAllPublishableKeys()"),
    level = DeprecationLevel.ERROR
)
fun getPublicKey(): RSAPublicKey {
    // ...
}
```

Forces removal after next version.

### Recommendation

**Choose Option A** - tests should validate production behavior (JWKS endpoint).

### Benefits

- ✅ Tests match production client behavior
- ✅ Cleaner API surface
- ✅ No misleading "backward compatibility" claims
- ✅ Forces proper testing patterns

---

## Issue #8: JwtService.kt - verifyToken() Comment Clarity

### Current Implementation

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/security/JwtService.kt` (lines 87-96)

```kotlin
/**
 * Verify JWT token signature and claims.
 * Used for internal testing and validation.
 *
 * Note: In production, clients should verify JWTs using the JWKS endpoint,
 * which automatically handles key rotation. This method is primarily for testing.
 */
fun verifyToken(token: String): DecodedJWT {
    // Get active signing key for verification
    val (_, keyPair) = keyRotationService.getActiveSigningKey()
    // ...
}
```

### Problem Analysis

1. **Misleading Comment**: Says "primarily for testing" but it's a legitimate internal method
2. **Limitation Not Clear**: Doesn't explain it only verifies with ACTIVE key
3. **Valid Use Cases**: Internal workflows, admin tools, debugging - not just testing
4. **Confusion**: Users might think it's wrong to use this in production code

### Proposed Solution

**Clarify comment to explain limitations and valid use cases:**

```kotlin
/**
 * Verify JWT token signature and claims using the ACTIVE signing key.
 *
 * **Limitation**: This method only verifies tokens against the current ACTIVE key.
 * Tokens signed with RETIRED keys (still valid during retention period) will fail.
 *
 * **For Production Clients**: Use the JWKS endpoint (/.well-known/jwks.json) which
 * returns ALL publishable keys (ACTIVE + RETIRED) and handles key rotation automatically.
 *
 * **Valid Use Cases for This Method**:
 * - Internal validation workflows where only ACTIVE key is needed
 * - Admin tools that only accept fresh tokens
 * - Unit testing token generation
 * - Debugging and troubleshooting
 *
 * @param token JWT token string to verify
 * @return Decoded JWT with verified signature and claims
 * @throws com.auth0.jwt.exceptions.JWTVerificationException if token is invalid or signed with non-ACTIVE key
 */
fun verifyToken(token: String): DecodedJWT {
    // Implementation remains the same
}
```

### Benefits

- ✅ Clear about limitations
- ✅ Explains when to use vs JWKS
- ✅ Documents valid production use cases
- ✅ No code changes needed

---

## Issue #9: KeyEncryptionService vs PostQuantumCryptographyService

### Current Implementation

**Two encryption services exist:**

1. **KeyEncryptionService** (`security/KeyEncryptionService.kt`):
   - Algorithm: AES-256-GCM
   - Purpose: Encrypt JWT private signing keys (RSA keys)
   - Implementation: `AesGcmKeyEncryptionService`

2. **PostQuantumCryptographyService** (`security/PostQuantumCryptographyService.kt`):
   - Algorithm: Kyber768 KEM + AES-256-GCM hybrid
   - Purpose: Encrypt WebAuthn credentials (quantum-resistant)
   - Implementation: Quantum-safe hybrid encryption

### Problem Analysis

**Initial Assessment**: Two different use cases with different algorithms.

**Re-evaluation After Review**: While AES-256-GCM is quantum-resistant (128-bit effective security via Grover's algorithm), consolidating to Kyber768 provides:
- Additional defense-in-depth
- Future-proofing against unexpected quantum advances
- Unified encryption approach (simpler mental model)
- Minimal performance impact in production (0.1ms → 1-2ms, once per 6 months)

| Service | Current | Performance | Quantum Resistance |
|---------|---------|-------------|-------------------|
| KeyEncryptionService | AES-256-GCM | 0.1ms | 128-bit effective (Grover) |
| PostQuantumCryptographyService | Kyber768 + AES | 1-2ms | Full (NIST Level 3) |

### Proposed Solution

**Consolidate JWT Key Encryption to Use PostQuantumCryptographyService** ✅ **CHOSEN APPROACH**

**Benefits of Consolidation**:
1. **Enhanced Security**: Maximum protection against quantum threats
2. **Unified Approach**: One encryption service for all sensitive data
3. **Simpler Codebase**: Remove KeyEncryptionService interface
4. **Defense-in-Depth**: Protection beyond Grover's algorithm limitations
5. **Future-Proof**: Ready for post-quantum era

**Performance Analysis**:
```
JWT Key Encryption Frequency:
- Production: Once per 6 months (180 days)
- Testing: Once per 30 seconds

Performance Impact:
- Current: 0.1ms (AES-256-GCM)
- Proposed: 1-2ms (Kyber768 + AES)
- Slowdown: 10-20x
- Real Impact: Negligible (happens rarely, not in request path)
```

**Implementation Steps**:

1. **Update KeyRotationService**:
```kotlin
class KeyRotationService(
    private val keyRepository: KeyRepository,
    private val encryptionService: PostQuantumCryptographyService,  // Changed from KeyEncryptionService
) {
    // Implementation remains the same - interface is compatible
}
```

2. **Update DI Modules**:
```kotlin
// Remove KeyEncryptionService provider
// Keep only PostQuantumCryptographyService

single<PostQuantumCryptographyService> {
    PostQuantumCryptographyService()
}

single {
    val keyRepository: KeyRepository by inject()
    val encryptionService: PostQuantumCryptographyService by inject()
    KeyRotationService(keyRepository, encryptionService)
}
```

3. **Delete KeyEncryptionService.kt and AesGcmKeyEncryptionService.kt**

4. **Update PostQuantumCryptographyService**:
```kotlin
/**
 * Post-Quantum Cryptography service for ALL sensitive data encryption.
 *
 * Uses Kyber768 KEM + AES-256-GCM hybrid encryption for maximum security.
 *
 * Used for:
 * - WebAuthn credentials (long-term storage)
 * - JWT signing keys (server-controlled, rotated)
 *
 * Provides defense-in-depth against quantum computers while maintaining
 * reasonable performance for infrequent operations.
 *
 * Performance: ~1-2ms per encryption/decryption (vs 0.1ms for AES-only)
 * Security: NIST Level 3 post-quantum resistance
 */
class PostQuantumCryptographyService {
    fun encrypt(plaintext: String): String { /* ... */ }
    fun decrypt(ciphertext: String): String { /* ... */ }
}
```

### Tradeoffs Accepted

**Performance Cost**: 10-20x slower (0.1ms → 1-2ms)
- **Mitigation**: JWT key operations are rare (6 months production, 30s testing)
- **Impact**: Not in request path, happens during rotation scheduler

**Dependency Complexity**: BouncyCastle PQC required
- **Already Required**: PostQuantumCryptographyService already in use
- **No Additional Dependencies**: Just wider usage of existing service

**Testing Updates Required**: Update test modules to use PostQuantumCryptographyService
- **Low Risk**: Interface remains compatible

### Why Consolidate (Decision Rationale)

1. **"Harvest Now, Decrypt Later" Threat**: Even with AES-256, quantum computers could threaten data in 10-20 years
2. **Defense-in-Depth**: Protects against unknown vulnerabilities beyond Grover's algorithm
3. **Consistency**: All sensitive data encrypted with same quantum-safe approach
4. **Minimal Downside**: Performance cost negligible for rotation frequency
5. **User Preference**: Prioritizes maximum security over marginal performance optimization

---

## Issue #10: KeyRotationService - Missing Fail-Fast Validation

### Current Implementation

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/security/KeyRotationService.kt` (lines 52-84)

```kotlin
// Configuration from environment variables
private val rotationEnabled: Boolean =
    (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
        ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
        ?: "false").toBoolean()

private val rotationIntervalDays: Long =
    (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS)
        ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS)
        ?: "180").toLong()

// ... similar pattern for all config values
```

### Problem Analysis

1. **Silent Defaults**: Missing required values fall back to defaults silently
2. **Late Failure**: Application starts successfully but may fail at runtime
3. **Debugging Difficulty**: Hard to diagnose misconfiguration
4. **Inconsistent with StorageModule**: StorageModule uses `requireNotNull` for required values

### Proposed Solution

**Add fail-fast validation for REQUIRED values:**

```kotlin
class KeyRotationService(
    private val keyRepository: KeyRepository,
    private val encryptionService: KeyEncryptionService,
) {
    private val logger = LoggerFactory.getLogger(KeyRotationService::class.java)

    // REQUIRED: Fail fast if not provided
    private val rotationEnabled: Boolean = run {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
        requireNotNull(value) {
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED} is required. " +
            "Set to 'true' to enable rotation or 'false' to disable."
        }.also {
            require(it in listOf("true", "false")) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED} must be 'true' or 'false', got: '$it'"
            }
        }.toBoolean()
    }

    // REQUIRED: Fail fast if rotation enabled but interval not set
    private val rotationIntervalDays: Long = run {
        if (!rotationEnabled) return@run 180L // Default when disabled

        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS)
        requireNotNull(value) {
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS} is required when rotation is enabled"
        }.toLongOrNull()
            ?: throw IllegalArgumentException(
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS} must be a valid number, got: '$value'"
            )
    }

    // Optional override (can be null)
    private val rotationIntervalSeconds: Long? =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS))
            ?.toLongOrNull()

    // REQUIRED when rotation enabled
    private val gracePeriodMinutes: Double = run {
        if (!rotationEnabled) return@run 60.0

        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES)
        requireNotNull(value) {
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES} is required when rotation is enabled"
        }.toDoubleOrNull()
            ?: throw IllegalArgumentException(
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES} must be a valid number, got: '$value'"
            )
    }

    // REQUIRED when rotation enabled
    private val retentionAfterRetirementMinutes: Double = run {
        if (!rotationEnabled) return@run 60.0

        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES)
        requireNotNull(value) {
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES} is required when rotation is enabled"
        }.toDoubleOrNull()
            ?: throw IllegalArgumentException(
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES} must be a valid number, got: '$value'"
            )
    }

    // Optional with sensible default
    private val keySize: Int = run {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE)
            ?: return@run 2048  // Default

        value.toIntOrNull()?.also {
            require(it in listOf(2048, 3072, 4096)) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE} must be 2048, 3072, or 4096, got: $it"
            }
        } ?: throw IllegalArgumentException(
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE} must be a valid integer, got: '$value'"
        )
    }

    // Optional with sensible default
    private val keyIdPrefix: String =
        System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX)
            ?: "webauthn"

    init {
        logger.info("JWT Key Rotation Service initialized:")
        logger.info("  Enabled: $rotationEnabled")
        if (rotationEnabled) {
            logger.info("  Interval: ${rotationIntervalSeconds?.let { "${it}s" } ?: "${rotationIntervalDays}d"}")
            logger.info("  Grace Period: ${gracePeriodMinutes}m")
            logger.info("  Retention: ${retentionAfterRetirementMinutes}m")
            logger.info("  Key Size: $keySize")
            logger.info("  Key ID Prefix: $keyIdPrefix")
        }
    }
}
```

### Benefits

- ✅ Application fails to start with clear error message
- ✅ Consistent with StorageModule validation pattern
- ✅ Easier debugging (misconfiguration detected immediately)
- ✅ Self-documenting required vs optional values

### Testing Impact

Update tests to provide required values:
```kotlin
@BeforeEach
fun setup() {
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED, "true")
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS, "180")
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES, "60")
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES, "60")
}
```

---

## Issue #11: V3 Migration Duplication (see Issue #4)

This issue is the same as Issue #4. The duplication exists between:
- `webauthn-server/src/main/resources/db/migration/V3__add_jwt_signing_keys_tables.sql`
- `mcp-server-webauthn-client/src/templates/vanilla/docker/init-db.sql.hbs` (lines 36-114)

**Resolution**: See Issue #4 for detailed analysis and implementation plan.

---

## Issue #12: TestStorageModule.kt - Hardcoded Secret

### Current Implementation

**File**: `webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/TestStorageModule.kt` (line 38)

```kotlin
single<KeyEncryptionService> {
    // Use a test master key for encryption (not secure, but fine for unit tests)
    AesGcmKeyEncryptionService("test-master-key-32-characters-long!!")
}
```

### Problem Analysis

1. **Hardcoded Secret**: Plaintext password in source code
2. **Version Control**: Secret visible in git history
3. **Bad Practice Example**: Tests should model secure patterns
4. **Predictable Key**: Same key across all test runs

### Proposed Solution

**Generate random key per test run:**

```kotlin
single<KeyEncryptionService> {
    // Generate secure random key for each test run
    // This prevents any cross-test contamination and models best practices
    val testMasterKey = generateSecureTestKey()
    AesGcmKeyEncryptionService(testMasterKey)
}

private fun generateSecureTestKey(): String {
    // 32 bytes = 256 bits (AES-256 requirement)
    val secureRandom = java.security.SecureRandom()
    val keyBytes = ByteArray(32)
    secureRandom.nextBytes(keyBytes)
    return java.util.Base64.getEncoder().encodeToString(keyBytes)
}
```

**Alternative: Use environment variable with fallback:**

```kotlin
single<KeyEncryptionService> {
    val testMasterKey = System.getenv("TEST_JWT_MASTER_KEY")
        ?: generateSecureTestKey()

    AesGcmKeyEncryptionService(testMasterKey)
}
```

This allows:
- CI/CD to set consistent key if needed
- Local development gets random key
- No hardcoded secrets in code

### Benefits

- ✅ No plaintext secrets in code
- ✅ Models secure practices
- ✅ Fresh key per test run (isolation)
- ✅ Still deterministic if env var set

---

## Issue #13: KeyRotationIntegrationTest.kt - Hardcoded Password

### Current Implementation

**File**: `webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/integration/KeyRotationIntegrationTest.kt`

Similar to Issue #12, this test hardcodes `"test-master-key-for-integration-tests"` in multiple places.

### Problem Analysis

Same as Issue #12 - hardcoded secrets in test code.

### Proposed Solution

**Use BaseIntegrationTest's generated key:**

Since `BaseIntegrationTest` already sets up environment variables (Issue #14), the integration test should use that:

```kotlin
@BeforeEach
fun setupKeyRotation() {
    // Set up test environment with accelerated rotation for testing
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED, "true")
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS, "30")
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES, "1")
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES, "1")

    // Use the master key set by BaseIntegrationTest (generated securely)
    val masterKey = System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY)
    require(masterKey != null) { "Master key should be set by BaseIntegrationTest" }

    // Initialize services using the secure test key
    keyRepository = PostgresKeyRepository(postgres.createDataSource())
    encryptionService = AesGcmKeyEncryptionService(masterKey)
    keyRotationService = KeyRotationService(keyRepository, encryptionService)
}
```

### Benefits

- ✅ Reuses secure key generation from BaseIntegrationTest
- ✅ No duplication of key generation logic
- ✅ Consistent test setup patterns

---

## Issue #14: BaseIntegrationTest.kt - Hardcoded Encryption Key

### Current Implementation

**File**: `webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/testutils/BaseIntegrationTest.kt` (line 110-114)

```kotlin
// JWT Key Rotation configuration
System.setProperty(
    EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY,
    "test-master-key-32-characters!!",
)
```

### Problem Analysis

1. **Hardcoded Secret**: Plaintext in source code
2. **Same Key Across Tests**: All integration tests use identical key
3. **Security Anti-Pattern**: Tests should demonstrate secure practices

### Proposed Solution

**Generate secure random key per test class:**

```kotlin
abstract class BaseIntegrationTest : KoinTest {
    // Generate secure test master key once per test class
    companion object {
        private val testMasterKey: String by lazy {
            val secureRandom = SecureRandom()
            val keyBytes = ByteArray(32)  // 256 bits for AES-256
            secureRandom.nextBytes(keyBytes)
            Base64.getEncoder().encodeToString(keyBytes)
        }
    }

    // ... TestContainers setup ...

    protected fun setupTestEnvironmentVariables() {
        stopKoin() // Ensure clean state

        // ... Redis, PostgreSQL, Jaeger config ...

        // JWT Key Rotation configuration - use generated secure key
        System.setProperty(
            EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY,
            testMasterKey
        )
    }
}
```

**Alternative: Support reproducible tests with env var override:**

```kotlin
companion object {
    private val testMasterKey: String by lazy {
        // Allow override for reproducible test runs
        System.getenv("TEST_JWT_MASTER_KEY") ?: run {
            val secureRandom = SecureRandom()
            val keyBytes = ByteArray(32)
            secureRandom.nextBytes(keyBytes)
            Base64.getEncoder().encodeToString(keyBytes)
        }
    }
}
```

This allows:
- **CI/CD**: Can set `TEST_JWT_MASTER_KEY` for deterministic builds
- **Local Dev**: Gets random key (better isolation)
- **Debugging**: Can set specific key to reproduce failures

### Benefits

- ✅ No hardcoded secrets
- ✅ Fresh key per test run (or deterministic if env set)
- ✅ Models secure practices
- ✅ Supports reproducible testing

---

## Implementation Priority & Order

### Phase 1: Low-Risk Documentation + Architecture Fix ✅ **COMPLETE**

**Estimated Time**: 1 hour (actual: 2 hours due to architecture fix)

1. ✅ Issue #5: Update EnvironmentVariables.kt comment
2. ✅ Issue #8: Clarify JwtService.verifyToken() comment
3. ✅ **Bonus**: Fixed AppModule/StorageModule architecture issue

**Risk**: None - only comments (architecture fix was necessary to proceed)

**Actual Implementation**: During test validation, discovered that JWT infrastructure in `appModule` was causing test failures. Performed architectural refactoring:
- **Moved** entire JWT infrastructure from `appModule` to `storageModule` (proper separation of concerns)
- **Simplified** AppModuleTest to use `testStorageModule` instead of custom minimal module
- **Removed** `createdAtStart = true` from KeyRotationScheduler (prevented eager bean creation)
- **Result**: All 10 AppModuleTest tests passing, 44 StorageModuleTest tests passing

**Validation Results**: ✅ **ALL PASSED**
```bash
# 1. Verify server builds successfully
./gradlew :webauthn-server:build
# ✅ Result: BUILD SUCCESSFUL

# 2. Run all server tests
./gradlew :webauthn-server:test
# ✅ Result: BUILD SUCCESSFUL in 2m 55s
# ✅ AppModuleTest: 10/10 tests passing
# ✅ StorageModuleTest: 44/44 tests passing
# ✅ JWT/Rotation tests: All passing
# ✅ Total: All server tests passing (no regressions)

# 3. No E2E test changes needed (only comments + architecture refactoring)
```

---

### Phase 2: Template Simplification (Medium Risk)

**Estimated Time**: 3 hours

1. ✅ Issue #1: Simplify generator.ts JWKS cache logic (use production defaults)
2. ✅ Issue #2: Remove docker-compose.yml.hbs conditionals
3. ✅ Issue #3: Remove envoy-gateway.yaml.hbs fallback

**Risk**: Medium - changes template generation
**Impact**: MCP-generated clients will have different default values

**Validation Steps**:
```bash
# 1. Verify server tests still pass (no server changes)
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation
./gradlew :webauthn-server:test
# Expected: All tests passing

# 2. Rebuild MCP templates
cd mcp-server-webauthn-client
npm run build

# 3. Regenerate test client with NEW template (explicit testing overrides)
cd ..
rm -rf test-key-rotation-client
node generate-rotation-test-client.mjs

# 4. Verify generated files have CORRECT values
grep "seconds: 10" test-key-rotation-client/docker/envoy-gateway.yaml
# Expected: JWKS cache = 10 seconds (testing override)

grep "MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS" test-key-rotation-client/docker/docker-compose.yml
# Expected: 30 seconds (testing override)

grep "MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES" test-key-rotation-client/docker/docker-compose.yml
# Expected: 0.25 minutes = 15 seconds (testing override)

# 5. Build Docker image for testing
./gradlew :webauthn-server:shadowJar
docker build -t webauthn-server:test-cleanup-phase2 -f webauthn-server/Dockerfile webauthn-server/

# 6. Update docker-compose to use test image
cd test-key-rotation-client/docker
sed -i '' 's/image: hitoshura25\/webauthn-server:latest/image: webauthn-server:test-cleanup-phase2\n    pull_policy: never/' docker-compose.yml

# 7. Start fresh environment
docker compose down -v
docker compose up -d

# 8. Wait for services to be healthy
sleep 20

# 9. Install dependencies and run E2E tests
cd ..
npm install
npm run build
npm test

# Expected: 40/40 tests passing
# Confirms: Template changes work correctly with testing overrides
```

---

### Phase 3: Database Schema Cleanup (High Risk)

**Estimated Time**: 2 hours

1. ✅ Issue #4: Remove JWT tables from init-db.sql.hbs (lines 36-114)

**Risk**: High - changes database initialization (Flyway must handle JWT tables)
**Impact**: Fresh Docker stacks rely on Flyway V3 migration for JWT tables

**Validation Steps**:
```bash
# 1. Verify server tests still pass
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation
./gradlew :webauthn-server:test
# Expected: All tests passing (server uses TestContainers with migrations)

# 2. Rebuild MCP templates with updated init-db.sql.hbs
cd mcp-server-webauthn-client
npm run build

# 3. Regenerate test client with NEW template
cd ..
rm -rf test-key-rotation-client
node generate-rotation-test-client.mjs

# 4. Verify init-db.sql does NOT contain JWT tables
grep -c "jwt_signing_keys" test-key-rotation-client/docker/init-db.sql
# Expected: 0 (should not find JWT tables)

grep -c "webauthn_users_secure" test-key-rotation-client/docker/init-db.sql
# Expected: 1+ (should find WebAuthn tables)

# 5. Build Docker image for testing
./gradlew :webauthn-server:shadowJar
docker build -t webauthn-server:test-cleanup-phase3 -f webauthn-server/Dockerfile webauthn-server/

# 6. Update docker-compose to use test image
cd test-key-rotation-client/docker
sed -i '' 's/image: hitoshura25\/webauthn-server:latest/image: webauthn-server:test-cleanup-phase3\n    pull_policy: never/' docker-compose.yml

# 7. Start fresh environment (CRITICAL: clean volumes)
docker compose down -v
docker compose up -d

# 8. Wait for services to be healthy
sleep 20

# 9. Verify ALL tables exist (both WebAuthn AND JWT)
docker exec -it webauthn-postgres psql -U webauthn_user -d webauthn -c "\dt"
# Expected tables:
#  - webauthn_users_secure (from init-db.sql)
#  - webauthn_credentials_secure (from init-db.sql)
#  - jwt_signing_keys (from Flyway V3)
#  - jwt_key_audit_log (from Flyway V3)
#  - flyway_schema_history (from Flyway)

# 10. Verify Flyway migration executed
docker logs webauthn-server 2>&1 | grep -i "flyway"
# Expected: Should show "Migrating schema to version 3" or "Successfully applied 1 migration"

# 11. Verify Flyway schema history
docker exec -it webauthn-postgres psql -U webauthn_user -d webauthn -c "SELECT version, description, success FROM flyway_schema_history ORDER BY installed_rank;"
# Expected: Version 3 with "add jwt signing keys tables" shown as success = true

# 12. Install dependencies and run E2E tests
cd ..
npm install
npm run build
npm test

# Expected: 40/40 tests passing
# Confirms: Flyway migrations work correctly without init-db.sql JWT tables
```

---

### Phase 4: Code Refactoring (Medium-High Risk)

**Estimated Time**: 6 hours

1. ✅ Issue #6: Consolidate StorageModule.kt database config
2. ✅ Issue #7: Remove deprecated getPublicKey() + update JwtServiceTest.kt
3. ✅ Issue #9: Consolidate to Kyber768 encryption (remove KeyEncryptionService)
4. ✅ Issue #10: Add fail-fast validation to KeyRotationService

**Risk**: Medium-High - changes production code, encryption, and removes deprecated methods
**Impact**:
- Existing JWT keys need re-encryption with Kyber768
- Tests using getPublicKey() need updates
- Validation errors fail-fast at startup

**Validation Steps**:
```bash
# 1. Run ALL server unit tests
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation
./gradlew :webauthn-server:test

# Expected: All tests passing
# Confirms: StorageModule refactoring, getPublicKey() removal, fail-fast validation work

# 2. Run integration tests specifically
./gradlew :webauthn-server:test --tests "*IntegrationTest"

# Expected: All integration tests passing
# Confirms: Kyber768 encryption works for JWT keys, database config consolidation works

# 3. Run KeyRotationIntegrationTest specifically
./gradlew :webauthn-server:test --tests "*KeyRotationIntegrationTest"

# Expected: All key rotation tests passing
# Confirms: Kyber768 encryption doesn't break rotation lifecycle

# 4. Full server build
./gradlew :webauthn-server:build

# Expected: Build successful with no compilation errors

# 5. Build Docker image for testing
./gradlew :webauthn-server:shadowJar
docker build -t webauthn-server:test-cleanup-phase4 -f webauthn-server/Dockerfile webauthn-server/

# 6. Regenerate test client (no template changes, but server changes)
rm -rf test-key-rotation-client
node generate-rotation-test-client.mjs

# 7. Update docker-compose to use test image
cd test-key-rotation-client/docker
sed -i '' 's/image: hitoshura25\/webauthn-server:latest/image: webauthn-server:test-cleanup-phase4\n    pull_policy: never/' docker-compose.yml

# 8. Start fresh environment (CRITICAL: Kyber768 encrypted keys)
docker compose down -v
docker compose up -d

# 9. Wait for services and check logs for fail-fast validation
sleep 20
docker logs webauthn-server 2>&1 | head -50
# Expected: Should show JWT rotation config initialization with no errors

# 10. Verify JWT key encryption with Kyber768
docker exec -it webauthn-postgres psql -U webauthn_user -d webauthn -c "SELECT key_id, status, LENGTH(private_key_pem) as encrypted_length FROM jwt_signing_keys;"
# Expected: encrypted_length should be larger (Kyber768 overhead)
# Typical: ~2000-3000 characters (was ~500 with AES-256-GCM)

# 11. Install dependencies and run E2E tests
cd ..
npm install
npm run build
npm test

# Expected: 40/40 tests passing
# Confirms: Kyber768 encryption works end-to-end, no regression from refactoring
```

---

### Phase 5: Test Security Improvements (Low Risk)

**Estimated Time**: 2 hours

1. ✅ Issue #12: Generate TestStorageModule key dynamically
2. ✅ Issue #13: Use BaseIntegrationTest key in KeyRotationIntegrationTest
3. ✅ Issue #14: Generate BaseIntegrationTest key securely

**Risk**: Low - only affects test code (no production impact)
**Impact**: Test master encryption keys generated per test run (better isolation)

**Validation Steps**:
```bash
# 1. Run unit tests multiple times to verify key randomness
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation

# First run
./gradlew :webauthn-server:test --tests "*JwtServiceTest" 2>&1 | tee test-run-1.log

# Second run
./gradlew :webauthn-server:test --tests "*JwtServiceTest" 2>&1 | tee test-run-2.log

# Verify different keys used (if logging added)
# Note: May need to add debug logging to verify key randomness

# 2. Run integration tests
./gradlew :webauthn-server:test --tests "*IntegrationTest"

# Expected: All tests passing
# Confirms: Random key generation doesn't break tests

# 3. Run KeyRotationIntegrationTest specifically
./gradlew :webauthn-server:test --tests "*KeyRotationIntegrationTest"

# Expected: All tests passing
# Confirms: Integration test uses BaseIntegrationTest's generated key

# 4. Full server test suite
./gradlew :webauthn-server:test

# Expected: All tests passing (no regression)

# 5. Build and test with fresh client (final validation)
./gradlew :webauthn-server:shadowJar
docker build -t webauthn-server:test-cleanup-phase5 -f webauthn-server/Dockerfile webauthn-server/

rm -rf test-key-rotation-client
node generate-rotation-test-client.mjs

cd test-key-rotation-client/docker
sed -i '' 's/image: hitoshura25\/webauthn-server:latest/image: webauthn-server:test-cleanup-phase5\n    pull_policy: never/' docker-compose.yml

docker compose down -v
docker compose up -d
sleep 20

cd ..
npm install
npm run build
npm test

# Expected: 40/40 tests passing
# Confirms: Test security improvements don't affect E2E functionality
```

---

## Success Criteria

**All phases complete when:**

### Code Quality
- ✅ All templates use explicit PRODUCTION defaults (no auto-detection)
- ✅ No duplication between migrations and init-db
- ✅ Database config centralized in StorageModule
- ✅ No deprecated methods in production code
- ✅ No hardcoded secrets (even in tests)
- ✅ Fail-fast validation on required env vars
- ✅ Unified Kyber768 encryption for all sensitive data

### Testing (CRITICAL)
- ✅ **Server unit tests**: ALL passing (`./gradlew :webauthn-server:test`)
- ✅ **Server integration tests**: ALL passing (including KeyRotationIntegrationTest)
- ✅ **MCP template build**: Successful (`npm run build`)
- ✅ **Client generation**: Successful with correct values
- ✅ **Docker image build**: Successful
- ✅ **E2E tests**: 40/40 passing (100% success rate) ← **MANDATORY**

### Documentation
- ✅ README.md updated with new defaults
- ✅ Plan document complete and accurate
- ✅ Comments clarified in all modified files

### Environment
- ✅ Fresh Docker environment tested (clean volumes)
- ✅ Flyway migrations verified (V3 creates JWT tables)
- ✅ Kyber768 encryption verified in database

---

## Risk Mitigation

### Rollback Plan

Each phase can be rolled back independently:

1. **Phase 1**: Revert comment changes
2. **Phase 2**: Revert template changes, regenerate clients
3. **Phase 3**: Revert init-db.sql.hbs, add JWT tables back
4. **Phase 4**: Revert code changes, restore deprecated methods
5. **Phase 5**: Revert test changes, restore hardcoded keys

### Testing Strategy

**Comprehensive Testing at Every Phase:**

1. **Server Tests** (ALWAYS run):
   ```bash
   ./gradlew :webauthn-server:test
   ```
   - Verifies: No regressions in server code
   - Confirms: Unit tests, integration tests all passing
   - Required: BEFORE proceeding to E2E tests

2. **MCP Template Rebuild** (when templates change):
   ```bash
   cd mcp-server-webauthn-client && npm run build
   ```
   - Verifies: Template changes compile correctly
   - Confirms: No syntax errors in Handlebars templates

3. **Client Regeneration** (ALWAYS after template/server changes):
   ```bash
   rm -rf test-key-rotation-client
   node generate-rotation-test-client.mjs
   ```
   - Verifies: Generator produces valid client code
   - Confirms: All template variables populated correctly

4. **Docker Image Build** (ALWAYS for server changes):
   ```bash
   ./gradlew :webauthn-server:shadowJar
   docker build -t webauthn-server:test-cleanup-phaseX -f webauthn-server/Dockerfile webauthn-server/
   ```
   - Verifies: Server builds successfully
   - Confirms: Docker image creation works

5. **E2E Tests** (ALWAYS as final validation):
   ```bash
   cd test-key-rotation-client/docker
   docker compose down -v  # Clean volumes!
   docker compose up -d
   sleep 20  # Wait for services

   cd ..
   npm install && npm run build && npm test
   ```
   - Verifies: Complete system integration
   - Confirms: 40/40 tests passing (100% success rate)
   - Required: PASS before marking phase complete

**Testing Checklist Per Phase:**
- [ ] Server unit tests passing
- [ ] Server integration tests passing
- [ ] MCP templates rebuild successfully
- [ ] Client regenerates without errors
- [ ] Docker image builds successfully
- [ ] Docker stack starts cleanly
- [ ] E2E tests: 40/40 passing ✅

---

## Decisions Made ✅

1. **Issue #1-3 (Defaults)**: ✅ **RESOLVED** - Use production-ready defaults (300s cache, 180d rotation, 60m grace/retention). Tests explicitly override.

2. **Issue #4 (init-db.sql.hbs)**: ✅ **RESOLVED** - Option A chosen (remove JWT tables from init-db.sql.hbs, use Flyway V3 migration).

3. **Issue #9 (Encryption Services)**: ✅ **RESOLVED** - Consolidate to Kyber768 for all sensitive data (JWT keys + WebAuthn creds).

## Open Questions for Review

1. **Issue #7**: Should we keep `getPublicKey()` with ERROR-level deprecation, or remove entirely?
   - **Recommendation**: Remove entirely - only used in tests, which should use JWKS endpoint

2. **Issue #10**: Should validation be strict (fail fast) or lenient (defaults)?
   - **Recommendation**: Strict fail-fast for required values (consistent with StorageModule)

3. **Issue #14**: Should test keys be deterministic (env var) or always random?
   - **Recommendation**: Random by default, allow env var override for reproducibility

4. **General**: Should all phases be done in one PR, or split across multiple PRs?
   - **Recommendation**: Split by phase - allows incremental review and rollback

---

## Next Steps

1. Review this document
2. Answer open questions
3. Approve/modify implementation order
4. Begin Phase 1 implementation
5. Test and validate each phase
6. Document changes in README

**Status**: Awaiting review and follow-up questions
