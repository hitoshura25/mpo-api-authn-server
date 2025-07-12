# WebAuthn Server - Scalable Storage Configuration

## Environment Variables

Configure your storage backend using these environment variables:

### Redis Configuration (Production Recommended)

```bash
export STORAGE_TYPE=redis
export REDIS_HOST=localhost          # Redis server host
export REDIS_PORT=6379              # Redis server port
export REDIS_PASSWORD=your_password  # Redis password (optional)
export REDIS_DATABASE=0             # Redis database number
export REDIS_MAX_CONNECTIONS=10     # Maximum connection pool size
```

### In-Memory Configuration (Development Only)

```bash
export STORAGE_TYPE=memory
```

## Docker Compose Example

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass your_password

  webauthn-server:
    build: .
    ports:
      - "8080:8080"
    environment:
      - STORAGE_TYPE=redis
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=your_password
    depends_on:
      - redis
```

## Kubernetes ConfigMap Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: webauthn-config
data:
  STORAGE_TYPE: "redis"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  REDIS_DATABASE: "0"
  REDIS_MAX_CONNECTIONS: "20"
```

## Benefits of This Solution

1. **Scalability**: Works across multiple instances and cloud environments
2. **Performance**: Redis provides microsecond latency
3. **TTL Support**: Automatic cleanup of expired requests (5 minutes default)
4. **High Availability**: Redis supports clustering and replication
5. **Fallback**: In-memory option available for development

## Security Considerations

- Use Redis AUTH in production
- Enable Redis TLS for network encryption
- Configure Redis to bind to specific interfaces only
- Use short TTL values for WebAuthn challenges (5 minutes max)
