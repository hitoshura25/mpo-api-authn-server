package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.postgresql.QuantumSafeCredentialStorage
import com.vmenon.mpo.api.authn.storage.redis.RedisAssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.redis.RedisRegistrationRequestStorage
import org.koin.core.qualifier.named
import org.koin.dsl.module
import org.koin.dsl.onClose
import redis.clients.jedis.JedisPool
import redis.clients.jedis.JedisPoolConfig

val storageModule = module {
    single(named("redisHost")) {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_REDIS_HOST)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_REDIS_HOST)
        requireNotNull(value) { "${EnvironmentVariables.MPO_AUTHN_REDIS_HOST} is required but was not provided" }
        require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_REDIS_HOST} cannot be blank" }
        value
    }

    single(named("redisPort")) {
        val portString = System.getProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PORT) ?: System.getenv(
            EnvironmentVariables.MPO_AUTHN_REDIS_PORT
        )
        if (portString != null) {
            require(portString.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_REDIS_PORT} cannot be blank" }
            val port = portString.toIntOrNull()
                ?: throw IllegalArgumentException("${EnvironmentVariables.MPO_AUTHN_REDIS_PORT} must be a valid integer, got: '$portString'")
            require(port in 1..65535) { "${EnvironmentVariables.MPO_AUTHN_REDIS_PORT} must be a valid port number (1-65535), got: $port" }
            port
        } else {
            6379
        }
    }

    single(named("redisPassword")) {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD) ?: System.getenv(
            EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD
        )
        requireNotNull(value) { "${EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD} is required but was not provided" }
        require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_REDIS_PASSWORD} cannot be blank" }
        value
    }

    single(named("redisDatabase")) {
        val databaseString = System.getProperty(EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE) ?: System.getenv(
            EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE
        )
        if (databaseString != null) {
            require(databaseString.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE} cannot be blank" }
            val database = databaseString.toIntOrNull()
                ?: throw IllegalArgumentException("${EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE} must be a valid integer, got: '$databaseString'")
            require(database >= 0) { "${EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE} must be non-negative, got: $database" }
            require(database <= 15) { "${EnvironmentVariables.MPO_AUTHN_REDIS_DATABASE} must be between 0-15 (standard Redis database range), got: $database" }
            database
        } else {
            0
        }
    }

    single(named("redisMaxConnections")) {
        val connectionsString =
            System.getProperty(EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS) ?: System.getenv(
                EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS
            )
        if (connectionsString != null) {
            require(connectionsString.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS} cannot be blank" }
            connectionsString.toIntOrNull()
                ?: throw IllegalArgumentException("${EnvironmentVariables.MPO_AUTHN_REDIS_MAX_CONNECTIONS} must be a valid integer, got: '$connectionsString'")
        } else {
            10
        }
    }

    single(named("dbHost")) {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_DB_HOST)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_DB_HOST)
        requireNotNull(value) { "${EnvironmentVariables.MPO_AUTHN_DB_HOST} is required but was not provided" }
        require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_DB_HOST} cannot be blank" }
        value
    }

    single(named("dbPort")) {
        val portString = System.getProperty(EnvironmentVariables.MPO_AUTHN_DB_PORT) ?: System.getenv(
            EnvironmentVariables.MPO_AUTHN_DB_PORT
        )
        if (portString != null) {
            require(portString.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_DB_PORT} cannot be blank" }
            val port = portString.toIntOrNull()
                ?: throw IllegalArgumentException("${EnvironmentVariables.MPO_AUTHN_DB_PORT} must be a valid integer, got: '$portString'")
            require(port in 1..65535) { "${EnvironmentVariables.MPO_AUTHN_DB_PORT} must be a valid port number (1-65535), got: $port" }
            port
        } else {
            5432
        }
    }

    single(named("dbName")) {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_DB_NAME)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_DB_NAME) ?: "webauthn"
        require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_DB_NAME} cannot be blank" }
        value
    }

    single(named("dbUsername")) {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_DB_USERNAME)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_DB_USERNAME)
        requireNotNull(value) { "${EnvironmentVariables.MPO_AUTHN_DB_USERNAME} is required but was not provided" }
        require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_DB_USERNAME} cannot be blank" }
        value
    }

    single(named("dbPassword")) {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_DB_PASSWORD)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_DB_PASSWORD)
        requireNotNull(value) { "${EnvironmentVariables.MPO_AUTHN_DB_PASSWORD} is required but was not provided" }
        require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_DB_PASSWORD} cannot be blank" }
        value
    }

    single(named("dbMaxPoolSize")) {
        val poolSizeString = System.getProperty(EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE) ?: System.getenv(
            EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE
        )
        if (poolSizeString != null) {
            require(poolSizeString.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE} cannot be blank" }
            poolSizeString.toIntOrNull()
                ?: throw IllegalArgumentException("${EnvironmentVariables.MPO_AUTHN_DB_MAX_POOL_SIZE} must be a valid integer, got: '$poolSizeString'")
        } else {
            10
        }
    }

    factory<JedisPool> {
        val host: String by inject(named("redisHost"))
        val port: Int by inject(named("redisPort"))
        val password: String by inject(named("redisPassword"))
        val database: Int by inject(named("redisDatabase"))
        val maxConnections: Int by inject(named("redisMaxConnections"))
        val config = JedisPoolConfig().apply {
            maxTotal = maxConnections
            maxIdle = maxConnections / 2
            minIdle = 1
            testOnBorrow = true
            testOnReturn = true
        }

        JedisPool(config, host, port, 2000, password, database)
    }

    single<RegistrationRequestStorage> {
        val jedisPool: JedisPool by inject()
        val openTelemetryHelper: OpenTelemetryTracer by inject()
        RedisRegistrationRequestStorage(jedisPool, openTelemetryHelper)
    }.onClose { it?.close() }

    single<AssertionRequestStorage> {
        val jedisPool: JedisPool by inject()
        val openTelemetryHelper: OpenTelemetryTracer by inject()
        RedisAssertionRequestStorage(jedisPool, openTelemetryHelper)
    }.onClose { it?.close() }

    single<CredentialStorage> {
        val host: String by inject(named("dbHost"))
        val port: Int by inject(named("dbPort"))
        val database: String by inject(named("dbName"))
        val username: String by inject(named("dbUsername"))
        val password: String by inject(named("dbPassword"))
        val maxPoolSize: Int by inject(named("dbMaxPoolSize"))

        QuantumSafeCredentialStorage.create(
            host = host,
            port = port,
            database = database,
            username = username,
            password = password,
            maxPoolSize = maxPoolSize,
        )
    }.onClose { it?.close() }
}