package com.vmenon.mpo.api.authn.model

import java.time.Instant

/**
 * Represents a JWT signing key stored in the database.
 *
 * Keys progress through a 4-phase lifecycle:
 * 1. PENDING: Newly generated, published in JWKS but not used for signing (grace period)
 * 2. ACTIVE: Currently used for signing new tokens
 * 3. RETIRED: No longer used for signing, but still in JWKS for verification
 * 4. DELETED: Removed from JWKS and database after retention period
 *
 * @property keyId Unique identifier for the key (e.g., "webauthn-2025-10-24")
 * @property privateKeyPem Encrypted private key in PEM format (encrypted at application level)
 * @property publicKeyPem Public key in PEM format (published in JWKS, not encrypted)
 * @property algorithm Signing algorithm (RS256, RS384, RS512)
 * @property keySize Key size in bits (2048, 3072, 4096)
 * @property status Current lifecycle state
 * @property createdAt When the key was generated
 * @property activatedAt When the key became ACTIVE (null if never activated)
 * @property retiredAt When the key became RETIRED (null if never retired)
 * @property expiresAt When the key should be deleted (set when retired)
 * @property metadata Additional metadata (rotation reason, policy version, etc.)
 */
data class JwtSigningKey(
    val keyId: String,
    val privateKeyPem: String,
    val publicKeyPem: String,
    val algorithm: String = "RS256",
    val keySize: Int = 2048,
    val status: KeyStatus,
    val createdAt: Instant,
    val activatedAt: Instant? = null,
    val retiredAt: Instant? = null,
    val expiresAt: Instant? = null,
    val metadata: Map<String, Any>? = null,
)

/**
 * Lifecycle states for JWT signing keys.
 *
 * State transitions:
 * ```
 * PENDING → ACTIVE → RETIRED → DELETED
 * ```
 *
 * - **PENDING**: Newly generated key published in JWKS during grace period
 * - **ACTIVE**: Current key used for signing new JWTs
 * - **RETIRED**: Previous key no longer used for signing but still verifies tokens
 * - **DELETED**: Expired key removed from JWKS and database
 */
enum class KeyStatus {
    /** Newly generated, published in JWKS but not yet used for signing (grace period) */
    PENDING,

    /** Currently used for signing new JWT tokens */
    ACTIVE,

    /** No longer used for signing, but still available in JWKS for token verification */
    RETIRED,

    /** Removed from JWKS and database after retention period */
    DELETED,
}

/**
 * Represents an audit log entry for JWT key lifecycle events.
 *
 * @property id Database-generated ID
 * @property keyId The key this event relates to
 * @property event Type of event that occurred
 * @property timestamp When the event occurred
 * @property metadata Additional context (admin user, rotation reason, etc.)
 */
data class JwtKeyAuditLog(
    val id: Long? = null,
    val keyId: String,
    val event: KeyEvent,
    val timestamp: Instant = Instant.now(),
    val metadata: Map<String, Any>? = null,
)

/**
 * Types of events in the JWT key lifecycle.
 *
 * Used for audit logging and monitoring.
 */
enum class KeyEvent {
    /** Key was generated */
    GENERATED,

    /** Key was promoted to ACTIVE status */
    ACTIVATED,

    /** Key was demoted to RETIRED status */
    RETIRED,

    /** Key was permanently deleted */
    DELETED,

    /** Manual rotation was triggered by an administrator */
    MANUAL_ROTATION,
}
