package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.AuthenticationCompleteRequest
import com.vmenon.mpo.api.authn.AuthenticationRequest
import com.vmenon.mpo.api.authn.AuthenticationResponse
import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.yubico.webauthn.FinishAssertionOptions
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.StartAssertionOptions
import com.yubico.webauthn.data.PublicKeyCredential
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import java.util.UUID
import org.koin.ktor.ext.inject
import org.slf4j.LoggerFactory

fun Application.configureAuthenticationRoutes() {
    val logger = LoggerFactory.getLogger("AuthenticationRoutes")

    routing {
        val assertionStorage: AssertionRequestStorage by inject()
        val relyingParty: RelyingParty by inject()
        val openTelemetryTracer: OpenTelemetryTracer by inject()

        post("/authenticate/start") {
            try {
                val request = openTelemetryTracer.traceOperation("call.receive") {
                    call.receive<AuthenticationRequest>()
                }

                // Validate input - username can be null for usernameless flow
                if (request.username != null && request.username.isBlank()) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "Username cannot be empty if provided")
                    )
                    return@post
                }

                val requestId = UUID.randomUUID().toString()

                val startAssertionOptions = if (request.username != null && request.username.isNotBlank()) {
                    openTelemetryTracer.traceOperation("relyingParty.startAssertion.withUsername") {
                        relyingParty.startAssertion(
                            StartAssertionOptions.builder()
                                .username(request.username)
                                .build()
                        )
                    }
                } else {
                    openTelemetryTracer.traceOperation("relyingParty.startAssertion.usernameless") {
                        relyingParty.startAssertion(
                            StartAssertionOptions.builder()
                                .build()
                        )
                    }
                }

                assertionStorage.storeAssertionRequest(requestId, startAssertionOptions)

                val credentialsJson = openTelemetryTracer.traceOperation("toCredentialsGetJson") {
                    startAssertionOptions.toCredentialsGetJson()
                }
                val credentialsObject = openTelemetryTracer.readTree(credentialsJson)

                openTelemetryTracer.traceOperation("call.response") {
                    val response = AuthenticationResponse(
                        requestId = requestId,
                        publicKeyCredentialRequestOptions = credentialsObject
                    )
                    call.respond(response)
                }

            } catch (e: Exception) {
                logger.error("Authentication start failed", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    mapOf("error" to "Authentication failed. Please try again.")
                )
            }
        }

        post("/authenticate/complete") {
            try {
                val request = call.receive<AuthenticationCompleteRequest>()

                val startAssertionOptions = assertionStorage.retrieveAndRemoveAssertionRequest(request.requestId)
                if (startAssertionOptions == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "Invalid or expired request ID")
                    )
                    return@post
                }

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
                    logger.info("Successfully authenticated user: $username")
                    call.respond(
                        mapOf(
                            "success" to true,
                            "message" to "Authentication successful",
                            "username" to username
                        )
                    )
                } else {
                    logger.warn("Authentication failed for assertion validation")
                    call.respond(
                        HttpStatusCode.Unauthorized,
                        mapOf("error" to "Authentication failed")
                    )
                }

            } catch (e: IllegalArgumentException) {
                logger.warn("Authentication complete failed with invalid arguments", e)
                call.respond(
                    HttpStatusCode.BadRequest,
                    mapOf("error" to "Invalid authentication data")
                )
            } catch (e: Exception) {
                logger.error("Authentication complete failed", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    mapOf("error" to "Authentication failed. Please try again.")
                )
            }
        }
    }
}
