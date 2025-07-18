package com.vmenon.mpo.api.authn.storage.redis

import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import redis.clients.jedis.JedisPool

/**
 * Redis-based implementation of RegistrationRequestStorage
 */
class RedisRegistrationRequestStorage(
    private val jedisPool: JedisPool,
    private val openTelemetryTracer: OpenTelemetryTracer,
    private val keyPrefix: String = "webauthn:reg:",
) : RegistrationRequestStorage {

    override fun storeRegistrationRequest(
        requestId: String,
        options: PublicKeyCredentialCreationOptions,
        ttlSeconds: Long
    ) {
        openTelemetryTracer.traceOperation("RedisRegistrationRequestStorage.storeRegistrationRequest") {
            val key = "$keyPrefix$requestId"
            val value = openTelemetryTracer.writeValueAsString(options)
            openTelemetryTracer.setex(jedisPool, key, ttlSeconds, value)
        }
    }

    override fun retrieveAndRemoveRegistrationRequest(requestId: String): PublicKeyCredentialCreationOptions? {
        return openTelemetryTracer.traceOperation("RedisRegistrationRequestStorage.retrieveAndRemoveRegistrationRequest") {
            val key = "$keyPrefix$requestId"
            val value = openTelemetryTracer.get(jedisPool, key)
            if (value != null) {
                openTelemetryTracer.del(jedisPool, key) // Remove after retrieving
                openTelemetryTracer.readValue(value, PublicKeyCredentialCreationOptions::class.java)
            } else {
                null
            }
        }
    }

    override fun close() {
        jedisPool.close()
    }
}
