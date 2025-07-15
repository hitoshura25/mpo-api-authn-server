package com.vmenon.mpo.api.authn.storage.redis

import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.utils.JacksonUtils.objectMapper
import com.yubico.webauthn.AssertionRequest
import redis.clients.jedis.JedisPool

/**
 * Redis-based implementation of AssertionRequestStorage
 */
class RedisAssertionRequestStorage(
    private val jedisPool: JedisPool,
    private val keyPrefix: String = "webauthn:auth:"
) : AssertionRequestStorage {

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
