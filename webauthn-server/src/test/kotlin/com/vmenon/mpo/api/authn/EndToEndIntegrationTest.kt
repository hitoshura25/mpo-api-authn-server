package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.di.storageModule
import com.vmenon.mpo.api.authn.testutils.BaseIntegrationTest
import com.vmenon.mpo.api.authn.testutils.WebAuthnTestHelpers
import com.vmenon.mpo.api.authn.utils.JacksonUtils
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.server.testing.testApplication
import org.junit.jupiter.api.Test
import org.koin.core.context.stopKoin
import java.util.UUID
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * End-to-end integration tests using real Redis and PostgreSQL instances via Testcontainers
 * This tests the complete WebAuthn flow with actual database persistence
 */
class EndToEndIntegrationTest : BaseIntegrationTest() {
    private val objectMapper = JacksonUtils.objectMapper

    @Test
    fun `test complete WebAuthn flow with real databases`() =
        testApplication {
            application {
                module(storageModule)
            }

            val username = "integration_test_user"
            val displayName = "Integration Test User"
            val keyPair = WebAuthnTestHelpers.generateTestKeypair()

            // Test server is running
            val healthResponse = client.get("/")
            assertEquals(HttpStatusCode.OK, healthResponse.status)
            assertEquals("WebAuthn Server is running!", healthResponse.bodyAsText())

            // Step 1: Start registration
            val startRegResponse = WebAuthnTestHelpers.startRegistration(client, username, displayName)
            assertEquals(HttpStatusCode.OK, startRegResponse.status)

            val startRegBody = objectMapper.readTree(startRegResponse.bodyAsText())
            assertNotNull(startRegBody.get("requestId"))
            assertNotNull(startRegBody.get("publicKeyCredentialCreationOptions"))

            val credentialOptions = startRegBody.get("publicKeyCredentialCreationOptions")

            // Verify registration options
            val publicKey = credentialOptions.get("publicKey")
            assertEquals(username, publicKey.get("user").get("name").asText())
            assertEquals(displayName, publicKey.get("user").get("displayName").asText())

            // Step 2: Complete registration
            val completeRegResponse = WebAuthnTestHelpers.completeRegistration(client, startRegResponse, keyPair)

            assertEquals(HttpStatusCode.OK, completeRegResponse.status)
            val completeRegBody = objectMapper.readTree(completeRegResponse.bodyAsText())
            assertTrue(completeRegBody.get("success").asBoolean())
            assertEquals("Registration successful", completeRegBody.get("message").asText())

            // Step 3: Start authentication
            val startAuthResponse = WebAuthnTestHelpers.startAuthentication(client, username)
            assertEquals(HttpStatusCode.OK, startAuthResponse.status)
            val startAuthBody = objectMapper.readTree(startAuthResponse.bodyAsText())
            assertNotNull(startAuthBody.get("requestId"))
            assertNotNull(startAuthBody.get("publicKeyCredentialRequestOptions"))

            // Step 4: Complete authentication
            val completeAuthResponse = WebAuthnTestHelpers.completeAuthentication(client, startAuthResponse, keyPair)
            assertEquals(HttpStatusCode.OK, completeAuthResponse.status)
            val completeAuthBody = objectMapper.readTree(completeAuthResponse.bodyAsText())
            assertTrue(completeAuthBody.get("success").asBoolean())
            assertEquals("Authentication successful", completeAuthBody.get("message").asText())
            assertEquals(username, completeAuthBody.get("username").asText())
        }

    @Test
    fun `test data persistence across application restarts`() {
        val username = "persistence_test_user"
        val displayName = "Persistence Test User"
        val keyPair = WebAuthnTestHelpers.generateTestKeypair()

        testApplication {
            application {
                module(storageModule)
            }

            // Register a user
            WebAuthnTestHelpers.registerUser(client, username, displayName, keyPair)

            // Simulate application restart by stopping Koin
            stopKoin()
        }

        testApplication {
            // Start application again
            application {
                module(storageModule)
            }

            // Try to authenticate the previously registered user
            val startAuthResponse = WebAuthnTestHelpers.startAuthentication(client, username)

            assertEquals(HttpStatusCode.OK, startAuthResponse.status)
            val startAuthBody = objectMapper.readTree(startAuthResponse.bodyAsText())

            // Verify that the user's credentials were persisted and can be found
            assertNotNull(startAuthBody.get("requestId"))
            assertNotNull(startAuthBody.get("publicKeyCredentialRequestOptions"))

            val requestCredentialOptions = startAuthBody.get("publicKeyCredentialRequestOptions")
            val allowCredentials = requestCredentialOptions.get("publicKey").get("allowCredentials")
            assertTrue(allowCredentials.size() > 0, "User credentials should be found after restart")
        }
    }

