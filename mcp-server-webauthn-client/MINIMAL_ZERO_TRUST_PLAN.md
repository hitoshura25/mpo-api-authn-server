# Minimal Zero Trust Implementation Plan - MCP WebAuthn Tool

**Goal**: Implement zero-trust architecture with minimal scope, fixed technology stack, and no configuration explosion.

**Philosophy**:
- **Don't reinvent the wheel** - use proven open-source solutions
- **Opinionated defaults** - one tech stack, done right
- **Minimal scope** - get core zero-trust working first, extend later
- **Zero config** - works out of the box, secure by default

---

## Fixed Technology Stack (Non-Negotiable)

### Why These Choices?

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **API Gateway** | **Envoy Gateway** | Lightweight, no database needed, built-in JWT plugin, service mesh ready |
| **Service Mesh** | **Istio** | Industry standard, automatic mTLS, mature ecosystem |
| **JWT Library** | **Auth0 java-jwt** | Already in ecosystem, battle-tested, RS256 support |
| **Example Service** | **Python FastAPI** | Fastest to implement, great JWT libraries, clear code |

**No configuration parameters** - these are the defaults, period.

---

## Minimal MCP Tool Interface (No Architecture Params)

### Current Parameters (Keep These)
```typescript
interface GenerateWebClientArgs {
  project_path: string;
  framework?: 'vanilla' | 'react' | 'vue';  // Web client framework
  server_url?: string;                       // Default: http://localhost:8080
  client_port?: number;                      // Default: 8082
}
```

### NEW: Only Add These Two Parameters
```typescript
interface GenerateWebClientArgs {
  // ... existing params ...

  // NEW: Relying Party configuration (already supported by server)
  relying_party_id?: string;      // Default: 'localhost'
  relying_party_name?: string;    // Default: 'WebAuthn Demo'
}
```

**That's it.** No `architecture`, no `gateway_type`, no `service_mesh_type`.

**Zero-trust is the default.** Every generation creates a complete secure stack.

---

## What Gets Generated (Always)

```
project-name/
├── docker/
│   ├── docker-compose.yml              # Full zero-trust stack
│   ├── envoy-gateway.yaml              # Envoy config with JWT verification
│   ├── istio/
│   │   ├── mtls-strict.yaml            # Enforce mTLS
│   │   ├── jwt-validation.yaml         # JWT validation policy
│   │   └── authz-policy.yaml           # Authorization rules
│   ├── init-db.sql                     # Database schema
│   └── secrets/                        # Auto-generated passwords
├── example-service/                     # Python FastAPI example
│   ├── main.py                         # JWT verification middleware
│   ├── requirements.txt
│   └── Dockerfile
├── src/                                 # Web client (vanilla/react/vue)
│   ├── index.ts
│   ├── webauthn-client.ts
│   └── ...
├── tests/
│   ├── webauthn.spec.js                # E2E: WebAuthn flow
│   ├── jwt-verification.spec.js        # E2E: JWT issuance & validation
│   └── mtls-verification.spec.js       # E2E: Service mesh security
├── docs/
│   └── INTEGRATION.md                  # How to add your services
├── scripts/
│   └── add-service.sh                  # Helper: scaffold new service
└── README.md
```

**Every generation includes everything.** No optional components.

---

## Phase 0: WebAuthn Server Enhancement (Week 1-2)

### Single Goal: Add JWT Signing

**No new endpoints, no JWKS complexity yet.** Just get JWT working.

#### Task 0.1: Add JWT Dependency

```kotlin
// webauthn-server/build.gradle.kts
dependencies {
    implementation("com.auth0:java-jwt:4.4.0")
}
```

#### Task 0.2: Create Minimal JWT Service

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/security/JwtService.kt`

```kotlin
package com.vmenon.mpo.api.authn.security

import com.auth0.jwt.JWT
import com.auth0.jwt.algorithms.Algorithm
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.interfaces.RSAPrivateKey
import java.security.interfaces.RSAPublicKey
import java.time.Instant
import java.util.Date
import org.koin.core.annotation.Single

