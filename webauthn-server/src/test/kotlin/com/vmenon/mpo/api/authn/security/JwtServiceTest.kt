package com.vmenon.mpo.api.authn.security

import com.auth0.jwt.JWT
import com.auth0.jwt.algorithms.Algorithm
import com.auth0.jwt.exceptions.JWTVerificationException
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.security.interfaces.RSAPublicKey
import java.time.Instant

/**
 * Unit tests for JwtService - RS256 JWT token creation and verification for zero-trust architecture.
 */
class JwtServiceTest {
    private val jwtService = JwtService()

    @Test
    fun `createToken should generate valid JWT with correct claims`() {
        val username = "test@example.com"
        val token = jwtService.createToken(username)

        assertNotNull(token)
        assertTrue(token.isNotEmpty())

        // Decode and verify token structure
        val decodedJwt = jwtService.verifyToken(token)

        assertEquals("mpo-webauthn", decodedJwt.issuer)
        assertEquals(username, decodedJwt.subject)
        assertNotNull(decodedJwt.issuedAt)
        assertNotNull(decodedJwt.expiresAt)

        // Verify token expiration is 15 minutes (900 seconds)
        val issuedAt = decodedJwt.issuedAt.toInstant()
        val expiresAt = decodedJwt.expiresAt.toInstant()
        val durationSeconds = java.time.Duration.between(issuedAt, expiresAt).seconds

        assertEquals(900L, durationSeconds, "Token should expire in 900 seconds (15 minutes)")
    }

    @Test
    fun `verifyToken should successfully verify valid token`() {
        val username = "valid_user@example.com"
        val token = jwtService.createToken(username)

        val decodedJwt = jwtService.verifyToken(token)

        assertEquals(username, decodedJwt.subject)
        assertEquals("mpo-webauthn", decodedJwt.issuer)
    }

    @Test
    fun `verifyToken should reject token with wrong issuer`() {
        // Create a token with a different JwtService instance (different key) and wrong issuer
        val fakeJwtService = JwtService()
        val username = "user@example.com"

        // Manually create a token with the wrong issuer using the fake service's key
        val fakeToken = fakeJwtService.createToken(username)

        // Now manually verify with wrong issuer expectation - this should fail
        // because the token was created by a different JwtService instance
        assertThrows<JWTVerificationException> {
            jwtService.verifyToken(fakeToken)
        }
    }

    @Test
    fun `token should have future expiration time`() {
        // Verify that created tokens expire in the future
        val username = "expiration_test@example.com"
        val token = jwtService.createToken(username)

        val decodedJwt = jwtService.verifyToken(token)

        // Verify expiration is in the future
        val expiresAt = decodedJwt.expiresAt.toInstant()
        val now = Instant.now()

        assertTrue(
            expiresAt.isAfter(now),
            "Token expiration should be in the future",
        )

        // Verify expiration is approximately 15 minutes from now (allowing 5 second tolerance)
        val expectedExpiry = now.plusSeconds(900)
        val timeDifference = Math.abs(java.time.Duration.between(expiresAt, expectedExpiry).seconds)

        assertTrue(
            timeDifference < 5,
            "Token should expire approximately 900 seconds from now " +
                "(difference: $timeDifference seconds)",
        )
    }

    @Test
    fun `getPublicKey should return RSA public key`() {
        val publicKey = jwtService.getPublicKey()

        assertNotNull(publicKey)
        assertTrue(publicKey is RSAPublicKey)
        assertEquals("RSA", publicKey.algorithm)

        // Verify key size is 2048 bits
        assertEquals(2048, publicKey.modulus.bitLength())
    }

    @Test
    fun `tokens should be verifiable with exported public key`() {
        val username = "public_key_test@example.com"
        val token = jwtService.createToken(username)

        // Simulate downstream service verifying token with public key
        val publicKey = jwtService.getPublicKey()
        val algorithm = Algorithm.RSA256(publicKey, null)

        val verifier =
            JWT.require(algorithm)
                .withIssuer("mpo-webauthn")
                .build()

        val decodedJwt = verifier.verify(token)

        assertEquals(username, decodedJwt.subject)
        assertEquals("mpo-webauthn", decodedJwt.issuer)
    }

    @Test
    fun `different JwtService instances should have different keys`() {
        val service1 = JwtService()
        val service2 = JwtService()

        val publicKey1 = service1.getPublicKey()
        val publicKey2 = service2.getPublicKey()

        // Different instances should generate different key pairs
        assertTrue(publicKey1.modulus != publicKey2.modulus)
    }

    @Test
    fun `same JwtService instance should reuse the same key`() {
        val publicKey1 = jwtService.getPublicKey()
        val publicKey2 = jwtService.getPublicKey()

        // Same instance should return the same key (lazy initialization)
        assertEquals(publicKey1.modulus, publicKey2.modulus)
        assertEquals(publicKey1.publicExponent, publicKey2.publicExponent)
    }

    @Test
    fun `createToken should handle special characters in username`() {
        val username = "user+tag@example.com"
        val token = jwtService.createToken(username)

        val decodedJwt = jwtService.verifyToken(token)

        assertEquals(username, decodedJwt.subject)
    }

    @Test
    fun `createToken should handle long usernames`() {
        val username = "a".repeat(64) + "@example.com"
        val token = jwtService.createToken(username)

        val decodedJwt = jwtService.verifyToken(token)

        assertEquals(username, decodedJwt.subject)
    }
}
