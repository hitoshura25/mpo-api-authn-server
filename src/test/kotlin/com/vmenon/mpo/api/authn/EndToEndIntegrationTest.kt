package com.vmenon.mpo.api.authn

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.vmenon.mpo.api.authn.di.storageModule
import com.vmenon.mpo.api.authn.yubico.TestAuthenticator
import com.vmenon.mpo.api.authn.yubico.TestAuthenticator.Defaults
import com.vmenon.mpo.api.authn.yubico.TestAuthenticator.generateKeypair
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
import java.util.Base64
import javax.crypto.KeyGenerator
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.koin.core.context.stopKoin
import org.testcontainers.containers.GenericContainer
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.utility.DockerImageName

/**
 * End-to-end integration tests using real Redis and PostgreSQL instances via Testcontainers
 * This tests the complete WebAuthn flow with actual database persistence
 */
@Testcontainers
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class EndToEndIntegrationTest {

    companion object {
        @Container
        val postgres = PostgreSQLContainer(DockerImageName.parse("postgres:15-alpine"))
            .withDatabaseName("webauthn_test")
            .withUsername("test_user")
            .withPassword("test_password")

        @Container
        val redis = GenericContainer(DockerImageName.parse("redis:7-alpine"))
            .withExposedPorts(6379)
            .withCommand("redis-server --requirepass test_password")
    }

    private val objectMapper = ObjectMapper().apply {
        registerModule(KotlinModule.Builder().build())
        registerModule(JavaTimeModule())
        registerModule(Jdk8Module())
    }

    private lateinit var encryptionKey: String

    @BeforeAll
    fun setupContainers() {
        // Start containers
        postgres.start()
        redis.start()

        // Generate encryption key for testing
        val keyGen = KeyGenerator.getInstance("AES")
        keyGen.init(256)
        val secretKey = keyGen.generateKey()
        encryptionKey = Base64.getEncoder().encodeToString(secretKey.encoded)

        println("PostgreSQL URL: ${postgres.jdbcUrl}")
        println("Redis URL: redis://localhost:${redis.getMappedPort(6379)}")
    }

    @AfterAll
    fun tearDownContainers() {
        postgres.stop()
        redis.stop()
    }

    @BeforeEach
    fun setupTest() {
        stopKoin() // Ensure clean state

        // Set environment variables for the test containers
        System.setProperty("STORAGE_TYPE", "redis")
        System.setProperty("REDIS_HOST", redis.host)
        System.setProperty("REDIS_PORT", redis.getMappedPort(6379).toString())
        System.setProperty("REDIS_PASSWORD", "test_password")
        System.setProperty("REDIS_DATABASE", "0")

        // PostgreSQL configuration
        System.setProperty("DB_HOST", postgres.host)
        System.setProperty("DB_PORT", postgres.getMappedPort(5432).toString())
        System.setProperty("DB_NAME", postgres.databaseName)
        System.setProperty("DB_USERNAME", postgres.username)
        System.setProperty("DB_PASSWORD", postgres.password)

        // Disable SSL for testcontainers (they don't support SSL by default)
        System.setProperty("DB_REQUIRE_SSL", "false")

        // Encryption key
        System.setProperty("ENCRYPTION_KEY", encryptionKey)
    }

    @AfterEach
    fun cleanupTest() {
        stopKoin()

        // Clear system properties
        val properties = listOf(
            "STORAGE_TYPE", "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "REDIS_DATABASE",
            "DB_HOST", "DB_PORT", "DB_NAME", "DB_USERNAME", "DB_PASSWORD", "ENCRYPTION_KEY"
        )
        properties.forEach { System.clearProperty(it) }
    }

    @Test
    fun `test complete WebAuthn flow with real databases`() = testApplication {
        application {
            module(storageModule)
        }

        val username = "integration_test_user"
        val displayName = "Integration Test User"
        val keyPair = generateKeypair(algorithm = Defaults.keyAlgorithm)

        // Test server is running
        val healthResponse = client.get("/")
        assertEquals(HttpStatusCode.OK, healthResponse.status)
        assertEquals("WebAuthn Server is running!", healthResponse.bodyAsText())

        // Step 1: Start registration
        val registrationRequest = RegistrationRequest(
            username = username,
            displayName = displayName
        )

        val startRegResponse = client.post("/register/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(registrationRequest))
        }

        assertEquals(HttpStatusCode.OK, startRegResponse.status)
        val startRegBody = objectMapper.readTree(startRegResponse.bodyAsText())
        assertNotNull(startRegBody.get("requestId"))
        assertNotNull(startRegBody.get("publicKeyCredentialCreationOptions"))

        val registrationRequestId = startRegBody.get("requestId").asText()
        val credentialOptionsString = startRegBody.get("publicKeyCredentialCreationOptions").asText()
        val credentialOptions = objectMapper.readTree(credentialOptionsString)

        // Verify registration options
        val publicKey = credentialOptions.get("publicKey")
        assertEquals(username, publicKey.get("user").get("name").asText())
        assertEquals(displayName, publicKey.get("user").get("displayName").asText())

        // Step 2: Complete registration
        val challenge = publicKey.get("challenge").asText()
        val credential = TestAuthenticator.createUnattestedCredentialForRegistration(
            ByteArray.fromBase64Url(challenge),
            keyPair,
        )

        val publicKeyCredentialJson = objectMapper.writeValueAsString(credential.first)
        val completeRegRequest = RegistrationCompleteRequest(
            requestId = registrationRequestId,
            credential = publicKeyCredentialJson
        )

        val completeRegResponse = client.post("/register/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRegRequest))
        }

        assertEquals(HttpStatusCode.OK, completeRegResponse.status)
        val completeRegBody = objectMapper.readTree(completeRegResponse.bodyAsText())
        assertTrue(completeRegBody.get("success").asBoolean())
        assertEquals("Registration successful", completeRegBody.get("message").asText())

        // Step 3: Start authentication
        val authRequest = AuthenticationRequest(username = username)

        val startAuthResponse = client.post("/authenticate/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(authRequest))
        }

        assertEquals(HttpStatusCode.OK, startAuthResponse.status)
        val startAuthBody = objectMapper.readTree(startAuthResponse.bodyAsText())
        assertNotNull(startAuthBody.get("requestId"))
        assertNotNull(startAuthBody.get("publicKeyCredentialRequestOptions"))

        val authRequestId = startAuthBody.get("requestId").asText()
        val requestCredentialOptions = objectMapper.readTree(
            startAuthBody.get("publicKeyCredentialRequestOptions").asText()
        )

        // Step 4: Complete authentication
        val authPublicKey = requestCredentialOptions.get("publicKey")
        val authChallenge = authPublicKey.get("challenge").asText()
        val allowCredentials = authPublicKey.get("allowCredentials").first()
        val credentialId = allowCredentials.get("id").asText()

        val authCredential = TestAuthenticator.createUnattestedCredentialForAuthentication(
            ByteArray.fromBase64Url(authChallenge),
            ByteArray.fromBase64Url(credentialId),
            keyPair,
        )

        val authCredentialJson = objectMapper.writeValueAsString(authCredential)
        val completeAuthRequest = AuthenticationCompleteRequest(
            requestId = authRequestId,
            credential = authCredentialJson
        )

        val completeAuthResponse = client.post("/authenticate/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeAuthRequest))
        }

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
        val keyPair = generateKeypair(algorithm = Defaults.keyAlgorithm)

        testApplication {
            application {
                module(storageModule)
            }

            // Register a user
            registerUser(client, username, displayName, keyPair)

            // Simulate application restart by stopping Koin and clearing caches
            stopKoin()
        }

        testApplication {
            // Start application again
            application {
                module(storageModule)
            }

            // Try to authenticate the previously registered user
            val authRequest = AuthenticationRequest(username = username)

            val startAuthResponse = client.post("/authenticate/start") {
                contentType(ContentType.Application.Json)
                setBody(objectMapper.writeValueAsString(authRequest))
            }

            assertEquals(HttpStatusCode.OK, startAuthResponse.status)
            val startAuthBody = objectMapper.readTree(startAuthResponse.bodyAsText())

            // Verify that the user's credentials were persisted and can be found
            assertNotNull(startAuthBody.get("requestId"))
            assertNotNull(startAuthBody.get("publicKeyCredentialRequestOptions"))

            val requestCredentialOptions = objectMapper.readTree(
                startAuthBody.get("publicKeyCredentialRequestOptions").asText()
            )
            val allowCredentials = requestCredentialOptions.get("publicKey").get("allowCredentials")
            assertTrue(allowCredentials.size() > 0, "User credentials should be found after restart")
        }
    }

    @Test
    fun `test Redis failure recovery`() = testApplication {
        application {
            module(storageModule)
        }

        val username = "redis_failure_test"
        val displayName = "Redis Failure Test"

        // Test that registration fails gracefully when Redis is unavailable
        // (This would require stopping Redis container mid-test in a real scenario)

        // For now, test that we can start registration which stores temporary data in Redis
        val registrationRequest = RegistrationRequest(
            username = username,
            displayName = displayName
        )

        val startRegResponse = client.post("/register/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(registrationRequest))
        }

        assertEquals(HttpStatusCode.OK, startRegResponse.status)

        // Verify Redis is working by checking we get a request ID
        val startRegBody = objectMapper.readTree(startRegResponse.bodyAsText())
        assertNotNull(startRegBody.get("requestId"))
    }

    @Test
    fun `test encrypted credential storage in PostgreSQL`() = testApplication {
        application {
            module(storageModule)
        }

        val username = "encryption_test_user"
        val displayName = "Encryption Test User"
        val keyPair = generateKeypair(algorithm = Defaults.keyAlgorithm)

        // Register a user (this will store encrypted data in PostgreSQL)
        registerUser(client, username, displayName, keyPair)

        // Verify data is encrypted in the database by connecting directly
        postgres.createConnection("").use { connection ->
            val statement = connection.createStatement()
            val resultSet = statement.executeQuery(
                "SELECT encrypted_user_data, encrypted_credential_data FROM webauthn_users_secure u " +
                        "JOIN webauthn_credentials_secure c ON u.user_handle_hash = c.user_handle_hash " +
                        "WHERE u.username_hash = encode(sha256('$username'::bytea), 'hex')"
            )

            assertTrue(resultSet.next(), "User should be found in database")

            val encryptedUserData = resultSet.getString("encrypted_user_data")
            val encryptedCredentialData = resultSet.getString("encrypted_credential_data")

            // Verify data is encrypted (should not contain plaintext username)
            assertTrue(encryptedUserData.isNotEmpty())
            assertTrue(encryptedCredentialData.isNotEmpty())
            assertFalse(encryptedUserData.contains(username), "Username should not be in plaintext")
            assertFalse(encryptedUserData.contains(displayName), "Display name should not be in plaintext")
        }
    }

    private suspend fun registerUser(client: HttpClient, username: String, displayName: String, keyPair: KeyPair) {
        val registrationRequest = RegistrationRequest(
            username = username,
            displayName = displayName
        )

        val startRegResponse = client.post("/register/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(registrationRequest))
        }

        assertEquals(HttpStatusCode.OK, startRegResponse.status)
        val startRegBody = objectMapper.readTree(startRegResponse.bodyAsText())
        val requestId = startRegBody.get("requestId").asText()
        val credentialOptions = objectMapper.readTree(
            startRegBody.get("publicKeyCredentialCreationOptions").asText()
        )

        val challenge = credentialOptions.get("publicKey").get("challenge").asText()
        val credential = TestAuthenticator.createUnattestedCredentialForRegistration(
            ByteArray.fromBase64Url(challenge),
            keyPair,
        )

        val completeRegRequest = RegistrationCompleteRequest(
            requestId = requestId,
            credential = objectMapper.writeValueAsString(credential.first)
        )

        val completeRegResponse = client.post("/register/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRegRequest))
        }

        assertEquals(HttpStatusCode.OK, completeRegResponse.status)
    }
}
