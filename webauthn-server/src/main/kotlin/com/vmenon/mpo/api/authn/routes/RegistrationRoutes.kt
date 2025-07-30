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
import com.yubico.webauthn.data.UserIdentity
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
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
            try {
                val request =
                    openTelemetryTracer.traceOperation("call.receive") {
                        call.receive<RegistrationRequest>()
                    }

                // Validate input
                if (request.username.isBlank()) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "Username is required"),
                    )
                    return@post
                }

                if (request.displayName.isBlank()) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "Display name is required"),
                    )
                    return@post
                }

                // Check for duplicate user
                val userAlreadyExists =
                    openTelemetryTracer.traceOperation("checkUserExists") {
                        credentialStorage.userExists(request.username)
                    }

                if (userAlreadyExists) {
                    logger.info("Registration attempt for existing user: ${request.username}")
                    call.respond(
                        HttpStatusCode.Conflict,
                        mapOf("error" to "Username is already registered"),
                    )
                    return@post
                }

                val requestId = UUID.randomUUID().toString()
                val userHandle =
                    ByteArray.fromBase64Url(
                        Base64.getUrlEncoder().withoutPadding()
                            .encodeToString(UUID.randomUUID().toString().toByteArray()),
                    )

                val user =
                    openTelemetryTracer.traceOperation("buildUserIdentity") {
                        UserIdentity.builder()
                            .name(request.username)
                            .displayName(request.displayName)
                            .id(userHandle)
                            .build()
                    }

                val startRegistrationOptions =
                    openTelemetryTracer.traceOperation("relyingParty.startRegistration") {
                        relyingParty.startRegistration(
                            StartRegistrationOptions.builder()
                                .user(user)
                                .build(),
                        )
                    }

                registrationStorage.storeRegistrationRequest(requestId, startRegistrationOptions)

                val credentialsJson =
                    openTelemetryTracer.traceOperation("toCredentialsCreateJson") {
                        startRegistrationOptions.toCredentialsCreateJson()
                    }
                val credentialsObject = openTelemetryTracer.readTree(credentialsJson)

                openTelemetryTracer.traceOperation("call.response") {
                    val registrationResponse =
                        RegistrationResponse(
                            requestId = requestId,
                            publicKeyCredentialCreationOptions = credentialsObject,
                        )
                    call.respond(registrationResponse)
                }
            } catch (e: Exception) {
                logger.error("Registration start failed", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    mapOf("error" to "Registration failed. Please try again."),
                )
            }
        }

        post("/register/complete") {
            try {
                val request = call.receive<RegistrationCompleteRequest>()

                val startRegistrationOptions =
                    registrationStorage.retrieveAndRemoveRegistrationRequest(request.requestId)
                if (startRegistrationOptions == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        mapOf("error" to "Invalid or expired request ID"),
                    )
                    return@post
                }

                val finishRegistrationOptions =
                    relyingParty.finishRegistration(
                        FinishRegistrationOptions.builder()
                            .request(startRegistrationOptions)
                            .response(
                                PublicKeyCredential.parseRegistrationResponseJson(
                                    request.credential,
                                ),
                            )
                            .build(),
                    )

                val userAccount =
                    UserAccount(
                        username = startRegistrationOptions.user.name,
                        displayName = startRegistrationOptions.user.displayName,
                        userHandle = startRegistrationOptions.user.id,
                    )

                val registration =
                    CredentialRegistration(
                        userAccount = userAccount,
                        credential =
                            RegisteredCredential.builder()
                                .credentialId(finishRegistrationOptions.keyId.id)
                                .userHandle(userAccount.userHandle)
                                .publicKeyCose(finishRegistrationOptions.publicKeyCose)
                                .signatureCount(finishRegistrationOptions.signatureCount)
                                .build(),
                    )

                // Double-check for race condition - user might have been created between start and complete
                if (credentialStorage.userExists(userAccount.username)) {
                    logger.warn("Race condition detected: User ${userAccount.username} was created during registration")
                    call.respond(
                        HttpStatusCode.Conflict,
                        mapOf("error" to "Username is already registered"),
                    )
                    return@post
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
    }
}
