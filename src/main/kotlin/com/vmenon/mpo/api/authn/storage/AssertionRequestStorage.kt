package com.vmenon.mpo.api.authn.storage

import com.yubico.webauthn.AssertionRequest

/**
 * Interface for storing temporary WebAuthn assertion requests with TTL support
 */
interface AssertionRequestStorage {

    /**
     * Store an assertion request with TTL
     * @param requestId unique identifier for the request
     * @param request the assertion request to store
     * @param ttlSeconds time to live in seconds (default 5 minutes)
     */
    suspend fun storeAssertionRequest(
        requestId: String,
        request: AssertionRequest,
        ttlSeconds: Long = 300
    )

    /**
     * Retrieve and remove an assertion request
     * @param requestId the request identifier
     * @return the stored request or null if not found/expired
     */
    suspend fun retrieveAndRemoveAssertionRequest(requestId: String): AssertionRequest?

    /**
     * Close/cleanup resources
     */
    fun close()
}
