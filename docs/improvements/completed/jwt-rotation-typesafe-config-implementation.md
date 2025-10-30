# JWT Rotation Duration Configuration - Typesafe Config Implementation

**Status:** Complete
**Branch:** feat/key_rotation
**Goal:** Replace multiple time-unit-specific environment variables with flexible HOCON duration format using Typesafe Config library

## Problem Statement

Current implementation uses multiple environment variables with different time units:
- `MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS` (production, 180 days)
- `MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS` (test override, 30 seconds) ← Inconsistent naming (missing "KEY")
- `MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES` (60 minutes)
- `MPO_AUTHN_JWT_KEY_RETENTION_MINUTES` (60 minutes)

**Issues:**
1. **Error-prone:** Both DAYS and SECONDS can be set, with SECONDS silently overriding DAYS
2. **Inconsistent naming:** `ROTATION_INTERVAL_SECONDS` missing "KEY" prefix
3. **Inflexible:** Need different env vars for different time units
4. **Hard to configure:** Production users see large numbers in seconds (15552000), test users see decimals in days (0.000347)
5. **Test mode detection:** Code assumes fast rotation = test mode (wrong assumption)

## Solution

Use Typesafe Config (Lightbend Config) library to support intuitive HOCON duration syntax:
- Production: `MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL="180d"` (human-readable)
- Testing: `MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL="30s"` (human-readable)
- **Single variable per duration, no ambiguity**
- **No backward compatibility:** Direct cutover, remove all legacy env vars
- **No "test mode" detection:** Universal scheduler-based activation logic

## Summary of Changes

### 1. **Add Typesafe Config Dependency**
- Explicitly add `com.typesafe:config:1.4.3` to build.gradle.kts
- Don't rely on transitive dependency from OpenTelemetry

### 2. **Replace Environment Variable Configuration**
- Remove: `MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS`, `MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS`
- Remove: `MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES`, `MPO_AUTHN_JWT_KEY_RETENTION_MINUTES`
- Add: `MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL`, `MPO_AUTHN_JWT_KEY_GRACE_PERIOD`, `MPO_AUTHN_JWT_KEY_RETENTION`
- No backward compatibility, no deprecated constants

### 3. **Implement Duration Parsing**
- Add `parseDurationFromEnv()` helper using Typesafe Config
- Parse HOCON format: "30s", "180d", "1h", "15 seconds", etc.
- Clear error messages with examples when invalid format provided

### 4. **Remove "Test Mode" Detection**
- Delete logic: `if (rotationInterval < 120s) { /* test mode */ }`
- Delete: Immediate activation with `Thread.sleep()` and `activatePendingKey()`
- `rotateKey()` now simply creates PENDING key and returns immediately

### 5. **Add Scheduler-Based Activation**
- New method: `KeyRotationService.checkAndActivatePendingKeys()`
- Called by KeyRotationScheduler every 10 seconds (fast rotation) or 1 hour (production)
- Universal logic works for all rotation speeds (30s to 180d)
- Non-blocking, idempotent, production-ready

