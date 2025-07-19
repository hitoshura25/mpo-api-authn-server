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

fun Application.configureAuthenticationRoutes() {
    routing {
        val assertionStorage: AssertionRequestStorage by inject()
        val relyingParty: RelyingParty by inject()
        val openTelemetryTracer: OpenTelemetryTracer by inject()

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
            val credentialsJson = openTelemetryTracer.traceOperation("toCredentialsCreateJson") {
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
    }
}
