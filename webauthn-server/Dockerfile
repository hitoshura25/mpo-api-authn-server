# Multi-stage build for optimal layer caching and minimal image size

# Stage 1: Build stage (if needed for dependency extraction)
FROM eclipse-temurin:21-jre-alpine AS base

# Install dependencies that rarely change (better layer caching)
RUN apk add --no-cache \
    curl \
    wget \
    && rm -rf /var/cache/apk/*

# Stage 2: Application layer
FROM base AS app

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Set working directory
WORKDIR /app

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Copy the shadow JAR (this layer changes when app changes)
COPY build/libs/webauthn-server-1.0-SNAPSHOT-all.jar app.jar

# Ensure JAR is owned by app user
RUN chown appuser:appgroup app.jar

# Switch to non-root user
USER appuser

# Expose port 8080
EXPOSE 8080

# Health check with proper timeout and startup period
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# JVM optimization for containerized environments
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:+UseG1GC \
               -XX:+UseStringDeduplication \
               -XX:+OptimizeStringConcat \
               -Djava.security.egd=file:/dev/./urandom"

# Run the application with optimized JVM settings
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]