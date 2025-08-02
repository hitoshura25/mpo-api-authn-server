package com.vmenon.webauthn.testservice.routes

import com.fasterxml.jackson.core.JsonProcessingException
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.vmenon.webauthn.testlib.WebAuthnTestAuthenticator
import com.vmenon.webauthn.testservice.models.ErrorResponse
import com.vmenon.webauthn.testservice.models.HealthResponse
import com.vmenon.webauthn.testservice.models.TestAuthenticationRequest
import com.vmenon.webauthn.testservice.models.TestCredentialResponse
import com.vmenon.webauthn.testservice.models.TestRegistrationRequest
import com.yubico.webauthn.data.ByteArray
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.Application
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.call
import io.ktor.server.request.receive
import io.ktor.server.response.respond
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import java.security.KeyPair
import java.util.UUID

/**
 * Routes for generating WebAuthn test credentials
 */
fun Application.configureTestRoutes() {
    val logger = LoggerFactory.getLogger("TestRoutes")
    val objectMapper = createObjectMapper()
    val testKeyPairs = mutableMapOf<String, KeyPair>()

    routing {
        get("/health") {
            call.handleHealthCheck()
        }

        post("/test/generate-registration-credential") {
            call.handleRegistrationCredential(testKeyPairs, objectMapper, logger)
        }

        post("/test/generate-authentication-credential") {
            call.handleAuthenticationCredential(testKeyPairs, objectMapper, logger)
        }

        post("/test/clear") {
            call.handleClearTestData(testKeyPairs, logger)
        }

        get("/test/sessions") {
            call.handleListSessions(testKeyPairs)
        }
    }
}

private fun createObjectMapper(): ObjectMapper =
    ObjectMapper()
        .registerKotlinModule()
        .registerModule(Jdk8Module())

private suspend fun ApplicationCall.handleHealthCheck() {
    respond(
        HealthResponse(
            status = "healthy",
            timestamp = System.currentTimeMillis(),
        ),
    )
}

private suspend fun ApplicationCall.handleRegistrationCredential(
    testKeyPairs: MutableMap<String, KeyPair>,
    objectMapper: ObjectMapper,
    logger: Logger,
) {
    runCatching {
        val request = receive<TestRegistrationRequest>()
        logger.info("Generating registration credential for challenge: ${request.challenge}")

        val keyPair = WebAuthnTestAuthenticator.generateKeyPair()
        val keyPairId = UUID.randomUUID().toString()
        testKeyPairs[keyPairId] = keyPair

        val credential = WebAuthnTestAuthenticator.createRegistrationCredential(
            challenge = ByteArray.fromBase64Url(request.challenge).bytes,
            keyPair = keyPair,
            rpId = request.rpId,
            origin = request.origin,
        )

        val credentialJson = objectMapper.writeValueAsString(credential)
        val credentialId = credential.id.base64Url

        respond(
            TestCredentialResponse(
                credential = credentialJson,
                keyPairId = keyPairId,
                credentialId = credentialId,
            ),
        )

        logger.info("Successfully generated registration credential with keyPairId: $keyPairId")
    }.onFailure { exception ->
        logger.error("Failed to generate registration credential", exception)
        respondWithError("Failed to generate registration credential", exception.message)
    }
}

private suspend fun ApplicationCall.handleAuthenticationCredential(
    testKeyPairs: MutableMap<String, KeyPair>,
    objectMapper: ObjectMapper,
    logger: Logger,
) {
    runCatching {
        val request = receive<TestAuthenticationRequest>()
        logger.info("Generating authentication credential for keyPairId: ${request.keyPairId}")

        val keyPair = testKeyPairs[request.keyPairId]
        if (keyPair == null) {
            respond(
                HttpStatusCode.BadRequest,
                ErrorResponse(
                    error = "Invalid keyPairId",
                    details = "KeyPair ${request.keyPairId} not found",
                ),
            )
            return
        }

        val credential = WebAuthnTestAuthenticator.createAuthenticationCredential(
            challenge = ByteArray.fromBase64Url(request.challenge).bytes,
            credentialId = ByteArray.fromBase64Url(request.credentialId).bytes,
            keyPair = keyPair,
            rpId = request.rpId,
            origin = request.origin,
        )

        val credentialJson = objectMapper.writeValueAsString(credential)

        respond(
            TestCredentialResponse(
                credential = credentialJson,
                keyPairId = request.keyPairId,
                credentialId = request.credentialId,
            ),
        )

        logger.info("Successfully generated authentication credential")
    }.onFailure { exception ->
        logger.error("Failed to generate authentication credential", exception)
        respondWithError("Failed to generate authentication credential", exception.message)
    }
}

private suspend fun ApplicationCall.handleClearTestData(
    testKeyPairs: MutableMap<String, KeyPair>,
    logger: Logger,
) {
    val clearedCount = testKeyPairs.size
    testKeyPairs.clear()
    logger.info("Cleared $clearedCount test key pairs")
    respond(
        mapOf(
            "message" to "Test data cleared",
            "clearedKeyPairs" to clearedCount,
        ),
    )
}

private suspend fun ApplicationCall.handleListSessions(testKeyPairs: Map<String, KeyPair>) {
    respond(
        mapOf(
            "activeKeyPairs" to testKeyPairs.keys.toList(),
            "count" to testKeyPairs.size,
        ),
    )
}

private suspend fun ApplicationCall.respondWithError(error: String, details: String?) {
    respond(
        HttpStatusCode.InternalServerError,
        ErrorResponse(
            error = error,
            details = details,
        ),
    )
}
