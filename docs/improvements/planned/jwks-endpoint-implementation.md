# JWKS Endpoint Implementation Plan

## Problem Summary

1. **❌ Envoy Gateway is broken**: `remote_jwks` expects JWKS format, but `/public-key` returns Base64 DER
2. **❌ No integration test exists**: Test gap allowed this breakage to reach production templates
3. **❌ Non-standard format**: Base64 DER is not industry standard (should be JWKS or PEM)

## Background

Current implementation returns Base64-encoded DER format from `/public-key` endpoint. This creates integration friction:
- Envoy Gateway's `remote_jwks` configuration expects JWKS format (RFC 7517)
- Modern JWT libraries prefer JWKS (PyJWKClient, jose, go-jose)
- OAuth2/OIDC industry standard is `/.well-known/jwks.json`
- No tests verify Envoy Gateway compatibility

## Solution Overview

**Replace `/public-key` with `/.well-known/jwks.json`**

Benefits:
- ✅ Works with Envoy Gateway immediately
- ✅ Industry standard OAuth2/OIDC pattern
- ✅ Future key rotation support (multiple keys with `kid`)
- ✅ Automatic library support (PyJWKClient, jose)
- ✅ Self-describing format (includes metadata)

---

## Phase 1: Introduce JWKS Endpoint

### 1.1 Create New JwksRoutes.kt

**File**: `/webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/routes/JwksRoutes.kt`

**Implementation**:
```kotlin
package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.security.JwtService
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.response.respond
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import kotlinx.serialization.Serializable
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
            val modulus = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(publicKey.modulus.toByteArray())
            val exponent = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(publicKey.publicExponent.toByteArray())

            // Build JWKS response
            val jwks = JwksResponse(
                keys = listOf(
                    JsonWebKey(
                        kty = "RSA",
                        use = "sig",
                        kid = "webauthn-2024-01",  // Key ID for rotation support
                        alg = "RS256",
                        n = modulus,
                        e = exponent
                    )
                )
            )

            call.respond(HttpStatusCode.OK, jwks)
        }
    }
}

/**
 * JWKS Response format (RFC 7517)
 */
@Serializable
data class JwksResponse(val keys: List<JsonWebKey>)

/**
 * JSON Web Key format (RFC 7517)
 */
@Serializable
data class JsonWebKey(
    val kty: String,    // Key Type (RSA, EC, OKP)
    val use: String,    // Public Key Use (sig=signature, enc=encryption)
    val kid: String,    // Key ID (for rotation)
    val alg: String,    // Algorithm (RS256, ES256, etc)
    val n: String,      // RSA Modulus (Base64URL without padding)
    val e: String       // RSA Exponent (Base64URL without padding)
)
```

### 1.2 Register JWKS Routes

**File**: `/webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/Application.kt`

Add after existing route configurations:
```kotlin
configureJwksRoutes()
```

---

## Phase 2: Remove /public-key Endpoint

### 2.1 Delete PublicKeyRoutes.kt

**File to delete**: `/webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/routes/PublicKeyRoutes.kt`

**Reason**: Replaced by JWKS endpoint. No production consumers exist (all internal templates).

### 2.2 Remove from Application.kt

**File**: `/webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/Application.kt`

Remove line: `configurePublicKeyRoutes()`

---

## Phase 3: Update Tests (CRITICAL - This Was Missing!)

### 3.1 Create JwksEndpointTest.kt

**File**: `/webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/routes/JwksEndpointTest.kt`

**Purpose**: Verify JWKS format compliance and structure

