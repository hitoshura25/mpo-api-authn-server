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