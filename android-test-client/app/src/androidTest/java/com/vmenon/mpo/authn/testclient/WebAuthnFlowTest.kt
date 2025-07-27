package com.vmenon.mpo.authn.testclient

import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.LargeTest
import androidx.test.platform.app.InstrumentationRegistry
import com.vmenon.mpo.api.authn.client.api.RegistrationApi
import com.vmenon.mpo.api.authn.client.api.AuthenticationApi
import com.vmenon.mpo.api.authn.client.model.*
import kotlinx.coroutines.runBlocking
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import com.vmenon.mpo.api.authn.client.ApiClient
import java.util.*

@RunWith(AndroidJUnit4::class)
@LargeTest
class WebAuthnFlowTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(MainActivity::class.java)

    private lateinit var apiClient: ApiClient
    private lateinit var registrationApi: RegistrationApi
    private lateinit var authenticationApi: AuthenticationApi

    @Before
    fun setup() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        
        // Use the same server URL as the app
        apiClient = ApiClient().apply {
            basePath = "http://10.0.2.2:8080"
        }
        
        registrationApi = RegistrationApi(apiClient)
        authenticationApi = AuthenticationApi(apiClient)
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

            // Step 2: Create mock credential (in real app, this would come from FIDO2 API)
            val mockCredential = createMockCredential()

            // Step 3: Complete registration
            val completeRequest = RegistrationCompleteRequest().apply {
                requestId = startResponse.requestId
                publicKeyCredential = mockCredential
            }

            val completeResponse = registrationApi.completeRegistration(completeRequest)

            // Verify completion response
            assert(completeResponse.credentialId != null) { "Credential ID should not be null" }
            
            println("✓ Registration complete successful - Credential ID: ${completeResponse.credentialId}")

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
            registerTestUser(testUsername)

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

            // Step 2: Create mock assertion (in real app, this would come from FIDO2 API)
            val mockAssertion = createMockAssertion()

            // Step 3: Complete authentication
            val completeRequest = AuthenticationCompleteRequest().apply {
                requestId = startResponse.requestId
                publicKeyCredential = mockAssertion
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

            try {
                authenticationApi.startAuthentication(authRequest)
                assert(false) { "Authentication for non-existent user should fail" }
            } catch (e: Exception) {
                println("✓ Non-existent user authentication correctly failed: ${e.message}")
            }

        } catch (e: Exception) {
            println("✗ Non-existent user test failed: ${e.message}")
            throw e
        }
    }

    private suspend fun registerTestUser(username: String) {
        val registrationRequest = RegistrationRequest().apply {
            this.username = username
            displayName = "Test User for Auth"
        }

        val startResponse = registrationApi.startRegistration(registrationRequest)
        val mockCredential = createMockCredential()

        val completeRequest = RegistrationCompleteRequest().apply {
            requestId = startResponse.requestId
            publicKeyCredential = mockCredential
        }

        registrationApi.completeRegistration(completeRequest)
        println("✓ Test user registered: $username")
    }

    private fun createMockCredential(): Map<String, Any> {
        return mapOf(
            "id" to "mock-credential-id-${UUID.randomUUID()}",
            "type" to "public-key",
            "rawId" to android.util.Base64.encodeToString(
                "mock-raw-id-${System.currentTimeMillis()}".toByteArray(), 
                android.util.Base64.NO_WRAP
            ),
            "response" to mapOf(
                "attestationObject" to android.util.Base64.encodeToString(
                    "mock-attestation-${System.currentTimeMillis()}".toByteArray(), 
                    android.util.Base64.NO_WRAP
                ),
                "clientDataJSON" to android.util.Base64.encodeToString(
                    """{"type":"webauthn.create","challenge":"mock-challenge","origin":"android:apk-key-hash:mock"}""".toByteArray(), 
                    android.util.Base64.NO_WRAP
                )
            )
        )
    }

    private fun createMockAssertion(): Map<String, Any> {
        return mapOf(
            "id" to "mock-credential-id-${UUID.randomUUID()}",
            "type" to "public-key",
            "rawId" to android.util.Base64.encodeToString(
                "mock-raw-id-${System.currentTimeMillis()}".toByteArray(), 
                android.util.Base64.NO_WRAP
            ),
            "response" to mapOf(
                "authenticatorData" to android.util.Base64.encodeToString(
                    "mock-auth-data-${System.currentTimeMillis()}".toByteArray(), 
                    android.util.Base64.NO_WRAP
                ),
                "clientDataJSON" to android.util.Base64.encodeToString(
                    """{"type":"webauthn.get","challenge":"mock-challenge","origin":"android:apk-key-hash:mock"}""".toByteArray(), 
                    android.util.Base64.NO_WRAP
                ),
                "signature" to android.util.Base64.encodeToString(
                    "mock-signature-${System.currentTimeMillis()}".toByteArray(), 
                    android.util.Base64.NO_WRAP
                )
            )
        )
    }
}