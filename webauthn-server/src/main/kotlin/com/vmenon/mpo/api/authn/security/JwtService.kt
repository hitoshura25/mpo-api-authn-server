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
 * - RS256 (RSA 2048-bit) asymmetric algorithm
 * - 15-minute token expiration (900 seconds)
 * - Public key can be exported for service mesh JWT verification
 *
 * Usage in Zero-Trust Architecture:
 * 1. WebAuthn server issues signed JWT on successful authentication
 * 2. API Gateway validates JWT signature using public key
 * 3. Downstream services can optionally verify JWT using public key
 * 4. All service-to-service communication secured via mTLS (handled by service mesh)
 */
class JwtService {
    private val keyPair: KeyPair by lazy {
        KeyPairGenerator.getInstance("RSA").apply {
            initialize(RSA_KEY_SIZE)
        }.generateKeyPair()
    }

    private val algorithm by lazy {
        Algorithm.RSA256(
            keyPair.public as RSAPublicKey,
            keyPair.private as RSAPrivateKey,
        )
    }

    companion object {
        private const val ISSUER = "mpo-webauthn"
        private const val AUDIENCE = "webauthn-clients" // JWT audience for Envoy Gateway validation
        private const val TOKEN_EXPIRY_SECONDS = 900L // 15 minutes
        private const val RSA_KEY_SIZE = 2048 // RSA-2048 for JWT signing
        private const val KEY_ID = "webauthn-2024-01" // JWKS Key ID for PyJWKClient compatibility
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
     * - kid (key ID): "webauthn-2024-01" (JWT header for PyJWKClient)
     *
     * @param username The authenticated user's username
     * @return RS256-signed JWT token string
     */
    fun createToken(username: String): String {
        val now = Instant.now()
        val expiry = now.plusSeconds(TOKEN_EXPIRY_SECONDS)

        return JWT.create()
            .withIssuer(ISSUER)
            .withAudience(AUDIENCE) // Required by Envoy Gateway JWT filter
            .withSubject(username)
            .withIssuedAt(Date.from(now))
            .withExpiresAt(Date.from(expiry))
            .withKeyId(KEY_ID) // Add kid header for PyJWKClient compatibility
            .sign(algorithm)
    }

    /**
     * Verify JWT token signature and claims.
     * Used for internal testing and validation.
     *
     * @param token JWT token string
     * @return Decoded JWT with verified signature and claims
     * @throws com.auth0.jwt.exceptions.JWTVerificationException if token is invalid
     */
    fun verifyToken(token: String): DecodedJWT {
        return JWT.require(algorithm)
            .withIssuer(ISSUER)
            .build()
            .verify(token)
    }

    /**
     * Get RSA public key for JWT signature verification.
     * This key should be distributed to downstream services via /public-key endpoint.
     *
     * Downstream services use this key to verify JWT signatures without
     * contacting the WebAuthn server for every request (zero-trust validation).
     *
     * @return RSA public key (2048-bit)
     */
    fun getPublicKey(): RSAPublicKey = keyPair.public as RSAPublicKey
}
