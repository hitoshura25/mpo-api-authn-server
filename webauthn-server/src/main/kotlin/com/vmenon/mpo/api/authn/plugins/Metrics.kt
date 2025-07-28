package com.vmenon.mpo.api.authn.plugins

import io.ktor.server.application.Application
import io.ktor.server.application.install
import io.ktor.server.metrics.micrometer.MicrometerMetrics
import io.ktor.server.request.httpMethod
import io.ktor.server.request.uri
import io.micrometer.core.instrument.binder.jvm.JvmGcMetrics
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics
import io.micrometer.core.instrument.binder.jvm.JvmThreadMetrics
import io.micrometer.core.instrument.binder.system.ProcessorMetrics
import io.micrometer.prometheus.PrometheusMeterRegistry
import org.koin.ktor.ext.inject

fun Application.configureMetrics() {
    val prometheusRegistry: PrometheusMeterRegistry by inject()

    install(MicrometerMetrics) {
        registry = prometheusRegistry

        meterBinders = listOf(
            JvmMemoryMetrics(),
            JvmGcMetrics(),
            JvmThreadMetrics(),
            ProcessorMetrics()
        )

        // Custom metrics
        timers { call, _ ->
            tag("method", call.request.httpMethod.value)
            tag("route", call.request.uri)
            tag("status", call.response.status()?.value.toString())
        }
    }
}
