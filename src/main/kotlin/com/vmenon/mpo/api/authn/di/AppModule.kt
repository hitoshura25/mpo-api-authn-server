package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.InMemoryCredentialRepository
import com.vmenon.mpo.api.authn.storage.InMemoryRequestStorage
import com.vmenon.mpo.api.authn.storage.RedisRequestStorage
import com.vmenon.mpo.api.authn.storage.RequestStorage
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.data.RelyingPartyIdentity
import org.koin.core.qualifier.named
import org.koin.dsl.module

/**
 * Koin dependency injection module for WebAuthn application
 */
val appModule = module {

    // Configuration beans - Read from system properties first, then environment variables
    single(named("storageType")) {
        System.getProperty("STORAGE_TYPE") ?: System.getenv("STORAGE_TYPE") ?: "memory"
    }

    single(named("redisHost")) {
        System.getProperty("REDIS_HOST") ?: System.getenv("REDIS_HOST") ?: "localhost"
    }

    single(named("redisPort")) {
        (System.getProperty("REDIS_PORT") ?: System.getenv("REDIS_PORT"))?.toIntOrNull() ?: 6379
    }

    single(named("redisPassword")) {
        System.getProperty("REDIS_PASSWORD") ?: System.getenv("REDIS_PASSWORD")
    }

    single(named("redisDatabase")) {
        (System.getProperty("REDIS_DATABASE") ?: System.getenv("REDIS_DATABASE"))?.toIntOrNull() ?: 0
    }

    single(named("redisMaxConnections")) {
        (System.getProperty("REDIS_MAX_CONNECTIONS") ?: System.getenv("REDIS_MAX_CONNECTIONS"))?.toIntOrNull() ?: 10
    }

    single(named("relyingPartyId")) {
        System.getProperty("RELYING_PARTY_ID") ?: System.getenv("RELYING_PARTY_ID") ?: "localhost"
    }

    single(named("relyingPartyName")) {
        System.getProperty("RELYING_PARTY_NAME") ?: System.getenv("RELYING_PARTY_NAME") ?: "WebAuthn Demo"
    }

    // Storage implementations
    single<RequestStorage>(named("redis")) {
        val host: String by inject(named("redisHost"))
        val port: Int by inject(named("redisPort"))
        val password: String? by inject(named("redisPassword"))
        val database: Int by inject(named("redisDatabase"))
        val maxConnections: Int by inject(named("redisMaxConnections"))

        RedisRequestStorage.create(
            host = host,
            port = port,
            password = password,
            database = database,
            maxConnections = maxConnections
        )
    }

    single<RequestStorage>(named("memory")) {
        InMemoryRequestStorage()
    }

    // Primary storage bean - selects implementation based on configuration
    single<RequestStorage> {
        val storageType: String by inject(named("storageType"))
        when (storageType.lowercase()) {
            "redis" -> {
                println("Initializing Redis storage...")
                get<RequestStorage>(named("redis"))
            }

            "memory" -> {
                println("WARNING: Using in-memory storage - not suitable for production multi-instance deployments")
                get<RequestStorage>(named("memory"))
            }

            else -> {
                throw IllegalArgumentException("Unsupported storage type: $storageType. Supported types: redis, memory")
            }
        }
    }

    // Credential repository
    single { InMemoryCredentialRepository() }

    // RelyingParty
    single {
        val relyingPartyId: String by inject(named("relyingPartyId"))
        val relyingPartyName: String by inject(named("relyingPartyName"))
        val credentialRepository: InMemoryCredentialRepository by inject()

        RelyingParty.builder()
            .identity(
                RelyingPartyIdentity.builder()
                    .id(relyingPartyId)
                    .name(relyingPartyName)
                    .build()
            )
            .credentialRepository(credentialRepository)
            .build()
    }
}
