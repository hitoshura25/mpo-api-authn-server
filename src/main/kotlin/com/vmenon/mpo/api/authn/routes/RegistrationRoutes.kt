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
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import java.security.SecureRandom
import java.util.UUID
import org.koin.ktor.ext.inject

fun Application.configureRegistrationRoutes() {
    routing {
        val registrationStorage: RegistrationRequestStorage by inject()
        val relyingParty: RelyingParty by inject()
        val credentialStorage: CredentialStorage by inject()
        val openTelemetryTracer: OpenTelemetryTracer by inject()

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
    }
}
