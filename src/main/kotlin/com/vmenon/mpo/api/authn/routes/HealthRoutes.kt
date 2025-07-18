package com.vmenon.mpo.api.authn.routes

import io.ktor.http.ContentType
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import io.micrometer.prometheus.PrometheusMeterRegistry
import org.koin.ktor.ext.inject

fun Application.configureHealthRoutes() {
    routing {
        val prometheusRegistry: PrometheusMeterRegistry by inject()

        get("/") {
            call.respondText("WebAuthn Server is running!")
        }

        get("/metrics") {
            call.respond(prometheusRegistry.scrape())
        }

        // Health check endpoint
        get("/health") {
            call.respond(mapOf("status" to "healthy", "timestamp" to System.currentTimeMillis()))
        }

        // Readiness probe
        get("/ready") {
            call.respond(mapOf("status" to "ready"))
        }

        get("/live") {
            // Add liveness checks here
            call.respondText("Alive", contentType = ContentType.Text.Plain)
        }
    }
}
