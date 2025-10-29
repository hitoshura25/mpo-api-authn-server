package com.vmenon.mpo.api.authn.security

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import com.vmenon.mpo.api.authn.model.JwtSigningKey
import com.vmenon.mpo.api.authn.model.KeyStatus
import com.vmenon.mpo.api.authn.repository.KeyRepository
import org.slf4j.LoggerFactory
import java.io.StringReader
import java.io.StringWriter
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.interfaces.RSAPrivateKey
import java.security.interfaces.RSAPublicKey
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.X509EncodedKeySpec
import java.time.Duration
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Base64
import org.bouncycastle.util.io.pem.PemObject
import org.bouncycastle.util.io.pem.PemReader
import org.bouncycastle.util.io.pem.PemWriter

/**
 * Core service for JWT key rotation management.
 *
 * Implements a 4-phase key lifecycle:
 * 1. **PENDING**: Newly generated, published in JWKS during grace period
 * 2. **ACTIVE**: Currently used for signing new tokens
 * 3. **RETIRED**: No longer signs, but still verifies existing tokens
 * 4. **DELETED**: Removed from JWKS and database
 *
 * Features:
 * - Automatic time-based rotation (configurable interval)
 * - Manual rotation trigger for emergency scenarios
 * - Graceful transition with zero client impact
 * - Quantum-resistant encryption for private keys (Kyber768 + AES-256-GCM)
 * - Complete audit trail
 *
 * @property keyRepository Database access for key storage
 * @property postQuantumCrypto Post-quantum encryption service for private keys
 */
