package com.vmenon.mpo.api.authn.storage.redis

import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.yubico.webauthn.AssertionRequest
import redis.clients.jedis.JedisPool

/**
 * Redis-based implementation of AssertionRequestStorage
 */
class RedisAssertionRequestStorage(
    private val jedisPool: JedisPool,
    private val openTelemetryTracer: OpenTelemetryTracer,
    private val keyPrefix: String = "webauthn:auth:",
) : AssertionRequestStorage {

    override fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long
    ) {
        openTelemetryTracer.traceOperation("RedisAssertionRequestStorage.storeAssertionRequest") {
            val key = "$keyPrefix$requestId"
            val value = openTelemetryTracer.writeValueAsString(request)
            openTelemetryTracer.setex(jedisPool, key, ttlSeconds, value)
        }
    }

    override fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest? {
        return openTelemetryTracer.traceOperation("RedisAssertionRequestStorage.retrieveAndRemoveAssertionRequest") {
            val key = "$keyPrefix$requestId"
            val value = openTelemetryTracer.get(jedisPool, key)
            if (value != null) {
                openTelemetryTracer.del(jedisPool, key) // Remove after retrieving
                openTelemetryTracer.readValue(value, AssertionRequest::class.java)
            } else {
                null
            }
        }
    }

    override fun close() {
        jedisPool.close()
    }
}
