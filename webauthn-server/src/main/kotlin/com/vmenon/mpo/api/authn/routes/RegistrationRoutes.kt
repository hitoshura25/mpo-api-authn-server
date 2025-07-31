package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.RegistrationCompleteRequest
import com.vmenon.mpo.api.authn.RegistrationRequest
import com.vmenon.mpo.api.authn.RegistrationResponse
import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.yubico.webauthn.FinishRegistrationOptions
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.StartRegistrationOptions
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.PublicKeyCredential
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import com.yubico.webauthn.data.UserIdentity
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
import org.slf4j.LoggerFactory
import java.util.Base64
import java.util.UUID

fun Application.configureRegistrationRoutes() {
    val logger = LoggerFactory.getLogger("RegistrationRoutes")

    routing {
        val registrationStorage: RegistrationRequestStorage by inject()
        val relyingParty: RelyingParty by inject()
        val credentialStorage: CredentialStorage by inject()
        val openTelemetryTracer: OpenTelemetryTracer by inject()

        post("/register/start") {
            handleRegistrationStart(registrationStorage, relyingParty, credentialStorage, openTelemetryTracer, logger)
        }

        post("/register/complete") {
            handleRegistrationComplete(registrationStorage, relyingParty, credentialStorage, openTelemetryTracer, logger)
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
        val registrationResponse = createRegistrationResponse(
            request, requestId, relyingParty, registrationStorage, openTelemetryTracer
        )
        
        call.respond(registrationResponse)
    } catch (e: Exception) {
        logger.error("Registration start failed", e)
        call.respond(
            HttpStatusCode.InternalServerError,
            mapOf("error" to "Registration failed. Please try again."),
        )
    }
}

private suspend fun PipelineContext<Unit, ApplicationCall>.validateRegistrationRequest(request: RegistrationRequest): Boolean {
    if (request.username.isBlank()) {
        call.respond(
            HttpStatusCode.BadRequest,
            mapOf("error" to "Username is required"),
        )
        return true
    }

    if (request.displayName.isBlank()) {
        call.respond(
            HttpStatusCode.BadRequest,
            mapOf("error" to "Display name is required"),
        )
        return true
    }
    return false
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

private suspend fun createRegistrationResponse(
    request: RegistrationRequest,
    requestId: String,
    relyingParty: RelyingParty,
    registrationStorage: RegistrationRequestStorage,
    openTelemetryTracer: OpenTelemetryTracer,
): RegistrationResponse {
    val userHandle = ByteArray.fromBase64Url(
        Base64.getUrlEncoder().withoutPadding()
            .encodeToString(UUID.randomUUID().toString().toByteArray()),
    )

    val user = openTelemetryTracer.traceOperation("buildUserIdentity") {
        UserIdentity.builder()
            .name(request.username)
            .displayName(request.displayName)
            .id(userHandle)
            .build()
    }

    val startRegistrationOptions = openTelemetryTracer.traceOperation("relyingParty.startRegistration") {
        relyingParty.startRegistration(
            StartRegistrationOptions.builder()
                .user(user)
                .build(),
        )
    }

    registrationStorage.storeRegistrationRequest(requestId, startRegistrationOptions)

    val credentialsJson = openTelemetryTracer.traceOperation("toCredentialsCreateJson") {
        startRegistrationOptions.toCredentialsCreateJson()
    }
    val credentialsObject = openTelemetryTracer.readTree(credentialsJson)

    return RegistrationResponse(
        requestId = requestId,
        publicKeyCredentialCreationOptions = credentialsObject,
    )
}

private suspend fun PipelineContext<Unit, ApplicationCall>.handleRegistrationComplete(
    registrationStorage: RegistrationRequestStorage,
    relyingParty: RelyingParty,
    credentialStorage: CredentialStorage,
    openTelemetryTracer: OpenTelemetryTracer,
    logger: org.slf4j.Logger,
) {
    try {
        val request = call.receive<RegistrationCompleteRequest>()

        val startRegistrationOptions = retrieveRegistrationRequest(request.requestId, registrationStorage)
            ?: return

        val finishRegistrationResult = processRegistrationFinish(startRegistrationOptions, request, relyingParty)
        val userAccount = createUserAccount(startRegistrationOptions)
        val registration = createCredentialRegistration(userAccount, finishRegistrationResult)

        if (checkForRaceCondition(userAccount.username, credentialStorage, logger)) {
            return
        }

        credentialStorage.addRegistration(registration)
        logger.info("Successfully registered user: ${userAccount.username}")
        call.respond(mapOf("success" to true, "message" to "Registration successful"))
    } catch (e: Exception) {
        logger.error("Registration complete failed", e)
        call.respond(
            HttpStatusCode.InternalServerError,
            mapOf("error" to "Registration failed. Please try again."),
        )
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

private fun processRegistrationFinish(
    startRegistrationOptions: PublicKeyCredentialCreationOptions,
    request: RegistrationCompleteRequest,
    relyingParty: RelyingParty,
) = relyingParty.finishRegistration(
    FinishRegistrationOptions.builder()
        .request(startRegistrationOptions)
        .response(PublicKeyCredential.parseRegistrationResponseJson(request.credential))
        .build(),
)

private fun createUserAccount(startRegistrationOptions: PublicKeyCredentialCreationOptions) =
    UserAccount(
        username = startRegistrationOptions.user.name,
        displayName = startRegistrationOptions.user.displayName,
        userHandle = startRegistrationOptions.user.id,
    )

private fun createCredentialRegistration(
    userAccount: UserAccount,
    finishRegistrationResult: com.yubico.webauthn.RegistrationResult,
) = CredentialRegistration(
    userAccount = userAccount,
    credential = RegisteredCredential.builder()
        .credentialId(finishRegistrationResult.keyId.id)
        .userHandle(userAccount.userHandle)
        .publicKeyCose(finishRegistrationResult.publicKeyCose)
        .signatureCount(finishRegistrationResult.signatureCount)
        .build(),
)

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
