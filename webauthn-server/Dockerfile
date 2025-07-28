# Use OpenJDK 21 runtime as base image
FROM openjdk:21-jre-slim

# Set working directory
WORKDIR /app

# Copy the shadow JAR
COPY build/libs/webauthn-test-service.jar app.jar

# Expose port 8081
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]