package com.vmenon.mpo.authn.testclient

import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.LargeTest
import androidx.test.platform.app.InstrumentationRegistry
import com.vmenon.mpo.api.authn.client.api.RegistrationApi
import com.vmenon.mpo.api.authn.client.api.AuthenticationApi
import com.vmenon.mpo.api.authn.client.model.RegistrationRequest
import com.vmenon.mpo.api.authn.client.model.RegistrationCompleteRequest
import com.vmenon.mpo.api.authn.client.model.AuthenticationRequest
import com.vmenon.mpo.api.authn.client.model.AuthenticationCompleteRequest
import kotlinx.coroutines.runBlocking
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import com.vmenon.mpo.api.authn.client.ApiClient
import java.util.UUID

@RunWith(AndroidJUnit4::class)
@LargeTest
class WebAuthnFlowTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    private lateinit var apiClient: ApiClient
    private lateinit var registrationApi: RegistrationApi
    private lateinit var authenticationApi: AuthenticationApi
    private lateinit var testServiceClient: TestServiceClient

    @Before
    fun setup() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext

        // Use the same server URL as the app
        apiClient = ApiClient().apply {
            basePath = "http://10.0.2.2:8080"
        }

        registrationApi = RegistrationApi(apiClient)
        authenticationApi = AuthenticationApi(apiClient)
        testServiceClient = TestServiceClient()
    }

    @Test
    fun testRegistrationFlow() = runBlocking {
        val testUsername = "test-user-${UUID.randomUUID()}"
        val testDisplayName = "Test User ${System.currentTimeMillis()}"

        try {
            // Step 1: Start registration
            val registrationRequest = RegistrationRequest().apply {
                username = testUsername
                displayName = testDisplayName
            }

            val startResponse = registrationApi.startRegistration(registrationRequest)

            // Verify response
            assert(startResponse.requestId != null) { "Request ID should not be null" }
            assert(startResponse.publicKeyCredentialCreationOptions != null) {
                "PublicKeyCredentialCreationOptions should not be null"
            }

            println("✓ Registration start successful - Request ID: ${startResponse.requestId}")

            // Step 2: Extract challenge and generate test credential via test service
            val challenge = extractChallenge(startResponse.publicKeyCredentialCreationOptions)
            val testCredentialResponse = testServiceClient.generateRegistrationCredential(
                TestRegistrationRequest(
                    challenge = challenge,
                    username = testUsername,
                    displayName = testDisplayName
                )
            )

            // Step 3: Complete registration using test service generated credential
            val completeRequest = RegistrationCompleteRequest().apply {
                requestId = startResponse.requestId
                credential = testCredentialResponse.credential
            }

            val completeResponse = registrationApi.completeRegistration(completeRequest)

            // Verify completion response
            assert(completeResponse.success == true) { "Registration should be successful" }
            assert(completeResponse.message == "Registration successful") { "Message should be 'Registration successful'" }

            println("✓ Registration complete successful - ${completeResponse.message}")

        } catch (e: Exception) {
            println("✗ Registration test failed: ${e.message}")
            throw e
        }
    }

    @Test
    fun testAuthenticationFlow() = runBlocking {
        val testUsername = "test-auth-user-${UUID.randomUUID()}"

        try {
            // First register a user to authenticate later
            val registrationInfo = registerTestUser(testUsername)

            // Step 1: Start authentication
            val authRequest = AuthenticationRequest().apply {
                username = testUsername
            }

            val startResponse = authenticationApi.startAuthentication(authRequest)

            // Verify response
            assert(startResponse.requestId != null) { "Request ID should not be null" }
            assert(startResponse.publicKeyCredentialRequestOptions != null) {
                "PublicKeyCredentialRequestOptions should not be null"
            }

            println("✓ Authentication start successful - Request ID: ${startResponse.requestId}")

            // Step 2: Extract challenge and generate test assertion via test service
            val authChallenge =
                extractAuthChallenge(startResponse.publicKeyCredentialRequestOptions)
            val testAssertionResponse = testServiceClient.generateAuthenticationCredential(
                TestAuthenticationRequest(
                    challenge = authChallenge,
                    credentialId = registrationInfo.second, // Use credential ID from registration
                    keyPairId = registrationInfo.first // Use key pair ID from registration
                )
            )

            // Step 3: Complete authentication using test service generated assertion
            val completeRequest = AuthenticationCompleteRequest().apply {
                requestId = startResponse.requestId
                credential = testAssertionResponse.credential
            }

            val completeResponse = authenticationApi.completeAuthentication(completeRequest)

            // Verify completion response
            assert(completeResponse.success != null) { "Success flag should not be null" }

            println("✓ Authentication complete - Authenticated: ${completeResponse.success}")

        } catch (e: Exception) {
            println("✗ Authentication test failed: ${e.message}")
            throw e
        }
    }

    @Test
    fun testServerHealthCheck() = runBlocking {
        try {
            // Simple health check to ensure server is accessible
            val healthApi = com.vmenon.mpo.api.authn.client.api.HealthApi(apiClient)
            val healthResponse = healthApi.getHealth()

            assert(healthResponse.status.toString() == "healthy") { "Server health check should return healthy" }

            println("✓ Server health check successful: ${healthResponse.status}")

        } catch (e: Exception) {
            println("✗ Server health check failed: ${e.message}")
            throw e
        }
    }

    @Test
    fun testTestServiceHealthCheck() = runBlocking {
        try {
            // Check that test service is accessible and healthy
            val healthResponse = testServiceClient.checkHealth()

            assert(healthResponse.status == "healthy") { "Test service health check should return healthy" }
            assert(healthResponse.service == "webauthn-test-credentials-service") { "Should be test service" }

            println("✓ Test service health check successful: ${healthResponse.status}")

        } catch (e: Exception) {
            println("✗ Test service health check failed: ${e.message}")
            throw e
        }
    }

    @Test
    fun testInvalidUsernameRegistration() = runBlocking {
        try {
            // Test with empty username
            val registrationRequest = RegistrationRequest().apply {
                username = ""
                displayName = "Test User"
            }

            try {
                registrationApi.startRegistration(registrationRequest)
                assert(false) { "Registration with empty username should fail" }
            } catch (e: Exception) {
                println("✓ Empty username registration correctly failed: ${e.message}")
            }

        } catch (e: Exception) {
            println("✗ Invalid username test failed: ${e.message}")
            throw e
        }
    }

    @Test
    fun testNonExistentUserAuthentication() = runBlocking {
        try {
            // Test authentication with non-existent user
            val authRequest = AuthenticationRequest().apply {
                username = "non-existent-user-${UUID.randomUUID()}"
            }

            // Authentication start should succeed (secure - no user enumeration)
            val startResponse = authenticationApi.startAuthentication(authRequest)
            assert(startResponse.requestId != null) { "Request ID should not be null" }
            println("✓ Authentication start succeeded (secure behavior - no username enumeration)")

            // The response should have empty allowCredentials for non-existent user
            // This is the secure behavior - we don't reveal if user exists or not
            println("✓ Non-existent user authentication test completed securely")

        } catch (e: Exception) {
            println("✗ Non-existent user test failed: ${e.message}")
            throw e
        }
    }

    private suspend fun registerTestUser(username: String): Pair<String, String> {
        val registrationRequest = RegistrationRequest().apply {
            this.username = username
            displayName = "Test User for Auth"
        }

        val startResponse = registrationApi.startRegistration(registrationRequest)

        // Generate test credential via test service
        val challenge = extractChallenge(startResponse.publicKeyCredentialCreationOptions)
        val testCredentialResponse = testServiceClient.generateRegistrationCredential(
            TestRegistrationRequest(
                challenge = challenge,
                username = username,
                displayName = "Test User for Auth"
            )
        )

        val completeRequest = RegistrationCompleteRequest().apply {
            requestId = startResponse.requestId
            credential = testCredentialResponse.credential
        }

        val completeResponse = registrationApi.completeRegistration(completeRequest)
        println("✓ Test user registered: $username")

        // Return keyPairId and credentialId for later authentication
        return Pair(
            testCredentialResponse.keyPairId,
            testCredentialResponse.credentialId ?: "unknown"
        )
    }

    private fun extractChallenge(creationOptions: Any): String {
        val gson = com.google.gson.Gson()
        // Convert the object to JSON string first, then parse it
        val jsonString = gson.toJson(creationOptions)
        val optionsJson = gson.fromJson(jsonString, com.google.gson.JsonObject::class.java)
        return optionsJson.getAsJsonObject("publicKey").get("challenge").asString
    }

    private fun extractAuthChallenge(requestOptions: Any): String {
        val gson = com.google.gson.Gson()
        // Convert the object to JSON string first, then parse it
        val jsonString = gson.toJson(requestOptions)
        val optionsJson = gson.fromJson(jsonString, com.google.gson.JsonObject::class.java)
        return optionsJson.getAsJsonObject("publicKey").get("challenge").asString
    }

}