    @Test
    fun `test registration complete request id does not match`() =
        testApplication {
            application {
                module(storageModule)
            }

            val username = "integration_test_user"
            val displayName = "Integration Test User"
            WebAuthnTestHelpers.startRegistration(client, username, displayName)

            val completeRegRequest =
                RegistrationCompleteRequest(
                    requestId = UUID.randomUUID().toString(),
                    credential = "",
                )

            val completeRegResponse =
                client.post("/register/complete") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(completeRegRequest))
                }
            assertEquals(HttpStatusCode.BadRequest, completeRegResponse.status)
        }

    @Test
    fun `test authentication complete request id does not match`() =
        testApplication {
            application {
                module(storageModule)
            }

            val username = "integration_test_user"
            val displayName = "Integration Test User"
            val keyPair = WebAuthnTestHelpers.generateTestKeypair()
            val startRegResponse = WebAuthnTestHelpers.startRegistration(client, username, displayName)
            WebAuthnTestHelpers.completeRegistration(client, startRegResponse, keyPair)
            WebAuthnTestHelpers.startAuthentication(client, username)
            val completeAuthRequest =
                AuthenticationCompleteRequest(
                    requestId = UUID.randomUUID().toString(),
                    credential = "",
                )
            val completeAuthResponse =
                client.post("/authenticate/complete") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(completeAuthRequest))
                }

            assertEquals(HttpStatusCode.BadRequest, completeAuthResponse.status)
        }

    @Test
    fun `test Redis failure before registration start`() =
        testApplication {
            application {
                module(storageModule)
            }

            redis.stop()

            val username = "redis_failure_test"
            val displayName = "Redis Failure Test"

            val registrationRequest =
                RegistrationRequest(
                    username = username,
                    displayName = displayName,
                )

            val startRegResponse =
                client.post("/register/start") {
                    contentType(ContentType.Application.Json)
                    setBody(objectMapper.writeValueAsString(registrationRequest))
                }

            assertEquals(HttpStatusCode.InternalServerError, startRegResponse.status)
            redis.start()
        }

    @Test
    fun `test Redis failure before registration complete`() =
        testApplication {
            application {
                module(storageModule)
            }

            val username = "redis_failure_test"
            val displayName = "Redis Failure Test"
            val keyPair = WebAuthnTestHelpers.generateTestKeypair()

            val startRegResponse = WebAuthnTestHelpers.startRegistration(client, username, displayName)
            redis.stop()

            val completeRegResponse = WebAuthnTestHelpers.completeRegistration(client, startRegResponse, keyPair)
            assertEquals(HttpStatusCode.InternalServerError, completeRegResponse.status)

            redis.start()
        }

    @Test
    fun `test encrypted credential storage in PostgreSQL`() =
        testApplication {
            application {
                module(storageModule)
            }

            val username = "encryption_test_user"
            val displayName = "Encryption Test User"
            val keyPair = WebAuthnTestHelpers.generateTestKeypair()

            // Register a user (this will store quantum-safe encrypted data in PostgreSQL)
            WebAuthnTestHelpers.registerUser(client, username, displayName, keyPair)

            // Verify data is quantum-safe encrypted in the database by connecting directly
            postgres.createConnection("")?.use { connection ->
                val statement = connection.createStatement()
                val resultSet =
                    statement.executeQuery(
                        "SELECT encrypted_user_data, encrypted_credential_data FROM webauthn_users_secure u " +
                            "JOIN webauthn_credentials_secure c ON u.user_handle_hash = c.user_handle_hash " +
                            "WHERE u.username_hash = encode(sha256('$username'::bytea), 'hex')",
                    )

                assertTrue(resultSet.next(), "User should be found in database")

                val encryptedUserData = resultSet.getString("encrypted_user_data")
                val encryptedCredentialData = resultSet.getString("encrypted_credential_data")

                // Verify data is quantum-safe encrypted (should contain method signature)
                assertTrue(encryptedUserData.isNotEmpty())
                assertTrue(encryptedCredentialData.isNotEmpty())
                assertTrue(
                    encryptedUserData.contains("KYBER768-AES256-GCM"), 
                    "Should use quantum-safe encryption"
                )
                assertTrue(
                    encryptedCredentialData.contains("KYBER768-AES256-GCM"), 
                    "Should use quantum-safe encryption"
                )
                assertFalse(encryptedUserData.contains(username), "Username should not be in plaintext")
                assertFalse(encryptedUserData.contains(displayName), "Display name should not be in plaintext")
            }
        }
}
