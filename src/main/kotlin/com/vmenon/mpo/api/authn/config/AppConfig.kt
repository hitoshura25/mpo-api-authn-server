package com.vmenon.mpo.api.authn.config

/**
 * Configuration properties for the WebAuthn application
 */
data class AppConfig(
    val storage: StorageConfig,
    val relyingParty: RelyingPartyConfig,
    val server: ServerConfig
)

data class StorageConfig(
    val type: String,
    val redis: RedisConfig?
)

data class RedisConfig(
    val host: String,
    val port: Int,
    val password: String?,
    val database: Int,
    val maxConnections: Int
)

data class RelyingPartyConfig(
    val id: String,
    val name: String
)

data class ServerConfig(
    val port: Int,
    val host: String
)
