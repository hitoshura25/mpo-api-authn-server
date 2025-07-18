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
}
