# Multi-stage build for optimal security and performance
# Production WebAuthn server prioritizes security with distroless image

# Stage 1: Setup stage with tools
# Updated to latest Eclipse Temurin to include January 2025 security patches (Java 21.0.8+)
FROM eclipse-temurin:21.0.8_9-jre-jammy AS setup

# Install tools needed for setup (better layer caching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/false -M appuser

# Stage 2: Ultra-secure production runtime (distroless)
FROM gcr.io/distroless/java21-debian12 AS app

# Copy user from setup stage
COPY --from=setup /etc/passwd /etc/passwd
COPY --from=setup /etc/group /etc/group

# Set working directory
WORKDIR /app

# Copy the shadow JAR (this layer changes when app changes)
COPY --chown=appuser:appgroup build/libs/webauthn-server-1.0-SNAPSHOT-all.jar app.jar

# Switch to non-root user
USER appuser

# Expose port 8080
EXPOSE 8080

# JVM optimization for containerized environments
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:+UseG1GC \
               -XX:+UseStringDeduplication \
               -XX:+OptimizeStringConcat \
               -XX:+UnlockExperimentalVMOptions \
               -XX:+EnableJVMCI \
               -Djava.security.egd=file:/dev/./urandom"

# Run the application with optimized JVM settings (distroless uses java directly)
ENTRYPOINT ["java", "-XX:+UseContainerSupport", "-XX:MaxRAMPercentage=75.0", "-XX:+UseG1GC", "-XX:+UseStringDeduplication", "-XX:+OptimizeStringConcat", "-XX:+UnlockExperimentalVMOptions", "-XX:+EnableJVMCI", "-Djava.security.egd=file:/dev/./urandom", "-jar", "app.jar"]