```kotlin
package com.vmenon.mpo.api.authn.routes

import io.ktor.client.request.get
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.server.testing.testApplication
import kotlinx.serialization.json.Json
import org.junit.jupiter.api.Test
import org.koin.test.KoinTest
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Tests for JWKS endpoint - ensures format compliance and Envoy compatibility
 */
class JwksEndpointTest : KoinTest {

    @Test
    fun `JWKS endpoint should return valid JWKS format`() = testApplication {
        // Arrange
        application { module(testing = true) }

        // Act
        val response = client.get("/.well-known/jwks.json")

        // Assert
        assertEquals(HttpStatusCode.OK, response.status)
        assertEquals(ContentType.Application.Json, response.contentType())

        val jwks = Json.decodeFromString<JwksResponse>(response.bodyAsText())
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
    fun `JWKS modulus should be Base64URL encoded without padding`() = testApplication {
        // Arrange
        application { module(testing = true) }

        // Act
        val response = client.get("/.well-known/jwks.json")
        val jwks = Json.decodeFromString<JwksResponse>(response.bodyAsText())
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
    fun `JWKS key ID should be consistent across requests`() = testApplication {
        // Arrange
        application { module(testing = true) }

        // Act
        val response1 = client.get("/.well-known/jwks.json")
        val response2 = client.get("/.well-known/jwks.json")

        val jwks1 = Json.decodeFromString<JwksResponse>(response1.bodyAsText())
        val jwks2 = Json.decodeFromString<JwksResponse>(response2.bodyAsText())

        // Assert - Same JwtService instance should return same kid
        assertEquals(jwks1.keys[0].kid, jwks2.keys[0].kid,
            "Key ID should be consistent across requests")
    }

    @Test
    fun `JWKS endpoint should be publicly accessible without authentication`() = testApplication {
        // Arrange
        application { module(testing = true) }

        // Act - Request without Authorization header
        val response = client.get("/.well-known/jwks.json")

        // Assert - Should work without authentication (Envoy needs public access)
        assertEquals(HttpStatusCode.OK, response.status,
            "JWKS endpoint must be publicly accessible for Envoy Gateway")
    }
}
```

### 3.2 Create EnvoyGatewayIntegrationTest.kt (NEW - Critical Gap!)

**File**: `/webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/integration/EnvoyGatewayIntegrationTest.kt`

**Purpose**: Simulate Envoy Gateway JWT verification workflow

**Why Critical**: This test would have caught the Base64 DER bug before it reached production templates!

