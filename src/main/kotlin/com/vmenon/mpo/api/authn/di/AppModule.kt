package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.ScalableCredentialRepository
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryAssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryCredentialRepository
import com.vmenon.mpo.api.authn.storage.inmem.InMemoryRegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.postgresql.SecurePostgreSQLCredentialRepository
import com.vmenon.mpo.api.authn.storage.redis.RedisAssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.redis.RedisRegistrationRequestStorage
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.data.RelyingPartyIdentity
import org.koin.core.qualifier.named
import org.koin.dsl.module

/**
 * Koin dependency injection module for WebAuthn application with separated storage interfaces
 */
val appModule = module {
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

    // Database configuration
    single(named("dbHost")) {
        System.getProperty("DB_HOST") ?: System.getenv("DB_HOST") ?: "localhost"
    }

    single(named("dbPort")) {
        (System.getProperty("DB_PORT") ?: System.getenv("DB_PORT"))?.toIntOrNull() ?: 5432
    }

    single(named("dbName")) {
        System.getProperty("DB_NAME") ?: System.getenv("DB_NAME") ?: "webauthn"
    }

    single(named("dbUsername")) {
        System.getProperty("DB_USERNAME") ?: System.getenv("DB_USERNAME") ?: "webauthn_user"
    }

    single(named("dbPassword")) {
        System.getProperty("DB_PASSWORD") ?: System.getenv("DB_PASSWORD") ?: "webauthn_password"
    }

    single(named("dbMaxPoolSize")) {
        (System.getProperty("DB_MAX_POOL_SIZE") ?: System.getenv("DB_MAX_POOL_SIZE"))?.toIntOrNull() ?: 10
    }

    // Encryption configuration for secure credential storage
    single(named("encryptionKey")) {
        System.getProperty("ENCRYPTION_KEY") ?: System.getenv("ENCRYPTION_KEY")
    }

    // Registration Storage implementations
    single<RegistrationRequestStorage>(named("redis")) {
        val host: String by inject(named("redisHost"))
        val port: Int by inject(named("redisPort"))
        val password: String? by inject(named("redisPassword"))
        val database: Int by inject(named("redisDatabase"))
        val maxConnections: Int by inject(named("redisMaxConnections"))

        RedisRegistrationRequestStorage.create(
            host = host,
            port = port,
            password = password,
            database = database,
            maxConnections = maxConnections
        )
    }

    single<RegistrationRequestStorage>(named("memory")) {
        InMemoryRegistrationRequestStorage()
    }

    single<RegistrationRequestStorage> {
        val storageType: String by inject(named("storageType"))
        when (storageType.lowercase()) {
            "redis" -> {
                println("Initializing Redis registration storage...")
                get<RegistrationRequestStorage>(named("redis"))
            }

            "memory" -> {
                println("WARNING: Using in-memory registration storage - not suitable for production multi-instance deployments")
                get<RegistrationRequestStorage>(named("memory"))
            }

            else -> {
                throw IllegalArgumentException("Unsupported storage type: $storageType. Supported types: redis, memory")
            }
        }
    }

    single<AssertionRequestStorage>(named("redis")) {
        val host: String by inject(named("redisHost"))
        val port: Int by inject(named("redisPort"))
        val password: String? by inject(named("redisPassword"))
        val database: Int by inject(named("redisDatabase"))
        val maxConnections: Int by inject(named("redisMaxConnections"))

        RedisAssertionRequestStorage.create(
            host = host,
            port = port,
            password = password,
            database = database,
            maxConnections = maxConnections
        )
    }

    single<AssertionRequestStorage>(named("memory")) {
        InMemoryAssertionRequestStorage()
    }

    single<AssertionRequestStorage> {
        val storageType: String by inject(named("storageType"))
        when (storageType.lowercase()) {
            "redis" -> {
                println("Initializing Redis assertion storage...")
                get<AssertionRequestStorage>(named("redis"))
            }

            "memory" -> {
                println("WARNING: Using in-memory assertion storage - not suitable for production multi-instance deployments")
                get<AssertionRequestStorage>(named("memory"))
            }

            else -> {
                throw IllegalArgumentException("Unsupported storage type: $storageType. Supported types: redis, memory")
            }
        }
    }

    // Credential Repository implementations
    single<ScalableCredentialRepository>(named("postgresql")) {
        val host: String by inject(named("dbHost"))
        val port: Int by inject(named("dbPort"))
        val database: String by inject(named("dbName"))
        val username: String by inject(named("dbUsername"))
        val password: String by inject(named("dbPassword"))
        val maxPoolSize: Int by inject(named("dbMaxPoolSize"))
        val encryptionKey: String? by inject(named("encryptionKey"))

        SecurePostgreSQLCredentialRepository.create(
            host = host,
            port = port,
            database = database,
            username = username,
            password = password,
            maxPoolSize = maxPoolSize,
            encryptionKeyBase64 = encryptionKey
        )
    }

    single<ScalableCredentialRepository>(named("memory")) {
        InMemoryCredentialRepository()
    }

    // Primary credential repository bean - PostgreSQL for production, memory for development
    single<ScalableCredentialRepository> {
        val storageType: String by inject(named("storageType"))
        when (storageType.lowercase()) {
            "redis", "postgresql", "database" -> {
                println("Initializing PostgreSQL credential repository...")
                get<ScalableCredentialRepository>(named("postgresql"))
            }

            "memory" -> {
                println("WARNING: Using in-memory credential repository - not suitable for production multi-instance deployments")
                get<ScalableCredentialRepository>(named("memory"))
            }

            else -> {
                throw IllegalArgumentException("Unsupported storage type: $storageType. Supported types: redis, postgresql, memory")
            }
        }
    }

    single {
        val relyingPartyId: String by inject(named("relyingPartyId"))
        val relyingPartyName: String by inject(named("relyingPartyName"))
        val credentialRepository: ScalableCredentialRepository by inject()

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
