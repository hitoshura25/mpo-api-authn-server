package com.vmenon.mpo.api.authn.testutils

import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.node.ObjectNode
import com.vmenon.mpo.api.authn.AuthenticationCompleteRequest
import com.vmenon.mpo.api.authn.AuthenticationRequest
import com.vmenon.mpo.api.authn.RegistrationCompleteRequest
import com.vmenon.mpo.api.authn.RegistrationRequest
import com.vmenon.mpo.api.authn.utils.JacksonUtils
import com.vmenon.webauthn.testlib.WebAuthnTestAuthenticator
import com.yubico.webauthn.data.ByteArray
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import java.security.KeyPair
import kotlin.test.assertEquals

/**
 * Shared test utilities for WebAuthn registration and authentication flows
 *
 * This class provides reusable methods to eliminate duplication across test files:
 * - EndToEndIntegrationTest
 * - VulnerabilityProtectionTest
 * - Other WebAuthn test classes
 */
object WebAuthnTestHelpers {
    private val objectMapper = JacksonUtils.objectMapper

    /**
     * Performs complete user registration flow
     * @param client HTTP client for making requests
     * @param username Username to register
     * @param displayName Display name for the user
     * @param keyPair Cryptographic key pair for the user
     * @return Registration response
     */
    suspend fun registerUser(
        client: HttpClient,
        username: String,
        displayName: String,
        keyPair: KeyPair,
    ): HttpResponse {
        val startRegResponse = startRegistration(client, username, displayName)
        assertEquals(HttpStatusCode.OK, startRegResponse.status, "Registration start should succeed")

        return completeRegistration(client, startRegResponse, keyPair)
    }

    /**
     * Starts WebAuthn registration process
     * @param client HTTP client for making requests
     * @param username Username to register
     * @param displayName Display name for the user
     * @return Registration start response
     */
    suspend fun startRegistration(
        client: HttpClient,
        username: String,
        displayName: String,
    ): HttpResponse {
        val registrationRequest =
            RegistrationRequest(
                username = username,
                displayName = displayName,
            )

        return client.post("/register/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(registrationRequest))
        }
    }

    /**
     * Completes WebAuthn registration process
     * @param client HTTP client for making requests
     * @param startRegResponse Response from registration start
     * @param keyPair Cryptographic key pair for the user
     * @return Registration complete response
     */
    suspend fun completeRegistration(
        client: HttpClient,
        startRegResponse: HttpResponse,
        keyPair: KeyPair,
    ): HttpResponse {
        val startRegBody = objectMapper.readTree(startRegResponse.bodyAsText())
        val requestId = startRegBody.get("requestId").asText()
        val challenge = extractChallenge(startRegBody, "publicKeyCredentialCreationOptions")

        val credential =
            WebAuthnTestAuthenticator.createRegistrationCredential(
                ByteArray.fromBase64Url(challenge).bytes,
                keyPair,
            )

        val completeRegRequest =
            RegistrationCompleteRequest(
                requestId = requestId,
                credential = objectMapper.writeValueAsString(credential),
            )

        return client.post("/register/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeRegRequest))
        }
    }

