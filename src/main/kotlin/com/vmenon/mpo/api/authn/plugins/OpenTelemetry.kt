package com.vmenon.mpo.api.authn.plugins

import io.ktor.server.application.Application
import io.ktor.server.application.install
import io.ktor.server.request.ApplicationRequest
import io.ktor.server.request.httpMethod
import io.ktor.server.request.uri
import io.opentelemetry.api.OpenTelemetry
import io.opentelemetry.instrumentation.api.instrumenter.SpanNameExtractor
import io.opentelemetry.instrumentation.ktor.v2_0.KtorServerTelemetry
import org.koin.ktor.ext.inject

fun Application.configureOpenTelemetry() {
    val openTelemetry: OpenTelemetry by inject()

    install(KtorServerTelemetry) {
        setOpenTelemetry(openTelemetry)
        spanNameExtractor {
            SpanNameExtractor<ApplicationRequest> { request ->
                "${request.httpMethod.value} ${request.uri}"
            }
        }
        attributesExtractor {
            onStart {
                attributes.put("http.request.timestamp", System.currentTimeMillis())
            }
            onEnd {
                attributes.put("http.response.timestamp", System.currentTimeMillis())
            }
        }
    }
}