@Single
class JwtService {
    private val keyPair: KeyPair by lazy {
        KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
    }

    private val algorithm by lazy {
        Algorithm.RSA256(
            keyPair.public as RSAPublicKey,
            keyPair.private as RSAPrivateKey
        )
    }

    fun createToken(username: String): String {
        val now = Instant.now()
        return JWT.create()
            .withIssuer("mpo-webauthn")
            .withSubject(username)
            .withIssuedAt(Date.from(now))
            .withExpiresAt(Date.from(now.plusSeconds(900))) // 15 minutes
            .sign(algorithm)
    }

    fun getPublicKey(): RSAPublicKey = keyPair.public as RSAPublicKey
}
```

#### Task 0.3: Update Authentication Route

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/routes/AuthenticationRoutes.kt`

```kotlin
private suspend fun PipelineContext<Unit, ApplicationCall>.handleSuccessfulAuthentication(
    username: String,
    logger: Logger,
) {
    val jwtService: JwtService by inject()

    logger.info("Successfully authenticated user: $username")

    val accessToken = jwtService.createToken(username)

    call.respond(
        mapOf(
            "success" to true,
            "access_token" to accessToken,
            "token_type" to "Bearer",
            "expires_in" to 900
        )
    )
}
```

#### Task 0.4: Add Public Key Endpoint (Minimal)

**File**: `webauthn-server/src/main/kotlin/com/vmenon/mpo/api/authn/routes/PublicKeyRoutes.kt`

```kotlin
package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.security.JwtService
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import org.koin.ktor.ext.inject
import java.util.Base64

fun Application.configurePublicKeyRoutes() {
    routing {
        val jwtService: JwtService by inject()

        get("/public-key") {
            val publicKey = jwtService.getPublicKey()
            val encoded = Base64.getEncoder().encodeToString(publicKey.encoded)
            call.respondText(encoded)
        }
    }
}
```

**That's it for server changes.** No JWKS, no complex key rotation. Public key is Base64-encoded DER format.

---

## Phase 1: Envoy Gateway Configuration (Week 3)

### Why Envoy Instead of Kong?

- ✅ **No database required** (Kong needs PostgreSQL)
- ✅ **Smaller footprint** (single container)
- ✅ **Native JWT plugin** (no external dependencies)
- ✅ **Service mesh ready** (integrates with Istio)
- ✅ **YAML configuration** (no REST API needed)

### Envoy Gateway Template

**File**: `mcp-server-webauthn-client/src/templates/docker/envoy-gateway.yaml.hbs`

```yaml
static_resources:
  listeners:
    - name: main_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8000
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                codec_type: AUTO
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        # Public routes (no JWT required)
                        - match:
                            prefix: "/register"
                          route:
                            cluster: webauthn_server
                        - match:
                            prefix: "/authenticate"
                          route:
                            cluster: webauthn_server
                        - match:
                            prefix: "/public-key"
                          route:
                            cluster: webauthn_server
                        - match:
                            prefix: "/health"
                          route:
                            cluster: webauthn_server

                        # Protected routes (JWT required)
                        - match:
                            prefix: "/api"
                          route:
                            cluster: example_service

                http_filters:
                  # JWT Authentication filter
                  - name: envoy.filters.http.jwt_authn
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
                      providers:
                        webauthn_provider:
                          issuer: "mpo-webauthn"
                          audiences:
                            - "webauthn-clients"
                          remote_jwks:
                            http_uri:
                              uri: http://webauthn-server:8080/public-key
                              cluster: webauthn_server
                              timeout: 5s
                            cache_duration:
                              seconds: 300  # Cache public key for 5 minutes
                      rules:
                        # Require JWT for /api/* routes
                        - match:
                            prefix: "/api"
                          requires:
                            provider_name: webauthn_provider

                  # CORS filter
                  - name: envoy.filters.http.cors
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.cors.v3.Cors

                  # Router filter (must be last)
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

  clusters:
    - name: webauthn_server
      connect_timeout: 0.25s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: webauthn_server
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: webauthn-server
                      port_value: 8080

    - name: example_service
      connect_timeout: 0.25s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: example_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: example-service
                      port_value: 9000
      # mTLS configuration (connects to Istio sidecar)
      transport_socket:
        name: envoy.transport_sockets.tls
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext
          common_tls_context:
            tls_certificates:
              - certificate_chain:
                  filename: /etc/envoy/certs/cert.pem
                private_key:
                  filename: /etc/envoy/certs/key.pem
            validation_context:
              trusted_ca:
                filename: /etc/envoy/certs/ca.pem
```

