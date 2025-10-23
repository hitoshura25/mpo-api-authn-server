package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.security.JwtService
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.response.respond
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import org.koin.ktor.ext.inject
import java.security.interfaces.RSAPublicKey
import java.util.Base64

/**
 * JWKS (JSON Web Key Set) endpoint for OAuth2/OIDC-compliant JWT verification.
 *
 * Returns public key in JWKS format (RFC 7517) for:
 * - Envoy Gateway remote_jwks configuration
 * - Modern JWT libraries (PyJWKClient, jose, go-jose)
 * - Key rotation support (multiple keys with 'kid')
 * - Industry standard OAuth2/OIDC pattern
 *
 * Standard endpoint path: /.well-known/jwks.json
 * This path is recognized by OAuth2/OIDC clients and API gateways.
 */
fun Application.configureJwksRoutes() {
    routing {
        val jwtService: JwtService by inject()

        /**
         * GET /.well-known/jwks.json
         *
         * Returns JWKS (JSON Web Key Set) containing RSA public key.
         * Format: RFC 7517 compliant JWKS
         *
         * Example response:
         * {
         *   "keys": [
         *     {
         *       "kty": "RSA",
         *       "use": "sig",
         *       "kid": "webauthn-2024-01",
         *       "alg": "RS256",
         *       "n": "0vx7agoebGcQSuuPiLJXZpt...",  // Base64URL-encoded modulus
         *       "e": "AQAB"                          // Base64URL-encoded exponent
         *     }
         *   ]
         * }
         *
         * Usage by downstream services:
         * - Envoy Gateway: Configure remote_jwks.http_uri to this endpoint
         * - Python: Use PyJWKClient("http://server/.well-known/jwks.json")
         * - Node.js: Use jose.createRemoteJWKSet(new URL("http://server/.well-known/jwks.json"))
         * - Go: Use jwk.Fetch(ctx, "http://server/.well-known/jwks.json")
         */
        get("/.well-known/jwks.json") {
            val publicKey = jwtService.getPublicKey() as RSAPublicKey

            // Extract RSA components and encode as Base64URL (RFC 7517 requirement)
            val modulus =
                Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(publicKey.modulus.toByteArray())
            val exponent =
                Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(publicKey.publicExponent.toByteArray())

            // Build JWKS response
            val jwks =
                JwksResponse(
                    keys =
                        listOf(
                            JsonWebKey(
                                kty = "RSA",
                                use = "sig",
                                kid = "webauthn-2024-01", // Key ID for rotation support
                                alg = "RS256",
                                n = modulus,
                                e = exponent,
                            ),
                        ),
                )

            call.respond(HttpStatusCode.OK, jwks)
        }
    }
}

/**
 * JWKS Response format (RFC 7517)
 * Serialized by Jackson (no annotation required)
 */
data class JwksResponse(val keys: List<JsonWebKey>)

/**
 * JSON Web Key format (RFC 7517)
 * Serialized by Jackson (no annotation required)
 */
data class JsonWebKey(
    val kty: String, // Key Type (RSA, EC, OKP)
    val use: String, // Public Key Use (sig=signature, enc=encryption)
    val kid: String, // Key ID (for rotation)
    val alg: String, // Algorithm (RS256, ES256, etc)
    val n: String, // RSA Modulus (Base64URL without padding)
    val e: String, // RSA Exponent (Base64URL without padding)
)
