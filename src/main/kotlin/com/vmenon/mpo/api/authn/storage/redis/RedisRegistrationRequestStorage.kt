package com.vmenon.mpo.api.authn.storage.redis

import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.utils.JacksonUtils.objectMapper
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import redis.clients.jedis.JedisPool

/**
 * Redis-based implementation of RegistrationRequestStorage
 */
class RedisRegistrationRequestStorage(
    private val jedisPool: JedisPool,
    private val keyPrefix: String = "webauthn:reg:"
) : RegistrationRequestStorage {

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
