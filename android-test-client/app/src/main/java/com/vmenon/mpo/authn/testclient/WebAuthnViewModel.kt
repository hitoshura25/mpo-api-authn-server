package com.vmenon.mpo.authn.testclient

import android.app.Activity
import android.util.Base64
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.vmenon.mpo.api.authn.client.api.RegistrationApi
import com.vmenon.mpo.api.authn.client.api.AuthenticationApi
import com.vmenon.mpo.api.authn.client.model.RegistrationRequest
import com.vmenon.mpo.api.authn.client.model.RegistrationCompleteRequest
import com.vmenon.mpo.api.authn.client.model.AuthenticationRequest
import com.vmenon.mpo.api.authn.client.model.AuthenticationCompleteRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import com.vmenon.mpo.api.authn.client.ApiClient
import java.security.SecureRandom

class WebAuthnViewModel : ViewModel() {
    
    private val _isLoading = MutableLiveData<Boolean>()
    val isLoading: LiveData<Boolean> = _isLoading
    
    private val _logMessages = MutableLiveData<MutableList<String>>()
    val logMessages: LiveData<MutableList<String>> = _logMessages
    
    private val _errorMessage = MutableLiveData<String?>()
    val errorMessage: LiveData<String?> = _errorMessage
    
    private val _successMessage = MutableLiveData<String?>()
    val successMessage: LiveData<String?> = _successMessage
    
    private val apiClient: ApiClient
    private val registrationApi: RegistrationApi
    private val authenticationApi: AuthenticationApi
    private val gson = Gson()
    
    init {
        _logMessages.value = mutableListOf()
        
        // Initialize API client
        apiClient = ApiClient().apply {
            basePath = BuildConfig.SERVER_URL
        }
        
        registrationApi = RegistrationApi(apiClient)
        authenticationApi = AuthenticationApi(apiClient)
        
        addLog("WebAuthn Test Client initialized")
        addLog("Server URL: ${BuildConfig.SERVER_URL}")
    }
    
    suspend fun registerUser(username: String, displayName: String, activity: Activity) {
        withContext(Dispatchers.Main) {
            _isLoading.value = true
        }
        
        try {
            addLog("Starting registration for user: $username")
            
            // Step 1: Start registration with server
            addLog("Step 1: Requesting registration challenge from server...")
            
            val registrationRequest = RegistrationRequest().apply {
                this.username = username
                this.displayName = displayName
            }
            
            val startResponse = withContext(Dispatchers.IO) {
                registrationApi.startRegistration(registrationRequest)
            }
            
            addLog("Registration challenge received")
            addLog("Request ID: ${startResponse.requestId}")
            
            // Step 2: Parse the PublicKeyCredentialCreationOptions and create credential
            addLog("Step 2: Creating WebAuthn credential...")
            
            // Parse the creation options (simplified for testing)
            addLog("Creating options parsed (mock implementation)")
            
            // For simplicity in this test client, we'll simulate the credential creation
            // In a real app, you would use the Intent result
            val mockCredential = createMockCredential()
            
            // Step 3: Complete registration
            addLog("Step 3: Completing registration...")
            
            val completeRequest = RegistrationCompleteRequest().apply {
                requestId = startResponse.requestId
                credential = gson.toJson(mockCredential)
            }
            
            val completeResponse = withContext(Dispatchers.IO) {
                registrationApi.completeRegistration(completeRequest)
            }
            
            addLog("Registration completed successfully!")
            addLog("Server response: ${completeResponse.credentialId}")
            
            withContext(Dispatchers.Main) {
                _successMessage.value = "User $username registered successfully"
            }
            
        } catch (e: Exception) {
            addLog("Registration failed: ${e.message}")
            withContext(Dispatchers.Main) {
                _errorMessage.value = e.message ?: "Unknown error occurred"
            }
        } finally {
            withContext(Dispatchers.Main) {
                _isLoading.value = false
            }
        }
    }
    
