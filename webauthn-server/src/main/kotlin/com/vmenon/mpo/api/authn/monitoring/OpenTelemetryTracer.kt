package com.vmenon.mpo.api.authn.monitoring

import com.fasterxml.jackson.databind.JsonNode
import com.vmenon.mpo.api.authn.utils.JacksonUtils.objectMapper
import io.opentelemetry.api.trace.StatusCode
import io.opentelemetry.api.trace.Tracer
import io.opentelemetry.context.Context
import io.opentelemetry.semconv.DbAttributes
import redis.clients.jedis.JedisPool
import redis.clients.jedis.exceptions.JedisException

class OpenTelemetryTracer(
    private val tracer: Tracer,
) {
    suspend fun <T> traceOperation(
        operation: String,
        block: suspend () -> T,
    ): T {
        val span =
            tracer.spanBuilder(operation)
                .setParent(Context.current())
                .startSpan()

        return runCatching {
            span.setStatus(StatusCode.OK)
            block()
        }.fold(
            onSuccess = { result ->
                span.end()
                result
            },
            onFailure = { exception ->
                // OpenTelemetry tracing must catch all exceptions to record them before re-throwing
                span.setStatus(StatusCode.ERROR, getMessage(exception))
                span.recordException(exception)
                span.end()
                throw exception
            }
        )
    }

    suspend fun <T> writeValueAsString(value: T): String {
        return traceOperation("ObjectMapper.writeValueAsString") {
            objectMapper.writeValueAsString(value)
        }
    }

    suspend fun <T> readValue(
        content: String,
        valueType: Class<T>,
    ): T {
        return traceOperation("ObjectMapper.readValue") {
            objectMapper.readValue(content, valueType)
        }
    }

    suspend fun readTree(content: String): JsonNode {
        return traceOperation("ObjectMapper.readTree") {
            objectMapper.readTree(content)
        }
    }

    fun setex(
        jedisPool: JedisPool,
        key: String,
        ttlSeconds: Long,
        value: String,
    ) {
        val span =
            tracer.spanBuilder("redis.setex")
                .setAttribute(DbAttributes.DB_SYSTEM_NAME, "redis")
                .setAttribute(DbAttributes.DB_OPERATION_NAME, "setex")
                .setAttribute("redis.key", key)
                .setAttribute("redis.ttl", ttlSeconds)
                .setParent(Context.current())
                .startSpan()

        try {
            jedisPool.resource.use { jedis ->
                jedis.setex(key, ttlSeconds, value)
            }
            span.setStatus(StatusCode.OK)
        } catch (exception: JedisException) {
            span.setStatus(StatusCode.ERROR, getMessage(exception))
            span.recordException(exception)
            throw exception
        } finally {
            span.end()
        }
    }

    fun get(
        jedisPool: JedisPool,
        key: String,
    ): String? {
        val span =
            tracer.spanBuilder("redis.get")
                .setAttribute(DbAttributes.DB_SYSTEM_NAME, "redis")
                .setAttribute(DbAttributes.DB_OPERATION_NAME, "get")
                .setAttribute("redis.key", key)
                .setParent(Context.current())
                .startSpan()

        try {
            val value =
                jedisPool.resource.use { jedis ->
                    jedis.get(key)
                }.also {
                    span.setStatus(StatusCode.OK)
                }
            span.setAttribute("redis.found", value != null)
            return value
        } catch (exception: JedisException) {
            span.setStatus(StatusCode.ERROR, getMessage(exception))
            span.recordException(exception)
            throw exception
        } finally {
            span.end()
        }
    }

    fun del(
        jedisPool: JedisPool,
        key: String,
    ) {
        val span =
            tracer.spanBuilder("redis.del")
                .setAttribute(DbAttributes.DB_SYSTEM_NAME, "redis")
                .setAttribute(DbAttributes.DB_OPERATION_NAME, "del")
                .setAttribute("redis.key", key)
                .setParent(Context.current())
                .startSpan()

        try {
            jedisPool.resource.use { jedis ->
                jedis.del(key)
            }.also {
                span.setStatus(StatusCode.OK)
            }
        } catch (exception: JedisException) {
            span.setStatus(StatusCode.ERROR, getMessage(exception))
            span.recordException(exception)
            throw exception
        } finally {
            span.end()
        }
    }

    private fun getMessage(exception: Throwable) = exception.message ?: "Unknown error"
}