```kotlin
package com.vmenon.mpo.api.authn.integration

import com.auth0.jwt.JWT
import com.auth0.jwt.algorithms.Algorithm
import com.auth0.jwt.interfaces.RSAKeyProvider
import com.vmenon.mpo.api.authn.routes.JwksResponse
import com.vmenon.mpo.api.authn.security.JwtService
import io.ktor.client.request.get
import io.ktor.client.statement.bodyAsText
import io.ktor.http.HttpStatusCode
import io.ktor.server.testing.testApplication
import kotlinx.serialization.json.Json
import org.junit.jupiter.api.Test
import org.koin.test.KoinTest
import org.koin.test.inject
import java.security.interfaces.RSAPrivateKey
import java.security.interfaces.RSAPublicKey
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

    @Test
    fun `Envoy should successfully fetch JWKS and verify JWT`() = testApplication {
        // Arrange
        application { module(testing = true) }
        val jwtService: JwtService by inject()

        // Step 1: Fetch JWKS (simulating Envoy Gateway remote_jwks)
        val jwksResponse = client.get("/.well-known/jwks.json")
        assertEquals(HttpStatusCode.OK, jwksResponse.status,
            "JWKS endpoint must be accessible to Envoy")

        val jwksJson = jwksResponse.bodyAsText()
        val jwks = Json.decodeFromString<JwksResponse>(jwksJson)

        // Step 2: Parse JWKS and reconstruct RSA public key (what Envoy does internally)
        val key = jwks.keys[0]
        val modulusBytes = Base64.getUrlDecoder().decode(key.n)
        val exponentBytes = Base64.getUrlDecoder().decode(key.e)

        val modulus = java.math.BigInteger(1, modulusBytes)
        val exponent = java.math.BigInteger(1, exponentBytes)

        val keySpec = java.security.spec.RSAPublicKeySpec(modulus, exponent)
        val keyFactory = java.security.KeyFactory.getInstance("RSA")
        val publicKey = keyFactory.generatePublic(keySpec) as RSAPublicKey

        // Step 3: Create a JWT token
        val username = "envoy-test@example.com"
        val token = jwtService.createToken(username)

        // Step 4: Verify JWT using JWKS-provided public key (what Envoy does)
        val algorithm = Algorithm.RSA256(publicKey, null)
        val verifier = JWT.require(algorithm)
            .withIssuer("mpo-webauthn")
            .build()

        val decodedJwt = verifier.verify(token)

        // Assert - JWT verification should succeed
        assertEquals(username, decodedJwt.subject,
            "JWT subject should match original username")
        assertEquals("mpo-webauthn", decodedJwt.issuer,
            "JWT issuer should be mpo-webauthn")
        assertNotNull(decodedJwt.expiresAt,
            "JWT should have expiration time")
    }

    @Test
    fun `Envoy JWKS cache should work with consistent responses`() = testApplication {
        // Arrange
        application { module(testing = true) }

        // Act - Fetch JWKS twice (simulating Envoy's cache behavior)
        val response1 = client.get("/.well-known/jwks.json")
        val response2 = client.get("/.well-known/jwks.json")

        val jwks1 = Json.decodeFromString<JwksResponse>(response1.bodyAsText())
        val jwks2 = Json.decodeFromString<JwksResponse>(response2.bodyAsText())

        // Assert - Both should return identical JWKS (same key)
        // This ensures Envoy's cache_duration: 300 seconds works correctly
        assertEquals(jwks1.keys[0].n, jwks2.keys[0].n,
            "RSA modulus should be consistent across requests")
        assertEquals(jwks1.keys[0].e, jwks2.keys[0].e,
            "RSA exponent should be consistent across requests")
        assertEquals(jwks1.keys[0].kid, jwks2.keys[0].kid,
            "Key ID should be consistent across requests")
    }

    @Test
    fun `JWKS endpoint should support Envoy HTTP client requirements`() = testApplication {
        // Arrange
        application { module(testing = true) }

        // Act - Request JWKS with typical Envoy headers
        val response = client.get("/.well-known/jwks.json") {
            // Envoy adds these headers
            headers.append("User-Agent", "envoy")
            headers.append("Accept", "application/json")
        }

        // Assert
        assertEquals(HttpStatusCode.OK, response.status)
        assertEquals("application/json", response.contentType()?.contentType,
            "Content-Type must be application/json for Envoy")
    }

    @Test
    fun `Multiple JWT verifications should work with single JWKS fetch`() = testApplication {
        // Arrange - Simulates Envoy caching JWKS for multiple requests
        application { module(testing = true) }
        val jwtService: JwtService by inject()

        // Fetch JWKS once (Envoy caches for 5 minutes)
        val jwksResponse = client.get("/.well-known/jwks.json")
        val jwks = Json.decodeFromString<JwksResponse>(jwksResponse.bodyAsText())
        val key = jwks.keys[0]

        // Reconstruct public key from JWKS
        val modulusBytes = Base64.getUrlDecoder().decode(key.n)
        val exponentBytes = Base64.getUrlDecoder().decode(key.e)
        val modulus = java.math.BigInteger(1, modulusBytes)
        val exponent = java.math.BigInteger(1, exponentBytes)
        val keySpec = java.security.spec.RSAPublicKeySpec(modulus, exponent)
        val keyFactory = java.security.KeyFactory.getInstance("RSA")
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
```

### 3.3 Update Existing ApplicationTest.kt

**File**: `/webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/ApplicationTest.kt`

**Add smoke test for JWKS endpoint**:

```kotlin
@Test
fun `application should expose JWKS endpoint`() = testApplication {
    application { module(testing = true) }

    val response = client.get("/.well-known/jwks.json")
    assertEquals(HttpStatusCode.OK, response.status)
}
```

---

## Phase 4: Update MCP-Generated Templates

### 4.1 Update Envoy Gateway Configuration

**File**: `/mcp-server-webauthn-client/src/templates/vanilla/docker/envoy-gateway.yaml.hbs`

