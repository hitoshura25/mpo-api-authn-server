package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.AssertionRequest
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions

/**
 * Interface for storing temporary WebAuthn requests with TTL support
 */
interface RequestStorage {

    /**
     * Store a registration request with TTL
     * @param requestId unique identifier for the request
     * @param options the registration options to store
     * @param ttlSeconds time to live in seconds (default 5 minutes)
     */
    fun storeRegistrationRequest(
        requestId: String,
        options: PublicKeyCredentialCreationOptions,
        ttlSeconds: Long = 300
    )

    /**
     * Retrieve and remove a registration request
     * @param requestId the request identifier
     * @return the stored options or null if not found/expired
     */
    fun retrieveAndRemoveRegistrationRequest(requestId: String): PublicKeyCredentialCreationOptions?

    /**
     * Store an assertion request with TTL
     * @param requestId unique identifier for the request
     * @param request the assertion request to store
     * @param ttlSeconds time to live in seconds (default 5 minutes)
     */
    fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long = 300
    )

    /**
     * Retrieve and remove an assertion request
     * @param requestId the request identifier
     * @return the stored request or null if not found/expired
     */
    fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest?

    /**
     * Close/cleanup resources
     */
    fun close()
}