---

## Phase 2: Istio Service Mesh (Week 4)

### Minimal Istio Setup

**No Kubernetes.** Use Istio's standalone Envoy sidecars in Docker Compose.

### Why This Works

Istio's core feature is the **Envoy proxy**. We can use Envoy directly without istiod control plane for a minimal setup.

**Strategy**:
1. Each service gets an Envoy sidecar container
2. Sidecars configured for mTLS
3. Certificates generated via `openssl` (stored in secrets/)
4. No control plane complexity

### Istio mTLS Configuration

**File**: `mcp-server-webauthn-client/src/templates/docker/istio/example-service-envoy.yaml.hbs`

```yaml
static_resources:
  listeners:
    - name: service_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 9000
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: service_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: local_service
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/"
                          route:
                            cluster: local_app
                http_filters:
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          # mTLS termination
          transport_socket:
            name: envoy.transport_sockets.tls
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
              require_client_certificate: true  # Enforce mTLS
              common_tls_context:
                tls_certificates:
                  - certificate_chain:
                      filename: /etc/certs/service-cert.pem
                    private_key:
                      filename: /etc/certs/service-key.pem
                validation_context:
                  trusted_ca:
                    filename: /etc/certs/ca-cert.pem

  clusters:
    - name: local_app
      connect_timeout: 0.25s
      type: STATIC
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: local_app
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: 127.0.0.1  # Localhost (shares network namespace)
                      port_value: 9001    # App listens on 9001, Envoy on 9000
```

---

## Phase 3: Docker Compose Orchestration (Week 5)

### Complete Stack Template

**File**: `mcp-server-webauthn-client/src/templates/docker/docker-compose.yml.hbs`

```yaml
version: '3.8'

services:
  # Envoy Gateway (entry point)
  envoy-gateway:
    image: envoyproxy/envoy:v1.29-latest
    ports:
      - "8000:8000"  # Gateway proxy
      - "9901:9901"  # Admin interface
    volumes:
      - ./envoy-gateway.yaml:/etc/envoy/envoy.yaml:ro
      - ./certs:/etc/envoy/certs:ro
    command: ["-c", "/etc/envoy/envoy.yaml", "--service-cluster", "gateway"]
    depends_on:
      - webauthn-server
      - example-service

  # WebAuthn Server (JWT issuer)
  webauthn-server:
    image: vmenon25/mpo-webauthn-server:latest
    environment:
      MPO_AUTHN_DB_HOST: postgres
      MPO_AUTHN_DB_PORT: 5432
      MPO_AUTHN_DB_NAME: webauthn
      MPO_AUTHN_DB_USERNAME: webauthn_user
      MPO_AUTHN_DB_PASSWORD_FILE: /run/secrets/postgres_password
      MPO_AUTHN_REDIS_HOST: redis
      MPO_AUTHN_REDIS_PORT: 6379
      MPO_AUTHN_REDIS_PASSWORD_FILE: /run/secrets/redis_password
      MPO_AUTHN_APP_RELYING_PARTY_ID: {{relying_party_id}}
      MPO_AUTHN_APP_RELYING_PARTY_NAME: {{relying_party_name}}
    secrets:
      - postgres_password
      - redis_password
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Example Service (Python FastAPI with mTLS)
  example-service-sidecar:
    image: envoyproxy/envoy:v1.29-latest
    volumes:
      - ./istio/example-service-envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./certs:/etc/certs:ro
    command: ["-c", "/etc/envoy/envoy.yaml", "--service-cluster", "example-service"]

  example-service:
    build:
      context: ../example-service
      dockerfile: Dockerfile
    network_mode: "service:example-service-sidecar"  # Share network with Envoy
    environment:
      APP_PORT: 9001  # App listens on 9001, Envoy sidecar exposes 9000
      WEBAUTHN_PUBLIC_KEY_URL: "http://webauthn-server:8080/public-key"
    depends_on:
      - example-service-sidecar

  # PostgreSQL (existing)
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: webauthn
      POSTGRES_USER: webauthn_user
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U webauthn_user -d webauthn"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis (existing)
  redis:
    image: redis:7-alpine
    command: sh -c 'redis-server --requirepass "$$(cat /run/secrets/redis_password)"'
    secrets:
      - redis_password
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

secrets:
  postgres_password:
    file: ./secrets/postgres_password
  redis_password:
    file: ./secrets/redis_password

volumes:
  postgres-data:
  redis-data:
```

