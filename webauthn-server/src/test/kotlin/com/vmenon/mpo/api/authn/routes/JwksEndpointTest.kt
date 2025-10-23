package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.module
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
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for JWKS endpoint - ensures format compliance and Envoy compatibility
 */
class JwksEndpointTest : KoinTest {
    @AfterEach
    fun cleanup() {
        stopKoin()
    }

    @Test
    fun `JWKS endpoint should return valid JWKS format`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }

            // Act
            val response = client.get("/.well-known/jwks.json")

            // Assert
            assertEquals(HttpStatusCode.OK, response.status)
            assertEquals(ContentType.Application.Json, response.contentType()?.withoutParameters())

            val jwks = JacksonUtils.objectMapper.readValue(response.bodyAsText(), JwksResponse::class.java)
            assertTrue(jwks.keys.isNotEmpty(), "JWKS should contain at least one key")

            val key = jwks.keys[0]
            assertEquals("RSA", key.kty, "Key type should be RSA")
            assertEquals("sig", key.use, "Key use should be 'sig' (signature)")
            assertEquals("RS256", key.alg, "Algorithm should be RS256")
            assertNotNull(key.kid, "Key ID (kid) should be present")
            assertNotNull(key.n, "RSA modulus (n) should be present")
            assertNotNull(key.e, "RSA exponent (e) should be present")
        }

    @Test
    fun `JWKS modulus should be Base64URL encoded without padding`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }

            // Act
            val response = client.get("/.well-known/jwks.json")
            val jwks = JacksonUtils.objectMapper.readValue(response.bodyAsText(), JwksResponse::class.java)
            val key = jwks.keys[0]

            // Assert - Base64URL should not contain +, /, or = characters
            assertFalse(key.n.contains('+'), "Modulus should use Base64URL (no + character)")
            assertFalse(key.n.contains('/'), "Modulus should use Base64URL (no / character)")
            assertFalse(key.n.contains('='), "Modulus should not have padding (no = character)")

            assertFalse(key.e.contains('+'), "Exponent should use Base64URL (no + character)")
            assertFalse(key.e.contains('/'), "Exponent should use Base64URL (no / character)")
            assertFalse(key.e.contains('='), "Exponent should not have padding (no = character)")
        }

    @Test
    fun `JWKS key ID should be consistent across requests`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }

            // Act
            val response1 = client.get("/.well-known/jwks.json")
            val response2 = client.get("/.well-known/jwks.json")

            val jwks1 = JacksonUtils.objectMapper.readValue(response1.bodyAsText(), JwksResponse::class.java)
            val jwks2 = JacksonUtils.objectMapper.readValue(response2.bodyAsText(), JwksResponse::class.java)

            // Assert - Same JwtService instance should return same kid
            assertEquals(
                jwks1.keys[0].kid,
                jwks2.keys[0].kid,
                "Key ID should be consistent across requests",
            )
        }

    @Test
    fun `JWKS endpoint should be publicly accessible without authentication`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }

            // Act - Request without Authorization header
            val response = client.get("/.well-known/jwks.json")

            // Assert - Should work without authentication (Envoy needs public access)
            assertEquals(
                HttpStatusCode.OK,
                response.status,
                "JWKS endpoint must be publicly accessible for Envoy Gateway",
            )
        }
}
