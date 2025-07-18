package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.utils.JacksonUtils
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
    fun testMetrics() = testApplication {
        application {
            module(testStorageModule)
        }

        val response = client.get("/metrics")
        assertEquals(HttpStatusCode.OK, response.status)
        assertNotNull(response.bodyAsText())
    }

    @Test
    fun testHealth() = testApplication {
        application {
            module(testStorageModule)
        }

        val response = client.get("/health")
        assertEquals(HttpStatusCode.OK, response.status)
        val responseBody = objectMapper.readTree(response.bodyAsText())
        assertEquals("healthy", responseBody.get("status").asText())
    }

    @Test
    fun testReady() = testApplication {
        application {
            module(testStorageModule)
        }

        val response = client.get("/ready")
        assertEquals(HttpStatusCode.OK, response.status)
        val responseBody = objectMapper.readTree(response.bodyAsText())
        assertEquals("ready", responseBody.get("status").asText())
    }

    @Test
    fun testLive() = testApplication {
        application {
            module(testStorageModule)
        }

        val response = client.get("/live")
        assertEquals(HttpStatusCode.OK, response.status)
        assertEquals("Alive", response.bodyAsText())
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
}
