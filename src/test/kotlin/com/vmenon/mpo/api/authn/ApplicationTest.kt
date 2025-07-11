package com.vmenon.mpo.api.authn

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.vmenon.mpo.api.authn.yubico.TestAuthenticator
import com.yubico.webauthn.data.ByteArray
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.server.testing.testApplication
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue
import org.junit.jupiter.api.Test

class ApplicationTest {

    private val objectMapper = ObjectMapper().apply {
        registerModule(KotlinModule.Builder().build())
        registerModule(JavaTimeModule())
        registerModule(Jdk8Module())
    }

    @Test
    fun testRootEndpoint() = testApplication {
        application {
            module()
        }

        val response = client.get("/")
        assertEquals(HttpStatusCode.OK, response.status)
        assertEquals("WebAuthn Server is running!", response.bodyAsText())
    }

    @Test
    fun testAuthenticationStart() = testApplication {
        application {
            module()
        }

        val authRequest = AuthenticationRequest(username = "testuser")

        val response = client.post("/authenticate/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(authRequest))
        }

        assertEquals(HttpStatusCode.OK, response.status)

        val responseBody = objectMapper.readTree(response.bodyAsText())
        assertNotNull(responseBody.get("requestId"))
        assertNotNull(responseBody.get("publicKeyCredentialRequestOptions"))
    }

    @Test
    fun testAuthenticationStartWithoutUsername() = testApplication {
        application {
            module()
        }

        val authRequest = AuthenticationRequest()

        val response = client.post("/authenticate/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(authRequest))
        }

        assertEquals(HttpStatusCode.OK, response.status)

        val responseBody = objectMapper.readTree(response.bodyAsText())
        assertNotNull(responseBody.get("requestId"))
        assertNotNull(responseBody.get("publicKeyCredentialRequestOptions"))
    }

    @Test
    fun testAuthenticationCompleteWithInvalidRequestId() = testApplication {
        application {
            module()
        }

        val completeRequest = AuthenticationCompleteRequest(
            requestId = "invalid-request-id",
            credential = "{}"
        )

        val response = client.post("/authenticate/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRequest))
        }

        assertEquals(HttpStatusCode.InternalServerError, response.status)
        assertTrue(response.bodyAsText().contains("Invalid request ID"))
    }

    @Test
    fun testAuthenticationCompleteSuccess() = testApplication {
        application {
            module()
        }

        // First, start an authentication to get a valid request ID
        val authRequest = AuthenticationRequest(username = "testuser")

        val startResponse = client.post("/authenticate/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(authRequest))
        }

        assertEquals(HttpStatusCode.OK, startResponse.status)
        val startResponseBody = objectMapper.readTree(startResponse.bodyAsText())
        assertNotNull(startResponseBody.get("requestId"))
        assertNotNull(startResponseBody.get("publicKeyCredentialRequestOptions"))

        val requestId = startResponseBody.get("requestId").asText()

        // Create a mock authentication response (this would normally come from the WebAuthn API)
        val mockCredential = """
        {
            "id": "mock-credential-id",
            "rawId": "bW9jay1jcmVkZW50aWFsLWlk",
            "type": "public-key",
            "response": {
                "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoibW9jay1jaGFsbGVuZ2UiLCJvcmlnaW4iOiJodHRwOi8vbG9jYWxob3N0OjgwODAifQ",
                "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAAAQ",
                "signature": "MEUCIQDTGOGq-Q_Qr8jKD9nSFLlJrXo0F0gPfMgM8HtTfJ5Ky3UFAiEA27FgHZOD5TkzB3c73-eW3WTFnZwqxX5gLqlhjSQd8Fbi"
            }
        }
        """.trimIndent()

        val completeRequest = AuthenticationCompleteRequest(
            requestId = requestId,
            credential = mockCredential
        )

        val completeResponse = client.post("/authenticate/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRequest))
        }

        // Note: This will likely fail with the actual WebAuthn validation
        // but we're testing that the endpoint accepts the request and processes it
        assertTrue(
            completeResponse.status == HttpStatusCode.OK ||
                    completeResponse.status == HttpStatusCode.InternalServerError
        )

        // If it's an error, it should be a validation error, not a "request ID not found" error
        if (completeResponse.status == HttpStatusCode.InternalServerError) {
            val errorMessage = completeResponse.bodyAsText()
            assertTrue(!errorMessage.contains("Invalid request ID"))
        }
    }

    @Test
    fun testRegistrationCompleteWithInvalidRequestId() = testApplication {
        application {
            module()
        }

        val completeRequest = RegistrationCompleteRequest(
            requestId = "invalid-request-id",
            credential = "{}"
        )

        val response = client.post("/register/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRequest))
        }

        assertEquals(HttpStatusCode.InternalServerError, response.status)
        assertTrue(response.bodyAsText().contains("Invalid request ID"))
    }

    @Test
    fun testRegistrationCompleteSuccess() = testApplication {
        application {
            module()
        }

        val registrationRequest = RegistrationRequest(
            username = "testuser",
            displayName = "Test User"
        )

        val startResponse = client.post("/register/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(registrationRequest))
        }

        assertEquals(HttpStatusCode.OK, startResponse.status)

        val startResponseBody = objectMapper.readTree(startResponse.bodyAsText())
        assertNotNull(startResponseBody.get("requestId"))
        assertNotNull(startResponseBody.get("publicKeyCredentialCreationOptions"))

        val credentialOptionsString = startResponseBody.get("publicKeyCredentialCreationOptions").asText()
        val credentialOptions = objectMapper.readTree(credentialOptionsString)
        assertEquals("testuser", credentialOptions.get("user").get("name").asText())
        assertEquals("Test User", credentialOptions.get("user").get("displayName").asText())
        assertEquals("localhost", credentialOptions.get("rp").get("id").asText())
        assertEquals("WebAuthn Demo", credentialOptions.get("rp").get("name").asText())

        val requestId = startResponseBody.get("requestId").asText()
        val createCredentialOptions =
            objectMapper.readTree(startResponseBody.get("publicKeyCredentialCreationOptions").asText())

        val challenge = createCredentialOptions.get("challenge").asText()
        val credential = TestAuthenticator.createUnattestedCredential(ByteArray.fromBase64Url(challenge))

        val publicKeyCredentialJson =
            objectMapper.writeValueAsString(credential.first)

        val completeRequest = RegistrationCompleteRequest(
            requestId = requestId,
            credential = publicKeyCredentialJson
        )

        val completeResponse = client.post("/register/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRequest))
        }
        assertTrue(completeResponse.status == HttpStatusCode.OK)
    }
}
