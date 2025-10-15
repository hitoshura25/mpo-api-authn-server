# Production WebAuthn server using secure Eclipse Temurin base
# Updated to latest Eclipse Temurin Noble (Ubuntu 24.04) to fix zlib CVE-2023-45853 (Java 21.0.8+)
# Switched from distroless to eclipse-temurin:21.0.8_9-jre-noble (0 critical vulnerabilities)

FROM eclipse-temurin:21.0.8_9-jre-noble AS base

# Install minimal production tools for health checks and monitoring
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Stage 2: Application layer
FROM base AS app

# OCI Image Labels for Docker Hub MCP and metadata discovery
# Standard OCI annotations (https://github.com/opencontainers/image-spec/blob/main/annotations.md)
LABEL org.opencontainers.image.title="MPO WebAuthn Server" \
      org.opencontainers.image.description="WebAuthn (FIDO2/Passkeys) authentication server built with Ktor and comprehensive security testing" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Vinayak Menon <hitoshura25@users.noreply.github.com>" \
      org.opencontainers.image.url="https://github.com/hitoshura25/mpo-api-authn-server" \
      org.opencontainers.image.documentation="https://github.com/hitoshura25/mpo-api-authn-server/blob/main/README.md" \
      org.opencontainers.image.source="https://github.com/hitoshura25/mpo-api-authn-server" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="hitoshura25"

# AI Agent Discovery Labels - Point to structured configuration
LABEL com.mpo.ai-agents.config.url="https://raw.githubusercontent.com/hitoshura25/mpo-api-authn-server/main/.ai-agents.json" \
      com.mpo.ai-agents.config.format="json" \
      com.mpo.ai-agents.quick-start="https://github.com/hitoshura25/mpo-api-authn-server#for-ai-agents--developers"

# Environment Variable Documentation Labels
LABEL com.mpo.env.database.host="MPO_AUTHN_DB_HOST" \
      com.mpo.env.database.host.default="postgres" \
      com.mpo.env.database.port="MPO_AUTHN_DB_PORT" \
      com.mpo.env.database.port.default="5432" \
      com.mpo.env.database.name="MPO_AUTHN_DB_NAME" \
      com.mpo.env.database.name.default="webauthn_db" \
      com.mpo.env.database.username="MPO_AUTHN_DB_USERNAME" \
      com.mpo.env.database.username.default="webauthn_user" \
      com.mpo.env.database.password="MPO_AUTHN_DB_PASSWORD" \
      com.mpo.env.database.password.required="true" \
      com.mpo.env.database.password.sensitive="true"

LABEL com.mpo.env.redis.host="MPO_AUTHN_REDIS_HOST" \
      com.mpo.env.redis.host.default="redis" \
      com.mpo.env.redis.port="MPO_AUTHN_REDIS_PORT" \
      com.mpo.env.redis.port.default="6379" \
      com.mpo.env.redis.password="MPO_AUTHN_REDIS_PASSWORD" \
      com.mpo.env.redis.password.required="true" \
      com.mpo.env.redis.password.sensitive="true"

LABEL com.mpo.env.app.relying-party-id="MPO_AUTHN_APP_RELYING_PARTY_ID" \
      com.mpo.env.app.relying-party-id.default="localhost" \
      com.mpo.env.app.relying-party-id.description="Must match your frontend domain" \
      com.mpo.env.app.relying-party-name="MPO_AUTHN_APP_RELYING_PARTY_NAME" \
      com.mpo.env.app.relying-party-name.default="MPO Api Authn"

# Dependency Labels
LABEL com.mpo.dependencies.postgres.image="postgres:15-alpine" \
      com.mpo.dependencies.postgres.required="true" \
      com.mpo.dependencies.redis.image="redis:7-alpine" \
      com.mpo.dependencies.redis.required="true" \
      com.mpo.dependencies.jaeger.image="jaegertracing/all-in-one:1.53" \
      com.mpo.dependencies.jaeger.required="false"

# Port Exposure Labels
LABEL com.mpo.ports.http="8080" \
      com.mpo.ports.http.description="Main HTTP API endpoint"

# Security Feature Labels
LABEL com.mpo.security.webauthn.version="2.0" \
      com.mpo.security.features="username-enumeration-protection,replay-attack-prevention,poisonseed-protection,fido2-compliance"

# Create non-root user for security
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Set working directory
WORKDIR /app

# Copy the shadow JAR with proper ownership (this layer changes when app changes)
COPY --chown=appuser:appgroup build/libs/webauthn-server-1.0-SNAPSHOT-all.jar app.jar

# Switch to non-root user
USER appuser

# Expose port 8080
EXPOSE 8080

# Health check for production monitoring
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# JVM optimization for containerized environments
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:+UseG1GC \
               -XX:+UseStringDeduplication \
               -XX:+OptimizeStringConcat \
               -XX:+UnlockExperimentalVMOptions \
               -XX:+EnableJVMCI \
               -Djava.security.egd=file:/dev/./urandom"

# Run the application with optimized JVM settings
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]