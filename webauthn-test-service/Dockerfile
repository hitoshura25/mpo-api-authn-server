# Test service prioritizes debuggability while maintaining good security
# Using Ubuntu LTS for glibc performance and debugging tools

FROM eclipse-temurin:21-jre-jammy AS base

# Install debugging and monitoring tools (better layer caching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    netcat-openbsd \
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
COPY --chown=appuser:appgroup build/libs/webauthn-test-service.jar app.jar

# Switch to non-root user
USER appuser

# Expose port 8081
EXPOSE 8081

# Health check with proper timeout and startup period
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8081/health || exit 1

# JVM optimization for containerized environments
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:+UseG1GC \
               -XX:+UseStringDeduplication \
               -XX:+OptimizeStringConcat \
               -Djava.security.egd=file:/dev/./urandom"

# Run the application with optimized JVM settings
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]