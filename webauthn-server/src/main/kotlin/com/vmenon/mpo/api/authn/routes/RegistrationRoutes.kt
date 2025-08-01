package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.RegistrationCompleteRequest
import com.vmenon.mpo.api.authn.RegistrationRequest
import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.call
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import io.ktor.util.pipeline.PipelineContext
import java.util.UUID
import org.koin.ktor.ext.inject
import org.slf4j.LoggerFactory

fun Application.configureRegistrationRoutes() {
    val logger = LoggerFactory.getLogger("RegistrationRoutes")

    routing {
        val registrationStorage: RegistrationRequestStorage by inject()
        val relyingParty: RelyingParty by inject()
        val credentialStorage: CredentialStorage by inject()
        val openTelemetryTracer: OpenTelemetryTracer by inject()

        post("/register/start") {
            handleRegistrationStart(
                registrationStorage, relyingParty, credentialStorage, openTelemetryTracer, logger
            )
        }

        post("/register/complete") {
            handleRegistrationComplete(registrationStorage, relyingParty, credentialStorage, logger)
        }
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.handleRegistrationStart(
    registrationStorage: RegistrationRequestStorage,
    relyingParty: RelyingParty,
    credentialStorage: CredentialStorage,
    openTelemetryTracer: OpenTelemetryTracer,
    logger: org.slf4j.Logger,
) {
    try {
        val request = openTelemetryTracer.traceOperation("call.receive") {
            call.receive<RegistrationRequest>()
        }

        if (validateRegistrationRequest(request)) return
        if (checkUserDoesNotExist(request.username, credentialStorage, openTelemetryTracer, logger)) {
            return
        }

        val requestId = UUID.randomUUID().toString()
        val registrationResponse = RegistrationUtils.createRegistrationResponse(
            request, requestId, relyingParty, registrationStorage, openTelemetryTracer
        )

        call.respond(registrationResponse)
    } catch (e: com.fasterxml.jackson.core.JsonProcessingException) {
        handleRegistrationError(call, logger, e, "Registration start failed")
    } catch (e: redis.clients.jedis.exceptions.JedisException) {
        handleRegistrationError(call, logger, e, "Registration start failed")
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.validateRegistrationRequest(
    request: RegistrationRequest,
): Boolean {
    val errorMessage = when {
        request.username.isBlank() -> "Username is required"
        request.displayName.isBlank() -> "Display name is required"
        else -> null
    }

    return if (errorMessage != null) {
        call.respond(HttpStatusCode.BadRequest, mapOf("error" to errorMessage))
        true
    } else {
        false
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.checkUserDoesNotExist(
    username: String,
    credentialStorage: CredentialStorage,
    openTelemetryTracer: OpenTelemetryTracer,
    logger: org.slf4j.Logger,
): Boolean {
    val userAlreadyExists = openTelemetryTracer.traceOperation("checkUserExists") {
        credentialStorage.userExists(username)
    }

    return if (userAlreadyExists) {
        logger.info("Registration attempt for existing user: $username")
        call.respond(
            HttpStatusCode.Conflict,
            mapOf("error" to "Username is already registered"),
        )
        true
    } else {
        false
    }
}


private suspend fun PipelineContext<Unit, ApplicationCall>.handleRegistrationComplete(
    registrationStorage: RegistrationRequestStorage,
    relyingParty: RelyingParty,
    credentialStorage: CredentialStorage,
    logger: org.slf4j.Logger,
) {
    try {
        val request = call.receive<RegistrationCompleteRequest>()

        val startRegistrationOptions = retrieveRegistrationRequest(request.requestId, registrationStorage)
            ?: return

        val finishRegistrationResult = RegistrationUtils.processRegistrationFinish(
            startRegistrationOptions, request, relyingParty
        )
        val userAccount = RegistrationUtils.createUserAccount(startRegistrationOptions)
        val registration = RegistrationUtils.createCredentialRegistration(userAccount, finishRegistrationResult)

        if (checkForRaceCondition(userAccount.username, credentialStorage, logger)) {
            return
        }

        credentialStorage.addRegistration(registration)
        logger.info("Successfully registered user: ${userAccount.username}")
        call.respond(mapOf("success" to true, "message" to "Registration successful"))
    } catch (e: com.fasterxml.jackson.core.JsonProcessingException) {
        handleRegistrationError(call, logger, e, "Registration complete failed")
    } catch (e: redis.clients.jedis.exceptions.JedisException) {
        handleRegistrationError(call, logger, e, "Registration complete failed")
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.retrieveRegistrationRequest(
    requestId: String,
    registrationStorage: RegistrationRequestStorage,
): PublicKeyCredentialCreationOptions? {
    val options = registrationStorage.retrieveAndRemoveRegistrationRequest(requestId)
    if (options == null) {
        call.respond(
            HttpStatusCode.BadRequest,
            mapOf("error" to "Invalid or expired request ID"),
        )
    }
    return options
}


private suspend fun PipelineContext<Unit, ApplicationCall>.checkForRaceCondition(
    username: String,
    credentialStorage: CredentialStorage,
    logger: org.slf4j.Logger,
): Boolean {
    return if (credentialStorage.userExists(username)) {
        logger.warn("Race condition detected: User $username was created during registration")
        call.respond(
            HttpStatusCode.Conflict,
            mapOf("error" to "Username is already registered"),
        )
        true
    } else {
        false
    }
}

private suspend fun handleRegistrationError(
    call: ApplicationCall,
    logger: org.slf4j.Logger,
    exception: Exception,
    message: String
) {
    logger.error(message, exception)
    call.respond(
        HttpStatusCode.InternalServerError,
        mapOf("error" to "Registration failed. Please try again."),
    )
}