---

## Phase 4: Example Service (Week 6)

### Minimal Python FastAPI Example

**File**: `mcp-server-webauthn-client/src/templates/example-service/main.py.hbs`

```python
"""
Minimal example service with JWT verification.
Runs behind Envoy sidecar with mTLS.
"""
from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Optional
import httpx
import jwt
import os

app = FastAPI()

# Configuration
PUBLIC_KEY_URL = os.getenv("WEBAUTHN_PUBLIC_KEY_URL")
PUBLIC_KEY_CACHE = None

def get_public_key():
    """Fetch public key from WebAuthn server (cached)"""
    global PUBLIC_KEY_CACHE
    if PUBLIC_KEY_CACHE is None:
        response = httpx.get(PUBLIC_KEY_URL)
        response.raise_for_status()
        # Public key is Base64-encoded DER format
        import base64
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        PUBLIC_KEY_CACHE = load_der_public_key(base64.b64decode(response.text))
    return PUBLIC_KEY_CACHE

def verify_jwt_token(authorization: Optional[str] = Header(None)) -> dict:
    """Verify JWT from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]

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

@app.get("/health")
def health():
    """Health check (no authentication)"""
    return {"status": "healthy"}

@app.get("/api/user/profile")
def get_profile(user: dict = Depends(verify_jwt_token)):
    """Protected endpoint - requires valid JWT"""
    return {
        "username": user["sub"],
        "message": "This is protected data",
        "auth_time": user.get("iat")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9001)  # Envoy sidecar listens on 9000
```

**File**: `mcp-server-webauthn-client/src/templates/example-service/requirements.txt.hbs`

```txt
fastapi==0.109.2
uvicorn[standard]==0.27.1
pyjwt[crypto]==2.8.0
httpx==0.26.0
cryptography==42.0.2
```

**File**: `mcp-server-webauthn-client/src/templates/example-service/Dockerfile.hbs`

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 9001

CMD ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "9001"]
```

---

## Phase 5: Certificate Generation (Week 7)

### Auto-Generate mTLS Certificates

**File**: `mcp-server-webauthn-client/src/lib/generator.ts`

```typescript
function generateMTLSCertificates(project_path: string) {
    const certsDir = join(project_path, 'docker', 'certs');
    mkdirSync(certsDir, { recursive: true });

    // Generate CA certificate
    execSync(`openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout ${certsDir}/ca-key.pem \
        -out ${certsDir}/ca-cert.pem \
        -days 365 \
        -subj "/CN=WebAuthn-CA"`, { stdio: 'inherit' });

    // Generate service certificate
    execSync(`openssl req -newkey rsa:2048 -nodes \
        -keyout ${certsDir}/service-key.pem \
        -out ${certsDir}/service-csr.pem \
        -subj "/CN=example-service"`, { stdio: 'inherit' });

    // Sign with CA
    execSync(`openssl x509 -req \
        -in ${certsDir}/service-csr.pem \
        -CA ${certsDir}/ca-cert.pem \
        -CAkey ${certsDir}/ca-key.pem \
        -CAcreateserial \
        -out ${certsDir}/service-cert.pem \
        -days 365`, { stdio: 'inherit' });

    // Cleanup CSR
    unlinkSync(join(certsDir, 'service-csr.pem'));
}
```

---

## Phase 6: Integration Documentation (Week 8)

### Minimal INTEGRATION.md

**File**: `mcp-server-webauthn-client/src/templates/docs/INTEGRATION.md.hbs`

```markdown
# Adding Your Service to Zero-Trust Stack

