package com.vmenon.mpo.api.authn

import com.fasterxml.jackson.core.JsonParseException
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import com.vmenon.mpo.api.authn.utils.JacksonUtils
import com.vmenon.webauthn.testlib.WebAuthnTestAuthenticator
import com.yubico.webauthn.RegistrationResult
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.COSEAlgorithmIdentifier
import com.yubico.webauthn.data.PublicKeyCredential
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.server.routing.get
import io.ktor.server.testing.ApplicationTestBuilder
import io.ktor.server.testing.testApplication
import io.micrometer.prometheus.PrometheusMeterRegistry
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkStatic
import io.mockk.unmockkStatic
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.koin.core.context.stopKoin
import org.koin.dsl.module
import org.koin.test.KoinTest
import java.util.Optional
import java.util.UUID
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class ApplicationTest : KoinTest {
    private val objectMapper = JacksonUtils.objectMapper
    private val mockRelyingParty = mockk<RelyingParty>()
    private val mockPrometheusRegistry = mockk<PrometheusMeterRegistry>()
    private val mockRegistrationStorage = mockk<RegistrationRequestStorage>()
    private val mockAssertionStorage = mockk<AssertionRequestStorage>()
    private val mockCredentialStorage = mockk<CredentialStorage>()
    private val keyPair = WebAuthnTestAuthenticator.generateKeyPair()

    @BeforeEach
    fun setup() {
        // Ensure clean Koin state before each test
        stopKoin()
        every { mockCredentialStorage.close() } returns Unit
        every { mockAssertionStorage.close() } returns Unit
        every { mockRegistrationStorage.close() } returns Unit
    }

    @AfterEach
    fun teardown() {
        // Clean up after each test
        stopKoin()
    }

    @Test
    fun testRootEndpoint() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val response = client.get("/")
            assertEquals(HttpStatusCode.OK, response.status)
            assertEquals("WebAuthn Server is running!", response.bodyAsText())
        }

    @Test
    fun testMetrics() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val response = client.get("/metrics")
            assertEquals(HttpStatusCode.OK, response.status)
            assertNotNull(response.bodyAsText())
        }

    @Test
    fun testHealth() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val response = client.get("/health")
            assertEquals(HttpStatusCode.OK, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals("healthy", responseBody.get("status").asText())
        }

    @Test
    fun testReady() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val response = client.get("/ready")
            assertEquals(HttpStatusCode.OK, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals("ready", responseBody.get("status").asText())
        }

    @Test
    fun testLive() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val response = client.get("/live")
            assertEquals(HttpStatusCode.OK, response.status)
            assertEquals("Alive", response.bodyAsText())
        }

    @Test
    fun testStatusPageErrorHandler() =
        testApplication {
            val errorFun = {
                throw UnsupportedOperationException()
            }
            application {
                module(testStorageModule)
            }
            routing {
                this.get("/testStatusPage") {
                    errorFun()
                }
            }

            val response = client.get("/testStatusPage")
            assertEquals(HttpStatusCode.InternalServerError, response.status)
            assertEquals("Error occurred", response.bodyAsText())
        }

    @Test
    fun testAuthenticationStartWithoutUsername() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val authRequest = AuthenticationRequest()

            val response =
                client.post("/authenticate/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(authRequest))
                }

            assertEquals(HttpStatusCode.OK, response.status)

            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertNotNull(responseBody.get("requestId"))
            assertNotNull(responseBody.get("publicKeyCredentialRequestOptions"))
        }

    @Test
    fun testAuthenticationCompleteWithInvalidRequestId() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val completeRequest =
                AuthenticationCompleteRequest(
                    requestId = "invalid-request-id",
                    credential = "{}",
                )

            val response =
                client.post("/authenticate/complete") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(completeRequest))
                }

            assertEquals(HttpStatusCode.BadRequest, response.status)
            assertTrue(response.bodyAsText().contains("Invalid or expired request ID"))
        }

    @Test
    fun testRegistrationCompleteWithInvalidRequestId() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val completeRequest =
                RegistrationCompleteRequest(
                    requestId = "invalid-request-id",
                    credential = "{}",
                )

            val response =
                client.post("/register/complete") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(completeRequest))
                }

            assertEquals(HttpStatusCode.BadRequest, response.status)
            assertTrue(response.bodyAsText().contains("Invalid or expired request ID"))
        }

    @Test
    fun testOpenAPISpecification() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val response = client.get("/openapi")
            assertEquals(HttpStatusCode.OK, response.status)
            assertTrue(
                response.contentType().toString().contains(ContentType.Text.Plain.toString()),
                "OpenAPI specification should not be empty",
            )

            val responseBody = response.bodyAsText()
            assertNotNull(responseBody)
            assertTrue(responseBody.isNotEmpty(), "OpenAPI specification should not be empty")
            assertTrue(responseBody.contains("openapi: 3.0.3"), "Should contain OpenAPI version")
            assertTrue(
                responseBody.contains("MPO WebAuthn Authentication Server API"),
                "Should contain API title",
            )
            assertTrue(
                responseBody.contains("/register/start"),
                "Should contain registration endpoints",
            )
            assertTrue(
                responseBody.contains("/authenticate/start"),
                "Should contain authentication endpoints",
            )

            // Verify YAML structure and key components
            assertTrue(responseBody.contains("info:"), "Should contain info section")
            assertTrue(responseBody.contains("title:"), "Should contain title")
            assertTrue(responseBody.contains("description:"), "Should contain description")
            assertTrue(
                responseBody.contains("paths:") || responseBody.contains("WebAuthn"),
                "Should contain paths or WebAuthn references",
            )

            // Verify it's valid YAML format (basic check)
            assertTrue(
                responseBody.lines().any { it.trim().startsWith("openapi:") },
                "Should start with openapi version",
            )
        }

    @Test
    fun testSwaggerUI() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val response = client.get("/swagger")
            assertEquals(HttpStatusCode.OK, response.status)

            val responseBody = response.bodyAsText()
            assertNotNull(responseBody)
            assertTrue(responseBody.isNotEmpty(), "Swagger UI should not be empty")
            assertTrue(responseBody.contains("Swagger UI"), "Should contain Swagger UI title")
            assertTrue(
                responseBody.contains("swagger-ui-bundle"),
                "Should contain Swagger UI bundle",
            )
        }

    @Test
    fun testSwaggerUIWithTrailingSlash() =
        testApplication {
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

    @Test
    fun testMetricsEndpointExceptionHandling() =
        testApplication {
            // Create a mock PrometheusMeterRegistry that throws an exception
            // when scrape() is called
            every { mockPrometheusRegistry.scrape() } throws
                RuntimeException("Metrics collection failed")

            application {
                module(testStorageModule)
                // Override the PrometheusMeterRegistry with our mock after other modules are loaded
                getKoin().loadModules(
                    listOf(
                        module {
                            single<PrometheusMeterRegistry> { mockPrometheusRegistry }
                        },
                    ),
                )
            }

            val response = client.get("/metrics")
            assertEquals(HttpStatusCode.InternalServerError, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals("Metrics unavailable", responseBody.get("error").asText())
        }

    @Test
    fun testRegistrationStartWithBlankUsername() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val regRequest = RegistrationRequest(username = "", displayName = "Test User")

            val response =
                client.post("/register/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(regRequest))
                }

            assertEquals(HttpStatusCode.BadRequest, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals("Username is required", responseBody.get("error").asText())
        }

    @Test
    fun testRegistrationStartWithBlankDisplayName() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val regRequest = RegistrationRequest(username = "Test user", displayName = "")

            val response =
                client.post("/register/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(regRequest))
                }

            assertEquals(HttpStatusCode.BadRequest, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals("Display name is required", responseBody.get("error").asText())
        }

    @Test
    fun testRegistrationStartWithRelyingPartyFailure() =
        testApplication {
            // Mock RelyingParty to throw an exception
            every { mockRelyingParty.startRegistration(any()) } throws
                JsonParseException(null, "RelyingParty configuration error")

            application {
                module(testStorageModule)
                getKoin().loadModules(
                    listOf(
                        module {
                            single<RelyingParty> { mockRelyingParty }
                        },
                    ),
                )
            }

            val regRequest = RegistrationRequest(username = "testuser", displayName = "Test User")

            val response =
                client.post("/register/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(regRequest))
                }

            assertEquals(HttpStatusCode.InternalServerError, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals(
                "Registration failed. Please try again.",
                responseBody.get("error").asText(),
            )
        }

    @Test
    fun testRegistrationStartWithStorageFailure() =
        testApplication {
            // Mock RegistrationRequestStorage to throw an exception
            coEvery {
                mockRegistrationStorage.storeRegistrationRequest(
                    any(),
                    any(),
                    any(),
                )
            } throws redis.clients.jedis.exceptions.JedisException("Storage system down")

            application {
                module(testStorageModule)
                getKoin().loadModules(
                    listOf(
                        module {
                            single<RegistrationRequestStorage> { mockRegistrationStorage }
                        },
                    ),
                )
            }

            val regRequest = RegistrationRequest(username = "testuser", displayName = "Test User")

            val response =
                client.post("/register/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(regRequest))
                }

            assertEquals(HttpStatusCode.InternalServerError, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals(
                "Registration failed. Please try again.",
                responseBody.get("error").asText(),
            )
        }

    @Test
    fun testRegistrationStartWithUserThatAlreadyExists() =
        testApplication {
            every { mockCredentialStorage.userExists("testuser") } returns true

            application {
                module(testStorageModule)
                getKoin().loadModules(
                    listOf(
                        module {
                            single<CredentialStorage> { mockCredentialStorage }
                        },
                    ),
                )
            }

            val regRequest = RegistrationRequest(username = "testuser", displayName = "Test User")

            val response =
                client.post("/register/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(regRequest))
                }

            assertEquals(HttpStatusCode.Conflict, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals("Username is already registered", responseBody.get("error").asText())
        }

    @Test
    fun testRegistrationCompleteWithUserThatAlreadyExists() =
        testApplication {
            val testChallenge = ByteArray.fromBase64Url("test-challenge").bytes
            val credential =
                WebAuthnTestAuthenticator.createRegistrationCredential(
                    testChallenge,
                    keyPair,
                )

            setupMocksForUserExistsScenario()
            setupApplicationWithMocks()

            val response = client.performRegistrationCompleteRequest(credential)

            verifyConflictResponse(response)
        }

    private fun setupMocksForUserExistsScenario() {
        every { mockRelyingParty.finishRegistration(any()) }.returns(
            createMockRegistrationResult(),
        )
        every { mockCredentialStorage.userExists("testuser") } returns true
        coEvery {
            mockRegistrationStorage.retrieveAndRemoveRegistrationRequest(any())
        } returns createMockPublicKeyCredentialCreationOptions()
    }

    private fun createMockRegistrationResult() =
        mockk<RegistrationResult> {
            every { keyId } returns
                mockk {
                    every { id } returns ByteArray.fromBase64Url(UUID.randomUUID().toString())
                }
            every { publicKeyCose } returns ByteArray.fromBase64Url(UUID.randomUUID().toString())
            every { signatureCount } returns 0
        }

    private fun createMockPublicKeyCredentialCreationOptions() =
        mockk<PublicKeyCredentialCreationOptions> {
            every { challenge } returns ByteArray.fromBase64Url("test-challenge")
            every { authenticatorSelection } returns
                Optional.of(
                    mockk {
                        every { userVerification } returns Optional.of(mockk())
                    },
                )
            every { pubKeyCredParams } returns
                listOf(
                    mockk {
                        every { alg } returns COSEAlgorithmIdentifier.ES256
                    },
                )
            every { user } returns
                mockk {
                    every { name } returns "testuser"
                    every { displayName } returns "teruser displayName"
                    every { id } returns ByteArray.fromBase64Url(UUID.randomUUID().toString())
                }
        }

    private fun ApplicationTestBuilder.setupApplicationWithMocks() {
        application {
            module(testStorageModule)
            getKoin().loadModules(
                listOf(
                    module {
                        single<CredentialStorage> { mockCredentialStorage }
                        single<RegistrationRequestStorage> { mockRegistrationStorage }
                        single<RelyingParty> { mockRelyingParty }
                    },
                ),
            )
        }
    }

    private suspend fun HttpClient.performRegistrationCompleteRequest(
        credential: PublicKeyCredential<*, *>,
    ) = post("/register/complete") {
        contentType(ContentType.Application.Json)
        setBody(
            objectMapper.writeValueAsString(
                RegistrationCompleteRequest(
                    requestId = "testRequest",
                    credential = objectMapper.writeValueAsString(credential),
                ),
            ),
        )
    }

    private suspend fun verifyConflictResponse(response: HttpResponse) {
        assertEquals(HttpStatusCode.Conflict, response.status)
        val responseBody = objectMapper.readTree(response.bodyAsText())
        assertEquals("Username is already registered", responseBody.get("error").asText())
    }

    @Test
    fun testAuthenticationStartWithEmptyUsername() =
        testApplication {
            application {
                module(testStorageModule)
            }

            val authRequest = AuthenticationRequest(username = "")

            val response =
                client.post("/authenticate/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(authRequest))
                }

            assertEquals(HttpStatusCode.BadRequest, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals("Username cannot be empty if provided", responseBody.get("error").asText())
        }

    @Test
    fun testAuthenticationCompleteWithRelyingPartyFailure() =
        testApplication {
            // Mock RelyingParty to throw an exception
            every { mockRelyingParty.finishAssertion(any()) } throws
                RuntimeException("RelyingParty service unavailable")

            application {
                module(testStorageModule)
                getKoin().loadModules(
                    listOf(
                        module {
                            single<RelyingParty> { mockRelyingParty }
                        },
                    ),
                )
            }

            val authRequest = AuthenticationRequest()

            val response =
                client.post("/authenticate/complete") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(authRequest))
                }

            assertEquals(HttpStatusCode.InternalServerError, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals(
                "Authentication failed. Please try again.",
                responseBody.get("error").asText(),
            )
        }

    @Test
    fun testAuthenticationStartWithStorageFailure() =
        testApplication {
            // Mock AssertionRequestStorage to throw an exception
            coEvery {
                mockAssertionStorage.storeAssertionRequest(
                    any(),
                    any(),
                    any(),
                )
            } throws redis.clients.jedis.exceptions.JedisException("Database connection failed")

            application {
                module(testStorageModule)
                getKoin().loadModules(
                    listOf(
                        module {
                            single<AssertionRequestStorage> { mockAssertionStorage }
                        },
                    ),
                )
            }

            val authRequest = AuthenticationRequest()

            val response =
                client.post("/authenticate/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(authRequest))
                }

            assertEquals(HttpStatusCode.InternalServerError, response.status)
            val responseBody = objectMapper.readTree(response.bodyAsText())
            assertEquals(
                "Authentication failed. Please try again.",
                responseBody.get("error").asText(),
            )
        }

    @Test
    fun testAuthenticationCompleteWithFailedAssertion() =
        testApplication {
            // Mock RelyingParty for startAssertion (needed for the start step)
            every { mockRelyingParty.startAssertion(any()) } returns
                mockk {
                    every { toCredentialsGetJson() } returns "{\"publicKey\": {}}"
                }

            // Mock RelyingParty to return a FinishAssertionResult where isSuccess = false
            every { mockRelyingParty.finishAssertion(any()) } returns
                mockk {
                    every { isSuccess } returns false
                }

            // Mock the static method PublicKeyCredential.parseAssertionResponseJson
            mockkStatic(PublicKeyCredential::class)
            every { PublicKeyCredential.parseAssertionResponseJson(any<String>()) } returns mockk()

            try {
                application {
                    module(testStorageModule)
                    getKoin().loadModules(
                        listOf(
                            module {
                                single<RelyingParty> { mockRelyingParty }
                            },
                        ),
                    )
                }

                // First start an authentication to get a valid request ID
                val authRequest = AuthenticationRequest()
                val startResponse =
                    client.post("/authenticate/start") {
                        contentType(ContentType.Application.Json)
                        setBody(objectMapper.writeValueAsString(authRequest))
                    }
                assertEquals(HttpStatusCode.OK, startResponse.status)
                val startBody = objectMapper.readTree(startResponse.bodyAsText())
                val requestId = startBody.get("requestId").asText()

                // Now try to complete with a valid request ID, but the assertion will fail
                val completeRequest =
                    AuthenticationCompleteRequest(
                        requestId = requestId,
                        credential = "{\"type\": \"public-key\", \"id\": \"test-credential-id\"}",
                    )

                val response =
                    client.post("/authenticate/complete") {
                        contentType(ContentType.Application.Json)
                        setBody(objectMapper.writeValueAsString(completeRequest))
                    }

                assertEquals(HttpStatusCode.Unauthorized, response.status)
                val responseBody = objectMapper.readTree(response.bodyAsText())
                assertEquals("Authentication failed", responseBody.get("error").asText())
            } finally {
                unmockkStatic(PublicKeyCredential::class)
            }
        }
}
