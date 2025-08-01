package com.vmenon.mpo.authn.testclient

import com.google.gson.annotations.SerializedName

/**
 * Models for communicating with webauthn-test-service
 * These mirror the models in webauthn-test-service but use Gson annotations
 */

/**
 * Request to generate a test registration credential
 */
data class TestRegistrationRequest(
    @SerializedName("challenge") 
    val challenge: String,
    
    @SerializedName("rpId") 
    val rpId: String = "localhost",
    
    @SerializedName("origin") 
    val origin: String = "https://localhost",
    
    @SerializedName("username") 
    val username: String = "test-user",
    
    @SerializedName("displayName") 
    val displayName: String = "Test User"
)

/**
 * Request to generate a test authentication credential
 */
data class TestAuthenticationRequest(
    @SerializedName("challenge") 
    val challenge: String,
    
    @SerializedName("credentialId") 
    val credentialId: String,
    
    @SerializedName("keyPairId") 
    val keyPairId: String,
    
    @SerializedName("rpId") 
    val rpId: String = "localhost",
    
    @SerializedName("origin") 
    val origin: String = "https://localhost"
)

/**
 * Response containing generated test credential
 */
data class TestCredentialResponse(
    @SerializedName("credential") 
    val credential: String,
    
    @SerializedName("keyPairId") 
    val keyPairId: String,
    
    @SerializedName("credentialId") 
    val credentialId: String? = null
)

/**
 * Health check response for test service
 */
data class TestServiceHealthResponse(
    @SerializedName("status") 
    val status: String,
    
    @SerializedName("timestamp") 
    val timestamp: Long,
    
    @SerializedName("service") 
    val service: String = "webauthn-test-service"
)