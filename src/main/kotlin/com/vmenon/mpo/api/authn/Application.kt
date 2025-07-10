package com.vmenon.mpo.api.authn

import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.yubico.webauthn.AssertionRequest
import com.yubico.webauthn.FinishAssertionOptions
import com.yubico.webauthn.FinishRegistrationOptions
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.StartAssertionOptions
import com.yubico.webauthn.StartRegistrationOptions
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.PublicKeyCredential
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import com.yubico.webauthn.data.RelyingPartyIdentity
import com.yubico.webauthn.data.UserIdentity
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.serialization.jackson.jackson
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.application.install
import io.ktor.server.engine.embeddedServer
import io.ktor.server.netty.Netty
import io.ktor.server.plugins.contentnegotiation.ContentNegotiation
import io.ktor.server.plugins.cors.routing.CORS
import io.ktor.server.plugins.statuspages.StatusPages
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import java.security.SecureRandom
import java.util.*
import java.util.concurrent.ConcurrentHashMap

fun Application.module() {
    val credentialRepository = InMemoryCredentialRepository()
    val registrationRequestStorage = ConcurrentHashMap<String, PublicKeyCredentialCreationOptions>()
    val assertionRequestStorage = ConcurrentHashMap<String, AssertionRequest>()

    val relyingParty = RelyingParty.builder()
        .identity(
            RelyingPartyIdentity.builder()
                .id("localhost")
                .name("WebAuthn Demo")
                .build()
        )
        .credentialRepository(credentialRepository)
        .build()

    install(ContentNegotiation) {
        jackson {
            registerModule(KotlinModule.Builder().build())
            registerModule(JavaTimeModule())
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

    routing {
        get("/") {
            call.respondText("WebAuthn Server is running!")
        }

        post("/register/start") {
            val request = call.receive<RegistrationRequest>()
            val requestId = UUID.randomUUID().toString()

            val userHandle = ByteArray(64)
            SecureRandom().nextBytes(userHandle)

            val user = UserIdentity.builder()
                .name(request.username)
                .displayName(request.displayName)
                .id(ByteArray(userHandle))
                .build()

            val startRegistrationOptions = relyingParty.startRegistration(
                StartRegistrationOptions.builder()
                    .user(user)
                    .build()
            )

            registrationRequestStorage[requestId] = startRegistrationOptions

            val response = RegistrationResponse(
                requestId = requestId,
                publicKeyCredentialCreationOptions = startRegistrationOptions.toJson()
            )

            call.respond(response)
        }

        post("/register/complete") {
            val request = call.receive<RegistrationCompleteRequest>()
            val startRegistrationOptions = registrationRequestStorage.remove(request.requestId)
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

            credentialRepository.addRegistration(registration)

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

            assertionRequestStorage[requestId] = startAssertionOptions

            val response = AuthenticationResponse(
                requestId = requestId,
                publicKeyCredentialRequestOptions = startAssertionOptions.toJson()
            )

            call.respond(response)
        }

        post("/authenticate/complete") {
            val request = call.receive<AuthenticationCompleteRequest>()
            val startAssertionOptions = assertionRequestStorage.remove(request.requestId)
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

fun main() {
    embeddedServer(Netty, port = 8080) {
        module()
    }.start(wait = true)
}