    /**
     * Starts WebAuthn authentication process
     * @param client HTTP client for making requests
     * @param username Username to authenticate
     * @return Authentication start response
     */
    suspend fun startAuthentication(
        client: HttpClient,
        username: String,
    ): HttpResponse {
        val authRequest = AuthenticationRequest(username = username)

        return client.post("/authenticate/start") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(authRequest))
        }
    }

    /**
     * Completes WebAuthn authentication process
     * @param client HTTP client for making requests
     * @param startAuthResponse Response from authentication start
     * @param keyPair Cryptographic key pair for the user
     * @param credentialId Optional credential ID (will be extracted from response if not provided)
     * @return Authentication complete response
     */
    suspend fun completeAuthentication(
        client: HttpClient,
        startAuthResponse: HttpResponse,
        keyPair: KeyPair,
        credentialId: String? = null,
    ): HttpResponse {
        val startAuthBody = objectMapper.readTree(startAuthResponse.bodyAsText())
        val authRequestId = startAuthBody.get("requestId").asText()
        val authChallenge = extractChallenge(startAuthBody, "publicKeyCredentialRequestOptions")

        val actualCredentialId = credentialId ?: extractCredentialId(startAuthBody)

        val authCredential =
            WebAuthnTestAuthenticator.createAuthenticationCredential(
                ByteArray.fromBase64Url(authChallenge).bytes,
                ByteArray.fromBase64Url(actualCredentialId).bytes,
                keyPair,
            )

        val completeAuthRequest =
            AuthenticationCompleteRequest(
                requestId = authRequestId,
                credential = objectMapper.writeValueAsString(authCredential),
            )

        return client.post("/authenticate/complete") {
            contentType(ContentType.Application.Json)
            setBody(objectMapper.writeValueAsString(completeAuthRequest))
        }
    }

    /**
     * Extracts challenge from WebAuthn response with proper JSON structure handling
     * Handles the nested publicKey structure correctly
     * @param responseData JSON response from WebAuthn endpoint
     * @param optionsField Name of the options field (e.g., "publicKeyCredentialCreationOptions")
     * @return Base64URL encoded challenge
     */
    fun extractChallenge(
        responseData: JsonNode,
        optionsField: String,
    ): String {
        return responseData.get(optionsField)
            ?.get("publicKey")
            ?.get("challenge")
            ?.asText()
            ?: throw IllegalArgumentException("Challenge not found in response")
    }

    /**
     * Extracts credential ID from authentication start response
     * @param authStartResponse Authentication start response
     * @return Base64URL encoded credential ID
     */
    fun extractCredentialId(authStartResponse: JsonNode): String {
        val allowCredentials =
            authStartResponse
                .get("publicKeyCredentialRequestOptions")
                ?.get("publicKey")
                ?.get("allowCredentials")

        return allowCredentials?.firstOrNull()?.get("id")?.asText()
            ?: "test-credential-id" // Fallback for tests
    }

    /**
     * Extracts request ID from WebAuthn response
     * @param responseData JSON response from WebAuthn endpoint
     * @return Request ID string
     */
    fun extractRequestId(responseData: JsonNode): String {
        return responseData.get("requestId")?.asText()
            ?: throw IllegalArgumentException("Request ID not found in response")
    }

    /**
     * Creates a tampered credential with modified origin for security testing
     * @param challenge Original challenge
     * @param keyPair User's key pair
     * @param maliciousOrigin Malicious origin to inject
     * @return Tampered credential JSON string
     */
    fun createTamperedCredentialWithOrigin(
        challenge: String,
        keyPair: KeyPair,
        maliciousOrigin: String,
    ): String {
        val credential =
            WebAuthnTestAuthenticator.createAuthenticationCredential(
                ByteArray.fromBase64Url(challenge).bytes,
                ByteArray.fromBase64Url("test-credential-id").bytes,
                keyPair,
            )

        val credentialJson = objectMapper.writeValueAsString(credential)
        val credentialNode = objectMapper.readTree(credentialJson) as ObjectNode

        // Create malicious client data JSON
        val maliciousClientData = """{"type":"webauthn.get","challenge":"$challenge","origin":"$maliciousOrigin"}"""
        val maliciousClientDataB64 = java.util.Base64.getEncoder().encodeToString(maliciousClientData.toByteArray())

        credentialNode.put("clientDataJSON", maliciousClientDataB64)
        return objectMapper.writeValueAsString(credentialNode)
    }

    /**
     * Creates a credential with tampered signature for security testing
     * @param credentialJson Original credential JSON
     * @return Tampered credential JSON string
     */
    fun tamperCredentialSignature(credentialJson: String): String {
        val credentialNode = objectMapper.readTree(credentialJson) as ObjectNode
        credentialNode.put("signature", "dGFtcGVyZWRfc2lnbmF0dXJl") // "tampered_signature" in base64
        return objectMapper.writeValueAsString(credentialNode)
    }

    /**
     * Generates a unique test username with timestamp
     * @param prefix Prefix for the username
     * @return Unique username
     */
    fun generateTestUsername(prefix: String = "test_user"): String {
        return "${prefix}_${System.currentTimeMillis()}"
    }

    /**
     * Generates a keypair for testing
     * @return Test key pair using default algorithm
     */
    fun generateTestKeypair(): KeyPair {
        return WebAuthnTestAuthenticator.generateKeyPair()
    }
}
