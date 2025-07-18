package com.vmenon.mpo.api.authn.storage.redis

import io.opentelemetry.api.trace.StatusCode
import io.opentelemetry.api.trace.Tracer
import io.opentelemetry.semconv.DbAttributes
import redis.clients.jedis.JedisPool

class RedisOpenTelemetryHelper(
    private val tracer: Tracer,
) {
    fun setex(jedisPool: JedisPool, key: String, ttlSeconds: Long, value: String) {
        val span = tracer.spanBuilder("redis.setex")
            .setAttribute(DbAttributes.DB_SYSTEM_NAME, "redis")
            .setAttribute(DbAttributes.DB_OPERATION_NAME, "setex")
            .setAttribute("redis.key", key)
            .setAttribute("redis.ttl", ttlSeconds)
            .startSpan()

        try {
            jedisPool.resource.use { jedis ->
                jedis.setex(key, ttlSeconds, value)
            }
            span.setStatus(StatusCode.OK)
        } catch (e: Exception) {
            span.setStatus(StatusCode.ERROR, e.message ?: "Unknown error")
            span.recordException(e)
            throw e
        } finally {
            span.end()
        }
    }

    fun get(jedisPool: JedisPool, key: String): String? {
        val span = tracer.spanBuilder("redis.get")
            .setAttribute(DbAttributes.DB_SYSTEM_NAME, "redis")
            .setAttribute(DbAttributes.DB_OPERATION_NAME, "get")
            .setAttribute("redis.key", key)
            .startSpan()

        try {
            val value = jedisPool.resource.use { jedis ->
                jedis.get(key)
            }.also {
                span.setStatus(StatusCode.OK)
            }
            span.setAttribute("redis.found", value != null)
            return value
        } catch (e: Exception) {
            span.setStatus(StatusCode.ERROR, e.message ?: "Unknown error")
            span.recordException(e)
            throw e
        } finally {
            span.end()
        }
    }

    fun del(jedisPool: JedisPool, key: String) {
        val span = tracer.spanBuilder("redis.del")
            .setAttribute(DbAttributes.DB_SYSTEM_NAME, "redis")
            .setAttribute(DbAttributes.DB_OPERATION_NAME, "del")
            .setAttribute("redis.key", key)
            .startSpan()

        try {
            jedisPool.resource.use { jedis ->
                jedis.del(key)
            }.also {
                span.setStatus(StatusCode.OK)
            }
        } catch (e: Exception) {
            span.setStatus(StatusCode.ERROR, e.message ?: "Unknown error")
            span.recordException(e)
            throw e
        } finally {
            span.end()
        }
    }
}