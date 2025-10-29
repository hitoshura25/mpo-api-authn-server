package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.security.KeyRotationService
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.response.header
import io.ktor.server.response.respond
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import org.koin.ktor.ext.inject
import java.io.StringReader
import java.security.KeyFactory
import java.security.interfaces.RSAPublicKey
import java.security.spec.X509EncodedKeySpec
import java.util.Base64
import org.bouncycastle.util.io.pem.PemReader

/**
 * JWKS (JSON Web Key Set) endpoint for OAuth2/OIDC-compliant JWT verification.
 *
 * Returns public keys in JWKS format (RFC 7517) for:
 * - Envoy Gateway remote_jwks configuration
 * - Modern JWT libraries (PyJWKClient, jose, go-jose)
 * - Automatic key rotation support (multiple keys during rotation)
 * - Industry standard OAuth2/OIDC pattern
 *
 * Key Rotation Support:
 * - Returns ACTIVE + RETIRED keys during rotation
 * - Clients use 'kid' (Key ID) from JWT header to select correct key
 * - Cache-Control headers optimize client-side caching
 * - Graceful rotation with zero client impact
 *
 * Standard endpoint path: /.well-known/jwks.json
 * This path is recognized by OAuth2/OIDC clients and API gateways.
 */
fun Application.configureJwksRoutes() {
    routing {
        val keyRotationService: KeyRotationService by inject()

        /**
         * GET /.well-known/jwks.json
         *
         * Returns JWKS (JSON Web Key Set) containing all publishable RSA public keys.
         * Format: RFC 7517 compliant JWKS
         *
         * During key rotation, this endpoint returns multiple keys:
         * - ACTIVE key (currently used for signing new tokens)
         * - RETIRED keys (still valid for verifying existing tokens)
         *
         * Example response (single key):
         * {
         *   "keys": [
         *     {
         *       "kty": "RSA",
         *       "use": "sig",
         *       "kid": "webauthn-2025-10-24",
         *       "alg": "RS256",
         *       "n": "0vx7agoebGcQSuuPiLJXZpt...",  // Base64URL-encoded modulus
         *       "e": "AQAB"                          // Base64URL-encoded exponent
         *     }
         *   ]
         * }
         *
         * Example response (during rotation):
         * {
         *   "keys": [
         *     { "kid": "webauthn-2025-10-24", ... },  // ACTIVE key
         *     { "kid": "webauthn-2024-01", ... }      // RETIRED key
         *   ]
         * }
         *
         * Cache-Control Header:
         * - max-age=300 (5 minutes) - Standard cache duration
         * - stale-if-error=3600 (1 hour) - Serve stale keys if endpoint fails
         * - public - Allow shared caching (CDN, proxies)
         *
         * Usage by downstream services:
         * - Envoy Gateway: Configure remote_jwks.http_uri to this endpoint
         * - Python: Use PyJWKClient("http://server/.well-known/jwks.json")
         * - Node.js: Use jose.createRemoteJWKSet(new URL("http://server/.well-known/jwks.json"))
         * - Go: Use jwk.Fetch(ctx, "http://server/.well-known/jwks.json")
         */
        get("/.well-known/jwks.json") {
            // Get all publishable keys (ACTIVE + RETIRED)
            val keys = keyRotationService.getAllPublishableKeys()

            // Convert each key to JWKS format
            val jwksList =
                keys.map { key ->
                    // Parse PEM-encoded public key
                    val publicKey = loadPublicKeyFromPem(key.publicKeyPem)

                    // Extract RSA components and encode as Base64URL (RFC 7517 requirement)
                    val modulus =
                        Base64.getUrlEncoder().withoutPadding()
                            .encodeToString(publicKey.modulus.toByteArray())
                    val exponent =
                        Base64.getUrlEncoder().withoutPadding()
                            .encodeToString(publicKey.publicExponent.toByteArray())

                    JsonWebKey(
                        kty = "RSA",
                        use = "sig",
                        kid = key.keyId, // Dynamic key ID from database
                        alg = key.algorithm,
                        n = modulus,
                        e = exponent,
                    )
                }

            // Build JWKS response
            val jwks = JwksResponse(keys = jwksList)

            // Add Cache-Control header for optimal client caching
            call.response.header(
                "Cache-Control",
                "max-age=300, stale-if-error=3600, public",
            )

            call.respond(HttpStatusCode.OK, jwks)
        }
    }
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
