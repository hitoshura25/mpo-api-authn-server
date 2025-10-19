package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.security.JwtService
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import org.koin.ktor.ext.inject
import java.util.Base64

/**
 * Public key endpoint for JWT signature verification in zero-trust architecture.
 *
 * This endpoint exposes the RSA public key used to sign JWT tokens, allowing
 * downstream services (API Gateway, microservices) to verify JWT signatures
 * without contacting the WebAuthn server for every request.
 *
 * Usage:
 * 1. Downstream services fetch public key from this endpoint
 * 2. Cache public key (recommended: 5 minutes)
 * 3. Verify JWT signatures using cached public key
 * 4. Refresh public key periodically or on verification failure
 *
 * Security Model:
 * - Public key can be safely distributed (only private key signs)
 * - mTLS between services ensures key is fetched securely
 * - Services should cache key to minimize latency
 */
fun Application.configurePublicKeyRoutes() {
    routing {
        val jwtService: JwtService by inject()

        /**
         * GET /public-key
         *
         * Returns RSA public key in Base64-encoded DER format.
         * This format is compatible with most JWT libraries and can be easily
         * converted to PEM format if needed.
         *
         * Example usage (Python):
         * ```python
         * import base64
         * from cryptography.hazmat.primitives.serialization import load_der_public_key
         *
         * response = httpx.get("http://webauthn-server:8080/public-key")
         * public_key = load_der_public_key(base64.b64decode(response.text))
         * jwt.decode(token, public_key, algorithms=["RS256"])
         * ```
         *
         * Example usage (TypeScript):
         * ```typescript
         * import * as jose from 'jose'
         *
         * const response = await fetch('http://webauthn-server:8080/public-key')
         * const publicKeyDer = await response.text()
         * const publicKey = await jose.importSPKI(
         *   `-----BEGIN PUBLIC KEY-----\n${publicKeyDer}\n-----END PUBLIC KEY-----`,
         *   'RS256'
         * )
         * await jose.jwtVerify(token, publicKey)
         * ```
         *
         * @response Base64-encoded DER format public key (text/plain)
         */
        get("/public-key") {
            val publicKey = jwtService.getPublicKey()
            val encodedKey = Base64.getEncoder().encodeToString(publicKey.encoded)
            call.respondText(encodedKey)
        }
    }
}