**Change (lines 72-78)**:

```yaml
# BEFORE (BROKEN - Envoy expects JWKS, not Base64 DER):
providers:
  webauthn_provider:
    issuer: "mpo-webauthn"
    audiences:
      - "webauthn-clients"
    remote_jwks:
      http_uri:
        uri: http://webauthn-server:8080/public-key  # ❌ Returns Base64 DER!
        cluster: webauthn_server
        timeout: 5s
      cache_duration:
        seconds: 300

# AFTER (CORRECT - JWKS format):
providers:
  webauthn_provider:
    issuer: "mpo-webauthn"
    audiences:
      - "webauthn-clients"
    remote_jwks:
      http_uri:
        uri: http://webauthn-server:8080/.well-known/jwks.json  # ✅ JWKS format
        cluster: webauthn_server
        timeout: 5s
      cache_duration:
        seconds: 300  # Cache JWKS for 5 minutes
```

### 4.2 Update Python Example Service

**File**: `/mcp-server-webauthn-client/src/templates/vanilla/example-service/main.py.hbs`

**Before (manual DER handling)**:
```python
import base64
from cryptography.hazmat.primitives.serialization import load_der_public_key

PUBLIC_KEY_URL = os.getenv("WEBAUTHN_PUBLIC_KEY_URL",
                          "http://webauthn-server:8080/public-key")
PUBLIC_KEY_CACHE = None

def get_public_key():
    """Fetch public key from WebAuthn server (cached)"""
    global PUBLIC_KEY_CACHE
    if PUBLIC_KEY_CACHE is None:
        try:
            response = httpx.get(PUBLIC_KEY_URL, timeout=5.0)
            response.raise_for_status()
            # Public key is Base64-encoded DER format
            public_key_der = base64.b64decode(response.text)
            PUBLIC_KEY_CACHE = load_der_public_key(public_key_der)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch public key: {str(e)}"
            )
    return PUBLIC_KEY_CACHE

def verify_jwt_token(authorization: Optional[str] = Header(None)) -> dict:
    # ... auth header validation ...

    try:
        public_key = get_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer="mpo-webauthn"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

**After (PyJWKClient - automatic JWKS handling)**:
```python
from jwt import PyJWKClient

JWKS_URL = os.getenv("WEBAUTHN_JWKS_URL",
                     "http://webauthn-server:8080/.well-known/jwks.json")

# PyJWKClient automatically fetches JWKS, caches it, and handles key rotation
jwks_client = PyJWKClient(JWKS_URL)

def verify_jwt_token(authorization: Optional[str] = Header(None)) -> dict:
    """Verify JWT from Authorization header using JWKS"""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )

    token = authorization.split(" ")[1]

    try:
        # PyJWKClient automatically:
        # 1. Fetches JWKS from URL (cached)
        # 2. Extracts kid from JWT header
        # 3. Finds matching key in JWKS
        # 4. Returns correct signing key
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer="mpo-webauthn"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

**Benefits**:
- ✅ Simpler code (no manual base64 decode)
- ✅ Automatic JWKS caching
- ✅ Automatic key rotation support (picks correct key by kid)
- ✅ Industry-standard pattern

### 4.3 Update example-service/requirements.txt

**File**: `/mcp-server-webauthn-client/src/templates/vanilla/example-service/requirements.txt`

**Add**:
```
PyJWT[crypto]>=2.8.0
```

**Note**: `[crypto]` extra includes cryptography library needed for JWKS support

### 4.4 Update Template README.md.hbs

**File**: `/mcp-server-webauthn-client/src/templates/vanilla/README.md.hbs`

**Changes**:
1. Replace all `/public-key` references with `/.well-known/jwks.json`
2. Update Python examples to use PyJWKClient
3. Update TypeScript examples to use `jose.createRemoteJWKSet()`
4. Add JWKS explanation section

**Example Python section**:
```markdown
### JWT Verification (Python)

```python
from jwt import PyJWKClient
import jwt

