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
        System.getProperty("MPO_AUTHN_REDIS_HOST") ?: System.getenv("MPO_AUTHN_REDIS_HOST") ?: "localhost"
    }

    single(named("redisPort")) {
        (System.getProperty("MPO_AUTHN_REDIS_PORT") ?: System.getenv("MPO_AUTHN_REDIS_PORT"))?.toIntOrNull() ?: 6379
    }

    single(named("redisPassword")) {
        System.getProperty("MPO_AUTHN_REDIS_PASSWORD") ?: System.getenv("MPO_AUTHN_REDIS_PASSWORD")
    }

    single(named("redisDatabase")) {
        (System.getProperty("MPO_AUTHN_REDIS_DATABASE") ?: System.getenv("MPO_AUTHN_REDIS_DATABASE"))?.toIntOrNull()
            ?: 0
    }

    single(named("redisMaxConnections")) {
        (System.getProperty("MPO_AUTHN_REDIS_MAX_CONNECTIONS")
            ?: System.getenv("MPO_AUTHN_REDIS_MAX_CONNECTIONS"))?.toIntOrNull() ?: 10
    }

    single(named("dbHost")) {
        System.getProperty("MPO_AUTHN_DB_HOST") ?: System.getenv("MPO_AUTHN_DB_HOST") ?: "localhost"
    }

    single(named("dbPort")) {
        (System.getProperty("MPO_AUTHN_DB_PORT") ?: System.getenv("MPO_AUTHN_DB_PORT"))?.toIntOrNull() ?: 5432
    }

    single(named("dbName")) {
        System.getProperty("MPO_AUTHN_DB_NAME") ?: System.getenv("MPO_AUTHN_DB_NAME") ?: "webauthn"
    }

    single(named("dbUsername")) {
        System.getProperty("MPO_AUTHN_DB_USERNAME") ?: System.getenv("MPO_AUTHN_DB_USERNAME") ?: "webauthn_user"
    }

    single(named("dbPassword")) {
        System.getProperty("MPO_AUTHN_DB_PASSWORD") ?: System.getenv("MPO_AUTHN_DB_PASSWORD") ?: "webauthn_password"
    }

    single(named("dbMaxPoolSize")) {
        (System.getProperty("MPO_AUTHN_DB_MAX_POOL_SIZE") ?: System.getenv("MPO_AUTHN_DB_MAX_POOL_SIZE"))?.toIntOrNull()
            ?: 10
    }

    factory<JedisPool> {
        val host: String by inject(named("redisHost"))
        val port: Int by inject(named("redisPort"))
        val password: String? by inject(named("redisPassword"))
        val database: Int by inject(named("redisDatabase"))
        val maxConnections: Int by inject(named("redisMaxConnections"))
        val config = JedisPoolConfig().apply {
            maxTotal = maxConnections
            maxIdle = maxConnections / 2
            minIdle = 1
            testOnBorrow = true
            testOnReturn = true
        }
        val jedisPool = if (password != null) {
            JedisPool(config, host, port, 2000, password, database)
        } else {
            JedisPool(config, host, port, 2000, null, database)
        }
        jedisPool
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