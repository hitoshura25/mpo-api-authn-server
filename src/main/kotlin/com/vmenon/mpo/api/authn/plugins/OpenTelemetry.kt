package com.vmenon.mpo.api.authn.plugins

import io.ktor.server.application.Application
import io.ktor.server.application.install
import io.ktor.server.plugins.origin
import io.ktor.server.request.ApplicationRequest
import io.ktor.server.request.httpMethod
import io.ktor.server.request.uri
import io.ktor.server.request.userAgent
import io.opentelemetry.api.OpenTelemetry
import io.opentelemetry.instrumentation.api.instrumenter.SpanNameExtractor
import io.opentelemetry.instrumentation.ktor.v2_0.KtorServerTelemetry
import org.koin.ktor.ext.inject

fun Application.configureOpenTelemetry() {
    val openTelemetry: OpenTelemetry by inject()

    install(KtorServerTelemetry) {
        setOpenTelemetry(openTelemetry)

        // Custom span names
        spanNameExtractor {
            SpanNameExtractor<ApplicationRequest> { request ->
                "${request.httpMethod.value} ${request.uri}"
            }
        }

        attributesExtractor {
            onStart {
                attributes.put("http.user_agent", request.userAgent() ?: "unknown")
                attributes.put("http.client_ip", request.origin.remoteHost)
            }

            onEnd {
                attributes.put("http.response.size", response?.headers?.get("Content-Length")?.toLongOrNull() ?: 0L)

                val statusCode = response?.status()?.value ?: 500
                if (statusCode >= 400) {
                    attributes.put("http.error", "HTTP $statusCode")
                }
            }
        }
    }
}