class KeyRotationService(
    private val keyRepository: KeyRepository,
    private val postQuantumCrypto: PostQuantumCryptographyService,
) {
    private val logger = LoggerFactory.getLogger(KeyRotationService::class.java)

    // Configuration from environment variables with fail-fast validation
    private val rotationEnabled: Boolean =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED)
            ?: "false").also { value ->
            require(value in listOf("true", "false")) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_ENABLED} must be 'true' or 'false', got: '$value'"
            }
        }.toBoolean()

    private val rotationIntervalDays: Long =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS)
            ?: "180").also { value ->
            val days = value.toLongOrNull()
                ?: throw IllegalArgumentException(
                    "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS} must be a valid number, got: '$value'",
                )
            require(days > 0) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS} must be positive, got: $days"
            }
        }.toLong()

    private val rotationIntervalSeconds: Long? =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS))?.also { value ->
            val seconds = value.toLongOrNull()
                ?: throw IllegalArgumentException(
                    "${EnvironmentVariables.MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS} must be a valid number, got: '$value'",
                )
            require(seconds > 0) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS} must be positive, got: $seconds"
            }
        }?.toLong()

    private val gracePeriodMinutes: Double =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES)
            ?: "60").also { value ->
            val minutes = value.toDoubleOrNull()
                ?: throw IllegalArgumentException(
                    "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES} must be a valid number, got: '$value'",
                )
            require(minutes > 0) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES} must be positive, got: $minutes"
            }
        }.toDouble()

    private val retentionAfterRetirementMinutes: Double =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES)
            ?: "60").also { value ->
            val minutes = value.toDoubleOrNull()
                ?: throw IllegalArgumentException(
                    "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES} must be a valid number, got: '$value'",
                )
            require(minutes > 0) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_RETENTION_MINUTES} must be positive, got: $minutes"
            }
        }.toDouble()

    private val keySize: Int =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE)
            ?: "2048").also { value ->
            val size = value.toIntOrNull()
                ?: throw IllegalArgumentException(
                    "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE} must be a valid integer, got: '$value'",
                )
            require(size in listOf(2048, 3072, 4096)) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_SIZE} must be 2048, 3072, or 4096, got: $size"
            }
        }.toInt()

    private val keyIdPrefix: String =
        (System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX)
            ?: "webauthn").also { value ->
            require(value.isNotBlank()) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX} cannot be blank"
            }
            require(value.matches(Regex("^[a-z0-9-]+$"))) {
                "${EnvironmentVariables.MPO_AUTHN_JWT_KEY_ID_PREFIX} must contain only lowercase letters, numbers, and hyphens, got: '$value'"
            }
        }

    init {
        logger.info("KeyRotationService initialized with configuration:")
        logger.info("  Rotation enabled: $rotationEnabled")
        logger.info("  Rotation interval: ${rotationIntervalSeconds?.let { "${it}s (test mode)" } ?: "${rotationIntervalDays}d (production)"}")
        logger.info("  Grace period: ${gracePeriodMinutes}min")
        logger.info("  Retention: ${retentionAfterRetirementMinutes}min")
        logger.info("  Key size: ${keySize} bits")
        logger.info("  Key ID prefix: '$keyIdPrefix'")
    }

    // In-memory cache for active key
    @Volatile
    private var cachedActiveKey: Pair<String, KeyPair>? = null

    /**
     * Get the current active signing key.
     * Returns cached key if available, otherwise loads from database.
     *
     * @return Pair of (keyId, KeyPair) for the active signing key
     * @throws IllegalStateException if no active key exists
     */
    fun getActiveSigningKey(): Pair<String, KeyPair> {
        // Return cached key if available
        cachedActiveKey?.let {
            logger.debug("Returning cached active key: ${it.first}")
            return it
        }

        // Load from database
        logger.debug("Loading active key from database...")
        val activeKey =
            keyRepository.getActiveKey()
                ?: throw IllegalStateException("No active signing key found. Run initialization first.")

        logger.debug("Retrieved active key from DB: keyId=${activeKey.keyId}, status=${activeKey.status}")
        logger.debug("Encrypted private key JSON length: ${activeKey.privateKeyPem.length} bytes")

        logger.debug("Decrypting private key...")
        val decryptedPrivateKeyPem = postQuantumCrypto.decryptFromString(activeKey.privateKeyPem)
        logger.debug("Decrypted private key PEM length: ${decryptedPrivateKeyPem.length} bytes")

        val privateKey = loadPrivateKeyFromPem(decryptedPrivateKeyPem)
        val publicKey = loadPublicKeyFromPem(activeKey.publicKeyPem)
        val keyPair = KeyPair(publicKey, privateKey)

        // Cache for future use
        cachedActiveKey = Pair(activeKey.keyId, keyPair)
        logger.info("✅ Loaded and cached active signing key: ${activeKey.keyId}")

        return Pair(activeKey.keyId, keyPair)
    }

    /**
     * Initialize key rotation system.
     * Creates initial ACTIVE key if none exists (backward compatibility).
     *
     * This method is safe to call multiple times - it only creates a key if none exists.
     */
    fun initialize() {
        val activeKey = keyRepository.getActiveKey()

        if (activeKey == null) {
            logger.info("No active key found. Creating initial key for backward compatibility...")

            // Generate backward-compatible key ID
            val keyId = "webauthn-2024-01" // Maintain existing ID for compatibility
            logger.info("Generated key ID: $keyId")

            val keyPair = generateKeyPair()
            val now = Instant.now()

            val (privateKeyPem, publicKeyPem) = keyPairToPem(keyPair)
            logger.debug("Private key PEM length: ${privateKeyPem.length} bytes")
            logger.debug("Public key PEM length: ${publicKeyPem.length} bytes")

            val encryptedPrivateKey = postQuantumCrypto.encryptToString(privateKeyPem)
            logger.debug("Encrypted private key JSON length: ${encryptedPrivateKey.length} bytes")

            val key =
                JwtSigningKey(
                    keyId = keyId,
                    privateKeyPem = encryptedPrivateKey,
                    publicKeyPem = publicKeyPem,
                    algorithm = "RS256",
                    keySize = keySize,
                    status = KeyStatus.ACTIVE,
                    createdAt = now,
                    activatedAt = now,
                    metadata = mapOf("initial_key" to true, "backward_compatible" to true),
                )

            logger.info("Saving key to repository: keyId=$keyId, status=${key.status}")
            keyRepository.saveKey(key)
            cachedActiveKey = Pair(keyId, keyPair)
            logger.info("✅ Created initial active key: $keyId")
        } else {
            logger.info("Active key already exists: ${activeKey.keyId}")
        }
    }

    /**
     * Check if rotation is needed and trigger if so.
     * Called by KeyRotationScheduler background job.
     *
     * Rotation criteria:
     * - Rotation must be enabled
     * - Active key age must exceed rotation interval
     */
    fun checkAndRotateIfNeeded() {
        if (!rotationEnabled) {
            logger.debug("Key rotation is disabled")
            return
        }

        val activeKey =
            keyRepository.getActiveKey() ?: run {
                logger.warn("No active key found during rotation check")
                return
            }

        // Calculate rotation interval (test mode uses seconds, production uses days)
        val rotationInterval =
            rotationIntervalSeconds?.let { Duration.ofSeconds(it) }
                ?: Duration.ofDays(rotationIntervalDays)

        val keyAge = Duration.between(activeKey.activatedAt ?: activeKey.createdAt, Instant.now())

        if (keyAge >= rotationInterval) {
            logger.info("Key rotation needed. Key age: $keyAge, Threshold: $rotationInterval")
            rotateKey(reason = "Automatic rotation - key age exceeded threshold")
        } else {
            logger.debug("No rotation needed. Key age: $keyAge, Threshold: $rotationInterval")
        }

        // Also cleanup expired keys
        cleanupExpiredKeys()
    }

    /**
     * Manually trigger key rotation.
     * Used for emergency rotation or admin-initiated rotation.
     *
     * Implements graceful 4-phase rotation:
     * 1. Generate new PENDING key
     * 2. Publish in JWKS (grace period)
     * 3. Activate new key, retire old key
     * 4. Delete expired retired key
     *
     * @param reason Reason for rotation (logged in audit trail)
     * @return Key ID of the newly generated key
     */
    fun rotateKey(reason: String = "Manual rotation"): String {
        logger.info("Starting key rotation. Reason: $reason")

        val activeKey =
            keyRepository.getActiveKey()
                ?: throw IllegalStateException("No active key found for rotation")

        // Phase 1: Generate new key in PENDING status
        val newKeyId = generateKeyId()
        val newKeyPair = generateKeyPair()
        val now = Instant.now()

        val (privateKeyPem, publicKeyPem) = keyPairToPem(newKeyPair)

        val pendingKey =
            JwtSigningKey(
                keyId = newKeyId,
                privateKeyPem = postQuantumCrypto.encryptToString(privateKeyPem),
                publicKeyPem = publicKeyPem,
                algorithm = "RS256",
                keySize = keySize,
                status = KeyStatus.PENDING,
                createdAt = now,
                metadata =
                    mapOf(
                        "rotation_reason" to reason,
                        "previous_key_id" to activeKey.keyId,
                    ),
            )

        keyRepository.saveKey(pendingKey)
        logger.info("Phase 1 complete: Generated PENDING key: $newKeyId")

        // Phase 2: Grace period
        // JWKS now returns both keys (handled automatically by getAllPublishableKeys())
        logger.info("Phase 2: Grace period started. Duration: $gracePeriodMinutes minutes")

        // In test mode with fast rotation, activate immediately after short grace period
        if (rotationIntervalSeconds != null && rotationIntervalSeconds < 120) {
            // Test mode: Use shorter grace period (30 seconds or half of rotation interval)
            val testGracePeriodSeconds = minOf(30L, rotationIntervalSeconds / 2)
            logger.info("Test mode detected: Using accelerated grace period of $testGracePeriodSeconds seconds")
            Thread.sleep(testGracePeriodSeconds * 1000)
            activatePendingKey(newKeyId, activeKey.keyId)
        } else {
            // Production mode: Pending key will be activated by scheduler after grace period
            logger.info("Production mode: Pending key will be activated by scheduler after grace period")
        }

        return newKeyId
    }

    /**
     * Activate a PENDING key and retire the current ACTIVE key.
     * Called by scheduler after grace period, or immediately in test mode.
     *
     * Phase 3 of rotation:
     * - New key becomes ACTIVE
     * - Old key becomes RETIRED
     * - Old key expiration time set
     *
     * @param pendingKeyId Key ID of the PENDING key to activate
     * @param activeKeyId Key ID of the current ACTIVE key to retire
     */
    fun activatePendingKey(
        pendingKeyId: String,
        activeKeyId: String,
    ) {
        val now = Instant.now()
        val retentionDuration = Duration.ofSeconds((retentionAfterRetirementMinutes * 60).toLong())

        logger.info("Phase 3: Activating key $pendingKeyId and retiring key $activeKeyId")

        // CRITICAL: Retire old key FIRST to avoid violating single_active_key constraint
        // We must not have two ACTIVE keys simultaneously
        keyRepository.updateKeyStatus(activeKeyId, KeyStatus.RETIRED, now)
        keyRepository.updateKeyExpiration(activeKeyId, now.plus(retentionDuration))

        // Now activate new key
        keyRepository.updateKeyStatus(pendingKeyId, KeyStatus.ACTIVE, now)

        // Clear cache to force reload of new active key
        cachedActiveKey = null

        logger.info(
            "Phase 3 complete: Key {} is now ACTIVE. Key {} is RETIRED (expires at {})",
            pendingKeyId,
            activeKeyId,
            now.plus(retentionDuration)
        )
    }

    /**
     * Cleanup expired RETIRED keys.
     * Called periodically by scheduler.
     *
     * Phase 4 of rotation:
     * - Remove keys past their expiration time
     * - Keys are permanently deleted from database
     */
    fun cleanupExpiredKeys() {
        val retiredKeys = keyRepository.getKeysByStatus(KeyStatus.RETIRED)
        val now = Instant.now()

        retiredKeys.forEach { key ->
            if (key.expiresAt != null && now.isAfter(key.expiresAt)) {
                logger.info("Phase 4: Cleaning up expired key: ${key.keyId} (expired at ${key.expiresAt})")
                keyRepository.deleteKey(key.keyId)
            }
        }
    }

    /**
     * Get all keys for JWKS endpoint (ACTIVE + RETIRED).
     * Called by JwksRoutes to generate the JWKS response.
     *
     * @return List of keys to publish in JWKS
     */
    fun getAllPublishableKeys(): List<JwtSigningKey> {
        return keyRepository.getAllActiveAndRetiredKeys()
    }

    /**
     * Generate a unique key ID with timestamp.
     * Format: {prefix}-YYYY-MM-DD-HHmmss
     *
     * Example: webauthn-2025-10-24-143052
     */
    private fun generateKeyId(): String {
        val timestamp =
            DateTimeFormatter.ofPattern("yyyy-MM-dd-HHmmss")
                .format(Instant.now().atZone(ZoneId.systemDefault()))
        return "$keyIdPrefix-$timestamp"
    }

    /**
     * Generate a new RSA key pair.
     *
     * @return KeyPair with the configured key size
     */
    private fun generateKeyPair(): KeyPair {
        return KeyPairGenerator.getInstance("RSA").apply {
            initialize(keySize)
        }.generateKeyPair()
    }

    /**
     * Convert a KeyPair to PEM format.
     *
     * @return Pair of (privateKeyPem, publicKeyPem)
     */
    private fun keyPairToPem(keyPair: KeyPair): Pair<String, String> {
        // Private key (PKCS#8 format)
        val privateKeyWriter = StringWriter()
        PemWriter(privateKeyWriter).use { writer ->
            writer.writeObject(PemObject("PRIVATE KEY", keyPair.private.encoded))
        }
        val privateKeyPem = privateKeyWriter.toString()

        // Public key (X.509 SubjectPublicKeyInfo format)
        val publicKeyWriter = StringWriter()
        PemWriter(publicKeyWriter).use { writer ->
            writer.writeObject(PemObject("PUBLIC KEY", keyPair.public.encoded))
        }
        val publicKeyPem = publicKeyWriter.toString()

        return Pair(privateKeyPem, publicKeyPem)
    }

    /**
     * Load an RSA private key from PEM format.
     *
     * @param pem PEM-encoded private key
     * @return RSAPrivateKey instance
     */
    private fun loadPrivateKeyFromPem(pem: String): RSAPrivateKey {
        val pemReader = PemReader(StringReader(pem))
        val pemObject = pemReader.readPemObject()
        pemReader.close()

        val keySpec = PKCS8EncodedKeySpec(pemObject.content)
        return KeyFactory.getInstance("RSA").generatePrivate(keySpec) as RSAPrivateKey
    }

    /**
     * Load an RSA public key from PEM format.
     *
     * @param pem PEM-encoded public key
     * @return RSAPublicKey instance
     */
    private fun loadPublicKeyFromPem(pem: String): RSAPublicKey {
        val pemReader = PemReader(StringReader(pem))
        val pemObject = pemReader.readPemObject()
        pemReader.close()

        val keySpec = X509EncodedKeySpec(pemObject.content)
        return KeyFactory.getInstance("RSA").generatePublic(keySpec) as RSAPublicKey
    }
}
