package com.vmenon.mpo.api.authn.config

/**
 * Constants for environment variable names used throughout the application.
 * This ensures consistent naming and prevents typos when referencing environment variables.
 */
object EnvironmentVariables {
    // Redis Configuration
    const val MPO_AUTHN_REDIS_HOST = "MPO_AUTHN_REDIS_HOST"
    const val MPO_AUTHN_REDIS_PORT = "MPO_AUTHN_REDIS_PORT"
    const val MPO_AUTHN_REDIS_PASSWORD = "MPO_AUTHN_REDIS_PASSWORD"
    const val MPO_AUTHN_REDIS_DATABASE = "MPO_AUTHN_REDIS_DATABASE"
    const val MPO_AUTHN_REDIS_MAX_CONNECTIONS = "MPO_AUTHN_REDIS_MAX_CONNECTIONS"

    // Database Configuration
    const val MPO_AUTHN_DB_HOST = "MPO_AUTHN_DB_HOST"
    const val MPO_AUTHN_DB_PORT = "MPO_AUTHN_DB_PORT"
    const val MPO_AUTHN_DB_NAME = "MPO_AUTHN_DB_NAME"
    const val MPO_AUTHN_DB_USERNAME = "MPO_AUTHN_DB_USERNAME"
    const val MPO_AUTHN_DB_PASSWORD = "MPO_AUTHN_DB_PASSWORD"
    const val MPO_AUTHN_DB_MAX_POOL_SIZE = "MPO_AUTHN_DB_MAX_POOL_SIZE"

    // Application Configuration
    const val MPO_AUTHN_APP_RELYING_PARTY_ID = "MPO_AUTHN_APP_RELYING_PARTY_ID"
    const val MPO_AUTHN_APP_RELYING_PARTY_NAME = "MPO_AUTHN_APP_RELYING_PARTY_NAME"

    // Monitoring
    const val MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME = "MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME"
    const val MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT = "MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT"

    // JWT Key Rotation Configuration
    const val MPO_AUTHN_JWT_KEY_ROTATION_ENABLED = "MPO_AUTHN_JWT_KEY_ROTATION_ENABLED"
    const val MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS = "MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS"
    const val MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES = "MPO_AUTHN_JWT_KEY_GRACE_PERIOD_MINUTES"
    const val MPO_AUTHN_JWT_KEY_RETENTION_MINUTES = "MPO_AUTHN_JWT_KEY_RETENTION_MINUTES"
    const val MPO_AUTHN_JWT_KEY_SIZE = "MPO_AUTHN_JWT_KEY_SIZE"
    const val MPO_AUTHN_JWT_KEY_ID_PREFIX = "MPO_AUTHN_JWT_KEY_ID_PREFIX"
    const val MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY = "MPO_AUTHN_JWT_MASTER_ENCRYPTION_KEY"

    // JWT Key Rotation - Override interval in seconds (for testing or fine-grained production control)
    // Takes precedence over MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS if set
    // Production default: Use MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL_DAYS (180 days)
    // Testing override: Set this to accelerate rotation (e.g., 30 seconds for E2E tests)
    const val MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS = "MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS"
}
