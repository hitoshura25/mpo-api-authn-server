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
    fun testRegistrationAndAuthenticationFlow() = runBlocking {
        val testUsername = "test-user-${UUID.randomUUID()}"
        val testDisplayName = "Test User ${System.currentTimeMillis()}"

        try {
            // Registration
            // Step 1: Start registration
            val registrationRequest = RegistrationRequest().apply {
                username = testUsername
                displayName = testDisplayName
            }

            val startRegistrationResponse = registrationApi.startRegistration(registrationRequest)

            // Verify response
            assert(startRegistrationResponse.requestId != null) { "Request ID should not be null" }
            assert(startRegistrationResponse.publicKeyCredentialCreationOptions != null) {
                "PublicKeyCredentialCreationOptions should not be null"
            }

            println("✓ Registration start successful - Request ID: ${startRegistrationResponse.requestId}")

            // Step 2: Extract challenge and generate test credential via test service
            val challenge = extractChallenge(startRegistrationResponse.publicKeyCredentialCreationOptions)
            val testCredentialResponse = testServiceClient.generateRegistrationCredential(
                TestRegistrationRequest(
                    challenge = challenge,
                    username = testUsername,
                    displayName = testDisplayName
                )
            )

            // Step 3: Complete registration using test service generated credential
            val completeRegistrationRequest = RegistrationCompleteRequest().apply {
                requestId = startRegistrationResponse.requestId
                credential = testCredentialResponse.credential
            }

            val completeRegistrationResponse = registrationApi.completeRegistration(completeRegistrationRequest)

            // Verify completion response
            assert(completeRegistrationResponse.success == true) { "Registration should be successful" }
            assert(completeRegistrationResponse.message == "Registration successful") { "Message should be 'Registration successful'" }

            println("✓ Registration complete successful - ${completeRegistrationResponse.message}")

            // Authentication
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
                    credentialId = testCredentialResponse.credentialId!!, // Use credential ID from registration
                    keyPairId = testCredentialResponse.keyPairId // Use key pair ID from registration
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
            println("✗ Registration test failed: ${e.message}")
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
