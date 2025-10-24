package com.vmenon.mpo.api.authn.integration

import com.auth0.jwt.JWT
import com.vmenon.mpo.api.authn.module
import com.vmenon.mpo.api.authn.routes.JwksResponse
import com.vmenon.mpo.api.authn.security.JwtService
import com.vmenon.mpo.api.authn.testStorageModule
import com.vmenon.mpo.api.authn.utils.JacksonUtils
import io.ktor.client.request.get
import io.ktor.client.statement.bodyAsText
import io.ktor.server.testing.testApplication
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.koin.core.context.stopKoin
import org.koin.test.KoinTest
import org.koin.test.inject
import kotlin.test.assertEquals
import kotlin.test.assertNotNull

/**
 * Test that verifies JWT tokens include 'kid' (Key ID) header for PyJWKClient compatibility.
 *
 * CRITICAL: This test catches missing 'kid' header issues that would break Python/Node.js/Go
 * JWT libraries expecting RFC 7515 standard JWT format.
 *
 * Background:
 * - PyJWKClient (Python) requires 'kid' in JWT header to match against JWKS
 * - Without 'kid', PyJWKClient throws: "Unable to find a signing key that matches: 'None'"
 * - This test ensures our JWT tokens are compatible with modern JWT verification libraries
 *
 * References:
 * - RFC 7515 (JSON Web Signature): Recommends 'kid' header for key identification
 * - RFC 7517 (JSON Web Key Set): Defines 'kid' parameter for key rotation
 * - PyJWT Issue #737: PyJWKClient requires 'kid' parameter
 */
class JwtKidHeaderTest : KoinTest {
    @AfterEach
    fun cleanup() {
        stopKoin()
    }

    @Test
    fun `JWT token should include kid header matching JWKS kid value`() =
        testApplication {
            // Arrange
            application { module(testStorageModule) }
            val jwtService: JwtService by inject()

            // Step 1: Fetch JWKS and extract expected kid
            val jwksResponse = client.get("/.well-known/jwks.json")
            val jwks = JacksonUtils.objectMapper.readValue(jwksResponse.bodyAsText(), JwksResponse::class.java)
            val expectedKid = jwks.keys[0].kid

            // Step 2: Create JWT token
            val username = "kid-test@example.com"
            val token = jwtService.createToken(username)

            // Step 3: Decode JWT header WITHOUT verification (just parsing)
            // This is what PyJWKClient does to extract the kid
            val decodedJwt = JWT.decode(token)

            // Step 4: Assert kid header is present
            assertNotNull(
                decodedJwt.keyId,
                "JWT header MUST include 'kid' (Key ID) for PyJWKClient compatibility. " +
                    "Without 'kid', Python JWT libraries fail with: " +
                    "\"Unable to find a signing key that matches: 'None'\". " +
                    "Fix: Add .withKeyId(\"$expectedKid\") to JWT.create() in JwtService.createToken()",
            )

            // Step 5: Assert kid matches JWKS kid
            assertEquals(
                expectedKid,
                decodedJwt.keyId,
                "JWT 'kid' header must match JWKS 'kid' value. " +
                    "JWKS advertises kid='$expectedKid', but JWT has kid='${decodedJwt.keyId}'. " +
                    "This mismatch will cause JWT verification failures in downstream services.",
            )

            // Step 6: Assert audience claim is present (required by Envoy Gateway)
            assertNotNull(
                decodedJwt.audience,
                "JWT MUST include 'aud' (audience) claim for Envoy Gateway JWT filter. " +
                    "Without 'aud', Envoy returns 403 Forbidden with error='invalid_token'. " +
                    "Fix: Add .withAudience(\"webauthn-clients\") to JWT.create() in JwtService.createToken()",
            )

            // Step 7: Assert audience matches Envoy configuration
            assertEquals(
                listOf("webauthn-clients"),
                decodedJwt.audience,
                "JWT 'aud' claim must match Envoy Gateway configuration. " +
                    "Envoy expects aud='webauthn-clients', but JWT has aud='${decodedJwt.audience}'. " +
                    "This mismatch will cause 403 Forbidden errors on all protected API calls.",
            )
        }
}