### 6. **Update MCP Templates**
- Update docker-compose.yml.hbs to use new env var format
- Update envoy-gateway.yaml.hbs to use `{{jwks_cache_duration_seconds}}`
- Update generator.ts to use new parameter names
- Regenerate test-key-rotation-client (don't manually edit!)

### 7. **Update Integration Tests**
- Use new env var format: `MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL="30s"`
- Manually call `checkAndActivatePendingKeys()` after grace period in tests
- No more reliance on "test mode" immediate activation

### 8. **Update Documentation**
- README.md with HOCON format examples
- Clear migration notes (breaking change)
- Updated examples for production and testing

## Files Modified

| File | Changes | Lines Changed |
|------|---------|---------------|
| `build.gradle.kts` | Add Typesafe Config dependency | +2 |
| `EnvironmentVariables.kt` | Replace legacy constants with new format | -25, +8 |
| `KeyRotationService.kt` | Add parsing, remove test mode, add scheduler method | -80, +120 |
| `KeyRotationScheduler.kt` | Add checkAndActivatePendingKeys() call | +1 |
| `KeyRotationIntegrationTest.kt` | Update to new format + manual activation | ~30 |
| `docker-compose.yml.hbs` | Update template env vars | -10, +4 |
| `envoy-gateway.yaml.hbs` | Parameterize JWKS cache duration | -1, +1 |
| `generator.ts` | Update parameter names and defaults | ~15 |
| `README.md` | Update documentation with new format | ~50 |

**Total:** ~350 lines changed across 9 files

## Implementation Details

---

## 1. Add Explicit Typesafe Config Dependency

### File: `webauthn-server/build.gradle.kts`

**Current Status:** Available transitively via OpenTelemetry (version 1.4.2)
**Action:** Add explicit dependency declaration

#### Change 1: Add Version Variable

**Location:** After line 53 (after `jwtVersion` declaration)

```kotlin
val jwtVersion = "0.12.6"
val typesafeConfigVersion = "1.4.3"  // ADD THIS LINE
```

#### Change 2: Add Dependency

**Location:** After line 89 (after JWT dependency in `dependencies` block)

```kotlin
// JWT Token Management
implementation("com.nimbusds:nimbus-jose-jwt:$jwtVersion")

// ADD THESE LINES:
// Duration parsing (HOCON format: "30s", "180d", "1h", etc.)
implementation("com.typesafe:config:$typesafeConfigVersion")
```

**Rationale:** Explicit dependency ensures we control the version and don't rely on transitive dependencies that could change.

---

## 2. Update Environment Variable Constants

### File: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/config/EnvironmentVariables.kt`

**Current lines 31-45:** Multiple time-unit-specific constants
**Action:** Replace with new unified constants, remove all legacy constants

#### Complete Replacement (lines 31-42)

```kotlin
// JWT Key Rotation Configuration
const val MPO_AUTHN_JWT_KEY_ROTATION_ENABLED = "MPO_AUTHN_JWT_KEY_ROTATION_ENABLED"

// Duration format (HOCON syntax: "30s", "180d", "1h", etc.)
// Supported units: s (seconds), m (minutes), h (hours), d (days)
const val MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL = "MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL"
const val MPO_AUTHN_JWT_KEY_GRACE_PERIOD = "MPO_AUTHN_JWT_KEY_GRACE_PERIOD"
const val MPO_AUTHN_JWT_KEY_RETENTION = "MPO_AUTHN_JWT_KEY_RETENTION"

// Other JWT configuration
const val MPO_AUTHN_JWT_KEY_SIZE = "MPO_AUTHN_JWT_KEY_SIZE"
const val MPO_AUTHN_JWT_KEY_ID_PREFIX = "MPO_AUTHN_JWT_KEY_ID_PREFIX"
const val MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY = "MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY"
```

**Changes:**
- ✅ Added new HOCON format constants
- ❌ **Removed all legacy constants** (no backward compatibility)
- ✅ Consistent naming: All use `MPO_AUTHN_JWT_KEY_*` prefix

---

## 3. Implement Duration Parsing in KeyRotationService

### File: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/security/KeyRotationService.kt`

#### Change 1: Add Imports (at top of file, after existing imports)

```kotlin
import com.typesafe.config.ConfigFactory
import com.typesafe.config.ConfigException
```

#### Change 2: Add Duration Parsing Helper Function

**Location:** After line 49 (after logger declaration, before configuration properties)

```kotlin
/**
 * Parse duration from environment variable using Typesafe Config (HOCON format).
 *
 * Supported formats:
 * - With unit suffix: "30s", "180d", "2h", "60m"
 * - With spaces: "30 seconds", "180 days", "2 hours", "60 minutes"
 * - Singular/plural: "1 second", "2 seconds"
 *
 * Supported units:
 * - ns, nano, nanos, nanosecond, nanoseconds
 * - us, micro, micros, microsecond, microseconds
 * - ms, milli, millis, millisecond, milliseconds
 * - s, second, seconds
 * - m, minute, minutes
 * - h, hour, hours
 * - d, day, days
 *
 * @param envVarName Name of environment variable (for error messages)
 * @param value Value to parse (e.g., "30s", "180d")
 * @return Parsed java.time.Duration
 * @throws IllegalArgumentException if format is invalid
 */
private fun parseDurationFromEnv(
    envVarName: String,
    value: String
): Duration {
    return try {
        // Parse as HOCON config with temporary key
        // Typesafe Config's getDuration() returns java.time.Duration directly (as of 1.4.x)
        val config = ConfigFactory.parseString("temp = $value")
        config.getDuration("temp")
    } catch (e: ConfigException.BadValue) {
        throw IllegalArgumentException(
            """
            $envVarName has invalid duration format: '$value'

            Expected format: <number><unit>
            Examples: '30s', '180d', '2h', '60m', '1 hour', '30 seconds'

            Supported units:
              • s, second, seconds
              • m, minute, minutes
              • h, hour, hours
              • d, day, days

            Original error: ${e.message}
            """.trimIndent(),
            e
        )
    } catch (e: ConfigException) {
        throw IllegalArgumentException(
            "$envVarName could not be parsed: '$value'. " +
            "Ensure the value follows HOCON duration format (e.g., '30s', '180d').",
            e
        )
    }
}
```

#### Change 3: Replace Configuration Property Declarations

**Location:** Lines 61-110 (replace existing configuration declarations)

```kotlin
// Configuration from environment variables with fail-fast validation
private val rotationEnabled: Boolean =
    (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
        ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
        ?: "false").also { value ->
        require(value in listOf("true", "false")) {
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED} must be 'true' or 'false', got: '$value'"
        }
    }.toBoolean()

/**
 * JWT key rotation interval (HOCON duration format).
 * Examples: "30s" (30 seconds), "180d" (180 days), "2h" (2 hours)
 * Default: "180d" (6 months)
 */
private val rotationInterval: Duration =
    parseDurationFromEnv(
        EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL,
        System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL)
            ?: "180d"
    )

/**
 * Grace period before retiring old key after rotation (HOCON duration format).
 * Examples: "1h" (1 hour), "15s" (15 seconds)
 * Default: "1h" (1 hour)
 */
private val gracePeriod: Duration =
    parseDurationFromEnv(
        EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD,
        System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD)
            ?: "1h"
    )

/**
 * Retention period for retired keys before deletion (HOCON duration format).
 * Examples: "1h" (1 hour), "30s" (30 seconds), "24h" (24 hours)
 * Default: "1h" (1 hour)
 */
private val retentionPeriod: Duration =
    parseDurationFromEnv(
        EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION,
        System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION)
            ?: "1h"
    )

// Remaining configuration properties stay the same
private val keySize: Int =
    (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE)
        ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE)
        ?: "2048").also { value ->
        require(value.toIntOrNull() in listOf(2048, 4096)) {
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE} must be 2048 or 4096, got: '$value'"
        }
    }.toInt()

private val keyIdPrefix: String =
    (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX)
        ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX)
        ?: "webauthn").also { value ->
        require(value.isNotBlank()) {
            "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX} cannot be blank"
        }
    }
```

**Changes:**
- ❌ **Removed all backward compatibility logic** (no legacy env var support)
- ✅ Simple, direct duration parsing with defaults
- ✅ Clear documentation of format and defaults
- ✅ Fails immediately if env var is set but invalid

#### Change 4: Update Init Block Logging

**Location:** Lines 137-145 (update logging to use Duration objects directly)

```kotlin
init {
    logger.info("KeyRotationService initialized with configuration:")
    logger.info("  Rotation enabled: $rotationEnabled")
    logger.info("  Rotation interval: $rotationInterval")
    logger.info("  Grace period: $gracePeriod")
    logger.info("  Retention period: $retentionPeriod")
    logger.info("  Key size: $keySize bits")
    logger.info("  Key ID prefix: '$keyIdPrefix'")
}
```

#### Change 5: Update checkAndRotateIfNeeded Method

**Location:** Lines 258-261 (already correct, but verify variable names)

```kotlin
val keyAge = Duration.between(activeKey.activatedAt ?: activeKey.createdAt, Instant.now())

if (keyAge >= rotationInterval) {
    logger.info("Key rotation needed. Key age: $keyAge, Rotation interval: $rotationInterval")
    rotateKey(reason = "Automatic rotation - key age ($keyAge) exceeded threshold ($rotationInterval)")
} else {
    logger.debug("No rotation needed. Key age: $keyAge, Rotation interval: $rotationInterval")
}
```

#### Change 6: Remove "Test Mode" Detection - Use Scheduler for All Activation

**Location:** Lines 288-338 (update rotateKey method)

**Problem:** Current code assumes `rotationInterval < 2 minutes` = test mode, which is a flawed assumption. Production might need fast rotation, tests might use longer intervals.

**Solution:** Remove immediate activation logic. Always let scheduler handle activation after grace period.

```kotlin
fun rotateKey(reason: String = "Manual rotation"): String {
    logger.info("Starting key rotation. Reason: $reason")

    val activeKey = keyRepository.getActiveKey()
        ?: throw IllegalStateException("No active key found for rotation")

    // Phase 1: Generate new key in PENDING status
    val newKeyId = generateKeyId()
    val newKeyPair = generateKeyPair()
    val now = Instant.now()

    val (privateKeyPem, publicKeyPem) = keyPairToPem(newKeyPair)

    val pendingKey = JwtSigningKey(
        keyId = newKeyId,
        privateKeyPem = postQuantumCrypto.encryptToString(privateKeyPem),
        publicKeyPem = publicKeyPem,
        algorithm = "RS256",
        keySize = keySize,
        status = KeyStatus.PENDING,
        createdAt = now,
        metadata = mapOf(
            "rotation_reason" to reason,
            "previous_key_id" to activeKey.keyId,
        ),
    )

    keyRepository.saveKey(pendingKey)

    // REMOVED: if/else block with "test mode" detection and immediate activation
    // NEW: Simple logging - scheduler handles all activation
    logger.info("Created PENDING key: $newKeyId (will activate after grace period: $gracePeriod)")

    return newKeyId
}
```

**Changes:**
- ❌ **Removed "test mode" detection** (rotation interval < 2 minutes check)
- ❌ **Removed immediate activation** (Thread.sleep + activatePendingKey call)
- ✅ **Universal behavior:** Works identically for fast and slow rotation
- ✅ **Non-blocking:** Returns immediately after creating PENDING key

#### Change 7: Add New Method - checkAndActivatePendingKeys()

**Location:** After cleanupExpiredKeys() method (around line 400)

**Purpose:** Scheduler periodically calls this to activate PENDING keys that have exceeded their grace period.

```kotlin
/**
 * Check for PENDING keys that have exceeded their grace period and activate them.
 * Called periodically by KeyRotationScheduler.
 *
 * This method handles all key activation, regardless of rotation speed (fast or slow).
 */
fun checkAndActivatePendingKeys() {
    val pendingKeys = keyRepository.getKeysByStatus(KeyStatus.PENDING)
    if (pendingKeys.isEmpty()) {
        logger.debug("No PENDING keys to activate")
        return
    }

    val now = Instant.now()

    pendingKeys.forEach { key ->
        val keyAge = Duration.between(key.createdAt, now)

        if (keyAge >= gracePeriod) {
            val activeKey = keyRepository.getActiveKey()
            if (activeKey != null) {
                logger.info(
                    "Activating PENDING key: ${key.keyId} (age: $keyAge >= grace period: $gracePeriod)"
                )
                activatePendingKey(key.keyId, activeKey.keyId)
            } else {
                logger.warn("No active key found - cannot activate PENDING key: ${key.keyId}")
            }
        } else {
            logger.debug(
                "PENDING key ${key.keyId} not yet ready (age: $keyAge < grace period: $gracePeriod)"
            )
        }
    }
}
```

**Changes:**
- ✅ **New method** to handle all PENDING key activation
- ✅ **Universal logic:** Works for both fast rotation (30s) and slow rotation (180d)
- ✅ **Called by scheduler:** Runs every 10 seconds (test mode) or 1 hour (production mode)
- ✅ **Idempotent:** Safe to call multiple times

#### Change 8: Update activatePendingKey Method (Optional Logging Enhancement)

**Location:** Line 380 (update logging to use Duration for clarity)

```kotlin
logger.info(
    "Phase 3 complete: Key {} is now ACTIVE. Key {} is RETIRED (expires at {} = {})",
    pendingKeyId,
    activeKeyId,
    now.plus(retentionPeriod),
    "now + $retentionPeriod"
)
```

---

## 4. Update KeyRotationScheduler

### File: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/scheduler/KeyRotationScheduler.kt`

**Action:** Add call to `checkAndActivatePendingKeys()` in scheduler loop

#### Change: Update Scheduler Loop

**Location:** Lines 46-52 (in `start()` method)

```kotlin
// Current:
while (isActive) {
    try {
        keyRotationService.checkAndRotateIfNeeded()
    } catch (e: Exception) {
        logger.error("Error during key rotation check", e)
    }
    delay(checkInterval.toMillis())
}

// Replace with:
while (isActive) {
    try {
        keyRotationService.checkAndRotateIfNeeded()
        keyRotationService.checkAndActivatePendingKeys()  // NEW: Activate PENDING keys
    } catch (e: Exception) {
        logger.error("Error during key rotation check", e)
    }
    delay(checkInterval.toMillis())
}
```

**Changes:**
- ✅ **Added scheduler call** to activate PENDING keys
- ✅ **Runs every check interval:** 10 seconds (fast rotation) or 1 hour (production)
- ✅ **Within same try/catch:** Errors handled gracefully

**Scheduler Frequency:**
- Fast rotation (`rotationInterval < 120s`): Checks every **10 seconds**
- Production rotation (`rotationInterval >= 120s`): Checks every **1 hour**

With 15-second grace period and 10-second check interval, PENDING keys activate within 15-25 seconds (grace period + up to one check interval).

---

## 5. Update MCP Docker Compose Template

### File: `mcp-server-webauthn-client/src/templates/vanilla/docker/docker-compose.yml.hbs`

**Current lines 121-125:** Uses old multi-variable format
**Action:** Replace with new unified duration format

#### Complete Replacement (lines 119-127)

```yaml
# JWT Key Rotation Configuration (HOCON duration format)
MPO_AUTHN_JWT_KEY_ROTATION_ENABLED: "{{jwt_rotation_enabled}}"
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL: "{{jwt_rotation_interval}}"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD: "{{jwt_grace_period}}"
MPO_AUTHN_JWT_KEY_RETENTION: "{{jwt_retention}}"
MPO_AUTHN_JWT_KEY_SIZE: "2048"
MPO_AUTHN_JWT_KEY_ID_PREFIX: "webauthn"
```

**Note:** Removed conditional `{{#if jwt_rotation_interval_seconds}}` logic - now uses single unified variable.

---

## 5. Update MCP Generator TypeScript

### File: `mcp-server-webauthn-client/src/lib/generator.ts`

#### Change 1: Update Interface Definition

**Location:** Lines 40-48 (update interface parameters)

```typescript
// Current:
jwt_rotation_enabled?: string;
jwt_rotation_interval_days?: string;
jwt_rotation_interval_seconds?: string;
jwt_grace_period_minutes?: string;
jwt_retention_minutes?: string;

// Replace with:
jwt_rotation_enabled?: string;
jwt_rotation_interval?: string;        // HOCON format (e.g., "180d", "30s")
jwt_grace_period?: string;             // HOCON format (e.g., "1h", "15s")
jwt_retention?: string;                // HOCON format (e.g., "1h", "30s")
jwks_cache_duration_seconds?: string;  // Already exists
```

#### Change 2: Update Default Values

**Location:** Lines 73-79 (update function parameter defaults)

```typescript
// Current:
jwt_rotation_enabled = 'true',
jwt_rotation_interval_days = '180',
jwt_rotation_interval_seconds,
jwt_grace_period_minutes = '60',
jwt_retention_minutes = '60',

// Replace with:
jwt_rotation_enabled = 'true',
jwt_rotation_interval = '180d',      // Production: 6 months
jwt_grace_period = '1h',             // Production: 1 hour
jwt_retention = '1h',                // Production: 1 hour
jwks_cache_duration_seconds = '300', // Already exists: 5 minutes
```

#### Change 3: Update Context Object

**Location:** Lines 150-160 (update context passed to Handlebars template)

```typescript
const context = {
  // ... other properties ...
  jwt_rotation_enabled,
  jwt_rotation_interval,     // NEW format
  jwt_grace_period,          // NEW format
  jwt_retention,             // NEW format
  jwks_cache_duration_seconds,
  // Remove: jwt_rotation_interval_days, jwt_rotation_interval_seconds,
  //         jwt_grace_period_minutes, jwt_retention_minutes
};
```

---

## 6. Update Integration Tests

### File: `webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/integration/KeyRotationIntegrationTest.kt`

**Action:** Update tests to use new duration format and manually trigger activation

#### Change 1: Update Test Setup

**Location:** Lines 54-65 (setupKeyRotation method)

```kotlin
@BeforeEach
fun setupKeyRotation() {
    // Clear any existing keys from database
    clearKeyTables()

    // Set up test environment with accelerated rotation using NEW duration format
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED, "true")
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL, "30s")  // 30 seconds
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD, "15s")       // 15 seconds
    System.setProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION, "30s")          // 30 seconds

    // Initialize services using Kyber768 post-quantum encryption
    keyRepository = PostgresKeyRepository(createDataSource())
    postQuantumCrypto = PostQuantumCryptographyService()
    keyRotationService = KeyRotationService(keyRepository, postQuantumCrypto)
}

@AfterEach
fun cleanupKeyRotation() {
    // Clear key rotation environment variables (NEW format)
    System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
    System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL)
    System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD)
    System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION)
    System.clearProperty(EnvironmentVariables.MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY)

    // Clear key tables
    clearKeyTables()
}
```

#### Change 2: Update Tests to Manually Trigger Activation

**Location:** Various test methods that call `rotateKey()`

```kotlin
@Test
fun `test key rotation creates PENDING key and scheduler activates it`() {
    keyRotationService.initialize()
    val initialActiveKey = keyRepository.getActiveKey()
    assertNotNull(initialActiveKey)

    // Trigger rotation (creates PENDING key, no longer activates immediately)
    val newKeyId = keyRotationService.rotateKey(reason = "Integration test")

    // Wait for grace period
    Thread.sleep(16000)  // 16 seconds (15s grace + 1s buffer)

    // Manually trigger activation (simulates scheduler)
    keyRotationService.checkAndActivatePendingKeys()

    // Verify new key is now ACTIVE
    val currentActiveKey = keyRepository.getActiveKey()
    assertNotNull(currentActiveKey)
    assertEquals(newKeyId, currentActiveKey.keyId)

    // Old key should be RETIRED
    val retiredKey = keyRepository.getKey(initialActiveKey.keyId)
    assertNotNull(retiredKey)
    assertEquals(KeyStatus.RETIRED, retiredKey.status)
}
```

**Apply similar pattern to all tests that wait for activation (lines 133-154, 234-258, 356-379)**

---

## 7. Update MCP Templates (IMPORTANT: Regenerate, Don't Edit Manually)

**CRITICAL:** The `test-key-rotation-client/` directory is a **generated folder**. Do NOT manually edit files in this directory.

**Workflow:**
1. Update MCP templates in `mcp-server-webauthn-client/src/templates/`
2. Rebuild MCP server: `cd mcp-server-webauthn-client && npm run build`
3. Delete generated test client: `rm -rf test-key-rotation-client`
4. Regenerate with MCP CLI: `node mcp-server-webauthn-client/dist/cli.js --path test-key-rotation-client --jwt-rotation-interval 30s --jwt-grace-period 15s --jwt-retention 30s --jwks-cache-duration-seconds 5`
5. Run tests to verify: `cd test-key-rotation-client && npm install && npm run build && npm test`

### Template Updates Required:

#### File 1: `mcp-server-webauthn-client/src/templates/vanilla/docker/docker-compose.yml.hbs`

**Location:** Lines 119-127

```yaml
# Current:
MPO_AUTHN_JWT_KEY_ROTATION_ENABLED: "{{jwt_rotation_enabled}}"
{{#if jwt_rotation_interval_seconds}}
MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS: "{{jwt_rotation_interval_seconds}}"
{{else}}
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS: "{{jwt_rotation_interval_days}}"
{{/if}}
MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES: "{{jwt_grace_period_minutes}}"
MPO_AUTHN_JWT_KEY_RETENTION_MINUTES: "{{jwt_retention_minutes}}"

# Replace with (NEW format):
MPO_AUTHN_JWT_KEY_ROTATION_ENABLED: "{{jwt_rotation_enabled}}"
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL: "{{jwt_rotation_interval}}"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD: "{{jwt_grace_period}}"
MPO_AUTHN_JWT_KEY_RETENTION: "{{jwt_retention}}"
```

#### File 2: `mcp-server-webauthn-client/src/templates/vanilla/docker/envoy-gateway.yaml.hbs`

**Location:** Lines 82-84 (in remote_jwks config)

```yaml
# Current:
cache_duration:
  seconds: 300

# Replace with (using template variable):
cache_duration:
  seconds: {{jwks_cache_duration_seconds}}
```

**Note:** This allows fast JWKS refresh for tests (5s) and slower refresh for production (300s)

---

## 8. Update MCP README Documentation

### File: `mcp-server-webauthn-client/README.md`

**Location:** Lines 248-273 (JWT Key Rotation Configuration section)

#### Complete Replacement

```markdown
**JWT Key Rotation Configuration (Advanced):**

The generated WebAuthn stack includes automatic JWT signing key rotation for enhanced security (always enabled). These parameters control the rotation behavior using **HOCON duration format**:

**CLI Parameters:**
- `--jwt-rotation-interval <duration>` - Time between key rotations (default: `180d` = 6 months)
- `--jwt-grace-period <duration>` - Grace period before retiring old key (default: `1h` = 1 hour)
- `--jwt-retention <duration>` - How long to keep retired keys for verification (default: `1h` = 1 hour)
- `--jwks-cache-duration-seconds <seconds>` - JWKS endpoint cache duration (default: `300` = 5 minutes)

**Duration Format (HOCON Syntax):**
- Format: `<number><unit>` (e.g., `30s`, `180d`, `2h`, `60m`)
- Supported units:
  - `s`, `second`, `seconds`
  - `m`, `minute`, `minutes`
  - `h`, `hour`, `hours`
  - `d`, `day`, `days`
- Examples: `"30s"` (30 seconds), `"2h"` (2 hours), `"180d"` (180 days), `"1 hour"` (1 hour)

**Production Example** (6-month rotation with 1-hour grace period):
```bash
npx -y @vmenon25/mcp-server-webauthn-client \
  --jwt-rotation-interval 180d \
  --jwt-grace-period 1h \
  --jwt-retention 1h \
  --jwks-cache-duration-seconds 300
```

**Testing Example** (accelerated 30-second rotation for E2E tests):
```bash
npx -y @vmenon25/mcp-server-webauthn-client \
  --jwt-rotation-interval 30s \
  --jwt-grace-period 15s \
  --jwt-retention 30s \
  --jwks-cache-duration-seconds 5
```

**How Key Rotation Works:**
1. **Initial State:** Server starts with first signing key (K1) in ACTIVE status
2. **Rotation Trigger:** After rotation interval (e.g., 180 days), server generates new key (K2)
3. **Pending Phase:** K2 is PENDING while K1 remains ACTIVE (seamless for existing tokens)
4. **Activation:** After grace period (e.g., 1 hour), K2 becomes ACTIVE, K1 becomes RETIRED
5. **Cleanup:** After retention period (e.g., 1 hour), K1 is deleted from database
6. **JWKS Endpoint:** `/.well-known/jwks.json` always serves current ACTIVE + RETIRED keys for verification

**Timeline Example (Production Settings):**
```
T+0:        K1 ACTIVE → Rotation needed
T+0:        K2 PENDING generated
T+1h:       K2 ACTIVE, K1 RETIRED (grace period expired)
T+2h:       K1 deleted (retention period expired)
T+180d:     K3 PENDING generated, cycle repeats
```

**Environment Variables (Alternative to CLI):**
```yaml
MPO_AUTHN_JWT_KEY_ROTATION_ENABLED: "true"
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL: "180d"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD: "1h"
MPO_AUTHN_JWT_KEY_RETENTION: "1h"
```

**Legacy Environment Variables (Deprecated, will be removed in v2.0):**
```yaml
# OLD (deprecated):
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS: "180"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES: "60"
MPO_AUTHN_JWT_KEY_RETENTION_MINUTES: "60"

# NEW (recommended):
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL: "180d"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD: "1h"
MPO_AUTHN_JWT_KEY_RETENTION: "1h"
```

**Why HOCON Format?**
- ✅ **Human-readable:** "180d" is clearer than 15552000 seconds or 0.000347 days
- ✅ **Flexible:** Same variable works for production (days) and testing (seconds)
- ✅ **Standard:** Industry-standard format used by Kubernetes, Spring Boot, etc.
- ✅ **Safe:** Native library parsing with clear error messages
```

---

## Verification Steps

### Step 1: Rebuild Server

```bash
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation
./gradlew clean
./gradlew :webauthn-server:build
```

**Expected:** Build successful with new Typesafe Config dependency resolved

### Step 2: Run Unit Tests

```bash
./gradlew :webauthn-server:test
```

**Expected:** All tests pass, including KeyRotationIntegrationTest with new duration format

### Step 3: Rebuild MCP Server

```bash
cd mcp-server-webauthn-client
npm run build
```

**Expected:** No TypeScript errors, templates compiled successfully

### Step 4: Build Docker Image with New Code

```bash
./gradlew :webauthn-server:shadowJar
docker build -t webauthn-server:test-typesafe-config -f webauthn-server/Dockerfile webauthn-server/
```

**Expected:** Docker image built successfully with new server code

### Step 5: Regenerate Test Client with New Templates

```bash
cd /Users/vinayakmenon/mpo-api-authn-server-key_rotation
rm -rf test-key-rotation-client
node mcp-server-webauthn-client/dist/cli.js \
  --path test-key-rotation-client \
  --jwt-rotation-interval 30s \
  --jwt-grace-period 15s \
  --jwt-retention 30s \
  --jwks-cache-duration-seconds 5
```

**Expected:** New test client generated with:
- docker-compose.yml using NEW format env vars
- envoy-gateway.yaml with 5-second JWKS cache
- All files properly templated

### Step 6: Update Test Client to Use Test Docker Image

**Edit:** `test-key-rotation-client/docker/docker-compose.yml`

```yaml
webauthn-server:
  image: webauthn-server:test-typesafe-config
  pull_policy: never
  # ... rest of config
```

### Step 7: Start Services and Run E2E Tests

```bash
cd test-key-rotation-client/docker
docker compose down -v
docker compose up -d
sleep 30  # Wait for services to be ready

cd ..
npm install
npm run build
npm test
```

**Expected:** 40/40 tests passing (100% success rate)

**Key verification points:**
- PENDING keys created by rotateKey()
- Scheduler activates PENDING keys after 15-second grace period
- Old keys retired and eventually cleaned up after 30-second retention
- All JWT rotation tests pass with scheduler-based activation

### Step 8: Verify No Legacy Environment Variables

```bash
docker compose -f test-key-rotation-client/docker/docker-compose.yml config | grep -E "(DAYS|MINUTES|ROTATION_INTERVAL_SECONDS)"
```

**Expected:** No matches (all legacy env vars removed)

### Step 9: Verify Duration Parsing Error Messages

Test invalid duration format:
```bash
docker run --rm \
  -e MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL="invalid" \
  webauthn-server:test-typesafe-config
```

**Expected:** Clear error message with examples:
```
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL has invalid duration format: 'invalid'

Expected format: <number><unit>
Examples: '30s', '180d', '2h', '60m', '1 hour', '30 seconds'

Supported units:
  • s, second, seconds
  • m, minute, minutes
  • h, hour, hours
  • d, day, days
```

---

## Migration Notes

**Breaking Change:** This is a direct cutover with NO backward compatibility.

### Configuration Changes Required

All deployments must update environment variables to use new HOCON duration format:

**Before:**
```yaml
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS: "180"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES: "60"
MPO_AUTHN_JWT_KEY_RETENTION_MINUTES: "60"
```

**After:**
```yaml
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL: "180d"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD: "1h"
MPO_AUTHN_JWT_KEY_RETENTION: "1h"
```

**For Test Environments:**

**Before:**
```yaml
MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS: "30"
```

**After:**
```yaml
MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL: "30s"
MPO_AUTHN_JWT_KEY_GRACE_PERIOD: "15s"
MPO_AUTHN_JWT_KEY_RETENTION: "30s"
```

### Deployment Impact

- ❌ Old env var names will **NOT work** (application will fail to start or use defaults)
- ✅ Clear error messages guide users to correct format
- ✅ Since feature is on `feat/key_rotation` branch (unreleased), no production impact

---

## Benefits Summary

### Before (Old Format)
- ❌ Multiple env vars per duration: `_DAYS`, `_SECONDS`, `_MINUTES`
- ❌ Error-prone: Both DAYS and SECONDS can be set simultaneously
- ❌ Inflexible: Need different vars for different units
- ❌ Inconsistent naming: `ROTATION_INTERVAL_SECONDS` vs `KEY_ROTATION_INTERVAL_DAYS`
- ❌ Hard to read: Production=15552000s, Test=0.000347d
- ❌ "Test mode" detection: Code assumes fast rotation = test (flawed)
- ❌ Blocking activation: Thread.sleep during grace period in "test mode"

### After (New Format)
- ✅ Single env var per duration: `MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL`
- ✅ Safe: Impossible to have conflicting configs
- ✅ Flexible: Same variable works for any time unit
- ✅ Consistent naming: All variables follow `MPO_AUTHN_JWT_KEY_*` pattern
- ✅ Human-readable: Production=180d, Test=30s
- ✅ Standard: Uses industry-standard HOCON format
- ✅ Native support: Typesafe Config library (battle-tested)
- ✅ Clear errors: Helpful messages guide users to correct format
- ✅ Universal scheduler: No mode assumptions, works for all rotation speeds
- ✅ Non-blocking: rotateKey() returns immediately, scheduler handles activation

---

## Risk Assessment

### Low Risk Items ✅
- Adding explicit dependency (already available transitively)
- Feature is unreleased (on `feat/key_rotation` branch, no production deployments)
- Clear error messages guide users to correct format
- Integration tests provide comprehensive coverage

### Medium Risk Items ⚠️
- **Breaking change** (no backward compatibility)
  - **Mitigation:** Feature unreleased, only affects new deployments
- MCP generator changes (affects client generation)
  - **Mitigation:** Update templates + regenerate test client + verify E2E tests pass
- Documentation updates (must be accurate and complete)
  - **Mitigation:** Code review + manual verification of all examples

### Acceptable Risk Items ✅
- Direct cutover without legacy support
  - **Justification:** Feature unreleased, cleaner codebase, no tech debt
- Scheduler-based activation for all cases
  - **Justification:** More robust architecture, works universally

### High Risk Items ❌
- None identified

---

## Timeline Estimate

- **Implementation:** 3-4 hours
- **Testing:** 2 hours
- **Documentation:** 1 hour
- **Code Review:** 1 hour
- **Total:** 7-8 hours

---

## Next Steps

1. Review this implementation document
2. Execute changes following the order in this document
3. Run verification steps after each major change
4. Update CLAUDE.md with new env var names
5. Create PR with detailed description referencing this document
6. After merge to main, monitor for any issues in production
7. Plan removal of deprecated env vars for v2.0 release

---

## References

- **Typesafe Config GitHub:** https://github.com/lightbend/config
- **HOCON Duration Format:** https://github.com/lightbend/config/blob/main/HOCON.md#duration-format
- **Java Duration API:** https://docs.oracle.com/javase/8/docs/api/java/time/Duration.html
- **Related Issue:** JWT rotation tests failing (6/40) due to timing configuration mismatch