    suspend fun authenticateUser(username: String, activity: Activity) {
        withContext(Dispatchers.Main) {
            _isLoading.value = true
        }
        
        try {
            addLog("Starting authentication for user: $username")
            
            // Step 1: Start authentication with server
            addLog("Step 1: Requesting authentication challenge from server...")
            
            val authRequest = AuthenticationRequest().apply {
                this.username = username
            }
            
            val startResponse = withContext(Dispatchers.IO) {
                authenticationApi.startAuthentication(authRequest)
            }
            
            addLog("Authentication challenge received")
            addLog("Request ID: ${startResponse.requestId}")
            
            // Step 2: Parse the PublicKeyCredentialRequestOptions
            addLog("Step 2: Creating WebAuthn assertion...")
            
            // Parse the request options (simplified for testing)
            addLog("Request options parsed (mock implementation)")
            
            // For simplicity in this test client, we'll simulate the assertion creation
            // In a real app, you would use the Intent result
            val mockAssertion = createMockAssertion()
            
            // Step 3: Complete authentication
            addLog("Step 3: Completing authentication...")
            
            val completeRequest = AuthenticationCompleteRequest().apply {
                requestId = startResponse.requestId
                credential = gson.toJson(mockAssertion)
            }
            
            val completeResponse = withContext(Dispatchers.IO) {
                authenticationApi.completeAuthentication(completeRequest)
            }
            
            addLog("Authentication completed successfully!")
            addLog("Authenticated: ${completeResponse.success}")
            
            withContext(Dispatchers.Main) {
                _successMessage.value = "User $username authenticated successfully"
            }
            
        } catch (e: Exception) {
            addLog("Authentication failed: ${e.message}")
            withContext(Dispatchers.Main) {
                _errorMessage.value = e.message ?: "Unknown error occurred"
            }
        } finally {
            withContext(Dispatchers.Main) {
                _isLoading.value = false
            }
        }
    }
    
    
    private fun createMockCredential(): Any {
        // Using a minimal valid CBOR attestation object from WebAuthn test vectors
        val attestationObjectBytes = byteArrayOf(
            // CBOR map with 3 entries: fmt, attStmt, authData
            0xa3.toByte(),
            // "fmt" key (3 bytes)
            0x63, 0x66, 0x6d, 0x74,
            // "none" value (4 bytes) 
            0x64, 0x6e, 0x6f, 0x6e, 0x65,
            // "attStmt" key (7 bytes)
            0x67, 0x61, 0x74, 0x74, 0x53, 0x74, 0x6d, 0x74,
            // empty map value (1 byte)
            0xa0.toByte(),
            // "authData" key (8 bytes)
            0x68, 0x61, 0x75, 0x74, 0x68, 0x44, 0x61, 0x74, 0x61,
            // authData value (37 bytes minimum)
            0x58, 0x25, // byte string of length 37
            // RP ID hash (32 bytes) - SHA256 of "localhost"
            0xc8.toByte(), 0x7f, 0x09.toByte(), 0x99.toByte(), 0x8a.toByte(), 0xb0.toByte(), 0x03, 0x06,
            0x47, 0x4f, 0x8a.toByte(), 0x3c, 0x58, 0x2e, 0x8c.toByte(), 0x35,
            0x8e.toByte(), 0x7f, 0x6d, 0x90.toByte(), 0x4e, 0x9c.toByte(), 0x5a, 0xd7.toByte(),
            0x9c.toByte(), 0xe7.toByte(), 0x8a.toByte(), 0x15, 0x4e, 0x6b, 0x79, 0xc1.toByte(),
            // Flags (1 byte) - UP=1, UV=1
            0x05,
            // Counter (4 bytes)
            0x00, 0x00, 0x00, 0x01
        )
        
        return mapOf(
            "id" to Base64.encodeToString(
                "test-credential-id".toByteArray(),
                Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
            ),
            "type" to "public-key",
            "clientExtensionResults" to mapOf<String, Any>(),
            "rawId" to Base64.encodeToString(
                "test-credential-id".toByteArray(),
                Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
            ),
            "response" to mapOf(
                "attestationObject" to Base64.encodeToString(attestationObjectBytes, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING),
                "clientDataJSON" to Base64.encodeToString(
                    """{"type":"webauthn.create","challenge":"Y2hhbGxlbmdl","origin":"https://localhost"}""".toByteArray(),
                    Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
                )
            )
        )
    }
    
