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

        assertEquals(HttpStatusCode.BadRequest, response.status)
        assertTrue(response.bodyAsText().contains("Invalid or expired request ID"))
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

        assertEquals(HttpStatusCode.BadRequest, response.status)
        assertTrue(response.bodyAsText().contains("Invalid or expired request ID"))
    }

    @Test
    fun testOpenAPISpecification() = testApplication {
        application {
            module(testStorageModule)
        }

        val response = client.get("/openapi")
        assertEquals(HttpStatusCode.OK, response.status)
        assertTrue(
            response.contentType().toString().contains(ContentType.Text.Plain.toString()),
            "OpenAPI specification should not be empty"
        )

        val responseBody = response.bodyAsText()
        assertNotNull(responseBody)
        assertTrue(responseBody.isNotEmpty(), "OpenAPI specification should not be empty")
        assertTrue(responseBody.contains("openapi: 3.0.3"), "Should contain OpenAPI version")
        assertTrue(responseBody.contains("MPO WebAuthn Authentication Server API"), "Should contain API title")
        assertTrue(responseBody.contains("/register/start"), "Should contain registration endpoints")
        assertTrue(responseBody.contains("/authenticate/start"), "Should contain authentication endpoints")

        // Verify YAML structure and key components
        assertTrue(responseBody.contains("info:"), "Should contain info section")
        assertTrue(responseBody.contains("title:"), "Should contain title")
        assertTrue(responseBody.contains("description:"), "Should contain description")
        assertTrue(
            responseBody.contains("paths:") || responseBody.contains("WebAuthn"),
            "Should contain paths or WebAuthn references"
        )

        // Verify it's valid YAML format (basic check)
        assertTrue(responseBody.lines().any { it.trim().startsWith("openapi:") }, "Should start with openapi version")
    }

    @Test
    fun testSwaggerUI() = testApplication {
        application {
            module(testStorageModule)
        }

        val response = client.get("/swagger")
        assertEquals(HttpStatusCode.OK, response.status)

        val responseBody = response.bodyAsText()
        assertNotNull(responseBody)
        assertTrue(responseBody.isNotEmpty(), "Swagger UI should not be empty")
        assertTrue(responseBody.contains("Swagger UI"), "Should contain Swagger UI title")
        assertTrue(responseBody.contains("swagger-ui-bundle"), "Should contain Swagger UI bundle")
    }

    @Test
    fun testSwaggerUIWithTrailingSlash() = testApplication {
        application {
            module(testStorageModule)
        }

        val testClient = createClient { followRedirects = false }
        val response = testClient.get("/swagger/")
        assertEquals(HttpStatusCode.MovedPermanently, response.status)

        // Check that the Location header points to the correct redirect URL
        val locationHeader = response.headers["Location"]
        assertEquals("/swagger", locationHeader)
    }
}
