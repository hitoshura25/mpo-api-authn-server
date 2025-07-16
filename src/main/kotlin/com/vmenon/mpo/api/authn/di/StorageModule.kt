package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.postgresql.QuantumSafeCredentialStorage
import com.vmenon.mpo.api.authn.storage.redis.RedisAssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.redis.RedisRegistrationRequestStorage
import org.koin.core.qualifier.named
import org.koin.dsl.module
import redis.clients.jedis.JedisPool
import redis.clients.jedis.JedisPoolConfig

val storageModule = module {
    single(named("redisHost")) {
        val value = System.getProperty("MPO_AUTHN_REDIS_HOST") ?: System.getenv("MPO_AUTHN_REDIS_HOST") ?: "localhost"
        require(value.isNotBlank()) { "MPO_AUTHN_REDIS_HOST cannot be blank" }
        value
    }

    single(named("redisPort")) {
        val portString = System.getProperty("MPO_AUTHN_REDIS_PORT") ?: System.getenv("MPO_AUTHN_REDIS_PORT")
        if (portString != null) {
            require(portString.isNotBlank()) { "MPO_AUTHN_REDIS_PORT cannot be blank" }
        }
        portString?.toIntOrNull() ?: 6379
    }

    single(named("redisPassword")) {
        val value = System.getProperty("MPO_AUTHN_REDIS_PASSWORD") ?: System.getenv("MPO_AUTHN_REDIS_PASSWORD")
        requireNotNull(value) { "MPO_AUTHN_REDIS_PASSWORD is required but was not provided" }
        require(value.isNotBlank()) { "MPO_AUTHN_REDIS_PASSWORD cannot be blank" }
        value
    }

    single(named("redisDatabase")) {
        val databaseString = System.getProperty("MPO_AUTHN_REDIS_DATABASE") ?: System.getenv("MPO_AUTHN_REDIS_DATABASE")
        if (databaseString != null) {
            require(databaseString.isNotBlank()) { "MPO_AUTHN_REDIS_DATABASE cannot be blank" }
        }
        databaseString?.toIntOrNull() ?: 0
    }

    single(named("redisMaxConnections")) {
        val connectionsString =
            System.getProperty("MPO_AUTHN_REDIS_MAX_CONNECTIONS") ?: System.getenv("MPO_AUTHN_REDIS_MAX_CONNECTIONS")
        if (connectionsString != null) {
            require(connectionsString.isNotBlank()) { "MPO_AUTHN_REDIS_MAX_CONNECTIONS cannot be blank" }
        }
        connectionsString?.toIntOrNull() ?: 10
    }

    single(named("dbHost")) {
        val value = System.getProperty("MPO_AUTHN_DB_HOST") ?: System.getenv("MPO_AUTHN_DB_HOST") ?: "localhost"
        require(value.isNotBlank()) { "MPO_AUTHN_DB_HOST cannot be blank" }
        value
    }

    single(named("dbPort")) {
        val portString = System.getProperty("MPO_AUTHN_DB_PORT") ?: System.getenv("MPO_AUTHN_DB_PORT")
        if (portString != null) {
            require(portString.isNotBlank()) { "MPO_AUTHN_DB_PORT cannot be blank" }
        }
        portString?.toIntOrNull() ?: 5432
    }

    single(named("dbName")) {
        val value = System.getProperty("MPO_AUTHN_DB_NAME") ?: System.getenv("MPO_AUTHN_DB_NAME") ?: "webauthn"
        require(value.isNotBlank()) { "MPO_AUTHN_DB_NAME cannot be blank" }
        value
    }

    single(named("dbUsername")) {
        val value = System.getProperty("MPO_AUTHN_DB_USERNAME") ?: System.getenv("MPO_AUTHN_DB_USERNAME")
        requireNotNull(value) { "MPO_AUTHN_DB_USERNAME is required but was not provided" }
        require(value.isNotBlank()) { "MPO_AUTHN_DB_USERNAME cannot be blank" }
        value
    }

    single(named("dbPassword")) {
        val value = System.getProperty("MPO_AUTHN_DB_PASSWORD") ?: System.getenv("MPO_AUTHN_DB_PASSWORD")
        requireNotNull(value) { "MPO_AUTHN_DB_PASSWORD is required but was not provided" }
        require(value.isNotBlank()) { "MPO_AUTHN_DB_PASSWORD cannot be blank" }
        value
    }

    single(named("dbMaxPoolSize")) {
        val poolSizeString =
            System.getProperty("MPO_AUTHN_DB_MAX_POOL_SIZE") ?: System.getenv("MPO_AUTHN_DB_MAX_POOL_SIZE")
        if (poolSizeString != null) {
            require(poolSizeString.isNotBlank()) { "MPO_AUTHN_DB_MAX_POOL_SIZE cannot be blank" }
        }
        poolSizeString?.toIntOrNull() ?: 10
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
        RedisRegistrationRequestStorage(jedisPool)
    }

    single<AssertionRequestStorage> {
        val jedisPool: JedisPool by inject()
        RedisAssertionRequestStorage(jedisPool)
    }

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
    }
}