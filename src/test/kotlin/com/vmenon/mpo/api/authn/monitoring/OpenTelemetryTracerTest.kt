package com.vmenon.mpo.api.authn.monitoring

import com.vmenon.mpo.api.authn.di.appModule
import com.vmenon.mpo.api.authn.di.monitoringModule
import com.vmenon.mpo.api.authn.di.storageModule
import com.vmenon.mpo.api.authn.test_utils.BaseIntegrationTest
import io.ktor.server.testing.testApplication
import io.opentelemetry.api.trace.Tracer
import java.util.UUID
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.koin.core.context.startKoin
import org.koin.core.context.stopKoin
import org.koin.test.get
import redis.clients.jedis.JedisPool
import redis.clients.jedis.exceptions.JedisConnectionException

class OpenTelemetryTracerTest : BaseIntegrationTest() {
    lateinit var openTelemetryTracer: OpenTelemetryTracer
    lateinit var jedisPool: JedisPool

    @BeforeEach
    fun setup() {
        startKoin {
            modules(listOf(appModule, storageModule, monitoringModule))
        }

        val tracer = get<Tracer>()
        jedisPool = get<JedisPool>()
        openTelemetryTracer = OpenTelemetryTracer(tracer)
    }

    @AfterEach
    fun cleanup() {
        stopKoin()
    }

    @Test
    fun `given Redis down when calling delete should throw connection exception`() = testApplication {
        redis.close()
        assertThrows<JedisConnectionException> {
            openTelemetryTracer.del(jedisPool, UUID.randomUUID().toString())
        }
        redis.start()
    }
}