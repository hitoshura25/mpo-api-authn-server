package com.vmenon.mpo.api.authn.storage

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.yubico.webauthn.AssertionRequest
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import redis.clients.jedis.JedisPool
import redis.clients.jedis.JedisPoolConfig

/**
 * Redis-based implementation of RequestStorage for scalable WebAuthn request storage
 */
class RedisRequestStorage(
    private val jedisPool: JedisPool,
    private val keyPrefix: String = "webauthn:"
) : RequestStorage {

    private val objectMapper = ObjectMapper().apply {
        registerModule(KotlinModule.Builder().build())
        registerModule(JavaTimeModule())
    }

    companion object {
        private const val REGISTRATION_PREFIX = "reg:"
        private const val ASSERTION_PREFIX = "auth:"

        fun create(
            host: String = "localhost",
            port: Int = 6379,
            password: String? = null,
            database: Int = 0,
            maxConnections: Int = 10
        ): RedisRequestStorage {
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

            return RedisRequestStorage(jedisPool)
        }
    }

    override fun storeRegistrationRequest(
        requestId: String,
        options: PublicKeyCredentialCreationOptions,
        ttlSeconds: Long
    ) {
        val key = "$keyPrefix$REGISTRATION_PREFIX$requestId"
        val value = objectMapper.writeValueAsString(options)

        jedisPool.resource.use { jedis ->
            jedis.setex(key, ttlSeconds, value)
        }
    }

    override fun retrieveAndRemoveRegistrationRequest(requestId: String): PublicKeyCredentialCreationOptions? {
        val key = "$keyPrefix$REGISTRATION_PREFIX$requestId"

        return jedisPool.resource.use { jedis ->
            val value = jedis.get(key)
            if (value != null) {
                jedis.del(key) // Remove after retrieving
                objectMapper.readValue(value, PublicKeyCredentialCreationOptions::class.java)
            } else {
                null
            }
        }
    }

    override fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long
    ) {
        val key = "$keyPrefix$ASSERTION_PREFIX$requestId"
        val value = objectMapper.writeValueAsString(request)

        jedisPool.resource.use { jedis ->
            jedis.setex(key, ttlSeconds, value)
        }
    }

    override fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest? {
        val key = "$keyPrefix$ASSERTION_PREFIX$requestId"

        return jedisPool.resource.use { jedis ->
            val value = jedis.get(key)
            if (value != null) {
                jedis.del(key) // Remove after retrieving
                objectMapper.readValue(value, AssertionRequest::class.java)
            } else {
                null
            }
        }
    }

    override fun close() {
        jedisPool.close()
    }
}
