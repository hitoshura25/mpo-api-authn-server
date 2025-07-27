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
import com.vmenon.mpo.api.authn.client.model.*
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
                publicKeyCredential = mockCredential
            }
            
            val completeResponse = withContext(Dispatchers.IO) {
                registrationApi.completeRegistration(completeRequest)
            }
            
            addLog("Registration completed successfully!")
            addLog("Credential ID: ${completeResponse.credentialId}")
            
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
                publicKeyCredential = mockAssertion
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
        // Create a mock credential response for testing
        // In a real app, this would come from the FIDO2 API
        return mapOf(
            "id" to "mock-credential-id",
            "type" to "public-key",
            "rawId" to Base64.encodeToString("mock-raw-id".toByteArray(), Base64.NO_WRAP),
            "response" to mapOf(
                "attestationObject" to Base64.encodeToString("mock-attestation".toByteArray(), Base64.NO_WRAP),
                "clientDataJSON" to Base64.encodeToString("mock-client-data".toByteArray(), Base64.NO_WRAP)
            )
        )
    }
    
    private fun createMockAssertion(): Any {
        // Create a mock assertion response for testing
        // In a real app, this would come from the FIDO2 API
        return mapOf(
            "id" to "mock-credential-id",
            "type" to "public-key",
            "rawId" to Base64.encodeToString("mock-raw-id".toByteArray(), Base64.NO_WRAP),
            "response" to mapOf(
                "authenticatorData" to Base64.encodeToString("mock-auth-data".toByteArray(), Base64.NO_WRAP),
                "clientDataJSON" to Base64.encodeToString("mock-client-data".toByteArray(), Base64.NO_WRAP),
                "signature" to Base64.encodeToString("mock-signature".toByteArray(), Base64.NO_WRAP)
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