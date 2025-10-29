package com.vmenon.mpo.api.authn.security

import com.auth0.jwt.JWT
import com.auth0.jwt.algorithms.Algorithm
import com.auth0.jwt.interfaces.DecodedJWT
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.interfaces.RSAPrivateKey
import java.security.interfaces.RSAPublicKey
import java.time.Instant
import java.util.Date

/**
 * JWT service using RS256 asymmetric signing for zero-trust architecture.
 * Provides JWT token creation and public key export for downstream service verification.
 *
 * Security Features:
 * - RS256 (RSA 2048-bit+) asymmetric algorithm
 * - 15-minute token expiration (900 seconds)
 * - Automatic key rotation with database persistence
 * - Public keys distributed via JWKS endpoint
 *
 * Usage in Zero-Trust Architecture:
 * 1. WebAuthn server issues signed JWT on successful authentication
 * 2. API Gateway validates JWT signature using JWKS endpoint
 * 3. Downstream services verify JWT using JWKS endpoint
 * 4. All service-to-service communication secured via mTLS (handled by service mesh)
 *
 * Key Rotation:
 * - Keys are stored in PostgreSQL with encrypted private keys
 * - Active key used for signing (retrieved from KeyRotationService)
 * - Multiple keys published in JWKS during rotation (ACTIVE + RETIRED)
 *
 * @property keyRotationService Service for managing key lifecycle and rotation
 */
class JwtService(
    private val keyRotationService: KeyRotationService,
) {
    companion object {
        private const val ISSUER = "mpo-webauthn"
        private const val AUDIENCE = "webauthn-clients" // JWT audience for Envoy Gateway validation
        private const val TOKEN_EXPIRY_SECONDS = 900L // 15 minutes
    }

    /**
     * Create signed JWT token for authenticated user.
     *
     * Token Claims:
     * - iss (issuer): "mpo-webauthn"
     * - aud (audience): "webauthn-clients" (required by Envoy Gateway)
     * - sub (subject): username (e.g., "user@example.com")
     * - iat (issued at): Current timestamp
     * - exp (expires): iat + 15 minutes
     * - kid (key ID): Dynamic from active signing key (JWT header for PyJWKClient)
     *
     * Uses the current ACTIVE signing key from the rotation service.
     * During rotation, the active key changes automatically without requiring code changes.
     *
     * @param username The authenticated user's username
     * @return RS256-signed JWT token string
     */
    fun createToken(username: String): String {
        val now = Instant.now()
        val expiry = now.plusSeconds(TOKEN_EXPIRY_SECONDS)

        // Get current active signing key (keyId + KeyPair)
        val (keyId, keyPair) = keyRotationService.getActiveSigningKey()

        // Create algorithm with active key
        val algorithm =
            Algorithm.RSA256(
                keyPair.public as RSAPublicKey,
                keyPair.private as RSAPrivateKey,
            )

        return JWT.create()
            .withIssuer(ISSUER)
            .withAudience(AUDIENCE) // Required by Envoy Gateway JWT filter
            .withSubject(username)
            .withIssuedAt(Date.from(now))
            .withExpiresAt(Date.from(expiry))
            .withKeyId(keyId) // Dynamic kid from active key
            .sign(algorithm)
    }

    /**
     * Verify JWT token signature and claims.
     *
     * This method is used for:
     * 1. Internal server-side token validation (e.g., API endpoint authentication)
     * 2. Testing and validation scenarios
     * 3. Scenarios where the caller explicitly uses the JWKS endpoint for key rotation awareness
     *
     * For distributed client applications, prefer using a JWKS-aware JWT library that
     * automatically fetches and caches public keys from the /.well-known/jwks.json endpoint.
     * This ensures clients automatically handle key rotation without code changes.
     *
     * Limitations:
     * - Only verifies using the CURRENT active key (does not check retired keys during grace period)
     * - For grace period support, clients must use JWKS endpoint which publishes all valid keys
     *
     * @param token JWT token string
     * @return Decoded JWT with verified signature and claims
     * @throws com.auth0.jwt.exceptions.JWTVerificationException if token is invalid
     */
    fun verifyToken(token: String): DecodedJWT {
        // Get active signing key for verification
        val (_, keyPair) = keyRotationService.getActiveSigningKey()

        val algorithm =
            Algorithm.RSA256(
                keyPair.public as RSAPublicKey,
                keyPair.private as RSAPrivateKey,
            )

        return JWT.require(algorithm)
            .withIssuer(ISSUER)
            .build()
            .verify(token)
    }
}
