package com.vmenon.mpo.api.authn.routes

import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import io.micrometer.prometheus.PrometheusMeterRegistry
import org.koin.ktor.ext.inject
import org.slf4j.LoggerFactory

fun Application.configureHealthRoutes() {
    val logger = LoggerFactory.getLogger("HealthRoutes")

    routing {
        val prometheusRegistry: PrometheusMeterRegistry by inject()

        get("/") {
            try {
                call.respondText("WebAuthn Server is running!")
            } catch (e: Exception) {
                logger.error("Root endpoint failed", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    mapOf("error" to "Server error")
                )
            }
        }

        get("/metrics") {
            try {
                val metrics = prometheusRegistry.scrape()
                call.respond(metrics)
            } catch (e: Exception) {
                logger.error("Metrics endpoint failed", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    mapOf("error" to "Metrics unavailable")
                )
            }
        }

        // Health check endpoint
        get("/health") {
            try {
                call.respond(
                    mapOf(
                        "status" to "healthy",
                        "timestamp" to System.currentTimeMillis()
                    )
                )
            } catch (e: Exception) {
                logger.error("Health check failed", e)
                call.respond(
                    HttpStatusCode.ServiceUnavailable,
                    mapOf("status" to "unhealthy", "error" to "Health check failed")
                )
            }
        }

        // Readiness probe
        get("/ready") {
            try {
                // TODO: Add actual readiness checks (database connectivity, etc.)
                call.respond(mapOf("status" to "ready"))
            } catch (e: Exception) {
                logger.error("Readiness check failed", e)
                call.respond(
                    HttpStatusCode.ServiceUnavailable,
                    mapOf("status" to "not ready", "error" to "Readiness check failed")
                )
            }
        }

        get("/live") {
            try {
                // Add liveness checks here
                call.respondText("Alive", contentType = ContentType.Text.Plain)
            } catch (e: Exception) {
                logger.error("Liveness check failed", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    mapOf("error" to "Liveness check failed")
                )
            }
        }
    }
}