# Automatic JWKS fetching and caching
jwks_client = PyJWKClient("http://webauthn-server:8080/.well-known/jwks.json")

def verify_token(token: str):
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer="mpo-webauthn"
    )
    return payload
```

**Example TypeScript section**:
```markdown
### JWT Verification (TypeScript)

```typescript
import * as jose from 'jose';

// Automatic JWKS fetching and caching
const JWKS = jose.createRemoteJWKSet(
  new URL('http://webauthn-server:8080/.well-known/jwks.json')
);

async function verifyToken(token: string) {
  const { payload } = await jose.jwtVerify(token, JWKS, {
    issuer: 'mpo-webauthn'
  });
  return payload;
}
```

---

## Phase 5: Update OpenAPI Specification

### 5.1 Add JWKS Endpoint to OpenAPI

**File**: `/webauthn-server/src/main/resources/openapi/documentation.yaml`

**Add**:
```yaml
paths:
  /.well-known/jwks.json:
    get:
      summary: Get JSON Web Key Set (JWKS)
      description: |
        Returns public key in JWKS format (RFC 7517) for JWT signature verification.

        This endpoint is used by:
        - Envoy Gateway (remote_jwks configuration)
        - OAuth2/OIDC clients
        - Modern JWT libraries (PyJWKClient, jose, go-jose)

        The response includes:
        - RSA public key components (modulus, exponent)
        - Key metadata (kid, alg, use)
        - Support for key rotation (multiple keys)

        Standard OAuth2/OIDC discovery path for public keys.
      tags:
        - Authentication
      operationId: getJwks
      responses:
        '200':
          description: JWKS containing RSA public key
          content:
            application/json:
              schema:
                type: object
                required:
                  - keys
                properties:
                  keys:
                    type: array
                    description: Array of JSON Web Keys
                    items:
                      type: object
                      required:
                        - kty
                        - use
                        - kid
                        - alg
                        - n
                        - e
                      properties:
                        kty:
                          type: string
                          description: Key Type
                          example: "RSA"
                          enum:
                            - RSA
                        use:
                          type: string
                          description: Public Key Use
                          example: "sig"
                          enum:
                            - sig
                        kid:
                          type: string
                          description: Key ID for rotation
                          example: "webauthn-2024-01"
                        alg:
                          type: string
                          description: Algorithm
                          example: "RS256"
                          enum:
                            - RS256
                        n:
                          type: string
                          description: RSA modulus (Base64URL-encoded, no padding)
                          example: "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw"
                        e:
                          type: string
                          description: RSA exponent (Base64URL-encoded, no padding)
                          example: "AQAB"
              example:
                keys:
                  - kty: "RSA"
                    use: "sig"
                    kid: "webauthn-2024-01"
                    alg: "RS256"
                    n: "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx..."
                    e: "AQAB"
```

### 5.2 Remove /public-key from OpenAPI

**Delete the `/public-key` endpoint specification entirely**

---

## Phase 6: Update Documentation

### 6.1 Update Main README.md

**File**: `/Users/vinayakmenon/mpo-api-authn-server/README.md`

Update JWT verification examples to reference `/.well-known/jwks.json` instead of `/public-key`

### 6.2 Update INTEGRATION.md templates

Update all JWKS references in MCP template documentation

---

## Testing Checklist

### Unit Tests
- [ ] `./gradlew :webauthn-server:test` - All unit tests pass
- [ ] `JwksEndpointTest` passes - JWKS format validation
- [ ] `JwksEndpointTest` verifies Base64URL encoding (no padding)
- [ ] `JwksEndpointTest` verifies consistent kid across requests

### Integration Tests (NEW - Critical!)
- [ ] `EnvoyGatewayIntegrationTest` passes - **Simulates Envoy workflow**
- [ ] `EnvoyGatewayIntegrationTest` verifies JWKS parsing works
- [ ] `EnvoyGatewayIntegrationTest` verifies JWT verification with JWKS
- [ ] `EnvoyGatewayIntegrationTest` verifies JWKS caching behavior

