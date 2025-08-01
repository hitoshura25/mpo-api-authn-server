package com.vmenon.webauthn.testservice.routes

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.vmenon.webauthn.testservice.models.ErrorResponse
import com.vmenon.webauthn.testservice.models.HealthResponse
import com.vmenon.webauthn.testservice.models.TestAuthenticationRequest
import com.vmenon.webauthn.testservice.models.TestCredentialResponse
import com.vmenon.webauthn.testservice.models.TestRegistrationRequest
import com.yubico.webauthn.data.ByteArray
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.serialization.jackson.jackson
import io.ktor.server.application.install
import io.ktor.server.plugins.contentnegotiation.ContentNegotiation
import io.ktor.server.testing.ApplicationTestBuilder
import io.ktor.server.testing.testApplication
import java.util.UUID
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class TestRoutesTest {
    private val objectMapper = ObjectMapper().registerKotlinModule()

    private fun createTestApp(block: suspend ApplicationTestBuilder.() -> Unit) =
        testApplication {
            application {
                install(ContentNegotiation) {
                    jackson()
                }
                configureTestRoutes()
            }
            block()
        }

    @Test
    fun `health endpoint returns healthy status`() =
        createTestApp {
            val response = client.get("/health")
            assertEquals(HttpStatusCode.OK, response.status)

            val healthResponse: HealthResponse = objectMapper.readValue(response.bodyAsText())
            assertEquals("healthy", healthResponse.status)
            assertEquals("webauthn-test-service", healthResponse.service)
            assertTrue(healthResponse.timestamp > 0)
        }

    @Test
    fun `generate registration credential returns valid response`() =
        createTestApp {
            val challenge = ByteArray.fromBase64Url("dGVzdC1jaGFsbGVuZ2U").base64Url
            val requestBody =
                TestRegistrationRequest(
                    challenge = challenge,
                    rpId = "example.com",
                    origin = "https://example.com",
                    username = "testuser",
                    displayName = "Test User",
                )

            val response =
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(requestBody))
                }

            assertEquals(HttpStatusCode.OK, response.status)

            val credentialResponse: TestCredentialResponse = objectMapper.readValue(response.bodyAsText())
            assertNotNull(credentialResponse.credential)
            assertNotNull(credentialResponse.keyPairId)
            assertNotNull(credentialResponse.credentialId)

            // Verify the credential JSON is valid
            try {
                objectMapper.readTree(credentialResponse.credential)
            } catch (e: Exception) {
                throw AssertionError("Credential JSON should be valid", e)
            }

            // Verify keyPairId is a valid UUID
            try {
                UUID.fromString(credentialResponse.keyPairId)
            } catch (e: Exception) {
                throw AssertionError("KeyPairId should be a valid UUID", e)
            }
        }

    @Test
    fun `generate registration credential with invalid challenge returns error`() =
        createTestApp {
            val requestBody =
                TestRegistrationRequest(
                    challenge = "invalid-base64-challenge!@#$%",
                )

            val response =
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(requestBody))
                }

            assertEquals(HttpStatusCode.InternalServerError, response.status)

            val errorResponse: ErrorResponse = objectMapper.readValue(response.bodyAsText())
            assertEquals("Failed to generate registration credential", errorResponse.error)
            assertNotNull(errorResponse.details)
        }

    @Test
    fun `generate authentication credential with valid keyPairId returns success`() =
        createTestApp {
            // First, generate a registration credential to get a keyPairId
            val challenge = ByteArray.fromBase64Url("dGVzdC1jaGFsbGVuZ2U").base64Url
            val registrationRequest = TestRegistrationRequest(challenge = challenge)

            val registrationResponse =
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(registrationRequest))
                }

            val registrationResult: TestCredentialResponse = objectMapper.readValue(registrationResponse.bodyAsText())

            // Now generate authentication credential
            val authChallenge = ByteArray.fromBase64Url("YXV0aC1jaGFsbGVuZ2U").base64Url
            val authRequest =
                TestAuthenticationRequest(
                    challenge = authChallenge,
                    credentialId = registrationResult.credentialId!!,
                    keyPairId = registrationResult.keyPairId,
                )

            val authResponse =
                client.post("/test/generate-authentication-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(authRequest))
                }

            assertEquals(HttpStatusCode.OK, authResponse.status)

            val authResult: TestCredentialResponse = objectMapper.readValue(authResponse.bodyAsText())
            assertNotNull(authResult.credential)
            assertEquals(registrationResult.keyPairId, authResult.keyPairId)
            assertEquals(registrationResult.credentialId, authResult.credentialId)

            // Verify the authentication credential JSON is valid
            try {
                objectMapper.readTree(authResult.credential)
            } catch (e: Exception) {
                throw AssertionError("Authentication credential JSON should be valid", e)
            }
        }

    @Test
    fun `generate authentication credential with invalid keyPairId returns error`() =
        createTestApp {
            val challenge = ByteArray.fromBase64Url("dGVzdC1jaGFsbGVuZ2U").base64Url
            val requestBody =
                TestAuthenticationRequest(
                    challenge = challenge,
                    credentialId = "test-credential-id",
                    keyPairId = "invalid-keypair-id",
                )

            val response =
                client.post("/test/generate-authentication-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(requestBody))
                }

            assertEquals(HttpStatusCode.BadRequest, response.status)

            val errorResponse: ErrorResponse = objectMapper.readValue(response.bodyAsText())
            assertEquals("Invalid keyPairId", errorResponse.error)
            assertTrue(errorResponse.details!!.contains("invalid-keypair-id"))
        }

    @Test
    fun `clear test data removes all key pairs`() =
        createTestApp {
            // Generate some test data first
            val challenge = ByteArray.fromBase64Url("dGVzdC1jaGFsbGVuZ2U").base64Url
            val requestBody = TestRegistrationRequest(challenge = challenge)

            // Create multiple registrations
            repeat(3) {
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(requestBody))
                }
            }

            // Clear test data
            val clearResponse = client.post("/test/clear")
            assertEquals(HttpStatusCode.OK, clearResponse.status)

            val clearResult: Map<String, Any> = objectMapper.readValue(clearResponse.bodyAsText())
            assertEquals("Test data cleared", clearResult["message"])
            assertEquals(3, clearResult["clearedKeyPairs"])

            // Verify sessions are empty
            val sessionsResponse = client.get("/test/sessions")
            val sessionsResult: Map<String, Any> = objectMapper.readValue(sessionsResponse.bodyAsText())
            assertEquals(0, sessionsResult["count"])
            assertTrue((sessionsResult["activeKeyPairs"] as List<*>).isEmpty())
        }

    @Test
    fun `sessions endpoint returns active key pairs`() =
        createTestApp {
            // Initially should be empty
            val initialResponse = client.get("/test/sessions")
            val initialResult: Map<String, Any> = objectMapper.readValue(initialResponse.bodyAsText())
            assertEquals(0, initialResult["count"])

            // Generate some test credentials
            val challenge = ByteArray.fromBase64Url("dGVzdC1jaGFsbGVuZ2U").base64Url
            val requestBody = TestRegistrationRequest(challenge = challenge)

            val registrationResponse =
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(requestBody))
                }

            val registrationResult: TestCredentialResponse = objectMapper.readValue(registrationResponse.bodyAsText())

            // Check sessions again
            val sessionsResponse = client.get("/test/sessions")
            val sessionsResult: Map<String, Any> = objectMapper.readValue(sessionsResponse.bodyAsText())
            assertEquals(1, sessionsResult["count"])

            val activeKeyPairs = sessionsResult["activeKeyPairs"] as List<*>
            assertTrue(activeKeyPairs.contains(registrationResult.keyPairId))
        }

    @Test
    fun `malformed JSON request returns appropriate error`() =
        createTestApp {
            val response =
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody("{ invalid json }")
                }

            // Should return bad request or internal server error
            assertTrue(response.status.value >= 400)
        }

    @Test
    fun `missing required fields in request returns error`() =
        createTestApp {
            val response =
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody("{}") // Empty JSON object
                }

            // Should return bad request or internal server error due to missing challenge
            assertTrue(response.status.value >= 400)
        }

    @Test
    fun `authentication credential with invalid challenge format returns error`() =
        createTestApp {
            // First generate a valid registration
            val validChallenge = ByteArray.fromBase64Url("dGVzdC1jaGFsbGVuZ2U").base64Url
            val registrationRequest = TestRegistrationRequest(challenge = validChallenge)

            val registrationResponse =
                client.post("/test/generate-registration-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(registrationRequest))
                }

            val registrationResult: TestCredentialResponse = objectMapper.readValue(registrationResponse.bodyAsText())

            // Now try authentication with invalid challenge
            val authRequest =
                TestAuthenticationRequest(
                    challenge = "invalid-challenge-format!@#",
                    credentialId = registrationResult.credentialId!!,
                    keyPairId = registrationResult.keyPairId,
                )

            val authResponse =
                client.post("/test/generate-authentication-credential") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(authRequest))
                }

            assertEquals(HttpStatusCode.InternalServerError, authResponse.status)

            val errorResponse: ErrorResponse = objectMapper.readValue(authResponse.bodyAsText())
            assertEquals("Failed to generate authentication credential", errorResponse.error)
        }
}
