package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import java.util.Optional
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.assertThrows
import org.koin.core.context.startKoin
import org.koin.core.context.stopKoin
import org.koin.core.error.InstanceCreationException
import org.koin.core.qualifier.named
import org.koin.test.KoinTest
import org.koin.test.get

@TestInstance(TestInstance.Lifecycle.PER_METHOD)
class MonitoringModuleTest : KoinTest {

    @AfterEach
    fun cleanup() {
        clearAllTestProperties()
        stopKoin()
    }

    // OpenTelemetry Service Name Tests
    @Test
    fun `OpenTelemetry service name should work through Koin DI when configured via system property`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME, "test-service")

        startKoin {
            modules(monitoringModule)
        }

        val serviceName = get<String>(named("openTelemetryServiceName"))
        assertEquals("test-service", serviceName)
    }

    @Test
    fun `OpenTelemetry service name should use default value when not configured through Koin DI`() {
        startKoin {
            modules(monitoringModule)
        }

        val serviceName = get<String>(named("openTelemetryServiceName"))
        assertEquals("MPO-API-AUTHN", serviceName)
    }

    @Test
    fun `Should throw InstanceCreationException when OpenTelemetry service name is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME, "")

        startKoin {
            modules(monitoringModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("openTelemetryServiceName"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when OpenTelemetry service name is whitespace only`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME, "   ")

        startKoin {
            modules(monitoringModule)
        }

        assertThrows<InstanceCreationException> {
            get<String>(named("openTelemetryServiceName"))
        }
    }

    // OpenTelemetry Jaeger Endpoint Tests
    @Test
    fun `OpenTelemetry Jaeger endpoint should work through Koin DI when configured via system property`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT, "http://jaeger:14250")

        startKoin {
            modules(monitoringModule)
        }

        val jaegerEndpoint = get<Optional<String>>(named("openTelemetryJaegerEndpoint"))
        assertTrue(jaegerEndpoint.isPresent)
        assertEquals("http://jaeger:14250", jaegerEndpoint.get())
    }

    @Test
    fun `OpenTelemetry Jaeger endpoint should be empty Optional when not configured through Koin DI`() {
        startKoin {
            modules(monitoringModule)
        }

        val jaegerEndpoint = get<Optional<String>>(named("openTelemetryJaegerEndpoint"))
        assertFalse(jaegerEndpoint.isPresent)
    }

    @Test
    fun `Should throw InstanceCreationException when OpenTelemetry Jaeger endpoint is blank`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT, "")

        startKoin {
            modules(monitoringModule)
        }

        assertThrows<InstanceCreationException> {
            get<Optional<String>>(named("openTelemetryJaegerEndpoint"))
        }
    }

    @Test
    fun `Should throw InstanceCreationException when OpenTelemetry Jaeger endpoint is whitespace only`() {
        System.setProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT, "   ")

        startKoin {
            modules(monitoringModule)
        }

        assertThrows<InstanceCreationException> {
            get<Optional<String>>(named("openTelemetryJaegerEndpoint"))
        }
    }

    private fun clearAllTestProperties() {
        val properties = listOf(
            EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME,
            EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT
        )
        properties.forEach { System.clearProperty(it) }
    }
}
