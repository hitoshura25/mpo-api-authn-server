package com.vmenon.webauthn.testservice.routes

import com.vmenon.webauthn.testservice.models.*
import com.vmenon.webauthn.testlib.WebAuthnTestAuthenticator
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.yubico.webauthn.data.ByteArray
import io.ktor.http.HttpStatusCode
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import org.slf4j.LoggerFactory
import java.security.KeyPair
import java.util.*

/**
 * Routes for generating WebAuthn test credentials
 */
fun Application.configureTestRoutes() {
    val logger = LoggerFactory.getLogger("TestRoutes")
    val objectMapper = ObjectMapper()
        .registerKotlinModule()
        .registerModule(Jdk8Module())
    
    // In-memory storage for test key pairs (for linking registration and authentication)
    val testKeyPairs = mutableMapOf<String, KeyPair>()
    
    routing {
        
        // Health check endpoint
        get("/health") {
            call.respond(HealthResponse(
                status = "healthy",
                timestamp = System.currentTimeMillis()
            ))
        }
        
        // Generate registration credential
        post("/test/generate-registration-credential") {
            try {
                val request = call.receive<TestRegistrationRequest>()
                logger.info("Generating registration credential for challenge: ${request.challenge}")
                
                // Generate keypair for this test
                val keyPair = WebAuthnTestAuthenticator.generateKeyPair()
                val keyPairId = UUID.randomUUID().toString()
                testKeyPairs[keyPairId] = keyPair
                
                // Create test credential using WebAuthnTestAuthenticator
                val credential = WebAuthnTestAuthenticator.createRegistrationCredential(
                    challenge = ByteArray.fromBase64Url(request.challenge).bytes,
                    keyPair = keyPair,
                    rpId = request.rpId,
                    origin = request.origin
                )
                
                // Convert to JSON string
                val credentialJson = objectMapper.writeValueAsString(credential)
                
                // Extract credential ID for future authentication
                val credentialId = credential.id.base64Url
                
                call.respond(TestCredentialResponse(
                    credential = credentialJson,
                    keyPairId = keyPairId,
                    credentialId = credentialId
                ))
                
                logger.info("Successfully generated registration credential with keyPairId: $keyPairId")
                
            } catch (e: Exception) {
                logger.error("Failed to generate registration credential", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    ErrorResponse(
                        error = "Failed to generate registration credential", 
                        details = e.message
                    )
                )
            }
        }
        
        // Generate authentication credential
        post("/test/generate-authentication-credential") {
            try {
                val request = call.receive<TestAuthenticationRequest>()
                logger.info("Generating authentication credential for keyPairId: ${request.keyPairId}")
                
                // Retrieve the keypair for this test
                val keyPair = testKeyPairs[request.keyPairId]
                if (keyPair == null) {
                    call.respond(
                        HttpStatusCode.BadRequest,
                        ErrorResponse(
                            error = "Invalid keyPairId", 
                            details = "KeyPair ${request.keyPairId} not found"
                        )
                    )
                    return@post
                }
                
                // Create test authentication credential
                val credential = WebAuthnTestAuthenticator.createAuthenticationCredential(
                    challenge = ByteArray.fromBase64Url(request.challenge).bytes,
                    credentialId = ByteArray.fromBase64Url(request.credentialId).bytes,
                    keyPair = keyPair,
                    rpId = request.rpId,
                    origin = request.origin
                )
                
                // Convert to JSON string
                val credentialJson = objectMapper.writeValueAsString(credential)
                
                call.respond(TestCredentialResponse(
                    credential = credentialJson,
                    keyPairId = request.keyPairId,
                    credentialId = request.credentialId
                ))
                
                logger.info("Successfully generated authentication credential")
                
            } catch (e: Exception) {
                logger.error("Failed to generate authentication credential", e)
                call.respond(
                    HttpStatusCode.InternalServerError,
                    ErrorResponse(
                        error = "Failed to generate authentication credential",
                        details = e.message
                    )
                )
            }
        }
        
        // Clear test data (useful for test cleanup)
        post("/test/clear") {
            val clearedCount = testKeyPairs.size
            testKeyPairs.clear()
            logger.info("Cleared $clearedCount test key pairs")
            call.respond(mapOf(
                "message" to "Test data cleared",
                "clearedKeyPairs" to clearedCount
            ))
        }
        
        // List active test sessions (for debugging)
        get("/test/sessions") {
            call.respond(mapOf(
                "activeKeyPairs" to testKeyPairs.keys.toList(),
                "count" to testKeyPairs.size
            ))
        }
    }
}