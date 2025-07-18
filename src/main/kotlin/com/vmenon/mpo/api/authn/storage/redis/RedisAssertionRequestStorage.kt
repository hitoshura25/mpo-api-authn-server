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
    private val redisOpenTelemetryHelper: RedisOpenTelemetryHelper,
    private val keyPrefix: String = "webauthn:auth:",
) : AssertionRequestStorage {

    override fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long
    ) {
        val key = "$keyPrefix$requestId"
        val value = objectMapper.writeValueAsString(request)
        redisOpenTelemetryHelper.setex(jedisPool, key, ttlSeconds, value)
    }

    override fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest? {
        val key = "$keyPrefix$requestId"
        val value = redisOpenTelemetryHelper.get(jedisPool, key)
        return if (value != null) {
            redisOpenTelemetryHelper.del(jedisPool, key) // Remove after retrieving
            objectMapper.readValue(value, AssertionRequest::class.java)
        } else {
            null
        }
    }

    override fun close() {
        jedisPool.close()
    }
}
