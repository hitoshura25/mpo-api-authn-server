package com.vmenon.mpo.api.authn.monitoring

import com.vmenon.mpo.api.authn.utils.JacksonUtils.objectMapper
import io.opentelemetry.api.trace.StatusCode
import io.opentelemetry.api.trace.Tracer
import io.opentelemetry.semconv.DbAttributes
import redis.clients.jedis.JedisPool

class OpenTelemetryTracer(
    private val tracer: Tracer,
) {
    suspend fun <T> traceOperation(operation: String, block: suspend () -> T): T {
        val span = tracer.spanBuilder(operation)
            .startSpan()

        return try {
            span.setStatus(StatusCode.OK)
            block()
        } catch (exception: Exception) {
            span.setStatus(StatusCode.ERROR, getMessage(exception))
            span.recordException(exception)
            throw exception
        } finally {
            span.end()
        }
    }

    suspend fun <T> writeValueAsString(value: T): String {
        return traceOperation("ObjectMapper.writeValueAsString") {
            objectMapper.writeValueAsString(value)
        }
    }

    suspend fun <T> readValue(content: String, valueType: Class<T>): T {
        return traceOperation("ObjectMapper.readValue") {
            objectMapper.readValue(content, valueType)
        }
    }

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
        } catch (exception: Exception) {
            span.setStatus(StatusCode.ERROR, getMessage(exception))
            span.recordException(exception)
            throw exception
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
        } catch (exception: Exception) {
            span.setStatus(StatusCode.ERROR, getMessage(exception))
            span.recordException(exception)
            throw exception
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
        } catch (exception: Exception) {
            span.setStatus(StatusCode.ERROR, getMessage(exception))
            span.recordException(exception)
            throw exception
        } finally {
            span.end()
        }
    }

    private fun getMessage(exception: Exception) = exception.message ?: "Unknown error"
}