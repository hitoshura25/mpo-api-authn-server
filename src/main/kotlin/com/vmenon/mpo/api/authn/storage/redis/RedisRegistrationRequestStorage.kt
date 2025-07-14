package com.vmenon.mpo.api.authn.storage.redis

import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.utils.JacksonUtils.objectMapper
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import redis.clients.jedis.JedisPool
import redis.clients.jedis.JedisPoolConfig

/**
 * Redis-based implementation of RegistrationRequestStorage
 */
class RedisRegistrationRequestStorage(
    private val jedisPool: JedisPool,
    private val keyPrefix: String = "webauthn:reg:"
) : RegistrationRequestStorage {

    companion object {
        fun create(
            host: String = "localhost",
            port: Int = 6379,
            password: String? = null,
            database: Int = 0,
            maxConnections: Int = 10
        ): RedisRegistrationRequestStorage {
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

            return RedisRegistrationRequestStorage(jedisPool)
        }
    }

    override fun storeRegistrationRequest(
        requestId: String,
        options: PublicKeyCredentialCreationOptions,
        ttlSeconds: Long
    ) {
        val key = "$keyPrefix$requestId"
        val value = objectMapper.writeValueAsString(options)

        jedisPool.resource.use { jedis ->
            jedis.setex(key, ttlSeconds, value)
        }
    }

    override fun retrieveAndRemoveRegistrationRequest(requestId: String): PublicKeyCredentialCreationOptions? {
        val key = "$keyPrefix$requestId"

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

    override fun close() {
        jedisPool.close()
    }
}