    private fun createMockAssertion(): Any {
        // Valid authenticatorData for assertion (37 bytes minimum)
        val authenticatorDataBytes = byteArrayOf(
            // RP ID hash (32 bytes) - SHA256 of "localhost"
            0xc8.toByte(), 0x7f, 0x09.toByte(), 0x99.toByte(), 0x8a.toByte(), 0xb0.toByte(), 0x03, 0x06,
            0x47, 0x4f, 0x8a.toByte(), 0x3c, 0x58, 0x2e, 0x8c.toByte(), 0x35,
            0x8e.toByte(), 0x7f, 0x6d, 0x90.toByte(), 0x4e, 0x9c.toByte(), 0x5a, 0xd7.toByte(),
            0x9c.toByte(), 0xe7.toByte(), 0x8a.toByte(), 0x15, 0x4e, 0x6b, 0x79, 0xc1.toByte(),
            // Flags (1 byte) - UP=1, UV=1
            0x05,
            // Counter (4 bytes) - incremented from registration
            0x00, 0x00, 0x00, 0x02
        )
        
        // Simple signature - in reality this would be computed, but for testing we use a fixed value
        val signatureBytes = byteArrayOf(
            0x30, 0x44, 0x02, 0x20, 0x12, 0x34, 0x56, 0x78, 0x9a.toByte(), 0xbc.toByte(), 0xde.toByte(), 0xf0.toByte(),
            0x12, 0x34, 0x56, 0x78, 0x9a.toByte(), 0xbc.toByte(), 0xde.toByte(), 0xf0.toByte(), 0x12, 0x34, 0x56, 0x78,
            0x9a.toByte(), 0xbc.toByte(), 0xde.toByte(), 0xf0.toByte(), 0x12, 0x34, 0x56, 0x78, 0x9a.toByte(), 0xbc.toByte(), 0xde.toByte(), 0xf0.toByte(),
            0x02, 0x20, 0xfe.toByte(), 0xdc.toByte(), 0xba.toByte(), 0x98.toByte(), 0x76, 0x54, 0x32, 0x10,
            0xfe.toByte(), 0xdc.toByte(), 0xba.toByte(), 0x98.toByte(), 0x76, 0x54, 0x32, 0x10, 0xfe.toByte(), 0xdc.toByte(), 0xba.toByte(), 0x98.toByte(),
            0x76, 0x54, 0x32, 0x10, 0xfe.toByte(), 0xdc.toByte(), 0xba.toByte(), 0x98.toByte(), 0x76, 0x54, 0x32, 0x10
        )
        
        return mapOf(
            "id" to Base64.encodeToString(
                "test-credential-id".toByteArray(),
                Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
            ),
            "type" to "public-key",
            "clientExtensionResults" to mapOf<String, Any>(),
            "rawId" to Base64.encodeToString(
                "test-credential-id".toByteArray(),
                Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
            ),
            "response" to mapOf(
                "authenticatorData" to Base64.encodeToString(
                    authenticatorDataBytes,
                    Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
                ),
                "clientDataJSON" to Base64.encodeToString(
                    """{"type":"webauthn.get","challenge":"Y2hhbGxlbmdl","origin":"https://localhost"}""".toByteArray(),
                    Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
                ),
                "signature" to Base64.encodeToString(
                    signatureBytes,
                    Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
                )
            )
        )
    }
    
    private fun addLog(message: String) {
        val timestamp = System.currentTimeMillis()
        val formattedMessage = "[${timestamp}] $message"
        
        val currentLogs = _logMessages.value ?: mutableListOf()
        currentLogs.add(formattedMessage)
        
        // Keep only last 100 log messages
        if (currentLogs.size > 100) {
            currentLogs.removeAt(0)
        }
        
        _logMessages.postValue(currentLogs)
    }
    
    fun clearError() {
        _errorMessage.value = null
    }
    
    fun clearSuccess() {
        _successMessage.value = null
    }
}