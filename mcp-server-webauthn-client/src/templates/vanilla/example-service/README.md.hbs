# Example Service - WebAuthn Zero-Trust Architecture

This is a minimal Python FastAPI service demonstrating JWT-based zero-trust architecture integration with the WebAuthn authentication server.

## Architecture

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│ Client  │────▶│ Envoy Gateway│────▶│ Example      │────▶│ WebAuthn    │
│         │     │ (JWT check)  │     │ Service      │     │ Server      │
└─────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                       │                    │                     │
                       │                    └─────────────────────┘
                       │                    Fetches JWKS (RFC 7517)
                       │                    (cached 5 min)
                       └──────────────────────────────────────────┘
                       Validates JWT signature
```

## Features

- **JWT Verification**: Validates RS256-signed JWT tokens using JWKS (RFC 7517)
- **JWKS Support**: Uses PyJWKClient for automatic key fetching and caching
- **Protected Endpoints**: All `/api/*` routes require valid JWT
- **Health Check**: `/health` endpoint without authentication
- **Error Handling**: Proper HTTP 401 responses for invalid/expired tokens

## Endpoints

### Public Endpoints (No Authentication)

- `GET /health` - Health check

### Protected Endpoints (JWT Required)

- `GET /api/user/profile` - Get authenticated user profile
- `GET /api/example/data` - Get example protected data

## JWT Verification Process

1. **Extract Token**: Parse Bearer token from Authorization header
2. **Fetch JWKS**: PyJWKClient fetches JSON Web Key Set from WebAuthn server (RFC 7517, cached)
3. **Select Key**: Automatically select correct signing key using `kid` (Key ID) from JWT header
4. **Verify Signature**: Validate RS256 signature using selected public key
5. **Check Claims**: Verify issuer (`mpo-webauthn`) and expiration
6. **Return User Data**: Extract username from `sub` claim

## Testing

### Test with curl

```bash
# 1. Authenticate and get JWT token
TOKEN=$(curl -s http://localhost:8000/authenticate/complete \
  -H "Content-Type: application/json" \
  -d '{"requestId":"...","credential":"..."}' \
  | jq -r '.access_token')

# 2. Call protected endpoint
curl http://localhost:8000/api/user/profile \
  -H "Authorization: Bearer $TOKEN"

# Expected response:
# {
#   "username": "user@example.com",
#   "message": "This is protected data from the example service",
#   "authenticated_at": 1234567890,
#   "expires_at": 1234568790,
#   "issuer": "mpo-webauthn"
# }
```

### Test without JWT (should fail)

```bash
curl http://localhost:8000/api/user/profile

# Expected response (HTTP 401):
# {
#   "detail": "Missing Authorization header"
# }
```

## Development

### Run Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export WEBAUTHN_JWKS_URL=http://localhost:8080/.well-known/jwks.json
export APP_PORT=9000

# Run server
python main.py
```

### Run with Docker

```bash
# Build image
docker build -t example-service .

# Run container
docker run -p 9000:9000 \
  -e WEBAUTHN_JWKS_URL=http://webauthn-server:8080/.well-known/jwks.json \
  example-service
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WEBAUTHN_JWKS_URL` | URL to fetch WebAuthn server's JWKS endpoint (RFC 7517) for JWT verification | `http://webauthn-server:8080/.well-known/jwks.json` | Yes |
| `APP_PORT` | Port for application to listen on (internal, accessed by Envoy sidecar) | `9001` | No |

### Port Configuration

The service uses two ports:
- **Port 9000**: Envoy sidecar (external, accessed by gateway) - **FIXED**
- **APP_PORT (default 9001)**: Your application (internal, accessed by sidecar) - **CONFIGURABLE**

To customize the application port, set `APP_PORT` in docker-compose.yml:

```yaml
environment:
  APP_PORT: 8080  # Use port 8080 instead of default 9001
```

The `docker-entrypoint.sh` script automatically exports `APP_PORT` with a default of 9001. Your application's Dockerfile CMD references this variable:

```dockerfile
CMD ["sh", "-c", "uvicorn main:app --host 127.0.0.1 --port $APP_PORT"]
```

**Note:** Always listen on `127.0.0.1` (localhost only), never `0.0.0.0`. The Envoy sidecar handles external traffic.

## Security Notes

- **No Private Key**: Service uses JWKS to verify signatures (can verify, not sign)
- **Automatic Key Rotation**: JWKS supports key rotation using `kid` (Key ID)
- **Short-Lived Tokens**: JWT tokens expire after 15 minutes
- **Stateless**: No session storage, fully stateless authentication
- **Zero-Trust**: Every request verified independently
- **Non-Root User**: Runs as non-root user in Docker for security

## Adding More Endpoints

All endpoints under `/api/*` are automatically protected by Envoy Gateway's JWT filter. To add a new protected endpoint:

```python
@app.get("/api/my-endpoint")
def my_endpoint(user: dict = Depends(verify_jwt_token)):
    return {
        "user": user["sub"],
        "data": "your protected data"
    }
```

No additional JWT verification code needed - Envoy handles it at the gateway level!
