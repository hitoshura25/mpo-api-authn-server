# Build stage
FROM gradle:8.13-jdk21 AS build

WORKDIR /app

# Copy Gradle wrapper and build files first (changes less frequently)
COPY gradle gradle
COPY gradlew gradlew.bat build.gradle.kts ./

# Copy source code (changes more frequently, so comes after dependency download)
COPY src src

# Build the application (no clean needed since we want to keep the cached dependencies)
RUN --mount=type=cache,target=~/.gradle ./gradlew shadowJar --parallel --no-daemon

# Runtime stage
FROM openjdk:21-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy the built JAR from build stage
COPY --from=build /app/build/libs/*-all.jar app.jar

# Change ownership to non-root user
RUN chown appuser:appuser app.jar

# Switch to non-root user
USER appuser

# Expose the port your Ktor app runs on
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]
