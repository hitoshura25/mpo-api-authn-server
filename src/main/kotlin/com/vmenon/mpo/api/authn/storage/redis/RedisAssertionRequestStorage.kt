package com.vmenon.mpo.api.authn.storage.redis

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.yubico.webauthn.AssertionRequest
import redis.clients.jedis.JedisPool
import redis.clients.jedis.JedisPoolConfig

/**
 * Redis-based implementation of AssertionRequestStorage
 */
class RedisAssertionRequestStorage(
    private val jedisPool: JedisPool,
    private val keyPrefix: String = "webauthn:auth:"
) : AssertionRequestStorage {

    private val objectMapper = ObjectMapper().apply {
        registerModule(KotlinModule.Builder().build())
        registerModule(JavaTimeModule())
    }

    companion object {
        fun create(
            host: String = "localhost",
            port: Int = 6379,
            password: String? = null,
            database: Int = 0,
            maxConnections: Int = 10
        ): RedisAssertionRequestStorage {
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

            return RedisAssertionRequestStorage(jedisPool)
        }
    }

    override fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long
    ) {
        val key = "$keyPrefix$requestId"
        val value = objectMapper.writeValueAsString(request)

        jedisPool.resource.use { jedis ->
            jedis.setex(key, ttlSeconds, value)
        }
    }

    override fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest? {
        val key = "$keyPrefix$requestId"

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
