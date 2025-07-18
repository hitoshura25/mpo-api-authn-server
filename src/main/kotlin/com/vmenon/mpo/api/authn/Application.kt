package com.vmenon.mpo.api.authn

import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.vmenon.mpo.api.authn.di.appModule
import com.vmenon.mpo.api.authn.di.monitoringModule
import com.vmenon.mpo.api.authn.di.storageModule
import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.yubico.webauthn.FinishAssertionOptions
import com.yubico.webauthn.FinishRegistrationOptions
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.StartAssertionOptions
import com.yubico.webauthn.StartRegistrationOptions
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.PublicKeyCredential
import com.yubico.webauthn.data.UserIdentity
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.serialization.jackson.jackson
import io.ktor.server.application.Application
import io.ktor.server.application.ApplicationStopping
import io.ktor.server.application.call
import io.ktor.server.application.install
import io.ktor.server.engine.embeddedServer
import io.ktor.server.metrics.micrometer.MicrometerMetrics
import io.ktor.server.netty.Netty
import io.ktor.server.plugins.callloging.CallLogging
import io.ktor.server.plugins.callloging.processingTimeMillis
import io.ktor.server.plugins.contentnegotiation.ContentNegotiation
import io.ktor.server.plugins.cors.routing.CORS
import io.ktor.server.plugins.origin
import io.ktor.server.plugins.statuspages.StatusPages
import io.ktor.server.request.ApplicationRequest
import io.ktor.server.request.httpMethod
import io.ktor.server.request.receive
import io.ktor.server.request.uri
import io.ktor.server.request.userAgent
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import io.micrometer.core.instrument.binder.jvm.JvmGcMetrics
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics
import io.micrometer.core.instrument.binder.jvm.JvmThreadMetrics
import io.micrometer.core.instrument.binder.system.ProcessorMetrics
import io.micrometer.prometheus.PrometheusMeterRegistry
import io.opentelemetry.api.OpenTelemetry
import io.opentelemetry.instrumentation.api.instrumenter.SpanNameExtractor
import io.opentelemetry.instrumentation.ktor.v2_0.KtorServerTelemetry
import java.security.SecureRandom
import java.util.UUID
import org.koin.core.module.Module
import org.koin.ktor.ext.inject
import org.koin.ktor.plugin.Koin
import org.koin.logger.slf4jLogger
import org.slf4j.event.Level

