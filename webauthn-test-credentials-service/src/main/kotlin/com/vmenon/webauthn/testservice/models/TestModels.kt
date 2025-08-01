package com.vmenon.webauthn.testservice.models

import com.fasterxml.jackson.annotation.JsonProperty

/**
 * Request to generate a test registration credential
 */
data class TestRegistrationRequest(
    @JsonProperty("challenge")
    val challenge: String,
    @JsonProperty("rpId")
    val rpId: String = "localhost",
    @JsonProperty("origin")
    val origin: String = "https://localhost",
    @JsonProperty("username")
    val username: String = "test-user",
    @JsonProperty("displayName")
    val displayName: String = "Test User",
)

/**
 * Request to generate a test authentication credential
 */
data class TestAuthenticationRequest(
    @JsonProperty("challenge")
    val challenge: String,
    @JsonProperty("credentialId")
    val credentialId: String,
    @JsonProperty("keyPairId")
    val keyPairId: String,
    @JsonProperty("rpId")
    val rpId: String = "localhost",
    @JsonProperty("origin")
    val origin: String = "https://localhost",
)

/**
 * Response containing generated test credential
 */
data class TestCredentialResponse(
    @JsonProperty("credential")
    val credential: String,
    @JsonProperty("keyPairId")
    val keyPairId: String,
    @JsonProperty("credentialId")
    val credentialId: String? = null,
)

/**
 * Health check response
 */
data class HealthResponse(
    @JsonProperty("status")
    val status: String,
    @JsonProperty("timestamp")
    val timestamp: Long,
    @JsonProperty("service")
    val service: String = "webauthn-test-credentials-service",
)

/**
 * Error response
 */
data class ErrorResponse(
    @JsonProperty("error")
    val error: String,
    @JsonProperty("details")
    val details: String? = null,
)
