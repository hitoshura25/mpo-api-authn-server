package com.vmenon.mpo.api.authn.integration

import com.auth0.jwt.JWT
import com.auth0.jwt.algorithms.Algorithm
import com.vmenon.mpo.api.authn.module
import com.vmenon.mpo.api.authn.routes.JwksResponse
import com.vmenon.mpo.api.authn.security.JwtService
import com.vmenon.mpo.api.authn.testStorageModule
import com.vmenon.mpo.api.authn.utils.JacksonUtils
import io.ktor.client.request.get
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.server.testing.testApplication
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.koin.core.context.stopKoin
import org.koin.test.KoinTest
import org.koin.test.inject
import java.math.BigInteger
import java.security.KeyFactory
import java.security.interfaces.RSAPublicKey
import java.security.spec.RSAPublicKeySpec
import java.util.Base64
import kotlin.test.assertEquals
import kotlin.test.assertNotNull

/**
 * Integration tests simulating Envoy Gateway JWT verification.
 *
 * CRITICAL: These tests verify that Envoy's remote_jwks configuration
 * can successfully fetch and use our JWKS endpoint to verify JWTs.
 *
 * This test gap previously allowed broken Base64 DER format to ship
 * to production templates. Envoy expects JWKS, not Base64 DER.
 */
class EnvoyGatewayIntegrationTest : KoinTest {
    @AfterEach
    fun cleanup() {
        stopKoin()
    }

    @Test
    fun `Envoy should successfully fetch JWKS and verify JWT`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }
            val jwtService: JwtService by inject()

            // Step 1: Fetch JWKS (simulating Envoy Gateway remote_jwks)
            val jwksResponse = client.get("/.well-known/jwks.json")
            assertEquals(
                HttpStatusCode.OK,
                jwksResponse.status,
                "JWKS endpoint must be accessible to Envoy",
            )

            val jwksJson = jwksResponse.bodyAsText()
            val jwks = JacksonUtils.objectMapper.readValue(jwksJson, JwksResponse::class.java)

            // Step 2: Parse JWKS and reconstruct RSA public key (what Envoy does internally)
            val key = jwks.keys[0]
            val modulusBytes = Base64.getUrlDecoder().decode(key.n)
            val exponentBytes = Base64.getUrlDecoder().decode(key.e)

            val modulus = BigInteger(1, modulusBytes)
            val exponent = BigInteger(1, exponentBytes)

            val keySpec = RSAPublicKeySpec(modulus, exponent)
            val keyFactory = KeyFactory.getInstance("RSA")
            val publicKey = keyFactory.generatePublic(keySpec) as RSAPublicKey

            // Step 3: Create a JWT token
            val username = "envoy-test@example.com"
            val token = jwtService.createToken(username)

            // Step 4: Verify JWT using JWKS-provided public key (what Envoy does)
            val algorithm = Algorithm.RSA256(publicKey, null)
            val verifier =
                JWT.require(algorithm)
                    .withIssuer("mpo-webauthn")
                    .build()

            val decodedJwt = verifier.verify(token)

            // Assert - JWT verification should succeed
            assertEquals(
                username,
                decodedJwt.subject,
                "JWT subject should match original username",
            )
            assertEquals(
                "mpo-webauthn",
                decodedJwt.issuer,
                "JWT issuer should be mpo-webauthn",
            )
            assertNotNull(
                decodedJwt.expiresAt,
                "JWT should have expiration time",
            )
        }

    @Test
    fun `Envoy JWKS cache should work with consistent responses`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }

            // Act - Fetch JWKS twice (simulating Envoy's cache behavior)
            val response1 = client.get("/.well-known/jwks.json")
            val response2 = client.get("/.well-known/jwks.json")

            val jwks1 = JacksonUtils.objectMapper.readValue(response1.bodyAsText(), JwksResponse::class.java)
            val jwks2 = JacksonUtils.objectMapper.readValue(response2.bodyAsText(), JwksResponse::class.java)

            // Assert - Both should return identical JWKS (same key)
            // This ensures Envoy's cache_duration: 300 seconds works correctly
            assertEquals(
                jwks1.keys[0].n,
                jwks2.keys[0].n,
                "RSA modulus should be consistent across requests",
            )
            assertEquals(
                jwks1.keys[0].e,
                jwks2.keys[0].e,
                "RSA exponent should be consistent across requests",
            )
            assertEquals(
                jwks1.keys[0].kid,
                jwks2.keys[0].kid,
                "Key ID should be consistent across requests",
            )
        }

    @Test
    fun `JWKS endpoint should support Envoy HTTP client requirements`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }

            // Act - Request JWKS with typical Envoy headers
            val response =
                client.get("/.well-known/jwks.json") {
                    // Envoy adds these headers
                    headers.append("User-Agent", "envoy")
                    headers.append("Accept", "application/json")
                }

            // Assert
            assertEquals(HttpStatusCode.OK, response.status)
            assertEquals(
                ContentType.Application.Json.contentType,
                response.contentType()?.contentType,
                "Content-Type must be application/json for Envoy",
            )
        }

    @Test
    fun `Multiple JWT verifications should work with single JWKS fetch`() =
        testApplication {
            // Arrange - Simulates Envoy caching JWKS for multiple requests
            application { module(testStorageModule) }
            val jwtService: JwtService by inject()

            // Fetch JWKS once (Envoy caches for 5 minutes)
            val jwksResponse = client.get("/.well-known/jwks.json")
            val jwks = JacksonUtils.objectMapper.readValue(jwksResponse.bodyAsText(), JwksResponse::class.java)
            val key = jwks.keys[0]

            // Reconstruct public key from JWKS
            val modulusBytes = Base64.getUrlDecoder().decode(key.n)
            val exponentBytes = Base64.getUrlDecoder().decode(key.e)
            val modulus = BigInteger(1, modulusBytes)
            val exponent = BigInteger(1, exponentBytes)
            val keySpec = RSAPublicKeySpec(modulus, exponent)
            val keyFactory = KeyFactory.getInstance("RSA")
            val publicKey = keyFactory.generatePublic(keySpec) as RSAPublicKey

            val algorithm = Algorithm.RSA256(publicKey, null)
            val verifier = JWT.require(algorithm).withIssuer("mpo-webauthn").build()

            // Act - Verify multiple tokens with same JWKS (simulating Envoy cache)
            val token1 = jwtService.createToken("user1@example.com")
            val token2 = jwtService.createToken("user2@example.com")
            val token3 = jwtService.createToken("user3@example.com")

            val decoded1 = verifier.verify(token1)
            val decoded2 = verifier.verify(token2)
            val decoded3 = verifier.verify(token3)

            // Assert - All tokens should verify successfully
            assertEquals("user1@example.com", decoded1.subject)
            assertEquals("user2@example.com", decoded2.subject)
            assertEquals("user3@example.com", decoded3.subject)
        }
}