## Quick Start

```bash
# 1. Copy example-service as template
cp -r example-service my-service

# 2. Update my-service/main.py with your logic

# 3. Add to docker-compose.yml
# (Copy example-service section, rename to my-service)

# 4. Generate certificate for your service
cd docker/certs
openssl req -newkey rsa:2048 -nodes \
  -keyout my-service-key.pem \
  -out my-service-csr.pem \
  -subj "/CN=my-service"

openssl x509 -req \
  -in my-service-csr.pem \
  -CA ca-cert.pem \
  -CAkey ca-key.pem \
  -CAcreateserial \
  -out my-service-cert.pem \
  -days 365

# 5. Start your service
docker compose up -d my-service
```

## JWT Verification Pattern

All services MUST verify JWT tokens. Use this pattern:

```python
# Python
from fastapi import Depends, HTTPException, Header
import jwt
import httpx

PUBLIC_KEY_URL = "http://webauthn-server:8080/public-key"

def verify_jwt(authorization: str = Header(None)):
    token = authorization.split(" ")[1]
    public_key_response = httpx.get(PUBLIC_KEY_URL)
    public_key = load_der_public_key(base64.b64decode(public_key_response.text))
    return jwt.decode(token, public_key, algorithms=["RS256"])

@app.get("/protected")
def protected(user: dict = Depends(verify_jwt)):
    return {"user": user["sub"]}
```

## mTLS Configuration

Your service MUST run behind Envoy sidecar. Update docker-compose.yml:

```yaml
my-service-sidecar:
  image: envoyproxy/envoy:v1.29-latest
  volumes:
    - ./istio/my-service-envoy.yaml:/etc/envoy/envoy.yaml:ro
    - ./certs:/etc/certs:ro

my-service:
  build: ../my-service
  network_mode: "service:my-service-sidecar"  # Share network
  depends_on:
    - my-service-sidecar
```

## Security Checklist

- ✅ Service verifies JWT signature using `/public-key` endpoint
- ✅ Service validates `exp` claim (token expiration)
- ✅ Service runs behind Envoy sidecar (mTLS)
- ✅ Service certificate signed by CA
- ✅ Service only accepts connections with valid client certificates
```

---

## Phase 7: Helper Script (Week 8)

### Minimal add-service.sh

**File**: `mcp-server-webauthn-client/src/templates/scripts/add-service.sh.hbs`

```bash
#!/bin/bash
set -e

SERVICE_NAME="$1"
if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: ./scripts/add-service.sh <service-name>"
    exit 1
fi

echo "🚀 Adding service: $SERVICE_NAME"

# 1. Copy template
cp -r example-service "../$SERVICE_NAME"

# 2. Generate certificates
cd docker/certs
openssl req -newkey rsa:2048 -nodes \
  -keyout ${SERVICE_NAME}-key.pem \
  -out ${SERVICE_NAME}-csr.pem \
  -subj "/CN=${SERVICE_NAME}"

openssl x509 -req \
  -in ${SERVICE_NAME}-csr.pem \
  -CA ca-cert.pem \
  -CAkey ca-key.pem \
  -CAcreateserial \
  -out ${SERVICE_NAME}-cert.pem \
  -days 365

rm ${SERVICE_NAME}-csr.pem
cd ../..