### E2E Tests (MCP Templates)
- [ ] Regenerate MCP client: `npx @vmenon25/mcp-server-webauthn-client --path /tmp/test-jwks`
- [ ] `cd /tmp/test-jwks/docker && docker compose up -d` - All services start
- [ ] `docker compose logs envoy-gateway` - No JWKS fetch errors
- [ ] `cd .. && npm install && npm run build` - Client builds successfully
- [ ] `npm test` - All Playwright tests pass (30/30)
- [ ] Python example service works with PyJWKClient
- [ ] Test protected API endpoint: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/user/profile`

### Manual Verification
- [ ] `curl http://localhost:8080/.well-known/jwks.json` - Returns valid JSON
- [ ] JWKS contains `keys` array with one RSA key
- [ ] Key has `kty`, `use`, `kid`, `alg`, `n`, `e` fields
- [ ] Modulus (`n`) is Base64URL without padding (no `=`)
- [ ] Envoy Gateway logs show successful JWKS fetch
- [ ] JWT verification works through Envoy Gateway

---

## Why EnvoyGatewayIntegrationTest is Critical

**This test simulates exactly what Envoy Gateway does:**

1. **Fetch JWKS**: `GET /.well-known/jwks.json`
2. **Parse JWKS**: Extract RSA modulus and exponent from Base64URL
3. **Reconstruct Public Key**: Build RSAPublicKey from JWKS components
4. **Verify JWT**: Use reconstructed key to verify JWT signature

**This test would have caught the Base64 DER bug!**

The bug:
- Envoy expects JWKS format (JSON with `n` and `e` fields)
- We returned Base64 DER (single string, not JSON)
- Envoy's JWKS parser fails silently
- No test verified Envoy compatibility

The fix:
- `EnvoyGatewayIntegrationTest` does exactly what Envoy does
- Test fails if JWKS format is wrong
- Test fails if Base64 encoding is wrong
- Test fails if JWT verification doesn't work

---

## Migration Impact

### Breaking Changes
- ❌ `/public-key` endpoint removed
- ✅ No production impact (all consumers are internal templates)

### Zero-Impact Migration
All affected code is in internal templates that we control:
1. Envoy Gateway config (template)
2. Python example service (template)
3. MCP-generated README (template)

When users generate new clients, they get the fixed version automatically.

### Backward Compatibility
Not needed - no external consumers exist.

---

## Summary

### Files Added
- `/webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/routes/JwksRoutes.kt`
- `/webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/routes/JwksEndpointTest.kt`
- `/webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/integration/EnvoyGatewayIntegrationTest.kt` ⭐ **Critical!**

### Files Deleted
- `/webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/routes/PublicKeyRoutes.kt`

### Files Modified
- `/webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/Application.kt`
- `/webauthn-server/src/test/kotlin/com/vmenon/mpo/api/authn/ApplicationTest.kt`
- `/webauthn-server/src/main/resources/openapi/documentation.yaml`
- `/mcp-server-webauthn-client/src/templates/vanilla/docker/envoy-gateway.yaml.hbs`
- `/mcp-server-webauthn-client/src/templates/vanilla/example-service/main.py.hbs`
- `/mcp-server-webauthn-client/src/templates/vanilla/example-service/requirements.txt`
- `/mcp-server-webauthn-client/src/templates/vanilla/README.md.hbs`

### Success Criteria
- ✅ All tests pass (unit + integration)
- ✅ Envoy Gateway successfully fetches JWKS
- ✅ JWT verification works through Envoy
- ✅ PyJWKClient example works
- ✅ Fresh client generation includes all fixes
- ✅ E2E tests pass (30/30)

---

## References

- **RFC 7517**: JSON Web Key (JWK) - https://datatracker.ietf.org/doc/html/rfc7517
- **Envoy JWT Authentication**: https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/jwt_authn/v3/config.proto
- **PyJWT Documentation**: https://pyjwt.readthedocs.io/en/stable/
- **Auth0 JWKS Guide**: https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-key-sets