fun Application.module(storageModule: Module) {
    install(Koin) {
        slf4jLogger()
        modules(listOf(appModule, storageModule, monitoringModule))
    }

    val registrationStorage: RegistrationRequestStorage by inject()
    val assertionStorage: AssertionRequestStorage by inject()
    val relyingParty: RelyingParty by inject()
    val credentialStorage: CredentialStorage by inject()
    val openTelemetryTracer: OpenTelemetryTracer by inject()

    install(ContentNegotiation) {
        jackson {
            registerModule(KotlinModule.Builder().build())
            registerModule(JavaTimeModule())
            registerModule(Jdk8Module())
        }
    }

    install(CORS) {
        allowMethod(HttpMethod.Options)
        allowMethod(HttpMethod.Put)
        allowMethod(HttpMethod.Delete)
        allowMethod(HttpMethod.Patch)
        allowHeader(HttpHeaders.Authorization)
        allowHeader(HttpHeaders.ContentType)
        anyHost()
    }

    install(StatusPages) {
        exception<Throwable> { call, cause ->
            call.respond(HttpStatusCode.InternalServerError, "Error: ${cause.message}")
        }
    }

    // Prometheus metrics registry
    val prometheusRegistry: PrometheusMeterRegistry by inject()

    // Install Micrometer metrics
    install(MicrometerMetrics) {
        registry = prometheusRegistry

        // Add JVM metrics
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

    // Install call logging
    install(CallLogging) {
        level = Level.INFO
        format { call ->
            val status = call.response.status()
            val httpMethod = call.request.httpMethod.value
            val uri = call.request.uri
            val userAgent = call.request.headers["User-Agent"]
            val duration = call.processingTimeMillis()

            "$httpMethod $uri - $status (${duration}ms) - $userAgent"
        }

        // Filter out health check endpoints from logs
        filter { call ->
            !call.request.uri.startsWith("/health")
        }
    }

    val openTelemetry: OpenTelemetry by inject()
    install(KtorServerTelemetry) {
        setOpenTelemetry(openTelemetry)

        // Custom span names
        spanNameExtractor {
            SpanNameExtractor<ApplicationRequest> { request ->
                "${request.httpMethod.value} ${request.uri}"
            }
        }
        // Add custom attributes
        attributesExtractor {
            onStart {
                attributes.put("http.user_agent", request.userAgent() ?: "unknown")
                attributes.put("http.client_ip", request.origin.remoteHost)
            }

            onEnd {
                attributes.put("http.response.size", response?.headers?.get("Content-Length")?.toLongOrNull() ?: 0L)

                // Set span status based on HTTP status code
                val statusCode = response?.status()?.value ?: 500
                if (statusCode >= 400) {
                    attributes.put("http.error", "HTTP $statusCode")
                }
            }
        }
    }

    routing {
        get("/") {
            call.respondText("WebAuthn Server is running!")
        }

        post("/register/start") {
            val request = openTelemetryTracer.traceOperation("call.receive") {
                call.receive<RegistrationRequest>()
            }
            val requestId = UUID.randomUUID().toString()
            val userHandle = ByteArray(64)
            SecureRandom().nextBytes(userHandle)

            val user = openTelemetryTracer.traceOperation("buildUserIdentity") {
                UserIdentity.builder()
                    .name(request.username)
                    .displayName(request.displayName)
                    .id(ByteArray(userHandle))
                    .build()

            }

            val startRegistrationOptions = openTelemetryTracer.traceOperation("relyingParty.startRegistration") {
                relyingParty.startRegistration(
                    StartRegistrationOptions.builder()
                        .user(user)
                        .build()
                )
            }

            registrationStorage.storeRegistrationRequest(requestId, startRegistrationOptions)

            val response = openTelemetryTracer.traceOperation("createRegistrationResponse") {
                RegistrationResponse(
                    requestId = requestId,
                    publicKeyCredentialCreationOptions = startRegistrationOptions.toCredentialsCreateJson()
                )
            }

            openTelemetryTracer.traceOperation("call.response") {
                call.respond(response)
            }
        }

        post("/register/complete") {
            val request = call.receive<RegistrationCompleteRequest>()
            val startRegistrationOptions = registrationStorage.retrieveAndRemoveRegistrationRequest(request.requestId)
                ?: throw IllegalArgumentException("Invalid request ID")

            val finishRegistrationOptions = relyingParty.finishRegistration(
                FinishRegistrationOptions.builder()
                    .request(startRegistrationOptions)
                    .response(
                        PublicKeyCredential.parseRegistrationResponseJson(
                            request.credential
                        )
                    )
                    .build()
            )

            val userAccount = UserAccount(
                username = startRegistrationOptions.user.name,
                displayName = startRegistrationOptions.user.displayName,
                userHandle = startRegistrationOptions.user.id
            )

            val registration = CredentialRegistration(
                userAccount = userAccount,
                credential = RegisteredCredential.builder()
                    .credentialId(finishRegistrationOptions.keyId.id)
                    .userHandle(userAccount.userHandle)
                    .publicKeyCose(finishRegistrationOptions.publicKeyCose)
                    .signatureCount(finishRegistrationOptions.signatureCount)
                    .build()
            )

            credentialStorage.addRegistration(registration)

            call.respond(mapOf("success" to true, "message" to "Registration successful"))
        }

        post("/authenticate/start") {
            val request = call.receive<AuthenticationRequest>()
            val requestId = UUID.randomUUID().toString()

            val startAssertionOptions = if (request.username != null) {
                relyingParty.startAssertion(
                    StartAssertionOptions.builder()
                        .username(request.username)
                        .build()
                )
            } else {
                relyingParty.startAssertion(
                    StartAssertionOptions.builder()
                        .build()
                )
            }

            assertionStorage.storeAssertionRequest(requestId, startAssertionOptions)

            val response = AuthenticationResponse(
                requestId = requestId,
                publicKeyCredentialRequestOptions = startAssertionOptions.toCredentialsGetJson()
            )

            call.respond(response)
        }

        post("/authenticate/complete") {
            val request = call.receive<AuthenticationCompleteRequest>()
            val startAssertionOptions = assertionStorage.retrieveAndRemoveAssertionRequest(request.requestId)
                ?: throw IllegalArgumentException("Invalid request ID")

            val finishAssertionOptions = relyingParty.finishAssertion(
                FinishAssertionOptions.builder()
                    .request(startAssertionOptions)
                    .response(
                        PublicKeyCredential.parseAssertionResponseJson(
                            request.credential
                        )
                    )
                    .build()
            )

            if (finishAssertionOptions.isSuccess) {
                val username = finishAssertionOptions.username
                call.respond(mapOf("success" to true, "message" to "Authentication successful", "username" to username))
            } else {
                call.respond(HttpStatusCode.BadRequest, mapOf("success" to false, "message" to "Authentication failed"))
            }
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

    environment.monitor.subscribe(ApplicationStopping) {
        credentialStorage.close()
        registrationStorage.close()
        assertionStorage.close()
    }
}

fun main() {
    embeddedServer(Netty, port = 8080) {
        module(storageModule)
    }.start(wait = true)
}
