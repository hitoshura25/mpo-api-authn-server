package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.test_utils.yubico.TestAuthenticator
import com.vmenon.mpo.api.authn.test_utils.yubico.TestAuthenticator.Defaults
import com.vmenon.mpo.api.authn.test_utils.yubico.TestAuthenticator.generateKeypair
import com.vmenon.mpo.api.authn.utils.JacksonUtils
import com.yubico.webauthn.data.ByteArray
import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.server.testing.testApplication
import java.security.KeyPair
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.koin.core.context.stopKoin
import org.koin.test.KoinTest

class ApplicationTest : KoinTest {
    private val objectMapper = JacksonUtils.objectMapper

    @BeforeEach
    fun setup() {
        // Ensure clean Koin state before each test
        stopKoin()
    }

    @AfterEach
    fun teardown() {
        // Clean up after each test
        stopKoin()
    }

    @Test
    fun testRootEndpoint() = testApplication {
        application {
            module(testStorageModule)
        }

        val response = client.get("/")
        assertEquals(HttpStatusCode.OK, response.status)
        assertEquals("WebAuthn Server is running!", response.bodyAsText())
    }

    @Test
    fun testAuthenticationStart() = testApplication {
        application {
            module(testStorageModule)
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
            module(testStorageModule)
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
            module(testStorageModule)
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
    fun testRegistrationCompleteWithInvalidRequestId() = testApplication {
        application {
            module(testStorageModule)
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
    fun testRegisterAndAuthenticationSuccess() = testApplication {
        application {
            module(testStorageModule)
        }

        val username = "testuser"
        val displayName = "Test User"
        val keyPair = generateKeypair(algorithm = Defaults.keyAlgorithm)

        registerUser(client, username, displayName, keyPair)
        authenticateUser(client, username, keyPair)
    }

    private suspend fun registerUser(client: HttpClient, username: String, displayName: String, keyPair: KeyPair) {
        val registrationRequest = RegistrationRequest(
            username = username,
            displayName = displayName
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
        val publicKey = credentialOptions.get("publicKey")
        assertEquals(username, publicKey.get("user").get("name").asText())
        assertEquals(displayName, publicKey.get("user").get("displayName").asText())
        assertEquals("localhost", publicKey.get("rp").get("id").asText())
        assertEquals("WebAuthn Demo", publicKey.get("rp").get("name").asText())

        val requestId = startResponseBody.get("requestId").asText()
        val createCredentialOptions =
            objectMapper.readTree(startResponseBody.get("publicKeyCredentialCreationOptions").asText())

        val challenge = createCredentialOptions.get("publicKey").get("challenge").asText()
        val credential = TestAuthenticator.createUnattestedCredentialForRegistration(
            ByteArray.fromBase64Url(challenge),
            keyPair,
        )

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

    private suspend fun authenticateUser(client: HttpClient, username: String, keyPair: KeyPair) {
        val authRequest = AuthenticationRequest(username)

        val startResponse = client.post("/authenticate/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(authRequest))
        }

        assertEquals(HttpStatusCode.OK, startResponse.status)
        val startResponseBody = objectMapper.readTree(startResponse.bodyAsText())
        assertNotNull(startResponseBody.get("requestId"))
        assertNotNull(startResponseBody.get("publicKeyCredentialRequestOptions"))

        val requestId = startResponseBody.get("requestId").asText()
        val requestCredentialOptions =
            objectMapper.readTree(startResponseBody.get("publicKeyCredentialRequestOptions").asText())
        val publicKey = requestCredentialOptions.get("publicKey")
        val challenge = publicKey.get("challenge").asText()
        val allowCredentials = publicKey.get("allowCredentials").first()
        val credential =
            TestAuthenticator.createUnattestedCredentialForAuthentication(
                ByteArray.fromBase64Url(challenge),
                ByteArray.fromBase64Url(allowCredentials.get("id").asText()),
                keyPair,
            )

        val publicKeyCredentialJson =
            objectMapper.writeValueAsString(credential)

        val completeRequest = AuthenticationCompleteRequest(
            requestId = requestId,
            credential = publicKeyCredentialJson
        )

        val completeResponse = client.post("/authenticate/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRequest))
        }

        assertTrue(completeResponse.status == HttpStatusCode.OK)
    }
}