echo "✅ Service created!"
echo "Next steps:"
echo "1. Edit ../${SERVICE_NAME}/main.py"
echo "2. Add ${SERVICE_NAME} to docker-compose.yml (copy example-service section)"
echo "3. docker compose up -d ${SERVICE_NAME}"
```

---

## Implementation Timeline (Minimal)

| Phase | Weeks | Deliverables |
|-------|-------|--------------|
| Phase 0: WebAuthn JWT | 1-2 | JWT signing, `/public-key` endpoint |
| Phase 1: Envoy Gateway | 3 | JWT verification, routing |
| Phase 2: Istio mTLS | 4 | Envoy sidecars, mTLS config |
| Phase 3: Docker Compose | 5 | Complete orchestration |
| Phase 4: Example Service | 6 | Python FastAPI template |
| Phase 5: Certificate Gen | 7 | Auto-generate mTLS certs |
| Phase 6-7: Docs & Scripts | 8 | INTEGRATION.md, add-service.sh |

**Total: 8 weeks** (vs 20 weeks in full plan)

---

## What We're NOT Building (Scope Cuts)

❌ Multiple architecture options (simple/gateway/zero-trust)
❌ Gateway selection (Kong/Traefik/Envoy) - just Envoy
❌ Service mesh selection (Istio/Linkerd/Consul) - just Istio-style Envoy
❌ Multi-language examples (TypeScript/Java) - just Python
❌ JWKS endpoint - just `/public-key` Base64 DER
❌ Key rotation
❌ Refresh tokens
❌ Kubernetes manifests
❌ Observability (Prometheus/Grafana)
❌ Rate limiting
❌ Complex authorization policies

**These can be added in v2.1+ once core zero-trust works.**

---

## Testing Strategy

### E2E Tests (Playwright)

```typescript
test('should issue JWT on successful authentication', async ({ request }) => {
    // Authenticate
    const response = await request.post('http://localhost:8000/authenticate/complete', {
        data: { /* ... */ }
    });

    const { access_token } = await response.json();

    // Verify JWT structure
    const parts = access_token.split('.');
    expect(parts.length).toBe(3);

    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString());
    expect(payload.iss).toBe('mpo-webauthn');
    expect(payload.exp).toBeGreaterThan(Date.now() / 1000);
});

test('should access protected endpoint with JWT', async ({ request }) => {
    const token = await getAuthToken(request);

    const response = await request.get('http://localhost:8000/api/user/profile', {
        headers: { 'Authorization': `Bearer ${token}` }
    });

    expect(response.ok()).toBeTruthy();
});

test('should reject request without JWT', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/user/profile');
    expect(response.status()).toBe(401);
});
```

---

## Success Criteria

### Must Have (Minimal Viable Product)
- ✅ WebAuthn server issues JWT tokens on successful authentication
- ✅ Envoy Gateway validates JWT for `/api/*` routes
- ✅ Example service verifies JWT signature
- ✅ mTLS between gateway and example service
- ✅ Auto-generated certificates work
- ✅ E2E tests pass
- ✅ `add-service.sh` successfully creates new service

### Nice to Have (Future)
- Automatic certificate rotation
- JWKS endpoint (instead of `/public-key`)
- Multiple language examples
- Kubernetes deployment option

---

## Migration from Current Tool

**Backward compatible:** Existing users don't need to change anything.

**New behavior:** Every generation now includes:
- Envoy Gateway (instead of direct WebAuthn access)
- Example service (shows integration pattern)
- mTLS certificates (auto-generated)

**Breaking changes:** None - all existing parameters work as before.

---

## Questions for Approval

1. ✅ **Envoy only** (no Kong/Traefik options) - acceptable?
2. ✅ **Python only** for example service (no TypeScript/Java yet) - acceptable?
3. ✅ **8 week timeline** - realistic for your team?
4. ✅ **No JWKS** (just `/public-key` DER format) - acceptable for v1?
5. ✅ **Always zero-trust** (no simple mode) - acceptable?

---

## Next Steps

1. **Review this plan** - confirm scope is minimal enough
2. **Approve tech stack** - Envoy + Istio-style sidecars + Python
3. **Start Phase 0** - Add JWT signing to WebAuthn server
4. **Weekly demos** - Show incremental progress

---

**END OF MINIMAL PLAN**
