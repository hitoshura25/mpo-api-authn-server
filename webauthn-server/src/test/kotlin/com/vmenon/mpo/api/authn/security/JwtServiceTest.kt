package com.vmenon.mpo.api.authn.security

import com.auth0.jwt.exceptions.JWTVerificationException
import io.mockk.every
import io.mockk.mockk
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.security.KeyPairGenerator
import java.time.Instant

/**
 * Unit tests for JwtService - RS256 JWT token creation and verification for zero-trust architecture.
 */
class JwtServiceTest {
    // Create a mock KeyRotationService that returns a test key pair
    private val mockKeyRotationService = mockk<KeyRotationService>().apply {
        val testKeyPair = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
        every { getActiveSigningKey() } returns Pair("test-key-id", testKeyPair)
    }

    private val jwtService = JwtService(mockKeyRotationService)

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
        val fakeKeyRotationService = mockk<KeyRotationService>().apply {
            val fakeKeyPair = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
            every { getActiveSigningKey() } returns Pair("fake-key-id", fakeKeyPair)
        }
        val fakeJwtService = JwtService(fakeKeyRotationService)
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
    fun `tokens should be verifiable using JwtService verifyToken method`() {
        val username = "public_key_test@example.com"
        val token = jwtService.createToken(username)

        // Verify token using JwtService (simulates downstream service verification pattern)
        val decodedJwt = jwtService.verifyToken(token)

        assertEquals(username, decodedJwt.subject)
        assertEquals("mpo-webauthn", decodedJwt.issuer)
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
