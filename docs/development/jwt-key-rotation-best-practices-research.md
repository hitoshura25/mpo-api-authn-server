# JWT Key Rotation Best Practices - Research Summary

**Date**: 2025-10-24
**Purpose**: Research-driven recommendations for implementing JWT key rotation in mcp-server-webauthn-client
**Focus Areas**: Security, Client Usability, Cross-Platform Portability (Android, Web, iOS)

---

## Executive Summary

Based on comprehensive research from industry leaders (Zalando, Okta, Auth0, HashiCorp), this document provides evidence-based recommendations for implementing JWT key rotation in the WebAuthn server stack. The recommendations prioritize:

1. **Security**: Industry-standard rotation frequencies and secure key management
2. **Client Usability**: Zero-impact rotation with automatic key resolution
3. **Portability**: RFC 7517 compliant JWKS that works across all platforms

**Key Recommendation**: Implement **automatic time-based rotation with database persistence** and **multi-key JWKS support** for graceful rollover.

---

## 1. Security Best Practices

### 1.1 Rotation Frequency Recommendations

**Industry Standard: 6-12 months for RSA keys in production**

| Source | Recommendation | Rationale |
|--------|---------------|-----------|
| **[Enterprise SSO (Stack Overflow)](https://stackoverflow.com/questions/51301843/rsa-jwt-key-rotation-period)** | 6-month rotation, 1-year validity | "At least 2 keys available at all times - one active key and one future key" |
| **[Okta Developer](https://developer.okta.com/docs/concepts/key-rotation/)** | 4 times yearly (every 3 months) | Standard practice for major identity providers |
| **[Google Cloud KMS](https://cloud.google.com/kms/docs/key-rotation)** | 90 days for high-security contexts | "Increases security with minimal administrative complexity" |
| **[NIST/Keylength.com](https://www.keylength.com/en/4/)** | Annually or less | Asymmetric keys should rotate yearly or after signing ~10,000 messages |

**Recommended Approach for WebAuthn Server:**
- **Primary Recommendation**: **6-month rotation with 1-year validity**
  - Provides ample time for clients to refresh caches
  - Balances security with operational stability
  - Industry-proven approach used by enterprise SSO systems
- **Alternative**: 90-day rotation for high-security environments

### 1.2 Security Rationale

**Why Key Rotation Matters** ([Zalando Engineering Blog](https://engineering.zalando.com/posts/2025/01/automated-json-web-key-rotation.html)):
> "Key rotation addresses the threat of undetected key compromise and reduces the window of vulnerability. If private key material leaks, anyone could forge fake tokens and impersonate users."

**Benefits:**
- Limits damage window if keys are compromised
- Addresses NIST 800-63B compliance requirements
- Enables recovery from security incidents
- Follows cryptographic best practices

### 1.3 Emergency Rotation Support

**Must-Have Feature**: Manual rotation trigger for security incidents
- Compromised key scenarios
- Security audit findings
- Regulatory compliance requirements
- Algorithm upgrades (e.g., RSA-2048 → RSA-4096)

---

## 2. Key Storage Options Analysis

### 2.1 Option Comparison

| Storage Type | Security | Multi-Instance Support | Complexity | Production Suitability | Cost |
|-------------|----------|------------------------|------------|----------------------|------|
| **PostgreSQL** | ⭐⭐⭐⭐ | ✅ Yes | Medium | High | Low (already in stack) |
| **Filesystem/Volume** | ⭐⭐⭐ | ⚠️ Requires shared storage | Low | Medium | Low |
| **HashiCorp Vault/KMS** | ⭐⭐⭐⭐⭐ | ✅ Yes | High | Very High | High (additional service) |
| **In-Memory (current)** | ⭐⭐ | ❌ No | Very Low | Low (dev only) | None |

### 2.2 Recommended Approach: PostgreSQL with RAM Caching

**Why PostgreSQL?**
1. **Already in the stack** - No additional infrastructure required
2. **Native multi-instance support** - Multiple server instances can share keys
3. **ACID compliance** - Reliable key lifecycle management
4. **Encryption at-rest** - PostgreSQL supports transparent data encryption
5. **Backup-friendly** - Standard database backup procedures apply

**Security Implementation:**
```
Private Key Storage:
1. Store private keys encrypted in PostgreSQL
2. Load keys into RAM at startup (follow KMS pattern)
3. Never write decrypted keys to disk
4. Use database encryption at-rest
5. Restrict database access via network policies
```

**Industry Consensus** ([Information Security Stack Exchange](https://security.stackexchange.com/questions/245796/json-web-token-secret-storage)):
> "The ideal setup is an HSM, but lacking that, a common approach is storing keys in a KMS that the server can talk to, with the server retrieving the secret(s) at startup/periodically and storing them in RAM."

**PostgreSQL as "Poor Man's KMS":**
- Acts as central key storage (like KMS)
- Keys loaded to RAM at startup (KMS pattern)
- Supports key versioning and metadata
- Much simpler than adding Vault to the stack
- Sufficient for most production use cases

### 2.3 Why NOT Other Options?

**Filesystem/Volume** ([Security Stack Exchange](https://security.stackexchange.com/questions/245796/json-web-token-secret-storage)):
- ❌ Not considered secure (vulnerable to SSRF/RCE exploits)
- ❌ Difficult to manage in multi-instance deployments
- ❌ No built-in key versioning or metadata support
- ✅ Only viable if using Docker secrets for initial bootstrap

**HashiCorp Vault/Cloud KMS** ([HashiCorp Vault](https://www.hashicorp.com/en/resources/better-together-jwt-and-vault-in-modern-apps), [Azure Key Vault](https://learn.microsoft.com/en-us/answers/questions/1397202/signing-jwt)):
- ✅ Most secure option available
- ❌ Significantly increases infrastructure complexity
- ❌ Additional cost and operational overhead
- ❌ Overkill for typical WebAuthn use cases
- 💡 Reserve for enterprise deployments with strict compliance needs

**In-Memory (Current Implementation):**
- ❌ Keys lost on restart (tokens become invalid)
- ❌ No rotation support (single key at a time)
- ❌ Not suitable for production
- ✅ Fine for development/testing only

---

## 3. Client Impact Mitigation Strategies

### 3.1 Graceful Rotation Process (Zero-Impact Deployment)

**Critical Principle** ([Zalando Engineering Blog](https://engineering.zalando.com/posts/2025/01/automated-json-web-key-rotation.html)):
> "Properly executed rotation is transparent to clients and does not result in any kind of access revocation or token invalidation."

**The 4-Phase Rotation Lifecycle:**

```
Phase 1: GENERATION (T=0)
├─ Generate new key pair (e.g., webauthn-2025-02)
├─ Store in database with status: PENDING
└─ DO NOT use for signing yet

Phase 2: PUBLICATION (T=0 to T=grace_period)
├─ Add new public key to JWKS endpoint
├─ JWKS now returns: [webauthn-2025-01 (active), webauthn-2025-02 (pending)]
├─ Continue signing with OLD key (webauthn-2025-01)
└─ Wait for clients to refresh caches (grace period)

Phase 3: ACTIVATION (T=grace_period)
├─ Promote new key to ACTIVE status
├─ Demote old key to RETIRED status
├─ Start signing new tokens with NEW key (webauthn-2025-02)
├─ JWKS still returns both keys for verification
└─ Old key verifies existing tokens but doesn't sign new ones

Phase 4: REMOVAL (T=grace_period + max_token_lifetime + safety_buffer)
├─ Remove old key from JWKS endpoint
├─ Delete old key from database
└─ JWKS now returns: [webauthn-2025-02 (active)]
```

**Timeline Calculation:**
```
Safe Removal Time = Time of Retirement + Max Token Lifetime + Safety Buffer

Example:
- Token lifetime: 15 minutes (900 seconds)
- Grace period: 5 minutes (300 seconds for cache refresh)
- Safety buffer: 5 minutes (300 seconds)
- Total retention: 25 minutes minimum

For production: Recommend 1-hour retention after retirement
```

### 3.2 Client-Side Requirements

**Mandatory Client Behavior** ([Okta Developer](https://developer.okta.com/docs/concepts/key-rotation/)):
> "Keys used to sign tokens automatically rotate and should always be resolved dynamically against the published JWKS. Your app might fail if you hardcode public keys in your apps."

**Client Implementation Checklist:**
- ✅ **Dynamic JWKS Fetching**: Fetch keys from `/.well-known/jwks.json` endpoint
- ✅ **Cache Management**: Cache JWKS response respecting HTTP Cache-Control headers
- ✅ **Multi-Key Support**: Handle JWKS with multiple keys (use `kid` from JWT header)
- ✅ **Refresh on Failure**: If signature verification fails, invalidate cache and retry once
- ✅ **HTTP Caching**: Follow `max-age`, `stale-if-error` directives

**Anti-Patterns to Avoid:**
- ❌ Hardcoding public keys in client code
- ❌ Assuming single key in JWKS
- ❌ Not checking `kid` field in JWT header
- ❌ Ignoring HTTP cache headers

### 3.3 JWKS Cache Duration Recommendations

**Production Cache Settings** ([Auth0 Community](https://community.auth0.com/t/caching-jwks-signing-key/17654), [KrakenD Documentation](https://www.krakend.io/docs/authorization/jwk-caching/)):

| Component | Recommended Cache Duration | Rationale |
|-----------|---------------------------|-----------|
| **Envoy Gateway** | 5-15 minutes (300-900s) | Balance between performance and freshness |
| **Mobile Apps** | 15 minutes - 1 hour | Longer caches acceptable due to refresh-on-error |
| **PyJWKClient (Python)** | 5 minutes (300s default) | Default in PyJWT library, works well |
| **Web Browsers** | Follow HTTP headers | Use Cache-Control directives |

**Stale-If-Error Grace Period** ([Auth0 Community](https://community.auth0.com/t/jks-validity-period/59407)):
- Auth0 uses: `stale-if-error=86400` (24 hours)
- Allows serving cached keys if JWKS endpoint is temporarily down
- Prevents authentication outages during network issues

**Recommended Cache-Control Header:**
```http
Cache-Control: max-age=300, stale-if-error=3600, public
```
- `max-age=300`: Cache for 5 minutes
- `stale-if-error=3600`: Use stale cache for 1 hour if endpoint fails
- `public`: Allow shared caching (CDN, proxies)

### 3.4 Grace Period Calculation

**Minimum Grace Period Formula:**
```
Grace Period ≥ (Maximum Client Cache Duration × 2)

Example:
- Max client cache: 15 minutes
- Minimum grace period: 30 minutes
- Recommended grace period: 1 hour (safer)
```

**Why 2× multiplier?**
- Accounts for clock skew between servers
- Covers clients that fetch just before cache expiry
- Provides buffer for network delays
- Prevents race conditions

---

## 4. Cross-Platform Client Compatibility

### 4.1 Platform-Specific Considerations

#### 4.1.1 Web Clients (JavaScript/TypeScript)

**Current Implementation: Already Compatible** ✅

The existing web client uses `@vmenon25/mpo-webauthn-client` which stores JWTs in sessionStorage. The client doesn't directly validate JWT signatures (Envoy Gateway handles this), making it rotation-agnostic.

**Key Rotation Impact: ZERO**
- Client sends JWT in `Authorization: Bearer <token>` header
- Envoy Gateway fetches JWKS and validates signature
- Client code requires no changes

**Best Practices:**
- Continue using sessionStorage for JWT storage (good practice)
- Token refresh logic remains unchanged
- No client-side key management needed

#### 4.1.2 Android Clients

**Current Implementation Status:**
- Android test client exists (`android-test-client/`)
- Uses generated Android client library (`android-client-library/`)
- Similar pattern to web client: sends JWT, server validates

**Key Rotation Impact: ZERO** (if server-side validation)

**If Client-Side Validation Required:**
```kotlin
// Example using nimbus-jose-jwt or similar
dependencies {
    implementation("com.nimbusds:nimbus-jose-jwt:9.37")
}

// JWKS-aware JWT validation
val jwksUrl = URL("https://envoy-gateway:8000/.well-known/jwks.json")
val jwkSource = RemoteJWKSet(jwksUrl)
val jwtProcessor = DefaultJWTProcessor<SecurityContext>()
jwtProcessor.jwsKeySelector = JWSVerificationKeySelector(JWSAlgorithm.RS256, jwkSource)

// Validation automatically fetches and caches JWKS
val claimsSet = jwtProcessor.process(jwtToken, null)
```

**Storage Best Practices** ([Compile7 - JWT Best Practices for Mobile Apps](https://compile7.org/decompile/jwt-best-practices-for-mobile-apps), [Auth0 Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices)):
- Use Android Keystore for JWT storage (encrypted, secure)
- Avoid SharedPreferences for sensitive tokens
- Implement certificate pinning for JWKS endpoint
- Use Network Security Configuration to enforce HTTPS

#### 4.1.3 iOS Clients (Future Implementation)

**Planned Implementation** (from `docs/improvements/planned/ios-test-client-implementation.md`):
- Swift client library generation planned
- SwiftUI test application
- AuthenticationServices WebAuthn integration

**Key Rotation Compatibility:**
```swift
// Example JWT validation with JWKS (iOS)
import JWTDecode
import JWKSet

let jwksURL = URL(string: "https://envoy-gateway:8000/.well-known/jwks.json")!
let jwkSet = try await JWKSet.fetch(from: jwksURL)
let jwt = try decode(jwt: token)
let isValid = try jwt.verify(using: jwkSet)
```

**Storage Best Practices** ([Auth0 Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices), [Descope JWT Storage Guide](https://www.descope.com/blog/post/developer-guide-jwt-storage)):
- Use iOS Keychain for JWT storage (encrypted, secure)
- Enable App Transport Security (ATS)
- Implement certificate pinning
- Use URLCache for JWKS caching

#### 4.1.4 Python Backends (Example Service)

**Current Implementation: PyJWKClient** ✅ **Already Rotation-Compatible** ([PyJWT Documentation](https://github.com/jpadilla/pyjwt), [PyJWKClient Source](https://github.com/jpadilla/pyjwt/blob/master/jwt/jwks_client.py))

The existing example service already uses PyJWKClient, which:
- Automatically fetches JWKS from server
- Caches keys with 5-minute TTL (configurable)
- Extracts `kid` from JWT header
- Matches against multiple keys in JWKS
- Refreshes on verification failure

**Current Code** (from `example-service/main.py.hbs`):
```python
from jwt import PyJWKClient

JWKS_URL = "http://webauthn-server:8080/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL)

# This already supports key rotation!
signing_key = jwks_client.get_signing_key_from_jwt(token)
payload = jwt.decode(token, signing_key.key, algorithms=["RS256"])
```

**Key Rotation Impact: ZERO** - Already fully compatible! ✅

**Enhancement Recommendations:**
```python
# Optional: Configure longer cache for performance
jwks_client = PyJWKClient(
    JWKS_URL,
    cache_keys=True,
    max_cached_keys=16,  # Support multiple rotated keys
    cache_timeout=900,   # 15 minutes (adjust based on rotation frequency)
)
```

### 4.2 RFC 7517 Compliance (Universal Compatibility)

**The JWKS Standard Ensures Cross-Platform Compatibility** ([RFC 7517](https://www.rfc-editor.org/rfc/rfc7517), [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519))

All modern JWT libraries support RFC 7517 (JSON Web Key Set):
- ✅ **JavaScript/TypeScript**: jose, jsonwebtoken, jwks-rsa
- ✅ **Python**: PyJWT (with PyJWKClient)
- ✅ **Java/Kotlin**: [nimbus-jose-jwt](https://connect2id.com/products/nimbus-jose-jwt), [java-jwt (Auth0)](https://github.com/auth0/java-jwt)
- ✅ **Swift/iOS**: JWTDecode, Swift-JWT
- ✅ **Go**: go-jose, jwt-go
- ✅ **Rust**: jsonwebtoken, jwt

**Standard JWKS Format** (existing implementation already compliant):
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "webauthn-2025-01",
      "alg": "RS256",
      "n": "base64url-encoded-modulus",
      "e": "base64url-encoded-exponent"
    },
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "webauthn-2025-02",
      "alg": "RS256",
      "n": "base64url-encoded-modulus",
      "e": "base64url-encoded-exponent"
    }
  ]
}
```

**Key Point**: Since the server already returns RFC 7517 compliant JWKS, adding key rotation requires **ZERO client changes** as long as clients follow the spec.

---

## 5. Recommended Implementation Approach

Based on the research, here's the recommended implementation strategy:

### 5.1 Core Design Decisions

| Decision Area | Recommendation | Justification |
|---------------|---------------|---------------|
| **Rotation Type** | Time-based automatic + manual trigger | Industry standard, addresses security incidents |
| **Storage** | PostgreSQL with RAM caching | Already in stack, supports multi-instance, secure enough |
| **Rotation Frequency** | 6 months (configurable) | Enterprise SSO standard, balances security/operations |
| **Key Overlap** | 2 keys minimum (old + new) | Standard practice, covers cache TTL |
| **Grace Period** | 1 hour (configurable) | 2× max cache duration (30min), includes safety buffer |
| **Token Lifetime** | 15 minutes (keep current) | Already optimal for WebAuthn use cases |
| **JWKS Cache** | 5 minutes (keep current) | Matches PyJWKClient default, proven effective |

### 5.2 Database Schema Design

```sql
CREATE TABLE jwt_signing_keys (
    key_id VARCHAR(64) PRIMARY KEY,           -- e.g., "webauthn-2025-01"
    private_key_pem TEXT NOT NULL,            -- Encrypted RSA private key (PEM format)
    public_key_pem TEXT NOT NULL,             -- RSA public key (PEM format)
    algorithm VARCHAR(16) NOT NULL DEFAULT 'RS256',
    key_size INTEGER NOT NULL DEFAULT 2048,   -- Bits (2048, 3072, 4096)
    status VARCHAR(16) NOT NULL,              -- PENDING, ACTIVE, RETIRED, DELETED
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMP,                   -- When key became ACTIVE
    retired_at TIMESTAMP,                     -- When key became RETIRED
    expires_at TIMESTAMP,                     -- Safe removal time
    metadata JSONB,                           -- Additional metadata (reason, rotation_policy, etc.)

    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'ACTIVE', 'RETIRED', 'DELETED')),
    CONSTRAINT single_active_key UNIQUE (status) WHERE (status = 'ACTIVE')
);

CREATE INDEX idx_jwt_keys_status ON jwt_signing_keys(status);
CREATE INDEX idx_jwt_keys_expires ON jwt_signing_keys(expires_at) WHERE status = 'RETIRED';
```

**Key Features:**
- **Encrypted storage**: Private keys encrypted at-rest (application-level encryption)
- **Single active key constraint**: PostgreSQL enforces exactly one ACTIVE key
- **Lifecycle tracking**: Created, activated, retired, expires timestamps
- **Metadata support**: Audit trail, rotation reasons, policy version

### 5.3 Key Lifecycle State Machine

```
        generate()
           │
           ▼
      [PENDING]
           │ publish_to_jwks()
           │ + wait(grace_period)
           ▼
       [ACTIVE] ◄── Only this key signs new tokens
           │ rotate()
           ▼
      [RETIRED] ◄── Still in JWKS for verification
           │ after(max_token_lifetime + safety_buffer)
           ▼
      [DELETED] ◄── Removed from JWKS and database
```

### 5.4 Configuration via Environment Variables

```bash
# Key Rotation Configuration
JWT_KEY_ROTATION_ENABLED=true                    # Enable automatic rotation
JWT_KEY_ROTATION_INTERVAL_DAYS=180              # 6 months
JWT_KEY_GRACE_PERIOD_MINUTES=60                 # 1 hour
JWT_KEY_RETENTION_AFTER_RETIREMENT_MINUTES=60   # 1 hour (token lifetime + buffer)
JWT_KEY_SIZE=2048                               # RSA key size (2048, 3072, 4096)
JWT_KEY_ALGORITHM=RS256                         # Signing algorithm

# Key ID Versioning Scheme
JWT_KEY_ID_PREFIX=webauthn                      # Prefix for key IDs
JWT_KEY_ID_FORMAT=timestamp                     # Options: timestamp, version, uuid
# Example formats:
# - timestamp: webauthn-2025-01-24
# - version: webauthn-v1, webauthn-v2
# - uuid: webauthn-550e8400-e29b-41d4-a716-446655440000

# Database Encryption (for private keys at-rest)
JWT_KEY_ENCRYPTION_ENABLED=true
JWT_KEY_ENCRYPTION_KEY_ENV=JWT_MASTER_KEY       # Environment variable containing master key

# Manual Rotation API
JWT_MANUAL_ROTATION_ENABLED=true                # Allow manual rotation via API endpoint
```

### 5.5 New API Endpoints

**Health & Status Endpoint:**
```
GET /.well-known/jwks-status
Response:
{
  "current_key_id": "webauthn-2025-01",
  "current_key_age_days": 45,
  "next_rotation_date": "2025-07-24T00:00:00Z",
  "rotation_interval_days": 180,
  "active_keys_count": 1,
  "pending_keys_count": 0,
  "retired_keys_count": 1,
  "last_rotation_date": "2025-01-24T00:00:00Z"
}
```

**Manual Rotation Trigger (Admin Only):**
```
POST /admin/jwt/rotate-key
Authorization: Bearer <admin-jwt>
Request Body:
{
  "reason": "Security incident - suspected key compromise",
  "grace_period_minutes": 60  // Optional override
}
Response:
{
  "new_key_id": "webauthn-2025-01-24",
  "old_key_id": "webauthn-2025-01",
  "grace_period_end": "2025-01-24T13:00:00Z",
  "activation_time": "2025-01-24T13:00:00Z"
}
```

### 5.6 Logging & Monitoring

**Structured Logging for Key Events:**
```json
{
  "event": "jwt_key_generated",
  "key_id": "webauthn-2025-02",
  "timestamp": "2025-01-24T12:00:00Z",
  "algorithm": "RS256",
  "key_size": 2048
}

{
  "event": "jwt_key_activated",
  "key_id": "webauthn-2025-02",
  "previous_key_id": "webauthn-2025-01",
  "timestamp": "2025-01-24T13:00:00Z"
}

{
  "event": "jwt_key_retired",
  "key_id": "webauthn-2025-01",
  "expires_at": "2025-01-24T14:00:00Z",
  "timestamp": "2025-01-24T13:00:00Z"
}
```

**Metrics to Track:**
- Key age (days since activation)
- Keys in each status (PENDING, ACTIVE, RETIRED)
- Rotation success/failure rate
- JWKS endpoint cache hit/miss ratio
- Signature verification failures (may indicate premature key removal)

---

## 6. Migration Strategy

### 6.1 Backward Compatibility Approach

**Goal**: Upgrade existing deployments without invalidating existing tokens or requiring client changes.

**Phase 1: Database Schema Addition**
- Add `jwt_signing_keys` table to database
- Run migration script during server startup
- No impact on existing functionality

**Phase 2: Legacy Key Migration**
- Generate new key pair on first startup
- Store in database with key_id: `webauthn-2024-01` (maintain existing ID)
- Mark as ACTIVE
- Server uses database key instead of in-memory generation

**Phase 3: JWKS Multi-Key Support**
- Update JWKS endpoint to return all ACTIVE + RETIRED keys
- Existing clients continue working (they fetch JWKS dynamically)
- No client changes required

**Phase 4: Rotation Enablement**
- Enable automatic rotation via environment variable
- First rotation creates new key with grace period
- Monitor logs and metrics

**Rollback Plan:**
- If issues arise, disable rotation: `JWT_KEY_ROTATION_ENABLED=false`
- Server continues using current ACTIVE key
- No data loss, no client impact

### 6.2 Testing Strategy

**Unit Tests:**
- Key generation and storage
- State machine transitions (PENDING → ACTIVE → RETIRED → DELETED)
- JWKS endpoint with multiple keys
- kid extraction and key selection

**Integration Tests:**
- Full rotation lifecycle end-to-end
- Token signing with new key after rotation
- Token verification with old key after rotation
- Expired key removal

**E2E Tests:**
- Web client authentication during rotation
- Android client compatibility (future)
- PyJWKClient verification (already tested)
- Envoy Gateway JWT validation with rotated keys

**Load Testing:**
- JWKS endpoint performance under load
- Database query performance for key retrieval
- RAM caching effectiveness

---

## 7. Security Considerations

### 7.1 Private Key Protection

**Encryption at Rest:**
- Store private keys encrypted in PostgreSQL
- Use application-level encryption (NOT database-level only)
- Master encryption key from environment variable (injected via secrets)
- Never log or expose private keys in any format

**Encryption in Transit:**
- Keys loaded from database to RAM over encrypted PostgreSQL connection
- Private keys never transmitted outside server process
- Public keys transmitted via HTTPS only (Envoy Gateway terminates TLS)

**Encryption in Use (RAM):**
- Private keys held in RAM for signing operations
- Clear keys from memory on server shutdown (JVM finalizer)
- No swap to disk (configure server with `--no-swap` or mlock)

### 7.2 Access Control

**Database Access:**
- WebAuthn server: Full access to `jwt_signing_keys` table
- Other services: NO access (use Envoy Gateway for JWT validation)
- Database user: Dedicated `webauthn_jwt_user` with minimal privileges

**API Access:**
- `/.well-known/jwks.json`: Public (read-only)
- `/.well-known/jwks-status`: Public (read-only, metadata only)
- `/admin/jwt/rotate-key`: Admin-only (requires admin JWT)

### 7.3 Audit Trail

**Track All Key Lifecycle Events:**
- Key generation (timestamp, algorithm, size)
- Key activation (timestamp, previous key)
- Key retirement (timestamp, reason)
- Key deletion (timestamp, retention period)
- Manual rotation triggers (admin user, reason)

**Database Audit Log:**
```sql
CREATE TABLE jwt_key_audit_log (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(64) NOT NULL,
    event VARCHAR(32) NOT NULL,  -- GENERATED, ACTIVATED, RETIRED, DELETED, MANUAL_ROTATION
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,  -- Additional context (admin_user, reason, etc.)
    FOREIGN KEY (key_id) REFERENCES jwt_signing_keys(key_id)
);
```

### 7.4 Compliance & Standards

**Adherence to Standards:**
- ✅ RFC 7517 (JSON Web Key Set)
- ✅ RFC 7519 (JSON Web Token)
- ✅ NIST 800-63B (Digital Identity Guidelines)
- ✅ OWASP JWT Security Cheat Sheet

**Cryptographic Standards:**
- RSA-2048 minimum (default)
- RS256 algorithm (RSA with SHA-256)
- Support for RSA-3072, RSA-4096 (configurable)
- Key rotation every 6-12 months (configurable)

---

## 8. Implementation Checklist

### Phase 1: Database & Core Infrastructure
- [ ] Create `jwt_signing_keys` table schema
- [ ] Create `jwt_key_audit_log` table schema
- [ ] Implement key encryption/decryption utilities
- [ ] Implement key generation service
- [ ] Add environment variable configuration
- [ ] Implement database migration script

### Phase 2: Key Management Service
- [ ] Implement key lifecycle state machine
- [ ] Implement key storage repository (PostgreSQL)
- [ ] Implement key loading from database to RAM
- [ ] Implement active key caching
- [ ] Add logging for all key events
- [ ] Add metrics for monitoring

### Phase 3: JWT Service Updates
- [ ] Update JwtService to use database keys
- [ ] Implement dynamic kid generation
- [ ] Update token signing to use ACTIVE key
- [ ] Add support for multiple concurrent keys
- [ ] Update JWKS endpoint to return multiple keys
- [ ] Add Cache-Control headers to JWKS endpoint

### Phase 4: Rotation Logic
- [ ] Implement time-based rotation scheduler
- [ ] Implement grace period handling
- [ ] Implement key activation logic
- [ ] Implement key retirement logic
- [ ] Implement key cleanup/deletion logic
- [ ] Add manual rotation API endpoint

### Phase 5: Monitoring & Admin
- [ ] Implement `/.well-known/jwks-status` endpoint
- [ ] Implement `/admin/jwt/rotate-key` endpoint
- [ ] Add health check for key age
- [ ] Add alerts for rotation failures
- [ ] Add dashboard metrics (Jaeger integration)

### Phase 6: Testing
- [ ] Unit tests for key lifecycle
- [ ] Integration tests for rotation
- [ ] E2E tests for web client
- [ ] E2E tests for Python service (PyJWKClient)
- [ ] Load testing for JWKS endpoint
- [ ] Security testing (pen testing key storage)

### Phase 7: Documentation & Deployment
- [ ] Update CLAUDE.md with key rotation details
- [ ] Update docker-compose.yml with new env vars
- [ ] Update README with configuration guide
- [ ] Create runbook for manual rotation
- [ ] Create troubleshooting guide
- [ ] Deploy to staging environment
- [ ] Monitor for issues
- [ ] Deploy to production

---

## 9. Estimated Impact Analysis

### 9.1 Client Impact: ZERO ✅

**No client changes required because:**
1. All existing clients fetch JWKS dynamically (as required by spec)
2. RFC 7517 compliant multi-key JWKS is standard
3. PyJWKClient already supports key rotation (built-in)
4. Envoy Gateway already caches and refreshes JWKS
5. Graceful rotation prevents any token invalidation

**Testing Required:**
- Validate existing E2E tests still pass
- Add rotation tests to verify zero impact

### 9.2 Server Changes: Moderate

**Components Modified:**
1. **JwtService.kt** - Use database keys instead of in-memory
2. **JwksRoutes.kt** - Return multiple keys from database
3. **AppModule.kt** - Add new DI bindings (KeyRepository, KeyRotationService)
4. **Database Schema** - New tables for key storage

**New Components:**
- KeyRepository (database access)
- KeyRotationService (rotation logic)
- KeyEncryptionUtil (encrypt/decrypt)
- KeyRotationScheduler (background job)
- Admin API routes (manual rotation)

**Estimated Effort:**
- Development: 3-5 days
- Testing: 2-3 days
- Documentation: 1 day
- Total: 6-9 days

### 9.3 Infrastructure Impact: Minimal

**PostgreSQL:**
- 2 new tables (minimal storage: ~1KB per key)
- Infrequent writes (only during rotation)
- No performance impact (keys cached in RAM)

**No New Services Required:**
- Uses existing PostgreSQL container
- No Vault/KMS needed
- No additional containers

**Docker Compose Changes:**
- Add environment variables for rotation config
- Add master encryption key to secrets
- No new service definitions

---

## 10. Future Enhancements (Optional)

### 10.1 Advanced Features (Post-MVP)

**Algorithm Agility:**
- Support multiple algorithms (RS256, RS384, RS512, ES256, ES384, ES512)
- Gradual migration from RSA to ECDSA (smaller keys, better performance)

**Multi-Tenant Support:**
- Per-tenant key rotation policies
- Isolated key storage per tenant
- Tenant-specific JWKS endpoints

**Hardware Security Module (HSM) Integration:**
- For high-security deployments
- Store private keys in HSM
- Signing operations performed in HSM

**Key Import/Export:**
- Import existing keys from PEM files
- Export public keys for external validation
- Backup/restore procedures

### 10.2 Compliance Enhancements

**FIPS 140-2 Compliance:**
- Use FIPS-approved cryptographic libraries
- FIPS mode for PostgreSQL encryption
- Hardware-backed key storage

**SOC 2 / ISO 27001:**
- Enhanced audit logging
- Immutable audit trail (append-only)
- Automated compliance reporting

---

## 11. References

### Industry Documentation
- [Zalando Engineering - JSON Web Key Rotation (2025)](https://engineering.zalando.com/posts/2025/01/automated-json-web-key-rotation.html)
- [Okta Developer - Key Rotation Concepts](https://developer.okta.com/docs/concepts/key-rotation/)
- [Auth0 - Rotate Signing Keys](https://auth0.com/docs/get-started/tenant-settings/signing-keys/rotate-signing-keys)
- [HashiCorp Vault - JWT and Vault in Modern Apps](https://www.hashicorp.com/en/resources/better-together-jwt-and-vault-in-modern-apps)

### Standards & Specifications
- [RFC 7517 - JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517)
- [RFC 7519 - JSON Web Token (JWT)](https://www.rfc-editor.org/rfc/rfc7519)
- [NIST SP 800-57 Part 3 - Key Management Guidance](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-57pt3r1.pdf)
- [NIST SP 800-63B - Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)

### Libraries & Tools
- [PyJWT - Python JWT Library](https://github.com/jpadilla/pyjwt)
- [PyJWKClient - JWKS Client](https://github.com/jpadilla/pyjwt/blob/master/jwt/jwks_client.py)
- [nimbus-jose-jwt - Java JWT Library](https://connect2id.com/products/nimbus-jose-jwt)
- [Auth0 java-jwt - Java JWT Library](https://github.com/auth0/java-jwt)

---

## Appendix: Key Terminology

**JWKS (JSON Web Key Set):** RFC 7517 standard format for publishing public keys used for JWT signature verification.

**kid (Key ID):** Unique identifier for a key in JWKS. JWT header includes kid to indicate which key signed the token.

**Grace Period:** Time window where both old and new public keys are available in JWKS, allowing clients to refresh caches.

**Key Rotation:** Process of generating new signing keys and gracefully transitioning from old to new keys without service disruption.

**Signing Key:** Private key used to create JWT signatures. Must be kept secret.

**Verification Key:** Public key used to verify JWT signatures. Published in JWKS for clients to download.

**RS256:** RSA signature with SHA-256 hash. Most common algorithm for JWT signing. Uses asymmetric key pairs (public/private).

**ACTIVE Key:** Current key used for signing new tokens.

**RETIRED Key:** Previous key no longer used for signing, but still available in JWKS for verifying existing tokens.

**PENDING Key:** Newly generated key published in JWKS but not yet used for signing (during grace period).

**DELETED Key:** Old key removed from JWKS and database after all tokens signed with it have expired.
