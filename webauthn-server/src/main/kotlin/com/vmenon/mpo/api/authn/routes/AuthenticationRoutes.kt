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
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.call
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import io.ktor.util.pipeline.PipelineContext
import org.koin.ktor.ext.inject
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import java.util.UUID

fun Application.configureAuthenticationRoutes() {
    val logger = LoggerFactory.getLogger("AuthenticationRoutes")

    routing {
        val assertionStorage: AssertionRequestStorage by inject()
        val relyingParty: RelyingParty by inject()
        val openTelemetryTracer: OpenTelemetryTracer by inject()

        post("/authenticate/start") {
            handleAuthenticationStart(assertionStorage, relyingParty, openTelemetryTracer, logger)
        }

        post("/authenticate/complete") {
            handleAuthenticationComplete(assertionStorage, relyingParty, logger)
        }
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.handleAuthenticationStart(
    assertionStorage: AssertionRequestStorage,
    relyingParty: RelyingParty,
    openTelemetryTracer: OpenTelemetryTracer,
    logger: Logger,
) {
    runCatching {
        val request = openTelemetryTracer.traceOperation("call.receive") {
            call.receive<AuthenticationRequest>()
        }

        if (validateAuthenticationRequest(request)) return

        val requestId = UUID.randomUUID().toString()
        val startAssertionOptions =
            createStartAssertionOptions(request, relyingParty, openTelemetryTracer)

        assertionStorage.storeAssertionRequest(requestId, startAssertionOptions)

        val authResponse =
            createAuthenticationResponse(requestId, startAssertionOptions, openTelemetryTracer)
        call.respond(authResponse)
    }.onFailure { exception ->
        handleAuthenticationError(call, logger, exception, "Authentication start failed")
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.handleAuthenticationComplete(
    assertionStorage: AssertionRequestStorage,
    relyingParty: RelyingParty,
    logger: Logger,
) {
    runCatching {
        val request = call.receive<AuthenticationCompleteRequest>()

        val startAssertionOptions =
            retrieveAssertionRequest(request.requestId, assertionStorage) ?: return

        val finishAssertionResult =
            processAssertionFinish(startAssertionOptions, request, relyingParty)

        if (finishAssertionResult.isSuccess) {
            handleSuccessfulAuthentication(finishAssertionResult.username, logger)
        } else {
            handleFailedAuthentication(logger)
        }
    }.onFailure { exception ->
        handleAuthenticationError(call, logger, exception, "Authentication complete failed")
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.validateAuthenticationRequest(
    request: AuthenticationRequest,
): Boolean {
    if (request.username != null && request.username.isBlank()) {
        call.respond(
            HttpStatusCode.BadRequest,
            mapOf("error" to "Username cannot be empty if provided"),
        )
        return true
    }
    return false
}

private suspend fun createStartAssertionOptions(
    request: AuthenticationRequest,
    relyingParty: RelyingParty,
    openTelemetryTracer: OpenTelemetryTracer,
) = if (request.username != null) {
    openTelemetryTracer.traceOperation("relyingParty.startAssertion.withUsername") {
        relyingParty.startAssertion(
            StartAssertionOptions.builder()
                .username(request.username)
                .build(),
        )
    }
} else {
    openTelemetryTracer.traceOperation("relyingParty.startAssertion.usernameless") {
        relyingParty.startAssertion(
            StartAssertionOptions.builder()
                .build(),
        )
    }
}

private suspend fun createAuthenticationResponse(
    requestId: String,
    startAssertionOptions: com.yubico.webauthn.AssertionRequest,
    openTelemetryTracer: OpenTelemetryTracer,
): AuthenticationResponse {
    val credentialsJson = openTelemetryTracer.traceOperation("toCredentialsGetJson") {
        startAssertionOptions.toCredentialsGetJson()
    }
    val credentialsObject = openTelemetryTracer.readTree(credentialsJson)

    return AuthenticationResponse(
        requestId = requestId,
        publicKeyCredentialRequestOptions = credentialsObject,
    )
}

private suspend fun PipelineContext<Unit, ApplicationCall>.retrieveAssertionRequest(
    requestId: String,
    assertionStorage: AssertionRequestStorage,
): com.yubico.webauthn.AssertionRequest? {
    val options = assertionStorage.retrieveAndRemoveAssertionRequest(requestId)
    if (options == null) {
        call.respond(
            HttpStatusCode.BadRequest,
            mapOf("error" to "Invalid or expired request ID"),
        )
    }
    return options
}

private fun processAssertionFinish(
    startAssertionOptions: com.yubico.webauthn.AssertionRequest,
    request: AuthenticationCompleteRequest,
    relyingParty: RelyingParty,
) = relyingParty.finishAssertion(
    FinishAssertionOptions.builder()
        .request(startAssertionOptions)
        .response(PublicKeyCredential.parseAssertionResponseJson(request.credential))
        .build(),
)

private suspend fun PipelineContext<Unit, ApplicationCall>.handleSuccessfulAuthentication(
    username: String,
    logger: Logger,
) {
    logger.info("Successfully authenticated user: $username")
    call.respond(
        mapOf(
            "success" to true,
            "message" to "Authentication successful",
            "username" to username,
        ),
    )
}

private suspend fun PipelineContext<Unit, ApplicationCall>.handleFailedAuthentication(
    logger: Logger,
) {
    logger.warn("This is a test, remove")

    logger.warn("Authentication failed for assertion validation")
    call.respond(
        HttpStatusCode.Unauthorized,
        mapOf("error" to "Authentication failed"),
    )
}

private suspend fun handleAuthenticationError(
    call: ApplicationCall,
    logger: Logger,
    exception: Throwable,
    message: String
) {
    logger.error(message, exception)
    call.respond(
        HttpStatusCode.InternalServerError,
        mapOf("error" to "Authentication failed. Please try again."),
    )
}
