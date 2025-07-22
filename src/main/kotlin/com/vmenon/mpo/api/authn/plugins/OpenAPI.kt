package com.vmenon.mpo.api.authn.plugins

import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.plugins.swagger.swaggerUI
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing

fun Application.configureOpenAPI() {
    routing {
        // Serve the static OpenAPI specification
        get("/openapi") {
            val openApiContent = this::class.java.classLoader
                .getResourceAsStream("openapi/documentation.yaml")
                ?.readBytes()
                ?.toString(Charsets.UTF_8)

            if (openApiContent != null) {
                call.respondText(openApiContent, ContentType.Text.Plain)
            } else {
                call.respond(HttpStatusCode.NotFound, "OpenAPI specification not found")
            }
        }

        // Swagger UI configuration - simplified to avoid code generation issues
        swaggerUI(path = "swagger") {
            version = "4.15.5"
        }
    }
}
