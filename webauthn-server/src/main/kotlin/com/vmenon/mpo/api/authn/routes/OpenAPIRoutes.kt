package com.vmenon.mpo.api.authn.routes

import io.ktor.http.ContentType
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.plugins.swagger.swaggerUI
import io.ktor.server.response.respondRedirect
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing

fun Application.configureOpenAPIRoutes() {
    routing {
        // Serve the static OpenAPI specification
        get("/openapi") {
            val openApiContent =
                this::class.java.classLoader
                    .getResourceAsStream("openapi/documentation.yaml")!!
                    .readBytes()
                    .toString(Charsets.UTF_8)

            call.respondText(openApiContent, ContentType.Text.Plain)
        }

        // Redirect /swagger/ (with trailing slash) to /swagger (without trailing slash)
        // This improves UX since the Swagger UI plugin only handles /swagger
        get("/swagger/") {
            call.respondRedirect("/swagger", permanent = true)
        }

        // Swagger UI configuration - simplified to avoid code generation issues
        swaggerUI(path = "swagger") {
            version = "4.15.5"
        }
    }
}
